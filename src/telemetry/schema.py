"""
Canonical telemetry schema for the AgriMesh learning loop.

One schema for *all* domains (crops **and** livestock, plus water, maintenance,
security). A ``Transition`` is a single agent decision and its measured
consequence — an RL ``(s, a, r, s')`` tuple with provenance. An ``Episode``
groups the transitions of one simulated farm-season so end-of-season outcomes
(yield, profit, welfare) can be attributed back to the decisions that produced
them.

See ``docs/LEARNING_LOOP.md`` §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Bump when the shape of Transition/Episode changes so retraining stays
# reproducible. Records carry the version they were written under.
SCHEMA_VERSION = "tel-v1"


# Known domains. Kept as plain strings (not an Enum) so the store stays
# forward-compatible with domains added before this list is updated.
DOMAINS = ("crop", "livestock", "water", "maintenance", "security")


def new_id() -> str:
    """Short unique id for episodes/transitions."""
    return uuid4().hex[:12]


@dataclass
class Transition:
    """A single decision and its measured one-tick consequence.

    ``reward`` / ``reward_components`` are populated by ``src/telemetry/reward.py``
    (a later step); they default to a neutral 0.0 / empty so transitions can be
    captured now and labelled in a backfill pass.
    """

    # --- identity / provenance ---
    transition_id: str
    episode_id: str
    farm_id: str
    tick: int  # day index within the episode
    timestamp: datetime
    domain: str  # one of DOMAINS
    agent_id: str
    policy_version: str

    # --- the decision ---
    decision_type: str  # e.g. "irrigate", "feed_livestock", "water_livestock"
    action: str  # discrete label
    parameters: Dict[str, Any] = field(default_factory=dict)

    # --- state before / after + surrounding context ---
    state_before: Dict[str, Any] = field(default_factory=dict)
    state_after: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    # --- the label (backfilled by the reward layer) ---
    outcome: Dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    reward_components: Dict[str, float] = field(default_factory=dict)

    # --- guardrails / autonomy metadata ---
    risk_level: str = "NORMAL"  # NORMAL | HIGH | HUMAN_APPROVAL
    approved_by: Optional[str] = None  # "auto" vs a human id (matters at L2+)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = new_id()


@dataclass
class Episode:
    """Header for one simulated farm-season run."""

    episode_id: str
    farm_id: str
    farm_config: Dict[str, Any] = field(default_factory=dict)
    weather_scenario: str = ""  # e.g. "harare_2019_dry", "synthetic_drought_p90"
    season_mode: str = ""  # wet_season | dry_season
    policy_bundle: Dict[str, str] = field(default_factory=dict)  # {decision_type: policy_version}
    n_ticks: int = 0
    season_outcome: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.episode_id:
            self.episode_id = new_id()


# Fields serialised as JSON text in the store (everything dict/list-shaped).
TRANSITION_JSON_FIELDS = (
    "parameters",
    "state_before",
    "state_after",
    "context",
    "outcome",
    "reward_components",
)

EPISODE_JSON_FIELDS = (
    "farm_config",
    "policy_bundle",
    "season_outcome",
)
