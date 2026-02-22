# AgriMesh Autonomous

Agent-driven Farm OS for Zimbabwe (simulation-first MVP).

## Vision
Build a distributed agricultural intelligence platform where software agents make daily farm decisions, learn from outcomes, and improve productivity/resilience over time.

## Zimbabwe mixed-farm operating context (now encoded)
This project now explicitly follows an integrated crop-livestock operating model for Zimbabwe:
- Mixed-loop sustainability: crop residues and by-products feed livestock; manure/compost returns nutrients to fields.
- AEZ-aware planning: farm decisions must be region- and rainfall-context aware (not one static recipe).
- Dual operating cadence:
  - Daily loops: livestock water/feed/health, irrigation checks, maintenance, security/biosecurity.
  - Seasonal modes: wet-season vs dry-season priorities and constraints.
- Welfare + biosecurity + water-security are hard constraints, not optional optimizations.

## Phase 1 Goal (Simulation MVP)
Within 6 months, deliver:
- Simulated farm environment
- 2 working agents:
  - Irrigation Agent
  - Yield Forecast Agent
- Daily decision logs
- Measurable improvement over baseline schedule

## Day 1 Deliverables (this commit)
- Repo scaffold
- Farm state schema (`schemas/farm_state.schema.json`)
- Agent specs (`docs/agents/`)
- Simulation design (`docs/simulation/`)
- 90-day execution plan (`docs/architecture/90-day-roadmap.md`)

## Suggested Tech Stack (MVP)
- Python 3.11+
- Pydantic or dataclasses for typed state models
- Pandas + NumPy for simulation and analysis
- FastAPI (later, for APIs)
- SQLite/Postgres for logs

## Initial Repo Structure
```
agrimesh-autonomous/
  docs/
    architecture/
    agents/
    simulation/
  schemas/
  farm_os/
    agents/
    core/
    env/
    logs/
  tests/
```

## Quick Start
1. Create a Python virtual environment
2. Install deps: `pip install -r requirements.txt`
3. Run simulation smoke: `python -m src.sim.runner`
4. Run benchmark (baseline vs agent): `python -m src.sim.benchmark`
5. Tune irrigation parameters (grid search): `python -m src.sim.tuning`
6. Run orchestrator cycle demo: `python -m src.orchestration.run_orchestrator_demo`
7. Check outputs in `logs/` (`baseline.jsonl`, `agent.jsonl`, `benchmark_report.json`, `tuning/tuning_summary.json`, `orchestrator_cycle.json`)

## Orchestration layer (new)
`src/orchestration/` now contains a management-orchestrator pattern with specialized agents:
- `FarmManagementOrchestrator` (conflict resolution + guardrails)
- `CropOperationsAgent`
- `LivestockOperationsAgent`
- `WeatherWaterAgent`
- `MaintenanceAgent`
- `SecurityBiosecurityAgent`

### Guardrails currently enforced
- High-risk actions (`spray_pesticide`, `animal_treatment`, `cull`, `drone_herd_offboard`) are auto-marked `HUMAN_APPROVAL`.
- Livestock water actions are auto-prioritized as `CRITICAL`.
- Irrigation actions are conflict-resolved against daily water budgets.

### AEZ-aware irrigation policy (new)
- Plot model now includes `aez_zone` (I–V style zone tag).
- Orchestrator resolves per-plot irrigation config from:
  - AEZ baseline
  - crop sensitivity (maize/potato/sorghum/groundnut)
  - seasonal mode (`wet_season` / `dry_season`)
- Implementation: `src/orchestration/aez_policy.py`

### AEZ-aware yield targeting (new)
- Added crop+zone yield bands and midpoint targets.
- Crop agent now logs per-plot expected yield ranges and farm-level yield-gap status.
- If yield gap is materially negative, orchestrator alerts for agronomy review.
- Implementation: `src/orchestration/yield_targets.py`

## Crop portfolio in current model scope
- Maize (staple)
- Potatoes (high-value, irrigation-sensitive)
- Sorghum (drought resilience)
- Groundnuts (legume + feed/compost loop)

## Success Metrics (Phase 1)
- Water-use efficiency improvement (%)
- Yield proxy improvement (%)
- Decision consistency and explainability
- Failure-rate under weather variability
- Welfare/biosecurity incident response latency

## Positioning (go-to-market)
Start with: **Smart irrigation + yield optimization**
Not: full autonomy claims.
