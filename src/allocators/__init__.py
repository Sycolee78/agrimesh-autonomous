# AgriMesh Allocators - AEZ-aware farm optimization
"""
Farm allocation optimizer for Zimbabwe.
Given geo point + area + goals → produces optimal land allocation,
livestock plan, rotation schedule, and agent deployment.
"""

from .optimizer import run_allocation, FarmAllocationResult
from .aez_lookup import AEZLookupAgent, AEZProfile
from .suitability import SuitabilityAgent, CropSuitability, LivestockSuitability
from .profit_estimator import ProfitEstimatorAgent, ProfitEstimate
from .resource_agent import ResourceAgent, ResourcePlan
from .scheduler import SchedulerAgent, FarmSchedule
from .deployment import DeploymentAgent, AgentDeploymentPlan

__all__ = [
    "run_allocation",
    "FarmAllocationResult",
    "AEZLookupAgent",
    "AEZProfile",
    "SuitabilityAgent",
    "CropSuitability",
    "LivestockSuitability",
    "ProfitEstimatorAgent",
    "ProfitEstimate",
    "ResourceAgent",
    "ResourcePlan",
    "SchedulerAgent",
    "FarmSchedule",
    "DeploymentAgent",
    "AgentDeploymentPlan",
]
