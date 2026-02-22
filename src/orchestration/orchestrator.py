from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
import json
from typing import Dict, List

from src.orchestration.agents import BaseOpsAgent, default_agent_set
from src.orchestration.contracts import AgentContext, AgentOutput, ActionProposal, Priority, RiskLevel


class FarmManagementOrchestrator:
    """Coordinates specialized farm agents with hard safety and approval guardrails."""

    def __init__(self, agents: List[BaseOpsAgent] | None = None):
        self.agents = agents or default_agent_set()

    @staticmethod
    def _apply_guardrails(proposals: List[ActionProposal]) -> List[ActionProposal]:
        guarded: List[ActionProposal] = []
        for p in proposals:
            # High-risk actions always require human approval.
            if p.action_type in {"spray_pesticide", "animal_treatment", "cull", "drone_herd_offboard"}:
                p.risk = RiskLevel.HUMAN_APPROVAL
                p.priority = Priority.CRITICAL

            # Welfare-first default: any action touching livestock water is critical.
            if p.action_type in {"check_water_points", "restore_livestock_water"}:
                p.priority = Priority.CRITICAL

            guarded.append(p)
        return guarded

    @staticmethod
    def _resolve_water_conflicts(proposals: List[ActionProposal], water_budget_liters: float) -> List[ActionProposal]:
        water_actions = [p for p in proposals if p.action_type == "irrigate"]
        non_water = [p for p in proposals if p.action_type != "irrigate"]

        total = sum(float(p.params.get("liters", 0.0)) for p in water_actions)
        if total <= water_budget_liters or total == 0:
            return proposals

        # Scale irrigation down while preserving relative intent.
        scale = water_budget_liters / total
        for p in water_actions:
            p.params["liters"] = round(float(p.params.get("liters", 0.0)) * scale, 2)
            p.params["water_conflict_scaled"] = True

        return non_water + water_actions

    def run_cycle(self, ctx: AgentContext, out_file: str = "logs/orchestrator_cycle.json") -> Dict[str, object]:
        outputs: List[AgentOutput] = [a.run(ctx) for a in self.agents]

        all_proposals: List[ActionProposal] = []
        all_alerts: List[str] = []
        observations: Dict[str, object] = {}

        for out in outputs:
            all_proposals.extend(out.proposals)
            all_alerts.extend(out.alerts)
            observations[out.agent_id] = out.observations

        all_proposals = self._apply_guardrails(all_proposals)
        water_budget = float(ctx.budgets.get("water_liters_day", ctx.farm_state.water_system.daily_supply_limit_liters))
        all_proposals = self._resolve_water_conflicts(all_proposals, water_budget)

        grouped = defaultdict(list)
        for p in all_proposals:
            grouped[p.priority.value].append(asdict(p))

        result = {
            "cycle_id": ctx.cycle_id,
            "mode": ctx.mode,
            "observations": observations,
            "alerts": all_alerts,
            "action_queue": dict(grouped),
            "approval_required": [asdict(p) for p in all_proposals if p.risk == RiskLevel.HUMAN_APPROVAL],
        }

        path = Path(out_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
