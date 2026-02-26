"""
OptimizerAgent - Mixed-Integer Program (MIP) for optimal farm allocation.
Uses PuLP/CBC solver to maximize profit subject to constraints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json

try:
    import pulp
    HAS_PULP = True
except ImportError:
    HAS_PULP = False


class ObjectiveType(Enum):
    MAXIMIZE_PROFIT = "maximize_profit"
    FOOD_SECURITY = "food_security"
    SOIL_BUILDING = "soil_building"
    BALANCED = "balanced"


@dataclass
class Enterprise:
    """Enterprise definition for optimizer."""
    name: str
    type: str  # "crop" or "livestock"
    
    # Area/count bounds
    min_area: float = 0.0
    max_area: Optional[float] = None
    min_count: int = 0
    max_count: Optional[int] = None
    
    # Economics
    yield_per_ha: float = 0.0
    price_per_unit: float = 0.0
    cost_per_ha: float = 0.0
    cost_per_head: float = 0.0
    
    # Resources
    labor_days_per_ha: float = 0.0
    labor_days_per_head: float = 0.0
    water_m3_per_ha: float = 0.0
    water_m3_per_head: float = 0.0
    
    # Integration
    fodder_output_t_ha: float = 0.0
    fodder_requirement_t_head: float = 0.0
    n_fixation_kg_ha: float = 0.0
    
    # Risk
    risk_factor: float = 1.0
    
    # Objective weights
    food_security_weight: float = 1.0
    soil_building_weight: float = 1.0


@dataclass
class FarmAllocationResult:
    """Result of optimization."""
    status: str
    objective_value: float
    
    crop_allocations: Dict[str, float]
    livestock_allocations: Dict[str, int]
    
    total_cropped_area: float
    labor_days_used: float
    water_m3_used: float
    fodder_balance: float
    
    expected_revenue: float
    expected_costs: float
    expected_profit: float
    profit_per_ha: float
    
    risk_score: float
    
    rotation_plan: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    binding_constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "objective_value": self.objective_value,
            "allocation": {
                "crops": self.crop_allocations,
                "livestock": self.livestock_allocations,
            },
            "resources": {
                "total_cropped_area_ha": self.total_cropped_area,
                "labor_days_used": self.labor_days_used,
                "water_m3_used": self.water_m3_used,
                "fodder_balance_t": self.fodder_balance,
            },
            "economics": {
                "expected_revenue_usd": self.expected_revenue,
                "expected_costs_usd": self.expected_costs,
                "expected_profit_usd": self.expected_profit,
                "profit_per_ha_usd": self.profit_per_ha,
            },
            "risk_score": self.risk_score,
            "rotation_plan": self.rotation_plan,
            "notes": self.notes,
            "binding_constraints": self.binding_constraints,
        }


def _create_default_enterprises(
    crop_suitability: Dict[str, Dict],
    livestock_capacity: Dict[str, Dict],
    prices: Dict[str, Dict],
    input_costs: Dict[str, Dict],
    livestock_costs: Dict[str, Dict],
    total_area: float,
) -> List[Enterprise]:
    """Create enterprise definitions from AEZ data."""
    enterprises = []
    
    crop_params = {
        "maize": {"labor": 45, "water": 500, "n_fix": 0, "fodder_out": 1.2},
        "sorghum": {"labor": 35, "water": 350, "n_fix": 0, "fodder_out": 1.5},
        "groundnuts": {"labor": 50, "water": 400, "n_fix": 80, "fodder_out": 1.0},
        "sunflower": {"labor": 30, "water": 400, "n_fix": 0, "fodder_out": 0.5},
        "cotton": {"labor": 60, "water": 600, "n_fix": 0, "fodder_out": 0},
        "tobacco": {"labor": 120, "water": 800, "n_fix": 0, "fodder_out": 0},
        "vegetables": {"labor": 150, "water": 1200, "n_fix": 0, "fodder_out": 0},
        "fodder": {"labor": 25, "water": 300, "n_fix": 0, "fodder_out": 1.0},
    }
    
    for crop, zone_data in crop_suitability.items():
        params = crop_params.get(crop, {"labor": 40, "water": 400, "n_fix": 0, "fodder_out": 0})
        cost_data = input_costs.get(crop, {"total": 200})
        price_data = prices.get(crop, {"typical": 300})
        
        yield_exp = zone_data.get("yield_t_ha", {}).get("expected", 2)
        
        risk_map = {"low": 0.8, "medium": 1.0, "high": 1.3, "very_high": 1.6}
        risk = risk_map.get(zone_data.get("risk", "medium"), 1.0)
        
        food_weight = 1.5 if crop in ["maize", "sorghum", "groundnuts"] else 1.0
        soil_weight = 1.5 if params["n_fix"] > 0 else 1.0
        
        enterprises.append(Enterprise(
            name=crop,
            type="crop",
            min_area=0,
            max_area=total_area * 0.6,
            yield_per_ha=yield_exp,
            price_per_unit=price_data.get("typical", 300),
            cost_per_ha=cost_data.get("total", 200),
            labor_days_per_ha=params["labor"],
            water_m3_per_ha=params["water"],
            fodder_output_t_ha=params["fodder_out"] * yield_exp,
            n_fixation_kg_ha=params["n_fix"],
            risk_factor=risk,
            food_security_weight=food_weight,
            soil_building_weight=soil_weight,
        ))
    
    livestock_params = {
        "cattle": {"labor": 15, "water": 18, "fodder": 3.5},
        "goats": {"labor": 8, "water": 2, "fodder": 0.7},
        "sheep": {"labor": 7, "water": 1.5, "fodder": 0.5},
        "poultry": {"labor": 0.5, "water": 0.1, "fodder": 0.04},
        "pigs": {"labor": 12, "water": 4, "fodder": 1.1},
    }
    
    revenue_map = {"cattle": 600, "goats": 110, "sheep": 90, "poultry": 7, "pigs": 220}
    
    for ls, cap_data in livestock_capacity.items():
        params = livestock_params.get(ls, {"labor": 10, "water": 2, "fodder": 1.0})
        ls_cost = livestock_costs.get(ls if ls != "poultry" else "poultry_broilers", {"total": 50})
        
        if ls == "cattle":
            max_count = int(total_area * cap_data.get("lsu_per_ha", 0.5) * 1.5)
        elif ls == "poultry":
            max_count = int(cap_data.get("birds_per_ha", 200) * total_area * 2)
        else:
            max_count = int(cap_data.get("heads_per_ha", 1.5) * total_area * 2)
        
        enterprises.append(Enterprise(
            name=ls,
            type="livestock",
            min_count=0,
            max_count=max_count,
            price_per_unit=revenue_map.get(ls, 100),
            cost_per_head=ls_cost.get("total", 50),
            labor_days_per_head=params["labor"],
            water_m3_per_head=params["water"] * 365,
            fodder_requirement_t_head=params["fodder"],
            risk_factor=1.0,
            food_security_weight=1.2 if ls in ["goats", "poultry"] else 1.0,
            soil_building_weight=1.3,
        ))
    
    return enterprises


def run_allocation(
    total_area_ha: float,
    enterprises: List[Enterprise],
    constraints: Dict[str, Any],
    objective: str = "maximize_profit",
) -> FarmAllocationResult:
    """Run MIP optimization for farm allocation."""
    
    crops = [e for e in enterprises if e.type == "crop"]
    livestock = [e for e in enterprises if e.type == "livestock"]
    
    # If PuLP not available, use heuristic
    if not HAS_PULP:
        return _heuristic_allocation(total_area_ha, crops, livestock, constraints, objective)
    
    prob = pulp.LpProblem("farm_allocation", pulp.LpMaximize)
    
    area_vars = {
        e.name: pulp.LpVariable(f"area_{e.name}", lowBound=e.min_area, upBound=e.max_area or total_area_ha)
        for e in crops
    }
    
    count_vars = {
        e.name: pulp.LpVariable(f"count_{e.name}", lowBound=e.min_count, upBound=e.max_count, cat=pulp.LpInteger)
        for e in livestock
    }
    
    # Objective
    crop_profit = pulp.lpSum([
        area_vars[e.name] * (e.yield_per_ha * e.price_per_unit - e.cost_per_ha)
        for e in crops
    ])
    
    livestock_profit = pulp.lpSum([
        count_vars[e.name] * (e.price_per_unit - e.cost_per_head)
        for e in livestock
    ])
    
    obj_map = {
        "maximize_profit": crop_profit + livestock_profit,
        "food_security": pulp.lpSum([
            area_vars[e.name] * (e.yield_per_ha * e.price_per_unit - e.cost_per_ha) * e.food_security_weight
            for e in crops
        ]) + pulp.lpSum([
            count_vars[e.name] * (e.price_per_unit - e.cost_per_head) * e.food_security_weight
            for e in livestock
        ]),
        "soil_building": pulp.lpSum([
            area_vars[e.name] * ((e.yield_per_ha * e.price_per_unit - e.cost_per_ha) * e.soil_building_weight + e.n_fixation_kg_ha * 1.5)
            for e in crops
        ]) + livestock_profit,
        "balanced": crop_profit + livestock_profit - pulp.lpSum([
            area_vars[e.name] * e.risk_factor * 10 for e in crops
        ]),
    }
    
    prob += obj_map.get(objective, crop_profit + livestock_profit)
    
    # Land constraint
    infra_reserve = constraints.get("infra_reserve_ha", 0.5)
    available_land = total_area_ha - infra_reserve
    prob += pulp.lpSum([area_vars[e.name] for e in crops]) <= available_land, "land_limit"
    
    # Labor constraint
    if constraints.get("max_labor_days"):
        total_labor = (
            pulp.lpSum([area_vars[e.name] * e.labor_days_per_ha for e in crops]) +
            pulp.lpSum([count_vars[e.name] * e.labor_days_per_head for e in livestock])
        )
        prob += total_labor <= constraints["max_labor_days"], "labor_limit"
    
    # Water constraint
    if constraints.get("max_water_m3"):
        total_water = (
            pulp.lpSum([area_vars[e.name] * e.water_m3_per_ha for e in crops]) +
            pulp.lpSum([count_vars[e.name] * e.water_m3_per_head for e in livestock])
        )
        prob += total_water <= constraints["max_water_m3"], "water_limit"
    
    # Fodder balance
    fodder_produced = pulp.lpSum([area_vars[e.name] * e.fodder_output_t_ha for e in crops])
    fodder_required = pulp.lpSum([count_vars[e.name] * e.fodder_requirement_t_head for e in livestock])
    min_balance = constraints.get("min_fodder_balance", 0)
    prob += fodder_produced >= fodder_required + min_balance, "fodder_balance"
    
    # Solve
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=60)
    status = prob.solve(solver)
    status_str = pulp.LpStatus[status]
    
    # Extract results
    crop_alloc = {e.name: max(0, area_vars[e.name].value() or 0) for e in crops}
    livestock_alloc = {e.name: int(max(0, count_vars[e.name].value() or 0)) for e in livestock}
    
    # Calculate metrics
    total_cropped = sum(crop_alloc.values())
    
    labor_used = (
        sum(crop_alloc[e.name] * e.labor_days_per_ha for e in crops) +
        sum(livestock_alloc[e.name] * e.labor_days_per_head for e in livestock)
    )
    
    water_used = (
        sum(crop_alloc[e.name] * e.water_m3_per_ha for e in crops) +
        sum(livestock_alloc[e.name] * e.water_m3_per_head for e in livestock)
    )
    
    fodder_prod = sum(crop_alloc[e.name] * e.fodder_output_t_ha for e in crops)
    fodder_req = sum(livestock_alloc[e.name] * e.fodder_requirement_t_head for e in livestock)
    fodder_balance = fodder_prod - fodder_req
    
    revenue = (
        sum(crop_alloc[e.name] * e.yield_per_ha * e.price_per_unit for e in crops) +
        sum(livestock_alloc[e.name] * e.price_per_unit for e in livestock)
    )
    
    costs = (
        sum(crop_alloc[e.name] * e.cost_per_ha for e in crops) +
        sum(livestock_alloc[e.name] * e.cost_per_head for e in livestock)
    )
    
    profit = revenue - costs
    profit_per_ha = profit / total_area_ha if total_area_ha > 0 else 0
    
    risk = sum(crop_alloc[e.name] * e.risk_factor for e in crops) / max(total_cropped, 0.1)
    
    # Binding constraints
    binding = []
    if total_cropped >= available_land * 0.95:
        binding.append("land")
    if constraints.get("max_labor_days") and labor_used >= constraints["max_labor_days"] * 0.95:
        binding.append("labor")
    
    return FarmAllocationResult(
        status=status_str,
        objective_value=pulp.value(prob.objective) or 0,
        crop_allocations=crop_alloc,
        livestock_allocations=livestock_alloc,
        total_cropped_area=total_cropped,
        labor_days_used=labor_used,
        water_m3_used=water_used,
        fodder_balance=fodder_balance,
        expected_revenue=revenue,
        expected_costs=costs,
        expected_profit=profit,
        profit_per_ha=profit_per_ha,
        risk_score=risk,
        notes=[] if status_str == "Optimal" else [f"Solution status: {status_str}"],
        binding_constraints=binding,
    )


def _heuristic_allocation(
    total_area_ha: float,
    crops: List[Enterprise],
    livestock: List[Enterprise],
    constraints: Dict[str, Any],
    objective: str,
) -> FarmAllocationResult:
    """Fallback heuristic when PuLP not available."""
    
    # Simple heuristic: allocate based on profit margin
    infra = constraints.get("infra_reserve_ha", 0.5)
    available = total_area_ha - infra
    
    # Sort crops by profit margin
    crop_margins = [(e, e.yield_per_ha * e.price_per_unit - e.cost_per_ha) for e in crops]
    crop_margins.sort(key=lambda x: x[1], reverse=True)
    
    crop_alloc = {}
    remaining = available
    
    for e, margin in crop_margins[:4]:  # Top 4 crops
        alloc = min(remaining * 0.3, e.max_area or remaining)
        if alloc > 0.1:
            crop_alloc[e.name] = alloc
            remaining -= alloc
    
    # Allocate remaining to fodder if present
    fodder = next((e for e in crops if e.name == "fodder"), None)
    if fodder and remaining > 0.5:
        crop_alloc["fodder"] = crop_alloc.get("fodder", 0) + remaining * 0.5
    
    # Livestock: prioritize goats and poultry
    livestock_alloc = {}
    for e in livestock:
        if e.name == "goats":
            livestock_alloc["goats"] = min(15, e.max_count or 15)
        elif e.name == "poultry":
            livestock_alloc["poultry"] = min(100, e.max_count or 100)
    
    # Calculate metrics
    total_cropped = sum(crop_alloc.values())
    revenue = sum(crop_alloc.get(e.name, 0) * e.yield_per_ha * e.price_per_unit for e in crops)
    revenue += sum(livestock_alloc.get(e.name, 0) * e.price_per_unit for e in livestock)
    costs = sum(crop_alloc.get(e.name, 0) * e.cost_per_ha for e in crops)
    costs += sum(livestock_alloc.get(e.name, 0) * e.cost_per_head for e in livestock)
    
    return FarmAllocationResult(
        status="Heuristic",
        objective_value=revenue - costs,
        crop_allocations=crop_alloc,
        livestock_allocations=livestock_alloc,
        total_cropped_area=total_cropped,
        labor_days_used=0,
        water_m3_used=0,
        fodder_balance=0,
        expected_revenue=revenue,
        expected_costs=costs,
        expected_profit=revenue - costs,
        profit_per_ha=(revenue - costs) / total_area_ha,
        risk_score=1.0,
        notes=["PuLP not installed - using heuristic allocation"],
        binding_constraints=[],
    )


def optimize_farm(
    lat: float,
    lon: float,
    area_ha: float,
    objective: str = "maximize_profit",
    constraints_dict: Optional[Dict] = None,
    allowed_enterprises: Optional[List[str]] = None,
) -> FarmAllocationResult:
    """
    High-level optimization function.
    Loads AEZ data and runs optimization.
    """
    from .aez_lookup import AEZLookupAgent
    
    agent = AEZLookupAgent()
    profile = agent.lookup(lat, lon)
    
    prices = agent.get_market_prices()
    input_costs = agent.get_input_costs()
    livestock_costs = agent.get_livestock_costs()
    
    crop_suit = profile.crop_suitability
    livestock_cap = profile.livestock_capacity
    
    if allowed_enterprises:
        crop_names = {"maize", "sorghum", "groundnuts", "sunflower", "cotton", "tobacco", "vegetables", "fodder"}
        ls_names = {"cattle", "goats", "sheep", "poultry", "pigs"}
        crop_suit = {k: v for k, v in crop_suit.items() if k in allowed_enterprises or k not in crop_names}
        livestock_cap = {k: v for k, v in livestock_cap.items() if k in allowed_enterprises or k not in ls_names}
    
    enterprises = _create_default_enterprises(
        crop_suit, livestock_cap, prices, input_costs, livestock_costs, area_ha
    )
    
    constraints = {
        "infra_reserve_ha": (constraints_dict or {}).get("infra_reserve_ha", 0.5),
        "max_labor_days": (constraints_dict or {}).get("max_labor_days_per_year"),
        "max_water_m3": (constraints_dict or {}).get("water_available_m3"),
        "min_fodder_balance": 0,
    }
    
    return run_allocation(area_ha, enterprises, constraints, objective)


if __name__ == "__main__":
    result = optimize_farm(
        lat=-17.83,
        lon=31.05,
        area_ha=7.0,
        objective="maximize_profit",
        constraints_dict={"max_labor_days_per_year": 1000},
    )
    
    print(f"Status: {result.status}")
    print(f"Expected profit: ${result.expected_profit:.0f}")
    print(f"\nCrops:")
    for crop, area in result.crop_allocations.items():
        if area > 0.1:
            print(f"  {crop}: {area:.2f} ha")
    print(f"\nLivestock:")
    for ls, count in result.livestock_allocations.items():
        if count > 0:
            print(f"  {ls}: {count}")
