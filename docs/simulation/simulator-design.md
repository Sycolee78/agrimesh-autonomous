# Simulator Design (v0)

## Purpose
Provide a controllable environment to test farm agents before field deployment.

## State Transition (daily step)
Given state S_t and actions A_t:
S_{t+1} = F(S_t, A_t, W_t, noise)
Where W_t = weather variables.

## Minimum Components
1. Weather generator/input loader
2. Soil moisture dynamics
3. Crop growth stage progression
4. Yield proxy function
5. Constraint engine (water/pump limits)
6. Event logger

## Run Modes
- Deterministic (for regression tests)
- Stochastic (for robustness tests)

## Baselines
- Fixed schedule irrigation (e.g., every N days)
- Human-like heuristic schedule

## Experiments
- Compare baseline vs Irrigation Agent v0
- Ablate rain-forecast input effect
- Test under dry/normal/wet profiles

## Artifacts per experiment
- Config file
- Metrics JSON
- Decision logs
- Plot/report summary
