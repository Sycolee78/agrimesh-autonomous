"""
Capital Tier Classification Engine

Classifies farm plans into capital tiers:
- A: High capital, high return
- B: Moderate capital, balanced return
- C: Low capital, resilient/slow growth
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.strategic_planner.enterprise_ranker import Enterprise, RankedEnterprise


@dataclass
class CapitalTierPlan:
    """A farm plan for a specific capital tier."""
    tier: str  # "A", "B", "C"
    tier_name: str
    tier_description: str
    
    # Allocation
    enterprise_mix: Dict[str, float]  # enterprise_id -> allocation
    enterprise_details: List[Dict]    # Detailed info per enterprise
    
    # Capital
    total_capital_required: float
    startup_capital: float
    working_capital: float
    capital_breakdown: Dict[str, float]  # Category -> amount
    
    # Returns
    expected_annual_revenue: float
    expected_annual_profit: float
    expected_roi_3yr: float
    profit_probability_3yr: float
    
    # Risk
    risk_level: str  # "low", "moderate", "high"
    risk_factors: List[str]
    
    # Timing
    time_to_first_revenue_months: int
    breakeven_months: int
    
    # Infrastructure
    required_infrastructure: List[str]
    optional_infrastructure: List[str]


@dataclass
class CapitalClassification:
    """Complete capital tier classification."""
    land_area_ha: float
    tier_a: Optional[CapitalTierPlan]
    tier_b: Optional[CapitalTierPlan]
    tier_c: Optional[CapitalTierPlan]
    recommended_tier: str
    recommendation_reason: str


# Capital thresholds (USD per hectare)
CAPITAL_THRESHOLDS = {
    "A": {"min": 5000, "typical": 15000, "max": 50000},
    "B": {"min": 1500, "typical": 4000, "max": 10000},
    "C": {"min": 200, "typical": 800, "max": 2000},
}


class CapitalClassifier:
    """
    Classifies enterprises and creates tiered farm plans.
    """
    
    def __init__(self):
        self.thresholds = CAPITAL_THRESHOLDS
    
    def classify_and_plan(
        self,
        ranked_enterprises: List[RankedEnterprise],
        land_analysis: "LandAnalysis",
        available_capital: Optional[float] = None,
    ) -> CapitalClassification:
        """
        Create farm plans for each capital tier.
        
        Args:
            ranked_enterprises: Pre-ranked enterprises for this land
            land_analysis: Land analysis result
            available_capital: Optional capital constraint
        
        Returns:
            CapitalClassification with plans for each tier
        """
        
        area = land_analysis.area_ha
        
        # Generate tier plans
        tier_a = self._generate_tier_plan(
            tier="A",
            ranked=ranked_enterprises,
            land=land_analysis,
            target_capital_per_ha=self.thresholds["A"]["typical"],
        )
        
        tier_b = self._generate_tier_plan(
            tier="B",
            ranked=ranked_enterprises,
            land=land_analysis,
            target_capital_per_ha=self.thresholds["B"]["typical"],
        )
        
        tier_c = self._generate_tier_plan(
            tier="C",
            ranked=ranked_enterprises,
            land=land_analysis,
            target_capital_per_ha=self.thresholds["C"]["typical"],
        )
        
        # Determine recommended tier
        recommended, reason = self._recommend_tier(
            tier_a, tier_b, tier_c, available_capital, land_analysis
        )
        
        return CapitalClassification(
            land_area_ha=area,
            tier_a=tier_a,
            tier_b=tier_b,
            tier_c=tier_c,
            recommended_tier=recommended,
            recommendation_reason=reason,
        )
    
    def _generate_tier_plan(
        self,
        tier: str,
        ranked: List[RankedEnterprise],
        land: "LandAnalysis",
        target_capital_per_ha: float,
    ) -> Optional[CapitalTierPlan]:
        """Generate a plan for a specific tier."""
        
        # Tier characteristics
        tier_info = {
            "A": {
                "name": "High Capital / High Return",
                "description": "Commercial-scale operations with infrastructure investment",
                "prefer": ["greenhouse_vegetables", "hydroponics", "aeroponics", "dairy_cattle", "tobacco"],
                "risk": "high",
            },
            "B": {
                "name": "Moderate Capital / Balanced Return",
                "description": "Mixed farming with targeted improvements",
                "prefer": ["maize", "vegetables", "poultry_layers", "goats", "pigs"],
                "risk": "moderate",
            },
            "C": {
                "name": "Low Capital / Resilient Growth",
                "description": "Rain-fed cropping with small livestock, minimal infrastructure",
                "prefer": ["sorghum", "groundnuts", "goats", "poultry_broilers", "fodder"],
                "risk": "low",
            },
        }
        
        info = tier_info[tier]
        
        # Filter and select enterprises
        selected = []
        remaining_area = land.area_ha
        total_capital = 0.0
        max_capital = target_capital_per_ha * land.area_ha * 1.5
        
        # Prioritize preferred enterprises for this tier
        preferred_ranked = sorted(
            ranked,
            key=lambda x: (
                1 if x.enterprise.id in info["prefer"] else 0,
                x.overall_rank_score
            ),
            reverse=True
        )
        
        for re in preferred_ranked:
            e = re.enterprise
            
            # Skip if over budget
            if total_capital >= max_capital:
                break
            
            # Determine allocation
            if e.category.value == "livestock":
                # For livestock, allocate based on carrying capacity
                max_units = remaining_area / max(0.1, e.land_per_unit)
                units = min(max_units, 50)  # Cap at reasonable numbers
                
                if units < 5:
                    continue  # Not enough for viable operation
                
                capital_needed = e.capital_per_ha * units
                
                if total_capital + capital_needed > max_capital:
                    # Scale down
                    units = (max_capital - total_capital) / e.capital_per_ha
                    if units < 3:
                        continue
                
                selected.append((e, round(units, 0), capital_needed))
                total_capital += capital_needed
                remaining_area -= units * e.land_per_unit
                
            elif e.category.value == "controlled_environment":
                # CEA: small area, high capital
                alloc = min(e.optimal_area_ha, remaining_area * 0.2, 0.5)  # Max 0.5 ha
                capital_needed = e.capital_per_ha * alloc
                
                if total_capital + capital_needed > max_capital:
                    continue
                
                selected.append((e, alloc, capital_needed))
                total_capital += capital_needed
                remaining_area -= alloc
                
            else:
                # Crops: allocate proportionally
                alloc = min(e.optimal_area_ha, remaining_area * 0.4)
                capital_needed = e.capital_per_ha * alloc
                
                if total_capital + capital_needed > max_capital:
                    alloc = (max_capital - total_capital) / max(1, e.capital_per_ha)
                    if alloc < e.min_area_ha * 0.5:
                        continue
                
                selected.append((e, alloc, capital_needed))
                total_capital += capital_needed
                remaining_area -= alloc
            
            if remaining_area < 0.1:
                break
        
        if not selected:
            return None
        
        # Calculate financial metrics
        annual_revenue = 0.0
        annual_costs = 0.0
        working_capital = 0.0
        first_revenue_months = 12
        
        enterprise_details = []
        capital_breakdown = {"crops": 0, "livestock": 0, "infrastructure": 0, "equipment": 0}
        
        for e, alloc, capital in selected:
            revenue = e.expected_yield_per_ha * e.price_per_unit_usd * alloc
            costs = e.operating_cost_per_ha_year * alloc
            
            annual_revenue += revenue
            annual_costs += costs
            working_capital += costs * 0.3
            
            first_revenue_months = min(first_revenue_months, e.time_to_first_revenue_months)
            
            if e.category.value == "livestock":
                capital_breakdown["livestock"] += capital
            elif e.category.value == "controlled_environment":
                capital_breakdown["infrastructure"] += capital
            else:
                capital_breakdown["crops"] += capital
            
            enterprise_details.append({
                "enterprise_id": e.id,
                "name": e.name,
                "category": e.category.value,
                "allocation": alloc,
                "allocation_unit": "animals" if e.category.value == "livestock" else "hectares",
                "capital_required": round(capital, 0),
                "annual_revenue": round(revenue, 0),
                "annual_costs": round(costs, 0),
            })
        
        # Infrastructure requirements
        infra_required = []
        infra_optional = []
        
        if any(e.requires_irrigation for e, _, _ in selected):
            if land.water_reliability in ("unreliable", "scarce"):
                infra_required.append("Borehole with pump")
                capital_breakdown["infrastructure"] += 5000
            infra_required.append("Drip irrigation system")
            capital_breakdown["infrastructure"] += 2000
        
        if any(e.requires_electricity for e, _, _ in selected):
            if not land.electricity_access:
                infra_required.append("Solar power system")
                capital_breakdown["infrastructure"] += 3000
        
        if any(e.requires_cold_chain for e, _, _ in selected):
            infra_optional.append("Cold storage facility")
        
        if any(e.category.value == "livestock" for e, _, _ in selected):
            infra_required.append("Fencing")
            infra_required.append("Water troughs")
            capital_breakdown["livestock"] += 1000
        
        # Risk factors
        risk_factors = []
        for e, _, _ in selected:
            if e.drought_sensitivity > 0.6:
                risk_factors.append(f"{e.name}: Drought sensitive")
            if e.market_risk > 0.4:
                risk_factors.append(f"{e.name}: Market price volatility")
        
        # Profit probability (simplified)
        avg_drought = sum(e.drought_sensitivity for e, _, _ in selected) / len(selected)
        avg_market = sum(e.market_risk for e, _, _ in selected) / len(selected)
        profit_prob = max(0.3, min(0.95, 0.85 - avg_drought * 0.3 - avg_market * 0.2))
        profit_prob *= land.rainfall_reliability
        
        # Calculate totals
        startup_capital = sum(c for _, _, c in selected) + capital_breakdown["infrastructure"]
        annual_profit = annual_revenue - annual_costs
        roi_3yr = (annual_profit * 3 - startup_capital) / max(1, startup_capital)
        breakeven = int(startup_capital / max(1, annual_profit / 12)) if annual_profit > 0 else 999
        
        return CapitalTierPlan(
            tier=tier,
            tier_name=info["name"],
            tier_description=info["description"],
            enterprise_mix={e.id: alloc for e, alloc, _ in selected},
            enterprise_details=enterprise_details,
            total_capital_required=round(startup_capital + working_capital, 0),
            startup_capital=round(startup_capital, 0),
            working_capital=round(working_capital, 0),
            capital_breakdown=capital_breakdown,
            expected_annual_revenue=round(annual_revenue, 0),
            expected_annual_profit=round(annual_profit, 0),
            expected_roi_3yr=round(roi_3yr * 100, 1),
            profit_probability_3yr=round(profit_prob * 100, 1),
            risk_level=info["risk"],
            risk_factors=risk_factors[:5],
            time_to_first_revenue_months=first_revenue_months,
            breakeven_months=min(breakeven, 60),
            required_infrastructure=infra_required,
            optional_infrastructure=infra_optional,
        )
    
    def _recommend_tier(
        self,
        tier_a: Optional[CapitalTierPlan],
        tier_b: Optional[CapitalTierPlan],
        tier_c: Optional[CapitalTierPlan],
        available_capital: Optional[float],
        land: "LandAnalysis",
    ) -> Tuple[str, str]:
        """Recommend the best tier based on context."""
        
        # If capital constraint provided, filter
        if available_capital:
            if tier_a and tier_a.total_capital_required <= available_capital:
                return "A", f"Capital available (${available_capital:,.0f}) supports high-return tier"
            if tier_b and tier_b.total_capital_required <= available_capital:
                return "B", f"Balanced tier fits within ${available_capital:,.0f} budget"
            if tier_c:
                return "C", f"Low-capital tier recommended for ${available_capital:,.0f} budget"
        
        # Risk-based recommendation
        if land.rainfall_reliability < 0.5:
            return "C", "Low rainfall reliability favors resilient, low-capital approach"
        
        if land.land_class == "prime_arable" and land.water_reliability in ("reliable", "seasonal"):
            if tier_a:
                return "A", "Prime land with water access supports intensive operations"
            return "B", "Prime land suitable for mixed farming"
        
        if land.land_class in ("marginal", "pastoral"):
            return "C", "Marginal land favors low-input, resilient systems"
        
        # Default to balanced
        return "B", "Balanced approach for typical conditions"
