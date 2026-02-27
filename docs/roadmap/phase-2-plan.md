# AgriMesh Phase 2: Production Readiness

## Overview
Phase 1 delivered a working simulation MVP. Phase 2 hardens the system for real-world validation.

## Workstreams

### WS1: Fix Yield/Water Trade-off (Week 1-2)
**Problem:** Current yield model is linear (moisture → yield), which penalizes smart water conservation.

**Fixes:**
1. **Non-linear yield response curve**
   - Optimal moisture range (e.g., 0.55-0.75) → max yield
   - Below critical threshold (0.35) → steep yield loss
   - Above saturation (0.85) → diminishing returns + waterlogging risk

2. **Growth-stage-aware irrigation**
   - Vegetative: moderate demand
   - Flowering: high demand (critical)
   - Grain fill: high demand
   - Maturity: reduced demand

3. **Multi-objective tuning**
   - Pareto frontier: water efficiency vs. yield
   - Configurable objective weights
   - Visualize trade-off curves

**Deliverables:**
- [ ] `src/sim/yield_model.py` — non-linear yield response
- [ ] `src/agents/irrigation/growth_stage.py` — stage-aware demand
- [ ] `src/sim/pareto_tuning.py` — multi-objective optimizer
- [ ] Updated benchmarks showing yield parity with 40%+ water savings

---

### WS2: Real Weather Data Integration (Week 2-3)
**Goal:** Replace synthetic weather with actual Zimbabwe meteorological data.

**Data Sources:**
1. **Open-Meteo API** (free, no key required)
   - Historical: 1940-present
   - Forecast: 16-day
   - Variables: temp, precip, humidity, wind, solar radiation

2. **Zimbabwe Met Services** (backup)
   - Station data for major AEZ zones

**Implementation:**
- [ ] `src/data/weather_client.py` — Open-Meteo fetcher
- [ ] `src/data/weather_cache.py` — local caching (SQLite)
- [ ] `data/weather/` — historical datasets for key locations
- [ ] Update simulator to use real weather sequences

**Validation locations:**
- Harare (Zone II)
- Bulawayo (Zone IV)
- Mutare (Zone I)
- Masvingo (Zone III)

---

### WS3: Hardware Interface Specification (Week 3-4)
**Goal:** Define protocols for eventual IoT sensor/actuator integration.

**Sensors:**
| Sensor Type | Protocol | Data Format | Polling |
|-------------|----------|-------------|---------|
| Soil moisture | Modbus RTU / LoRa | % VWC | 15 min |
| Temperature | I2C / LoRa | °C | 15 min |
| Rainfall | Tipping bucket | mm | Event |
| Tank level | Ultrasonic / 4-20mA | liters | 5 min |
| Flow meter | Pulse / Modbus | L/min | Continuous |

**Actuators:**
| Actuator Type | Protocol | Command Format |
|---------------|----------|----------------|
| Solenoid valve | GPIO / Relay | ON/OFF + duration |
| Pump | VFD / Relay | ON/OFF / speed % |
| Drip zone | Valve bank | Zone ID + duration |

**Deliverables:**
- [ ] `docs/hardware/sensor-spec-v1.md`
- [ ] `docs/hardware/actuator-spec-v1.md`
- [ ] `docs/hardware/communication-architecture.md`
- [ ] `src/hardware/` — abstract interface layer (for future)
- [ ] `schemas/sensor_reading.schema.json`
- [ ] `schemas/actuator_command.schema.json`

---

### WS4: Pilot Validation (Week 4-5)
**Goal:** Simulate against real farm historical data to validate agent decisions.

**Approach:**
1. Source historical data from a Zimbabwe farm (or construct realistic scenario)
2. Replay historical weather + known irrigation decisions
3. Compare: actual outcomes vs. agent recommendations
4. Measure: "If agent had controlled, what would yield/water have been?"

**Deliverables:**
- [ ] `data/pilots/sample_farm_2024/` — historical dataset
- [ ] `src/validation/replay_simulator.py` — historical replay mode
- [ ] `src/validation/counterfactual.py` — "what if agent" analysis
- [ ] Validation report with metrics

---

### WS5: LLM Reasoning Agent (Week 5-6)
**Goal:** Add natural language explanation layer for agent decisions.

**Architecture:**
```
Orchestrator Decision → LLM Agent → Human-readable explanation
                                  → Recommendation confidence
                                  → Alternative options with trade-offs
```

**Features:**
- Explain why irrigation was increased/decreased
- Flag anomalies in plain language
- Generate daily/weekly summary reports
- Answer farmer questions about recommendations

**Implementation:**
- [ ] `src/agents/reasoning/llm_explainer.py`
- [ ] `src/agents/reasoning/prompts/` — prompt templates
- [ ] Integration with orchestrator decision logs
- [ ] Frontend: explanation panel in Streamlit UI

**Model options:**
- Local: Ollama + Llama 3 / Mistral
- API: Claude / GPT-4 (for production)

---

## Timeline Summary

| Week | Focus | Key Deliverable |
|------|-------|-----------------|
| 1 | WS1: Yield model fix | Non-linear response + growth stages |
| 2 | WS1 + WS2: Tuning + weather | Pareto optimizer + Open-Meteo integration |
| 3 | WS2 + WS3: Weather + hardware | Real data benchmarks + sensor specs |
| 4 | WS3 + WS4: Hardware + pilot | Interface layer + historical replay |
| 5 | WS4 + WS5: Validation + LLM | Counterfactual analysis + explainer agent |
| 6 | WS5 + Integration | Full pipeline demo |

## Success Criteria (Phase 2 Exit)
- [ ] Agent achieves ≥95% of baseline yield with ≥30% water savings
- [ ] Real Zimbabwe weather data integrated for 4+ locations
- [ ] Hardware interface spec published and reviewed
- [ ] Pilot validation shows <10% decision deviation from optimal
- [ ] LLM explainer generates coherent daily summaries
