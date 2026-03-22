"""
Resource Economy Engine for AgriMesh Autonomous

Manages shared farm resources with agent bidding and allocation.
Implements priority-based resource allocation with preemption for critical needs.
Supports hard budget constraints with alerts and automatic throttling.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Dict, List, Optional, Callable, Any
from uuid import uuid4


class Priority(IntEnum):
    """Resource request priorities (higher = more urgent)."""
    LOW = 1
    NORMAL = 3
    HIGH = 5
    URGENT = 7
    WELFARE = 9      # Animal welfare - cannot be deferred
    CRITICAL = 10    # Biosecurity, safety - immediate action required


class AlertLevel(IntEnum):
    """Budget alert severity levels."""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class BudgetAlert:
    """Alert raised when budget thresholds are breached."""
    alert_id: str
    level: AlertLevel
    resource_type: str
    message: str
    threshold_percent: float
    current_percent: float
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


@dataclass
class BudgetConstraint:
    """Hard or soft constraint on resource usage."""
    daily_limit: Optional[float] = None      # Hard cap per day
    weekly_limit: Optional[float] = None     # Hard cap per week
    warning_threshold: float = 0.75          # Alert at 75% usage
    critical_threshold: float = 0.90         # Alert at 90% usage
    hard_stop_threshold: float = 1.0         # Block at 100% (hard constraint)
    allow_welfare_override: bool = True      # Welfare/critical can exceed limits


@dataclass
class Resource:
    """A farm resource with capacity, cost, and budget constraint tracking."""
    name: str
    total: float
    available: float
    unit: str
    cost_per_unit: float = 0.0
    reserved: float = 0.0
    
    # Budget constraint tracking
    constraint: Optional[BudgetConstraint] = None
    daily_consumed: float = 0.0
    weekly_consumed: float = 0.0
    period_start: datetime = field(default_factory=datetime.now)

    @property
    def utilization(self) -> float:
        """Current utilization percentage."""
        if self.total == 0:
            return 0.0
        return (self.total - self.available) / self.total

    @property
    def daily_utilization(self) -> float:
        """Daily budget utilization (0-1+)."""
        if not self.constraint or not self.constraint.daily_limit:
            return 0.0
        return self.daily_consumed / self.constraint.daily_limit

    @property
    def weekly_utilization(self) -> float:
        """Weekly budget utilization (0-1+)."""
        if not self.constraint or not self.constraint.weekly_limit:
            return 0.0
        return self.weekly_consumed / self.constraint.weekly_limit

    def can_allocate(self, quantity: float, priority: Priority = Priority.NORMAL) -> bool:
        """Check if quantity can be allocated within budget constraints."""
        if quantity > self.available:
            return False
        
        if not self.constraint:
            return True
        
        # Check daily limit
        if self.constraint.daily_limit:
            new_daily = self.daily_consumed + quantity
            if new_daily > self.constraint.daily_limit * self.constraint.hard_stop_threshold:
                # Allow welfare/critical to override
                if priority >= Priority.WELFARE and self.constraint.allow_welfare_override:
                    return True
                return False
        
        # Check weekly limit
        if self.constraint.weekly_limit:
            new_weekly = self.weekly_consumed + quantity
            if new_weekly > self.constraint.weekly_limit * self.constraint.hard_stop_threshold:
                if priority >= Priority.WELFARE and self.constraint.allow_welfare_override:
                    return True
                return False
        
        return True

    def allocate(self, quantity: float, priority: Priority = Priority.NORMAL) -> bool:
        """Allocate quantity from available pool with budget tracking."""
        if not self.can_allocate(quantity, priority):
            return False
        self.available -= quantity
        self.daily_consumed += quantity
        self.weekly_consumed += quantity
        return True

    def release(self, quantity: float) -> None:
        """Return quantity to available pool."""
        self.available = min(self.total, self.available + quantity)
    
    def reset_daily(self) -> None:
        """Reset daily consumption counter."""
        self.daily_consumed = 0.0
        self.period_start = datetime.now()
    
    def reset_weekly(self) -> None:
        """Reset weekly consumption counter."""
        self.weekly_consumed = 0.0
        self.daily_consumed = 0.0
        self.period_start = datetime.now()

    def check_thresholds(self) -> List[BudgetAlert]:
        """Check if any budget thresholds are breached."""
        alerts = []
        if not self.constraint:
            return alerts
        
        # Daily threshold checks
        if self.constraint.daily_limit:
            util = self.daily_utilization
            if util >= self.constraint.critical_threshold:
                alerts.append(BudgetAlert(
                    alert_id=f"{self.name}-daily-critical-{str(uuid4())[:6]}",
                    level=AlertLevel.CRITICAL,
                    resource_type=self.name,
                    message=f"Daily {self.name} budget at {util*100:.1f}% - approaching hard limit",
                    threshold_percent=self.constraint.critical_threshold * 100,
                    current_percent=util * 100
                ))
            elif util >= self.constraint.warning_threshold:
                alerts.append(BudgetAlert(
                    alert_id=f"{self.name}-daily-warning-{str(uuid4())[:6]}",
                    level=AlertLevel.WARNING,
                    resource_type=self.name,
                    message=f"Daily {self.name} budget at {util*100:.1f}%",
                    threshold_percent=self.constraint.warning_threshold * 100,
                    current_percent=util * 100
                ))
        
        # Weekly threshold checks
        if self.constraint.weekly_limit:
            util = self.weekly_utilization
            if util >= self.constraint.critical_threshold:
                alerts.append(BudgetAlert(
                    alert_id=f"{self.name}-weekly-critical-{str(uuid4())[:6]}",
                    level=AlertLevel.CRITICAL,
                    resource_type=self.name,
                    message=f"Weekly {self.name} budget at {util*100:.1f}% - approaching hard limit",
                    threshold_percent=self.constraint.critical_threshold * 100,
                    current_percent=util * 100
                ))
            elif util >= self.constraint.warning_threshold:
                alerts.append(BudgetAlert(
                    alert_id=f"{self.name}-weekly-warning-{str(uuid4())[:6]}",
                    level=AlertLevel.WARNING,
                    resource_type=self.name,
                    message=f"Weekly {self.name} budget at {util*100:.1f}%",
                    threshold_percent=self.constraint.warning_threshold * 100,
                    current_percent=util * 100
                ))
        
        return alerts


@dataclass
class ResourceRequest:
    """Agent request for resource allocation."""
    request_id: str = field(default_factory=lambda: str(uuid4())[:8])
    agent_id: str = ""
    resource_type: str = ""
    quantity: float = 0.0
    priority: Priority = Priority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    reason: str = ""
    can_be_partial: bool = False  # Accept partial allocation if full unavailable


@dataclass
class Allocation:
    """Approved resource allocation."""
    allocation_id: str = field(default_factory=lambda: str(uuid4())[:8])
    request: ResourceRequest = field(default_factory=ResourceRequest)
    quantity_allocated: float = 0.0
    status: str = "pending"  # pending, approved, active, completed, rejected, preempted
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResourcePool:
    """
    Shared resource pool for the farm.
    
    Manages water, labour, land, feed, budget, electricity, fertilizer.
    Supports priority-based allocation with preemption and budget constraints.
    """

    def __init__(self, farm_id: str):
        self.farm_id = farm_id
        self.resources: Dict[str, Resource] = {}
        self.pending_requests: List[ResourceRequest] = []
        self.active_allocations: List[Allocation] = []
        self.allocation_history: List[Allocation] = []
        self.alerts: List[BudgetAlert] = []
        self.alert_handlers: List[Callable[[BudgetAlert], None]] = []
        self.consumption_history: List[Dict[str, Any]] = []  # For burn-down tracking
        self._initialize_default_resources()

    def _initialize_default_resources(self) -> None:
        """Initialize standard farm resource pool."""
        self.resources = {
            "water": Resource(
                name="water",
                total=100000.0,  # liters per day
                available=100000.0,
                unit="liters",
                cost_per_unit=0.001  # USD per liter
            ),
            "labour": Resource(
                name="labour",
                total=80.0,  # person-hours per day
                available=80.0,
                unit="person-hours",
                cost_per_unit=2.5  # USD per hour
            ),
            "budget": Resource(
                name="budget",
                total=1000.0,  # daily budget USD
                available=1000.0,
                unit="USD",
                cost_per_unit=1.0
            ),
            "electricity": Resource(
                name="electricity",
                total=500.0,  # kWh per day
                available=500.0,
                unit="kWh",
                cost_per_unit=0.12  # USD per kWh
            ),
            "feed": Resource(
                name="feed",
                total=1000.0,  # kg per day
                available=1000.0,
                unit="kg",
                cost_per_unit=0.30  # USD per kg
            ),
        }

    def set_resource_capacity(
        self,
        resource_type: str,
        total: float,
        available: Optional[float] = None,
        cost_per_unit: Optional[float] = None
    ) -> None:
        """Configure resource capacity and cost."""
        if resource_type in self.resources:
            r = self.resources[resource_type]
            r.total = total
            if available is not None:
                r.available = min(available, total)
            if cost_per_unit is not None:
                r.cost_per_unit = cost_per_unit
        else:
            self.resources[resource_type] = Resource(
                name=resource_type,
                total=total,
                available=available if available is not None else total,
                unit="units",
                cost_per_unit=cost_per_unit if cost_per_unit is not None else 0.0
            )

    def submit_request(self, request: ResourceRequest) -> str:
        """
        Submit a resource request to the pool.
        
        Returns request_id for tracking.
        """
        self.pending_requests.append(request)
        # Sort by priority (highest first), then by deadline
        self.pending_requests.sort(
            key=lambda r: (-r.priority, r.deadline or datetime.max)
        )
        return request.request_id

    def process_requests(self) -> List[Allocation]:
        """
        Process all pending requests in priority order.
        
        Returns list of new allocations.
        """
        new_allocations = []
        remaining_requests = []

        for request in self.pending_requests:
            allocation = self._try_allocate(request)
            if allocation:
                new_allocations.append(allocation)
            elif request.priority >= Priority.URGENT:
                # Try preemption for urgent requests
                allocation = self._try_preempt_and_allocate(request)
                if allocation:
                    new_allocations.append(allocation)
                else:
                    remaining_requests.append(request)
            else:
                remaining_requests.append(request)

        self.pending_requests = remaining_requests
        return new_allocations

    def _try_allocate(self, request: ResourceRequest) -> Optional[Allocation]:
        """Attempt to allocate requested resource with budget constraint checks."""
        resource = self.resources.get(request.resource_type)
        if not resource:
            return None

        # Check budget constraints
        if resource.can_allocate(request.quantity, request.priority):
            resource.allocate(request.quantity, request.priority)
            allocation = Allocation(
                request=request,
                quantity_allocated=request.quantity,
                status="approved",
                approved_at=datetime.now()
            )
            self.active_allocations.append(allocation)
            
            # Check and raise alerts after allocation
            alerts = resource.check_thresholds()
            for alert in alerts:
                self.alerts.append(alert)
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception:
                        pass
            
            return allocation

        # Try partial allocation if allowed and within budget
        if request.can_be_partial and resource.available > 0:
            # Calculate max allocatable within budget
            max_qty = resource.available
            if resource.constraint and resource.constraint.daily_limit:
                budget_remaining = resource.constraint.daily_limit - resource.daily_consumed
                max_qty = min(max_qty, budget_remaining)
            
            if max_qty > 0:
                resource.allocate(max_qty, request.priority)
                allocation = Allocation(
                    request=request,
                    quantity_allocated=max_qty,
                    status="approved",
                    approved_at=datetime.now()
                )
                self.active_allocations.append(allocation)
                
                # Check alerts
                alerts = resource.check_thresholds()
                for alert in alerts:
                    self.alerts.append(alert)
                    for handler in self.alert_handlers:
                        try:
                            handler(alert)
                        except Exception:
                            pass
                
                return allocation

        return None

    def _try_preempt_and_allocate(self, request: ResourceRequest) -> Optional[Allocation]:
        """
        Attempt to preempt lower-priority allocations for urgent requests.
        
        Only preempts allocations with priority < request.priority.
        """
        resource = self.resources.get(request.resource_type)
        if not resource:
            return None

        needed = request.quantity - resource.available
        if needed <= 0:
            return self._try_allocate(request)

        # Find preemptable allocations (lower priority, same resource)
        preemptable = [
            a for a in self.active_allocations
            if (a.request.resource_type == request.resource_type and
                a.request.priority < request.priority and
                a.status == "approved")
        ]
        # Sort by priority ascending (lowest first to preempt)
        preemptable.sort(key=lambda a: a.request.priority)

        freed = 0.0
        to_preempt = []
        for alloc in preemptable:
            to_preempt.append(alloc)
            freed += alloc.quantity_allocated
            if freed >= needed:
                break

        if freed >= needed:
            # Execute preemption
            for alloc in to_preempt:
                self._release_allocation(alloc, preempted=True)
            return self._try_allocate(request)

        return None

    def _release_allocation(self, allocation: Allocation, preempted: bool = False) -> None:
        """Release an allocation and return resources to pool."""
        resource = self.resources.get(allocation.request.resource_type)
        if resource:
            resource.release(allocation.quantity_allocated)
        
        allocation.status = "preempted" if preempted else "completed"
        allocation.completed_at = datetime.now()
        
        if allocation in self.active_allocations:
            self.active_allocations.remove(allocation)
        self.allocation_history.append(allocation)

    def complete_allocation(self, allocation_id: str) -> bool:
        """Mark an allocation as completed and release resources."""
        for alloc in self.active_allocations:
            if alloc.allocation_id == allocation_id:
                self._release_allocation(alloc, preempted=False)
                return True
        return False

    def set_budget_constraint(
        self,
        resource_type: str,
        daily_limit: Optional[float] = None,
        weekly_limit: Optional[float] = None,
        warning_threshold: float = 0.75,
        critical_threshold: float = 0.90,
        hard_stop: bool = True
    ) -> None:
        """Set budget constraints on a resource."""
        resource = self.resources.get(resource_type)
        if not resource:
            return
        
        resource.constraint = BudgetConstraint(
            daily_limit=daily_limit,
            weekly_limit=weekly_limit,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            hard_stop_threshold=1.0 if hard_stop else 1.5,  # Soft allows 50% overage
            allow_welfare_override=True
        )

    def register_alert_handler(self, handler: Callable[[BudgetAlert], None]) -> None:
        """Register a callback for budget alerts."""
        self.alert_handlers.append(handler)

    def check_all_thresholds(self) -> List[BudgetAlert]:
        """Check all resources for threshold breaches."""
        new_alerts = []
        for resource in self.resources.values():
            alerts = resource.check_thresholds()
            for alert in alerts:
                new_alerts.append(alert)
                self.alerts.append(alert)
                # Fire handlers
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception:
                        pass  # Don't let handler errors break the pool
        return new_alerts

    def reset_daily_budgets(self) -> None:
        """Reset all daily consumption counters."""
        for resource in self.resources.values():
            resource.reset_daily()

    def reset_weekly_budgets(self) -> None:
        """Reset all weekly consumption counters."""
        for resource in self.resources.values():
            resource.reset_weekly()

    def record_consumption_snapshot(self) -> Dict:
        """Record current consumption state for burn-down tracking."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "resources": {}
        }
        for name, r in self.resources.items():
            snapshot["resources"][name] = {
                "daily_consumed": r.daily_consumed,
                "weekly_consumed": r.weekly_consumed,
                "daily_limit": r.constraint.daily_limit if r.constraint else None,
                "weekly_limit": r.constraint.weekly_limit if r.constraint else None,
                "daily_remaining": (
                    r.constraint.daily_limit - r.daily_consumed 
                    if r.constraint and r.constraint.daily_limit else None
                ),
                "utilization": r.utilization,
                "daily_utilization": r.daily_utilization,
                "weekly_utilization": r.weekly_utilization
            }
        self.consumption_history.append(snapshot)
        return snapshot

    def get_burn_down_data(self, hours: int = 24) -> List[Dict]:
        """Get consumption history for burn-down charts."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            s for s in self.consumption_history
            if datetime.fromisoformat(s["timestamp"]) >= cutoff
        ]

    def get_status(self) -> Dict:
        """Get current resource pool status with budget info."""
        return {
            "farm_id": self.farm_id,
            "timestamp": datetime.now().isoformat(),
            "resources": {
                name: {
                    "available": r.available,
                    "total": r.total,
                    "utilization": f"{r.utilization * 100:.1f}%",
                    "unit": r.unit,
                    "cost_per_unit": r.cost_per_unit,
                    "daily_consumed": r.daily_consumed,
                    "weekly_consumed": r.weekly_consumed,
                    "daily_limit": r.constraint.daily_limit if r.constraint else None,
                    "weekly_limit": r.constraint.weekly_limit if r.constraint else None,
                    "daily_utilization": f"{r.daily_utilization * 100:.1f}%" if r.constraint else "N/A",
                    "budget_status": self._get_budget_status(r)
                }
                for name, r in self.resources.items()
            },
            "pending_requests": len(self.pending_requests),
            "active_allocations": len(self.active_allocations),
            "budget_spent": self._calculate_budget_spent(),
            "active_alerts": [a for a in self.alerts if not a.acknowledged][-10:]
        }

    def _get_budget_status(self, resource: Resource) -> str:
        """Get human-readable budget status for a resource."""
        if not resource.constraint:
            return "unconstrained"
        
        util = resource.daily_utilization
        if util >= resource.constraint.hard_stop_threshold:
            return "blocked"
        elif util >= resource.constraint.critical_threshold:
            return "critical"
        elif util >= resource.constraint.warning_threshold:
            return "warning"
        return "ok"

    def _calculate_budget_spent(self) -> float:
        """Calculate total budget spent on active allocations."""
        total = 0.0
        for alloc in self.active_allocations:
            resource = self.resources.get(alloc.request.resource_type)
            if resource:
                total += alloc.quantity_allocated * resource.cost_per_unit
        return total

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a budget alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_budget_summary(self) -> Dict:
        """Get summary of all budget constraints and their status."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "resources": {},
            "alerts_active": len([a for a in self.alerts if not a.acknowledged]),
            "overall_status": "ok"
        }
        
        worst_status = "ok"
        status_order = {"ok": 0, "warning": 1, "critical": 2, "blocked": 3}
        
        for name, r in self.resources.items():
            status = self._get_budget_status(r)
            if status_order.get(status, 0) > status_order.get(worst_status, 0):
                worst_status = status
            
            if r.constraint:
                summary["resources"][name] = {
                    "status": status,
                    "daily": {
                        "consumed": r.daily_consumed,
                        "limit": r.constraint.daily_limit,
                        "remaining": (
                            r.constraint.daily_limit - r.daily_consumed
                            if r.constraint.daily_limit else None
                        ),
                        "percent": r.daily_utilization * 100
                    },
                    "weekly": {
                        "consumed": r.weekly_consumed,
                        "limit": r.constraint.weekly_limit,
                        "remaining": (
                            r.constraint.weekly_limit - r.weekly_consumed
                            if r.constraint.weekly_limit else None
                        ),
                        "percent": r.weekly_utilization * 100
                    }
                }
        
        summary["overall_status"] = worst_status
        return summary


# Convenience factory
def create_resource_pool(
    farm_id: str,
    water_capacity: float = 100000.0,
    labour_hours: float = 80.0,
    daily_budget: float = 1000.0,
    with_constraints: bool = False
) -> ResourcePool:
    """Create a resource pool with custom capacities and optional budget constraints."""
    pool = ResourcePool(farm_id)
    pool.set_resource_capacity("water", water_capacity)
    pool.set_resource_capacity("labour", labour_hours)
    pool.set_resource_capacity("budget", daily_budget)
    
    if with_constraints:
        # Set default budget constraints
        pool.set_budget_constraint(
            "water",
            daily_limit=water_capacity,
            weekly_limit=water_capacity * 7,
            warning_threshold=0.75,
            critical_threshold=0.90
        )
        pool.set_budget_constraint(
            "labour",
            daily_limit=labour_hours,
            weekly_limit=labour_hours * 6,  # 6-day work week
            warning_threshold=0.80,
            critical_threshold=0.95
        )
        pool.set_budget_constraint(
            "budget",
            daily_limit=daily_budget,
            weekly_limit=daily_budget * 7,
            warning_threshold=0.70,
            critical_threshold=0.85,
            hard_stop=True
        )
    
    return pool


def create_constrained_pool(
    farm_id: str,
    daily_water_liters: float = 50000.0,
    daily_labour_hours: float = 40.0,
    daily_budget_usd: float = 500.0,
    weekly_budget_usd: float = 3000.0
) -> ResourcePool:
    """Create a resource pool with strict budget constraints for production use."""
    pool = ResourcePool(farm_id)
    
    # Water - with daily and weekly limits
    pool.set_resource_capacity("water", daily_water_liters * 1.2)  # 20% buffer in total capacity
    pool.set_budget_constraint(
        "water",
        daily_limit=daily_water_liters,
        weekly_limit=daily_water_liters * 7,
        warning_threshold=0.75,
        critical_threshold=0.90,
        hard_stop=True
    )
    
    # Labour - with daily and weekly limits
    pool.set_resource_capacity("labour", daily_labour_hours * 1.5)  # Allow overtime in emergencies
    pool.set_budget_constraint(
        "labour",
        daily_limit=daily_labour_hours,
        weekly_limit=daily_labour_hours * 6,  # 6-day work week
        warning_threshold=0.80,
        critical_threshold=0.95,
        hard_stop=False  # Soft limit - allow welfare overrides
    )
    
    # Budget - strict USD limits
    pool.set_resource_capacity("budget", weekly_budget_usd)
    pool.set_budget_constraint(
        "budget",
        daily_limit=daily_budget_usd,
        weekly_limit=weekly_budget_usd,
        warning_threshold=0.70,
        critical_threshold=0.85,
        hard_stop=True
    )
    
    # Feed - with weekly budget
    pool.set_resource_capacity("feed", 2000.0)  # kg per day capacity
    pool.set_budget_constraint(
        "feed",
        daily_limit=1500.0,  # kg
        weekly_limit=9000.0,  # kg
        warning_threshold=0.80,
        critical_threshold=0.95,
        hard_stop=False  # Never starve animals
    )
    
    # Electricity
    pool.set_resource_capacity("electricity", 600.0)  # kWh/day capacity
    pool.set_budget_constraint(
        "electricity",
        daily_limit=500.0,
        weekly_limit=3000.0,
        warning_threshold=0.75,
        critical_threshold=0.90,
        hard_stop=False
    )
    
    return pool
