from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Literal

from src.agents.irrigation.policies import BaselineFixedSchedulePolicy, RuleBasedIrrigationPolicy
from src.common.models import FarmState, KPIState, PlotState, WaterSystemState, WeatherState
from src.sim.environment import FarmSimulator


def initial_state() -> FarmState:
    return FarmState(
        timestamp=datetime(2026, 2, 20, 6, 0, 0),
        plots=[
            PlotState(plot_id="P1", area_m2=300, crop_type="maize", crop_stage="vegetative", soil_moisture=0.44),
            PlotState(plot_id="P2", area_m2=260, crop_type="maize", crop_stage="vegetative", soil_moisture=0.40),
        ],
        water_system=WaterSystemState(
            tank_level_liters=8000,
            daily_supply_limit_liters=1200,
            pump_capacity_lpm=65,
        ),
        weather=WeatherState(
            temperature_c=29,
            humidity_pct=58,
            rainfall_mm=1.5,
        ),
        kpis=KPIState(),
    )


def run(days: int = 14, policy: Literal["baseline", "agent"] = "agent", out_file: str = "logs/sim_run.jsonl") -> None:
    state = initial_state()
    sim = FarmSimulator()

    if policy == "baseline":
        actor = BaselineFixedSchedulePolicy(liters_per_plot=120)
    else:
        actor = RuleBasedIrrigationPolicy()

    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for day in range(days):
            cycle_id = f"day-{day+1:03d}"
            plan, rationale = actor.decide(state, cycle_id)
            state, decision, outcome = sim.step(
                state=state,
                plan_by_plot=plan.irrigation_by_plot_liters,
                cycle_id=cycle_id,
                agent_id=plan.agent_id,
                rationale=rationale,
                policy_version=actor.policy_version,
            )
            row = {
                "cycle_id": cycle_id,
                "decision": asdict(decision),
                "outcome": asdict(outcome),
                "timestamp": state.timestamp.isoformat(),
            }
            f.write(json.dumps(row, default=str) + "\n")

    print(f"Simulation finished: {days} days, policy={policy}, output={out_path}")


if __name__ == "__main__":
    run()
