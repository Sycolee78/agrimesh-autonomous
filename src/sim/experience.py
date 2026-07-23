"""
Experience generation — the AgriMesh "data factory".

Runs the deterministic crop simulator over a matrix of
``(farm config × weather scenario × season × policy)`` and captures every day's
``(state, action, next_state, outcome)`` transition into the telemetry store.
In simulation-only mode this is how the learning loop gets its training data at
scale, RL-gym style: better policies produce better episodes, which train better
policies.

See ``docs/LEARNING_LOOP.md`` §2.

CLI::

    python -m src.sim.experience --episodes 50 --days 60
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.agents.irrigation.policies import (
    BaselineFixedSchedulePolicy,
    GrowthStageAwarePolicy,
    RuleBasedIrrigationPolicy,
)
from src.common.models import (
    FarmState,
    KPIState,
    PlotState,
    WaterSystemState,
    WeatherState,
)
from src.sim.environment import FarmSimulator
from src.sim.yield_model import get_critical_threshold, get_target_moisture
from src.telemetry import Episode, TelemetryStore, new_id
from src.telemetry.adapters import transitions_from_sim_step


# Named weather scenarios give episode diversity without hitting the weather API.
WEATHER_SCENARIOS: Dict[str, WeatherState] = {
    "normal": WeatherState(temperature_c=27, humidity_pct=60, rainfall_mm=3.0),
    "dry": WeatherState(temperature_c=32, humidity_pct=40, rainfall_mm=0.0),
    "drought": WeatherState(temperature_c=35, humidity_pct=30, rainfall_mm=0.0),
    "wet": WeatherState(temperature_c=24, humidity_pct=80, rainfall_mm=14.0),
}

POLICIES = {
    "baseline": lambda: BaselineFixedSchedulePolicy(liters_per_plot=120),
    "rule": lambda: RuleBasedIrrigationPolicy(),
    "growth_stage": lambda: GrowthStageAwarePolicy(),
}

CROP_ROTATION = ["maize", "potato", "sorghum", "groundnut"]
AEZ_ZONES = ["I", "IIa", "IIb", "III", "IV", "V"]


@dataclass
class FarmConfig:
    """Minimal spec for one simulated farm."""

    farm_id: str
    aez_zone: str = "III"
    crops: List[str] = field(default_factory=lambda: ["maize", "maize"])
    plot_area_m2: float = 300.0
    initial_moisture: float = 0.45
    tank_liters: float = 8000.0
    daily_supply_limit: float = 1200.0

    def to_state(self, weather: WeatherState) -> FarmState:
        plots = [
            PlotState(
                plot_id=f"P{i+1}",
                area_m2=self.plot_area_m2,
                crop_type=crop,
                crop_stage="vegetative",
                soil_moisture=self.initial_moisture,
                aez_zone=self.aez_zone,
            )
            for i, crop in enumerate(self.crops)
        ]
        return FarmState(
            timestamp=datetime(2026, 1, 1, 6, 0, 0),
            plots=plots,
            water_system=WaterSystemState(
                tank_level_liters=self.tank_liters,
                daily_supply_limit_liters=self.daily_supply_limit,
                pump_capacity_lpm=65,
            ),
            weather=weather,
            kpis=KPIState(),
        )


def run_episode(
    store: TelemetryStore,
    config: FarmConfig,
    weather_scenario: str = "normal",
    policy_name: str = "rule",
    season_mode: str = "dry_season",
    days: int = 60,
) -> str:
    """Run one farm-season, capturing transitions. Returns the ``episode_id``."""
    weather = WEATHER_SCENARIOS[weather_scenario]
    state = config.to_state(weather)
    sim = FarmSimulator()
    actor = POLICIES[policy_name]()

    episode = Episode(
        episode_id=new_id(),
        farm_id=config.farm_id,
        farm_config={
            "aez_zone": config.aez_zone,
            "crops": config.crops,
            "plot_area_m2": config.plot_area_m2,
            "tank_liters": config.tank_liters,
        },
        weather_scenario=weather_scenario,
        season_mode=season_mode,
        policy_bundle={"irrigate": actor.policy_version},
    )
    store.write_episode(episode)

    for day in range(days):
        cycle_id = f"day-{day+1:03d}"
        # Per-plot descriptors known at decision time -> self-describing transitions.
        plot_meta = {
            p.plot_id: {
                "crop_type": p.crop_type,
                "aez_zone": p.aez_zone,
                "day_of_season": p.day_of_season,
                "target_moisture": round(get_target_moisture(p.crop_type, p.day_of_season), 3),
                "critical_threshold": round(get_critical_threshold(p.crop_type), 3),
            }
            for p in state.plots
        }
        plan, rationale = actor.decide(state, cycle_id)
        state, decision_log, outcome_log = sim.step(
            state=state,
            plan_by_plot=plan.irrigation_by_plot_liters,
            cycle_id=cycle_id,
            agent_id=plan.agent_id,
            rationale=rationale,
            policy_version=actor.policy_version,
        )
        store.write_transitions(
            transitions_from_sim_step(
                episode.episode_id,
                tick=day,
                decision_log=decision_log,
                outcome_log=outcome_log,
                farm_id=config.farm_id,
                timestamp=state.timestamp,
                context={"season_mode": season_mode, "weather_scenario": weather_scenario},
                plot_meta=plot_meta,
            )
        )

    # Season-level outcome for episodic credit assignment later.
    episode.n_ticks = days
    episode.season_outcome = {
        "crop_stress_events_total": state.kpis.crop_stress_events,
        "water_use_efficiency": round(state.kpis.water_use_efficiency, 4),
        "yield_estimate_tons_per_ha": round(state.kpis.yield_estimate_tons_per_ha, 3),
    }
    store.write_episode(episode)
    return episode.episode_id


def generate_experience(
    store: TelemetryStore,
    n_episodes: int = 50,
    days: int = 60,
    policies: Optional[List[str]] = None,
    seed: int = 42,
) -> List[str]:
    """Generate a diverse batch of episodes across the config matrix."""
    import random

    rng = random.Random(seed)
    policies = policies or list(POLICIES.keys())
    scenarios = list(WEATHER_SCENARIOS.keys())
    seasons = ["dry_season", "wet_season"]

    episode_ids: List[str] = []
    for i in range(n_episodes):
        aez = rng.choice(AEZ_ZONES)
        crops = [rng.choice(CROP_ROTATION) for _ in range(rng.randint(1, 3))]
        config = FarmConfig(
            farm_id=f"farm-{i:04d}",
            aez_zone=aez,
            crops=crops,
            initial_moisture=round(rng.uniform(0.25, 0.55), 2),
            tank_liters=rng.choice([5000.0, 8000.0, 12000.0]),
        )
        episode_ids.append(
            run_episode(
                store,
                config=config,
                weather_scenario=rng.choice(scenarios),
                policy_name=rng.choice(policies),
                season_mode=rng.choice(seasons),
                days=days,
            )
        )
    return episode_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AgriMesh experience data")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--db", type=str, default="logs/telemetry.db")
    parser.add_argument("--label", action="store_true", help="backfill rewards after generation")
    args = parser.parse_args()

    store = TelemetryStore(args.db)
    ids = generate_experience(store, n_episodes=args.episodes, days=args.days)
    print(f"Generated {len(ids)} episodes, {store.count_transitions()} transitions -> {args.db}")

    if args.label:
        from src.telemetry.reward import label_store

        n = label_store(store)
        print(f"Labelled {n} transitions with rewards")


if __name__ == "__main__":
    main()
