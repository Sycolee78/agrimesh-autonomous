"""
AEZ Optimizer API - High-level interface for farm allocation.
Main entry point for the allocation pipeline.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

from .aez_lookup import AEZLookupAgent, AEZProfile
from .suitability import SuitabilityAgent
from .profit_estimator import ProfitEstimatorAgent
from .resource_agent import ResourceAgent
from .optimizer import OptimizerAgent, FarmAllocationResult
from .scheduler import SchedulerAgent
from .deployment import DeploymentAgent, AgentDeploymentPlan


@dataclass
class AllocationRequest:
    """Input request for farm allocation."""
    location: Dict[str, float]  # lat, lon
    area_ha: float
    objective: str = "maximize_profit"  # maximize_profit | food_security | soil_building
    constraints: Optional[Dict[str, Any]] = None
    market_access: Optional[Dict[str, Any]] = None
    soil: Optional[Dict[str, Any]] = None
    season: Optional[Dict[str, Any]] = None
    allowed_enterprises: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AllocationRequest":
        return cls(
            location=data["location"],
            area_ha=data["area_ha"],
            objective=data.get("objective", "maximize_profit"),
            constraints=data.get("constraints"),
            market_access=data.get("market_access"),
            soil=data.get("soil"),
            season=data.get("season"),
            allowed_enterprises=data.get("allowed_enterprises"),
        )


@dataclass
class AllocationResponse:
    """Complete response from allocation pipeline."""
    status: str
    location: Dict[str, float]
    aez_profile: Dict[str, Any]
    allocation: Dict[str, Any]
    rotation: List[Dict[str, Any]]
    profit_estimate: Dict[str, Any]
    resource_plan: Dict[str, Any]
    schedule: Dict[str, Any]
    agents_plan: Dict[str, Any]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "location": self.location,
            "aez_profile": self.aez_profile,
            "allocation": self.allocation,
            "rotation": self.rotation,
            "profit_estimate": self.profit_estimate,
            "resource_plan": self.resource_plan,
            "schedule": self.schedule,
            "agents_plan": self.agents_plan,
            "summary": self.summary,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class AEZOptimizerAPI:
    """
    Main API for the AEZ-aware farm optimizer.
    
    Usage:
        api = AEZOptimizerAPI()
        result = api.optimize({
            "location": {"lat": -17.8, "lon": 31.0},
            "area_ha": 7.0,
            "objective": "maximize_profit",
            "constraints": {"max_labor_days_per_year": 1000},
            "allowed_enterprises": ["maize", "goats", "poultry", "groundnuts", "vegetables"]
        })
    """
    
    def __init__(self):
        self.aez_agent = AEZLookupAgent()
        self.suitability_agent = SuitabilityAgent(self.aez_agent)
        self.optimizer_agent = OptimizerAgent(self.aez_agent, self.suitability_agent)
        self.scheduler_agent = SchedulerAgent()
        self.deployment_agent = DeploymentAgent()
    
    def lookup_aez(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Look up AEZ profile for coordinates.
        
        Returns:
            Dict with zone info, crop suitability, livestock capacity
        """
        profile = self.aez_agent.lookup(lat, lon)
        return profile.to_dict()
    
    def get_suitability(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        objective: str = "maximize_profit",
        market_distance_km: float = 20,
    ) -> Dict[str, Any]:
        """
        Get enterprise suitability rankings for a location.
        
        Returns:
            Dict with ranked crops and livestock
        """
        return self.suitability_agent.recommend_enterprise_mix(
            lat, lon, area_ha, objective, market_distance_km=market_distance_km
        )
    
    def _generate_rotation_plan(
        self,
        crop_allocations: Dict[str, float],
        years: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate simple rotation plan.
        """
        rotations = []
        
        # Get legume and non-legume crops
        legumes = [c for c in crop_allocations if c in ["groundnuts", "soybean", "cowpeas"]]
        cereals = [c for c in crop_allocations if c in ["maize", "sorghum"]]
        others = [c for c in crop_allocations if c not in legumes + cereals]
        
        for year in range(1, years + 1):
            year_plan = {"year": year, "allocations": {}}
            
            # Simple rotation: alternate legumes with cereals on some land
            if year % 2 == 1:
                # Odd years: normal allocation
                for crop, area in crop_allocations.items():
                    year_plan["allocations"][crop] = f"{area:.1f}ha"
            else:
                # Even years: swap some cereal area for legumes
                for crop, area in crop_allocations.items():
                    if crop in cereals and legumes:
                        # Reduce cereal, increase legume
                        swap_area = area * 0.2
                        year_plan["allocations"][crop] = f"{area - swap_area:.1f}ha"
                        year_plan["allocations"][legumes[0]] = f"{crop_allocations.get(legumes[0], 0) + swap_area:.1f}ha"
                    else:
                        year_plan["allocations"][crop] = f"{area:.1f}ha"
                
                year_plan["notes"] = "Increased legume area for N-fixation"
            
            rotations.append(year_plan)
        
        return rotations
    
    def optimize(self, request: Dict[str, Any]) -> AllocationResponse:
        """
        Run full optimization pipeline.
        
        Args:
            request: Dict with location, area_ha, objective, constraints, etc.
            
        Returns:
            AllocationResponse with complete farm plan
        """
        # Parse request
        req = AllocationRequest.from_dict(request)
        
        lat = req.location["lat"]
        lon = req.location["lon"]
        
        # Get market distance
        market_km = 20
        if req.market_access:
            market_km = req.market_access.get("distance_km", 20)
        
        # Run optimizer
        opt_result = self.optimizer_agent.optimize(
            lat=lat,
            lon=lon,
            area_ha=req.area_ha,
            objective=req.objective,
            constraints=req.constraints,
            allowed_enterprises=req.allowed_enterprises,
            market_distance_km=market_km,
        )
        
        # Extract allocations
        crop_allocs = opt_result["allocation"]["crop_allocations_ha"]
        livestock_counts = opt_result["allocation"]["livestock_counts"]
        
        # Generate rotation plan
        rotation = self._generate_rotation_plan(crop_allocs, years=3)
        
        # Generate schedule
        schedule = self.scheduler_agent.generate_schedule(
            crop_allocs,
            livestock_counts,
            zone=opt_result["aez_profile"]["zone"],
        )
        
        # Generate deployment plan
        deployment = self.deployment_agent.create_deployment_plan(
            lat=lat,
            lon=lon,
            area_ha=req.area_ha,
            crop_allocations=crop_allocs,
            livestock_counts=livestock_counts,
        )
        
        # Build summary
        summary = {
            "zone": opt_result["aez_profile"]["zone"],
            "zone_name": opt_result["aez_profile"]["zone_name"],
            "drought_risk": opt_result["aez_profile"]["drought_risk"],
            "total_area_ha": req.area_ha,
            "crop_area_ha": sum(crop_allocs.values()),
            "infrastructure_ha": opt_result["allocation"]["infrastructure_ha"],
            "crops": list(crop_allocs.keys()),
            "livestock": list(livestock_counts.keys()),
            "total_livestock": sum(livestock_counts.values()),
            "expected_profit_yr1": opt_result["profit_projection"]["yearly_projections"][0]["total_profit_usd"]["expected"],
            "npv_3yr": opt_result["profit_projection"]["npv_usd"]["expected"],
            "labor_days_year": opt_result["resource_plan"]["labor"]["total_labor_days_year"],
            "water_m3_year": opt_result["resource_plan"]["water"]["total_m3_year"],
            "capex_required": opt_result["resource_plan"]["infrastructure"]["estimated_capex_usd"],
            "agents_deployed": len(deployment.agents),
        }
        
        return AllocationResponse(
            status="success",
            location=req.location,
            aez_profile=opt_result["aez_profile"],
            allocation={
                "crops": [
                    {"enterprise": crop, "ha": area}
                    for crop, area in crop_allocs.items()
                    if area > 0
                ],
                "livestock": [
                    {"type": ls, "count": count}
                    for ls, count in livestock_counts.items()
                    if count > 0
                ],
            },
            rotation=rotation,
            profit_estimate=opt_result["profit_projection"],
            resource_plan=opt_result["resource_plan"],
            schedule=schedule.to_dict(),
            agents_plan=deployment.to_dict(),
            summary=summary,
        )
    
    def get_all_zones(self) -> Dict[str, Dict]:
        """Get all AEZ zone definitions."""
        return self.aez_agent.get_all_zones()
    
    def get_market_prices(self) -> Dict[str, Dict]:
        """Get current market price data."""
        return self.aez_agent.get_market_prices()


# Convenience function for direct use
def optimize_farm(
    lat: float,
    lon: float,
    area_ha: float,
    objective: str = "maximize_profit",
    constraints: Optional[Dict] = None,
    allowed_enterprises: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Quick function to optimize a farm allocation.
    
    Args:
        lat, lon: Farm coordinates
        area_ha: Total farm area
        objective: maximize_profit | food_security | soil_building
        constraints: Optional dict with max_labor_days_per_year, water_available_m3
        allowed_enterprises: Optional list of allowed crops/livestock
        
    Returns:
        Dict with complete allocation result
    """
    api = AEZOptimizerAPI()
    result = api.optimize({
        "location": {"lat": lat, "lon": lon},
        "area_ha": area_ha,
        "objective": objective,
        "constraints": constraints or {},
        "allowed_enterprises": allowed_enterprises,
    })
    return result.to_dict()


if __name__ == "__main__":
    # Test the API
    api = AEZOptimizerAPI()
    
    result = api.optimize({
        "location": {"lat": -17.83, "lon": 31.05},
        "area_ha": 7.0,
        "objective": "maximize_profit",
        "constraints": {"max_labor_days_per_year": 1000},
        "market_access": {"distance_km": 15},
        "allowed_enterprises": ["maize", "groundnuts", "vegetables", "fodder", "goats", "poultry"],
    })
    
    print(f"Zone: {result.summary['zone']} - {result.summary['zone_name']}")
    print(f"\nAllocation:")
    for crop in result.allocation["crops"]:
        print(f"  {crop['enterprise']}: {crop['ha']:.1f} ha")
    for ls in result.allocation["livestock"]:
        print(f"  {ls['type']}: {ls['count']} head")
    
    print(f"\nFinancials:")
    print(f"  Year 1 profit: ${result.summary['expected_profit_yr1']:.0f}")
    print(f"  3-year NPV: ${result.summary['npv_3yr']:.0f}")
    print(f"  Infrastructure capex: ${result.summary['capex_required']:.0f}")
    
    print(f"\nResources:")
    print(f"  Labor: {result.summary['labor_days_year']:.0f} days/year")
    print(f"  Water: {result.summary['water_m3_year']:.0f} m³/year")
    
    print(f"\nAgents deployed: {result.summary['agents_deployed']}")
