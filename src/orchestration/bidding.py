"""
Agent Bidding Protocol for AgriMesh Autonomous

Agents submit resource bids with justification.
Orchestrator resolves conflicts and allocates resources.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum

from .resource_economy import (
    ResourcePool, ResourceRequest, Allocation, Priority
)


class BidStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIAL = "partial"
    QUEUED = "queued"


@dataclass
class ResourceBid:
    """
    Agent bid for resources with justification and constraints.
    
    Bids are more expressive than raw requests - they include
    reasoning, alternatives, and timing flexibility.
    """
    bid_id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    
    # Resource request
    resource_type: str = ""
    quantity_requested: float = 0.0
    quantity_minimum: float = 0.0  # Minimum acceptable (for partial fulfillment)
    
    # Priority and timing
    priority: Priority = Priority.NORMAL
    needed_by: Optional[datetime] = None
    duration_hours: float = 1.0
    flexible_timing: bool = False  # Can be delayed up to 24h
    
    # Justification
    reason: str = ""
    expected_outcome: str = ""
    risk_if_denied: str = ""
    
    # Alternatives
    alternative_resources: List[str] = field(default_factory=list)
    
    # Status
    status: BidStatus = BidStatus.PENDING
    allocated_quantity: float = 0.0
    response_message: str = ""
    
    # Timestamps
    submitted_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    def to_request(self) -> ResourceRequest:
        """Convert bid to a ResourceRequest for the pool."""
        return ResourceRequest(
            request_id=self.bid_id,
            agent_id=self.agent_id,
            resource_type=self.resource_type,
            quantity=self.quantity_requested,
            priority=self.priority,
            deadline=self.needed_by,
            reason=self.reason,
            can_be_partial=(self.quantity_minimum < self.quantity_requested)
        )


class BiddingEngine:
    """
    Manages resource bidding from multiple agents.
    
    Collects bids during a bidding window, then resolves
    conflicts and allocates resources fairly based on priority.
    """

    def __init__(self, resource_pool: ResourcePool):
        self.pool = resource_pool
        self.current_bids: List[ResourceBid] = []
        self.resolved_bids: List[ResourceBid] = []
        self.bid_counter = 0
        
        # Conflict resolution hooks
        self._on_conflict: Optional[Callable] = None
        self._on_allocation: Optional[Callable] = None

    def submit_bid(self, bid: ResourceBid) -> str:
        """
        Submit a resource bid.
        
        Returns bid_id for tracking.
        """
        self.bid_counter += 1
        bid.bid_id = f"BID-{self.bid_counter:04d}"
        bid.submitted_at = datetime.now()
        bid.status = BidStatus.PENDING
        self.current_bids.append(bid)
        return bid.bid_id

    def get_bid_status(self, bid_id: str) -> Optional[ResourceBid]:
        """Get status of a submitted bid."""
        for bid in self.current_bids + self.resolved_bids:
            if bid.bid_id == bid_id:
                return bid
        return None

    def resolve_bids(self) -> List[ResourceBid]:
        """
        Resolve all pending bids.
        
        Uses priority-based allocation with conflict resolution.
        Returns list of resolved bids with updated status.
        """
        if not self.current_bids:
            return []

        # Sort by priority (highest first), then by submission time
        sorted_bids = sorted(
            self.current_bids,
            key=lambda b: (-b.priority, b.submitted_at)
        )

        resolved = []
        for bid in sorted_bids:
            result = self._resolve_single_bid(bid)
            resolved.append(result)

        self.resolved_bids.extend(resolved)
        self.current_bids = []
        return resolved

    def _resolve_single_bid(self, bid: ResourceBid) -> ResourceBid:
        """Resolve a single bid against current pool state."""
        bid.resolved_at = datetime.now()

        resource = self.pool.resources.get(bid.resource_type)
        if not resource:
            bid.status = BidStatus.REJECTED
            bid.response_message = f"Unknown resource type: {bid.resource_type}"
            return bid

        # Check availability
        if resource.available >= bid.quantity_requested:
            # Full allocation
            request = bid.to_request()
            self.pool.submit_request(request)
            allocations = self.pool.process_requests()
            
            if allocations:
                bid.status = BidStatus.ACCEPTED
                bid.allocated_quantity = bid.quantity_requested
                bid.response_message = "Full allocation granted"
                if self._on_allocation:
                    self._on_allocation(bid, allocations[0])
            else:
                bid.status = BidStatus.REJECTED
                bid.response_message = "Allocation failed unexpectedly"

        elif resource.available >= bid.quantity_minimum:
            # Partial allocation
            partial_qty = resource.available
            request = bid.to_request()
            request.quantity = partial_qty
            self.pool.submit_request(request)
            allocations = self.pool.process_requests()
            
            if allocations:
                bid.status = BidStatus.PARTIAL
                bid.allocated_quantity = partial_qty
                bid.response_message = (
                    f"Partial allocation: {partial_qty:.1f}/{bid.quantity_requested:.1f} "
                    f"{resource.unit}"
                )
            else:
                bid.status = BidStatus.REJECTED
                bid.response_message = "Partial allocation failed"

        elif bid.flexible_timing:
            # Queue for later
            bid.status = BidStatus.QUEUED
            bid.response_message = (
                f"Queued - insufficient {bid.resource_type} "
                f"(available: {resource.available:.1f} {resource.unit})"
            )
            # Keep in pending for next resolution cycle
            self.current_bids.append(bid)

        else:
            # Cannot fulfill
            bid.status = BidStatus.REJECTED
            bid.response_message = (
                f"Insufficient {bid.resource_type}: "
                f"requested {bid.quantity_requested:.1f}, "
                f"available {resource.available:.1f} {resource.unit}"
            )
            
            # Fire conflict callback
            if self._on_conflict:
                self._on_conflict(bid, resource.available)

        return bid

    def get_pending_summary(self) -> Dict:
        """Get summary of pending bids by resource type."""
        summary = {}
        for bid in self.current_bids:
            rt = bid.resource_type
            if rt not in summary:
                summary[rt] = {"count": 0, "total_requested": 0.0}
            summary[rt]["count"] += 1
            summary[rt]["total_requested"] += bid.quantity_requested
        return summary

    def get_resolution_report(self) -> Dict:
        """Generate report of most recent resolution cycle."""
        if not self.resolved_bids:
            return {"message": "No bids resolved yet"}
        
        recent = [b for b in self.resolved_bids[-20:]]  # Last 20 bids
        
        by_status = {}
        for bid in recent:
            status = bid.status.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append({
                "bid_id": bid.bid_id,
                "agent": bid.agent_name,
                "resource": bid.resource_type,
                "requested": bid.quantity_requested,
                "allocated": bid.allocated_quantity,
                "message": bid.response_message
            })

        return {
            "total_resolved": len(recent),
            "by_status": by_status,
            "timestamp": datetime.now().isoformat()
        }

    def register_conflict_handler(self, handler: Callable) -> None:
        """Register callback for resource conflicts."""
        self._on_conflict = handler

    def register_allocation_handler(self, handler: Callable) -> None:
        """Register callback for successful allocations."""
        self._on_allocation = handler


# Convenience helpers for agents

def create_irrigation_bid(
    agent_id: str,
    water_liters: float,
    zone_id: str,
    soil_moisture: float,
    crop_stage: str = "vegetative"
) -> ResourceBid:
    """Create a water bid for irrigation."""
    # Determine priority based on soil moisture
    if soil_moisture < 0.25:
        priority = Priority.URGENT
        risk = "Crop stress imminent, potential yield loss"
    elif soil_moisture < 0.35:
        priority = Priority.HIGH
        risk = "Approaching stress threshold"
    else:
        priority = Priority.NORMAL
        risk = "Routine irrigation"

    return ResourceBid(
        agent_id=agent_id,
        agent_name="Irrigation Agent",
        resource_type="water",
        quantity_requested=water_liters,
        quantity_minimum=water_liters * 0.5,  # Accept 50% minimum
        priority=priority,
        duration_hours=2.0,
        flexible_timing=(soil_moisture > 0.40),
        reason=f"Irrigation for zone {zone_id} ({crop_stage} stage)",
        expected_outcome=f"Restore soil moisture from {soil_moisture:.0%} to optimal",
        risk_if_denied=risk
    )


def create_livestock_bid(
    agent_id: str,
    resource_type: str,
    quantity: float,
    animal_count: int,
    is_welfare_critical: bool = False
) -> ResourceBid:
    """Create a resource bid for livestock operations."""
    priority = Priority.WELFARE if is_welfare_critical else Priority.HIGH
    
    return ResourceBid(
        agent_id=agent_id,
        agent_name="Livestock Agent",
        resource_type=resource_type,
        quantity_requested=quantity,
        quantity_minimum=quantity * 0.8,  # Animals need at least 80%
        priority=priority,
        duration_hours=1.0,
        flexible_timing=False,  # Animals can't wait
        reason=f"Daily {resource_type} for {animal_count} animals",
        expected_outcome="Maintain animal health and productivity",
        risk_if_denied="Animal welfare concern" if is_welfare_critical else "Reduced productivity"
    )
