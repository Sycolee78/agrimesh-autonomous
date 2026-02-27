# AgriMesh Actuator Specification v1

## Overview
This document defines actuator interfaces for AgriMesh automated farm control.

Design principles:
- **Fail-safe**: Default to OFF/CLOSED on communication loss
- **Manual override**: Physical bypass for all critical actuators
- **Feedback**: Confirm state after command execution
- **Gradual adoption**: Start manual, add automation incrementally

---

## Actuator Categories

### 1. Solenoid Valves (Irrigation Zones)

#### Latching Solenoid (Recommended - Low Power)
| Attribute | Value |
|-----------|-------|
| Type | Latching (bistable) |
| Voltage | 9-12V DC pulse |
| Current | 200-400mA pulse (100ms) |
| Holding | 0mA (latching) |
| Pipe Size | 3/4", 1", 1.5", 2" |
| Flow Rate | 20-200 L/min |
| Examples | Hunter PGV, Rain Bird DV |

#### Standard Solenoid (Simpler, higher power)
| Attribute | Value |
|-----------|-------|
| Type | Normally closed |
| Voltage | 24V AC (common) or 12V DC |
| Current | 150-350mA continuous |
| Pipe Size | 1/2" - 2" |

#### Command Format
```json
{
  "actuator_id": "VALVE-ZONE-A1",
  "actuator_type": "solenoid_valve",
  "command": "OPEN",
  "duration_seconds": 1800,
  "issued_at": "2026-02-27T10:00:00Z",
  "issued_by": "irrigation_agent_v2",
  "cycle_id": "cycle-2026-02-27-001"
}
```

#### Feedback Format
```json
{
  "actuator_id": "VALVE-ZONE-A1",
  "actuator_type": "solenoid_valve",
  "current_state": "OPEN",
  "state_since": "2026-02-27T10:00:02Z",
  "scheduled_close": "2026-02-27T10:30:00Z",
  "flow_lpm": 45.2,
  "total_liters_session": 850
}
```

---

### 2. Pumps

#### Submersible / Centrifugal Pump
| Attribute | Value |
|-----------|-------|
| Control | Relay / Contactor |
| Voltage | 220V AC (single phase) |
| Power | 0.5 - 5 HP typical |
| Interface | Relay contact (NO/NC) |

#### VFD-Controlled Pump (Variable Speed)
| Attribute | Value |
|-----------|-------|
| Control | Variable Frequency Drive |
| Interface | Modbus RTU / 0-10V analog |
| Speed Range | 20-100% |
| Soft Start | Yes |

#### Command Format
```json
{
  "actuator_id": "PUMP-MAIN",
  "actuator_type": "pump",
  "command": "START",
  "speed_pct": 75,
  "max_runtime_seconds": 7200,
  "issued_at": "2026-02-27T06:00:00Z",
  "issued_by": "water_agent"
}
```

#### Feedback Format
```json
{
  "actuator_id": "PUMP-MAIN",
  "actuator_type": "pump",
  "current_state": "RUNNING",
  "speed_pct": 75,
  "current_amps": 8.2,
  "runtime_seconds": 1234,
  "total_liters": 2850,
  "inlet_pressure_bar": 1.2,
  "outlet_pressure_bar": 2.8
}
```

---

### 3. Drip Zone Controllers

#### Multi-Zone Manifold
| Attribute | Value |
|-----------|-------|
| Zones | 4-12 per controller |
| Valve Type | Latching solenoid per zone |
| Interface | GPIO / shift register |
| Power | 12V DC |

#### Command Format
```json
{
  "actuator_id": "DRIP-CONTROLLER-1",
  "actuator_type": "drip_zone_controller",
  "commands": [
    {"zone": 1, "state": "OPEN", "duration_seconds": 900},
    {"zone": 2, "state": "OPEN", "duration_seconds": 900},
    {"zone": 3, "state": "CLOSED"},
    {"zone": 4, "state": "CLOSED"}
  ],
  "issued_at": "2026-02-27T05:30:00Z"
}
```

---

### 4. Fertigation Injector

#### Venturi Injector (Simple)
| Attribute | Value |
|-----------|-------|
| Type | Passive venturi |
| Control | Solenoid on suction line |
| Ratio | Fixed (adjust with valve) |

#### Dosing Pump (Precise)
| Attribute | Value |
|-----------|-------|
| Type | Peristaltic / diaphragm |
| Control | Pulse or analog |
| Range | 0.1 - 10 L/hr |
| Interface | GPIO pulse / 4-20mA |

#### Command Format
```json
{
  "actuator_id": "FERT-INJECT-1",
  "actuator_type": "fertigation_injector",
  "command": "INJECT",
  "solution": "NPK-20-20-20",
  "volume_ml": 500,
  "duration_seconds": 300,
  "target_ec_ms_cm": 1.8
}
```

---

## Safety & Interlocks

### Mandatory Interlocks
| Condition | Action |
|-----------|--------|
| Tank level < 10% | Block pump start |
| Flow = 0 while pump running | Stop pump after 30s (dry run) |
| Runtime > max_runtime | Stop pump, close valves |
| Communication loss > 5 min | Close all valves, stop pump |
| Manual override active | Ignore agent commands |

### Interlock Implementation
```python
class ActuatorController:
    def execute(self, command: ActuatorCommand) -> ActuatorResult:
        # Check interlocks
        if command.actuator_type == "pump":
            if self.tank_level_pct < 10:
                return ActuatorResult(
                    success=False,
                    reason="INTERLOCK: Tank level too low",
                    interlock_code="TANK_LOW"
                )
            if self.manual_override_active:
                return ActuatorResult(
                    success=False,
                    reason="INTERLOCK: Manual override active",
                    interlock_code="MANUAL_OVERRIDE"
                )
        
        # Execute command
        ...
```

---

## Communication Architecture

### Field Controller (ESP32-based)
```
┌─────────────────────────────────────────┐
│  Field Controller (per irrigation zone) │
├─────────────────────────────────────────┤
│  ESP32 + LoRa                           │
│  ├── GPIO → Relay board (4-8 channels)  │
│  ├── I2C → Sensor hub                   │
│  └── UART → Flow meter                  │
├─────────────────────────────────────────┤
│  Relays control:                        │
│  - Zone solenoid valves (2-4)           │
│  - Fertigation injector                 │
│  - Aux outputs                          │
└─────────────────────────────────────────┘
        │
        │ LoRa (868 MHz)
        ▼
┌─────────────────────────────────────────┐
│  Central Gateway (Raspberry Pi)         │
├─────────────────────────────────────────┤
│  - LoRa HAT (field comms)               │
│  - WiFi/4G (cloud uplink)               │
│  - AgriMesh orchestrator                │
│  - Local decision cache                 │
│  └── Pump controller (direct or relay)  │
└─────────────────────────────────────────┘
```

### Command Flow
```
AgriMesh Orchestrator
    │
    ▼ (ActionPlan)
Gateway Controller
    │
    ▼ (Validate + queue)
Command Scheduler
    │
    ▼ (LoRa packet)
Field Controller
    │
    ▼ (GPIO/Relay)
Physical Actuator
    │
    ▼ (Feedback)
Field Controller
    │
    ▼ (LoRa packet)
Gateway → Orchestrator (OutcomeLog)
```

---

## Command Queue & Timing

### Scheduling Rules
1. **Irrigation windows**: Default 05:00-09:00, 17:00-20:00 (avoid midday evaporation)
2. **Zone sequencing**: Max 2 zones simultaneously (pump capacity)
3. **Minimum runtime**: 10 minutes per zone (even water distribution)
4. **Cooldown**: 5 minutes between pump stop/start

### Queue Structure
```json
{
  "queue_id": "2026-02-27-morning",
  "scheduled_start": "2026-02-27T05:00:00Z",
  "commands": [
    {
      "sequence": 1,
      "actuator_id": "PUMP-MAIN",
      "command": "START",
      "delay_seconds": 0
    },
    {
      "sequence": 2,
      "actuator_id": "VALVE-ZONE-A1",
      "command": "OPEN",
      "duration_seconds": 1800,
      "delay_seconds": 10
    },
    {
      "sequence": 3,
      "actuator_id": "VALVE-ZONE-A2",
      "command": "OPEN",
      "duration_seconds": 1800,
      "delay_seconds": 1810
    }
  ],
  "on_complete": "STOP_PUMP",
  "on_failure": "EMERGENCY_STOP"
}
```

---

## Human Approval Flow

### High-Risk Actions (Require Approval)
- Fertigation injection
- Pump runtime > 4 hours
- Irrigation during non-standard hours
- Any command marked `risk_level: HIGH` by orchestrator

### Approval Interface
```json
{
  "approval_request_id": "APR-2026-02-27-001",
  "action_summary": "Irrigate Zone A1-A4 with NPK solution",
  "requested_by": "crop_operations_agent",
  "risk_level": "HIGH",
  "reason": "Fertigation operation",
  "expires_at": "2026-02-27T04:30:00Z",
  "channels": ["sms", "app_notification"],
  "approve_code": "APPROVE-7829",
  "reject_code": "REJECT-7829"
}
```

---

## Bill of Materials (Reference)

### Per-Zone Actuator Kit
| Component | Qty | Est. Cost (USD) |
|-----------|-----|-----------------|
| Latching solenoid valve (1") | 2 | $30 |
| 4-channel relay module | 1 | $5 |
| ESP32 + LoRa (same as sensor) | 1 | $15 |
| Wiring, connectors | 1 | $10 |
| Enclosure (IP65) | 1 | $10 |
| **Zone actuator total** | - | **~$70** |

### Pump Controller Kit
| Component | Qty | Est. Cost (USD) |
|-----------|-----|-----------------|
| Contactor (25A) | 1 | $25 |
| Current sensor (SCT-013) | 1 | $8 |
| Pressure transducer | 2 | $40 |
| ESP32 controller | 1 | $15 |
| Enclosure | 1 | $15 |
| **Pump controller total** | - | **~$100** |

---

## Integration with AgriMesh

### ActionPlan → Actuator Commands
```python
def translate_action_plan(plan: ActionPlan) -> List[ActuatorCommand]:
    commands = []
    
    for plot_id, liters in plan.irrigation_by_plot_liters.items():
        if liters > 0:
            zone = plot_to_zone_mapping[plot_id]
            duration = calculate_duration(liters, zone.flow_rate_lpm)
            
            commands.append(ActuatorCommand(
                actuator_id=zone.valve_id,
                command="OPEN",
                duration_seconds=duration,
                issued_by=plan.agent_id,
                cycle_id=plan.cycle_id,
            ))
    
    return commands
```

### Feedback → OutcomeLog
```python
def update_outcome_from_feedback(
    outcome: OutcomeLog,
    feedback: List[ActuatorFeedback]
) -> OutcomeLog:
    actual_water = sum(f.total_liters_session for f in feedback if f.actuator_type == "solenoid_valve")
    
    outcome.actual_changes["total_water_applied_liters"] = actual_water
    outcome.actual_changes["actuator_feedback"] = [asdict(f) for f in feedback]
    
    return outcome
```
