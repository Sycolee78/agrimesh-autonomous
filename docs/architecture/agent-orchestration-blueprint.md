# Agent Orchestration Blueprint (Zimbabwe mixed-farm context)

## Objective
Translate a sustainability-first integrated crop-livestock operating model into executable, auditable agent workflows.

## Operational modes
- `wet_season`: planting/weed/pest pressure, pasture growth, runoff risk
- `dry_season`: irrigation optimization, fodder budgeting, water reliability, fire risk

## Orchestrator responsibilities
1. Gather specialized agent outputs
2. Enforce non-negotiable constraints (welfare, biosecurity, water security)
3. Resolve conflicts (especially water allocation)
4. Queue actions by priority and risk
5. Flag human-approval actions

## Specialized agents in code (v0)
- CropOperationsAgent
- LivestockOperationsAgent
- WeatherWaterAgent
- MaintenanceAgent
- SecurityBiosecurityAgent

## Hard constraints (v0)
- Livestock water checks are always CRITICAL.
- High-risk operations require explicit human approval.
- Water-demand conflicts are scaled to daily available budget.

## Next implementation checkpoints
1. Add AEZ-aware field configuration (`field_id -> aez_zone`) and zone-specific policy defaults.
2. Add livestock telemetry models (cattle/goat/poultry): water status, mortality anomalies, heat stress.
3. Add biosecurity workflow engine (visitor vehicle disinfection, quarantine timers).
4. Add economic layer (enterprise margin by crop/livestock unit).
5. Add event bus interface (MQTT topic contracts) for edge execution.
