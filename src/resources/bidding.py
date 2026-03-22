"""
Agent Bidding Protocol - Structured resource requests with justification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import defaultdict
import heapq
import threading

from src.resources.pool import ResourcePool, ResourceType, AllocationPriority, ResourceAllocation


class BidStatus(str, Enum):
    """Status of a resource bid."""
    PENDING = "pending"
    APPROVED = "approved"
    PARTIAL = "partial"
    REJECTED = "rejected"
    QUEUED = "queued"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ResourceBid:
    """
    A structured request for resources from an agent.
    
    Includes justification and constraints for allocation decisions.
    """
    bid_id: str
    agent_id: str
    resource_type: ResourceType
    amount_requested: float
    amount_minimum: float  # Minimum acceptable (for partial fulfillment)
    priority: AllocationPriority
    justification: str
    deadline: Optional[datetime] = None  # When the resource is needed by
    created_at: datetime = field(default_factory=datetime.now)
    status: BidStatus = BidStatus.PENDING
    amount_allocated: float = 0.0
    allocation_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other: "ResourceBid") -> bool:
        """Compare bids for priority queue (higher priority first)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # Earlier deadline wins ties
        if self.deadline and other.deadline:
            return self.deadline < other.deadline
        return self.created_at < other.created_at


@dataclass
class BidResult:
    """Result of processing a resource bid."""
    bid: ResourceBid
    success: bool
    allocation: Optional[ResourceAllocation]
    message: str
    alternatives: List[str] = field(default_factory=list)  # Suggested alternatives


class BiddingEngine:
    """
    Processes resource bids from agents with intelligent allocation.
    
    Features:
    - Priority-based bid processing
    - Partial fulfillment when full request unavailable
    - Queue management for deferred bids
    - Justification logging for audit trail
    - Conflict resolution between competing bids
    """
    
    def __init__(self, resource_pool: ResourcePool):
        self.pool = resource_pool
        self._lock = threading.RLock()
        
        # Bid tracking
        self._bids: Dict[str, ResourceBid] = {}
        self._bid_counter = 0
        
        # Priority queues per resource type
        self._queues: Dict[ResourceType, List[ResourceBid]] = defaultdict(list)
        
        # Bid history for analysis
        self._history: List[ResourceBid] = []
    
    def submit_bid(
        self,
        agent_id: str,
        resource_type: ResourceType,
        amount: float,
        priority: AllocationPriority,
        justification: str,
        minimum_amount: Optional[float] = None,
        deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceBid:
        """
        Submit a resource bid.
        
        Args:
            agent_id: ID of the requesting agent
            resource_type: Type of resource needed
            amount: Requested amount
            priority: Priority level
            justification: Why this resource is needed
            minimum_amount: Minimum acceptable (defaults to 50% of amount)
            deadline: When resource is needed by
            metadata: Additional context
            
        Returns:
            The created bid
        """
        with self._lock:
            self._bid_counter += 1
            bid_id = f"bid-{self.pool.farm_id}-{self._bid_counter:06d}"
            
            bid = ResourceBid(
                bid_id=bid_id,
                agent_id=agent_id,
                resource_type=resource_type,
                amount_requested=amount,
                amount_minimum=minimum_amount if minimum_amount is not None else amount * 0.5,
                priority=priority,
                justification=justification,
                deadline=deadline,
                metadata=metadata or {},
            )
            
            self._bids[bid_id] = bid
            return bid
    
    def process_bid(self, bid: ResourceBid) -> BidResult:
        """
        Process a single bid immediately.
        
        Returns result with allocation or rejection reason.
        """
        with self._lock:
            if bid.status != BidStatus.PENDING:
                return BidResult(
                    bid=bid,
                    success=False,
                    allocation=None,
                    message=f"Bid already processed: {bid.status.value}",
                )
            
            # Try full allocation
            success, allocation, message = self.pool.request_allocation(
                resource_type=bid.resource_type,
                amount=bid.amount_requested,
                priority=bid.priority,
                agent_id=bid.agent_id,
                purpose=bid.justification,
                preemptible=bid.priority.value < AllocationPriority.CRITICAL.value,
                metadata={
                    "bid_id": bid.bid_id,
                    **bid.metadata,
                },
            )
            
            if success and allocation:
                bid.status = BidStatus.APPROVED
                bid.amount_allocated = allocation.amount
                bid.allocation_id = allocation.allocation_id
                self._history.append(bid)
                
                return BidResult(
                    bid=bid,
                    success=True,
                    allocation=allocation,
                    message=message,
                )
            
            # Try partial allocation if minimum acceptable
            pool_state = self.pool.get_pool_state(bid.resource_type)
            if pool_state and pool_state.available >= bid.amount_minimum:
                partial_success, partial_alloc, partial_msg = self.pool.request_allocation(
                    resource_type=bid.resource_type,
                    amount=pool_state.available,  # Take what's available
                    priority=bid.priority,
                    agent_id=bid.agent_id,
                    purpose=f"{bid.justification} (partial)",
                    preemptible=bid.priority.value < AllocationPriority.CRITICAL.value,
                    metadata={
                        "bid_id": bid.bid_id,
                        "partial": True,
                        **bid.metadata,
                    },
                )
                
                if partial_success and partial_alloc:
                    bid.status = BidStatus.PARTIAL
                    bid.amount_allocated = partial_alloc.amount
                    bid.allocation_id = partial_alloc.allocation_id
                    self._history.append(bid)
                    
                    deficit = bid.amount_requested - partial_alloc.amount
                    return BidResult(
                        bid=bid,
                        success=True,
                        allocation=partial_alloc,
                        message=f"Partial fulfillment: {partial_alloc.amount:.1f}/{bid.amount_requested:.1f}. Deficit: {deficit:.1f}",
                        alternatives=[
                            f"Request remaining {deficit:.1f} later",
                            "Adjust operations to use partial amount",
                        ],
                    )
            
            # Cannot fulfill - queue or reject
            if bid.deadline and bid.deadline > datetime.now():
                # Queue for later processing
                bid.status = BidStatus.QUEUED
                heapq.heappush(self._queues[bid.resource_type], bid)
                
                return BidResult(
                    bid=bid,
                    success=False,
                    allocation=None,
                    message=f"Queued for later processing. Position: {len(self._queues[bid.resource_type])}",
                    alternatives=[
                        "Wait for resources to become available",
                        "Reduce requested amount",
                        "Lower priority if not urgent",
                    ],
                )
            
            # Reject
            bid.status = BidStatus.REJECTED
            bid.rejection_reason = message
            self._history.append(bid)
            
            return BidResult(
                bid=bid,
                success=False,
                allocation=None,
                message=message,
                alternatives=self._generate_alternatives(bid, pool_state),
            )
    
    def process_queue(self, resource_type: ResourceType) -> List[BidResult]:
        """
        Process queued bids for a resource type.
        
        Called when resources become available.
        """
        results = []
        with self._lock:
            queue = self._queues.get(resource_type, [])
            processed = []
            
            while queue:
                bid = heapq.heappop(queue)
                
                # Check if expired
                if bid.deadline and bid.deadline < datetime.now():
                    bid.status = BidStatus.EXPIRED
                    bid.rejection_reason = "Deadline passed"
                    self._history.append(bid)
                    results.append(BidResult(
                        bid=bid,
                        success=False,
                        allocation=None,
                        message="Bid expired",
                    ))
                    continue
                
                # Try to process
                bid.status = BidStatus.PENDING  # Reset for reprocessing
                result = self.process_bid(bid)
                results.append(result)
                
                # If still couldn't allocate, re-queue
                if not result.success and bid.status == BidStatus.QUEUED:
                    processed.append(bid)
                
                # Stop if no more resources available
                pool_state = self.pool.get_pool_state(resource_type)
                if not pool_state or pool_state.available <= 0:
                    break
            
            # Re-add unprocessed bids
            for bid in processed:
                heapq.heappush(queue, bid)
            
            self._queues[resource_type] = queue
        
        return results
    
    def cancel_bid(self, bid_id: str) -> bool:
        """Cancel a pending or queued bid."""
        with self._lock:
            bid = self._bids.get(bid_id)
            if not bid:
                return False
            
            if bid.status in [BidStatus.PENDING, BidStatus.QUEUED]:
                bid.status = BidStatus.CANCELLED
                
                # Remove from queue if present
                queue = self._queues.get(bid.resource_type, [])
                self._queues[bid.resource_type] = [b for b in queue if b.bid_id != bid_id]
                heapq.heapify(self._queues[bid.resource_type])
                
                return True
            
            return False
    
    def get_bid(self, bid_id: str) -> Optional[ResourceBid]:
        """Get bid by ID."""
        return self._bids.get(bid_id)
    
    def get_agent_bids(
        self,
        agent_id: str,
        status: Optional[BidStatus] = None,
    ) -> List[ResourceBid]:
        """Get all bids from an agent."""
        with self._lock:
            bids = [b for b in self._bids.values() if b.agent_id == agent_id]
            if status:
                bids = [b for b in bids if b.status == status]
            return bids
    
    def get_queue_depth(self, resource_type: ResourceType) -> int:
        """Get number of bids waiting in queue."""
        return len(self._queues.get(resource_type, []))
    
    def get_bid_history(
        self,
        limit: int = 100,
        agent_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> List[ResourceBid]:
        """Get historical bids with optional filters."""
        with self._lock:
            history = list(self._history)
            
            if agent_id:
                history = [b for b in history if b.agent_id == agent_id]
            
            if resource_type:
                history = [b for b in history if b.resource_type == resource_type]
            
            return history[-limit:]
    
    def _generate_alternatives(
        self,
        bid: ResourceBid,
        pool_state: Optional[Any],
    ) -> List[str]:
        """Generate alternative suggestions for rejected bids."""
        alternatives = []
        
        if pool_state:
            if pool_state.available > 0:
                alternatives.append(
                    f"Reduce request to {pool_state.available:.1f} (currently available)"
                )
            
            remaining_daily = pool_state.daily_limit - pool_state.daily_used
            if remaining_daily > 0 and remaining_daily < bid.amount_requested:
                alternatives.append(
                    f"Split request: {remaining_daily:.1f} today, rest tomorrow"
                )
            
            if pool_state.daily_used >= pool_state.daily_limit:
                alternatives.append("Daily limit reached - wait until tomorrow")
        
        if bid.priority.value < AllocationPriority.CRITICAL.value:
            alternatives.append("Increase priority if task is urgent")
        
        alternatives.append("Coordinate with other agents to share resources")
        
        return alternatives[:4]  # Limit to 4 suggestions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bidding statistics."""
        with self._lock:
            total = len(self._history)
            approved = sum(1 for b in self._history if b.status == BidStatus.APPROVED)
            partial = sum(1 for b in self._history if b.status == BidStatus.PARTIAL)
            rejected = sum(1 for b in self._history if b.status == BidStatus.REJECTED)
            
            return {
                "total_bids": total,
                "approved": approved,
                "partial": partial,
                "rejected": rejected,
                "approval_rate": (approved + partial) / total if total > 0 else 0,
                "queued_by_type": {
                    rt.value: len(q) for rt, q in self._queues.items() if q
                },
                "pending_bids": sum(1 for b in self._bids.values() if b.status == BidStatus.PENDING),
            }
