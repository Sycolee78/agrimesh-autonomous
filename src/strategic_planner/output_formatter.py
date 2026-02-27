"""
Output Formatter

Formats strategic plan outputs for API and frontend consumption.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


class StrategicPlanFormatter:
    """
    Formats strategic plan outputs.
    """
    
    def format_full_plan(
        self,
        land_analysis,
        enterprise_rankings: List,
        capital_classification,
        profitability_projection,
        spatial_layout,
        risk_assessment,
        energy_plan,
        agent_deployment: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Format complete strategic plan for API response.
        """
        
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0",
                "plan_type": "strategic_farm_plan",
            },
            
            "land_analysis": self._format_land_analysis(land_analysis),
            
            "enterprise_rankings": self._format_rankings(enterprise_rankings[:10]),
            
            "capital_classes": self._format_capital_classes(capital_classification),
            
            "recommended_layout": self._format_layout(spatial_layout),
            
            "profit_projection": self._format_profitability(profitability_projection),
            
            "risk_assessment": self._format_risk(risk_assessment),
            
            "energy_plan": self._format_energy(energy_plan),
            
            "agent_deployment": agent_deployment or self._default_agent_deployment(),
            
            "summary": self._generate_summary(
                land_analysis, capital_classification, profitability_projection
            ),
        }
    
    def _format_land_analysis(self, land) -> Dict:
        """Format land analysis."""
        return {
            "coordinates": {"lat": land.lat, "lon": land.lon},
            "area_ha": land.area_ha,
            "aez_zone": land.aez_zone,
            "aez_subzone": land.aez_subzone,
            "climate": {
                "annual_rainfall_mm": land.annual_rainfall_mm,
                "rainfall_reliability": land.rainfall_reliability,
                "temperature_range": land.temperature_range,
                "growing_days": land.growing_days,
                "frost_risk": land.frost_risk,
            },
            "soil": {
                "type": land.soil_type,
                "fertility": land.soil_fertility,
                "depth_cm": land.soil_depth_cm,
                "drainage": land.drainage,
            },
            "terrain": {
                "slope_percent": land.slope_percent,
                "classification": land.terrain_classification,
                "erosion_risk": land.erosion_risk,
            },
            "water": {
                "source": land.water_source,
                "reliability": land.water_reliability,
                "borehole_feasibility": land.borehole_feasibility,
                "flood_risk": land.flood_risk,
            },
            "access": {
                "market_distance_km": land.market_distance_km,
                "road_quality": land.road_quality,
                "electricity_access": land.electricity_access,
            },
            "classification": {
                "land_class": land.land_class,
                "recommended_systems": land.recommended_systems,
                "constraints": land.constraints,
            },
        }
    
    def _format_rankings(self, rankings: List) -> List[Dict]:
        """Format enterprise rankings."""
        formatted = []
        for i, r in enumerate(rankings):
            formatted.append({
                "rank": i + 1,
                "enterprise_id": r.enterprise.id,
                "name": r.enterprise.name,
                "category": r.enterprise.category.value,
                "scores": {
                    "suitability": r.suitability_score,
                    "profit_potential": r.profit_potential_score,
                    "risk": r.risk_score,
                    "overall": r.overall_rank_score,
                },
                "economics": {
                    "estimated_profit_per_ha": r.estimated_profit_per_ha,
                    "capital_required": r.capital_required,
                },
                "constraints": r.constraints,
                "recommendations": r.recommendations,
            })
        return formatted
    
    def _format_capital_classes(self, classification) -> Dict:
        """Format capital tier classification."""
        
        def format_tier(tier):
            if not tier:
                return None
            return {
                "tier": tier.tier,
                "name": tier.tier_name,
                "description": tier.tier_description,
                "enterprise_mix": tier.enterprise_mix,
                "enterprise_details": tier.enterprise_details,
                "capital": {
                    "total_required": tier.total_capital_required,
                    "startup": tier.startup_capital,
                    "working": tier.working_capital,
                    "breakdown": tier.capital_breakdown,
                },
                "returns": {
                    "annual_revenue": tier.expected_annual_revenue,
                    "annual_profit": tier.expected_annual_profit,
                    "roi_3yr_pct": tier.expected_roi_3yr,
                    "profit_probability_3yr_pct": tier.profit_probability_3yr,
                },
                "risk": {
                    "level": tier.risk_level,
                    "factors": tier.risk_factors,
                },
                "timing": {
                    "first_revenue_months": tier.time_to_first_revenue_months,
                    "breakeven_months": tier.breakeven_months,
                },
                "infrastructure": {
                    "required": tier.required_infrastructure,
                    "optional": tier.optional_infrastructure,
                },
            }
        
        return {
            "land_area_ha": classification.land_area_ha,
            "A": format_tier(classification.tier_a),
            "B": format_tier(classification.tier_b),
            "C": format_tier(classification.tier_c),
            "recommended_tier": classification.recommended_tier,
            "recommendation_reason": classification.recommendation_reason,
        }
    
    def _format_layout(self, layout) -> Dict:
        """Format spatial layout."""
        
        zones = []
        for z in layout.zones:
            zones.append({
                "zone_id": z.zone_id,
                "type": z.zone_type.value,
                "name": z.name,
                "area_ha": z.area_ha,
                "position": {
                    "x": z.x,
                    "y": z.y,
                    "width": z.width,
                    "height": z.height,
                },
                "polygon": z.polygon,
                "enterprise_id": z.enterprise_id,
                "notes": z.notes,
                "color": z.color,
            })
        
        return {
            "total_area_ha": layout.total_area_ha,
            "utilized_area_ha": layout.utilized_area_ha,
            "zones": zones,
            "networks": {
                "water": layout.water_network,
                "roads": layout.road_network,
                "power": layout.power_network,
            },
            "scores": {
                "water_efficiency": layout.water_efficiency_score,
                "biosecurity": layout.biosecurity_score,
                "labor_efficiency": layout.labor_efficiency_score,
            },
            "orientation": layout.orientation,
            "slope_direction": layout.slope_direction,
            "design_notes": layout.design_notes,
        }
    
    def _format_profitability(self, projection) -> Dict:
        """Format profitability projection."""
        
        if projection is None:
            return {
                "enterprise_mix": {},
                "capital": {"startup": 0, "working_capital_year1": 0, "total_required": 0},
                "scenarios": {"pessimistic": [], "expected": [], "optimistic": []},
                "key_metrics": {"breakeven_months": 0, "irr_3yr_pct": 0, "npv_3yr_usd": 0, "payback_period_months": 0},
                "probability": {"profit_probability_3yr_pct": 0, "profit_probability_5yr_pct": 0},
                "risk_metrics": {"max_drawdown_usd": 0, "volatility_pct": 0, "sharpe_ratio": 0},
                "sensitivity": {},
            }
        
        def format_scenarios(scenarios):
            return [
                {
                    "year": s.year,
                    "revenue": s.revenue,
                    "operating_costs": s.operating_costs,
                    "gross_profit": s.gross_profit,
                    "cumulative_profit": s.cumulative_profit,
                }
                for s in scenarios
            ]
        
        return {
            "enterprise_mix": projection.enterprise_mix,
            "capital": {
                "startup": projection.startup_capital,
                "working_capital_year1": projection.working_capital_year1,
                "total_required": projection.total_capital_required,
            },
            "scenarios": {
                "pessimistic": format_scenarios(projection.pessimistic),
                "expected": format_scenarios(projection.expected),
                "optimistic": format_scenarios(projection.optimistic),
            },
            "key_metrics": {
                "breakeven_months": projection.breakeven_months,
                "irr_3yr_pct": projection.irr_3yr,
                "npv_3yr_usd": projection.npv_3yr,
                "payback_period_months": projection.payback_period_months,
            },
            "probability": {
                "profit_probability_3yr_pct": projection.profit_probability_3yr,
                "profit_probability_5yr_pct": projection.profit_probability_5yr,
            },
            "risk_metrics": {
                "max_drawdown_usd": projection.max_drawdown,
                "volatility_pct": projection.volatility,
                "sharpe_ratio": projection.sharpe_ratio,
            },
            "sensitivity": projection.sensitivity,
        }
    
    def _format_risk(self, risk) -> Dict:
        """Format risk assessment."""
        
        factors = []
        for f in risk.risk_factors:
            factors.append({
                "id": f.id,
                "name": f.name,
                "category": f.category.value,
                "severity": f.severity,
                "probability": f.probability,
                "impact": f.impact_description,
                "mitigations": f.mitigation_strategies,
            })
        
        return {
            "overall": {
                "level": risk.overall_risk_level,
                "score": risk.overall_risk_score,
            },
            "category_scores": {
                "climate": risk.climate_risk_score,
                "market": risk.market_risk_score,
                "operational": risk.operational_risk_score,
                "financial": risk.financial_risk_score,
            },
            "risk_factors": factors,
            "top_risks": [
                {"name": r.name, "severity": r.severity, "probability": r.probability}
                for r in risk.top_risks
            ],
            "scenario_impacts": {
                "drought_impact_pct": risk.drought_impact_pct,
                "price_crash_impact_pct": risk.price_crash_impact_pct,
                "disease_outbreak_impact_pct": risk.disease_outbreak_impact_pct,
            },
            "mitigations": risk.recommended_mitigations,
            "insurance_recommendations": risk.insurance_recommendations,
        }
    
    def _format_energy(self, energy) -> Dict:
        """Format energy and sustainability plan."""
        
        solar = None
        if energy.solar_system:
            s = energy.solar_system
            solar = {
                "capacity_kw": s.capacity_kw,
                "panel_count": s.panel_count,
                "battery_kwh": s.battery_capacity_kwh,
                "daily_generation_kwh": s.estimated_daily_generation_kwh,
                "cost_usd": s.estimated_cost_usd,
                "payback_years": s.payback_years,
            }
        
        water = {
            "borehole_depth_m": energy.water_system.borehole_depth_m,
            "borehole_yield_lph": energy.water_system.borehole_yield_lph,
            "pump_type": energy.water_system.pump_type,
            "pump_power_kw": energy.water_system.pump_power_kw,
            "tank_capacity_liters": energy.water_system.tank_capacity_liters,
            "rainwater_harvest_liters_year": energy.water_system.rainwater_harvest_liters_year,
            "cost_usd": energy.water_system.estimated_cost_usd,
        }
        
        biogas = None
        if energy.biogas_system:
            b = energy.biogas_system
            biogas = {
                "digester_volume_m3": b.digester_volume_m3,
                "daily_gas_m3": b.daily_gas_production_m3,
                "cooking_hours": b.daily_cooking_hours,
                "electricity_kwh": b.daily_electricity_kwh,
                "manure_input_kg": b.manure_input_kg_day,
                "cost_usd": b.estimated_cost_usd,
            }
        
        loops = [
            {
                "name": l.name,
                "input": l.input_source,
                "output": l.output_use,
                "annual_value_usd": l.annual_value_usd,
                "notes": l.notes,
            }
            for l in energy.resource_loops
        ]
        
        return {
            "power": {
                "solar_system": solar,
                "grid_connection": energy.grid_connection,
                "backup_generator": energy.backup_generator,
                "total_demand_kw": energy.total_power_demand_kw,
            },
            "water": {
                "system": water,
                "irrigation_type": energy.irrigation_type,
                "self_sufficiency_pct": energy.water_self_sufficiency_pct,
            },
            "biogas": biogas,
            "resource_loops": loops,
            "scores": {
                "energy_self_sufficiency": energy.energy_self_sufficiency_score,
                "water_self_sufficiency": energy.water_self_sufficiency_score,
                "circularity": energy.circularity_score,
                "overall_sustainability": energy.overall_sustainability_score,
            },
            "economics": {
                "total_infrastructure_cost_usd": energy.total_infrastructure_cost_usd,
                "annual_savings_usd": energy.annual_savings_usd,
                "carbon_offset_tons_year": energy.carbon_offset_tons_year,
            },
            "recommended_model": energy.recommended_model,
            "implementation_phases": energy.implementation_phases,
        }
    
    def _default_agent_deployment(self) -> Dict:
        """Generate default agent deployment plan."""
        return {
            "agents": [
                {
                    "agent_id": "irrigation_agent",
                    "name": "Irrigation Agent",
                    "zones": ["crop_fields"],
                    "schedule": "daily",
                },
                {
                    "agent_id": "livestock_agent",
                    "name": "Livestock Operations Agent",
                    "zones": ["livestock_paddocks"],
                    "schedule": "twice_daily",
                },
                {
                    "agent_id": "weather_agent",
                    "name": "Weather & Water Agent",
                    "zones": ["all"],
                    "schedule": "hourly",
                },
                {
                    "agent_id": "maintenance_agent",
                    "name": "Maintenance Agent",
                    "zones": ["infrastructure"],
                    "schedule": "weekly",
                },
            ],
            "orchestrator": {
                "name": "Farm Management Orchestrator",
                "decision_frequency": "daily",
                "human_approval_required": ["high_risk_actions", "large_expenditures"],
            },
        }
    
    def _generate_summary(self, land, capital_class, profitability) -> Dict:
        """Generate executive summary."""
        
        rec_tier = capital_class.recommended_tier
        tier = getattr(capital_class, f"tier_{rec_tier.lower()}")
        
        return {
            "land_suitability": land.land_class,
            "aez_zone": land.aez_zone,
            "recommended_tier": rec_tier,
            "capital_required_usd": tier.total_capital_required if tier else 0,
            "expected_annual_profit_usd": tier.expected_annual_profit if tier else 0,
            "profit_probability_pct": tier.profit_probability_3yr if tier else 0,
            "breakeven_months": tier.breakeven_months if tier else 0,
            "risk_level": tier.risk_level if tier else "unknown",
            "top_enterprises": list(tier.enterprise_mix.keys())[:3] if tier else [],
            "key_constraints": land.constraints[:3],
        }
    
    def to_json(self, plan: Dict, indent: int = 2) -> str:
        """Convert plan to JSON string."""
        return json.dumps(plan, indent=indent, default=str)
