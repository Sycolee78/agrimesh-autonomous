"""
Reward / outcome labelling for the AgriMesh learning loop.

Turns the raw, measured ``outcome`` on each ``Transition`` into a scalar
``reward`` (plus a component breakdown) that a policy learner can optimize.
Capture (``adapters.py``) and labelling (here) are deliberately separate so the
objective can change without re-running simulations — just re-label.

Defaults are **not arbitrary**; they encode the repository's own stated
principles (see ``CLAUDE.md`` and ``docs/LEARNING_LOOP.md`` §4):

- Positioning leads with "smart irrigation + yield optimization" and 96% water
  savings → irrigation defaults to a **water-use-efficiency** objective
  (reward moisture progress toward target, penalize water spent and overshoot).
- Water-security and animal welfare are "non-negotiable ... hard constraints,
  not optimization targets" → livestock water shortfall carries a
  **catastrophic** penalty a learned policy cannot trade away.

Every weight lives on ``RewardConfig`` and can be overridden in one place. To
optimize absolute yield instead of water-thrift, use
``RewardConfig.absolute_yield()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.telemetry.schema import Transition


@dataclass
class RewardConfig:
    """Tunable objective weights. Defaults = water-use-efficiency + hard floors."""

    # --- irrigation (crop) ---
    w_moisture_progress: float = 1.0   # reward closing the gap to target moisture
    w_water_cost: float = 0.5          # penalty per 1000 L applied (thrift lever)
    w_overshoot: float = 0.8           # penalty for pushing moisture above target (waste)
    w_stress: float = 2.0              # penalty for ending below the crop's critical floor
    default_target_moisture: float = 0.60
    default_critical_threshold: float = 0.35

    # --- livestock water (welfare / water-security hard constraint) ---
    livestock_unmet_penalty: float = 1000.0  # catastrophic; per unit of unmet demand
    catastrophic_floor: bool = True

    @classmethod
    def water_efficiency(cls) -> "RewardConfig":
        """Explicit constructor for the default (water-thrift) objective."""
        return cls()

    @classmethod
    def absolute_yield(cls) -> "RewardConfig":
        """Optimize hitting the moisture target regardless of water spent."""
        return cls(w_water_cost=0.0, w_overshoot=0.0)


def compute_reward(
    transition: Transition, config: Optional[RewardConfig] = None
) -> Tuple[float, Dict[str, float]]:
    """Return ``(reward, reward_components)`` for a transition.

    Dispatches on ``decision_type``. Unknown types get a neutral 0.0 so the
    store stays labellable end-to-end even before every domain has an objective.
    """
    cfg = config or RewardConfig()
    dtype = transition.decision_type

    if dtype == "irrigate":
        return _irrigation_reward(transition, cfg)
    if dtype in ("water_livestock", "restore_livestock_water"):
        return _livestock_water_reward(transition, cfg)
    return 0.0, {}


def _irrigation_reward(
    t: Transition, cfg: RewardConfig
) -> Tuple[float, Dict[str, float]]:
    ctx = t.context or {}
    outcome = t.outcome or {}

    m_before = _num(t.state_before.get("soil_moisture"))
    m_after = _num(t.state_after.get("soil_moisture"))
    target = _num(ctx.get("target_moisture"), cfg.default_target_moisture)
    critical = _num(ctx.get("critical_threshold"), cfg.default_critical_threshold)
    liters = _num(outcome.get("liters_applied"), 0.0)

    # Progress: distance to target closed *from below* (getting drier plots wetter).
    dist_before = max(0.0, target - m_before)
    dist_after = max(0.0, target - m_after)
    progress = dist_before - dist_after

    # Overshoot: moisture pushed above target is wasted water.
    overshoot = max(0.0, m_after - target)

    # Stress: ending below the crop's critical floor is bad regardless of water.
    stress = 1.0 if m_after < critical else 0.0

    water_cost = liters / 1000.0

    components = {
        "moisture_progress": round(cfg.w_moisture_progress * progress, 4),
        "water_cost": round(-cfg.w_water_cost * water_cost, 4),
        "overshoot": round(-cfg.w_overshoot * overshoot, 4),
        "stress": round(-cfg.w_stress * stress, 4),
    }
    reward = round(sum(components.values()), 4)
    return reward, components


def _livestock_water_reward(
    t: Transition, cfg: RewardConfig
) -> Tuple[float, Dict[str, float]]:
    """Welfare/water-security: any unmet demand is catastrophic by default.

    Reads ``outcome['unmet_liters']`` (or ``unmet``) — populated once the
    livestock sim sub-step exists. Until then this yields a neutral 0.0, so the
    function is ready without fabricating a signal.
    """
    outcome = t.outcome or {}
    unmet = _num(outcome.get("unmet_liters", outcome.get("unmet")), 0.0)

    if unmet <= 0:
        return 0.0, {"welfare_ok": 0.0}

    penalty = -cfg.livestock_unmet_penalty * (unmet if cfg.catastrophic_floor else min(unmet, 1.0))
    return round(penalty, 4), {"water_shortfall": round(penalty, 4)}


def label_store(store, config: Optional[RewardConfig] = None, only_unlabelled: bool = True) -> int:
    """Backfill rewards onto stored transitions. Returns the count labelled.

    Idempotent: re-running with a different ``RewardConfig`` re-labels the same
    transitions with the new objective (that's the point of separating capture
    from labelling).
    """
    cfg = config or RewardConfig()
    labelled = 0
    for t in store.query_transitions():
        if only_unlabelled and t.reward_components:
            continue
        reward, components = compute_reward(t, cfg)
        if not components:
            continue
        store.update_reward(t.transition_id, reward, components)
        labelled += 1
    return labelled


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
