# Irrigation Agent Spec (v0)

## Objective
Optimize irrigation timing/volume to reduce water waste while maintaining or improving crop health and yield proxy.

## Inputs
- Soil moisture (current, trend)
- Weather forecast (rain probability, temperature, evapotranspiration proxy)
- Crop stage
- Water budget (daily/weekly)
- Field constraints (pump/valve capacity)

## Outputs
- `irrigate_now: bool`
- `target_mm: float`
- `zone_actions:[]` (future multi-zone)
- `reason: string`
- `confidence: float [0,1]`

## Policy v0 (Rule-based)
Example logic:
1. If heavy rain expected within 12h and moisture above lower threshold -> defer
2. If moisture below stage-specific threshold -> irrigate
3. If moisture critically low -> irrigate regardless (unless hard constraint)
4. Cap action by water budget and infrastructure limits

## Constraints
- Must never exceed max daily water cap
- Must output explanation for every decision
- Must degrade safely under missing data (fallback threshold policy)

## Evaluation
- Water use per simulated hectare
- Stress-day count
- Yield proxy impact
- Rule violation count
