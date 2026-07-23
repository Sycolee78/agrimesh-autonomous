# AgriMesh — Learning Loop & Telemetry Schema (deep-dive)

> First deep-dive from the [Masterplan](./MASTERPLAN.md). Mode: **simulation-only**.
> Scope: **crops + livestock**. Goal: turn the simulator into a *data factory*
> whose decision/outcome logs continuously retrain the models that drive the
> orchestrator — a closed **perceive → decide → act → learn** loop, entirely in sim.
>
> Status: **design for review**. Modeling choices needing sign-off are in §7 🟠.

---

## 1. The problem, precisely

Two halves of a learning loop exist but never connect, and the loop never closes:

- **Operational logging** (`src/common/decision_logger.py`) records
  `context → action → outcome`, and even exposes `export_for_training()` — but
  `outcome_value` is almost never written back. Nothing observes *what happened
  after* a decision, so there is no supervised signal from operation.
- **ML training** (`src/ml/training/data_generator.py`) learns from **synthetic
  site→yield data**. That is a *spatial* recommender ("what to plant where"),
  not an *operational* learner ("did today's irrigation work?").
- The simulator (`src/sim/environment.py`) **already returns the raw signal** —
  `step()` yields `(next_state, DecisionLog, OutcomeLog)`, i.e. a full
  `(state, action, next_state, outcome)` transition — but it is discarded after
  each run instead of being captured into a persistent, trainable store. It also
  only simulates **crops/irrigation**; livestock is not in the step yet.

**So the closed loop is ~70% built and disconnected.** This deep-dive defines the
missing connective tissue: a canonical telemetry schema, an outcome/reward layer,
a curation→training→evaluation→deployment pipeline, and the sim harness that mass-
produces labeled episodes for both crops and livestock.

---

## 2. Target: the simulator as a data factory (RL-style environment)

In simulation-only mode, we don't wait for real farms to generate experience —
**the sim generates it at scale**:

```
   ┌────────────────────────── EXPERIENCE GENERATION ──────────────────────────┐
   │  for each (farm config × AEZ zone × weather scenario × season × policy):   │
   │      run the orchestrator loop day-by-day                                  │
   │      each day emits a Transition:  state → action → next_state → outcome   │
   │      → persist to the Episode Store (canonical schema, §3)                 │
   └───────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
   ┌───────── CURATION ─────────┐   ┌───────── TRAINING ─────────┐   ┌── EVAL/GATE ──┐
   │ episode store → tidy       │→  │ retrain per decision-type   │→ │ vs held-out   │
   │ per-model training tables  │   │ (yield / irrigation policy /│   │ & vs baseline │
   │ (features, action, reward) │   │  enterprise / livestock)    │   │ improvement?  │
   └────────────────────────────┘   └─────────────────────────────┘   └──────┬───────┘
                                                                              │ pass
                                     ┌────────────────────────────────────────▼──────┐
                                     │ MODEL REGISTRY (versioned) → orchestrator uses │
                                     │ new policy next run  →  loop repeats, improves │
                                     └────────────────────────────────────────────────┘
```

This is a self-improving flywheel: better policies produce better episodes,
which train better policies. It doubles as the **evaluation harness** for the
autonomy ladder — we can measure L2/L3-style policies in sim before any hardware.

---

## 3. Canonical telemetry schema

One schema for *all* decisions (crops **and** livestock), superseding the two
divergent log shapes. Proposed home: `src/telemetry/`.

### 3.1 The core unit — `Transition`
A single agent decision and its measured consequence (an RL `(s, a, r, s')` tuple
plus provenance):

```python
@dataclass
class Transition:
    # identity / provenance
    transition_id: str
    episode_id: str            # one simulated farm-season run
    farm_id: str
    tick: int                  # day index within the episode
    timestamp: datetime
    domain: str                # "crop" | "livestock" | "water" | "maintenance" | "security"
    agent_id: str
    policy_version: str        # which model/policy produced the action

    # the decision
    decision_type: str         # "irrigate" | "feed_livestock" | "water_livestock" | ...
    action: str                # discrete label
    parameters: dict           # e.g. {"liters": 420, "plot_id": "P1"}

    # state before / after (structured, versioned)
    state_before: dict         # observation the agent acted on
    state_after: dict          # observation one tick later
    context: dict              # AEZ zone, season mode, weather, budgets, herd, ...

    # the label (see §4)
    outcome: dict              # measured effects (moisture delta, liters, welfare, ...)
    reward: float              # scalar objective for this decision_type
    reward_components: dict    # breakdown (water_saved, stress_penalty, welfare, ...)

    # guardrails / autonomy metadata
    risk_level: str            # NORMAL | HIGH | HUMAN_APPROVAL
    approved_by: str | None    # human vs auto (matters at L2+)
    schema_version: str
```

### 3.2 The `Episode`
Header for one simulated farm-season, so transitions are groupable and
attributable to end-of-season outcomes (yield, profit, welfare incidents):

```python
@dataclass
class Episode:
    episode_id: str
    farm_config: dict          # location, AEZ, plots, herd, water system, budgets
    weather_scenario: str      # e.g. "harare_2019_dry", "synthetic_drought_p90"
    season_mode: str           # wet_season | dry_season
    policy_bundle: dict        # {decision_type: policy_version} used this run
    n_ticks: int
    season_outcome: dict       # total yield, profit, water used, welfare incidents
    created_at: datetime
    schema_version: str
```

### 3.3 Storage
- **Format:** append-only. Start with **SQLite** (matches current loggers) and/or
  **Parquet** for training pulls; both trivially map from the dataclasses.
- **Migration:** wrap the existing `DecisionLogger` and the sim's
  `DecisionLog`/`OutcomeLog` in an adapter that emits `Transition`s — no rewrite
  of callers, just capture what's already flowing.
- **Versioned:** `schema_version` on every record so retraining is reproducible.

---

## 4. The outcome / reward layer (the crux)

A logged action is worthless for learning without a **label**: what did it
achieve? Two attribution horizons:

1. **Immediate outcome** — measurable next tick, already computed by the sim
   (e.g. `soil_moisture_after − soil_moisture_before`, `liters_used`, stress
   avoided). Cheap, dense signal → trains operational policies (irrigation).
2. **Episodic outcome** — end-of-season yield/profit/welfare, credited back to
   the decisions that led there (credit assignment). Sparse but aligned with
   what we actually care about → trains planners/recommenders.

### Proposed reward definitions (🟠 need sign-off — see §7)

| Decision type | Reward = maximize | Penalize |
|---------------|-------------------|----------|
| **Irrigate** (crop) | water-use efficiency = yield-factor gained per liter | crop stress days; water waste above target moisture band |
| **Crop plan / enterprise** | season profit + food-security fit for AEZ | capital over budget; soil depletion |
| **Feed livestock** | body-condition / growth vs feed cost; residue-loop use | welfare shortfall; feed waste |
| **Water livestock** | welfare satisfied (never thirsty) — **hard floor** | any unmet demand = large negative (guardrail) |
| **Maintenance** | uptime / failures prevented per labour-hour | deferred-maintenance risk |
| **Security/biosecurity** | incidents prevented / response latency | breach severity |

**Guardrail rewards are asymmetric by design:** welfare/biosecurity/water-security
failures carry outsized penalties so no learned policy can trade them away for
efficiency. This encodes the product's hard constraints *into the objective*, not
just the runtime guardrail.

---

## 5. Livestock in the loop (new — required by "both" scope)

Today `sim/environment.py` steps crops/irrigation only. To learn the **mixed
crop-livestock loop** we add a livestock sub-step so it emits transitions too:

- **State:** herd counts, body condition, water-point levels, feed stores,
  residue availability from crop plots.
- **Actions:** `water_livestock`, `feed_livestock` (residue vs purchased),
  `move_herd`, welfare/biosecurity checks.
- **Dynamics (v1, deterministic like the crop model):** feed/water → body
  condition; unmet water → welfare incident; manure output → soil-fertility
  input back to crop plots (closing the mixed loop); residue from harvest → feed
  stock. This makes the crop↔livestock coupling *learnable*, not just narrated.
- Livestock transitions flow into the same `Transition` schema (§3) with
  `domain="livestock"`.

This is the one piece that requires **new simulation dynamics**, not just plumbing.

---

## 6. Pipeline & module plan

Proposed new/changed modules (all sim-side, no hardware):

```
src/telemetry/
  schema.py          # Transition, Episode dataclasses + schema_version
  store.py           # append-only SQLite/Parquet writer + query/export
  adapters.py        # wrap existing DecisionLogger + sim DecisionLog/OutcomeLog → Transition
  reward.py          # per-decision-type reward fns (§4), guardrail-asymmetric

src/sim/
  environment.py     # + livestock sub-step (§5), emit Transitions
  experience.py      # NEW: batch runner over (config × weather × season × policy)
                     #      = the "data factory" driver

src/ml/
  training/
    dataset.py       # NEW: episode store → per-model training tables (replaces
                     #      synthetic-only data_generator for operational models)
  registry.py        # NEW: versioned model store + metadata (metrics, data hash)
  evaluate.py        # NEW: held-out + vs-baseline gates before promotion

scripts/
  run_experience.py  # generate N episodes
  train_from_logs.py # curate → train → evaluate → register
```

Wiring back: the orchestrator/agents load the **registered** policy version for
each `decision_type`; a promoted model changes behavior on the next run, closing
the loop. Existing `src/validation/counterfactual.py` becomes the "vs-baseline"
evaluator.

---

## 7. Open modeling questions (need your guidance) 🟠

1. **Reward definitions (§4)** — do the maximize/penalize columns match how *you*
   judge a good decision? Especially: how hard should the water-security floor be
   for livestock, and is water-use-efficiency (yield-per-liter) the right
   irrigation objective vs. absolute yield?
2. **Objective weighting** — single scalar reward per decision, or multi-objective
   (profit vs. resilience vs. welfare) exposed as tunable weights per farm?
3. **Credit assignment** — for season-level outcomes (yield/profit), simple
   attribution (split evenly / by resource share) for v1, or proper temporal
   credit later? I'd propose simple-now, RL-later.
4. **Learning method for irrigation** — start with **supervised imitation** of the
   best rule-based policy + tuning (safe, interpretable), then graduate to RL
   once the sim/reward is trusted? Or go RL directly?
5. **Livestock dynamics realism (§5)** — is a simple deterministic body-condition/
   welfare model acceptable for v1, or do you have specific Zimbabwe cattle/goat/
   poultry parameters (intake, growth, water needs) we should encode?
6. **What "improvement" gates a model** — beat the current policy on reward by X%
   on held-out weather scenarios? Any absolute welfare/water constraints that must
   never regress regardless of reward?

---

## 8. Build order (proposed)

1. `src/telemetry/schema.py` + `store.py` + `adapters.py` — capture what already
   flows from the sim into a canonical, queryable store. **No behavior change,
   immediate value** (real datasets start accumulating).
2. `reward.py` — encode §4 (pending your sign-off), backfill rewards onto stored
   transitions.
3. `sim/experience.py` + `scripts/run_experience.py` — the data factory; generate
   the first large labeled crop dataset.
4. `ml/training/dataset.py` + `evaluate.py` + `registry.py` — train an operational
   irrigation policy from logs, gate it, register it; wire the orchestrator to load it.
5. Add the **livestock sub-step** (§5) and extend the factory to the mixed loop.

Step 1 is safe and unblocks everything; I can start there while you weigh in on §7.
