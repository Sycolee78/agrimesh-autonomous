from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Tuple

from src.common.models import ActionPlan, FarmState
from src.sim.yield_model import get_target_moisture, get_critical_threshold, get_growth_stage, CROP_PROFILES


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

    policy_version = "irrigation-rule-v2"

    def __init__(
        self,
        target_moisture: float = 0.68,
        stress_threshold: float = 0.40,
        liters_per_moisture_point: float = 380.0,
        min_daily_liters_per_plot: float = 45.0,
    ):
        self.target_moisture = target_moisture
        self.stress_threshold = stress_threshold
        self.liters_per_moisture_point = liters_per_moisture_point
        self.min_daily_liters_per_plot = min_daily_liters_per_plot

    def decide(self, state: FarmState, cycle_id: str, per_plot_overrides: Dict[str, Dict[str, float]] | None = None) -> Tuple[ActionPlan, str]:
        planned: Dict[str, float] = {}

        rain_factor = max(0.0, 1.0 - (state.weather.rainfall_mm / 20.0))  # heavy rain -> less irrigation

        for plot in state.plots:
            cfg = (per_plot_overrides or {}).get(plot.plot_id, {})
            target_moisture = float(cfg.get("target_moisture", self.target_moisture))
            stress_threshold = float(cfg.get("stress_threshold", self.stress_threshold))
            liters_per_point = float(cfg.get("liters_per_moisture_point", self.liters_per_moisture_point))
            min_floor = float(cfg.get("min_daily_liters_per_plot", self.min_daily_liters_per_plot))

            deficit = max(0.0, target_moisture - plot.soil_moisture)
            liters = deficit * liters_per_point * rain_factor

            # If plot is below stress threshold, enforce a recovery floor.
            if plot.soil_moisture < stress_threshold:
                liters = max(liters, min_floor)

            planned[plot.plot_id] = round(max(0.0, liters), 2)

        total_planned = sum(planned.values())
        cap = min(state.water_system.tank_level_liters, state.water_system.daily_supply_limit_liters)

        if total_planned > cap and total_planned > 0:
            scale = cap / total_planned
            planned = {k: round(v * scale, 2) for k, v in planned.items()}

        stress_plots = [p.plot_id for p in state.plots if p.soil_moisture < self.stress_threshold]
        rationale = (
            f"Rule-based irrigation with optional AEZ/crop overrides; default_target={self.target_moisture:.2f}; "
            f"rain_factor={rain_factor:.2f}; default_min_floor={self.min_daily_liters_per_plot:.1f}; "
            f"stress_plots={stress_plots}"
        )

        return ActionPlan(agent_id="irrigation_agent", cycle_id=cycle_id, irrigation_by_plot_liters=planned), rationale


class GrowthStageAwarePolicy:
    """
    Advanced irrigation policy that adapts to crop growth stages.
    
    Key improvements over RuleBasedIrrigationPolicy:
    - Dynamic target moisture based on growth stage (higher during flowering)
    - Crop-specific optimal ranges (not one-size-fits-all)
    - Yield-optimized, not just water-efficient
    """

    policy_version = "irrigation-growth-stage-v1"

    def __init__(
        self,
        liters_per_moisture_point: float = 400.0,
        recovery_boost_factor: float = 1.5,
    ):
        self.liters_per_moisture_point = liters_per_moisture_point
        self.recovery_boost_factor = recovery_boost_factor

    def decide(self, state: FarmState, cycle_id: str, per_plot_overrides: Dict[str, Dict[str, float]] | None = None) -> Tuple[ActionPlan, str]:
        planned: Dict[str, float] = {}
        rationale_parts = []

        rain_factor = max(0.0, 1.0 - (state.weather.rainfall_mm / 20.0))
        
        for plot in state.plots:
            crop = plot.crop_type
            day_of_season = getattr(plot, 'day_of_season', 30)
            
            # Get crop-specific targets based on growth stage
            target_moisture = get_target_moisture(crop, day_of_season)
            critical_threshold = get_critical_threshold(crop)
            growth_stage = get_growth_stage(day_of_season, crop)
            
            # Apply any per-plot overrides
            cfg = (per_plot_overrides or {}).get(plot.plot_id, {})
            target_moisture = float(cfg.get("target_moisture", target_moisture))
            liters_per_point = float(cfg.get("liters_per_moisture_point", self.liters_per_moisture_point))
            
            # Calculate deficit
            deficit = max(0.0, target_moisture - plot.soil_moisture)
            liters = deficit * liters_per_point * rain_factor
            
            # Recovery boost if below critical
            if plot.soil_moisture < critical_threshold:
                liters = liters * self.recovery_boost_factor
                rationale_parts.append(f"{plot.plot_id}:STRESS_RECOVERY")
            
            # During flowering, ensure minimum water
            if growth_stage.value == "flowering" and liters < 30:
                liters = max(liters, 30.0)
                rationale_parts.append(f"{plot.plot_id}:FLOWERING_MIN")
            
            planned[plot.plot_id] = round(max(0.0, liters), 2)

        # Cap to available water
        total_planned = sum(planned.values())
        cap = min(state.water_system.tank_level_liters, state.water_system.daily_supply_limit_liters)

        if total_planned > cap and total_planned > 0:
            # Priority scaling: stressed plots get priority
            priorities = {}
            for plot in state.plots:
                critical = get_critical_threshold(plot.crop_type)
                if plot.soil_moisture < critical:
                    priorities[plot.plot_id] = 2.0  # High priority
                elif get_growth_stage(getattr(plot, 'day_of_season', 30), plot.crop_type).value == "flowering":
                    priorities[plot.plot_id] = 1.5  # Medium-high priority
                else:
                    priorities[plot.plot_id] = 1.0
            
            # Weighted scaling
            total_weighted = sum(planned[p] * priorities.get(p, 1.0) for p in planned)
            if total_weighted > 0:
                scale = cap / total_weighted
                planned = {k: round(min(v, v * priorities.get(k, 1.0) * scale), 2) for k, v in planned.items()}

        rationale = (
            f"Growth-stage-aware irrigation; rain_factor={rain_factor:.2f}; "
            f"details=[{', '.join(rationale_parts) if rationale_parts else 'normal ops'}]"
        )

        return ActionPlan(agent_id="irrigation_agent_v2", cycle_id=cycle_id, irrigation_by_plot_liters=planned), rationale
