# AgriMesh Sensor Specification v1

## Overview
This document defines the sensor interfaces for AgriMesh field deployment in Zimbabwe.

Design principles:
- **Rugged**: Designed for dusty, wet, high-UV environments
- **Low-power**: Solar-capable, battery backup
- **Affordable**: Prioritize value sensors over premium
- **Repairable**: Common components, local sourcing where possible

---

## Sensor Categories

### 1. Soil Moisture Sensors

#### Primary: Capacitive Soil Moisture (Recommended)
| Attribute | Value |
|-----------|-------|
| Type | Capacitive (corrosion-resistant) |
| Output | Analog (0-3.3V) or I2C |
| Range | 0-100% VWC |
| Accuracy | ±3% VWC |
| Power | 3.3V, <20mA active |
| Depth | 15cm, 30cm, 60cm (multi-depth recommended) |
| Examples | Adafruit STEMMA, DFRobot SEN0193 |

#### Alternative: TDR/FDR Probes (Higher accuracy)
| Attribute | Value |
|-----------|-------|
| Type | Time Domain Reflectometry |
| Output | SDI-12 or Modbus RTU |
| Range | 0-100% VWC |
| Accuracy | ±1-2% VWC |
| Power | 12V, <50mA |
| Examples | Meter TEROS 10, Campbell CS616 |

#### Data Format
```json
{
  "sensor_id": "SM-001",
  "sensor_type": "soil_moisture",
  "timestamp": "2026-02-27T10:00:00Z",
  "readings": {
    "depth_15cm": 0.42,
    "depth_30cm": 0.48,
    "depth_60cm": 0.52
  },
  "unit": "vwc_fraction",
  "battery_pct": 85,
  "signal_rssi": -67
}
```

---

### 2. Temperature Sensors

#### Soil Temperature
| Attribute | Value |
|-----------|-------|
| Type | DS18B20 (waterproof) |
| Output | 1-Wire digital |
| Range | -55°C to +125°C |
| Accuracy | ±0.5°C |
| Power | 3.3-5V, <1mA |
| Depth | 10cm, 30cm |

#### Air Temperature + Humidity
| Attribute | Value |
|-----------|-------|
| Type | BME280 / SHT40 |
| Output | I2C / SPI |
| Temp Range | -40°C to +85°C |
| Humidity Range | 0-100% RH |
| Accuracy | ±0.5°C, ±3% RH |
| Power | 3.3V, <1mA |

#### Data Format
```json
{
  "sensor_id": "TEMP-001",
  "sensor_type": "temperature",
  "timestamp": "2026-02-27T10:00:00Z",
  "readings": {
    "air_temp_c": 28.5,
    "air_humidity_pct": 62.3,
    "soil_temp_10cm_c": 24.2,
    "soil_temp_30cm_c": 22.8
  },
  "battery_pct": 92
}
```

---

### 3. Rain Gauge

#### Tipping Bucket (Recommended)
| Attribute | Value |
|-----------|-------|
| Type | Tipping bucket |
| Resolution | 0.2mm or 0.5mm per tip |
| Output | Pulse (reed switch) |
| Range | 0-400mm/hr |
| Power | Passive (no power needed) |
| Examples | Davis 6466, generic ABS units |

#### Data Format
```json
{
  "sensor_id": "RAIN-001",
  "sensor_type": "rainfall",
  "timestamp": "2026-02-27T10:00:00Z",
  "readings": {
    "tips_since_last": 12,
    "mm_since_last": 2.4,
    "total_season_mm": 342.6
  },
  "interval_seconds": 900
}
```

---

### 4. Tank Level Sensor

#### Ultrasonic (Non-contact)
| Attribute | Value |
|-----------|-------|
| Type | Ultrasonic distance |
| Output | Analog / UART / I2C |
| Range | 20cm - 4m |
| Accuracy | ±1cm |
| Power | 5V, <30mA |
| Examples | JSN-SR04T (waterproof), A02YYUW |

#### Pressure Transducer (Submersible)
| Attribute | Value |
|-----------|-------|
| Type | Hydrostatic pressure |
| Output | 4-20mA / 0-5V |
| Range | 0-10m water column |
| Accuracy | ±0.5% FS |
| Power | 12-24V |

#### Data Format
```json
{
  "sensor_id": "TANK-001",
  "sensor_type": "tank_level",
  "timestamp": "2026-02-27T10:00:00Z",
  "readings": {
    "level_liters": 4520,
    "level_pct": 45.2,
    "distance_cm": 182
  },
  "tank_capacity_liters": 10000
}
```

---

### 5. Flow Meter

#### Pulse Flow Meter
| Attribute | Value |
|-----------|-------|
| Type | Hall-effect pulse |
| Output | Pulse (frequency proportional to flow) |
| Range | 1-60 L/min typical |
| Accuracy | ±2-5% |
| Power | 5V, <10mA |
| Pipe Size | 1/2", 3/4", 1" |
| Examples | YF-S201, YF-DN50 |

#### Data Format
```json
{
  "sensor_id": "FLOW-001",
  "sensor_type": "flow_meter",
  "timestamp": "2026-02-27T10:00:00Z",
  "readings": {
    "current_lpm": 12.5,
    "total_liters_session": 1850,
    "total_liters_lifetime": 45230
  }
}
```

---

## Communication Protocols

### Field Network: LoRa (Recommended)
| Attribute | Value |
|-----------|-------|
| Frequency | 868 MHz (Africa) |
| Range | 2-15 km (line of sight) |
| Data Rate | 0.3-50 kbps |
| Topology | Star (sensors → gateway) |
| Protocol | LoRaWAN or proprietary |

### Local Bus: I2C / 1-Wire
- Short-range sensor clusters
- Single microcontroller hub per zone

### Gateway Uplink: Cellular / WiFi
| Option | Use Case |
|--------|----------|
| 4G LTE | Remote farms, no WiFi |
| WiFi | Near homestead |
| Ethernet | Permanent installations |

---

## Polling Intervals

| Sensor Type | Interval | Rationale |
|-------------|----------|-----------|
| Soil moisture | 15 min | Slow-changing, battery conservation |
| Temperature | 15 min | Slow-changing |
| Rainfall | Event-triggered + 15 min summary | Capture real-time events |
| Tank level | 5 min | Track rapid changes during irrigation |
| Flow meter | Continuous during pump operation | Precise water accounting |

---

## Bill of Materials (Reference)

### Minimum Viable Sensor Kit (per zone)
| Component | Qty | Est. Cost (USD) |
|-----------|-----|-----------------|
| Capacitive soil moisture sensor | 2 | $10 |
| DS18B20 soil temperature | 1 | $3 |
| BME280 air temp/humidity | 1 | $5 |
| Tipping bucket rain gauge | 1 (shared) | $25 |
| ESP32 + LoRa module | 1 | $15 |
| Solar panel (5W) | 1 | $10 |
| 18650 battery + holder | 1 | $5 |
| Enclosure (IP65) | 1 | $8 |
| **Zone total** | - | **~$80** |

### Gateway Kit
| Component | Qty | Est. Cost (USD) |
|-----------|-----|-----------------|
| Raspberry Pi 4 | 1 | $55 |
| LoRa HAT | 1 | $25 |
| 4G USB modem | 1 | $30 |
| Power supply + UPS | 1 | $20 |
| Weatherproof enclosure | 1 | $15 |
| **Gateway total** | - | **~$145** |

---

## Integration Notes

### AgriMesh State Mapping
```python
# Sensor reading → FarmState update
def update_state_from_sensors(state: FarmState, readings: List[SensorReading]):
    for reading in readings:
        if reading.sensor_type == "soil_moisture":
            plot = find_plot(state, reading.zone_id)
            plot.soil_moisture = reading.readings["depth_15cm"]
        elif reading.sensor_type == "tank_level":
            state.water_system.tank_level_liters = reading.readings["level_liters"]
        elif reading.sensor_type == "rainfall":
            state.weather.rainfall_mm += reading.readings["mm_since_last"]
        # etc.
```

### Calibration Requirements
- Soil moisture: Site-specific calibration recommended (VWC vs. raw reading)
- Tank level: Configure tank geometry (diameter, height)
- Flow meter: Verify pulse-per-liter constant

---

## Future Considerations
- NDVI/crop health cameras
- Weather station integration (wind, solar radiation)
- Livestock water trough sensors
- GPS/GNSS for geo-referenced readings
