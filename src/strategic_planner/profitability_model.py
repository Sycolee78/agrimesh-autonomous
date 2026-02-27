"""
Profitability Model Engine

Calculates probability-based profitability projections
using Monte Carlo simulation and historical variance.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class ProfitScenario:
    """Single scenario projection."""
    year: int
    revenue: float
    operating_costs: float
    gross_profit: float
    cumulative_profit: float


@dataclass
class ProfitabilityProjection:
    """Complete profitability analysis."""
    enterprise_mix: Dict[str, float]  # enterprise_id -> area_ha or count
    
    # Capital
    startup_capital: float
    working_capital_year1: float
    total_capital_required: float
    
    # Multi-year projections
    pessimistic: List[ProfitScenario]  # 10th percentile
    expected: List[ProfitScenario]      # 50th percentile (median)
    optimistic: List[ProfitScenario]    # 90th percentile
    
    # Key metrics
    breakeven_months: int
    irr_3yr: float  # Internal rate of return
    npv_3yr: float  # Net present value
    payback_period_months: int
    
    # Probability
    profit_probability_3yr: float  # Probability of positive cumulative profit
    profit_probability_5yr: float
    
    # Risk metrics
    max_drawdown: float  # Worst case loss
    volatility: float    # Standard deviation of returns
    sharpe_ratio: float  # Risk-adjusted return
    
    # Sensitivity
    sensitivity: Dict[str, float]  # Factor -> impact on profit


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    simulations: int
    profit_3yr_mean: float
    profit_3yr_std: float
    profit_3yr_median: float
    profit_3yr_10th: float
    profit_3yr_90th: float
    profit_probability_3yr: float
    breakeven_probability_3yr: float
    roi_distribution: List[float]


class ProfitabilityModel:
    """
    Monte Carlo-based profitability modeling.
    """
    
    def __init__(self, simulations: int = 1000):
        self.simulations = simulations
        random.seed(42)  # Reproducible
    
    def project_profitability(
        self,
        enterprise_allocations: Dict[str, Tuple["Enterprise", float]],  # id -> (enterprise, allocation)
        land_analysis: "LandAnalysis",
        projection_years: int = 5,
        discount_rate: float = 0.12,
    ) -> ProfitabilityProjection:
        """
        Generate complete profitability projection.
        
        Args:
            enterprise_allocations: Dict of enterprise_id -> (Enterprise, area_or_count)
            land_analysis: Land analysis result
            projection_years: Years to project
            discount_rate: Discount rate for NPV
        
        Returns:
            Complete ProfitabilityProjection
        """
        
        # Calculate capital requirements
        startup_capital, working_capital = self._calc_capital_requirements(
            enterprise_allocations, land_analysis
        )
        
        # Run Monte Carlo simulation
        mc_results = self._run_monte_carlo(
            enterprise_allocations,
            land_analysis,
            projection_years,
        )
        
        # Generate scenario projections
        pessimistic = self._generate_scenario(
            enterprise_allocations, land_analysis, projection_years, "pessimistic"
        )
        expected = self._generate_scenario(
            enterprise_allocations, land_analysis, projection_years, "expected"
        )
        optimistic = self._generate_scenario(
            enterprise_allocations, land_analysis, projection_years, "optimistic"
        )
        
        # Calculate key metrics
        breakeven_months = self._calc_breakeven(expected, startup_capital + working_capital)
        irr = self._calc_irr(expected, startup_capital + working_capital)
        npv = self._calc_npv(expected, startup_capital + working_capital, discount_rate)
        
        # Risk metrics
        max_drawdown = self._calc_max_drawdown(pessimistic, startup_capital + working_capital)
        volatility = mc_results.profit_3yr_std / max(1, mc_results.profit_3yr_mean)
        sharpe = self._calc_sharpe_ratio(mc_results, discount_rate)
        
        # Sensitivity analysis
        sensitivity = self._sensitivity_analysis(
            enterprise_allocations, land_analysis, projection_years
        )
        
        return ProfitabilityProjection(
            enterprise_mix={k: v[1] for k, v in enterprise_allocations.items()},
            startup_capital=round(startup_capital, 0),
            working_capital_year1=round(working_capital, 0),
            total_capital_required=round(startup_capital + working_capital, 0),
            pessimistic=pessimistic,
            expected=expected,
            optimistic=optimistic,
            breakeven_months=breakeven_months,
            irr_3yr=round(irr * 100, 1),  # As percentage
            npv_3yr=round(npv, 0),
            payback_period_months=breakeven_months,
            profit_probability_3yr=round(mc_results.profit_probability_3yr * 100, 1),
            profit_probability_5yr=round(mc_results.profit_probability_3yr * 1.1, 1),  # Approximate
            max_drawdown=round(max_drawdown, 0),
            volatility=round(volatility * 100, 1),
            sharpe_ratio=round(sharpe, 2),
            sensitivity=sensitivity,
        )
    
    def _calc_capital_requirements(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
    ) -> Tuple[float, float]:
        """Calculate startup and working capital."""
        
        startup = 0.0
        working = 0.0
        
        for eid, (enterprise, allocation) in allocations.items():
            # Startup capital
            if enterprise.category.value == "livestock":
                # allocation is number of animals
                startup += enterprise.capital_per_ha * allocation
            else:
                # allocation is hectares
                startup += enterprise.capital_per_ha * allocation
            
            # Working capital (first year operating costs + buffer)
            working += enterprise.operating_cost_per_ha_year * allocation * 0.3
        
        # Infrastructure additions based on land
        if land_analysis.water_reliability in ("unreliable", "scarce"):
            startup += 5000  # Borehole
        
        if not land_analysis.electricity_access:
            startup += 3000  # Solar system
        
        # Contingency
        startup *= 1.1
        working *= 1.2
        
        return startup, working
    
    def _run_monte_carlo(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
        years: int,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation."""
        
        profits_3yr = []
        
        for _ in range(self.simulations):
            cumulative = 0.0
            
            for year in range(1, min(4, years + 1)):
                year_profit = 0.0
                
                for eid, (enterprise, allocation) in allocations.items():
                    # Random yield factor based on variance
                    yield_factor = random.gauss(1.0, enterprise.drought_sensitivity * 0.3)
                    yield_factor = max(0.3, min(1.5, yield_factor))
                    
                    # Random price factor
                    price_factor = random.gauss(1.0, enterprise.price_volatility * 0.5)
                    price_factor = max(0.5, min(1.5, price_factor))
                    
                    # Climate factor based on AEZ
                    climate_factor = random.gauss(land_analysis.rainfall_reliability, 0.15)
                    climate_factor = max(0.5, min(1.2, climate_factor))
                    
                    # Calculate revenue
                    base_yield = enterprise.expected_yield_per_ha * allocation
                    actual_yield = base_yield * yield_factor * climate_factor
                    revenue = actual_yield * enterprise.price_per_unit_usd * price_factor
                    
                    # Operating costs (some variance)
                    cost_factor = random.gauss(1.0, 0.1)
                    costs = enterprise.operating_cost_per_ha_year * allocation * cost_factor
                    
                    year_profit += revenue - costs
                
                cumulative += year_profit
            
            profits_3yr.append(cumulative)
        
        # Statistics
        profits_sorted = sorted(profits_3yr)
        n = len(profits_sorted)
        
        mean_profit = sum(profits_3yr) / n
        variance = sum((p - mean_profit) ** 2 for p in profits_3yr) / n
        std_profit = math.sqrt(variance)
        
        median_profit = profits_sorted[n // 2]
        p10 = profits_sorted[int(n * 0.1)]
        p90 = profits_sorted[int(n * 0.9)]
        
        profitable_count = sum(1 for p in profits_3yr if p > 0)
        
        return MonteCarloResult(
            simulations=self.simulations,
            profit_3yr_mean=mean_profit,
            profit_3yr_std=std_profit,
            profit_3yr_median=median_profit,
            profit_3yr_10th=p10,
            profit_3yr_90th=p90,
            profit_probability_3yr=profitable_count / n,
            breakeven_probability_3yr=profitable_count / n,
            roi_distribution=profits_3yr[:100],  # Sample for visualization
        )
    
    def _generate_scenario(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
        years: int,
        scenario: str,
    ) -> List[ProfitScenario]:
        """Generate yearly projection for a scenario."""
        
        # Scenario multipliers
        multipliers = {
            "pessimistic": {"yield": 0.7, "price": 0.85, "cost": 1.15},
            "expected": {"yield": 1.0, "price": 1.0, "cost": 1.0},
            "optimistic": {"yield": 1.2, "price": 1.15, "cost": 0.9},
        }
        m = multipliers[scenario]
        
        scenarios = []
        cumulative = 0.0
        
        for year in range(1, years + 1):
            revenue = 0.0
            costs = 0.0
            
            for eid, (enterprise, allocation) in allocations.items():
                # Account for ramp-up in year 1
                ramp = 1.0 if year > 1 else 0.7
                
                # Skip revenue if time-to-revenue not reached
                if year == 1 and enterprise.time_to_first_revenue_months > 9:
                    ramp = 0.3
                
                year_yield = enterprise.expected_yield_per_ha * allocation * m["yield"] * ramp
                year_revenue = year_yield * enterprise.price_per_unit_usd * m["price"]
                year_costs = enterprise.operating_cost_per_ha_year * allocation * m["cost"]
                
                revenue += year_revenue
                costs += year_costs
            
            gross_profit = revenue - costs
            cumulative += gross_profit
            
            scenarios.append(ProfitScenario(
                year=year,
                revenue=round(revenue, 0),
                operating_costs=round(costs, 0),
                gross_profit=round(gross_profit, 0),
                cumulative_profit=round(cumulative, 0),
            ))
        
        return scenarios
    
    def _calc_breakeven(self, expected: List[ProfitScenario], total_capital: float) -> int:
        """Calculate months to breakeven."""
        
        cumulative = -total_capital
        
        for scenario in expected:
            monthly_profit = scenario.gross_profit / 12
            
            for month in range(12):
                cumulative += monthly_profit
                if cumulative >= 0:
                    return (scenario.year - 1) * 12 + month + 1
        
        return 999  # Never breaks even in projection period
    
    def _calc_irr(self, expected: List[ProfitScenario], total_capital: float) -> float:
        """Calculate Internal Rate of Return (simplified)."""
        
        if not expected:
            return 0.0
        
        # Cash flows: initial investment negative, then yearly profits
        cash_flows = [-total_capital]
        for s in expected[:3]:  # 3-year IRR
            cash_flows.append(s.gross_profit)
        
        # Simple IRR approximation using Newton's method
        irr = 0.1  # Initial guess
        
        for _ in range(100):
            npv = sum(cf / (1 + irr) ** i for i, cf in enumerate(cash_flows))
            npv_derivative = sum(-i * cf / (1 + irr) ** (i + 1) for i, cf in enumerate(cash_flows))
            
            if abs(npv_derivative) < 1e-10:
                break
            
            irr = irr - npv / npv_derivative
            
            if abs(npv) < 1:
                break
        
        return max(-1, min(5, irr))  # Cap at -100% to 500%
    
    def _calc_npv(
        self,
        expected: List[ProfitScenario],
        total_capital: float,
        discount_rate: float,
    ) -> float:
        """Calculate Net Present Value."""
        
        npv = -total_capital
        
        for i, s in enumerate(expected[:3]):
            npv += s.gross_profit / (1 + discount_rate) ** (i + 1)
        
        return npv
    
    def _calc_max_drawdown(self, pessimistic: List[ProfitScenario], total_capital: float) -> float:
        """Calculate maximum potential loss."""
        
        cumulative = -total_capital
        max_loss = total_capital
        
        for s in pessimistic:
            cumulative += s.gross_profit
            if cumulative < -max_loss:
                max_loss = -cumulative
        
        return max_loss
    
    def _calc_sharpe_ratio(self, mc_results: MonteCarloResult, risk_free_rate: float) -> float:
        """Calculate Sharpe ratio."""
        
        if mc_results.profit_3yr_std < 1:
            return 0.0
        
        excess_return = mc_results.profit_3yr_mean / mc_results.profit_3yr_std
        return excess_return
    
    def _sensitivity_analysis(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
        years: int,
    ) -> Dict[str, float]:
        """Analyze sensitivity to key factors."""
        
        # Calculate base profit
        base = sum(
            (e.expected_yield_per_ha * e.price_per_unit_usd - e.operating_cost_per_ha_year) * alloc
            for e, alloc in allocations.values()
        ) * min(3, years)
        
        sensitivity = {}
        
        # Price sensitivity
        price_shock = sum(
            e.expected_yield_per_ha * e.price_per_unit_usd * 0.1 * alloc
            for e, alloc in allocations.values()
        ) * min(3, years)
        sensitivity["price_10pct_change"] = round(price_shock / max(1, base) * 100, 1)
        
        # Yield sensitivity
        yield_shock = sum(
            e.expected_yield_per_ha * 0.1 * e.price_per_unit_usd * alloc
            for e, alloc in allocations.values()
        ) * min(3, years)
        sensitivity["yield_10pct_change"] = round(yield_shock / max(1, base) * 100, 1)
        
        # Cost sensitivity
        cost_shock = sum(
            e.operating_cost_per_ha_year * 0.1 * alloc
            for e, alloc in allocations.values()
        ) * min(3, years)
        sensitivity["cost_10pct_change"] = round(cost_shock / max(1, base) * 100, 1)
        
        return sensitivity


def calculate_profit_probability(
    enterprise_mix: List[Tuple["Enterprise", float]],
    land_analysis: "LandAnalysis",
    years: int = 3,
) -> float:
    """
    Quick profit probability calculation for ranking.
    
    Returns probability (0-1) of positive cumulative profit.
    """
    
    model = ProfitabilityModel(simulations=200)  # Fewer for quick estimate
    
    allocations = {e.id: (e, alloc) for e, alloc in enterprise_mix}
    mc = model._run_monte_carlo(allocations, land_analysis, years)
    
    return mc.profit_probability_3yr
