"""
ResourceAgent - Estimates water, labor, input requirements and constraints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .aez_lookup import AEZProfile


@dataclass
class WaterRequirement:
    """Water requirement breakdown."""
    crop_irrigation_m3: float
    livestock_drinking_m3: float
    domestic_m3: float
    total_m3: float
    peak_month_m3: float
    source_recommendation: str
    notes: List[str] = field(default_factory=list)
    deficit_m3: float = 0.0  # 0 if no constraint, positive if exceeds available
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requirement_m3_year": self.total_m3,
            "breakdown": {
                "irrigation_m3": self.crop_irrigation_m3,
                "livestock_m3": self.livestock_drinking_m3,
                "domestic_m3": self.domestic_m3,
            },
            "peak_month_m3": self.peak_month_m3,
            "source_recommendation": self.source_recommendation,
            "deficit_m3": self.deficit_m3,
            "notes": self.notes,
        }


@dataclass
class LaborRequirement:
    """Labor requirement breakdown."""
    crop_labor_days: float
    livestock_labor_days: float
    management_labor_days: float
    total_labor_days: float
    peak_month_days: float
    peak_month: str = "November"  # Planting season typically
    ftes_required: float = 0.0  # Full-time equivalents
    seasonal_workers: int = 0
    family_labor_available: float = 500  # Default assumption
    hired_needed_days: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_labor_days_year": self.total_labor_days,
            "breakdown": {
                "crop_days": self.crop_labor_days,
                "livestock_days": self.livestock_labor_days,
                "management_days": self.management_labor_days,
            },
            "seasonality": {
                "peak_month": self.peak_month,
                "peak_days": self.peak_month_days,
            },
            "labor_needs": {
                "ftes_required": self.ftes_required,
                "seasonal_workers": self.seasonal_workers,
                "hired_needed_days": self.hired_needed_days,
            },
            "notes": self.notes,
        }


@dataclass
class InputRequirement:
    """Input requirements and costs."""
    seeds: Dict[str, float]  # crop -> kg
    fertilizer_n_kg: float
    fertilizer_p_kg: float
    fertilizer_k_kg: float
    chemicals_usd: float
    feed_kg: float
    veterinary_usd: float
    total_input_cost_usd: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "seeds_kg": self.seeds,
            "fertilizer_kg": {
                "nitrogen": self.fertilizer_n_kg,
                "phosphorus": self.fertilizer_p_kg,
                "potassium": self.fertilizer_k_kg,
            },
            "chemicals_usd": self.chemicals_usd,
            "feed_kg": self.feed_kg,
            "veterinary_usd": self.veterinary_usd,
            "total_input_cost_usd": self.total_input_cost_usd,
        }


@dataclass
class InfrastructureRequirement:
    """Infrastructure needs."""
    storage_m2: float
    housing_livestock_m2: float
    fencing_m: float
    water_storage_m3: float
    irrigation_type: str
    estimated_capex_usd: float
    items: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "storage_m2": self.storage_m2,
            "housing_livestock_m2": self.housing_livestock_m2,
            "fencing_m": self.fencing_m,
            "water_storage_m3": self.water_storage_m3,
            "irrigation_type": self.irrigation_type,
            "estimated_capex_usd": self.estimated_capex_usd,
            "items": self.items,
        }


@dataclass
class ResourcePlan:
    """Complete resource plan for a farm."""
    water: WaterRequirement
    labor: LaborRequirement
    inputs: InputRequirement
    infrastructure: InfrastructureRequirement
    constraints_satisfied: bool
    constraint_violations: List[str] = field(default_factory=list)
    
    @property
    def total_operating_cost_usd(self) -> float:
        """Total annual operating cost (inputs + labor estimate)."""
        labor_cost = self.labor.total_labor_days * 5  # $5/day estimate
        return self.inputs.total_input_cost_usd + labor_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "water": self.water.to_dict(),
            "labor": self.labor.to_dict(),
            "inputs": self.inputs.to_dict(),
            "infrastructure": self.infrastructure.to_dict(),
            "total_operating_cost_usd": self.total_operating_cost_usd,
            "constraints_satisfied": self.constraints_satisfied,
            "constraint_violations": self.constraint_violations,
        }


# Crop water requirements (m3/ha/year) - Zimbabwe context
CROP_WATER_REQ = {
    "maize": {"rainfed": 0, "supplemental": 1500, "irrigated": 5000},
    "sorghum": {"rainfed": 0, "supplemental": 800, "irrigated": 3500},
    "groundnuts": {"rainfed": 0, "supplemental": 1200, "irrigated": 4000},
    "sunflower": {"rainfed": 0, "supplemental": 1000, "irrigated": 3500},
    "cotton": {"rainfed": 0, "supplemental": 1500, "irrigated": 5500},
    "tobacco": {"rainfed": 0, "supplemental": 2000, "irrigated": 6000},
    "vegetables": {"rainfed": 0, "supplemental": 3000, "irrigated": 8000},
    "fodder": {"rainfed": 0, "supplemental": 1500, "irrigated": 5000},
}

# Livestock water requirements (liters/head/day)
LIVESTOCK_WATER_REQ = {
    "cattle": 50,
    "goats": 5,
    "sheep": 4,
    "poultry": 0.3,
    "pigs": 10,
}

# Crop labor requirements (days/ha/year)
CROP_LABOR_REQ = {
    "maize": 45,
    "sorghum": 35,
    "groundnuts": 50,
    "sunflower": 30,
    "cotton": 60,
    "tobacco": 120,
    "vegetables": 150,
    "fodder": 25,
}

# Livestock labor requirements (days/head/year)
LIVESTOCK_LABOR_REQ = {
    "cattle": 15,
    "goats": 8,
    "sheep": 7,
    "poultry": 0.5,
    "pigs": 12,
}

# Seed rates (kg/ha)
SEED_RATES = {
    "maize": 25,
    "sorghum": 8,
    "groundnuts": 100,
    "sunflower": 5,
    "cotton": 15,
    "tobacco": 0.05,  # Seedlings typically
    "vegetables": 5,  # Varies by type
    "fodder": 10,
}

# NPK requirements (kg/ha)
FERTILIZER_REQ = {
    "maize": {"n": 120, "p": 40, "k": 30},
    "sorghum": {"n": 60, "p": 30, "k": 20},
    "groundnuts": {"n": 20, "p": 40, "k": 30},  # Low N due to fixation
    "sunflower": {"n": 60, "p": 30, "k": 30},
    "cotton": {"n": 80, "p": 40, "k": 40},
    "tobacco": {"n": 80, "p": 60, "k": 120},
    "vegetables": {"n": 150, "p": 60, "k": 100},
    "fodder": {"n": 80, "p": 30, "k": 40},
}


class ResourceAgent:
    """
    Agent for estimating resource requirements and checking constraints.
    """
    
    def estimate_water(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        aez_profile: AEZProfile,
        irrigation_strategy: str = "supplemental",
    ) -> WaterRequirement:
        """
        Estimate water requirements for the farm plan.
        
        Args:
            crop_allocations: Dict of crop -> hectares
            livestock_counts: Dict of livestock -> count
            aez_profile: AEZ profile for rainfall context
            irrigation_strategy: rainfed | supplemental | irrigated
        """
        # Crop irrigation
        crop_water = 0.0
        for crop, area in crop_allocations.items():
            water_req = CROP_WATER_REQ.get(crop, {"supplemental": 1500})
            crop_water += area * water_req.get(irrigation_strategy, 1500)
        
        # Adjust for rainfall - reduce irrigation needs in wetter zones
        rainfall_factor = 1.0
        if aez_profile.rainfall_mm["mean"] >= 800:
            rainfall_factor = 0.7
        elif aez_profile.rainfall_mm["mean"] >= 650:
            rainfall_factor = 0.85
        
        crop_water *= rainfall_factor
        
        # Livestock drinking water
        livestock_water = 0.0
        for livestock, count in livestock_counts.items():
            daily_req = LIVESTOCK_WATER_REQ.get(livestock, 5)
            livestock_water += count * daily_req * 365 / 1000  # Convert to m3/year
        
        # Domestic use (estimate for farm household)
        domestic = 50 * 365 / 1000  # 50 L/day for small household
        
        total = crop_water + livestock_water + domestic
        
        # Peak month estimate (dry season + crops need water)
        peak_month = total * 0.15  # 15% of annual in peak month
        
        # Source recommendation
        if total > 10000:
            source = "borehole_or_dam"
        elif total > 3000:
            source = "borehole"
        else:
            source = "rainwater_harvest_with_backup"
        
        notes = []
        if aez_profile.zone in ["IV", "V"]:
            notes.append("Low rainfall zone - water storage critical")
        if crop_water > 5000:
            notes.append("Consider drip irrigation for efficiency")
        
        return WaterRequirement(
            crop_irrigation_m3=crop_water,
            livestock_drinking_m3=livestock_water,
            domestic_m3=domestic,
            total_m3=total,
            peak_month_m3=peak_month,
            source_recommendation=source,
            notes=notes,
        )
    
    def estimate_labor(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
    ) -> LaborRequirement:
        """
        Estimate labor requirements for the farm plan.
        """
        # Crop labor
        crop_labor = 0.0
        for crop, area in crop_allocations.items():
            labor_req = CROP_LABOR_REQ.get(crop, 40)
            crop_labor += area * labor_req
        
        # Livestock labor
        livestock_labor = 0.0
        for livestock, count in livestock_counts.items():
            labor_req = LIVESTOCK_LABOR_REQ.get(livestock, 10)
            livestock_labor += count * labor_req
        
        # Management overhead (10%)
        management = (crop_labor + livestock_labor) * 0.10
        
        total = crop_labor + livestock_labor + management
        
        # Peak month (planting/harvest season)
        peak_month = total * 0.18  # 18% in peak month
        
        # FTEs (assume 250 working days/year)
        ftes = total / 250
        
        # Seasonal workers needed at peak
        seasonal = max(0, int(peak_month / 25) - 1)  # Assume 25 days/month/person
        
        # Family labor assumption (500 days/year = 2 people full-time)
        family_labor = 500
        hired_needed = max(0, total - family_labor)
        
        notes = []
        if ftes > 2:
            notes.append("Consider permanent farm workers")
        if seasonal > 3:
            notes.append("Significant seasonal labor requirement - plan ahead")
        
        return LaborRequirement(
            crop_labor_days=crop_labor,
            livestock_labor_days=livestock_labor,
            management_labor_days=management,
            total_labor_days=total,
            peak_month_days=peak_month,
            peak_month="November",  # Planting season
            ftes_required=round(ftes, 1),
            seasonal_workers=seasonal,
            family_labor_available=family_labor,
            hired_needed_days=hired_needed,
            notes=notes,
        )
    
    def estimate_inputs(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        n_credit_from_legumes: float = 0,
    ) -> InputRequirement:
        """
        Estimate input requirements and costs.
        
        Args:
            crop_allocations: Dict of crop -> hectares
            livestock_counts: Dict of livestock -> count
            n_credit_from_legumes: kg N to subtract (from rotation benefits)
        """
        seeds = {}
        total_n = 0.0
        total_p = 0.0
        total_k = 0.0
        chemicals_cost = 0.0
        
        for crop, area in crop_allocations.items():
            # Seeds
            seed_rate = SEED_RATES.get(crop, 10)
            seeds[crop] = area * seed_rate
            
            # Fertilizer
            fert = FERTILIZER_REQ.get(crop, {"n": 60, "p": 30, "k": 30})
            total_n += area * fert["n"]
            total_p += area * fert["p"]
            total_k += area * fert["k"]
            
            # Chemicals (pesticides, herbicides) - rough estimate
            chemicals_cost += area * 30  # $30/ha average
        
        # Apply N credit from legumes
        total_n = max(0, total_n - n_credit_from_legumes)
        
        # Livestock feed (supplementary)
        feed_kg = 0.0
        vet_cost = 0.0
        
        feed_rates = {"cattle": 500, "goats": 100, "sheep": 80, "poultry": 40, "pigs": 400}
        vet_rates = {"cattle": 30, "goats": 15, "sheep": 12, "poultry": 1, "pigs": 25}
        
        for livestock, count in livestock_counts.items():
            feed_kg += count * feed_rates.get(livestock, 100)
            vet_cost += count * vet_rates.get(livestock, 15)
        
        # Calculate total input cost
        # Fertilizer prices (approx USD/kg)
        n_price = 1.2
        p_price = 1.5
        k_price = 1.0
        seed_cost = sum(seeds.values()) * 2  # $2/kg average
        feed_cost = feed_kg * 0.3  # $0.30/kg
        
        total_cost = (
            total_n * n_price +
            total_p * p_price +
            total_k * k_price +
            seed_cost +
            chemicals_cost +
            feed_cost +
            vet_cost
        )
        
        return InputRequirement(
            seeds=seeds,
            fertilizer_n_kg=total_n,
            fertilizer_p_kg=total_p,
            fertilizer_k_kg=total_k,
            chemicals_usd=chemicals_cost,
            feed_kg=feed_kg,
            veterinary_usd=vet_cost,
            total_input_cost_usd=total_cost,
        )
    
    def estimate_infrastructure(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        area_ha: float,
        water_req: WaterRequirement,
    ) -> InfrastructureRequirement:
        """
        Estimate infrastructure requirements.
        """
        items = []
        total_capex = 0.0
        
        # Storage for crops (5 m2 per ha)
        total_crop_area = sum(crop_allocations.values())
        storage = total_crop_area * 5
        items.append({"item": "grain_storage", "size_m2": storage, "cost_usd": storage * 50})
        total_capex += storage * 50
        
        # Livestock housing
        housing = 0.0
        housing_rates = {"cattle": 8, "goats": 1.5, "sheep": 1.2, "poultry": 0.1, "pigs": 3}
        
        for livestock, count in livestock_counts.items():
            space = count * housing_rates.get(livestock, 2)
            housing += space
        
        items.append({"item": "livestock_housing", "size_m2": housing, "cost_usd": housing * 80})
        total_capex += housing * 80
        
        # Fencing (perimeter + paddocks)
        perimeter = (area_ha * 10000) ** 0.5 * 4  # Approximate square
        paddock_fencing = perimeter * 0.5  # Internal divisions
        total_fencing = perimeter + paddock_fencing
        
        items.append({"item": "fencing", "length_m": total_fencing, "cost_usd": total_fencing * 3})
        total_capex += total_fencing * 3
        
        # Water storage (30 days buffer)
        water_storage = water_req.peak_month_m3 * 1.5
        
        items.append({"item": "water_tank", "capacity_m3": water_storage, "cost_usd": water_storage * 100})
        total_capex += water_storage * 100
        
        # Irrigation type recommendation
        irrigated_area = crop_allocations.get("vegetables", 0) + crop_allocations.get("tobacco", 0)
        if irrigated_area > 1:
            irrigation = "drip_system"
            irr_cost = irrigated_area * 2000
        elif irrigated_area > 0:
            irrigation = "sprinkler"
            irr_cost = irrigated_area * 1000
        else:
            irrigation = "none_or_furrow"
            irr_cost = 0
        
        if irr_cost > 0:
            items.append({"item": "irrigation_system", "type": irrigation, "cost_usd": irr_cost})
            total_capex += irr_cost
        
        return InfrastructureRequirement(
            storage_m2=storage,
            housing_livestock_m2=housing,
            fencing_m=total_fencing,
            water_storage_m3=water_storage,
            irrigation_type=irrigation,
            estimated_capex_usd=total_capex,
            items=items,
        )
    
    def create_resource_plan(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        aez_profile: AEZProfile,
        area_ha: float,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ResourcePlan:
        """
        Create complete resource plan and check constraints.
        
        Args:
            crop_allocations: Dict of crop -> hectares
            livestock_counts: Dict of livestock -> count
            aez_profile: AEZ profile
            area_ha: Total farm area
            constraints: Optional dict with max_labor_days, water_available_m3, etc.
        """
        constraints = constraints or {}
        
        # Calculate N credit from legumes
        legume_n = 0.0
        if "groundnuts" in crop_allocations:
            legume_n += crop_allocations["groundnuts"] * 80
        
        # Estimate all resources
        water = self.estimate_water(crop_allocations, livestock_counts, aez_profile)
        labor = self.estimate_labor(crop_allocations, livestock_counts)
        inputs = self.estimate_inputs(crop_allocations, livestock_counts, legume_n)
        infrastructure = self.estimate_infrastructure(
            crop_allocations, livestock_counts, area_ha, water
        )
        
        # Check constraints
        violations = []
        
        if "max_labor_days" in constraints:
            if labor.total_labor_days > constraints["max_labor_days"]:
                violations.append(
                    f"Labor exceeds limit: {labor.total_labor_days:.0f} > {constraints['max_labor_days']}"
                )
        
        if "water_available_m3" in constraints and constraints["water_available_m3"]:
            available = constraints["water_available_m3"]
            if water.total_m3 > available:
                water.deficit_m3 = water.total_m3 - available
                violations.append(
                    f"Water exceeds limit: {water.total_m3:.0f} > {available}"
                )
        
        if "max_capex_usd" in constraints:
            if infrastructure.estimated_capex_usd > constraints["max_capex_usd"]:
                violations.append(
                    f"Capex exceeds limit: ${infrastructure.estimated_capex_usd:.0f} > ${constraints['max_capex_usd']}"
                )
        
        return ResourcePlan(
            water=water,
            labor=labor,
            inputs=inputs,
            infrastructure=infrastructure,
            constraints_satisfied=len(violations) == 0,
            constraint_violations=violations,
        )


if __name__ == "__main__":
    from .aez_lookup import AEZLookupAgent
    
    aez_agent = AEZLookupAgent()
    profile = aez_agent.lookup(-17.83, 31.05)
    
    agent = ResourceAgent()
    
    crops = {"maize": 2.5, "groundnuts": 1.0, "vegetables": 0.5, "fodder": 1.0}
    livestock = {"goats": 12, "poultry": 100}
    
    plan = agent.create_resource_plan(
        crops, livestock, profile, area_ha=7.0,
        constraints={"max_labor_days": 1000}
    )
    
    print(f"Water: {plan.water.total_m3:.0f} m³/year")
    print(f"Labor: {plan.labor.total_labor_days:.0f} days/year ({plan.labor.ftes_required} FTEs)")
    print(f"Input cost: ${plan.inputs.total_input_cost_usd:.0f}")
    print(f"Infrastructure: ${plan.infrastructure.estimated_capex_usd:.0f}")
    print(f"Constraints OK: {plan.constraints_satisfied}")
