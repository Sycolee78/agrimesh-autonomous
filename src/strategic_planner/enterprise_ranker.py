"""
Enterprise Ranking Engine

Defines all viable farm enterprises (crops + livestock + CEA)
and ranks them based on land analysis and profitability potential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class EnterpriseCategory(Enum):
    CROP = "crop"
    LIVESTOCK = "livestock"
    CEA = "controlled_environment"  # Aeroponics, hydroponics, greenhouses
    AGROFORESTRY = "agroforestry"
    AQUACULTURE = "aquaculture"


@dataclass
class Enterprise:
    """Definition of a farm enterprise."""
    id: str
    name: str
    category: EnterpriseCategory
    
    # Land requirements
    min_area_ha: float
    optimal_area_ha: float
    land_per_unit: float  # ha per unit (1 for crops, land per animal for livestock)
    
    # AEZ suitability (1-5 scale)
    aez_suitability: Dict[str, float]
    
    # Resource requirements
    water_demand: str  # "low", "medium", "high", "very_high"
    water_liters_per_ha_day: float  # For crops; per animal for livestock
    labor_days_per_ha_year: int
    
    # Economics (USD)
    capital_per_ha: float  # Or per unit for livestock
    operating_cost_per_ha_year: float
    
    # Yield and revenue
    expected_yield_per_ha: float  # tons/ha for crops, units for livestock
    yield_unit: str
    price_per_unit_usd: float
    price_volatility: float  # 0-1, higher = more volatile
    
    # Timing
    time_to_first_revenue_months: int
    production_cycle_months: int
    
    # Risk factors
    drought_sensitivity: float  # 0-1
    pest_disease_risk: float  # 0-1
    market_risk: float  # 0-1
    
    # Integration benefits
    provides_feed: bool = False
    provides_manure: bool = False
    fixes_nitrogen: bool = False
    requires_feed: bool = False
    
    # Special requirements
    requires_irrigation: bool = False
    requires_electricity: bool = False
    requires_cold_chain: bool = False


# ============== CROP ENTERPRISES ==============

CROPS: Dict[str, Enterprise] = {
    "maize": Enterprise(
        id="maize",
        name="Maize (Grain)",
        category=EnterpriseCategory.CROP,
        min_area_ha=0.5,
        optimal_area_ha=5.0,
        land_per_unit=1.0,
        aez_suitability={"I": 4, "IIa": 5, "IIb": 5, "III": 4, "IV": 2, "V": 1},
        water_demand="medium",
        water_liters_per_ha_day=40,
        labor_days_per_ha_year=45,
        capital_per_ha=350,
        operating_cost_per_ha_year=280,
        expected_yield_per_ha=4.5,
        yield_unit="tons",
        price_per_unit_usd=280,
        price_volatility=0.3,
        time_to_first_revenue_months=5,
        production_cycle_months=5,
        drought_sensitivity=0.7,
        pest_disease_risk=0.5,
        market_risk=0.3,
        provides_feed=True,
    ),
    "sorghum": Enterprise(
        id="sorghum",
        name="Sorghum",
        category=EnterpriseCategory.CROP,
        min_area_ha=0.5,
        optimal_area_ha=5.0,
        land_per_unit=1.0,
        aez_suitability={"I": 2, "IIa": 3, "IIb": 4, "III": 5, "IV": 5, "V": 4},
        water_demand="low",
        water_liters_per_ha_day=25,
        labor_days_per_ha_year=35,
        capital_per_ha=200,
        operating_cost_per_ha_year=150,
        expected_yield_per_ha=2.5,
        yield_unit="tons",
        price_per_unit_usd=220,
        price_volatility=0.25,
        time_to_first_revenue_months=4,
        production_cycle_months=4,
        drought_sensitivity=0.3,
        pest_disease_risk=0.3,
        market_risk=0.4,
        provides_feed=True,
    ),
    "groundnuts": Enterprise(
        id="groundnuts",
        name="Groundnuts",
        category=EnterpriseCategory.CROP,
        min_area_ha=0.25,
        optimal_area_ha=2.0,
        land_per_unit=1.0,
        aez_suitability={"I": 3, "IIa": 5, "IIb": 5, "III": 4, "IV": 3, "V": 2},
        water_demand="medium",
        water_liters_per_ha_day=35,
        labor_days_per_ha_year=60,
        capital_per_ha=400,
        operating_cost_per_ha_year=300,
        expected_yield_per_ha=1.5,
        yield_unit="tons",
        price_per_unit_usd=800,
        price_volatility=0.35,
        time_to_first_revenue_months=5,
        production_cycle_months=5,
        drought_sensitivity=0.5,
        pest_disease_risk=0.4,
        market_risk=0.3,
        fixes_nitrogen=True,
    ),
    "vegetables": Enterprise(
        id="vegetables",
        name="Mixed Vegetables",
        category=EnterpriseCategory.CROP,
        min_area_ha=0.1,
        optimal_area_ha=1.0,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 4, "III": 3, "IV": 2, "V": 2},
        water_demand="very_high",
        water_liters_per_ha_day=80,
        labor_days_per_ha_year=200,
        capital_per_ha=1500,
        operating_cost_per_ha_year=2000,
        expected_yield_per_ha=15.0,
        yield_unit="tons",
        price_per_unit_usd=400,
        price_volatility=0.5,
        time_to_first_revenue_months=2,
        production_cycle_months=3,
        drought_sensitivity=0.9,
        pest_disease_risk=0.6,
        market_risk=0.5,
        requires_irrigation=True,
        requires_cold_chain=True,
    ),
    "tobacco": Enterprise(
        id="tobacco",
        name="Tobacco",
        category=EnterpriseCategory.CROP,
        min_area_ha=1.0,
        optimal_area_ha=10.0,
        land_per_unit=1.0,
        aez_suitability={"I": 3, "IIa": 5, "IIb": 5, "III": 3, "IV": 1, "V": 0},
        water_demand="high",
        water_liters_per_ha_day=60,
        labor_days_per_ha_year=150,
        capital_per_ha=3000,
        operating_cost_per_ha_year=2500,
        expected_yield_per_ha=2.0,
        yield_unit="tons",
        price_per_unit_usd=3500,
        price_volatility=0.4,
        time_to_first_revenue_months=7,
        production_cycle_months=7,
        drought_sensitivity=0.7,
        pest_disease_risk=0.5,
        market_risk=0.3,
        requires_irrigation=True,
    ),
    "sunflower": Enterprise(
        id="sunflower",
        name="Sunflower",
        category=EnterpriseCategory.CROP,
        min_area_ha=1.0,
        optimal_area_ha=5.0,
        land_per_unit=1.0,
        aez_suitability={"I": 2, "IIa": 4, "IIb": 5, "III": 5, "IV": 3, "V": 2},
        water_demand="medium",
        water_liters_per_ha_day=35,
        labor_days_per_ha_year=30,
        capital_per_ha=300,
        operating_cost_per_ha_year=200,
        expected_yield_per_ha=1.5,
        yield_unit="tons",
        price_per_unit_usd=450,
        price_volatility=0.3,
        time_to_first_revenue_months=4,
        production_cycle_months=4,
        drought_sensitivity=0.4,
        pest_disease_risk=0.3,
        market_risk=0.3,
    ),
    "fodder": Enterprise(
        id="fodder",
        name="Fodder Crops",
        category=EnterpriseCategory.CROP,
        min_area_ha=0.5,
        optimal_area_ha=3.0,
        land_per_unit=1.0,
        aez_suitability={"I": 4, "IIa": 5, "IIb": 5, "III": 4, "IV": 3, "V": 2},
        water_demand="medium",
        water_liters_per_ha_day=45,
        labor_days_per_ha_year=40,
        capital_per_ha=250,
        operating_cost_per_ha_year=200,
        expected_yield_per_ha=8.0,
        yield_unit="tons_dm",
        price_per_unit_usd=100,  # Internal value
        price_volatility=0.2,
        time_to_first_revenue_months=3,
        production_cycle_months=12,
        drought_sensitivity=0.5,
        pest_disease_risk=0.2,
        market_risk=0.2,
        provides_feed=True,
    ),
}


# ============== LIVESTOCK ENTERPRISES ==============

LIVESTOCK: Dict[str, Enterprise] = {
    "beef_cattle": Enterprise(
        id="beef_cattle",
        name="Beef Cattle",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=5.0,
        optimal_area_ha=50.0,
        land_per_unit=2.0,  # 2 ha per animal in AEZ III
        aez_suitability={"I": 3, "IIa": 4, "IIb": 5, "III": 5, "IV": 4, "V": 3},
        water_demand="medium",
        water_liters_per_ha_day=50,  # per animal
        labor_days_per_ha_year=15,
        capital_per_ha=800,  # per animal
        operating_cost_per_ha_year=200,  # per animal per year
        expected_yield_per_ha=0.4,  # calves per cow
        yield_unit="calves",
        price_per_unit_usd=600,  # per weaner
        price_volatility=0.25,
        time_to_first_revenue_months=18,
        production_cycle_months=12,
        drought_sensitivity=0.5,
        pest_disease_risk=0.4,
        market_risk=0.25,
        requires_feed=True,
        provides_manure=True,
    ),
    "dairy_cattle": Enterprise(
        id="dairy_cattle",
        name="Dairy Cattle",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=2.0,
        optimal_area_ha=20.0,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 4, "III": 3, "IV": 1, "V": 0},
        water_demand="high",
        water_liters_per_ha_day=100,
        labor_days_per_ha_year=60,
        capital_per_ha=2500,  # per animal
        operating_cost_per_ha_year=800,
        expected_yield_per_ha=3500,  # liters per cow per year
        yield_unit="liters_milk",
        price_per_unit_usd=0.5,  # per liter
        price_volatility=0.2,
        time_to_first_revenue_months=24,
        production_cycle_months=12,
        drought_sensitivity=0.6,
        pest_disease_risk=0.5,
        market_risk=0.3,
        requires_feed=True,
        provides_manure=True,
        requires_electricity=True,
        requires_cold_chain=True,
    ),
    "goats": Enterprise(
        id="goats",
        name="Goats (Meat)",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=1.0,
        optimal_area_ha=10.0,
        land_per_unit=0.3,  # 3-4 goats per ha
        aez_suitability={"I": 2, "IIa": 4, "IIb": 5, "III": 5, "IV": 5, "V": 4},
        water_demand="low",
        water_liters_per_ha_day=8,  # per animal
        labor_days_per_ha_year=20,
        capital_per_ha=120,  # per animal
        operating_cost_per_ha_year=30,
        expected_yield_per_ha=1.5,  # kids per doe
        yield_unit="kids",
        price_per_unit_usd=80,
        price_volatility=0.3,
        time_to_first_revenue_months=12,
        production_cycle_months=8,
        drought_sensitivity=0.3,
        pest_disease_risk=0.3,
        market_risk=0.3,
        requires_feed=True,
        provides_manure=True,
    ),
    "sheep": Enterprise(
        id="sheep",
        name="Sheep",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=2.0,
        optimal_area_ha=15.0,
        land_per_unit=0.4,
        aez_suitability={"I": 4, "IIa": 3, "IIb": 4, "III": 4, "IV": 3, "V": 2},
        water_demand="low",
        water_liters_per_ha_day=6,
        labor_days_per_ha_year=25,
        capital_per_ha=150,
        operating_cost_per_ha_year=40,
        expected_yield_per_ha=1.2,
        yield_unit="lambs",
        price_per_unit_usd=100,
        price_volatility=0.25,
        time_to_first_revenue_months=12,
        production_cycle_months=8,
        drought_sensitivity=0.4,
        pest_disease_risk=0.4,
        market_risk=0.3,
        requires_feed=True,
        provides_manure=True,
    ),
    "pigs": Enterprise(
        id="pigs",
        name="Pigs",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=0.2,
        optimal_area_ha=2.0,
        land_per_unit=0.02,  # Intensive
        aez_suitability={"I": 4, "IIa": 5, "IIb": 5, "III": 4, "IV": 2, "V": 1},
        water_demand="medium",
        water_liters_per_ha_day=15,
        labor_days_per_ha_year=100,
        capital_per_ha=400,  # per sow
        operating_cost_per_ha_year=500,
        expected_yield_per_ha=18,  # piglets per sow per year
        yield_unit="piglets",
        price_per_unit_usd=50,
        price_volatility=0.4,
        time_to_first_revenue_months=8,
        production_cycle_months=6,
        drought_sensitivity=0.2,
        pest_disease_risk=0.6,
        market_risk=0.4,
        requires_feed=True,
        provides_manure=True,
    ),
    "poultry_layers": Enterprise(
        id="poultry_layers",
        name="Poultry (Layers)",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=0.1,
        optimal_area_ha=0.5,
        land_per_unit=0.001,  # Very intensive
        aez_suitability={"I": 4, "IIa": 5, "IIb": 5, "III": 5, "IV": 4, "V": 3},
        water_demand="medium",
        water_liters_per_ha_day=0.3,  # per bird
        labor_days_per_ha_year=150,
        capital_per_ha=12,  # per bird
        operating_cost_per_ha_year=15,  # per bird per year
        expected_yield_per_ha=280,  # eggs per bird per year
        yield_unit="eggs",
        price_per_unit_usd=0.12,
        price_volatility=0.3,
        time_to_first_revenue_months=5,
        production_cycle_months=12,
        drought_sensitivity=0.2,
        pest_disease_risk=0.6,
        market_risk=0.3,
        requires_feed=True,
        provides_manure=True,
    ),
    "poultry_broilers": Enterprise(
        id="poultry_broilers",
        name="Poultry (Broilers)",
        category=EnterpriseCategory.LIVESTOCK,
        min_area_ha=0.05,
        optimal_area_ha=0.3,
        land_per_unit=0.001,
        aez_suitability={"I": 4, "IIa": 5, "IIb": 5, "III": 5, "IV": 4, "V": 3},
        water_demand="medium",
        water_liters_per_ha_day=0.25,
        labor_days_per_ha_year=200,
        capital_per_ha=8,  # per bird
        operating_cost_per_ha_year=10,  # per bird per cycle
        expected_yield_per_ha=2.0,  # kg live weight
        yield_unit="kg_meat",
        price_per_unit_usd=2.5,
        price_volatility=0.35,
        time_to_first_revenue_months=2,
        production_cycle_months=2,
        drought_sensitivity=0.2,
        pest_disease_risk=0.5,
        market_risk=0.4,
        requires_feed=True,
        provides_manure=True,
    ),
}


# ============== CEA ENTERPRISES ==============

CEA_SYSTEMS: Dict[str, Enterprise] = {
    "greenhouse_vegetables": Enterprise(
        id="greenhouse_vegetables",
        name="Greenhouse Vegetables",
        category=EnterpriseCategory.CEA,
        min_area_ha=0.02,
        optimal_area_ha=0.2,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 5, "III": 5, "IV": 5, "V": 5},  # Works anywhere
        water_demand="high",
        water_liters_per_ha_day=50,  # Much less than open field
        labor_days_per_ha_year=400,
        capital_per_ha=50000,
        operating_cost_per_ha_year=25000,
        expected_yield_per_ha=100,  # Much higher than field
        yield_unit="tons",
        price_per_unit_usd=600,
        price_volatility=0.4,
        time_to_first_revenue_months=3,
        production_cycle_months=12,
        drought_sensitivity=0.1,
        pest_disease_risk=0.4,
        market_risk=0.4,
        requires_irrigation=True,
        requires_electricity=True,
    ),
    "hydroponics": Enterprise(
        id="hydroponics",
        name="Hydroponics System",
        category=EnterpriseCategory.CEA,
        min_area_ha=0.01,
        optimal_area_ha=0.1,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 5, "III": 5, "IV": 5, "V": 5},
        water_demand="medium",  # Very efficient
        water_liters_per_ha_day=30,
        labor_days_per_ha_year=500,
        capital_per_ha=80000,
        operating_cost_per_ha_year=35000,
        expected_yield_per_ha=150,
        yield_unit="tons",
        price_per_unit_usd=700,
        price_volatility=0.35,
        time_to_first_revenue_months=2,
        production_cycle_months=12,
        drought_sensitivity=0.05,
        pest_disease_risk=0.3,
        market_risk=0.4,
        requires_irrigation=True,
        requires_electricity=True,
    ),
    "aeroponics": Enterprise(
        id="aeroponics",
        name="Aeroponic Tower System",
        category=EnterpriseCategory.CEA,
        min_area_ha=0.005,
        optimal_area_ha=0.05,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 5, "III": 5, "IV": 5, "V": 5},
        water_demand="low",  # 90% less water
        water_liters_per_ha_day=10,
        labor_days_per_ha_year=600,
        capital_per_ha=120000,
        operating_cost_per_ha_year=45000,
        expected_yield_per_ha=200,  # Highest yield
        yield_unit="tons",
        price_per_unit_usd=750,
        price_volatility=0.35,
        time_to_first_revenue_months=2,
        production_cycle_months=12,
        drought_sensitivity=0.02,
        pest_disease_risk=0.2,
        market_risk=0.4,
        requires_irrigation=True,
        requires_electricity=True,
    ),
    "vertical_farming": Enterprise(
        id="vertical_farming",
        name="Vertical Farming",
        category=EnterpriseCategory.CEA,
        min_area_ha=0.002,
        optimal_area_ha=0.02,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 5, "III": 5, "IV": 5, "V": 5},
        water_demand="low",
        water_liters_per_ha_day=8,
        labor_days_per_ha_year=800,
        capital_per_ha=200000,
        operating_cost_per_ha_year=80000,
        expected_yield_per_ha=400,  # Extremely high
        yield_unit="tons",
        price_per_unit_usd=800,
        price_volatility=0.3,
        time_to_first_revenue_months=3,
        production_cycle_months=12,
        drought_sensitivity=0.01,
        pest_disease_risk=0.15,
        market_risk=0.35,
        requires_irrigation=True,
        requires_electricity=True,
    ),
    "container_farming": Enterprise(
        id="container_farming",
        name="Container Farm (Modular)",
        category=EnterpriseCategory.CEA,
        min_area_ha=0.003,
        optimal_area_ha=0.01,
        land_per_unit=1.0,
        aez_suitability={"I": 5, "IIa": 5, "IIb": 5, "III": 5, "IV": 5, "V": 5},
        water_demand="low",
        water_liters_per_ha_day=15,
        labor_days_per_ha_year=300,
        capital_per_ha=60000,
        operating_cost_per_ha_year=20000,
        expected_yield_per_ha=80,
        yield_unit="tons",
        price_per_unit_usd=650,
        price_volatility=0.35,
        time_to_first_revenue_months=2,
        production_cycle_months=12,
        drought_sensitivity=0.02,
        pest_disease_risk=0.2,
        market_risk=0.4,
        requires_electricity=True,
    ),
}


# Combine all enterprises
ALL_ENTERPRISES: Dict[str, Enterprise] = {**CROPS, **LIVESTOCK, **CEA_SYSTEMS}


@dataclass
class RankedEnterprise:
    """An enterprise ranked for a specific land parcel."""
    enterprise: Enterprise
    suitability_score: float  # 0-100
    profit_potential_score: float  # 0-100
    risk_score: float  # 0-100 (lower is better)
    overall_rank_score: float  # 0-100
    estimated_profit_per_ha: float
    capital_required: float
    constraints: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class EnterpriseRanker:
    """
    Ranks enterprises based on land analysis and constraints.
    """
    
    def __init__(self):
        self.enterprises = ALL_ENTERPRISES
    
    def rank_enterprises(
        self,
        land_analysis,  # LandAnalysis
        available_capital: Optional[float] = None,
        available_labor_days: Optional[int] = None,
        has_irrigation: bool = False,
        has_electricity: bool = False,
        exclude_categories: Optional[List[str]] = None,
        preferred_categories: Optional[List[str]] = None,
    ) -> List[RankedEnterprise]:
        """
        Rank all viable enterprises for the given land.
        
        Returns list sorted by overall_rank_score (descending).
        """
        
        ranked = []
        exclude = set(exclude_categories or [])
        prefer = set(preferred_categories or [])
        
        for eid, enterprise in self.enterprises.items():
            # Skip excluded categories
            if enterprise.category.value in exclude:
                continue
            
            # Check basic viability
            if not self._is_viable(enterprise, land_analysis, has_irrigation, has_electricity):
                continue
            
            # Calculate scores
            suitability = self._calc_suitability(enterprise, land_analysis)
            profit_potential = self._calc_profit_potential(enterprise, land_analysis)
            risk = self._calc_risk_score(enterprise, land_analysis)
            
            # Check capital constraint
            capital_needed = enterprise.capital_per_ha * min(enterprise.optimal_area_ha, land_analysis.area_ha)
            if available_capital and capital_needed > available_capital * 1.5:
                continue  # Skip if way over budget
            
            # Check labor constraint
            labor_needed = enterprise.labor_days_per_ha_year * min(enterprise.optimal_area_ha, land_analysis.area_ha)
            if available_labor_days and labor_needed > available_labor_days * 1.2:
                continue
            
            # Calculate overall score
            # Weight: suitability 30%, profit 40%, risk 30%
            overall = suitability * 0.30 + profit_potential * 0.40 + (100 - risk) * 0.30
            
            # Boost preferred categories
            if enterprise.category.value in prefer:
                overall *= 1.15
            
            # Estimate profit
            revenue = enterprise.expected_yield_per_ha * enterprise.price_per_unit_usd
            profit_per_ha = revenue - enterprise.operating_cost_per_ha_year
            
            # Identify constraints and recommendations
            constraints, recommendations = self._analyze_constraints(
                enterprise, land_analysis, has_irrigation, has_electricity
            )
            
            ranked.append(RankedEnterprise(
                enterprise=enterprise,
                suitability_score=round(suitability, 1),
                profit_potential_score=round(profit_potential, 1),
                risk_score=round(risk, 1),
                overall_rank_score=round(overall, 1),
                estimated_profit_per_ha=round(profit_per_ha, 0),
                capital_required=round(capital_needed, 0),
                constraints=constraints,
                recommendations=recommendations,
            ))
        
        # Sort by overall score descending
        ranked.sort(key=lambda x: x.overall_rank_score, reverse=True)
        
        return ranked
    
    def _is_viable(
        self,
        enterprise: Enterprise,
        land: "LandAnalysis",
        has_irrigation: bool,
        has_electricity: bool,
    ) -> bool:
        """Check if enterprise is viable on this land."""
        
        # Check AEZ suitability (must be at least 1)
        # Try full zone first (e.g., "IIa"), then base zone (e.g., "II")
        aez_full = land.aez_zone
        aez_base = land.aez_zone.replace("a", "").replace("b", "")
        
        suitability = enterprise.aez_suitability.get(aez_full, 
                      enterprise.aez_suitability.get(aez_base, 0))
        
        if suitability < 1:
            return False
        
        # Check area requirement
        if land.area_ha < enterprise.min_area_ha * 0.5:
            return False
        
        # Check irrigation requirement
        if enterprise.requires_irrigation and not has_irrigation:
            if land.water_reliability == "scarce":
                return False
        
        # Check electricity requirement
        if enterprise.requires_electricity and not has_electricity:
            if not land.electricity_access:
                return False
        
        return True
    
    def _calc_suitability(self, enterprise: Enterprise, land: "LandAnalysis") -> float:
        """Calculate suitability score (0-100)."""
        
        score = 0.0
        
        # AEZ suitability (40%)
        aez_full = land.aez_zone
        aez_base = land.aez_zone.replace("a", "").replace("b", "")
        aez_suit = enterprise.aez_suitability.get(aez_full, 
                   enterprise.aez_suitability.get(aez_base, 0))
        aez_score = aez_suit * 20  # 0-100
        score += aez_score * 0.40
        
        # Water match (25%)
        water_scores = {
            "low": {"reliable": 100, "seasonal": 90, "unreliable": 80, "scarce": 70},
            "medium": {"reliable": 100, "seasonal": 80, "unreliable": 50, "scarce": 30},
            "high": {"reliable": 100, "seasonal": 60, "unreliable": 30, "scarce": 10},
            "very_high": {"reliable": 100, "seasonal": 40, "unreliable": 15, "scarce": 5},
        }
        water_score = water_scores.get(enterprise.water_demand, {}).get(land.water_reliability, 50)
        score += water_score * 0.25
        
        # Soil match (20%)
        soil_score = 50
        if land.soil_fertility == "excellent":
            soil_score = 100
        elif land.soil_fertility == "good":
            soil_score = 80
        elif land.soil_fertility == "moderate":
            soil_score = 60
        elif land.soil_fertility == "poor":
            soil_score = 40
        score += soil_score * 0.20
        
        # Slope suitability (15%)
        slope_score = 100
        if land.slope_percent > 15:
            slope_score = 30
        elif land.slope_percent > 8:
            slope_score = 60
        elif land.slope_percent > 3:
            slope_score = 90
        score += slope_score * 0.15
        
        return score
    
    def _calc_profit_potential(self, enterprise: Enterprise, land: "LandAnalysis") -> float:
        """Calculate profit potential score (0-100)."""
        
        # Base revenue per ha
        revenue = enterprise.expected_yield_per_ha * enterprise.price_per_unit_usd
        costs = enterprise.operating_cost_per_ha_year
        profit = revenue - costs
        
        # ROI scoring
        if profit <= 0:
            roi_score = 0
        else:
            roi = profit / enterprise.capital_per_ha
            roi_score = min(100, roi * 100)  # 100% ROI = score 100
        
        # Market access adjustment
        market_factor = 1.0
        if land.market_distance_km > 100:
            market_factor = 0.6
        elif land.market_distance_km > 50:
            market_factor = 0.8
        elif land.market_distance_km > 20:
            market_factor = 0.9
        
        # Cold chain adjustment for perishables
        if enterprise.requires_cold_chain and land.market_distance_km > 30:
            market_factor *= 0.7
        
        return roi_score * market_factor
    
    def _calc_risk_score(self, enterprise: Enterprise, land: "LandAnalysis") -> float:
        """Calculate risk score (0-100, lower is better)."""
        
        score = 0.0
        
        # Drought risk (30%)
        if land.rainfall_reliability < 0.5:
            drought_exposure = enterprise.drought_sensitivity * 100 * (1 - land.rainfall_reliability)
        else:
            drought_exposure = enterprise.drought_sensitivity * 50 * (1 - land.rainfall_reliability)
        score += drought_exposure * 0.30
        
        # Pest/disease risk (25%)
        score += enterprise.pest_disease_risk * 100 * 0.25
        
        # Market risk (25%)
        market_risk = enterprise.market_risk * 100
        if land.market_distance_km > 50:
            market_risk *= 1.3
        score += min(100, market_risk) * 0.25
        
        # Price volatility (20%)
        score += enterprise.price_volatility * 100 * 0.20
        
        return min(100, score)
    
    def _analyze_constraints(
        self,
        enterprise: Enterprise,
        land: "LandAnalysis",
        has_irrigation: bool,
        has_electricity: bool,
    ) -> Tuple[List[str], List[str]]:
        """Analyze constraints and generate recommendations."""
        
        constraints = []
        recommendations = []
        
        # Water constraints
        if enterprise.water_demand in ("high", "very_high"):
            if land.water_reliability in ("unreliable", "scarce"):
                constraints.append("Water scarcity")
                recommendations.append("Install borehole with solar pump")
        
        # Electricity
        if enterprise.requires_electricity and not has_electricity:
            constraints.append("No grid electricity")
            recommendations.append("Install solar power system")
        
        # Market access
        if land.market_distance_km > 50:
            constraints.append("Remote from markets")
            if enterprise.requires_cold_chain:
                recommendations.append("Build cold storage facility")
        
        # Slope
        if land.slope_percent > 8:
            constraints.append("Steep terrain")
            recommendations.append("Implement contour farming / terracing")
        
        # Soil
        if land.soil_fertility == "poor":
            constraints.append("Poor soil fertility")
            recommendations.append("Implement soil improvement program")
        
        return constraints, recommendations
