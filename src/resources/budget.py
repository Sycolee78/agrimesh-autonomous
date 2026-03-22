"""
Budget Manager - Enforce resource budgets with warning thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import threading


class BudgetStatus(str, Enum):
    """Budget consumption status."""
    NORMAL = "normal"       # Under 75% used
    WARNING = "warning"     # 75-90% used
    CRITICAL = "critical"   # 90-100% used
    EXCEEDED = "exceeded"   # Over 100%
    HARDSTOP = "hardstop"   # Cannot allocate more


class BudgetPeriod(str, Enum):
    """Budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"


@dataclass
class BudgetAlert:
    """Alert generated when budget threshold is crossed."""
    alert_id: str
    resource_type: str
    period: BudgetPeriod
    status: BudgetStatus
    current_usage: float
    budget_limit: float
    usage_percent: float
    message: str
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class BudgetConfig:
    """Configuration for a resource budget."""
    resource_type: str
    period: BudgetPeriod
    limit: float
    warning_threshold: float = 0.75  # 75%
    critical_threshold: float = 0.90  # 90%
    hard_stop: bool = True  # Prevent allocations over limit
    rollover: bool = False  # Allow unused budget to roll over
    rollover_cap: float = 0.25  # Max rollover (25% of limit)


@dataclass
class BudgetState:
    """Current state of a budget."""
    config: BudgetConfig
    period_start: datetime
    period_end: datetime
    used: float
    remaining: float
    status: BudgetStatus
    rollover_amount: float = 0.0
    alerts_generated: int = 0


class BudgetManager:
    """
    Manages resource budgets with enforcement and alerts.
    
    Features:
    - Daily/weekly/monthly budget limits
    - Warning (75%), critical (90%), hard-stop thresholds
    - Budget rollover for unused amounts
    - Alert generation and acknowledgment
    - Override capability for emergencies
    """
    
    # Threshold levels
    WARNING_THRESHOLD = 0.75
    CRITICAL_THRESHOLD = 0.90
    HARDSTOP_THRESHOLD = 1.00
    
    def __init__(self, farm_id: str):
        self.farm_id = farm_id
        self._lock = threading.RLock()
        
        # Budget configs and states
        self._budgets: Dict[str, Dict[BudgetPeriod, BudgetState]] = {}
        
        # Alerts
        self._alerts: List[BudgetAlert] = []
        self._alert_counter = 0
        
        # Override tracking
        self._overrides: Dict[str, datetime] = {}  # resource -> override_expiry
        
        # Listeners for budget events
        self._listeners: List[Callable] = []
    
    def configure_budget(
        self,
        resource_type: str,
        period: BudgetPeriod,
        limit: float,
        warning_threshold: float = 0.75,
        critical_threshold: float = 0.90,
        hard_stop: bool = True,
        rollover: bool = False,
        rollover_cap: float = 0.25,
    ) -> None:
        """Configure a budget for a resource."""
        with self._lock:
            config = BudgetConfig(
                resource_type=resource_type,
                period=period,
                limit=limit,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                hard_stop=hard_stop,
                rollover=rollover,
                rollover_cap=rollover_cap,
            )
            
            if resource_type not in self._budgets:
                self._budgets[resource_type] = {}
            
            # Calculate period boundaries
            now = datetime.now()
            period_start, period_end = self._calculate_period_bounds(period, now)
            
            self._budgets[resource_type][period] = BudgetState(
                config=config,
                period_start=period_start,
                period_end=period_end,
                used=0.0,
                remaining=limit,
                status=BudgetStatus.NORMAL,
            )
    
    def check_budget(
        self,
        resource_type: str,
        amount: float,
        period: Optional[BudgetPeriod] = None,
    ) -> tuple[bool, BudgetStatus, str]:
        """
        Check if an amount can be allocated within budget.
        
        Returns:
            (allowed, status, message)
        """
        with self._lock:
            budgets = self._budgets.get(resource_type, {})
            
            if not budgets:
                return True, BudgetStatus.NORMAL, "No budget configured"
            
            # Check all periods or specific one
            periods_to_check = [period] if period else list(budgets.keys())
            
            for p in periods_to_check:
                state = budgets.get(p)
                if not state:
                    continue
                
                # Refresh period if needed
                self._refresh_period_if_needed(state)
                
                # Check override
                if self._has_active_override(resource_type):
                    return True, state.status, "Override active - budget bypassed"
                
                new_total = state.used + amount
                usage_pct = new_total / state.config.limit if state.config.limit > 0 else 1.0
                
                # Check hard stop
                if state.config.hard_stop and usage_pct > 1.0:
                    return False, BudgetStatus.HARDSTOP, \
                        f"Budget exceeded for {p.value} period. Limit: {state.config.limit:.1f}, Used: {state.used:.1f}"
                
                # Determine status
                if usage_pct >= 1.0:
                    return True, BudgetStatus.EXCEEDED, \
                        f"Warning: {p.value} budget will be exceeded ({usage_pct*100:.0f}%)"
                elif usage_pct >= state.config.critical_threshold:
                    return True, BudgetStatus.CRITICAL, \
                        f"Critical: {p.value} budget at {usage_pct*100:.0f}%"
                elif usage_pct >= state.config.warning_threshold:
                    return True, BudgetStatus.WARNING, \
                        f"Warning: {p.value} budget at {usage_pct*100:.0f}%"
            
            return True, BudgetStatus.NORMAL, "Within budget"
    
    def record_usage(
        self,
        resource_type: str,
        amount: float,
        source: str = "unknown",
    ) -> List[BudgetAlert]:
        """
        Record resource usage and generate alerts if thresholds crossed.
        
        Returns any alerts generated.
        """
        alerts = []
        
        with self._lock:
            budgets = self._budgets.get(resource_type, {})
            
            for period, state in budgets.items():
                # Refresh period if needed
                self._refresh_period_if_needed(state)
                
                old_status = state.status
                state.used += amount
                state.remaining = max(0, state.config.limit - state.used)
                
                # Update status
                usage_pct = state.used / state.config.limit if state.config.limit > 0 else 1.0
                
                if usage_pct >= 1.0:
                    state.status = BudgetStatus.EXCEEDED
                elif usage_pct >= state.config.critical_threshold:
                    state.status = BudgetStatus.CRITICAL
                elif usage_pct >= state.config.warning_threshold:
                    state.status = BudgetStatus.WARNING
                else:
                    state.status = BudgetStatus.NORMAL
                
                # Generate alert if status worsened
                if self._status_worsened(old_status, state.status):
                    alert = self._create_alert(
                        resource_type=resource_type,
                        period=period,
                        status=state.status,
                        usage=state.used,
                        limit=state.config.limit,
                        source=source,
                    )
                    alerts.append(alert)
                    self._notify_listeners("budget_alert", alert)
            
        return alerts
    
    def get_budget_status(
        self,
        resource_type: str,
        period: Optional[BudgetPeriod] = None,
    ) -> Dict[str, Any]:
        """Get current budget status for a resource."""
        with self._lock:
            budgets = self._budgets.get(resource_type, {})
            
            if period:
                state = budgets.get(period)
                if state:
                    self._refresh_period_if_needed(state)
                    return self._state_to_dict(state)
                return {}
            
            result = {}
            for p, state in budgets.items():
                self._refresh_period_if_needed(state)
                result[p.value] = self._state_to_dict(state)
            
            return result
    
    def get_all_budgets(self) -> Dict[str, Any]:
        """Get status of all configured budgets."""
        with self._lock:
            result = {}
            for resource_type, periods in self._budgets.items():
                result[resource_type] = {}
                for period, state in periods.items():
                    self._refresh_period_if_needed(state)
                    result[resource_type][period.value] = self._state_to_dict(state)
            return result
    
    def set_override(
        self,
        resource_type: str,
        duration_hours: float = 1.0,
        reason: str = "emergency",
    ) -> None:
        """
        Set a temporary budget override (for emergencies).
        
        This bypasses budget enforcement for the specified duration.
        """
        with self._lock:
            expiry = datetime.now() + timedelta(hours=duration_hours)
            self._overrides[resource_type] = expiry
            
            alert = BudgetAlert(
                alert_id=f"override-{self._alert_counter}",
                resource_type=resource_type,
                period=BudgetPeriod.DAILY,
                status=BudgetStatus.NORMAL,
                current_usage=0,
                budget_limit=0,
                usage_percent=0,
                message=f"Budget override activated for {duration_hours}h. Reason: {reason}",
                metadata={"override": True, "reason": reason, "expiry": expiry.isoformat()},
            )
            self._alert_counter += 1
            self._alerts.append(alert)
            self._notify_listeners("budget_override", alert)
    
    def clear_override(self, resource_type: str) -> None:
        """Clear an active budget override."""
        with self._lock:
            if resource_type in self._overrides:
                del self._overrides[resource_type]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a budget alert."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
            return False
    
    def get_alerts(
        self,
        resource_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
    ) -> List[BudgetAlert]:
        """Get budget alerts with filters."""
        with self._lock:
            alerts = list(self._alerts)
            
            if resource_type:
                alerts = [a for a in alerts if a.resource_type == resource_type]
            
            if acknowledged is not None:
                alerts = [a for a in alerts if a.acknowledged == acknowledged]
            
            return alerts[-limit:]
    
    def get_burn_rate(
        self,
        resource_type: str,
        period: BudgetPeriod = BudgetPeriod.DAILY,
    ) -> Dict[str, float]:
        """Calculate current burn rate for budget planning."""
        with self._lock:
            budgets = self._budgets.get(resource_type, {})
            state = budgets.get(period)
            
            if not state:
                return {}
            
            self._refresh_period_if_needed(state)
            
            # Calculate elapsed time
            now = datetime.now()
            elapsed = (now - state.period_start).total_seconds()
            total_seconds = (state.period_end - state.period_start).total_seconds()
            
            if elapsed <= 0:
                return {}
            
            # Current rate
            current_rate = state.used / (elapsed / 3600)  # per hour
            
            # Projected usage at current rate
            remaining_hours = (state.period_end - now).total_seconds() / 3600
            projected_total = state.used + (current_rate * remaining_hours)
            
            # Required rate to stay within budget
            safe_rate = state.remaining / max(remaining_hours, 0.1)
            
            return {
                "current_rate_per_hour": round(current_rate, 2),
                "safe_rate_per_hour": round(safe_rate, 2),
                "projected_total": round(projected_total, 2),
                "projected_over_budget": projected_total > state.config.limit,
                "hours_remaining": round(remaining_hours, 1),
                "percent_time_elapsed": round((elapsed / total_seconds) * 100, 1),
                "percent_budget_used": round((state.used / state.config.limit) * 100, 1),
            }
    
    def add_listener(self, callback: Callable) -> None:
        """Add event listener for budget events."""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event_type: str, data: Any) -> None:
        """Notify listeners of budget events."""
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception:
                pass
    
    def _calculate_period_bounds(
        self,
        period: BudgetPeriod,
        reference: datetime,
    ) -> tuple[datetime, datetime]:
        """Calculate start and end of a budget period."""
        if period == BudgetPeriod.DAILY:
            start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == BudgetPeriod.WEEKLY:
            start = reference - timedelta(days=reference.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY:
            start = reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        else:  # SEASONAL - approximate as 3 months
            quarter = (reference.month - 1) // 3
            start = reference.replace(month=quarter * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_month = (quarter + 1) * 3 + 1
            if end_month > 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=end_month)
        
        return start, end
    
    def _refresh_period_if_needed(self, state: BudgetState) -> None:
        """Check if budget period has ended and reset if needed."""
        now = datetime.now()
        
        if now >= state.period_end:
            # Period ended - calculate rollover and reset
            rollover = 0.0
            if state.config.rollover and state.remaining > 0:
                max_rollover = state.config.limit * state.config.rollover_cap
                rollover = min(state.remaining, max_rollover)
            
            # Update to new period
            state.period_start, state.period_end = self._calculate_period_bounds(
                state.config.period, now
            )
            state.used = 0.0
            state.remaining = state.config.limit + rollover
            state.rollover_amount = rollover
            state.status = BudgetStatus.NORMAL
            state.alerts_generated = 0
    
    def _has_active_override(self, resource_type: str) -> bool:
        """Check if there's an active override for a resource."""
        expiry = self._overrides.get(resource_type)
        if expiry and expiry > datetime.now():
            return True
        elif expiry:
            del self._overrides[resource_type]
        return False
    
    def _status_worsened(self, old: BudgetStatus, new: BudgetStatus) -> bool:
        """Check if budget status has worsened."""
        severity = {
            BudgetStatus.NORMAL: 0,
            BudgetStatus.WARNING: 1,
            BudgetStatus.CRITICAL: 2,
            BudgetStatus.EXCEEDED: 3,
            BudgetStatus.HARDSTOP: 4,
        }
        return severity.get(new, 0) > severity.get(old, 0)
    
    def _create_alert(
        self,
        resource_type: str,
        period: BudgetPeriod,
        status: BudgetStatus,
        usage: float,
        limit: float,
        source: str,
    ) -> BudgetAlert:
        """Create a budget alert."""
        self._alert_counter += 1
        usage_pct = (usage / limit * 100) if limit > 0 else 100
        
        messages = {
            BudgetStatus.WARNING: f"Budget warning: {usage_pct:.0f}% of {period.value} limit used",
            BudgetStatus.CRITICAL: f"Budget critical: {usage_pct:.0f}% of {period.value} limit used",
            BudgetStatus.EXCEEDED: f"Budget exceeded: {usage_pct:.0f}% of {period.value} limit used",
            BudgetStatus.HARDSTOP: f"Hard stop: {period.value} budget exhausted",
        }
        
        alert = BudgetAlert(
            alert_id=f"budget-{self.farm_id}-{self._alert_counter:06d}",
            resource_type=resource_type,
            period=period,
            status=status,
            current_usage=usage,
            budget_limit=limit,
            usage_percent=usage_pct,
            message=messages.get(status, f"Budget status: {status.value}"),
            metadata={"source": source},
        )
        
        self._alerts.append(alert)
        return alert
    
    def _state_to_dict(self, state: BudgetState) -> Dict[str, Any]:
        """Convert BudgetState to dictionary."""
        usage_pct = (state.used / state.config.limit * 100) if state.config.limit > 0 else 0
        
        return {
            "limit": state.config.limit,
            "used": state.used,
            "remaining": state.remaining,
            "rollover": state.rollover_amount,
            "status": state.status.value,
            "usage_percent": round(usage_pct, 1),
            "period_start": state.period_start.isoformat(),
            "period_end": state.period_end.isoformat(),
            "warning_threshold": state.config.warning_threshold,
            "critical_threshold": state.config.critical_threshold,
            "hard_stop": state.config.hard_stop,
        }
