"""
Abstract hardware interfaces for AgriMesh.

These interfaces define the contract between AgriMesh software agents
and physical sensors/actuators. Implementations can be:
- SimulatedHardware (for testing)
- LoRaHardware (field deployment)
- MockHardware (unit tests)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SensorType(Enum):
    SOIL_MOISTURE = "soil_moisture"
    TEMPERATURE = "temperature"
    RAINFALL = "rainfall"
    TANK_LEVEL = "tank_level"
    FLOW_METER = "flow_meter"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"


class ActuatorType(Enum):
    SOLENOID_VALVE = "solenoid_valve"
    PUMP = "pump"
    DRIP_ZONE = "drip_zone"
    FERTIGATION = "fertigation"


class ActuatorState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass
class SensorReading:
    """Universal sensor reading container."""
    sensor_id: str
    sensor_type: SensorType
    timestamp: datetime
    readings: Dict[str, float]
    unit: str
    zone_id: Optional[str] = None
    battery_pct: Optional[float] = None
    signal_rssi: Optional[int] = None
    raw_value: Optional[Any] = None


@dataclass
class ActuatorCommand:
    """Command to send to an actuator."""
    actuator_id: str
    actuator_type: ActuatorType
    command: str  # "OPEN", "CLOSE", "START", "STOP", etc.
    issued_at: datetime
    issued_by: str  # Agent ID
    cycle_id: str
    duration_seconds: Optional[int] = None
    speed_pct: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActuatorFeedback:
    """Feedback from actuator after command execution."""
    actuator_id: str
    actuator_type: ActuatorType
    current_state: ActuatorState
    state_since: datetime
    command_acknowledged: bool
    execution_latency_ms: int
    total_liters_session: Optional[float] = None
    flow_lpm: Optional[float] = None
    current_amps: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class InterlockStatus:
    """Status of safety interlocks."""
    interlock_id: str
    description: str
    is_tripped: bool
    tripped_at: Optional[datetime] = None
    reason: Optional[str] = None


class SensorInterface(ABC):
    """Abstract interface for reading sensors."""
    
    @abstractmethod
    def get_reading(self, sensor_id: str) -> SensorReading:
        """Get current reading from a specific sensor."""
        pass
    
    @abstractmethod
    def get_all_readings(self, sensor_type: Optional[SensorType] = None) -> List[SensorReading]:
        """Get readings from all sensors, optionally filtered by type."""
        pass
    
    @abstractmethod
    def get_sensor_ids(self) -> List[str]:
        """List all registered sensor IDs."""
        pass


class ActuatorInterface(ABC):
    """Abstract interface for controlling actuators."""
    
    @abstractmethod
    def execute(self, command: ActuatorCommand) -> ActuatorFeedback:
        """Execute a command on an actuator."""
        pass
    
    @abstractmethod
    def get_state(self, actuator_id: str) -> ActuatorFeedback:
        """Get current state of an actuator."""
        pass
    
    @abstractmethod
    def emergency_stop(self) -> List[ActuatorFeedback]:
        """Emergency stop all actuators."""
        pass
    
    @abstractmethod
    def check_interlocks(self) -> List[InterlockStatus]:
        """Check all safety interlocks."""
        pass


class HardwareManager(ABC):
    """
    Combined interface for all hardware operations.
    
    Implementations should handle:
    - Sensor polling and caching
    - Actuator command queuing
    - Interlock enforcement
    - Communication retries
    """
    
    @property
    @abstractmethod
    def sensors(self) -> SensorInterface:
        pass
    
    @property
    @abstractmethod
    def actuators(self) -> ActuatorInterface:
        pass
    
    @abstractmethod
    def sync(self) -> Dict[str, Any]:
        """Synchronize state with physical hardware."""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check overall hardware health."""
        pass


# Simulated implementation for testing

class SimulatedSensors(SensorInterface):
    """Simulated sensors for testing."""
    
    def __init__(self, initial_state: Dict[str, SensorReading] = None):
        self._state = initial_state or {}
    
    def set_reading(self, sensor_id: str, reading: SensorReading):
        """Set a simulated reading (for tests)."""
        self._state[sensor_id] = reading
    
    def get_reading(self, sensor_id: str) -> SensorReading:
        if sensor_id not in self._state:
            raise KeyError(f"Unknown sensor: {sensor_id}")
        return self._state[sensor_id]
    
    def get_all_readings(self, sensor_type: Optional[SensorType] = None) -> List[SensorReading]:
        readings = list(self._state.values())
        if sensor_type:
            readings = [r for r in readings if r.sensor_type == sensor_type]
        return readings
    
    def get_sensor_ids(self) -> List[str]:
        return list(self._state.keys())


class SimulatedActuators(ActuatorInterface):
    """Simulated actuators for testing."""
    
    def __init__(self):
        self._states: Dict[str, ActuatorFeedback] = {}
        self._interlocks: List[InterlockStatus] = []
    
    def add_actuator(self, actuator_id: str, actuator_type: ActuatorType):
        """Register a simulated actuator."""
        self._states[actuator_id] = ActuatorFeedback(
            actuator_id=actuator_id,
            actuator_type=actuator_type,
            current_state=ActuatorState.CLOSED if actuator_type == ActuatorType.SOLENOID_VALVE else ActuatorState.STOPPED,
            state_since=datetime.now(),
            command_acknowledged=True,
            execution_latency_ms=0,
        )
    
    def execute(self, command: ActuatorCommand) -> ActuatorFeedback:
        if command.actuator_id not in self._states:
            raise KeyError(f"Unknown actuator: {command.actuator_id}")
        
        # Check interlocks
        tripped = [i for i in self._interlocks if i.is_tripped]
        if tripped:
            return ActuatorFeedback(
                actuator_id=command.actuator_id,
                actuator_type=command.actuator_type,
                current_state=ActuatorState.ERROR,
                state_since=datetime.now(),
                command_acknowledged=False,
                execution_latency_ms=0,
                error_code="INTERLOCK",
                error_message=f"Interlock tripped: {tripped[0].description}",
            )
        
        # Simulate command execution
        if command.command in ("OPEN", "START"):
            new_state = ActuatorState.OPEN if command.actuator_type == ActuatorType.SOLENOID_VALVE else ActuatorState.RUNNING
        else:
            new_state = ActuatorState.CLOSED if command.actuator_type == ActuatorType.SOLENOID_VALVE else ActuatorState.STOPPED
        
        self._states[command.actuator_id] = ActuatorFeedback(
            actuator_id=command.actuator_id,
            actuator_type=command.actuator_type,
            current_state=new_state,
            state_since=datetime.now(),
            command_acknowledged=True,
            execution_latency_ms=50,  # Simulated latency
        )
        
        return self._states[command.actuator_id]
    
    def get_state(self, actuator_id: str) -> ActuatorFeedback:
        if actuator_id not in self._states:
            raise KeyError(f"Unknown actuator: {actuator_id}")
        return self._states[actuator_id]
    
    def emergency_stop(self) -> List[ActuatorFeedback]:
        results = []
        for actuator_id, state in self._states.items():
            new_state = ActuatorState.CLOSED if state.actuator_type == ActuatorType.SOLENOID_VALVE else ActuatorState.STOPPED
            self._states[actuator_id] = ActuatorFeedback(
                actuator_id=actuator_id,
                actuator_type=state.actuator_type,
                current_state=new_state,
                state_since=datetime.now(),
                command_acknowledged=True,
                execution_latency_ms=10,
            )
            results.append(self._states[actuator_id])
        return results
    
    def check_interlocks(self) -> List[InterlockStatus]:
        return self._interlocks
    
    def set_interlock(self, interlock: InterlockStatus):
        """Set interlock state (for tests)."""
        self._interlocks = [i for i in self._interlocks if i.interlock_id != interlock.interlock_id]
        self._interlocks.append(interlock)


class SimulatedHardwareManager(HardwareManager):
    """Simulated hardware manager for testing."""
    
    def __init__(self):
        self._sensors = SimulatedSensors()
        self._actuators = SimulatedActuators()
    
    @property
    def sensors(self) -> SensorInterface:
        return self._sensors
    
    @property
    def actuators(self) -> ActuatorInterface:
        return self._actuators
    
    def sync(self) -> Dict[str, Any]:
        return {
            "synced_at": datetime.now().isoformat(),
            "sensors": len(self._sensors.get_sensor_ids()),
            "actuators": len(self._actuators._states),
            "status": "OK",
        }
    
    def health_check(self) -> Dict[str, Any]:
        interlocks = self._actuators.check_interlocks()
        tripped = [i for i in interlocks if i.is_tripped]
        return {
            "healthy": len(tripped) == 0,
            "interlocks_tripped": len(tripped),
            "sensors_online": len(self._sensors.get_sensor_ids()),
            "actuators_online": len(self._actuators._states),
        }
