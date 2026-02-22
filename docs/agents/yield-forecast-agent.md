# Yield Forecast Agent Spec (v0)

## Objective
Estimate end-of-cycle yield proxy and near-term stress risk to guide planning.

## Inputs
- Historical soil moisture trajectory
- Weather trajectory and forecast summary
- Crop stage progression
- Irrigation actions history
- Optional soil fertility index

## Outputs
- `yield_proxy_estimate: float`
- `stress_risk_7d: float [0,1]`
- `recommendation_tag: string` (e.g., 'increase_irrigation', 'stable')
- `reason: string`

## Model v0
- Start simple: heuristic score or linear regression baseline
- Keep model transparent and explainable
- Emit confidence interval once basic variance modeling exists

## Constraints
- Deterministic mode must be supported for reproducible tests
- Must log feature inputs used for each estimate

## Evaluation
- MAE / MAPE against simulated ground-truth proxy
- Early-warning usefulness (stress risk precision/recall)
- Contribution to downstream irrigation improvements
