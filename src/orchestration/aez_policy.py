from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class IrrigationConfig:
    target_moisture: float
    stress_threshold: float
    liters_per_moisture_point: float
    min_daily_liters_per_plot: float


# Zimbabwe-aligned directional defaults (heuristic v0)
AEZ_BASE: Dict[str, IrrigationConfig] = {
    "I": IrrigationConfig(0.70, 0.42, 420.0, 35.0),
    "II": IrrigationConfig(0.68, 0.40, 400.0, 35.0),
    "III": IrrigationConfig(0.66, 0.40, 390.0, 40.0),
    "IV": IrrigationConfig(0.63, 0.39, 380.0, 45.0),
    "V": IrrigationConfig(0.60, 0.38, 360.0, 45.0),
}

CROP_TARGET_BONUS = {
    "potato": 0.05,
    "maize": 0.03,
    "groundnut": 0.01,
    "sorghum": -0.02,
}


def resolve_irrigation_config(aez_zone: str, crop_type: str, mode: str) -> IrrigationConfig:
    base = AEZ_BASE.get(aez_zone.upper(), AEZ_BASE["III"])
    bonus = CROP_TARGET_BONUS.get(crop_type.lower(), 0.0)

    mode_shift = 0.02 if mode == "dry_season" else -0.01
    target = min(0.80, max(0.50, base.target_moisture + bonus + mode_shift))

    return IrrigationConfig(
        target_moisture=target,
        stress_threshold=base.stress_threshold,
        liters_per_moisture_point=base.liters_per_moisture_point,
        min_daily_liters_per_plot=base.min_daily_liters_per_plot,
    )
