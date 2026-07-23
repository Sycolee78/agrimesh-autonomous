"""
Append-only telemetry store for the AgriMesh learning loop.

SQLite-backed (matches the existing decision loggers; a Parquet export path can
be added later for bulk training pulls). Writes are append-only — transitions are
immutable facts, except for a labelling pass that backfills ``reward`` /
``outcome`` computed by ``src/telemetry/reward.py``.

See ``docs/LEARNING_LOOP.md`` §3.3.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from src.telemetry.schema import (
    EPISODE_JSON_FIELDS,
    TRANSITION_JSON_FIELDS,
    Episode,
    Transition,
)


class TelemetryStore:
    """Persist and query ``Episode`` / ``Transition`` records."""

    def __init__(self, db_path: str = "logs/telemetry.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id       TEXT PRIMARY KEY,
                    farm_id          TEXT NOT NULL,
                    farm_config      TEXT NOT NULL,
                    weather_scenario TEXT,
                    season_mode      TEXT,
                    policy_bundle    TEXT NOT NULL,
                    n_ticks          INTEGER NOT NULL DEFAULT 0,
                    season_outcome   TEXT NOT NULL,
                    created_at       TEXT NOT NULL,
                    schema_version   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transitions (
                    transition_id    TEXT PRIMARY KEY,
                    episode_id       TEXT NOT NULL,
                    farm_id          TEXT NOT NULL,
                    tick             INTEGER NOT NULL,
                    timestamp        TEXT NOT NULL,
                    domain           TEXT NOT NULL,
                    agent_id         TEXT NOT NULL,
                    policy_version   TEXT NOT NULL,
                    decision_type    TEXT NOT NULL,
                    action           TEXT NOT NULL,
                    parameters       TEXT NOT NULL,
                    state_before     TEXT NOT NULL,
                    state_after      TEXT NOT NULL,
                    context          TEXT NOT NULL,
                    outcome          TEXT NOT NULL,
                    reward           REAL NOT NULL DEFAULT 0.0,
                    reward_components TEXT NOT NULL,
                    risk_level       TEXT NOT NULL,
                    approved_by      TEXT,
                    schema_version   TEXT NOT NULL,
                    FOREIGN KEY (episode_id) REFERENCES episodes(episode_id)
                );

                CREATE INDEX IF NOT EXISTS idx_tr_episode
                    ON transitions(episode_id);
                CREATE INDEX IF NOT EXISTS idx_tr_decision_type
                    ON transitions(decision_type);
                CREATE INDEX IF NOT EXISTS idx_tr_domain
                    ON transitions(domain);
                """
            )
            conn.commit()

    # ------------------------------------------------------------------ write

    def write_episode(self, episode: Episode) -> str:
        """Insert (or replace) an episode header. Returns ``episode_id``."""
        row = self._episode_to_row(episode)
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO episodes (
                    episode_id, farm_id, farm_config, weather_scenario,
                    season_mode, policy_bundle, n_ticks, season_outcome,
                    created_at, schema_version
                ) VALUES (
                    :episode_id, :farm_id, :farm_config, :weather_scenario,
                    :season_mode, :policy_bundle, :n_ticks, :season_outcome,
                    :created_at, :schema_version
                )
                """,
                row,
            )
            conn.commit()
        return episode.episode_id

    def write_transition(self, transition: Transition) -> str:
        """Append a single transition. Returns ``transition_id``."""
        return self.write_transitions([transition])[0]

    def write_transitions(self, transitions: Iterable[Transition]) -> List[str]:
        """Append a batch of transitions. Returns their ids."""
        rows = [self._transition_to_row(t) for t in transitions]
        if not rows:
            return []
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO transitions (
                    transition_id, episode_id, farm_id, tick, timestamp, domain,
                    agent_id, policy_version, decision_type, action, parameters,
                    state_before, state_after, context, outcome, reward,
                    reward_components, risk_level, approved_by, schema_version
                ) VALUES (
                    :transition_id, :episode_id, :farm_id, :tick, :timestamp, :domain,
                    :agent_id, :policy_version, :decision_type, :action, :parameters,
                    :state_before, :state_after, :context, :outcome, :reward,
                    :reward_components, :risk_level, :approved_by, :schema_version
                )
                """,
                rows,
            )
            conn.commit()
        return [r["transition_id"] for r in rows]

    def update_reward(
        self,
        transition_id: str,
        reward: float,
        reward_components: Optional[Dict[str, float]] = None,
        outcome: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Backfill the label computed by the reward layer."""
        sets = ["reward = ?"]
        params: List[Any] = [reward]
        if reward_components is not None:
            sets.append("reward_components = ?")
            params.append(json.dumps(reward_components))
        if outcome is not None:
            sets.append("outcome = ?")
            params.append(json.dumps(outcome))
        params.append(transition_id)
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE transitions SET {', '.join(sets)} WHERE transition_id = ?",
                params,
            )
            conn.commit()

    # ------------------------------------------------------------------- read

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM episodes WHERE episode_id = ?", (episode_id,)
            ).fetchone()
        return self._row_to_episode(row) if row else None

    def query_transitions(
        self,
        episode_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Transition]:
        conditions: List[str] = []
        params: List[Any] = []
        if episode_id:
            conditions.append("episode_id = ?")
            params.append(episode_id)
        if decision_type:
            conditions.append("decision_type = ?")
            params.append(decision_type)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM transitions WHERE {where} "
                f"ORDER BY episode_id, tick LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_transition(r) for r in rows]

    def count_transitions(self) -> int:
        with self._get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM transitions").fetchone()[0]

    def export_for_training(
        self,
        decision_type: str,
        require_reward: bool = True,
    ) -> List[Dict[str, Any]]:
        """Tidy rows for a model trainer: features-in / action / label-out.

        ``require_reward`` drops transitions the reward layer has not labelled
        yet (reward defaults to 0.0 and no components).
        """
        rows: List[Dict[str, Any]] = []
        for t in self.query_transitions(decision_type=decision_type):
            if require_reward and not t.reward_components:
                continue
            rows.append(
                {
                    "state_before": t.state_before,
                    "context": t.context,
                    "action": t.action,
                    "parameters": t.parameters,
                    "reward": t.reward,
                    "reward_components": t.reward_components,
                    "outcome": t.outcome,
                }
            )
        return rows

    # ---------------------------------------------------------- (de)serialise

    @staticmethod
    def _transition_to_row(t: Transition) -> Dict[str, Any]:
        row = asdict(t)
        for f in TRANSITION_JSON_FIELDS:
            row[f] = json.dumps(row[f])
        row["timestamp"] = (
            t.timestamp.isoformat() if isinstance(t.timestamp, datetime) else t.timestamp
        )
        return row

    @staticmethod
    def _row_to_transition(row: sqlite3.Row) -> Transition:
        data = dict(row)
        for f in TRANSITION_JSON_FIELDS:
            data[f] = json.loads(data[f])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return Transition(**data)

    @staticmethod
    def _episode_to_row(e: Episode) -> Dict[str, Any]:
        row = asdict(e)
        for f in EPISODE_JSON_FIELDS:
            row[f] = json.dumps(row[f])
        row["created_at"] = (
            e.created_at.isoformat() if isinstance(e.created_at, datetime) else e.created_at
        )
        return row

    @staticmethod
    def _row_to_episode(row: sqlite3.Row) -> Episode:
        data = dict(row)
        for f in EPISODE_JSON_FIELDS:
            data[f] = json.loads(data[f])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return Episode(**data)
