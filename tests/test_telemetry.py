"""Smoke + round-trip tests for the telemetry capture layer."""

from __future__ import annotations

from datetime import datetime

from src.common.models import (
    FarmState,
    KPIState,
    PlotState,
    WaterSystemState,
    WeatherState,
)
from src.sim.environment import FarmSimulator
from src.telemetry import Episode, TelemetryStore
from src.telemetry.adapters import transitions_from_sim_step


def _state() -> FarmState:
    return FarmState(
        timestamp=datetime(2026, 2, 20, 6, 0, 0),
        plots=[
            PlotState(plot_id="P1", area_m2=300, crop_type="maize",
                      crop_stage="vegetative", soil_moisture=0.30),
            PlotState(plot_id="P2", area_m2=260, crop_type="maize",
                      crop_stage="vegetative", soil_moisture=0.55),
        ],
        water_system=WaterSystemState(
            tank_level_liters=8000, daily_supply_limit_liters=1200, pump_capacity_lpm=65),
        weather=WeatherState(temperature_c=29, humidity_pct=58, rainfall_mm=1.5),
        kpis=KPIState(),
    )


def test_store_roundtrip(tmp_path):
    store = TelemetryStore(str(tmp_path / "tel.db"))
    ep = Episode(episode_id="", farm_id="f1", weather_scenario="test",
                 season_mode="dry_season", policy_bundle={"irrigate": "rule-v1"})
    store.write_episode(ep)

    sim = FarmSimulator()
    _, decision_log, outcome_log = sim.step(
        _state(),
        plan_by_plot={"P1": 300.0, "P2": 0.0},
        cycle_id="c1", agent_id="irrigation", rationale="dry P1",
        policy_version="rule-v1",
    )

    transitions = transitions_from_sim_step(
        ep.episode_id, tick=0, decision_log=decision_log, outcome_log=outcome_log,
        farm_id="f1", context={"aez_zone": "III", "season_mode": "dry_season"},
    )

    # one transition per plot
    assert len(transitions) == 2
    ids = store.write_transitions(transitions)
    assert len(ids) == 2
    assert store.count_transitions() == 2

    # P1 was irrigated, P2 was not
    by_plot = {t.parameters["plot_id"]: t for t in transitions}
    assert by_plot["P1"].action == "irrigate"
    assert by_plot["P2"].action == "no_irrigate"

    # round-trip preserves structure and measured outcome
    loaded = store.query_transitions(episode_id=ep.episode_id, decision_type="irrigate")
    assert len(loaded) == 2
    p1 = next(t for t in loaded if t.parameters["plot_id"] == "P1")
    assert p1.domain == "crop"
    assert p1.context["aez_zone"] == "III"
    assert p1.outcome["liters_applied"] == 300.0
    assert p1.outcome["soil_moisture_delta"] is not None
    assert isinstance(p1.timestamp, datetime)

    assert store.get_episode(ep.episode_id).farm_id == "f1"


def test_export_requires_reward(tmp_path):
    store = TelemetryStore(str(tmp_path / "tel.db"))
    ep = Episode(episode_id="", farm_id="f1")
    store.write_episode(ep)
    sim = FarmSimulator()
    _, d, o = sim.step(_state(), {"P1": 300.0, "P2": 100.0}, "c1", "irrigation",
                       "r", "rule-v1")
    store.write_transitions(
        transitions_from_sim_step(ep.episode_id, 0, d, o, farm_id="f1"))

    # nothing labelled yet -> excluded when reward is required
    assert store.export_for_training("irrigate", require_reward=True) == []
    assert len(store.export_for_training("irrigate", require_reward=False)) == 2
