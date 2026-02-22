from __future__ import annotations

from dataclasses import dataclass

from farm_os.env.simulator import FarmState, IrrigationAction


@dataclass
class Thresholds:
    default_low: float = 35.0
    critical_low: float = 22.0
    rain_deferral_mm: float = 8.0


class IrrigationAgentV0:
    """Rule-based irrigation policy with explainable output."""

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.thresholds = thresholds or Thresholds()

    def decide(self, state: FarmState) -> IrrigationAction:
        if state.forecast_rain_12h_mm >= self.thresholds.rain_deferral_mm and state.soil_moisture_pct > self.thresholds.default_low:
            return IrrigationAction(False, 0.0, "Rain expected soon; deferring irrigation")

        if state.soil_moisture_pct <= self.thresholds.critical_low:
            target = min(state.max_irrigation_mm_day, 14.0)
            return IrrigationAction(True, target, "Critical moisture threshold breached")

        if state.soil_moisture_pct <= self.thresholds.default_low:
            target = min(state.max_irrigation_mm_day, 8.0)
            return IrrigationAction(True, target, "Moisture below stage threshold")

        return IrrigationAction(False, 0.0, "Moisture within acceptable range")
