# AgriMesh Autonomous

Agent-driven Farm OS for Zimbabwe (simulation-first MVP).

## Vision
Build a distributed agricultural intelligence platform where software agents make daily farm decisions, learn from outcomes, and improve productivity/resilience over time.

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
5. Check outputs in `logs/` (`baseline.jsonl`, `agent.jsonl`, `benchmark_report.json`)

## Success Metrics (Phase 1)
- Water-use efficiency improvement (%)
- Yield proxy improvement (%)
- Decision consistency and explainability
- Failure-rate under weather variability

## Positioning (go-to-market)
Start with: **Smart irrigation + yield optimization**
Not: full autonomy claims.
