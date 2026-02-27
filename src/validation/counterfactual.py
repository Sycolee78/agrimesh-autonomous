"""
Counterfactual analysis: What if the agent had controlled irrigation?

Replays pilot farm data through the AgriMesh agent and compares outcomes
to what actually happened under human control.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.common.models import (
    FarmState,
    KPIState,
    PlotState,
    WaterSystemState,
    WeatherState,
)
from src.sim.environment import FarmSimulator
from src.sim.yield_model import CROP_PROFILES, get_growth_stage
from src.agents.irrigation.policies import GrowthStageAwarePolicy
from src.validation.pilot_data import PilotFarmData, load_pilot_data


def run_counterfactual_analysis(
    pilot_data: PilotFarmData,
    output_dir: Optional[Path] = None,
) -> Dict:
    """
    Run counterfactual analysis on pilot data.
    
    Replays the exact weather conditions from the pilot dataset,
    but substitutes the AgriMesh agent for irrigation decisions.
    
    Args:
        pilot_data: Loaded pilot farm dataset
        output_dir: Where to save results
    
    Returns:
        Comparison results
    """
    
    print(f"Running counterfactual analysis on: {pilot_data.farm_id}")
    print(f"Location: {pilot_data.location}, Crop: {pilot_data.crop}, Area: {pilot_data.area_ha} ha")
    
    # Initialize agent
    agent = GrowthStageAwarePolicy()
    simulator = FarmSimulator()
    
    # Water system config (realistic for Zimbabwe smallholder)
    water_config = {
        "tank_capacity": 10000 * pilot_data.area_ha,  # 10,000L per ha
        "daily_limit": 2000 * pilot_data.area_ha,
        "pump_lpm": 40,
    }
    
    # Create initial state
    initial_moisture = 0.45
    plot = PlotState(
        plot_id=f"{pilot_data.crop}-main",
        area_m2=pilot_data.area_ha * 10000,
        crop_type=pilot_data.crop,
        crop_stage="germination",
        soil_moisture=initial_moisture,
        aez_zone=pilot_data.aez_zone,
        day_of_season=1,
        cumulative_stress_days=0,
    )
    
    water_system = WaterSystemState(
        tank_level_liters=water_config["tank_capacity"],
        daily_supply_limit_liters=water_config["daily_limit"],
        pump_capacity_lpm=water_config["pump_lpm"],
    )
    
    # Track both scenarios
    human_results = []
    agent_results = []
    
    # Agent state tracking
    agent_state = FarmState(
        timestamp=datetime.fromisoformat(pilot_data.planting_date),
        plots=[plot],
        water_system=water_system,
        weather=WeatherState(temperature_c=25, humidity_pct=60, rainfall_mm=0),
        kpis=KPIState(),
    )
    
    # Replay each day
    for day_idx, record in enumerate(pilot_data.daily_records):
        weather = record.weather
        
        # Update weather in agent state
        agent_state.weather = WeatherState(
            temperature_c=(weather["temp_max_c"] + weather["temp_min_c"]) / 2,
            humidity_pct=weather.get("humidity_pct", 60),
            rainfall_mm=weather.get("rain_mm", 0),
        )
        
        # Tank refill (simplified)
        refill = water_config["daily_limit"] * 0.3
        agent_state.water_system.tank_level_liters = min(
            water_config["tank_capacity"],
            agent_state.water_system.tank_level_liters + refill
        )
        
        # HUMAN path: Use actual irrigation from pilot data
        human_irrigation = record.irrigation_applied_liters
        
        # AGENT path: Get agent decision
        cycle_id = f"counterfactual-day-{day_idx + 1}"
        plan, rationale = agent.decide(agent_state, cycle_id)
        agent_irrigation = sum(plan.irrigation_by_plot_liters.values())
        
        # Apply agent irrigation to agent state
        agent_state, _, outcome = simulator.step(
            state=agent_state,
            plan_by_plot=plan.irrigation_by_plot_liters,
            cycle_id=cycle_id,
            agent_id=agent.policy_version,
            rationale=rationale,
            policy_version=agent.policy_version,
        )
        
        # Record human results (approximate state tracking)
        human_results.append({
            "day": day_idx + 1,
            "date": record.date,
            "irrigation_liters": human_irrigation,
            "soil_moisture": record.soil_moisture_measured,  # May be None
            "crop_stage": record.crop_stage,
        })
        
        # Record agent results
        agent_results.append({
            "day": day_idx + 1,
            "date": record.date,
            "irrigation_liters": round(agent_irrigation, 2),
            "soil_moisture": round(agent_state.plots[0].soil_moisture, 4),
            "crop_stage": agent_state.plots[0].crop_stage,
            "yield_estimate": agent_state.kpis.yield_estimate_tons_per_ha,
            "stress_events": agent_state.kpis.crop_stress_events,
        })
    
    # Calculate totals
    human_total_water = sum(r["irrigation_liters"] for r in human_results)
    agent_total_water = sum(r["irrigation_liters"] for r in agent_results)
    
    human_yield = pilot_data.final_yield_tons or 0
    human_yield_per_ha = human_yield / pilot_data.area_ha if pilot_data.area_ha else 0
    
    agent_yield_per_ha = agent_results[-1]["yield_estimate"] if agent_results else 0
    agent_yield = agent_yield_per_ha * pilot_data.area_ha
    
    # Build comparison
    comparison = {
        "pilot_farm": {
            "farm_id": pilot_data.farm_id,
            "location": pilot_data.location,
            "crop": pilot_data.crop,
            "area_ha": pilot_data.area_ha,
            "season": pilot_data.season,
        },
        "human_control": {
            "total_irrigation_liters": round(human_total_water, 1),
            "irrigation_per_ha": round(human_total_water / pilot_data.area_ha, 1),
            "final_yield_tons": human_yield,
            "yield_per_ha": round(human_yield_per_ha, 2),
            "irrigation_style": pilot_data.metadata.get("irrigation_style", "unknown"),
        },
        "agent_control": {
            "total_irrigation_liters": round(agent_total_water, 1),
            "irrigation_per_ha": round(agent_total_water / pilot_data.area_ha, 1),
            "final_yield_tons": round(agent_yield, 2),
            "yield_per_ha": round(agent_yield_per_ha, 2),
            "stress_events": agent_results[-1]["stress_events"] if agent_results else 0,
        },
        "delta": {
            "water_saved_liters": round(human_total_water - agent_total_water, 1),
            "water_saved_pct": round((human_total_water - agent_total_water) / max(1, human_total_water) * 100, 1),
            "yield_change_tons": round(agent_yield - human_yield, 2),
            "yield_change_pct": round((agent_yield - human_yield) / max(0.1, human_yield) * 100, 1),
        },
        "daily_human": human_results,
        "daily_agent": agent_results,
    }
    
    # Save results
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"counterfactual_{pilot_data.farm_id}.json"
        with open(output_file, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"Results saved to {output_file}")
    
    return comparison


def print_counterfactual_report(comparison: Dict):
    """Print a human-readable counterfactual report."""
    
    farm = comparison["pilot_farm"]
    human = comparison["human_control"]
    agent = comparison["agent_control"]
    delta = comparison["delta"]
    
    print(f"\n{'='*70}")
    print("COUNTERFACTUAL ANALYSIS REPORT")
    print(f"{'='*70}")
    
    print(f"\nFarm: {farm['farm_id']}")
    print(f"Location: {farm['location']} | Crop: {farm['crop']} | Area: {farm['area_ha']} ha")
    print(f"Season: {farm['season']}")
    
    print(f"\n{'-'*70}")
    print("COMPARISON: Human Control vs AgriMesh Agent")
    print(f"{'-'*70}")
    
    print(f"\n{'Metric':<30} {'Human':<20} {'Agent':<20}")
    print(f"{'-'*70}")
    print(f"{'Total irrigation (L)':<30} {human['total_irrigation_liters']:>15,.0f} {agent['total_irrigation_liters']:>15,.0f}")
    print(f"{'Irrigation per ha (L/ha)':<30} {human['irrigation_per_ha']:>15,.0f} {agent['irrigation_per_ha']:>15,.0f}")
    print(f"{'Final yield (tons)':<30} {human['final_yield_tons']:>15.2f} {agent['final_yield_tons']:>15.2f}")
    print(f"{'Yield per ha (t/ha)':<30} {human['yield_per_ha']:>15.2f} {agent['yield_per_ha']:>15.2f}")
    
    print(f"\n{'-'*70}")
    print("IMPACT SUMMARY")
    print(f"{'-'*70}")
    
    water_emoji = "💧" if delta["water_saved_pct"] > 0 else "⚠️"
    yield_emoji = "🌾" if delta["yield_change_pct"] > 0 else "⚠️"
    
    print(f"\n{water_emoji} Water: {delta['water_saved_liters']:+,.0f} L ({delta['water_saved_pct']:+.1f}%)")
    print(f"{yield_emoji} Yield: {delta['yield_change_tons']:+.2f} tons ({delta['yield_change_pct']:+.1f}%)")
    
    if delta["water_saved_pct"] > 20 and delta["yield_change_pct"] >= 0:
        print("\n✅ RECOMMENDATION: AgriMesh agent would significantly improve water efficiency")
        print("   without sacrificing yield. Strong candidate for adoption.")
    elif delta["water_saved_pct"] > 0 and delta["yield_change_pct"] > 0:
        print("\n✅ RECOMMENDATION: AgriMesh agent would improve both water use AND yield.")
        print("   Ideal candidate for adoption.")
    elif delta["yield_change_pct"] < -10:
        print("\n⚠️ CAUTION: Agent shows yield reduction. Review policy parameters.")
    else:
        print("\n📊 NEUTRAL: Results are comparable. Consider other factors.")


def run_multi_scenario_validation(
    locations: List[str] = None,
    styles: List[str] = None,
    output_dir: Optional[Path] = None,
) -> Dict:
    """
    Run counterfactual analysis across multiple scenarios.
    """
    
    locations = locations or ["harare", "bulawayo", "mutare", "masvingo"]
    styles = styles or ["traditional", "efficient", "erratic"]
    
    from src.validation.pilot_data import generate_pilot_dataset
    
    all_results = []
    
    for location in locations:
        for style in styles:
            print(f"\n{'='*50}")
            print(f"Scenario: {location} / {style}")
            print(f"{'='*50}")
            
            try:
                # Generate pilot data
                pilot = generate_pilot_dataset(
                    location=location,
                    season_year=2024,
                    crop="maize",
                    area_ha=5.0,
                    irrigation_style=style,
                    output_dir=Path("data/pilots") if output_dir else None,
                )
                
                # Run counterfactual
                comparison = run_counterfactual_analysis(
                    pilot_data=pilot,
                    output_dir=output_dir,
                )
                
                all_results.append({
                    "location": location,
                    "style": style,
                    "human_water": comparison["human_control"]["total_irrigation_liters"],
                    "agent_water": comparison["agent_control"]["total_irrigation_liters"],
                    "human_yield": comparison["human_control"]["yield_per_ha"],
                    "agent_yield": comparison["agent_control"]["yield_per_ha"],
                    "water_saved_pct": comparison["delta"]["water_saved_pct"],
                    "yield_change_pct": comparison["delta"]["yield_change_pct"],
                })
                
            except Exception as e:
                print(f"Error in {location}/{style}: {e}")
                continue
    
    # Summary statistics
    if all_results:
        avg_water_saved = sum(r["water_saved_pct"] for r in all_results) / len(all_results)
        avg_yield_change = sum(r["yield_change_pct"] for r in all_results) / len(all_results)
        
        print(f"\n{'='*70}")
        print("MULTI-SCENARIO SUMMARY")
        print(f"{'='*70}")
        print(f"\nScenarios analyzed: {len(all_results)}")
        print(f"Average water savings: {avg_water_saved:+.1f}%")
        print(f"Average yield change: {avg_yield_change:+.1f}%")
        
        # Best/worst scenarios
        best_water = max(all_results, key=lambda x: x["water_saved_pct"])
        best_yield = max(all_results, key=lambda x: x["yield_change_pct"])
        
        print(f"\nBest water savings: {best_water['location']}/{best_water['style']} ({best_water['water_saved_pct']:+.1f}%)")
        print(f"Best yield improvement: {best_yield['location']}/{best_yield['style']} ({best_yield['yield_change_pct']:+.1f}%)")
    
    return {"scenarios": all_results}


# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        # Run multi-scenario validation
        results = run_multi_scenario_validation(
            output_dir=Path("logs/validation"),
        )
    else:
        # Single scenario
        from src.validation.pilot_data import generate_pilot_dataset
        
        location = sys.argv[1] if len(sys.argv) > 1 else "harare"
        style = sys.argv[2] if len(sys.argv) > 2 else "traditional"
        
        print(f"Generating pilot data for {location} ({style} irrigation)...")
        
        pilot = generate_pilot_dataset(
            location=location,
            season_year=2024,
            crop="maize",
            area_ha=5.0,
            irrigation_style=style,
            output_dir=Path("data/pilots"),
        )
        
        comparison = run_counterfactual_analysis(
            pilot_data=pilot,
            output_dir=Path("logs/validation"),
        )
        
        print_counterfactual_report(comparison)
