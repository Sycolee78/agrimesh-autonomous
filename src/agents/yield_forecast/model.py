from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, List

from src.common.models import FarmState


@dataclass
class YieldForecastResult:
    yield_proxy_estimate_tpha: float
    stress_risk_7d: float
    recommendation_tag: str
    reason: str


class YieldForecastAgentV0:
    """Transparent heuristic forecast model for Phase 1 scaffolding."""

    model_version = "yield-heuristic-v0"

    def __init__(self, stress_threshold: float = 0.38):
        self.stress_threshold = stress_threshold

    def predict(self, state: FarmState, recent_avg_moisture: List[float] | None = None) -> YieldForecastResult:
        moistures = [p.soil_moisture for p in state.plots]
        avg_m = mean(moistures) if moistures else 0.0

        if recent_avg_moisture:
            trend_m = mean(recent_avg_moisture[-7:])
            avg_effective = (avg_m * 0.6) + (trend_m * 0.4)
        else:
            avg_effective = avg_m

        heat_penalty = max(0.0, (state.weather.temperature_c - 30.0) * 0.03)
        rain_bonus = min(0.2, state.weather.rainfall_mm * 0.01)
        stress_count = sum(1 for p in state.plots if p.soil_moisture < self.stress_threshold)
        stress_risk = min(1.0, max(0.0, (stress_count / max(1, len(state.plots))) + heat_penalty - rain_bonus))

        yield_proxy = max(0.5, 2.0 + avg_effective * 3.8 - (stress_risk * 0.9))

        if stress_risk > 0.6:
            tag = "increase_irrigation"
        elif stress_risk > 0.35:
            tag = "watch_stress"
        else:
            tag = "stable"

        reason = (
            f"avg_m={avg_m:.3f}, avg_effective={avg_effective:.3f}, "
            f"heat_penalty={heat_penalty:.3f}, rain_bonus={rain_bonus:.3f}, stress_count={stress_count}"
        )

        return YieldForecastResult(
            yield_proxy_estimate_tpha=round(yield_proxy, 3),
            stress_risk_7d=round(stress_risk, 3),
            recommendation_tag=tag,
            reason=reason,
        )

    def to_log_dict(self, result: YieldForecastResult) -> Dict[str, object]:
        return {
            "model_version": self.model_version,
            "yield_proxy_estimate_tpha": result.yield_proxy_estimate_tpha,
            "stress_risk_7d": result.stress_risk_7d,
            "recommendation_tag": result.recommendation_tag,
            "reason": result.reason,
        }
