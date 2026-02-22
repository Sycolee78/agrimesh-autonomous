from __future__ import annotations

from datetime import datetime
import random
from typing import Dict, List

import pandas as pd
import streamlit as st

from src.common.models import FarmState, KPIState, PlotState, WaterSystemState, WeatherState
from src.orchestration import AgentContext, FarmManagementOrchestrator
from src.sim.environment import FarmSimulator


st.set_page_config(page_title="AgriMesh Simulator", page_icon="🌾", layout="wide")


@st.cache_data
def _seeded_weather(day: int, base_temp: float, base_rain: float, variability: float) -> Dict[str, float]:
    random.seed(1000 + day)
    temp = base_temp + random.uniform(-variability, variability)
    rain = max(0.0, base_rain + random.uniform(-variability, variability))
    humidity = min(90.0, max(25.0, 55.0 + random.uniform(-12.0, 12.0)))
    return {"temp": round(temp, 2), "rain": round(rain, 2), "humidity": round(humidity, 2)}


def initial_state() -> FarmState:
    return FarmState(
        timestamp=datetime(2026, 2, 22, 6, 0, 0),
        plots=[
            PlotState(plot_id="P1", area_m2=300, crop_type="maize", crop_stage="vegetative", soil_moisture=0.42, aez_zone="II"),
            PlotState(plot_id="P2", area_m2=260, crop_type="potato", crop_stage="tuber_init", soil_moisture=0.38, aez_zone="III"),
            PlotState(plot_id="P3", area_m2=240, crop_type="sorghum", crop_stage="vegetative", soil_moisture=0.48, aez_zone="IV"),
            PlotState(plot_id="P4", area_m2=180, crop_type="groundnut", crop_stage="flowering", soil_moisture=0.45, aez_zone="III"),
        ],
        water_system=WaterSystemState(tank_level_liters=12000, daily_supply_limit_liters=1800, pump_capacity_lpm=70),
        weather=WeatherState(temperature_c=30, humidity_pct=55, rainfall_mm=1.2),
        kpis=KPIState(),
    )


def extract_irrigation_plan(action_queue: Dict[str, List[Dict]]) -> Dict[str, float]:
    plan: Dict[str, float] = {}
    for priority in action_queue.values():
        for action in priority:
            if action.get("action_type") == "irrigate":
                plan[action["target"]] = float(action.get("params", {}).get("liters", 0.0))
    return plan


st.title("🌾 AgriMesh Autonomous — Simulation Frontend")
st.caption("Simulates AEZ-aware multi-agent orchestration for a Zimbabwe mixed farm.")

with st.sidebar:
    st.header("Simulation Controls")
    days = st.slider("Days", min_value=7, max_value=120, value=30, step=1)
    mode = st.selectbox("Season Mode", options=["dry_season", "wet_season"], index=0)
    water_budget = st.number_input("Daily Water Budget (L)", min_value=200, max_value=5000, value=1200, step=50)
    base_temp = st.slider("Base Temperature (°C)", min_value=15, max_value=40, value=30)
    base_rain = st.slider("Base Rainfall (mm)", min_value=0.0, max_value=20.0, value=1.0, step=0.1)
    variability = st.slider("Weather Variability", min_value=0.0, max_value=8.0, value=2.0, step=0.2)
    run = st.button("Run Simulation", type="primary")

if run:
    orchestrator = FarmManagementOrchestrator()
    simulator = FarmSimulator()
    state = initial_state()

    rows = []
    alert_log = []
    latest_actions = {}

    for day in range(1, days + 1):
        w = _seeded_weather(day, base_temp, base_rain, variability)
        state.weather.temperature_c = w["temp"]
        state.weather.rainfall_mm = w["rain"]
        state.weather.humidity_pct = w["humidity"]

        ctx = AgentContext(
            cycle_id=f"day-{day:03d}",
            mode=mode,
            farm_state=state,
            budgets={"water_liters_day": float(water_budget)},
        )
        orch = orchestrator.run_cycle(ctx)
        irrigation_plan = extract_irrigation_plan(orch["action_queue"])
        latest_actions = orch["action_queue"]

        state, decision, outcome = simulator.step(
            state=state,
            plan_by_plot=irrigation_plan,
            cycle_id=ctx.cycle_id,
            agent_id="orchestrator_irrigation",
            rationale="orchestrated multi-agent cycle",
            policy_version="orch-v1",
        )

        rows.append(
            {
                "day": day,
                "timestamp": state.timestamp,
                "water_applied_l": outcome.actual_changes["total_water_applied_liters"],
                "tank_level_l": outcome.actual_changes["tank_level_liters"],
                "stress_events_total": outcome.kpi_delta["crop_stress_events_total"],
                "wue": outcome.kpi_delta["water_use_efficiency"],
                "yield_proxy": outcome.kpi_delta["yield_estimate_tons_per_ha"],
                "rain_mm": state.weather.rainfall_mm,
                "temp_c": state.weather.temperature_c,
            }
        )
        if orch.get("alerts"):
            alert_log.extend([{"day": day, "alert": a} for a in orch["alerts"]])

    df = pd.DataFrame(rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final Yield Proxy (t/ha)", f"{df['yield_proxy'].iloc[-1]:.2f}")
    c2.metric("Total Water Applied (L)", f"{df['water_applied_l'].sum():,.0f}")
    c3.metric("Final Tank Level (L)", f"{df['tank_level_l'].iloc[-1]:,.0f}")
    c4.metric("Stress Events", int(df["stress_events_total"].iloc[-1]))

    st.subheader("KPI Trends")
    st.line_chart(df.set_index("day")[["yield_proxy", "wue"]])
    st.subheader("Resources & Conditions")
    st.line_chart(df.set_index("day")[["water_applied_l", "tank_level_l", "rain_mm", "temp_c"]])

    st.subheader("Latest Orchestrator Action Queue")
    st.json(latest_actions)

    st.subheader("Alerts")
    if alert_log:
        st.dataframe(pd.DataFrame(alert_log), use_container_width=True)
    else:
        st.info("No alerts generated in this run.")

    with st.expander("Raw daily records"):
        st.dataframe(df, use_container_width=True)
else:
    st.info("Set parameters in the sidebar, then click **Run Simulation**.")
