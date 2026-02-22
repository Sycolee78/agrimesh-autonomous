from __future__ import annotations

from src.common.models import FarmState, KPIState, PlotState, WaterSystemState, WeatherState
from src.orchestration import AgentContext, FarmManagementOrchestrator
from datetime import datetime
import json


def demo_state() -> FarmState:
    return FarmState(
        timestamp=datetime(2026, 2, 22, 6, 0, 0),
        plots=[
            PlotState(plot_id="P1", area_m2=300, crop_type="maize", crop_stage="vegetative", soil_moisture=0.40, aez_zone="II"),
            PlotState(plot_id="P2", area_m2=260, crop_type="potato", crop_stage="tuber_init", soil_moisture=0.36, aez_zone="III"),
            PlotState(plot_id="P3", area_m2=240, crop_type="sorghum", crop_stage="vegetative", soil_moisture=0.47, aez_zone="IV"),
            PlotState(plot_id="P4", area_m2=180, crop_type="groundnut", crop_stage="flowering", soil_moisture=0.43, aez_zone="III"),
        ],
        water_system=WaterSystemState(tank_level_liters=9000, daily_supply_limit_liters=1400, pump_capacity_lpm=70),
        weather=WeatherState(temperature_c=31, humidity_pct=49, rainfall_mm=0.7),
        kpis=KPIState(),
    )


if __name__ == "__main__":
    orchestrator = FarmManagementOrchestrator()
    ctx = AgentContext(
        cycle_id="orch-001",
        mode="dry_season",
        farm_state=demo_state(),
        budgets={"water_liters_day": 1200},
    )
    result = orchestrator.run_cycle(ctx, out_file="logs/orchestrator_cycle.json")
    print(json.dumps(result, indent=2))
