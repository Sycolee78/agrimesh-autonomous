from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from hashlib import sha256
import json
from typing import Dict, Tuple

from src.common.models import DecisionLog, FarmState, OutcomeLog


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

        stress_events = sum(1 for p in state.plots if p.soil_moisture < 0.38)
        avg_moisture = sum(p.soil_moisture for p in state.plots) / max(1, len(state.plots))

        # Toy KPI formulas for scaffold
        state.kpis.crop_stress_events += stress_events
        state.kpis.water_use_efficiency = round(avg_moisture / max(1.0, total_applied / 1000.0), 4) if total_applied > 0 else 0.0
        state.kpis.yield_estimate_tons_per_ha = round(2.0 + avg_moisture * 3.5 - (state.kpis.crop_stress_events * 0.01), 3)

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
