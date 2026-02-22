from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class YieldBand:
    low_tpha: float
    high_tpha: float


# Heuristic initialization targets by crop + AEZ (to be calibrated with local data)
# Values are intentionally conservative for v0 planning.
YIELD_TARGETS: Dict[str, Dict[str, YieldBand]] = {
    "maize": {
        "I": YieldBand(6.5, 10.0),
        "II": YieldBand(5.0, 8.0),
        "III": YieldBand(3.5, 6.0),
        "IV": YieldBand(1.8, 4.0),
        "V": YieldBand(0.8, 2.5),
    },
    "potato": {
        "I": YieldBand(28.0, 40.0),
        "II": YieldBand(24.0, 36.0),
        "III": YieldBand(20.0, 32.0),
        "IV": YieldBand(14.0, 24.0),
        "V": YieldBand(8.0, 18.0),
    },
    "sorghum": {
        "I": YieldBand(3.0, 5.0),
        "II": YieldBand(2.5, 4.5),
        "III": YieldBand(2.0, 4.0),
        "IV": YieldBand(1.2, 3.0),
        "V": YieldBand(0.8, 2.2),
    },
    "groundnut": {
        "I": YieldBand(1.8, 3.2),
        "II": YieldBand(1.4, 2.8),
        "III": YieldBand(1.0, 2.3),
        "IV": YieldBand(0.7, 1.8),
        "V": YieldBand(0.5, 1.2),
    },
}


def get_yield_band(crop_type: str, aez_zone: str) -> YieldBand:
    crop = crop_type.lower()
    zone = aez_zone.upper()
    crop_map = YIELD_TARGETS.get(crop)
    if not crop_map:
        return YieldBand(1.0, 3.0)
    return crop_map.get(zone, crop_map.get("III", YieldBand(1.0, 3.0)))


def midpoint_target(crop_type: str, aez_zone: str) -> float:
    band = get_yield_band(crop_type, aez_zone)
    return round((band.low_tpha + band.high_tpha) / 2.0, 3)
