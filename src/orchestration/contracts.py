from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any

from src.common.models import FarmState


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"


class RiskLevel(str, Enum):
    SAFE = "safe"
    GUARDED = "guarded"
    HUMAN_APPROVAL = "human_approval"


@dataclass
class ActionProposal:
    action_type: str
    target: str
    params: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    risk: RiskLevel = RiskLevel.SAFE


@dataclass
class AgentOutput:
    agent_id: str
    observations: Dict[str, Any] = field(default_factory=dict)
    proposals: List[ActionProposal] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)


@dataclass
class AgentContext:
    cycle_id: str
    mode: str  # wet_season | dry_season
    farm_state: FarmState
    budgets: Dict[str, float] = field(default_factory=dict)
