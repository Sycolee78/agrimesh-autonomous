"""
ProfitEstimatorAgent - Economic modeling for farm enterprises.
Simple interface for profit estimation and scenario analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class Scenario(Enum):
    PESSIMISTIC = "pessimistic"
    EXPECTED = "expected"
    OPTIMISTIC = "optimistic"


# Scenario adjustment factors
SCENARIO_FACTORS = {
    Scenario.PESSIMISTIC: {"yield": 0.6, "price": 0.8, "cost": 1.15},
    Scenario.EXPECTED: {"yield": 1.0, "price": 1.0, "cost": 1.0},
    Scenario.OPTIMISTIC: {"yield": 1.25, "price": 1.15, "cost": 0.95},
}


@dataclass
class ProfitEstimate:
    """Profit estimate for a farm plan."""
    year: int
    scenario: str
    
    total_revenue_usd: float
    total_costs_usd: float
    net_profit_usd: float
    roi_percent: float
    profit_per_ha_usd: float
    
    # Integration benefits
    n_fixation_value_usd: float = 0
    manure_value_usd: float = 0
    
    # Risk
    breakeven_yield_factor: float = 1.0
    
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "scenario": self.scenario,
            "total_revenue_usd": self.total_revenue_usd,
            "total_costs_usd": self.total_costs_usd,
            "net_profit_usd": self.net_profit_usd,
            "roi_percent": self.roi_percent,
            "profit_per_ha_usd": self.profit_per_ha_usd,
            "integration_benefits": {
                "n_fixation_value_usd": self.n_fixation_value_usd,
                "manure_value_usd": self.manure_value_usd,
            },
            "breakeven_yield_factor": self.breakeven_yield_factor,
            "notes": self.notes,
        }


class ProfitEstimatorAgent:
    """Agent for estimating farm profitability."""
    
    def __init__(self, labor_cost_per_day: float = 8):
        self.labor_cost = labor_cost_per_day
        self.n_price_per_kg = 1.5
        self.manure_value_per_head = {
            "cattle": 30, "goats": 8, "sheep": 6, "poultry": 0.5, "pigs": 15
        }
    
    def estimate_farm(
        self,
        allocations: Dict[str, float],
        crop_params: Dict[str, Dict],
        livestock_params: Dict[str, Dict],
        total_area_ha: float,
        year: int = 1,
        scenario: Scenario = Scenario.EXPECTED,
    ) -> ProfitEstimate:
        """
        Estimate farm profitability.
        
        Args:
            allocations: Dict of enterprise -> area (crops) or count (livestock)
            crop_params: {crop: {yield, price, cost, labor_days, n_fixation}}
            livestock_params: {livestock: {revenue, cost, labor_days}}
            total_area_ha: Total farm area
            year: Projection year
            scenario: Economic scenario
        """
        factors = SCENARIO_FACTORS[scenario]
        
        total_revenue = 0
        total_costs = 0
        n_fixation_value = 0
        manure_value = 0
        total_labor_days = 0
        
        # Crop economics
        for crop, params in crop_params.items():
            area = allocations.get(crop, 0)
            if area <= 0:
                continue
            
            adj_yield = params.get("yield", 2) * factors["yield"]
            adj_price = params.get("price", 300) * factors["price"]
            adj_cost = params.get("cost", 200) * factors["cost"]
            
            revenue = area * adj_yield * adj_price
            cost = area * adj_cost
            labor_days = area * params.get("labor_days", 40)
            
            total_revenue += revenue
            total_costs += cost
            total_labor_days += labor_days
            
            # N-fixation benefit
            n_fix = params.get("n_fixation", 0)
            if n_fix > 0:
                n_fixation_value += area * n_fix * self.n_price_per_kg
        
        # Livestock economics
        for livestock, params in livestock_params.items():
            count = int(allocations.get(livestock, 0))
            if count <= 0:
                continue
            
            adj_revenue = params.get("revenue", 100) * factors["yield"] * factors["price"]
            adj_cost = params.get("cost", 50) * factors["cost"]
            
            revenue = count * adj_revenue
            cost = count * adj_cost
            labor_days = count * params.get("labor_days", 10)
            
            total_revenue += revenue
            total_costs += cost
            total_labor_days += labor_days
            
            # Manure value
            manure_value += count * self.manure_value_per_head.get(livestock, 5)
        
        # Labor costs
        labor_costs = total_labor_days * self.labor_cost
        total_costs += labor_costs
        
        # Calculate metrics
        net_profit = total_revenue - total_costs
        total_investment = total_costs
        roi = (net_profit / total_investment * 100) if total_investment > 0 else 0
        profit_per_ha = net_profit / total_area_ha if total_area_ha > 0 else 0
        
        # Breakeven
        breakeven = total_costs / total_revenue if total_revenue > 0 else 1.0
        
        # Notes
        notes = []
        if n_fixation_value > 50:
            notes.append(f"Legume N-fixation saves ~${n_fixation_value:.0f}")
        if manure_value > 100:
            notes.append(f"Manure worth ~${manure_value:.0f} for soil fertility")
        if breakeven > 0.8:
            notes.append("High breakeven - vulnerable to yield shocks")
        
        return ProfitEstimate(
            year=year,
            scenario=scenario.value,
            total_revenue_usd=total_revenue,
            total_costs_usd=total_costs,
            net_profit_usd=net_profit,
            roi_percent=roi,
            profit_per_ha_usd=profit_per_ha,
            n_fixation_value_usd=n_fixation_value,
            manure_value_usd=manure_value,
            breakeven_yield_factor=breakeven,
            notes=notes,
        )
    
    def multi_year_projection(
        self,
        allocations: Dict[str, float],
        crop_params: Dict[str, Dict],
        livestock_params: Dict[str, Dict],
        total_area_ha: float,
        years: int = 3,
    ) -> Dict[str, Any]:
        """Multi-year projection with scenarios."""
        results = {"years": years, "scenarios": {}}
        
        for scenario in Scenario:
            yearly = []
            cumulative = 0
            
            for year in range(1, years + 1):
                est = self.estimate_farm(
                    allocations, crop_params, livestock_params,
                    total_area_ha, year, scenario
                )
                cumulative += est.net_profit_usd
                yearly.append({
                    "year": year,
                    "net_profit": est.net_profit_usd,
                    "cumulative": cumulative,
                })
            
            results["scenarios"][scenario.value] = {
                "yearly": yearly,
                "total_profit": cumulative,
            }
        
        exp = results["scenarios"]["expected"]["total_profit"]
        pess = results["scenarios"]["pessimistic"]["total_profit"]
        opt = results["scenarios"]["optimistic"]["total_profit"]
        
        results["summary"] = {
            "expected_total_profit": exp,
            "profit_range": {"min": pess, "max": opt},
            "risk_adjusted_profit": exp * 0.6 + pess * 0.3 + opt * 0.1,
        }
        
        return results
