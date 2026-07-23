"""Tests for the experience data factory and the reward labelling layer."""

from __future__ import annotations

from src.sim.experience import FarmConfig, generate_experience, run_episode
from src.telemetry import TelemetryStore
from src.telemetry.reward import RewardConfig, compute_reward, label_store


def test_run_episode_captures_transitions(tmp_path):
    store = TelemetryStore(str(tmp_path / "tel.db"))
    ep_id = run_episode(
        store,
        FarmConfig(farm_id="f1", crops=["maize", "potato"], initial_moisture=0.30),
        weather_scenario="dry",
        policy_name="rule",
        days=10,
    )
    # 2 plots x 10 days
    transitions = store.query_transitions(episode_id=ep_id)
    assert len(transitions) == 20
    # transitions are self-describing: crop metadata rode along in context
    t = transitions[0]
    assert t.context["crop_type"] in ("maize", "potato")
    assert "target_moisture" in t.context
    assert "critical_threshold" in t.context

    episode = store.get_episode(ep_id)
    assert episode.n_ticks == 10
    assert "yield_estimate_tons_per_ha" in episode.season_outcome


def test_generate_experience_batch(tmp_path):
    store = TelemetryStore(str(tmp_path / "tel.db"))
    ids = generate_experience(store, n_episodes=8, days=15, seed=7)
    assert len(ids) == 8
    assert store.count_transitions() > 0


def test_labelling_and_water_efficiency(tmp_path):
    store = TelemetryStore(str(tmp_path / "tel.db"))
    run_episode(store, FarmConfig(farm_id="f1", initial_moisture=0.30),
                weather_scenario="dry", policy_name="rule", days=12)

    # before labelling, training export is empty (reward gate)
    assert store.export_for_training("irrigate", require_reward=True) == []

    n = label_store(store, RewardConfig.water_efficiency())
    assert n > 0
    rows = store.export_for_training("irrigate", require_reward=True)
    assert len(rows) == n
    assert all("reward" in r and "reward_components" in r for r in rows)


def test_water_cost_penalizes_more_under_efficiency():
    """A transition that used water should score lower under the water-thrift
    objective than under the absolute-yield objective (which ignores water)."""
    from datetime import datetime
    from src.telemetry.schema import Transition

    t = Transition(
        transition_id="t1", episode_id="e1", farm_id="f1", tick=0,
        timestamp=datetime.now(), domain="crop", agent_id="a", policy_version="p",
        decision_type="irrigate", action="irrigate",
        parameters={"plot_id": "P1", "liters": 800.0},
        state_before={"soil_moisture": 0.40}, state_after={"soil_moisture": 0.62},
        context={"crop_type": "maize", "target_moisture": 0.60, "critical_threshold": 0.35},
        outcome={"liters_applied": 800.0},
    )
    eff, _ = compute_reward(t, RewardConfig.water_efficiency())
    yld, _ = compute_reward(t, RewardConfig.absolute_yield())
    assert eff < yld  # water thrift penalizes the 800 L; absolute-yield does not


def test_livestock_water_shortfall_is_catastrophic():
    from datetime import datetime
    from src.telemetry.schema import Transition

    t = Transition(
        transition_id="t2", episode_id="e1", farm_id="f1", tick=0,
        timestamp=datetime.now(), domain="livestock", agent_id="a", policy_version="p",
        decision_type="water_livestock", action="water_livestock",
        outcome={"unmet_liters": 5.0},
    )
    reward, components = compute_reward(t, RewardConfig())
    assert reward < -100  # unmet livestock water is a hard, catastrophic penalty
    assert "water_shortfall" in components
