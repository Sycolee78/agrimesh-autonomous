from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PlotState:
    plot_id: str
    area_m2: float
    crop_type: str
    crop_stage: str
    soil_moisture: float  # 0-1
    soil_type: str = "loam"
    aez_zone: str = "III"
    last_irrigation_at: Optional[datetime] = None


@dataclass
class WaterSystemState:
    tank_level_liters: float
    daily_supply_limit_liters: float
    pump_capacity_lpm: float


@dataclass
class WeatherState:
    temperature_c: float
    humidity_pct: float
    rainfall_mm: float


@dataclass
class KPIState:
    water_use_efficiency: float = 0.0
    crop_stress_events: int = 0
    yield_estimate_tons_per_ha: float = 0.0


@dataclass
class FarmState:
    timestamp: datetime
    plots: List[PlotState]
    water_system: WaterSystemState
    weather: WeatherState
    kpis: KPIState = field(default_factory=KPIState)
    schema_version: str = "v1"


@dataclass
class ActionPlan:
    agent_id: str
    cycle_id: str
    irrigation_by_plot_liters: Dict[str, float] = field(default_factory=dict)


@dataclass
class DecisionLog:
    cycle_id: str
    agent_id: str
    observation_hash: str
    rationale: str
    policy_version: str
    action_plan: Dict[str, Any]


@dataclass
class OutcomeLog:
    cycle_id: str
    actual_changes: Dict[str, Any]
    kpi_delta: Dict[str, Any]
    anomalies: List[str] = field(default_factory=list)
