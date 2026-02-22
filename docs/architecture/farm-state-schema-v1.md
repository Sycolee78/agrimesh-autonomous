# Farm State Schema v1

## Domain Entities

### FarmState
- `timestamp`
- `plots[]`
- `water_system`
- `weather`
- `crop_plan`
- `resources`
- `kpis`

### Plot
- `plot_id`
- `area_m2`
- `crop_type`
- `crop_stage`
- `soil_moisture`
- `soil_type`
- `health_signals`
- `last_irrigation_at`

### WaterSystem
- `tank_level_liters`
- `daily_supply_limit_liters`
- `pump_capacity_lpm`
- `valve_status_by_plot`

### Weather
- `temperature_c`
- `humidity_pct`
- `rainfall_mm`
- `forecast_24h`
- `forecast_7d`

### Resources
- `labor_hours_available`
- `energy_kwh_available`
- `fertilizer_stock_kg`

### KPIs
- `water_use_efficiency`
- `crop_stress_events`
- `yield_estimate_tons_per_ha`
- `operational_cost_index`

## Event Logs (Required)
### DecisionLog
- `cycle_id`
- `agent_id`
- `observation_hash`
- `action_plan`
- `rationale`
- `policy_version`

### OutcomeLog
- `cycle_id`
- `actual_changes`
- `kpi_delta`
- `anomalies`

## Notes
- Keep schema explicit and versioned (`schema_version`).
- Add livestock entities in v2 without breaking v1 contracts.
