from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FarmState:
    timestamp: datetime
    soil_moisture_pct: float
    forecast_rain_12h_mm: float
    temp_c: float
    crop_stage: str
    water_available_m3: float
    max_irrigation_mm_day: float


@dataclass
class IrrigationAction:
    irrigate_now: bool
    target_mm: float
    reason: str


class Simulator:
    """Minimal daily-step simulator scaffold (v0)."""

    def step(self, state: FarmState, action: IrrigationAction) -> FarmState:
        irrigation_effect = action.target_mm * 0.35 if action.irrigate_now else 0.0
        rain_effect = state.forecast_rain_12h_mm * 0.25
        evap_loss = max(0.8, 0.05 * state.temp_c)

        next_moisture = state.soil_moisture_pct + irrigation_effect + rain_effect - evap_loss
        next_moisture = max(0.0, min(100.0, next_moisture))

        return FarmState(
            timestamp=state.timestamp + timedelta(days=1),
            soil_moisture_pct=next_moisture,
            forecast_rain_12h_mm=0.0,
            temp_c=state.temp_c,
            crop_stage=state.crop_stage,
            water_available_m3=max(0.0, state.water_available_m3 - (action.target_mm * 0.1)),
            max_irrigation_mm_day=state.max_irrigation_mm_day,
        )
