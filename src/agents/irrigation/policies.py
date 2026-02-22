from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Tuple

from src.common.models import ActionPlan, FarmState


class BaselineFixedSchedulePolicy:
    """Simple baseline: fixed liters per plot per day."""

    policy_version = "baseline-fixed-v1"

    def __init__(self, liters_per_plot: float = 120.0):
        self.liters_per_plot = liters_per_plot

    def decide(self, state: FarmState, cycle_id: str) -> Tuple[ActionPlan, str]:
        plan = {plot.plot_id: self.liters_per_plot for plot in state.plots}
        rationale = f"Fixed schedule: {self.liters_per_plot}L per plot"
        return ActionPlan(agent_id="baseline_irrigation", cycle_id=cycle_id, irrigation_by_plot_liters=plan), rationale


class RuleBasedIrrigationPolicy:
    """Irrigation policy using soil moisture, rain, and tank constraints."""

    policy_version = "irrigation-rule-v1"

    def __init__(
        self,
        target_moisture: float = 0.62,
        stress_threshold: float = 0.38,
        liters_per_moisture_point: float = 300.0,
    ):
        self.target_moisture = target_moisture
        self.stress_threshold = stress_threshold
        self.liters_per_moisture_point = liters_per_moisture_point

    def decide(self, state: FarmState, cycle_id: str) -> Tuple[ActionPlan, str]:
        planned: Dict[str, float] = {}

        rain_factor = max(0.0, 1.0 - (state.weather.rainfall_mm / 20.0))  # heavy rain -> less irrigation

        for plot in state.plots:
            deficit = max(0.0, self.target_moisture - plot.soil_moisture)
            liters = deficit * self.liters_per_moisture_point * rain_factor
            planned[plot.plot_id] = round(max(0.0, liters), 2)

        total_planned = sum(planned.values())
        cap = min(state.water_system.tank_level_liters, state.water_system.daily_supply_limit_liters)

        if total_planned > cap and total_planned > 0:
            scale = cap / total_planned
            planned = {k: round(v * scale, 2) for k, v in planned.items()}

        stress_plots = [p.plot_id for p in state.plots if p.soil_moisture < self.stress_threshold]
        rationale = (
            f"Rule-based irrigation using deficits to target {self.target_moisture:.2f}; "
            f"rain_factor={rain_factor:.2f}; stress_plots={stress_plots}"
        )

        return ActionPlan(agent_id="irrigation_agent", cycle_id=cycle_id, irrigation_by_plot_liters=planned), rationale
