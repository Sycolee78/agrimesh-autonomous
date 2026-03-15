"""
Resource Economy Engine for AgriMesh Autonomous

Manages shared farm resources with agent bidding and allocation.
Implements priority-based resource allocation with preemption for critical needs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Dict, List, Optional
from uuid import uuid4


class Priority(IntEnum):
    """Resource request priorities (higher = more urgent)."""
    LOW = 1
    NORMAL = 3
    HIGH = 5
    URGENT = 7
    WELFARE = 9      # Animal welfare - cannot be deferred
    CRITICAL = 10    # Biosecurity, safety - immediate action required


@dataclass
class Resource:
    """A farm resource with capacity and cost tracking."""
    name: str
    total: float
    available: float
    unit: str
    cost_per_unit: float = 0.0
    reserved: float = 0.0

    @property
    def utilization(self) -> float:
        """Current utilization percentage."""
        if self.total == 0:
            return 0.0
        return (self.total - self.available) / self.total

    def can_allocate(self, quantity: float) -> bool:
        """Check if quantity can be allocated."""
        return quantity <= self.available

    def allocate(self, quantity: float) -> bool:
        """Allocate quantity from available pool."""
        if not self.can_allocate(quantity):
            return False
        self.available -= quantity
        return True

    def release(self, quantity: float) -> None:
        """Return quantity to available pool."""
        self.available = min(self.total, self.available + quantity)


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
    Supports priority-based allocation with preemption.
    """

    def __init__(self, farm_id: str):
        self.farm_id = farm_id
        self.resources: Dict[str, Resource] = {}
        self.pending_requests: List[ResourceRequest] = []
        self.active_allocations: List[Allocation] = []
        self.allocation_history: List[Allocation] = []
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
        """Attempt to allocate requested resource."""
        resource = self.resources.get(request.resource_type)
        if not resource:
            return None

        if resource.can_allocate(request.quantity):
            resource.allocate(request.quantity)
            allocation = Allocation(
                request=request,
                quantity_allocated=request.quantity,
                status="approved",
                approved_at=datetime.now()
            )
            self.active_allocations.append(allocation)
            return allocation

        # Try partial allocation if allowed
        if request.can_be_partial and resource.available > 0:
            partial = resource.available
            resource.allocate(partial)
            allocation = Allocation(
                request=request,
                quantity_allocated=partial,
                status="approved",
                approved_at=datetime.now()
            )
            self.active_allocations.append(allocation)
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

    def get_status(self) -> Dict:
        """Get current resource pool status."""
        return {
            "farm_id": self.farm_id,
            "timestamp": datetime.now().isoformat(),
            "resources": {
                name: {
                    "available": r.available,
                    "total": r.total,
                    "utilization": f"{r.utilization * 100:.1f}%",
                    "unit": r.unit,
                    "cost_per_unit": r.cost_per_unit
                }
                for name, r in self.resources.items()
            },
            "pending_requests": len(self.pending_requests),
            "active_allocations": len(self.active_allocations),
            "budget_spent": self._calculate_budget_spent()
        }

    def _calculate_budget_spent(self) -> float:
        """Calculate total budget spent on active allocations."""
        total = 0.0
        for alloc in self.active_allocations:
            resource = self.resources.get(alloc.request.resource_type)
            if resource:
                total += alloc.quantity_allocated * resource.cost_per_unit
        return total


# Convenience factory
def create_resource_pool(
    farm_id: str,
    water_capacity: float = 100000.0,
    labour_hours: float = 80.0,
    daily_budget: float = 1000.0
) -> ResourcePool:
    """Create a resource pool with custom capacities."""
    pool = ResourcePool(farm_id)
    pool.set_resource_capacity("water", water_capacity)
    pool.set_resource_capacity("labour", labour_hours)
    pool.set_resource_capacity("budget", daily_budget)
    return pool
