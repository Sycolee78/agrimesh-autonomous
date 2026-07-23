"""
Adapters: existing log shapes → canonical ``Transition`` records.

The point of these adapters is *capture without rewrite*. The simulator already
returns ``DecisionLog`` + ``OutcomeLog`` from every ``step()``, and the
orchestrator already logs ``Decision`` rows; these functions turn that existing
signal into ``Transition``s the learning loop can train on, without touching the
callers that produce it.

Rewards are left neutral here — ``src/telemetry/reward.py`` (a later step)
backfills ``reward`` / ``reward_components`` / ``outcome`` once the objectives
are signed off. See ``docs/LEARNING_LOOP.md`` §4, §6.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.telemetry.schema import Transition, new_id


def transitions_from_sim_step(
    episode_id: str,
    tick: int,
    decision_log: Any,  # src.common.models.DecisionLog
    outcome_log: Any,  # src.common.models.OutcomeLog
    *,
    farm_id: str = "sim-farm",
    timestamp: Optional[datetime] = None,
    context: Optional[Dict[str, Any]] = None,
    plot_meta: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Transition]:
    """Convert one simulator ``step()`` into per-plot crop irrigation transitions.

    The sim packs its decision as
    ``action_plan={"irrigation_by_plot_liters": {plot_id: liters}}`` and its
    result as ``actual_changes`` carrying ``soil_moisture_before`` /
    ``soil_moisture_after`` per plot. We emit one transition per plot so each
    plot's irrigation decision is independently learnable.

    ``plot_meta`` (optional) carries per-plot descriptors known to the caller at
    decision time — ``crop_type``, ``target_moisture``, ``critical_threshold``,
    ``day_of_season`` — merged into each transition's context so the reward layer
    can label it without re-deriving crop models. Makes transitions
    self-describing and reproducible.
    """
    ts = timestamp or datetime.now()
    ctx = dict(context or {})
    meta = plot_meta or {}

    plan = decision_log.action_plan.get("irrigation_by_plot_liters", {})
    changes = outcome_log.actual_changes or {}
    before = changes.get("soil_moisture_before", {})
    after = changes.get("soil_moisture_after", {})
    kpi_delta = outcome_log.kpi_delta or {}

    # Plots that were planned or that we have before/after readings for.
    plot_ids = set(plan) | set(before) | set(after)

    return [
        _build_crop_transition(
            episode_id, tick, ts, farm_id, decision_log, plot_id,
            float(plan.get(plot_id, 0.0)),
            before.get(plot_id), after.get(plot_id), changes, kpi_delta,
            {**ctx, **meta.get(plot_id, {})},
        )
        for plot_id in sorted(plot_ids)
    ]


def _build_crop_transition(
    episode_id: str,
    tick: int,
    ts: datetime,
    farm_id: str,
    decision_log: Any,
    plot_id: str,
    liters: float,
    moisture_before: Optional[float],
    moisture_after: Optional[float],
    changes: Dict[str, Any],
    kpi_delta: Dict[str, Any],
    ctx: Dict[str, Any],
) -> Transition:
    return Transition(
        transition_id=new_id(),
        episode_id=episode_id,
        farm_id=farm_id,
        tick=tick,
        timestamp=ts,
        domain="crop",
        agent_id=decision_log.agent_id,
        policy_version=decision_log.policy_version,
        decision_type="irrigate",
        action="irrigate" if liters > 0 else "no_irrigate",
        parameters={"plot_id": plot_id, "liters": round(liters, 2)},
        state_before={"soil_moisture": moisture_before},
        state_after={"soil_moisture": moisture_after},
        context={
            **ctx,
            "cycle_id": decision_log.cycle_id,
            "rationale": decision_log.rationale,
        },
        outcome={
            "soil_moisture_delta": _delta(moisture_before, moisture_after),
            "liters_applied": round(liters, 2),
            "tank_level_liters": changes.get("tank_level_liters"),
            "water_use_efficiency": kpi_delta.get("water_use_efficiency"),
        },
    )


def transition_from_decision(
    episode_id: str,
    tick: int,
    decision: Any,  # src.common.decision_logger.Decision
    *,
    farm_id: str = "sim-farm",
    domain: str = "crop",
    policy_version: str = "unknown",
) -> Transition:
    """Convert an orchestrator ``Decision`` row into a ``Transition``.

    Used for the orchestrator path (livestock, maintenance, security, water),
    where decisions are logged via ``src/common/decision_logger.py`` rather than
    produced by the crop sim ``step()``.
    """
    outcome: Dict[str, Any] = {}
    if decision.outcome is not None:
        outcome["outcome"] = decision.outcome
    if decision.outcome_value is not None:
        outcome["outcome_value"] = decision.outcome_value

    return Transition(
        transition_id=new_id(),
        episode_id=episode_id,
        farm_id=farm_id,
        tick=tick,
        timestamp=decision.timestamp,
        domain=domain,
        agent_id=decision.agent_id,
        policy_version=policy_version,
        decision_type=decision.decision_type,
        action=decision.action,
        parameters=dict(decision.parameters or {}),
        state_before=dict(decision.context or {}),
        state_after={},
        context={"agent_name": decision.agent_name},
        outcome=outcome,
        risk_level="NORMAL",
        approved_by=None,
    )


def _delta(before: Optional[float], after: Optional[float]) -> Optional[float]:
    if before is None or after is None:
        return None
    return round(after - before, 4)
