"""
Strategic Farm Planner

Main orchestrator that integrates all planning components to generate
comprehensive farm plans from land coordinates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.strategic_planner.geospatial_analyzer import GeospatialAnalyzer, LandAnalysis
from src.strategic_planner.enterprise_ranker import EnterpriseRanker, RankedEnterprise
from src.strategic_planner.profitability_model import ProfitabilityModel
from src.strategic_planner.spatial_layout_engine import SpatialLayoutEngine
from src.strategic_planner.capital_classifier import CapitalClassifier
from src.strategic_planner.risk_model import RiskModel
from src.strategic_planner.energy_sustainability import EnergySustainabilityPlanner
from src.strategic_planner.output_formatter import StrategicPlanFormatter


@dataclass
class PlanningRequest:
    """Request for strategic farm plan."""
    lat: float
    lon: float
    area_ha: float
    polygon: Optional[List[Tuple[float, float]]] = None
    
    # Optional constraints
    available_capital: Optional[float] = None
    available_labor_days: Optional[int] = None
    
    # Infrastructure
    has_irrigation: bool = False
    has_electricity: bool = False
    
    # Preferences
    preferred_tier: Optional[str] = None  # "A", "B", "C"
    objective: str = "balanced"  # "maximize_profit", "minimize_risk", "balanced", "food_security"
    
    # Exclusions
    exclude_enterprises: Optional[List[str]] = None
    prefer_enterprises: Optional[List[str]] = None


class StrategicFarmPlanner:
    """
    Main strategic farm planning engine.
    
    Usage:
        planner = StrategicFarmPlanner()
        plan = planner.generate_plan(
            lat=-17.83,
            lon=31.05,
            area_ha=10.0,
            available_capital=50000,
        )
    """
    
    def __init__(self):
        self.geo_analyzer = GeospatialAnalyzer()
        self.enterprise_ranker = EnterpriseRanker()
        self.profitability_model = ProfitabilityModel()
        self.layout_engine = SpatialLayoutEngine()
        self.capital_classifier = CapitalClassifier()
        self.risk_model = RiskModel()
        self.energy_planner = EnergySustainabilityPlanner()
        self.formatter = StrategicPlanFormatter()
    
    def generate_plan(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        polygon: Optional[List[Tuple[float, float]]] = None,
        available_capital: Optional[float] = None,
        available_labor_days: Optional[int] = None,
        has_irrigation: bool = False,
        has_electricity: bool = False,
        preferred_tier: Optional[str] = None,
        objective: str = "balanced",
        exclude_enterprises: Optional[List[str]] = None,
        prefer_enterprises: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete strategic farm plan.
        
        Args:
            lat: Latitude
            lon: Longitude
            area_ha: Total area in hectares
            polygon: Optional polygon boundary
            available_capital: Optional capital constraint (USD)
            available_labor_days: Optional labor constraint (days/year)
            has_irrigation: Whether irrigation exists
            has_electricity: Whether grid electricity exists
            preferred_tier: Preferred capital tier ("A", "B", "C")
            objective: Planning objective
            exclude_enterprises: Enterprises to exclude
            prefer_enterprises: Enterprises to prefer
        
        Returns:
            Complete strategic plan dictionary
        """
        
        print(f"\n{'='*60}")
        print(f"Strategic Farm Plan Generation")
        print(f"Location: ({lat}, {lon}), Area: {area_ha} ha")
        print(f"{'='*60}")
        
        # Step 1: Land Analysis
        print("\n[1/7] Analyzing land characteristics...")
        land_analysis = self.geo_analyzer.analyze(lat, lon, area_ha, polygon)
        print(f"  AEZ Zone: {land_analysis.aez_zone}")
        print(f"  Land Class: {land_analysis.land_class}")
        print(f"  Rainfall: {land_analysis.annual_rainfall_mm}mm")
        
        # Update infrastructure flags from land analysis
        if not has_electricity and land_analysis.electricity_access:
            has_electricity = True
        
        # Step 2: Enterprise Ranking
        print("\n[2/7] Ranking viable enterprises...")
        enterprise_rankings = self.enterprise_ranker.rank_enterprises(
            land_analysis=land_analysis,
            available_capital=available_capital,
            available_labor_days=available_labor_days,
            has_irrigation=has_irrigation or land_analysis.water_reliability == "reliable",
            has_electricity=has_electricity,
            exclude_categories=None,
            preferred_categories=prefer_enterprises,
        )
        print(f"  Viable enterprises: {len(enterprise_rankings)}")
        if enterprise_rankings:
            print(f"  Top 3: {', '.join(r.enterprise.name for r in enterprise_rankings[:3])}")
        
        # Step 3: Capital Classification
        print("\n[3/7] Classifying capital tiers...")
        capital_classification = self.capital_classifier.classify_and_plan(
            ranked_enterprises=enterprise_rankings,
            land_analysis=land_analysis,
            available_capital=available_capital,
        )
        print(f"  Recommended tier: {capital_classification.recommended_tier}")
        print(f"  Reason: {capital_classification.recommendation_reason}")
        
        # Get selected tier for remaining analysis
        if preferred_tier and hasattr(capital_classification, f"tier_{preferred_tier.lower()}"):
            selected_tier = getattr(capital_classification, f"tier_{preferred_tier.lower()}")
        else:
            selected_tier = getattr(capital_classification, f"tier_{capital_classification.recommended_tier.lower()}")
        
        if not selected_tier:
            # Fallback to any available tier
            for t in ["b", "c", "a"]:
                selected_tier = getattr(capital_classification, f"tier_{t}")
                if selected_tier:
                    break
        
        # Build enterprise allocations for remaining analysis
        enterprise_allocations = {}
        if selected_tier:
            from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
            for eid, alloc in selected_tier.enterprise_mix.items():
                if eid in ALL_ENTERPRISES:
                    enterprise_allocations[eid] = (ALL_ENTERPRISES[eid], alloc)
        
        # Step 4: Profitability Projection
        print("\n[4/7] Projecting profitability...")
        profitability = None
        if enterprise_allocations:
            profitability = self.profitability_model.project_profitability(
                enterprise_allocations=enterprise_allocations,
                land_analysis=land_analysis,
                projection_years=5,
            )
            print(f"  3-year profit probability: {profitability.profit_probability_3yr}%")
            print(f"  Breakeven: {profitability.breakeven_months} months")
        
        # Step 5: Spatial Layout
        print("\n[5/7] Generating spatial layout...")
        infrastructure_requirements = selected_tier.required_infrastructure if selected_tier else []
        layout = self.layout_engine.generate_layout(
            enterprise_allocations=enterprise_allocations,
            land_analysis=land_analysis,
            infrastructure_requirements=infrastructure_requirements,
        )
        print(f"  Zones created: {len(layout.zones)}")
        print(f"  Utilized area: {layout.utilized_area_ha} ha")
        
        # Step 6: Risk Assessment
        print("\n[6/7] Assessing risks...")
        risk_assessment = self.risk_model.assess_risks(
            enterprise_mix=selected_tier.enterprise_mix if selected_tier else {},
            land_analysis=land_analysis,
            capital_tier=capital_classification.recommended_tier,
        )
        print(f"  Overall risk: {risk_assessment.overall_risk_level} ({risk_assessment.overall_risk_score}/100)")
        if risk_assessment.top_risks:
            print(f"  Top risk: {risk_assessment.top_risks[0].name}")
        
        # Step 7: Energy & Sustainability Plan
        print("\n[7/7] Planning energy & sustainability...")
        energy_plan = self.energy_planner.plan(
            enterprise_allocations=enterprise_allocations,
            land_analysis=land_analysis,
            layout=layout,
        )
        print(f"  Recommended model: {energy_plan.recommended_model}")
        print(f"  Sustainability score: {energy_plan.overall_sustainability_score}/100")
        
        # Format output
        print("\n[✓] Formatting output...")
        plan = self.formatter.format_full_plan(
            land_analysis=land_analysis,
            enterprise_rankings=enterprise_rankings,
            capital_classification=capital_classification,
            profitability_projection=profitability,
            spatial_layout=layout,
            risk_assessment=risk_assessment,
            energy_plan=energy_plan,
        )
        
        print(f"\n{'='*60}")
        print("Plan generation complete!")
        print(f"{'='*60}")
        
        return plan
    
    def generate_plan_from_request(self, request: PlanningRequest) -> Dict[str, Any]:
        """Generate plan from a PlanningRequest object."""
        return self.generate_plan(
            lat=request.lat,
            lon=request.lon,
            area_ha=request.area_ha,
            polygon=request.polygon,
            available_capital=request.available_capital,
            available_labor_days=request.available_labor_days,
            has_irrigation=request.has_irrigation,
            has_electricity=request.has_electricity,
            preferred_tier=request.preferred_tier,
            objective=request.objective,
            exclude_enterprises=request.exclude_enterprises,
            prefer_enterprises=request.prefer_enterprises,
        )
    
    def quick_analysis(
        self,
        lat: float,
        lon: float,
        area_ha: float,
    ) -> Dict[str, Any]:
        """
        Quick analysis without full plan generation.
        Returns land suitability and top 3 enterprises.
        """
        
        land = self.geo_analyzer.analyze(lat, lon, area_ha)
        rankings = self.enterprise_ranker.rank_enterprises(land)
        
        return {
            "land": {
                "aez_zone": land.aez_zone,
                "land_class": land.land_class,
                "rainfall_mm": land.annual_rainfall_mm,
                "constraints": land.constraints,
            },
            "top_enterprises": [
                {
                    "name": r.enterprise.name,
                    "category": r.enterprise.category.value,
                    "score": r.overall_rank_score,
                    "profit_per_ha": r.estimated_profit_per_ha,
                }
                for r in rankings[:3]
            ],
            "recommended_systems": land.recommended_systems[:5],
        }
    
    def save_plan(self, plan: Dict, filepath: Path) -> None:
        """Save plan to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(plan, f, indent=2, default=str)
        
        print(f"Plan saved to {filepath}")


# Convenience function for API
def plan_farm(
    lat: float,
    lon: float,
    area_ha: float,
    capital: Optional[float] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Quick farm planning function.
    
    Example:
        plan = plan_farm(-17.83, 31.05, 7.0, capital=30000)
    """
    planner = StrategicFarmPlanner()
    return planner.generate_plan(
        lat=lat,
        lon=lon,
        area_ha=area_ha,
        available_capital=capital,
        preferred_tier=tier,
    )


# CLI
if __name__ == "__main__":
    import sys
    
    # Default: Harare region, 10 ha
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else -17.83
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 31.05
    area = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    capital = float(sys.argv[4]) if len(sys.argv) > 4 else None
    
    planner = StrategicFarmPlanner()
    plan = planner.generate_plan(
        lat=lat,
        lon=lon,
        area_ha=area,
        available_capital=capital,
    )
    
    # Save plan
    output_path = Path(f"logs/strategic_plans/plan_{lat}_{lon}_{area}ha.json")
    planner.save_plan(plan, output_path)
    
    # Print summary
    summary = plan.get("summary", {})
    print(f"\n{'='*60}")
    print("PLAN SUMMARY")
    print(f"{'='*60}")
    print(f"Land Class: {summary.get('land_suitability', 'N/A')}")
    print(f"AEZ Zone: {summary.get('aez_zone', 'N/A')}")
    print(f"Recommended Tier: {summary.get('recommended_tier', 'N/A')}")
    print(f"Capital Required: ${summary.get('capital_required_usd', 0):,.0f}")
    print(f"Annual Profit: ${summary.get('expected_annual_profit_usd', 0):,.0f}")
    print(f"Profit Probability: {summary.get('profit_probability_pct', 0)}%")
    print(f"Breakeven: {summary.get('breakeven_months', 'N/A')} months")
    print(f"Risk Level: {summary.get('risk_level', 'N/A')}")
    print(f"Top Enterprises: {', '.join(summary.get('top_enterprises', []))}")
