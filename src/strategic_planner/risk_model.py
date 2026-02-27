"""
Risk Assessment Model

Comprehensive risk analysis for farm plans including:
- Climate risk
- Market risk
- Operational risk
- Financial risk
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RiskCategory(Enum):
    CLIMATE = "climate"
    MARKET = "market"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"


@dataclass
class RiskFactor:
    """Individual risk factor."""
    id: str
    name: str
    category: RiskCategory
    severity: str  # "low", "moderate", "high", "critical"
    probability: float  # 0-1
    impact_description: str
    mitigation_strategies: List[str]


@dataclass
class RiskAssessment:
    """Complete risk assessment."""
    overall_risk_level: str  # "low", "moderate", "high"
    overall_risk_score: float  # 0-100
    
    # Category scores
    climate_risk_score: float
    market_risk_score: float
    operational_risk_score: float
    financial_risk_score: float
    
    # Detailed risks
    risk_factors: List[RiskFactor]
    top_risks: List[RiskFactor]
    
    # Mitigation
    recommended_mitigations: List[str]
    insurance_recommendations: List[str]
    
    # Scenario impacts
    drought_impact_pct: float
    price_crash_impact_pct: float
    disease_outbreak_impact_pct: float


class RiskModel:
    """
    Comprehensive risk assessment for farm plans.
    """
    
    def assess_risks(
        self,
        enterprise_mix: Dict[str, float],
        land_analysis: "LandAnalysis",
        capital_tier: str,
    ) -> RiskAssessment:
        """
        Perform complete risk assessment.
        """
        
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        risk_factors = []
        
        # Climate risks
        climate_score, climate_risks = self._assess_climate_risks(
            enterprise_mix, land_analysis
        )
        risk_factors.extend(climate_risks)
        
        # Market risks
        market_score, market_risks = self._assess_market_risks(
            enterprise_mix, land_analysis
        )
        risk_factors.extend(market_risks)
        
        # Operational risks
        ops_score, ops_risks = self._assess_operational_risks(
            enterprise_mix, land_analysis, capital_tier
        )
        risk_factors.extend(ops_risks)
        
        # Financial risks
        fin_score, fin_risks = self._assess_financial_risks(
            enterprise_mix, land_analysis, capital_tier
        )
        risk_factors.extend(fin_risks)
        
        # Overall score (weighted average)
        overall = (
            climate_score * 0.30 +
            market_score * 0.25 +
            ops_score * 0.25 +
            fin_score * 0.20
        )
        
        # Determine level
        if overall < 30:
            level = "low"
        elif overall < 60:
            level = "moderate"
        else:
            level = "high"
        
        # Top risks
        top_risks = sorted(
            risk_factors,
            key=lambda r: r.probability * (3 if r.severity == "critical" else 2 if r.severity == "high" else 1),
            reverse=True
        )[:5]
        
        # Mitigation recommendations
        mitigations = self._generate_mitigations(top_risks, land_analysis)
        insurance = self._recommend_insurance(enterprise_mix, top_risks)
        
        # Scenario impacts
        drought_impact = self._calc_drought_impact(enterprise_mix)
        price_impact = self._calc_price_crash_impact(enterprise_mix)
        disease_impact = self._calc_disease_impact(enterprise_mix)
        
        return RiskAssessment(
            overall_risk_level=level,
            overall_risk_score=round(overall, 1),
            climate_risk_score=round(climate_score, 1),
            market_risk_score=round(market_score, 1),
            operational_risk_score=round(ops_score, 1),
            financial_risk_score=round(fin_score, 1),
            risk_factors=risk_factors,
            top_risks=top_risks,
            recommended_mitigations=mitigations,
            insurance_recommendations=insurance,
            drought_impact_pct=round(drought_impact, 1),
            price_crash_impact_pct=round(price_impact, 1),
            disease_outbreak_impact_pct=round(disease_impact, 1),
        )
    
    def _assess_climate_risks(
        self,
        enterprise_mix: Dict[str, float],
        land: "LandAnalysis",
    ) -> tuple:
        """Assess climate-related risks."""
        
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        risks = []
        score = 0.0
        
        # Drought risk
        if land.rainfall_reliability < 0.6:
            drought_prob = 1 - land.rainfall_reliability
            risks.append(RiskFactor(
                id="drought",
                name="Drought",
                category=RiskCategory.CLIMATE,
                severity="high" if drought_prob > 0.5 else "moderate",
                probability=drought_prob,
                impact_description="Reduced crop yields and livestock water stress",
                mitigation_strategies=[
                    "Install borehole with solar pump",
                    "Grow drought-resistant varieties",
                    "Implement rainwater harvesting",
                ],
            ))
            score += drought_prob * 50
        
        # Flood risk
        if land.flood_risk != "none":
            flood_prob = 0.3 if land.flood_risk == "moderate" else 0.1
            risks.append(RiskFactor(
                id="flood",
                name="Flooding",
                category=RiskCategory.CLIMATE,
                severity="moderate",
                probability=flood_prob,
                impact_description="Crop damage, infrastructure damage, livestock loss",
                mitigation_strategies=[
                    "Build drainage systems",
                    "Elevate storage areas",
                    "Use raised beds",
                ],
            ))
            score += flood_prob * 40
        
        # Frost risk
        if land.frost_risk in ("moderate", "high"):
            frost_prob = 0.4 if land.frost_risk == "high" else 0.2
            risks.append(RiskFactor(
                id="frost",
                name="Frost damage",
                category=RiskCategory.CLIMATE,
                severity="moderate",
                probability=frost_prob,
                impact_description="Sensitive crop damage, delayed planting",
                mitigation_strategies=[
                    "Plant frost-tolerant varieties",
                    "Use protective covers",
                    "Time planting carefully",
                ],
            ))
            score += frost_prob * 30
        
        # Heat stress
        if land.aez_zone in ("IV", "V"):
            risks.append(RiskFactor(
                id="heat_stress",
                name="Heat stress",
                category=RiskCategory.CLIMATE,
                severity="moderate",
                probability=0.4,
                impact_description="Reduced livestock productivity, crop stress",
                mitigation_strategies=[
                    "Provide shade structures",
                    "Use heat-tolerant varieties",
                    "Adjust work schedules",
                ],
            ))
            score += 20
        
        return score, risks
    
    def _assess_market_risks(
        self,
        enterprise_mix: Dict[str, float],
        land: "LandAnalysis",
    ) -> tuple:
        """Assess market-related risks."""
        
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        risks = []
        score = 0.0
        
        # Price volatility
        total_alloc = sum(enterprise_mix.values()) or 1
        weighted_volatility = sum(
            ALL_ENTERPRISES[eid].price_volatility * alloc
            for eid, alloc in enterprise_mix.items()
            if eid in ALL_ENTERPRISES
        ) / total_alloc
        
        if weighted_volatility > 0.3:
            risks.append(RiskFactor(
                id="price_volatility",
                name="Price volatility",
                category=RiskCategory.MARKET,
                severity="high" if weighted_volatility > 0.4 else "moderate",
                probability=0.7,
                impact_description="Revenue fluctuation, cash flow uncertainty",
                mitigation_strategies=[
                    "Diversify enterprise mix",
                    "Use forward contracts",
                    "Target multiple markets",
                ],
            ))
            score += weighted_volatility * 80
        
        # Market access
        if land.market_distance_km > 50:
            risks.append(RiskFactor(
                id="market_access",
                name="Limited market access",
                category=RiskCategory.MARKET,
                severity="moderate",
                probability=1.0,
                impact_description="Higher transport costs, perishable losses",
                mitigation_strategies=[
                    "Join farmer cooperatives",
                    "Build on-farm storage",
                    "Focus on non-perishables",
                ],
            ))
            score += 25
        
        # Concentration risk
        max_share = max(enterprise_mix.values()) / total_alloc if enterprise_mix else 0
        if max_share > 0.6:
            risks.append(RiskFactor(
                id="concentration",
                name="Enterprise concentration",
                category=RiskCategory.MARKET,
                severity="moderate",
                probability=0.5,
                impact_description="Over-reliance on single enterprise",
                mitigation_strategies=[
                    "Diversify crops/livestock",
                    "Add value-addition activities",
                ],
            ))
            score += max_share * 30
        
        return score, risks
    
    def _assess_operational_risks(
        self,
        enterprise_mix: Dict[str, float],
        land: "LandAnalysis",
        capital_tier: str,
    ) -> tuple:
        """Assess operational risks."""
        
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        risks = []
        score = 0.0
        
        # Labor risk
        total_labor = sum(
            ALL_ENTERPRISES[eid].labor_days_per_ha_year * alloc
            for eid, alloc in enterprise_mix.items()
            if eid in ALL_ENTERPRISES
        )
        
        if total_labor > 500:
            risks.append(RiskFactor(
                id="labor_shortage",
                name="Labor availability",
                category=RiskCategory.OPERATIONAL,
                severity="moderate",
                probability=0.3,
                impact_description="Difficulty hiring seasonal workers",
                mitigation_strategies=[
                    "Invest in mechanization",
                    "Stagger planting dates",
                    "Build worker housing",
                ],
            ))
            score += 20
        
        # Pest/disease risk
        has_livestock = any(
            ALL_ENTERPRISES.get(eid, {}).category.value == "livestock"
            for eid in enterprise_mix
            if eid in ALL_ENTERPRISES
        )
        
        if has_livestock:
            risks.append(RiskFactor(
                id="livestock_disease",
                name="Livestock disease outbreak",
                category=RiskCategory.OPERATIONAL,
                severity="high",
                probability=0.15,
                impact_description="Animal mortality, quarantine, market closure",
                mitigation_strategies=[
                    "Implement biosecurity protocols",
                    "Regular veterinary checks",
                    "Vaccination programs",
                ],
            ))
            score += 25
        
        # Water system failure
        if land.water_reliability in ("unreliable", "scarce"):
            risks.append(RiskFactor(
                id="water_failure",
                name="Water system failure",
                category=RiskCategory.OPERATIONAL,
                severity="high",
                probability=0.2,
                impact_description="Irrigation failure, livestock dehydration",
                mitigation_strategies=[
                    "Install backup water storage",
                    "Maintain pumps regularly",
                    "Have emergency water supply",
                ],
            ))
            score += 30
        
        return score, risks
    
    def _assess_financial_risks(
        self,
        enterprise_mix: Dict[str, float],
        land: "LandAnalysis",
        capital_tier: str,
    ) -> tuple:
        """Assess financial risks."""
        
        risks = []
        score = 0.0
        
        # Capital intensity risk
        if capital_tier == "A":
            risks.append(RiskFactor(
                id="high_capital",
                name="High capital exposure",
                category=RiskCategory.FINANCIAL,
                severity="moderate",
                probability=0.3,
                impact_description="Large potential losses if operations fail",
                mitigation_strategies=[
                    "Secure adequate insurance",
                    "Phase investments gradually",
                    "Maintain cash reserves",
                ],
            ))
            score += 25
        
        # Cash flow risk
        risks.append(RiskFactor(
            id="cash_flow",
            name="Cash flow gaps",
            category=RiskCategory.FINANCIAL,
            severity="moderate",
            probability=0.4,
            impact_description="Insufficient funds during growing season",
            mitigation_strategies=[
                "Maintain 3-month operating reserve",
                "Stagger production cycles",
                "Establish credit lines",
            ],
        ))
        score += 15
        
        return score, risks
    
    def _generate_mitigations(
        self,
        top_risks: List[RiskFactor],
        land: "LandAnalysis",
    ) -> List[str]:
        """Generate prioritized mitigation strategies."""
        
        all_strategies = []
        for risk in top_risks:
            all_strategies.extend(risk.mitigation_strategies)
        
        # Prioritize and deduplicate
        seen = set()
        unique = []
        for s in all_strategies:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        
        return unique[:8]
    
    def _recommend_insurance(
        self,
        enterprise_mix: Dict[str, float],
        top_risks: List[RiskFactor],
    ) -> List[str]:
        """Recommend insurance products."""
        
        insurance = []
        
        risk_ids = {r.id for r in top_risks}
        
        if "drought" in risk_ids:
            insurance.append("Crop weather index insurance")
        
        if "livestock_disease" in risk_ids:
            insurance.append("Livestock mortality insurance")
        
        if "flood" in risk_ids:
            insurance.append("Flood damage insurance")
        
        insurance.append("Multi-peril crop insurance")
        insurance.append("Farm infrastructure insurance")
        
        return insurance[:4]
    
    def _calc_drought_impact(self, enterprise_mix: Dict[str, float]) -> float:
        """Calculate revenue impact of drought scenario."""
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        weighted_sensitivity = sum(
            ALL_ENTERPRISES[eid].drought_sensitivity * alloc
            for eid, alloc in enterprise_mix.items()
            if eid in ALL_ENTERPRISES
        ) / max(1, sum(enterprise_mix.values()))
        
        return weighted_sensitivity * 60  # Up to 60% revenue impact
    
    def _calc_price_crash_impact(self, enterprise_mix: Dict[str, float]) -> float:
        """Calculate revenue impact of 30% price drop."""
        return 30.0  # Direct 30% revenue impact
    
    def _calc_disease_impact(self, enterprise_mix: Dict[str, float]) -> float:
        """Calculate revenue impact of disease outbreak."""
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        livestock_share = sum(
            alloc for eid, alloc in enterprise_mix.items()
            if eid in ALL_ENTERPRISES and ALL_ENTERPRISES[eid].category.value == "livestock"
        ) / max(1, sum(enterprise_mix.values()))
        
        return livestock_share * 50  # Up to 50% impact on livestock revenue
