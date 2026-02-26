"""
Farm Allocation Pipeline - Complete end-to-end farm planning.
Orchestrates all agents to produce a comprehensive farm plan from coordinates.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

from .aez_lookup import AEZLookupAgent, AEZProfile
from .suitability import SuitabilityAgent
from .profit_estimator import ProfitEstimatorAgent, Scenario
from .optimizer import optimize_farm, FarmAllocationResult
from .resource_agent import ResourceAgent, ResourcePlan
from .scheduler import SchedulerAgent, FarmSchedule
from .deployment import DeploymentAgent, AgentDeploymentPlan


@dataclass
class FarmPlanRequest:
    """Input request for farm planning."""
    location: Dict[str, float]  # {"lat": -17.8, "lon": 31.0}
    area_ha: float
    objective: str = "maximize_profit"  # maximize_profit | food_security | soil_building
    
    # Optional constraints
    constraints: Dict[str, Any] = field(default_factory=dict)
    # max_labor_days_per_year, water_available_m3, etc.
    
    # Optional filters
    allowed_enterprises: Optional[List[str]] = None
    
    # Market access
    market_distance_km: float = 20
    
    # Existing infrastructure
    existing_infrastructure: Optional[List[str]] = None
    
    # Planning horizon
    planning_years: int = 3


@dataclass
class FarmPlan:
    """Complete farm plan output."""
    # Request info
    location: Dict[str, float]
    area_ha: float
    objective: str
    
    # AEZ context
    aez_profile: Dict[str, Any]
    
    # Allocation
    allocation: Dict[str, Any]  # From optimizer
    
    # Economics
    profit_estimate: Dict[str, Any]
    multi_year_projection: Dict[str, Any]
    
    # Resources
    resource_plan: Dict[str, Any]
    
    # Schedule
    farm_schedule: Dict[str, Any]
    
    # Agent deployment
    agent_deployment: Dict[str, Any]
    
    # 7-ha example comparison (if applicable)
    example_comparison: Optional[Dict[str, Any]] = None
    
    # Recommendations
    key_recommendations: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "area_ha": self.area_ha,
            "objective": self.objective,
            "aez_profile": self.aez_profile,
            "allocation": self.allocation,
            "profit_estimate": self.profit_estimate,
            "multi_year_projection": self.multi_year_projection,
            "resource_plan": self.resource_plan,
            "farm_schedule": self.farm_schedule,
            "agent_deployment": self.agent_deployment,
            "example_comparison": self.example_comparison,
            "key_recommendations": self.key_recommendations,
            "risk_factors": self.risk_factors,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path):
        """Save plan to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())


class FarmAllocationPipeline:
    """
    Main pipeline orchestrating all allocation agents.
    """
    
    def __init__(self):
        self.aez_agent = AEZLookupAgent()
        self.suitability_agent = SuitabilityAgent(self.aez_agent)
        self.profit_agent = ProfitEstimatorAgent()
        self.resource_agent = ResourceAgent()
        self.scheduler_agent = SchedulerAgent()
        self.deployment_agent = DeploymentAgent()
    
    def plan(self, request: FarmPlanRequest) -> FarmPlan:
        """
        Execute complete farm planning pipeline.
        
        Args:
            request: FarmPlanRequest with location and parameters
            
        Returns:
            Complete FarmPlan
        """
        lat = request.location["lat"]
        lon = request.location["lon"]
        
        # Step 1: AEZ Lookup
        aez_profile = self.aez_agent.lookup(lat, lon)
        
        # Step 2: Run optimizer
        allocation_result = optimize_farm(
            lat=lat,
            lon=lon,
            area_ha=request.area_ha,
            objective=request.objective,
            constraints_dict=request.constraints,
            allowed_enterprises=request.allowed_enterprises,
        )
        
        # Step 3: Profit estimation
        # Build params from AEZ data
        crop_params = {}
        for crop, area in allocation_result.crop_allocations.items():
            if area > 0.1:
                suit = aez_profile.crop_suitability.get(crop, {})
                prices = self.aez_agent.get_market_prices()
                costs = self.aez_agent.get_input_costs()
                
                yield_exp = suit.get("yield_t_ha", {}).get("expected", 2)
                price = prices.get(crop, {}).get("typical", 300)
                cost = costs.get(crop, {}).get("total", 200)
                
                # Get additional params
                n_fix = 80 if crop == "groundnuts" else 0
                labor = costs.get(crop, {}).get("labor_days", 40)
                
                crop_params[crop] = {
                    "yield": yield_exp,
                    "price": price,
                    "cost": cost,
                    "labor_days": labor,
                    "n_fixation": n_fix,
                }
        
        livestock_params = {}
        livestock_costs = self.aez_agent.get_livestock_costs()
        prices = self.aez_agent.get_market_prices()
        
        revenue_map = {
            "cattle": "cattle_beef",
            "goats": "goat_meat",
            "poultry": "poultry_broiler",
            "pigs": "pig_meat",
        }
        
        for ls, count in allocation_result.livestock_allocations.items():
            if count > 0:
                price_key = revenue_map.get(ls, ls)
                revenue = prices.get(price_key, {}).get("typical", 100)
                cost = livestock_costs.get(ls, {}).get("total", 50)
                labor = livestock_costs.get(ls, {}).get("labor_days", 10)
                
                livestock_params[ls] = {
                    "revenue": revenue,
                    "cost": cost,
                    "labor_days": labor,
                    "infrastructure": 200 if ls in ["goats", "poultry"] else 500,
                }
        
        # Build allocations dict for profit estimator
        allocations = {**allocation_result.crop_allocations}
        allocations.update({k: v for k, v in allocation_result.livestock_allocations.items()})
        
        # Year 1 estimate
        profit_estimate = self.profit_agent.estimate_farm(
            allocations=allocations,
            crop_params=crop_params,
            livestock_params=livestock_params,
            total_area_ha=request.area_ha,
            year=1,
            scenario=Scenario.EXPECTED,
        )
        
        # Multi-year projection
        multi_year = self.profit_agent.multi_year_projection(
            allocations=allocations,
            crop_params=crop_params,
            livestock_params=livestock_params,
            total_area_ha=request.area_ha,
            years=request.planning_years,
        )
        
        # Step 4: Resource planning
        resource_plan = self.resource_agent.create_resource_plan(
            crop_allocations=allocation_result.crop_allocations,
            livestock_counts=allocation_result.livestock_allocations,
            aez_profile=aez_profile,
            area_ha=request.area_ha,
            constraints=request.constraints,
        )
        
        # Step 5: Scheduling
        farm_schedule = self.scheduler_agent.generate_schedule(
            crop_allocations=allocation_result.crop_allocations,
            livestock_counts=allocation_result.livestock_allocations,
            zone=aez_profile.zone,
        )
        
        # Step 6: Agent deployment
        agent_deployment = self.deployment_agent.create_deployment_plan(
            lat=lat,
            lon=lon,
            area_ha=request.area_ha,
            crop_allocations=allocation_result.crop_allocations,
            livestock_counts=allocation_result.livestock_allocations,
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            aez_profile, allocation_result, profit_estimate, resource_plan
        )
        
        risk_factors = self._identify_risks(
            aez_profile, allocation_result, resource_plan
        )
        
        # Compare to 7-ha example if applicable
        example_comparison = None
        if 5 <= request.area_ha <= 10:
            example_comparison = self._compare_to_example(
                allocation_result, request.area_ha
            )
        
        return FarmPlan(
            location=request.location,
            area_ha=request.area_ha,
            objective=request.objective,
            aez_profile=aez_profile.to_dict(),
            allocation=allocation_result.to_dict(),
            profit_estimate=profit_estimate.to_dict(),
            multi_year_projection=multi_year,
            resource_plan=resource_plan.to_dict(),
            farm_schedule=farm_schedule.to_dict(),
            agent_deployment=agent_deployment.to_dict(),
            example_comparison=example_comparison,
            key_recommendations=recommendations,
            risk_factors=risk_factors,
        )
    
    def _generate_recommendations(
        self,
        aez: AEZProfile,
        allocation: FarmAllocationResult,
        profit: Any,
        resources: ResourcePlan,
    ) -> List[str]:
        """Generate key recommendations based on analysis."""
        recs = []
        
        # AEZ-based
        if aez.drought_risk() in ["high", "very_high"]:
            recs.append(f"Zone {aez.zone} has {aez.drought_risk()} drought risk - prioritize water storage")
        
        # Allocation-based
        if allocation.fodder_balance < 0:
            recs.append("Fodder deficit detected - increase fodder area or reduce livestock")
        
        if "land" in allocation.binding_constraints:
            recs.append("Land is fully utilized - consider intensification strategies")
        
        # Profit-based
        if profit.roi_percent < 20:
            recs.append("Low ROI - consider higher-value crops or value-addition")
        
        if profit.n_fixation_value_usd > 50:
            recs.append(f"Legume rotation saves ~${profit.n_fixation_value_usd:.0f}/year in fertilizer")
        
        # Resource-based
        if resources.water.total_m3 > 10000:
            recs.append(f"High water requirement ({resources.water.total_m3:.0f} m³/year) - invest in water infrastructure")
        
        if resources.labor.seasonal_workers > 2:
            recs.append(f"Significant seasonal labor needed ({resources.labor.seasonal_workers} workers) - plan ahead")
        
        # Default recommendations
        if not recs:
            recs.append("Farm plan is well-balanced - focus on execution and monitoring")
        
        return recs[:5]  # Top 5
    
    def _identify_risks(
        self,
        aez: AEZProfile,
        allocation: FarmAllocationResult,
        resources: ResourcePlan,
    ) -> List[str]:
        """Identify key risk factors."""
        risks = []
        
        if aez.rainfall_reliability < 0.7:
            risks.append(f"Low rainfall reliability ({aez.rainfall_reliability:.0%}) - drought risk")
        
        if allocation.risk_score > 1.2:
            risks.append("High-risk crop mix - vulnerable to weather shocks")
        
        if resources.water.total_m3 > 15000:
            risks.append("Very high water requirement - ensure reliable source")
        
        # Market risk
        total_veg = allocation.crop_allocations.get("vegetables", 0)
        if total_veg > 1.0:
            risks.append("High vegetable area - market price volatility risk")
        
        # Labor seasonality
        if resources.labor.peak_month_days > 150:
            risks.append(f"High labor peak ({resources.labor.peak_month_days:.0f} days) - plan seasonal workers")
        
        return risks
    
    def _compare_to_example(
        self,
        allocation: FarmAllocationResult,
        area_ha: float,
    ) -> Dict[str, Any]:
        """Compare to the 7-ha reference example."""
        # Reference 7-ha allocation
        reference = {
            "maize": 2.5,
            "groundnuts": 1.0,
            "vegetables": 0.5,
            "fodder": 1.0,
            "pasture": 1.5,
            "infrastructure": 0.5,
            "goats": 12,
            "poultry": 100,
        }
        
        # Scale reference to current area
        scale = area_ha / 7.0
        scaled_ref = {k: v * scale if k not in ["goats", "poultry"] else int(v * scale) 
                      for k, v in reference.items()}
        
        # Compare
        comparison = {
            "reference": scaled_ref,
            "optimized": {
                **allocation.crop_allocations,
                **{k: v for k, v in allocation.livestock_allocations.items()},
            },
            "scale_factor": scale,
            "notes": [],
        }
        
        # Add comparison notes
        for crop in ["maize", "groundnuts", "vegetables"]:
            ref = scaled_ref.get(crop, 0)
            opt = allocation.crop_allocations.get(crop, 0)
            if abs(ref - opt) > 0.3:
                direction = "more" if opt > ref else "less"
                comparison["notes"].append(
                    f"Optimized {crop}: {opt:.1f} ha ({direction} than reference {ref:.1f} ha)"
                )
        
        return comparison


def plan_farm(
    lat: float,
    lon: float,
    area_ha: float,
    objective: str = "maximize_profit",
    constraints: Optional[Dict] = None,
    allowed_enterprises: Optional[List[str]] = None,
) -> FarmPlan:
    """
    Convenience function for farm planning.
    
    Example:
        plan = plan_farm(-17.83, 31.05, 7.0, "maximize_profit")
        print(plan.to_json())
    """
    request = FarmPlanRequest(
        location={"lat": lat, "lon": lon},
        area_ha=area_ha,
        objective=objective,
        constraints=constraints or {},
        allowed_enterprises=allowed_enterprises,
    )
    
    pipeline = FarmAllocationPipeline()
    return pipeline.plan(request)


if __name__ == "__main__":
    # Example: Plan a 7-ha farm near Harare
    plan = plan_farm(
        lat=-17.83,
        lon=31.05,
        area_ha=7.0,
        objective="maximize_profit",
    )
    
    print("=" * 60)
    print("FARM PLAN SUMMARY")
    print("=" * 60)
    
    print(f"\nLocation: {plan.location}")
    print(f"Area: {plan.area_ha} ha")
    print(f"AEZ Zone: {plan.aez_profile['zone']} - {plan.aez_profile['zone_name']}")
    
    print(f"\n--- ALLOCATION ---")
    for crop, area in plan.allocation["allocation"]["crops"].items():
        if area > 0.1:
            print(f"  {crop}: {area:.2f} ha")
    for ls, count in plan.allocation["allocation"]["livestock"].items():
        if count > 0:
            print(f"  {ls}: {count} head")
    
    print(f"\n--- ECONOMICS ---")
    print(f"  Year 1 Net Profit: ${plan.profit_estimate['net_profit_usd']:.0f}")
    print(f"  ROI: {plan.profit_estimate['roi_percent']:.1f}%")
    print(f"  3-Year Expected: ${plan.multi_year_projection['summary']['expected_total_profit']:.0f}")
    
    print(f"\n--- RESOURCES ---")
    print(f"  Water needed: {plan.resource_plan['water']['total_requirement_m3_year']:.0f} m³/year")
    print(f"  Labor needed: {plan.resource_plan['labor']['total_labor_days_year']:.0f} days/year")
    print(f"  Operating cost: ${plan.resource_plan['total_operating_cost_usd']:.0f}")
    
    print(f"\n--- RECOMMENDATIONS ---")
    for rec in plan.key_recommendations:
        print(f"  • {rec}")
    
    print(f"\n--- RISK FACTORS ---")
    for risk in plan.risk_factors:
        print(f"  ⚠️ {risk}")
    
    # Save to file
    plan.save(Path("logs/farm_plan_example.json"))
    print(f"\nPlan saved to logs/farm_plan_example.json")
