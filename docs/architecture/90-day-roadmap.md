# 90-Day Roadmap — AgriMesh Autonomous (Phase 1)

## Outcome by Day 90
A working simulation MVP with Irrigation Agent + Yield Forecast Agent, benchmarked against baseline policies with reproducible reports.

## Sprint 1 (Days 1–14): Foundations
- [ ] Finalize repo standards (lint, format, testing)
- [ ] Freeze farm state schema v0.1
- [ ] Build simulation environment skeleton
- [ ] Implement weather + soil moisture dynamics (simple first)
- [ ] Define baseline irrigation policy
- Deliverable: deterministic simulation run (7-day)

## Sprint 2 (Days 15–30): Irrigation Agent v0
- [ ] Implement Irrigation Agent (rule-based thresholds)
- [ ] Add constraints: water budget, pump capacity
- [ ] Add decision logs + explanation fields
- [ ] Run 30-day simulations across 3 weather profiles
- Deliverable: baseline vs irrigation agent report v0

## Sprint 3 (Days 31–45): Yield Forecast Agent v0
- [ ] Define yield proxy formula
- [ ] Implement forecast model (heuristic/regression baseline)
- [ ] Emit planning signals (e.g., stress risk)
- [ ] Integrate with simulation loop
- Deliverable: forecast accuracy + usefulness report

## Sprint 4 (Days 46–60): Robustness + Evaluation
- [ ] Add stochastic weather variability
- [ ] Add failure modes (sensor noise, missing data)
- [ ] Introduce evaluation dashboard script/notebook
- Deliverable: robustness report + stress tests

## Sprint 5 (Days 61–75): Refinement
- [ ] Tune irrigation policy parameters
- [ ] Improve forecast features and calibration
- [ ] Add experiment tracking metadata
- Deliverable: improved metrics over Sprint 2/3

## Sprint 6 (Days 76–90): MVP Packaging
- [ ] Freeze schema v1.0
- [ ] Write operator docs + architecture brief
- [ ] Produce final benchmark report
- [ ] Prepare demo scenario and narrative
- Deliverable: Phase 1 MVP package

## Core Metrics (tracked weekly)
1. Water-use efficiency delta vs baseline
2. Yield proxy delta vs baseline
3. Decision explainability completeness (%)
4. Simulation stability (run success rate)
5. Policy robustness under variability
