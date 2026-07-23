"""
AgriMesh telemetry: canonical decision/outcome capture for the learning loop.

This package turns the signal the simulator already produces
(``DecisionLog`` + ``OutcomeLog`` per step) into a persistent, queryable,
trainable store of ``Transition`` records — the raw material for retraining
the policies that drive the orchestrator.

See ``docs/LEARNING_LOOP.md`` for the design.

Typical use::

    from src.telemetry import Episode, Transition, TelemetryStore
    from src.telemetry.adapters import transitions_from_sim_step

    store = TelemetryStore("logs/telemetry.db")
    store.write_episode(episode)
    store.write_transitions(
        transitions_from_sim_step(episode.episode_id, tick, decision_log,
                                  outcome_log, state_before, state_after)
    )
"""

from __future__ import annotations

from src.telemetry.schema import (
    SCHEMA_VERSION,
    Episode,
    Transition,
    new_id,
)
from src.telemetry.store import TelemetryStore

__all__ = [
    "SCHEMA_VERSION",
    "Episode",
    "Transition",
    "TelemetryStore",
    "new_id",
]
