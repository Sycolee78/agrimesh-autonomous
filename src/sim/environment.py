from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from hashlib import sha256
import json
from typing import Dict, Tuple

from src.common.models import DecisionLog, FarmState, OutcomeLog
from src.sim.yield_model import calculate_yield_factor, get_critical_threshold, CROP_PROFILES


class FarmSimulator:
    """Deterministic simulation core for daily cycles (Phase 1)."""

    def __init__(self):
        self.day_index = 0

    @staticmethod
    def _observation_hash(state: FarmState) -> str:
        payload = {
            "timestamp": state.timestamp.isoformat(),
            "plots": [asdict(p) for p in state.plots],
            "weather": asdict(state.weather),
            "water_system": asdict(state.water_system),
            "schema_version": state.schema_version,
        }
        blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return sha256(blob).hexdigest()

    def step(self, state: FarmState, plan_by_plot: Dict[str, float], cycle_id: str, agent_id: str, rationale: str, policy_version: str) -> Tuple[FarmState, DecisionLog, OutcomeLog]:
        before_moisture = {p.plot_id: p.soil_moisture for p in state.plots}
        total_applied = 0.0

        # Apply irrigation (simple conversion for now)
        for plot in state.plots:
            liters = max(0.0, plan_by_plot.get(plot.plot_id, 0.0))
            total_applied += liters
            moisture_gain = liters / 300.0
            rain_gain = state.weather.rainfall_mm / 100.0
            evap_loss = max(0.0, (state.weather.temperature_c - 20.0) / 200.0)
            plot.soil_moisture = min(1.0, max(0.0, plot.soil_moisture + moisture_gain + rain_gain - evap_loss))

        state.water_system.tank_level_liters = max(0.0, state.water_system.tank_level_liters - total_applied)

        # Track stress and update yield using realistic crop model
        stress_events = 0
        total_yield_factor = 0.0
        
        for plot in state.plots:
            # Advance day of season
            plot.day_of_season = getattr(plot, 'day_of_season', 30) + 1
            
            # Check for stress (below critical threshold for this crop)
            critical = get_critical_threshold(plot.crop_type)
            if plot.soil_moisture < critical:
                stress_events += 1
                plot.cumulative_stress_days = getattr(plot, 'cumulative_stress_days', 0) + 1
            
            # Calculate yield factor for this plot
            yield_factor = calculate_yield_factor(
                soil_moisture=plot.soil_moisture,
                crop=plot.crop_type,
                day_of_season=plot.day_of_season,
                cumulative_stress_days=plot.cumulative_stress_days,
            )
            total_yield_factor += yield_factor
        
        avg_moisture = sum(p.soil_moisture for p in state.plots) / max(1, len(state.plots))
        avg_yield_factor = total_yield_factor / max(1, len(state.plots))
        
        # KPIs using realistic yield model
        state.kpis.crop_stress_events += stress_events
        state.kpis.water_use_efficiency = round(avg_yield_factor / max(0.1, total_applied / 1000.0), 4) if total_applied > 0 else avg_yield_factor
        
        # Weighted average yield based on crop profiles
        total_yield = 0.0
        total_area = 0.0
        for plot in state.plots:
            profile = CROP_PROFILES.get(plot.crop_type, CROP_PROFILES["maize"])
            plot_yield_factor = calculate_yield_factor(
                plot.soil_moisture, plot.crop_type, plot.day_of_season, plot.cumulative_stress_days
            )
            plot_area_ha = plot.area_m2 / 10000
            total_yield += profile.max_yield_potential * plot_yield_factor * plot_area_ha
            total_area += plot_area_ha
        
        state.kpis.yield_estimate_tons_per_ha = round(total_yield / max(0.01, total_area), 3)

        state.timestamp = state.timestamp + timedelta(days=1)
        self.day_index += 1

        decision_log = DecisionLog(
            cycle_id=cycle_id,
            agent_id=agent_id,
            observation_hash=self._observation_hash(state),
            rationale=rationale,
            policy_version=policy_version,
            action_plan={"irrigation_by_plot_liters": plan_by_plot},
        )

        after_moisture = {p.plot_id: p.soil_moisture for p in state.plots}
        outcome_log = OutcomeLog(
            cycle_id=cycle_id,
            actual_changes={
                "tank_level_liters": state.water_system.tank_level_liters,
                "soil_moisture_before": before_moisture,
                "soil_moisture_after": after_moisture,
                "total_water_applied_liters": round(total_applied, 2),
            },
            kpi_delta={
                "crop_stress_events_total": state.kpis.crop_stress_events,
                "water_use_efficiency": state.kpis.water_use_efficiency,
                "yield_estimate_tons_per_ha": state.kpis.yield_estimate_tons_per_ha,
            },
            anomalies=[],
        )

        return state, decision_log, outcome_log
