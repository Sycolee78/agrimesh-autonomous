"""
Resource Pool - Priority-based resource allocation with preemption support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict
import threading


class ResourceType(str, Enum):
    """Types of resources managed by the farm."""
    WATER = "water"           # Liters
    ELECTRICITY = "electricity"  # kWh
    LABOR = "labor"           # Hours
    FUEL = "fuel"             # Liters
    FEED = "feed"             # Kg
    FERTILIZER = "fertilizer" # Kg
    PESTICIDE = "pesticide"   # Liters


class AllocationPriority(int, Enum):
    """Priority levels for resource allocation."""
    CRITICAL = 100    # Life/safety (livestock water, emergency)
    HIGH = 75         # Time-sensitive (irrigation at optimal window)
    NORMAL = 50       # Standard operations
    LOW = 25          # Deferrable tasks
    BACKGROUND = 10   # Can be preempted anytime


@dataclass
class ResourceAllocation:
    """Record of a resource allocation."""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    priority: AllocationPriority
    agent_id: str
    purpose: str
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    preemptible: bool = True
    actual_used: float = 0.0
    status: str = "active"  # active, completed, preempted, expired
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoolState:
    """Current state of a resource pool."""
    resource_type: ResourceType
    total_capacity: float
    available: float
    reserved: float
    allocated: float
    daily_limit: float
    daily_used: float
    active_allocations: List[str] = field(default_factory=list)


class ResourcePool:
    """
    Manages a pool of farm resources with priority-based allocation.
    
    Features:
    - Priority-based allocation (higher priority gets resources first)
    - Preemption (critical tasks can reclaim from lower priority)
    - Reservation system for scheduled tasks
    - Daily limits with rollover tracking
    - Thread-safe operations
    """
    
    def __init__(self, farm_id: str):
        self.farm_id = farm_id
        self._lock = threading.RLock()
        
        # Resource pools: type -> PoolState
        self._pools: Dict[ResourceType, PoolState] = {}
        
        # Active allocations: allocation_id -> ResourceAllocation
        self._allocations: Dict[str, ResourceAllocation] = {}
        
        # Allocation counter for IDs
        self._allocation_counter = 0
        
        # Event listeners
        self._listeners: List[callable] = []
    
    def initialize_pool(
        self,
        resource_type: ResourceType,
        total_capacity: float,
        daily_limit: float,
        initial_available: Optional[float] = None,
    ) -> None:
        """Initialize a resource pool."""
        with self._lock:
            self._pools[resource_type] = PoolState(
                resource_type=resource_type,
                total_capacity=total_capacity,
                available=initial_available if initial_available is not None else total_capacity,
                reserved=0.0,
                allocated=0.0,
                daily_limit=daily_limit,
                daily_used=0.0,
            )
    
    def get_pool_state(self, resource_type: ResourceType) -> Optional[PoolState]:
        """Get current state of a resource pool."""
        with self._lock:
            return self._pools.get(resource_type)
    
    def get_all_pools(self) -> Dict[ResourceType, PoolState]:
        """Get state of all resource pools."""
        with self._lock:
            return dict(self._pools)
    
    def request_allocation(
        self,
        resource_type: ResourceType,
        amount: float,
        priority: AllocationPriority,
        agent_id: str,
        purpose: str,
        preemptible: bool = True,
        duration_minutes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Optional[ResourceAllocation], str]:
        """
        Request resource allocation.
        
        Returns:
            (success, allocation, message)
        """
        with self._lock:
            pool = self._pools.get(resource_type)
            if not pool:
                return False, None, f"Resource pool {resource_type.value} not initialized"
            
            # Check daily limit
            if pool.daily_used + amount > pool.daily_limit:
                remaining = pool.daily_limit - pool.daily_used
                return False, None, f"Daily limit exceeded. Available: {remaining:.1f}"
            
            # Check availability
            if pool.available >= amount:
                # Direct allocation
                allocation = self._create_allocation(
                    resource_type, amount, priority, agent_id, purpose,
                    preemptible, duration_minutes, metadata
                )
                pool.available -= amount
                pool.allocated += amount
                pool.daily_used += amount
                pool.active_allocations.append(allocation.allocation_id)
                
                self._notify_listeners("allocated", allocation)
                return True, allocation, "Allocated successfully"
            
            # Try preemption if high priority
            if priority.value >= AllocationPriority.HIGH.value:
                preempted_amount = self._try_preemption(
                    resource_type, amount - pool.available, priority
                )
                
                if pool.available + preempted_amount >= amount:
                    allocation = self._create_allocation(
                        resource_type, amount, priority, agent_id, purpose,
                        preemptible, duration_minutes, metadata
                    )
                    pool.available -= amount
                    pool.allocated += amount
                    pool.daily_used += amount
                    pool.active_allocations.append(allocation.allocation_id)
                    
                    self._notify_listeners("allocated_with_preemption", allocation)
                    return True, allocation, f"Allocated with preemption ({preempted_amount:.1f} reclaimed)"
            
            # Partial allocation option
            if pool.available > 0:
                partial_amount = pool.available
                allocation = self._create_allocation(
                    resource_type, partial_amount, priority, agent_id, 
                    f"{purpose} (partial)", preemptible, duration_minutes, metadata
                )
                pool.available = 0
                pool.allocated += partial_amount
                pool.daily_used += partial_amount
                pool.active_allocations.append(allocation.allocation_id)
                
                self._notify_listeners("partial_allocation", allocation)
                return True, allocation, f"Partial allocation: {partial_amount:.1f}/{amount:.1f}"
            
            return False, None, f"Insufficient resources. Requested: {amount:.1f}, Available: {pool.available:.1f}"
    
    def release_allocation(
        self,
        allocation_id: str,
        actual_used: Optional[float] = None,
    ) -> bool:
        """Release a resource allocation, returning unused resources to pool."""
        with self._lock:
            allocation = self._allocations.get(allocation_id)
            if not allocation or allocation.status != "active":
                return False
            
            pool = self._pools.get(allocation.resource_type)
            if not pool:
                return False
            
            # Calculate unused amount
            used = actual_used if actual_used is not None else allocation.amount
            unused = allocation.amount - used
            
            allocation.actual_used = used
            allocation.status = "completed"
            
            # Return unused to pool
            pool.available += unused
            pool.allocated -= allocation.amount
            
            if allocation_id in pool.active_allocations:
                pool.active_allocations.remove(allocation_id)
            
            self._notify_listeners("released", allocation)
            return True
    
    def _create_allocation(
        self,
        resource_type: ResourceType,
        amount: float,
        priority: AllocationPriority,
        agent_id: str,
        purpose: str,
        preemptible: bool,
        duration_minutes: Optional[int],
        metadata: Optional[Dict[str, Any]],
    ) -> ResourceAllocation:
        """Create a new allocation record."""
        self._allocation_counter += 1
        allocation_id = f"{self.farm_id}-{resource_type.value}-{self._allocation_counter:06d}"
        
        now = datetime.now()
        expires_at = None
        if duration_minutes:
            from datetime import timedelta
            expires_at = now + timedelta(minutes=duration_minutes)
        
        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            agent_id=agent_id,
            purpose=purpose,
            allocated_at=now,
            expires_at=expires_at,
            preemptible=preemptible,
            metadata=metadata or {},
        )
        
        self._allocations[allocation_id] = allocation
        return allocation
    
    def _try_preemption(
        self,
        resource_type: ResourceType,
        needed: float,
        requesting_priority: AllocationPriority,
    ) -> float:
        """
        Try to preempt lower-priority allocations to free up resources.
        Returns the amount freed.
        """
        pool = self._pools.get(resource_type)
        if not pool:
            return 0.0
        
        # Find preemptible allocations with lower priority
        preemptible = [
            self._allocations[aid]
            for aid in pool.active_allocations
            if aid in self._allocations
            and self._allocations[aid].preemptible
            and self._allocations[aid].priority.value < requesting_priority.value
        ]
        
        # Sort by priority (lowest first) then by amount
        preemptible.sort(key=lambda a: (a.priority.value, -a.amount))
        
        freed = 0.0
        for allocation in preemptible:
            if freed >= needed:
                break
            
            # Preempt this allocation
            unused = allocation.amount - allocation.actual_used
            allocation.status = "preempted"
            pool.allocated -= allocation.amount
            pool.available += unused
            freed += unused
            
            if allocation.allocation_id in pool.active_allocations:
                pool.active_allocations.remove(allocation.allocation_id)
            
            self._notify_listeners("preempted", allocation)
        
        return freed
    
    def reset_daily_usage(self) -> None:
        """Reset daily usage counters (call at start of each day)."""
        with self._lock:
            for pool in self._pools.values():
                pool.daily_used = 0.0
    
    def refill_pool(
        self,
        resource_type: ResourceType,
        amount: float,
    ) -> bool:
        """Add resources to pool (e.g., from rain collection, delivery)."""
        with self._lock:
            pool = self._pools.get(resource_type)
            if not pool:
                return False
            
            pool.available = min(pool.total_capacity, pool.available + amount)
            self._notify_listeners("refilled", {
                "resource_type": resource_type,
                "amount": amount,
                "new_available": pool.available,
            })
            return True
    
    def add_listener(self, callback: callable) -> None:
        """Add event listener for pool changes."""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event_type: str, data: Any) -> None:
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                listener(event_type, data)
            except Exception:
                pass  # Don't let listener errors break the pool
    
    def get_allocation(self, allocation_id: str) -> Optional[ResourceAllocation]:
        """Get allocation by ID."""
        with self._lock:
            return self._allocations.get(allocation_id)
    
    def get_active_allocations(
        self,
        resource_type: Optional[ResourceType] = None,
        agent_id: Optional[str] = None,
    ) -> List[ResourceAllocation]:
        """Get active allocations with optional filters."""
        with self._lock:
            allocations = [
                a for a in self._allocations.values()
                if a.status == "active"
            ]
            
            if resource_type:
                allocations = [a for a in allocations if a.resource_type == resource_type]
            
            if agent_id:
                allocations = [a for a in allocations if a.agent_id == agent_id]
            
            return allocations
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of resource usage across all pools."""
        with self._lock:
            summary = {
                "farm_id": self.farm_id,
                "timestamp": datetime.now().isoformat(),
                "pools": {},
            }
            
            for resource_type, pool in self._pools.items():
                summary["pools"][resource_type.value] = {
                    "total_capacity": pool.total_capacity,
                    "available": pool.available,
                    "allocated": pool.allocated,
                    "reserved": pool.reserved,
                    "daily_limit": pool.daily_limit,
                    "daily_used": pool.daily_used,
                    "daily_remaining": pool.daily_limit - pool.daily_used,
                    "utilization_pct": (pool.allocated / pool.total_capacity * 100) if pool.total_capacity > 0 else 0,
                    "active_allocations": len(pool.active_allocations),
                }
            
            return summary
