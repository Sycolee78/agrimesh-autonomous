# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this project is

**AgriMesh Autonomous** is a simulation-first, agent-driven "Farm OS" for
Zimbabwe. The goal is a distributed agricultural intelligence platform where
software agents make daily farm decisions (irrigation, livestock, planning),
learn from outcomes, and optimize productivity/resilience — starting as a
simulation MVP rather than live hardware autonomy.

Domain context is central and encoded throughout the code:
- **AEZ-aware**: Zimbabwe's 5 agro-ecological zones (I–V) drive rainfall,
  crop suitability, and policy. See `src/allocators/aez_lookup.py`,
  `src/orchestration/aez_policy.py`.
- **Mixed crop-livestock loop**: residues feed livestock, manure returns to
  fields. Crop scope: maize, potatoes, sorghum, groundnuts (+ vegetables,
  fodder, pasture in the allocator).
- **Hard constraints**: animal welfare, biosecurity, and water security are
  non-negotiable — treated as guardrails, not optimization targets.

Positioning: lead with "smart irrigation + yield optimization," not full
autonomy claims.

## Tech stack

- **Backend/core**: Python 3.11+ (uses `from __future__ import annotations`,
  dataclasses, type hints throughout). Pydantic, NumPy, Pandas, PuLP
  (optimization), scikit-learn (ML), FastAPI + Uvicorn (API).
- **Streamlit frontend**: `frontend/` — the original multi-page analytics UI
  (8 pages: Farm Planner, Strategic Planner, Weather, Optimization,
  Validation, AI Advisor, ML Planner, Resources).
- **React/Next.js frontend**: `web-frontend/` — Next.js 14 + TypeScript +
  Tailwind + Leaflet (OpenStreetMap) + Zustand + Recharts.
- No CI configured yet (`.github/` does not exist).

## Repository layout

```
src/                    # Main, actively developed Python code
  agents/               # Individual agent policies (irrigation, yield_forecast, reasoning/LLM)
  orchestration/        # FarmManagementOrchestrator + specialized ops agents + resource economy
  allocators/           # AEZ-aware farm planning pipeline (MIP optimizer, profit, scheduler)
  strategic_planner/    # Enterprise ranking, capital tiers, Monte Carlo profit, spatial layout
  sim/                  # Simulation engine, runner, benchmark, yield model, tuning
  resources/            # Resource pool, bidding, budget, decision logger (SQLite)
  ml/                   # ML planner: feature extraction, yield predictor, enterprise recommender
  api/                  # FastAPI app (src/api/main.py), farm profile storage, auto planner
  data/                 # Weather client (Open-Meteo), Zimbabwe locations
  hardware/             # Sensor/actuator interface specs (not yet wired to real hardware)
  common/               # Shared dataclass models, decision logger
  validation/           # Counterfactual analysis, pilot data generation
frontend/               # Streamlit app (app.py + pages/)
web-frontend/           # Next.js React app
farm_os/                # Original Day-1 scaffold (early simulator/agent demo) — see note below
docs/                   # Architecture, agent specs, roadmaps, hardware/sim design
schemas/                # JSON schemas (farm_state, resource_pool)
data/                   # AEZ, pilot, weather data
tests/                  # pytest smoke + unit tests
scripts/                # Demo scripts (e.g. demo_ml_planner.py)
```

**Note on `farm_os/` vs `src/`**: `src/` is the primary codebase. `farm_os/`
is the earlier scaffold (`env/simulator.py`, `agents/irrigation_agent.py`,
`core/run_demo.py`). It is mostly superseded by `src/sim/`, but the
orchestrator and decision logger still write logs to `farm_os/logs/`
(SQLite). Prefer building on `src/`; don't assume `farm_os/` modules are
current.

## Running things

**Important**: All Python entrypoints require the project root on
`PYTHONPATH` (imports are `from src...`). `pyproject.toml` sets
`pythonpath = ["."]` for pytest; for manual runs export it:
`export PYTHONPATH="$(pwd):$PYTHONPATH"`.

```bash
# Streamlit frontend (creates venv, installs deps, launches :8501)
./run.sh

# FastAPI backend (:8000, docs at /docs)
./run-api.sh                       # or: uvicorn src.api.main:app --reload --port 8000

# React frontend
cd web-frontend && npm install && npm run dev   # :3000

# Simulation / analysis directly
python -m src.sim.runner
python -m src.sim.benchmark
python -m src.sim.tuning
python -m src.orchestration.run_orchestrator_demo
python -m src.allocators.pipeline

# Tests
pip install pytest            # not preinstalled in fresh envs
python -m pytest -q
```

Dependencies: `pip install -r requirements.txt`. The React frontend can run
standalone on mock data if the API is down.

## Conventions & patterns

- **Python style**: dataclasses for state models (see `src/common/models.py`),
  `from __future__ import annotations` at the top of modules, explicit type
  hints, module-level docstrings describing purpose. Match the surrounding
  file's density and idiom.
- **Orchestrator pattern**: `FarmManagementOrchestrator` coordinates
  specialized ops agents (`CropOperations`, `LivestockOperations`,
  `WeatherWater`, `Maintenance`, `SecurityBiosecurity`) via a resource
  economy (agents *bid* for water/labour/budget) and safety guardrails.
  Contracts live in `src/orchestration/contracts.py`
  (`AgentContext`, `ActionProposal`, `Priority`, `RiskLevel`).
- **Guardrails (enforced, do not bypass)**: high-risk actions
  (`spray_pesticide`, `animal_treatment`, `cull`, `drone_herd_offboard`) are
  auto-marked `HUMAN_APPROVAL`; livestock water is auto-`CRITICAL`;
  irrigation is conflict-resolved against daily water budgets.
- **Decision logging**: decisions persist to SQLite for audit and future ML
  training (`src/resources/logger.py`, `src/common/decision_logger.py`).
  Preserve this — logs are the training-data pipeline.
- **AEZ everywhere**: farm logic should be zone- and season-aware
  (`wet_season`/`dry_season`), never a single static recipe.

## Development workflow

- Work happens in phases (see `docs/ROADMAP.md`). Current: Phase 6 (farm
  profiles & onboarding); planned: IoT/hardware bridge, production hardening
  (auth, rate limiting, environments).
- Commit style in history: `feat(scope): summary`, `docs: ...`,
  `feat(phaseN): ...`. Keep messages clear and scoped.
- When adding features, update the relevant `docs/` and the README section
  if user-facing.
- No linter/formatter is configured for Python; follow existing style. The
  React app has `next lint` available.

## Things to watch out for

- **PYTHONPATH** is the most common source of import errors — always set it.
- `pytest` is not preinstalled in fresh environments; install before testing.
- Two frontends coexist (Streamlit + React) with overlapping features;
  confirm which one a task targets.
- `farm_os/` is partly legacy but still holds the log DB path — don't delete
  it blindly.
- Keep welfare/biosecurity/water-security guardrails intact; they are
  product requirements, not optional.
