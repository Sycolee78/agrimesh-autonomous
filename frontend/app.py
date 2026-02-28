from __future__ import annotations

from datetime import datetime
import json
import random
from typing import Dict, List, Any

import altair as alt
import pandas as pd
import streamlit as st

from src.common.models import FarmState, KPIState, PlotState, WaterSystemState, WeatherState
from src.orchestration import AgentContext, FarmManagementOrchestrator
from src.sim.environment import FarmSimulator


st.set_page_config(
    page_title="AgriMesh Autonomous Farm OS",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# HOME PAGE OVERVIEW
# ============================================================================

st.title("🌾 AgriMesh Autonomous")
st.caption("Agent-driven Farm OS for Zimbabwe — Smart Irrigation & Yield Optimization")

# Show overview on first visit or when toggled
if "show_overview" not in st.session_state:
    st.session_state["show_overview"] = True

with st.expander("📖 **Project Overview** — What AgriMesh Does", expanded=st.session_state["show_overview"]):
    st.session_state["show_overview"] = False  # Collapse after first view
    
    st.markdown("""
    ### 🎯 Mission
    **AgriMesh Autonomous** is an intelligent farm management system designed for Zimbabwe's 
    diverse agro-ecological zones. It uses AI agents to make daily irrigation decisions, 
    optimizing for both **water savings** and **crop yield**.
    
    ---
    
    ### ✅ What's Working (Phase 2 Complete)
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🌱 Smart Irrigation Agent**
        - Non-linear yield model (optimal moisture ranges)
        - Growth-stage-aware decisions
        - AEZ-specific crop policies
        
        **🌦️ Real Weather Integration**
        - Open-Meteo API for Zimbabwe
        - Historical data (1940-present)
        - 16-day forecasting
        
        **📊 Multi-Objective Optimization**
        - Pareto frontier analysis
        - Water vs yield trade-off curves
        - Configurable preferences
        """)
    
    with col2:
        st.markdown("""
        **🤖 LLM Reasoning Agent**
        - Decision explanations in plain language
        - Daily/weekly summaries
        - Farmer Q&A
        
        **✅ Pilot Validation**
        - Counterfactual analysis
        - 12 scenarios validated
        - 96% avg water savings
        
        **🗺️ Strategic Farm Planner**
        - AEZ-aware enterprise selection
        - Profit projections
        - Spatial layout planning
        """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 📈 Key Results
    """)
    
    result_cols = st.columns(4)
    with result_cols[0]:
        st.metric("Avg Water Savings", "96.2%", help="Across 12 pilot scenarios")
    with result_cols[1]:
        st.metric("Yield Impact", "-2.5%", help="Minimal trade-off for massive water savings")
    with result_cols[2]:
        st.metric("Best Case", "+5.4% yield", help="Bulawayo with erratic traditional irrigation")
    with result_cols[3]:
        st.metric("Locations Tested", "4", help="Harare, Bulawayo, Mutare, Masvingo")
    
    st.markdown("---")
    
    st.markdown("""
    ### 🧭 Navigate the App
    
    | Page | What It Does |
    |------|-------------|
    | **🏠 Home** (this page) | Run daily farm simulations with the orchestrator |
    | **🗺️ Farm Planner** | Click Zimbabwe map for AEZ-based recommendations |
    | **🎯 Strategic Planner** | Full farm planning with enterprise selection |
    | **🌦️ Weather Analysis** | View real weather data for any Zimbabwe location |
    | **📈 Optimization** | Explore Pareto frontier and tune parameters |
    | **✅ Validation** | Run counterfactual analysis on pilot farms |
    | **🤖 AI Advisor** | Ask questions, get explanations from the LLM agent |
    """)
    
    st.info("👈 Use the **sidebar** to navigate between pages, or scroll down to run a simulation.")

st.divider()


def default_plot_catalog() -> List[Dict[str, Any]]:
    return [
        {"plot_id": "P1", "crop_type": "maize", "crop_stage": "vegetative", "soil_moisture": 0.42, "aez_zone": "II", "area_m2": 300, "lat": -17.81, "lon": 31.05},
        {"plot_id": "P2", "crop_type": "potato", "crop_stage": "tuber_init", "soil_moisture": 0.38, "aez_zone": "III", "area_m2": 260, "lat": -17.813, "lon": 31.056},
        {"plot_id": "P3", "crop_type": "sorghum", "crop_stage": "vegetative", "soil_moisture": 0.48, "aez_zone": "IV", "area_m2": 240, "lat": -17.816, "lon": 31.049},
        {"plot_id": "P4", "crop_type": "groundnut", "crop_stage": "flowering", "soil_moisture": 0.45, "aez_zone": "III", "area_m2": 180, "lat": -17.819, "lon": 31.054},
    ]


def default_scenario() -> Dict[str, Any]:
    return {
        "name": "default-zw-mixed-farm",
        "controls": {
            "days": 30,
            "mode": "dry_season",
            "water_budget": 1200,
            "base_temp": 30,
            "base_rain": 1.0,
            "variability": 2.0,
            "inject_demo_human_approval": False,
        },
        "farm": {
            "tank_level_liters": 12000,
            "daily_supply_limit_liters": 1800,
            "pump_capacity_lpm": 70,
            "plots": default_plot_catalog(),
        },
    }


@st.cache_data
def _seeded_weather(day: int, base_temp: float, base_rain: float, variability: float) -> Dict[str, float]:
    random.seed(1000 + day)
    temp = base_temp + random.uniform(-variability, variability)
    rain = max(0.0, base_rain + random.uniform(-variability, variability))
    humidity = min(90.0, max(25.0, 55.0 + random.uniform(-12.0, 12.0)))
    return {"temp": round(temp, 2), "rain": round(rain, 2), "humidity": round(humidity, 2)}


def scenario_to_state(scenario: Dict[str, Any]) -> FarmState:
    farm = scenario["farm"]
    return FarmState(
        timestamp=datetime(2026, 2, 22, 6, 0, 0),
        plots=[
            PlotState(
                plot_id=p["plot_id"],
                area_m2=float(p.get("area_m2", 200)),
                crop_type=p["crop_type"],
                crop_stage=p.get("crop_stage", "vegetative"),
                soil_moisture=float(p.get("soil_moisture", 0.4)),
                aez_zone=p.get("aez_zone", "III"),
            )
            for p in farm["plots"]
        ],
        water_system=WaterSystemState(
            tank_level_liters=float(farm["tank_level_liters"]),
            daily_supply_limit_liters=float(farm["daily_supply_limit_liters"]),
            pump_capacity_lpm=float(farm["pump_capacity_lpm"]),
        ),
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


def apply_approval_filter(orch: Dict[str, Any], approved: Dict[str, bool]) -> Dict[str, Any]:
    denied = []
    approved_required = []

    for i, action in enumerate(orch.get("approval_required", [])):
        key = f"{action.get('action_type')}::{action.get('target')}::{i}"
        ok = approved.get(key, False)
        action["approved"] = ok
        if ok:
            approved_required.append(action)
        else:
            denied.append(action)

    # Remove denied human-approval actions from queue
    if denied:
        for prio, actions in orch.get("action_queue", {}).items():
            orch["action_queue"][prio] = [
                a
                for a in actions
                if not any(
                    a.get("action_type") == d.get("action_type") and a.get("target") == d.get("target")
                    for d in denied
                )
            ]

    orch["approval_required"] = approved_required
    return orch


def maybe_inject_demo_human_approval(orch: Dict[str, Any]) -> Dict[str, Any]:
    demo = {
        "action_type": "spray_pesticide",
        "target": "P2",
        "params": {"chemical": "targeted-IPM", "wind_limit_ms": 4.0},
        "priority": "critical",
        "risk": "human_approval",
    }
    orch.setdefault("approval_required", []).append(demo)
    orch.setdefault("action_queue", {}).setdefault("critical", []).append(demo)
    return orch


st.header("🔄 Daily Farm Simulation")
st.caption("Run multi-day simulations with the orchestrator, AEZ-aware irrigation, and approval workflows.")


def render_initial_map(scenario: Dict[str, Any]) -> None:
    """Render plot map before simulation runs."""
    plots = scenario.get("farm", {}).get("plots", [])
    if not plots:
        return
    map_df = pd.DataFrame(plots)
    if "lat" not in map_df.columns or "lon" not in map_df.columns:
        st.warning("Plot coordinates (lat/lon) missing — map cannot render.")
        return
    scatter = (
        alt.Chart(map_df)
        .mark_circle(size=220)
        .encode(
            x=alt.X("lon:Q", title="Longitude"),
            y=alt.Y("lat:Q", title="Latitude"),
            color=alt.Color("soil_moisture:Q", title="Initial moisture", scale=alt.Scale(scheme="bluegreen")),
            tooltip=["plot_id", "crop_type", "aez_zone", "soil_moisture", "area_m2"],
        )
        .properties(height=320)
    )
    st.altair_chart(scatter, use_container_width=True)

loaded_scenario = default_scenario()
with st.sidebar:
    st.header("Scenario")
    uploaded = st.file_uploader("Load scenario JSON", type=["json"])
    if uploaded is not None:
        try:
            loaded_scenario = json.loads(uploaded.getvalue().decode("utf-8"))
            st.success(f"Loaded scenario: {loaded_scenario.get('name', 'unnamed')}")
        except Exception as e:  # pragma: no cover
            st.error(f"Invalid scenario JSON: {e}")
            loaded_scenario = default_scenario()

controls = loaded_scenario["controls"]

with st.sidebar:
    st.header("Simulation Controls")
    days = st.slider("Days", min_value=7, max_value=120, value=int(controls.get("days", 30)), step=1)
    mode = st.selectbox("Season Mode", options=["dry_season", "wet_season"], index=0 if controls.get("mode") == "dry_season" else 1)
    water_budget = st.number_input("Daily Water Budget (L)", min_value=200, max_value=5000, value=int(controls.get("water_budget", 1200)), step=50)
    base_temp = st.slider("Base Temperature (°C)", min_value=15, max_value=40, value=int(controls.get("base_temp", 30)))
    base_rain = st.slider("Base Rainfall (mm)", min_value=0.0, max_value=20.0, value=float(controls.get("base_rain", 1.0)), step=0.1)
    variability = st.slider("Weather Variability", min_value=0.0, max_value=8.0, value=float(controls.get("variability", 2.0)), step=0.2)
    inject_demo_human_approval = st.checkbox("Inject demo HUMAN_APPROVAL action", value=bool(controls.get("inject_demo_human_approval", False)))
    run = st.button("Run Simulation", type="primary")

# Scenario save block
scenario_payload = {
    "name": loaded_scenario.get("name", "custom-scenario"),
    "controls": {
        "days": days,
        "mode": mode,
        "water_budget": water_budget,
        "base_temp": base_temp,
        "base_rain": base_rain,
        "variability": variability,
        "inject_demo_human_approval": inject_demo_human_approval,
    },
    "farm": loaded_scenario.get("farm", default_scenario()["farm"]),
}
with st.expander("Save Scenario Preset"):
    st.download_button(
        "Download scenario JSON",
        data=json.dumps(scenario_payload, indent=2),
        file_name=f"{scenario_payload['name']}.json",
        mime="application/json",
    )
    st.code(json.dumps(scenario_payload, indent=2), language="json")

if run:
    orchestrator = FarmManagementOrchestrator()
    simulator = FarmSimulator()
    state = scenario_to_state(scenario_payload)

    rows = []
    alert_log = []
    latest_actions = {}
    latest_approval_required = []

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
        if inject_demo_human_approval:
            orch = maybe_inject_demo_human_approval(orch)

        # Manual approval UI state (per day)
        approvals = {}
        for i, action in enumerate(orch.get("approval_required", [])):
            key = f"{action.get('action_type')}::{action.get('target')}::{i}"
            approvals[key] = st.session_state.get(f"approve_{day}_{key}", False)
        orch = apply_approval_filter(orch, approvals)

        irrigation_plan = extract_irrigation_plan(orch["action_queue"])
        latest_actions = orch["action_queue"]
        latest_approval_required = orch.get("approval_required", [])

        state, decision, outcome = simulator.step(
            state=state,
            plan_by_plot=irrigation_plan,
            cycle_id=ctx.cycle_id,
            agent_id="orchestrator_irrigation",
            rationale="orchestrated multi-agent cycle",
            policy_version="orch-v2",
        )

        plot_snapshot = {p.plot_id: round(p.soil_moisture, 3) for p in state.plots}
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
                "plot_moisture": plot_snapshot,
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

    st.subheader("Per-plot cards")
    latest_m = df.iloc[-1]["plot_moisture"]
    card_cols = st.columns(len(state.plots))
    for idx, p in enumerate(state.plots):
        with card_cols[idx]:
            st.markdown(f"**{p.plot_id} · {p.crop_type.upper()}**")
            st.caption(f"AEZ {p.aez_zone} · {int(p.area_m2)} m²")
            st.metric("Soil Moisture", f"{latest_m.get(p.plot_id, 0):.2f}")

    st.subheader("Plot map view")
    map_df = pd.DataFrame(scenario_payload["farm"]["plots"])
    map_df["moisture"] = map_df["plot_id"].map(latest_m)
    scatter = (
        alt.Chart(map_df)
        .mark_circle(size=220)
        .encode(
            x=alt.X("lon:Q", title="Longitude"),
            y=alt.Y("lat:Q", title="Latitude"),
            color=alt.Color("moisture:Q", title="Soil moisture", scale=alt.Scale(scheme="bluegreen")),
            tooltip=["plot_id", "crop_type", "aez_zone", "moisture", "area_m2"],
        )
        .properties(height=320)
    )
    st.altair_chart(scatter, use_container_width=True)

    st.subheader("Manual action approvals (HUMAN_APPROVAL)")
    if latest_approval_required:
        st.warning("Review high-risk actions below. Re-run after setting approvals.")
        for i, action in enumerate(latest_approval_required):
            k = f"approve_{days}_{action.get('action_type')}::{action.get('target')}::{i}"
            st.checkbox(
                f"Approve {action.get('action_type')} on {action.get('target')} (risk={action.get('risk')})",
                key=k,
            )
            st.json(action)
    else:
        st.info("No HUMAN_APPROVAL actions generated in this run.")

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
    st.subheader("🗺️ Initial Plot Map")
    render_initial_map(scenario_payload)
