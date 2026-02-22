from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.agents.irrigation.policies import RuleBasedIrrigationPolicy
from src.agents.yield_forecast import YieldForecastAgentV0
from src.orchestration.aez_policy import resolve_irrigation_config
from src.orchestration.contracts import AgentContext, AgentOutput, ActionProposal, Priority, RiskLevel


class BaseOpsAgent:
    agent_id = "base_agent"

    def run(self, ctx: AgentContext) -> AgentOutput:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class CropOperationsAgent(BaseOpsAgent):
    agent_id: str = "crop_ops"

    def __post_init__(self):
        self.irrigation = RuleBasedIrrigationPolicy()
        self.yield_model = YieldForecastAgentV0()

    def run(self, ctx: AgentContext) -> AgentOutput:
        out = AgentOutput(agent_id=self.agent_id)

        per_plot_overrides = {}
        for plot in ctx.farm_state.plots:
            cfg = resolve_irrigation_config(plot.aez_zone, plot.crop_type, ctx.mode)
            per_plot_overrides[plot.plot_id] = {
                "target_moisture": cfg.target_moisture,
                "stress_threshold": cfg.stress_threshold,
                "liters_per_moisture_point": cfg.liters_per_moisture_point,
                "min_daily_liters_per_plot": cfg.min_daily_liters_per_plot,
            }

        plan, rationale = self.irrigation.decide(ctx.farm_state, ctx.cycle_id, per_plot_overrides=per_plot_overrides)
        out.observations["irrigation_config_by_plot"] = per_plot_overrides

        for plot_id, liters in plan.irrigation_by_plot_liters.items():
            out.proposals.append(
                ActionProposal(
                    action_type="irrigate",
                    target=plot_id,
                    params={"liters": liters, "reason": rationale},
                    priority=Priority.HIGH,
                    risk=RiskLevel.GUARDED,
                )
            )

        forecast = self.yield_model.predict(ctx.farm_state)
        out.observations["yield_forecast"] = self.yield_model.to_log_dict(forecast)

        if forecast.recommendation_tag == "increase_irrigation":
            out.alerts.append("Yield model indicates elevated stress risk; irrigation should be prioritized.")

        return out


@dataclass
class LivestockOperationsAgent(BaseOpsAgent):
    agent_id: str = "livestock_ops"

    def run(self, ctx: AgentContext) -> AgentOutput:
        out = AgentOutput(agent_id=self.agent_id)
        # Placeholder: in future wire cattle/goat/poultry telemetry.
        out.proposals.extend(
            [
                ActionProposal(
                    action_type="check_water_points",
                    target="all_livestock_troughs",
                    params={"deadline_hours": 2},
                    priority=Priority.CRITICAL,
                    risk=RiskLevel.SAFE,
                ),
                ActionProposal(
                    action_type="feed_round",
                    target="cattle_goats_poultry",
                    params={"mode": "seasonal_ration"},
                    priority=Priority.HIGH,
                    risk=RiskLevel.SAFE,
                ),
            ]
        )
        return out


@dataclass
class WeatherWaterAgent(BaseOpsAgent):
    agent_id: str = "weather_water_ops"

    def run(self, ctx: AgentContext) -> AgentOutput:
        out = AgentOutput(agent_id=self.agent_id)
        rain = ctx.farm_state.weather.rainfall_mm
        out.observations["rainfall_mm"] = rain

        if ctx.mode == "dry_season":
            out.proposals.append(
                ActionProposal(
                    action_type="calibrate_flow_meters",
                    target="irrigation_network",
                    params={"window": "today"},
                    priority=Priority.HIGH,
                    risk=RiskLevel.SAFE,
                )
            )
        return out


@dataclass
class MaintenanceAgent(BaseOpsAgent):
    agent_id: str = "maintenance_ops"

    def run(self, ctx: AgentContext) -> AgentOutput:
        out = AgentOutput(agent_id=self.agent_id)
        out.proposals.append(
            ActionProposal(
                action_type="pump_vibration_check",
                target="main_borehole_pump",
                params={"max_mm_s": 7.0},
                priority=Priority.HIGH,
                risk=RiskLevel.SAFE,
            )
        )
        return out


@dataclass
class SecurityBiosecurityAgent(BaseOpsAgent):
    agent_id: str = "security_biosecurity"

    def run(self, ctx: AgentContext) -> AgentOutput:
        out = AgentOutput(agent_id=self.agent_id)
        out.proposals.extend(
            [
                ActionProposal(
                    action_type="visitor_biosecurity_check",
                    target="farm_gate",
                    params={"require_disinfection": True},
                    priority=Priority.CRITICAL,
                    risk=RiskLevel.SAFE,
                ),
                ActionProposal(
                    action_type="perimeter_scan",
                    target="all_zones",
                    params={"camera+gate": True},
                    priority=Priority.HIGH,
                    risk=RiskLevel.SAFE,
                ),
            ]
        )
        return out


def default_agent_set() -> List[BaseOpsAgent]:
    return [
        CropOperationsAgent(),
        LivestockOperationsAgent(),
        WeatherWaterAgent(),
        MaintenanceAgent(),
        SecurityBiosecurityAgent(),
    ]
