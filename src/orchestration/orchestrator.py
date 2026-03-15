"""
Farm Management Orchestrator for AgriMesh Autonomous

Coordinates specialized farm agents with:
- Resource economy (bidding for water, labour, budget)
- Safety guardrails
- Decision logging
- Priority-based execution
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Optional
from uuid import uuid4

from src.orchestration.agents import BaseOpsAgent, default_agent_set
from src.orchestration.contracts import (
    AgentContext, AgentOutput, ActionProposal, Priority, RiskLevel
)
from src.orchestration.resource_economy import (
    ResourcePool, ResourceRequest, Priority as ResourcePriority, create_resource_pool
)
from src.orchestration.bidding import (
    BiddingEngine, ResourceBid, BidStatus, create_irrigation_bid, create_livestock_bid
)
from src.common.decision_logger import DecisionLogger, Decision


# Map contract Priority to resource Priority
PRIORITY_MAP = {
    Priority.CRITICAL: ResourcePriority.CRITICAL,
    Priority.HIGH: ResourcePriority.HIGH,
    Priority.NORMAL: ResourcePriority.NORMAL,
}


class FarmManagementOrchestrator:
    """
    Coordinates specialized farm agents with resource economy and safety guardrails.
    
    Key features:
    - Resource pool management (water, labour, budget, etc.)
    - Agent bidding protocol for resource allocation
    - Decision logging for audit and ML training
    - Hard safety guardrails for welfare-critical actions
    """

    def __init__(
        self,
        agents: Optional[List[BaseOpsAgent]] = None,
        farm_id: str = "default-farm",
        resource_config: Optional[Dict] = None,
        enable_logging: bool = True,
        log_path: str = "farm_os/logs/decisions.db"
    ):
        self.farm_id = farm_id
        self.agents = agents or default_agent_set()
        
        # Initialize resource economy
        config = resource_config or {}
        self.resource_pool = create_resource_pool(
            farm_id=farm_id,
            water_capacity=config.get("water_capacity", 100000),
            labour_hours=config.get("labour_hours", 80),
            daily_budget=config.get("daily_budget", 1000)
        )
        self.bidding_engine = BiddingEngine(self.resource_pool)
        
        # Decision logging
        self.enable_logging = enable_logging
        self.decision_logger = DecisionLogger(log_path) if enable_logging else None
        
        # Cycle tracking
        self.cycle_count = 0
        self.last_cycle_result: Optional[Dict] = None

        # Register conflict handlers
        self.bidding_engine.register_conflict_handler(self._on_resource_conflict)
        self.bidding_engine.register_allocation_handler(self._on_resource_allocated)

    def configure_resources(
        self,
        water_liters: Optional[float] = None,
        labour_hours: Optional[float] = None,
        daily_budget: Optional[float] = None,
        **kwargs
    ) -> None:
        """Configure resource pool capacities."""
        if water_liters is not None:
            self.resource_pool.set_resource_capacity("water", water_liters)
        if labour_hours is not None:
            self.resource_pool.set_resource_capacity("labour", labour_hours)
        if daily_budget is not None:
            self.resource_pool.set_resource_capacity("budget", daily_budget)
        for resource_type, capacity in kwargs.items():
            self.resource_pool.set_resource_capacity(resource_type, capacity)

    def reset_daily_resources(self) -> None:
        """Reset resource pool to full capacity (call at start of each day)."""
        for resource in self.resource_pool.resources.values():
            resource.available = resource.total
            resource.reserved = 0.0
        self.resource_pool.pending_requests.clear()

    @staticmethod
    def _apply_guardrails(proposals: List[ActionProposal]) -> List[ActionProposal]:
        """Apply safety guardrails to action proposals."""
        guarded: List[ActionProposal] = []
        for p in proposals:
            # High-risk actions always require human approval
            if p.action_type in {
                "spray_pesticide", "animal_treatment", "cull", 
                "drone_herd_offboard", "chemical_application"
            }:
                p.risk = RiskLevel.HUMAN_APPROVAL
                p.priority = Priority.CRITICAL

            # Welfare-first: livestock water is always critical
            if p.action_type in {"check_water_points", "restore_livestock_water"}:
                p.priority = Priority.CRITICAL

            guarded.append(p)
        return guarded

    def _convert_proposals_to_bids(
        self,
        proposals: List[ActionProposal],
        agent_outputs: List[AgentOutput]
    ) -> List[ResourceBid]:
        """Convert action proposals to resource bids."""
        bids = []
        agent_map = {out.agent_id: out for out in agent_outputs}

        for proposal in proposals:
            # Determine resource requirements
            if proposal.action_type == "irrigate":
                liters = float(proposal.params.get("liters", 0))
                if liters > 0:
                    bid = ResourceBid(
                        agent_id=proposal.params.get("agent_id", "irrigation"),
                        agent_name="Irrigation Agent",
                        resource_type="water",
                        quantity_requested=liters,
                        quantity_minimum=liters * 0.5,  # Accept 50% minimum
                        priority=PRIORITY_MAP.get(proposal.priority, ResourcePriority.NORMAL),
                        duration_hours=2.0,
                        flexible_timing=(proposal.priority != Priority.CRITICAL),
                        reason=f"Irrigate {proposal.target}",
                        expected_outcome=f"Restore soil moisture in {proposal.target}",
                        risk_if_denied="Potential crop stress"
                    )
                    bids.append(bid)

            elif proposal.action_type in {"feed_livestock", "water_livestock"}:
                resource = "feed" if "feed" in proposal.action_type else "water"
                quantity = float(proposal.params.get("quantity", 0))
                if quantity > 0:
                    bid = create_livestock_bid(
                        agent_id=proposal.params.get("agent_id", "livestock"),
                        resource_type=resource,
                        quantity=quantity,
                        animal_count=int(proposal.params.get("animal_count", 1)),
                        is_welfare_critical=(proposal.priority == Priority.CRITICAL)
                    )
                    bids.append(bid)

            elif proposal.action_type in {"maintenance", "repair"}:
                # Maintenance requires labour
                hours = float(proposal.params.get("labour_hours", 1.0))
                bid = ResourceBid(
                    agent_id=proposal.params.get("agent_id", "maintenance"),
                    agent_name="Maintenance Agent",
                    resource_type="labour",
                    quantity_requested=hours,
                    quantity_minimum=hours * 0.5,
                    priority=PRIORITY_MAP.get(proposal.priority, ResourcePriority.NORMAL),
                    duration_hours=hours,
                    flexible_timing=True,
                    reason=f"Maintenance: {proposal.target}",
                    expected_outcome="Equipment/infrastructure maintained",
                    risk_if_denied="Deferred maintenance risk"
                )
                bids.append(bid)

        return bids

    def _resolve_resources_via_bidding(
        self,
        proposals: List[ActionProposal],
        agent_outputs: List[AgentOutput]
    ) -> tuple[List[ActionProposal], List[ResourceBid]]:
        """
        Resolve resource conflicts using the bidding engine.
        
        Returns approved proposals and list of resolved bids.
        """
        # Convert proposals to bids
        bids = self._convert_proposals_to_bids(proposals, agent_outputs)
        
        # Submit all bids
        for bid in bids:
            self.bidding_engine.submit_bid(bid)
        
        # Resolve bids
        resolved_bids = self.bidding_engine.resolve_bids()
        
        # Build map of successful bids
        approved_resources = {}
        for bid in resolved_bids:
            if bid.status in (BidStatus.ACCEPTED, BidStatus.PARTIAL):
                key = (bid.agent_id, bid.resource_type)
                approved_resources[key] = bid.allocated_quantity

        # Update proposals based on bid results
        updated_proposals = []
        for proposal in proposals:
            if proposal.action_type == "irrigate":
                agent_id = proposal.params.get("agent_id", "irrigation")
                key = (agent_id, "water")
                if key in approved_resources:
                    proposal.params["liters"] = approved_resources[key]
                    proposal.params["bid_allocated"] = True
                    updated_proposals.append(proposal)
                else:
                    # Bid rejected - don't include proposal
                    proposal.params["bid_rejected"] = True
            else:
                updated_proposals.append(proposal)

        return updated_proposals, resolved_bids

    def _log_cycle_decisions(
        self,
        cycle_id: str,
        ctx: AgentContext,
        proposals: List[ActionProposal],
        resolved_bids: List[ResourceBid],
        alerts: List[str]
    ) -> None:
        """Log all decisions from this cycle."""
        if not self.enable_logging or not self.decision_logger:
            return

        # Log each approved proposal
        for proposal in proposals:
            decision = Decision(
                decision_id=f"{cycle_id}-{str(uuid4())[:8]}",
                agent_id=proposal.params.get("agent_id", "unknown"),
                agent_name=proposal.action_type.replace("_", " ").title() + " Agent",
                decision_type=proposal.action_type,
                action=f"{proposal.action_type}:{proposal.target}",
                parameters=proposal.params,
                context={
                    "cycle_id": cycle_id,
                    "mode": ctx.mode,
                    "priority": proposal.priority.value,
                    "risk": proposal.risk.value
                },
                success=True
            )
            self.decision_logger.log(decision)

        # Log resource bids
        for bid in resolved_bids:
            decision = Decision(
                decision_id=f"{cycle_id}-bid-{bid.bid_id}",
                agent_id=bid.agent_id,
                agent_name=bid.agent_name,
                decision_type="resource_bid",
                action=f"bid:{bid.resource_type}",
                parameters={
                    "requested": bid.quantity_requested,
                    "allocated": bid.allocated_quantity,
                    "status": bid.status.value
                },
                context={
                    "cycle_id": cycle_id,
                    "priority": bid.priority,
                    "reason": bid.reason
                },
                outcome=bid.response_message,
                success=(bid.status in (BidStatus.ACCEPTED, BidStatus.PARTIAL))
            )
            self.decision_logger.log(decision)

        # Log alerts
        for i, alert in enumerate(alerts):
            decision = Decision(
                decision_id=f"{cycle_id}-alert-{i}",
                agent_id="orchestrator",
                agent_name="Orchestrator",
                decision_type="alert",
                action="raise_alert",
                parameters={"message": alert},
                context={"cycle_id": cycle_id},
                success=True
            )
            self.decision_logger.log(decision)

    def _on_resource_conflict(self, bid: ResourceBid, available: float) -> None:
        """Handle resource conflict (callback from bidding engine)."""
        if self.enable_logging and self.decision_logger:
            self.decision_logger.log_quick(
                agent_id="orchestrator",
                agent_name="Orchestrator",
                decision_type="resource_conflict",
                action="conflict_detected",
                parameters={
                    "bid_id": bid.bid_id,
                    "resource": bid.resource_type,
                    "requested": bid.quantity_requested,
                    "available": available
                }
            )

    def _on_resource_allocated(self, bid: ResourceBid, allocation) -> None:
        """Handle successful resource allocation (callback)."""
        pass  # Logged in _log_cycle_decisions

    def run_cycle(
        self,
        ctx: AgentContext,
        out_file: str = "logs/orchestrator_cycle.json"
    ) -> Dict[str, object]:
        """
        Run a complete orchestration cycle.
        
        1. Collect proposals from all agents
        2. Apply safety guardrails
        3. Resolve resource conflicts via bidding
        4. Log all decisions
        5. Return action queue
        """
        self.cycle_count += 1
        
        # Run all agents
        outputs: List[AgentOutput] = [agent.run(ctx) for agent in self.agents]

        all_proposals: List[ActionProposal] = []
        all_alerts: List[str] = []
        observations: Dict[str, object] = {}

        for out in outputs:
            all_proposals.extend(out.proposals)
            all_alerts.extend(out.alerts)
            observations[out.agent_id] = out.observations

        # Apply safety guardrails
        all_proposals = self._apply_guardrails(all_proposals)

        # Resolve resources via bidding
        approved_proposals, resolved_bids = self._resolve_resources_via_bidding(
            all_proposals, outputs
        )

        # Log decisions
        self._log_cycle_decisions(
            ctx.cycle_id, ctx, approved_proposals, resolved_bids, all_alerts
        )

        # Group by priority
        grouped = defaultdict(list)
        for p in approved_proposals:
            grouped[p.priority.value].append(asdict(p))

        # Build result
        result = {
            "cycle_id": ctx.cycle_id,
            "cycle_number": self.cycle_count,
            "mode": ctx.mode,
            "timestamp": datetime.now().isoformat(),
            "observations": observations,
            "alerts": all_alerts,
            "action_queue": dict(grouped),
            "approval_required": [
                asdict(p) for p in approved_proposals 
                if p.risk == RiskLevel.HUMAN_APPROVAL
            ],
            "resource_status": self.resource_pool.get_status(),
            "bids_resolved": len(resolved_bids),
            "bids_accepted": sum(
                1 for b in resolved_bids 
                if b.status in (BidStatus.ACCEPTED, BidStatus.PARTIAL)
            ),
            "bids_rejected": sum(
                1 for b in resolved_bids 
                if b.status == BidStatus.REJECTED
            ),
        }

        # Write to file
        path = Path(out_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        
        self.last_cycle_result = result
        return result

    def get_resource_status(self) -> Dict:
        """Get current resource pool status."""
        return self.resource_pool.get_status()

    def get_decision_summary(self, days: int = 1) -> Dict:
        """Get decision summary for recent days."""
        if not self.decision_logger:
            return {"error": "Logging not enabled"}
        return self.decision_logger.get_daily_summary()

    def submit_manual_bid(self, bid: ResourceBid) -> str:
        """Submit a manual resource bid (for external/UI requests)."""
        return self.bidding_engine.submit_bid(bid)

    def force_resolve_bids(self) -> List[ResourceBid]:
        """Force resolution of all pending bids."""
        return self.bidding_engine.resolve_bids()


# Factory function for common configurations
def create_orchestrator(
    farm_id: str = "default-farm",
    water_capacity: float = 100000,
    labour_hours: float = 80,
    daily_budget: float = 1000,
    enable_logging: bool = True
) -> FarmManagementOrchestrator:
    """Create an orchestrator with standard configuration."""
    return FarmManagementOrchestrator(
        farm_id=farm_id,
        resource_config={
            "water_capacity": water_capacity,
            "labour_hours": labour_hours,
            "daily_budget": daily_budget
        },
        enable_logging=enable_logging
    )
