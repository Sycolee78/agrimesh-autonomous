# AgriMesh Autonomous — Masterplan to Full Autonomy

> Living planning document. The goal: evolve AgriMesh from a simulation-first
> advisory system into a **fully autonomous farm that can be commissioned on
> any selected parcel of land** in Zimbabwe (and comparable agro-climates),
> operating safely with a human on the loop rather than in the loop.
>
> Status of this doc: **draft for review** — sections marked 🟠 contain
> assumptions that need the product owner's guidance. See §9.

### Decisions locked (2026-07-23)
- **Deployment mode:** **simulation-only for now** — perfect the brain, learning
  loop, and commissioning in sim before any hardware spend. Hardware is
  *designed on paper* (BOM/layout), not built.
- **Scope:** **crops *and* livestock together** — the full mixed loop.
- **First deep-dive:** **the learning loop / telemetry schema** (see
  `docs/LEARNING_LOOP.md`).
- Implication: the **simulator is the data factory** (an RL-style environment).
  Autonomy levels (§2) are exercised *in sim* until we choose to go to hardware.

---

## 1. North Star

A farmer (or an installer on their behalf) points at a piece of land, answers a
short survey, and within a season AgriMesh is:

1. **Sensing** the farm continuously (soil moisture, weather, water, livestock,
   crop health).
2. **Deciding** daily/hourly what to do — irrigation, fertigation, feed/water
   for livestock, planning, alerts — using AEZ- and season-aware policies plus
   learned models.
3. **Acting** on physical hardware (valves, pumps, fertigation, gates) within a
   safety envelope, escalating high-risk actions to a human.
4. **Learning** from logged outcomes so decisions improve every season.

Positioning stays disciplined: we lead with **"smart irrigation + yield
optimization that runs itself,"** not sci-fi full-autonomy claims. Autonomy is
earned level-by-level as trust and safety evidence accumulate.

---

## 2. What "fully autonomous" means — the autonomy ladder

Borrowed from self-driving, adapted to farms. Each level is a shippable product.

| Level | Name | Human role | AgriMesh does | Where we are |
|------|------|-----------|---------------|--------------|
| L0 | Manual | Does everything | Records data | — |
| L1 | **Advisory** | Decides & acts | Recommends + explains | **← today (in sim)** |
| L2 | Supervised automation | Approves each action | Proposes + executes on approval | next target |
| L3 | Conditional autonomy | Handles exceptions only | Acts within an envelope; escalates edge cases | mid-term |
| L4 | High autonomy | Sets goals/budgets seasonally | Runs whole seasons hands-off in known conditions | long-term |
| L5 | Full autonomy | Owns the land | Runs any land, any conditions | vision |

**Principle:** welfare, biosecurity, and water-security actions never auto-escalate
past their guardrail regardless of level. High-risk actions (spray, animal
treatment, cull, herd offboard) stay human-approved even at L4.

---

## 3. Current state assessment (grounded in the code)

### Strong (production-shaped, in simulation)
- **Orchestrator + resource economy** — `src/orchestration/`: agents *bid* for
  water/labour/budget; conflict resolution; guardrails auto-mark high-risk
  actions as `HUMAN_APPROVAL`; livestock water auto-`CRITICAL`.
- **AEZ-aware planning** — `src/allocators/` (MIP via PuLP), `src/strategic_planner/`
  (enterprise ranking, capital tiers, Monte Carlo profit, spatial layout).
- **Simulation engine** — `src/sim/` (runner, benchmark, tuning, non-linear
  yield model, weather-driven).
- **Decision logging** — SQLite via `src/resources/logger.py` &
  `src/common/decision_logger.py`. This is the training-data pipeline.
- **ML planner** — `src/ml/` (feature extraction, yield predictor, enterprise
  recommender) trained on **synthetic** data today.
- **APIs + frontends** — FastAPI (`src/api/`), Streamlit analytics, React/Leaflet
  map planner, farm profiles (local + server-side JSON).

### Scaffolded only (the gap to autonomy)
- **Hardware layer** — `src/hardware/interfaces.py` defines clean abstract
  contracts (`SensorInterface`, `ActuatorInterface`, `HardwareManager`,
  interlocks, emergency-stop) but ships **only a simulated implementation**.
  No LoRa/cellular driver, no firmware, no real device ever attached.
- **Closed-loop control** — the orchestrator computes proposals but nothing
  drives real actuators or reconciles commanded-vs-actual state.

### Missing entirely
- Auth / multi-tenancy / per-user accounts; production DB (still SQLite/JSON files).
- Edge runtime (on-farm compute) and offline-first / store-and-forward.
- Connectivity stack (LoRaWAN, cellular, satellite fallback).
- **Site commissioning pipeline** — the thing that makes "any land" real.
- Telemetry ingestion → data lake → **learning loop / MLOps** (logs never
  retrain models yet).
- Farmer experience for low-connectivity rural users (mobile app, SMS/USSD,
  voice, local languages — Shona/Ndebele).
- Fleet management (many farms, many devices, OTA updates).
- CI/CD, observability, security hardening, backups.
- Real market/price feeds; today prices are static constants.

---

## 4. Target architecture (end state)

```
┌──────────────────────────────────────────────────────────────────┐
│  INTERFACE LAYER                                                   │
│  Farmer mobile app · SMS/USSD · voice (Shona/Ndebele) · web dash  │
│  Installer/commissioning app · stakeholder reports                │
└──────────────────────────────────────────────────────────────────┘
                              ▲  (intermittent)
┌──────────────────────────────────────────────────────────────────┐
│  CLOUD / PLATFORM LAYER                                            │
│  Multi-tenant API · auth · fleet mgmt · OTA · data lake           │
│  Model training (MLOps) · digital-twin sync · market feeds        │
└──────────────────────────────────────────────────────────────────┘
                              ▲  store-and-forward
┌──────────────────────────────────────────────────────────────────┐
│  EDGE LAYER  (on-farm gateway, solar-powered, offline-capable)    │
│  ┌─ Perception ─┐  ┌─ Autonomy engine ──────┐  ┌─ Actuation ─┐    │
│  │ sensor ingest│→ │ orchestrator (exists)   │→ │ HAL drivers │    │
│  │ + fusion     │  │ + safety envelope       │  │ + interlocks│    │
│  └──────────────┘  │ + escalation            │  └─────────────┘    │
│   local digital    └─────────────────────────┘   local decision   │
│   twin (src/sim)                                  log (SQLite)     │
└──────────────────────────────────────────────────────────────────┘
                              ▲  LoRa / wired
┌──────────────────────────────────────────────────────────────────┐
│  FIELD LAYER  sensors (soil moisture, tank, flow, weather) ·      │
│  actuators (solenoid valves, pumps, fertigation, gates) ·         │
│  livestock (water points, troughs, gates) · power (solar+battery) │
└──────────────────────────────────────────────────────────────────┘
```

Key architectural bets:
- **Edge-first / offline-first.** The autonomy loop must run fully on the farm
  gateway with no internet. Cloud is for fleet, training, and backup — never a
  hard dependency for daily operation. Rural Zimbabwe connectivity demands this.
- **The existing `src/sim` becomes the on-device digital twin** — used for
  what-if planning, safe pre-checks of actions, and sim-to-real validation.
- **The HAL (`src/hardware/interfaces.py`) is the seam.** Everything above it is
  hardware-agnostic; we implement it once per controller family.

---

## 5. "Install on any selected land" — the commissioning pipeline

This is the heart of the goal and today's biggest gap. Turning a bare parcel
into a running AgriMesh farm should be a repeatable, mostly-automated workflow:

1. **Select land** — draw the parcel on the map (React frontend already does
   click-to-locate). Capture boundary polygon, area, coordinates.
2. **Auto-characterize the site** — derive from location + open data:
   - AEZ zone, rainfall regime, growing seasons (`aez_lookup` exists).
   - Weather history/forecast (Open-Meteo client exists).
   - 🟠 Soil type, slope/topography, water-source proximity (needs new data
     sources: soil maps, DEM/elevation, hydrology).
3. **Plan the farm** — run the allocator + strategic planner to propose crop/
   livestock mix, layout, and economics for *this* parcel (exists).
4. **Generate the physical design** — from the plan, produce a **hardware BOM
   and field layout**: how many zones, valves, sensors, pump sizing, pipe runs,
   solar/battery sizing, gateway placement. 🟠 New module.
5. **Provision & register** — create the tenant/farm, register the gateway and
   each device (IDs, zones, calibration), push initial policies.
6. **Calibrate** — per-sensor calibration, actuator dry-run, interlock test,
   flow verification. Digital twin seeded from real readings.
7. **Go live** — start at L2 (supervised) and graduate to L3 as confidence
   metrics clear thresholds.

Deliverable: a **Commissioning Wizard** (extends the existing onboarding wizard)
plus a `src/commissioning/` module that outputs a site design + device manifest.

---

## 6. The autonomy control loop on real hardware

The daily/continuous loop, hardened for physical actuation:

```
 perceive → estimate state (sensor fusion + twin) → plan (orchestrator)
    → safety-check against envelope → act via HAL → verify feedback
    → log outcome → learn (offline) ↺   escalate on any exception
```

Requirements to make this safe:
- **Safety envelope:** hard limits per actuator (max runtime, max daily liters,
  pressure/current bounds) enforced *below* the planner, at the HAL. Extend the
  existing interlock/emergency-stop contracts into a real enforcement layer.
- **Command reconciliation:** every `ActuatorCommand` must be confirmed by
  `ActuatorFeedback`; mismatches (valve didn't open, flow anomaly) trigger
  ret/alert/stop.
- **Escalation:** anything outside the envelope, any guardrail action, or any
  low-confidence decision → human approval via app/SMS with a timeout-safe
  default (usually "do nothing / hold").
- **Sim-to-real:** validate a policy in the twin before it's allowed to act;
  compare predicted vs actual outcomes to catch model drift.

---

## 7. Workstreams (epics)

Organized as parallel tracks. Each is independently valuable and testable.

### Track A — Platform hardening (foundation)
- Auth & multi-tenancy (farms belong to accounts; installers vs farmers vs admin).
- Real database (Postgres) + migrations + backups; move off JSON/SQLite files.
- CI/CD (`.github/` — none today): lint, `pytest`, type-check, frontend build.
- Observability: structured logs, metrics, health endpoints, alerting.
- API rate limiting, secrets management, environments (dev/staging/prod).

### Track B — Hardware & edge
- Implement the HAL for a first controller family (🟠 e.g. ESP32/Raspberry Pi +
  relay boards, or a LoRaWAN node). Real `SensorInterface`/`ActuatorInterface`.
- Device firmware / edge agent that runs the orchestrator offline on the gateway.
- Safety-envelope enforcement + command reconciliation + emergency stop.
- Power management (solar + battery sizing, low-power sensor duty cycles).

### Track C — Connectivity & offline
- LoRaWAN for field nodes; cellular/Wi-Fi backhaul; 🟠 satellite fallback.
- Store-and-forward: farm runs offline, syncs telemetry & receives OTA when online.
- OTA update mechanism for firmware, policies, and models.

### Track D — Commissioning ("any land") — see §5
- Site characterization (soil, topography, hydrology data sources).
- Hardware BOM + field-layout generator (`src/commissioning/`).
- Commissioning wizard UI + device registration + calibration flows.

### Track E — Autonomy engine
- Closed-loop controller wrapping the orchestrator (§6).
- Confidence scoring + escalation policy + human-approval workflow.
- Autonomy-level state machine (L1→L4) with graduation criteria per farm.
- Digital-twin pre-check of actions before actuation.

### Track F — Learning loop / MLOps
- Telemetry ingestion → data lake; schema from existing decision logs.
- Retrain yield/enterprise/irrigation models on **real** outcomes (replace
  synthetic-only training in `src/ml/`).
- Model registry, evaluation gates, staged rollout, drift monitoring.
- Counterfactual/impact reporting (extends `src/validation/`).

### Track G — Farmer experience (rural-first)
- Mobile app (works offline, syncs when possible).
- **SMS/USSD** interface for feature-phone farmers; **voice + local languages**
  (Shona, Ndebele) for low-literacy users. 🟠 Priority TBD.
- Human-in-the-loop approvals delivered where the farmer actually is.
- Plain-language decision explanations (LLM agent exists — wire it in).

### Track H — Livestock autonomy
- Automated water-point monitoring & refill; feed scheduling from residue loop.
- Welfare/biosecurity monitoring; alerting; treatment stays human-approved.

### Track I — Economics & market integration
- Live market/price feeds replacing static constants; input-cost tracking.
- Profit/what-if reporting per farm; budget-aware autonomy.

### Track J — Trust, safety & compliance
- Welfare/biosecurity/water-security as certified, tested guardrails.
- Audit trail (decision logs already support this) + explainability.
- 🟠 Regulatory: agrochemical handling, water rights, animal welfare law, data privacy.

### Track K — Business / deployment
- Installer kit + playbook; supply chain for the BOM; pilot-farm program.
- Pricing/ownership model (device sale vs. service vs. co-op). 🟠

---

## 8. Phased roadmap (sequencing)

Builds on the existing roadmap (Phases 5–9) and extends it.

**Near-term — "make the brain trustworthy & the platform real"**
- Finish Phase 6 (server-side profiles, import/export).
- Track A basics: CI + tests green, auth, Postgres, observability.
- Track F seed: start capturing real-shaped telemetry from sim; build ingestion.
- Track E design: closed-loop controller + safety-envelope spec (still in sim).

**Mid-term — "first real hardware on one pilot farm (L2→L3)"**
- Track B: HAL implementation for chosen controller; edge agent runs orchestrator
  offline; safety envelope + reconciliation live.
- Track C: LoRa + store-and-forward + OTA.
- Track D: commissioning wizard + BOM/layout generator; commission the pilot.
- Track G: farmer approvals via app/SMS; explanations wired in.
- Ship **supervised automation (L2)** on the pilot, graduate to **L3** on
  irrigation once confidence metrics clear.

**Long-term — "multi-farm conditional/high autonomy (L3→L4)"**
- Track F: real learning loop closes; models retrain on outcomes; drift-monitored.
- Fleet management, OTA at scale, multi-tenant hardening.
- Livestock autonomy (Track H), economics/market integration (Track I).
- Expand from irrigation autonomy to whole-season L4 in known AEZ conditions.

---

## 9. Open questions — where I need your guidance 🟠

These are domain/business calls that change the plan. Numbered so you can answer
by number:

1. **Autonomy target for the MVP** — is the first shippable milestone L2
   (approve-each-action) or straight to L3 (acts within an envelope) for
   irrigation only?
2. **Hardware reality** — do you have a target controller/BOM in mind (e.g.
   Raspberry Pi + relays, ESP32 + LoRa, a commercial irrigation controller), a
   budget per farm, and a pilot site? This drives Track B/D heavily.
3. **Connectivity on the pilot land** — cellular coverage? Wi-Fi? Must it run
   fully offline from day one?
4. **Scope priority** — irrigation-first (crops) vs. livestock-first vs. both?
   The mixed crop-livestock loop is core to the vision but we should sequence one.
5. **Farmer interface** — smartphone app, or must we support feature phones
   (SMS/USSD) and local-language voice from the start?
6. **Business model** — device ownership vs. managed service vs. co-op? Affects
   multi-tenancy, billing, and support design.
7. **Regulatory constraints** in Zimbabwe for autonomous agrochemical/water/
   livestock actions that we must design around now.

---

## 10. Immediate next steps (proposed)

Independent of the answers above, these are safe to start now and unblock the rest:

1. **Stand up CI** (`.github/workflows`) + get `pytest` green as a gate.
2. **Specify the safety envelope + closed-loop controller** (design doc +
   interfaces) in `src/` — still simulated, but the real autonomy seam.
3. **Draft the commissioning pipeline** (`src/commissioning/` skeleton + wizard
   design) so "any land → running farm" has a concrete shape.
4. **Design the telemetry/learning-loop schema** so decision logs can retrain
   real models later.

Pick the track you want to push first and I'll go deep on it.
