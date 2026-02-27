"""
Weather-driven simulation using real Open-Meteo data.

Runs the AgriMesh simulation with actual historical weather
from Zimbabwe locations instead of synthetic data.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.common.models import (
    ActionPlan,
    DecisionLog,
    FarmState,
    KPIState,
    OutcomeLog,
    PlotState,
    WaterSystemState,
    WeatherState,
)
from src.data.weather_client import OpenMeteoClient, DailyWeather, ZIMBABWE_LOCATIONS
from src.sim.environment import FarmSimulator
from src.sim.yield_model import CROP_PROFILES, get_growth_stage
from src.agents.irrigation.policies import GrowthStageAwarePolicy, BaselineFixedSchedulePolicy


def create_farm_state(
    weather: DailyWeather,
    plots_config: List[Dict],
    water_config: Dict,
    day_of_season: int = 1,
) -> FarmState:
    """Create farm state from weather data and config."""
    
    plots = []
    for cfg in plots_config:
        plots.append(PlotState(
            plot_id=cfg["plot_id"],
            area_m2=cfg.get("area_m2", 10000),  # 1 ha default
            crop_type=cfg.get("crop_type", "maize"),
            crop_stage=get_growth_stage(day_of_season, cfg.get("crop_type", "maize")).value,
            soil_moisture=cfg.get("initial_moisture", 0.55),
            soil_type=cfg.get("soil_type", "loam"),
            aez_zone=cfg.get("aez_zone", "II"),
            day_of_season=day_of_season,
            cumulative_stress_days=0,
        ))
    
    water_system = WaterSystemState(
        tank_level_liters=water_config.get("tank_capacity", 10000),
        daily_supply_limit_liters=water_config.get("daily_limit", 2000),
        pump_capacity_lpm=water_config.get("pump_lpm", 50),
    )
    
    weather_state = WeatherState(
        temperature_c=weather.temperature_mean_c,
        humidity_pct=weather.humidity_mean_pct,
        rainfall_mm=weather.precipitation_mm,
    )
    
    return FarmState(
        timestamp=datetime.combine(weather.date, datetime.min.time()),
        plots=plots,
        water_system=water_system,
        weather=weather_state,
        kpis=KPIState(),
    )


def run_weather_driven_simulation(
    location: str,
    season_start: date,
    season_days: int = 120,
    plots_config: Optional[List[Dict]] = None,
    water_config: Optional[Dict] = None,
    policy: str = "growth_stage",  # "growth_stage", "rule_based", "baseline"
    output_dir: Optional[Path] = None,
) -> Dict:
    """
    Run simulation with real weather data.
    
    Args:
        location: Zimbabwe location name (e.g., "harare")
        season_start: Start date of growing season
        season_days: Number of days to simulate
        plots_config: Plot configuration list
        water_config: Water system configuration
        policy: Irrigation policy to use
        output_dir: Directory for output logs
    
    Returns:
        Dictionary with simulation results
    """
    
    # Default configs
    if plots_config is None:
        plots_config = [
            {"plot_id": "maize-1", "crop_type": "maize", "area_m2": 20000, "aez_zone": "II"},
            {"plot_id": "maize-2", "crop_type": "maize", "area_m2": 15000, "aez_zone": "II"},
            {"plot_id": "groundnuts-1", "crop_type": "groundnuts", "area_m2": 10000, "aez_zone": "II"},
        ]
    
    if water_config is None:
        water_config = {
            "tank_capacity": 15000,
            "daily_limit": 3000,
            "pump_lpm": 60,
        }
    
    # Fetch weather data
    client = OpenMeteoClient()
    season_end = season_start + timedelta(days=season_days)
    
    print(f"Fetching weather data for {location}: {season_start} to {season_end}")
    weather_data = client.get_historical(location, season_start, season_end)
    
    if len(weather_data) < season_days:
        print(f"Warning: Only got {len(weather_data)} days of weather data")
    
    # Initialize policy
    if policy == "growth_stage":
        irrigation_policy = GrowthStageAwarePolicy()
    elif policy == "baseline":
        irrigation_policy = BaselineFixedSchedulePolicy(liters_per_plot=150)
    else:
        from src.agents.irrigation.policies import RuleBasedIrrigationPolicy
        irrigation_policy = RuleBasedIrrigationPolicy()
    
    # Initialize simulator
    simulator = FarmSimulator()
    
    # Create initial state
    state = create_farm_state(
        weather=weather_data[0],
        plots_config=plots_config,
        water_config=water_config,
        day_of_season=1,
    )
    
    # Run simulation
    results = []
    total_water = 0.0
    total_rainfall = 0.0
    
    for day_idx, weather in enumerate(weather_data):
        # Update weather in state
        state.weather = WeatherState(
            temperature_c=weather.temperature_mean_c,
            humidity_pct=weather.humidity_mean_pct,
            rainfall_mm=weather.precipitation_mm,
        )
        
        # Refill tank (simulate daily water supply + rainfall collection)
        tank_refill = min(
            water_config.get("daily_limit", 3000) * 0.3,  # 30% of limit as base
            water_config.get("tank_capacity", 15000) - state.water_system.tank_level_liters,
        )
        # Add rainwater harvesting (10% of rainfall * total area)
        total_area_m2 = sum(p.area_m2 for p in state.plots)
        rainwater = weather.precipitation_mm * total_area_m2 * 0.001 * 0.1  # 10% capture
        state.water_system.tank_level_liters = min(
            water_config.get("tank_capacity", 15000),
            state.water_system.tank_level_liters + tank_refill + rainwater,
        )
        
        # Get irrigation decision
        cycle_id = f"day-{day_idx + 1}-{weather.date.isoformat()}"
        plan, rationale = irrigation_policy.decide(state, cycle_id)
        
        # Apply irrigation
        plan_by_plot = plan.irrigation_by_plot_liters
        state, decision_log, outcome_log = simulator.step(
            state=state,
            plan_by_plot=plan_by_plot,
            cycle_id=cycle_id,
            agent_id=irrigation_policy.policy_version,
            rationale=rationale,
            policy_version=irrigation_policy.policy_version,
        )
        
        day_water = sum(plan_by_plot.values())
        total_water += day_water
        total_rainfall += weather.precipitation_mm
        
        results.append({
            "day": day_idx + 1,
            "date": weather.date.isoformat(),
            "weather": {
                "temp_c": weather.temperature_mean_c,
                "rain_mm": weather.precipitation_mm,
                "humidity_pct": weather.humidity_mean_pct,
                "et0_mm": weather.evapotranspiration_mm,
            },
            "irrigation_liters": round(day_water, 2),
            "tank_level_liters": round(state.water_system.tank_level_liters, 2),
            "avg_moisture": round(sum(p.soil_moisture for p in state.plots) / len(state.plots), 4),
            "stress_events": state.kpis.crop_stress_events,
            "yield_estimate": state.kpis.yield_estimate_tons_per_ha,
            "growth_stages": {p.plot_id: p.crop_stage for p in state.plots},
        })
    
    # Save results
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"weather_sim_{location}_{season_start.isoformat()}_{policy}.json"
        with open(output_file, "w") as f:
            json.dump({
                "config": {
                    "location": location,
                    "season_start": season_start.isoformat(),
                    "season_days": season_days,
                    "policy": policy,
                    "plots": plots_config,
                    "water": water_config,
                },
                "summary": {
                    "total_days": len(results),
                    "total_irrigation_liters": round(total_water, 2),
                    "total_rainfall_mm": round(total_rainfall, 2),
                    "avg_daily_irrigation": round(total_water / len(results), 2),
                    "final_yield_estimate": results[-1]["yield_estimate"] if results else 0,
                    "total_stress_events": results[-1]["stress_events"] if results else 0,
                },
                "daily": results,
            }, f, indent=2)
        
        print(f"Results saved to {output_file}")
    
    return {
        "location": location,
        "season_start": season_start.isoformat(),
        "policy": policy,
        "days_simulated": len(results),
        "total_irrigation_liters": round(total_water, 2),
        "total_rainfall_mm": round(total_rainfall, 2),
        "final_yield_tons_per_ha": results[-1]["yield_estimate"] if results else 0,
        "total_stress_events": results[-1]["stress_events"] if results else 0,
        "daily_results": results,
    }


def compare_policies_weather_driven(
    location: str,
    season_start: date,
    season_days: int = 120,
) -> Dict:
    """
    Compare all policies using real weather data.
    """
    
    policies = ["baseline", "growth_stage"]
    results = {}
    
    for policy in policies:
        print(f"\n{'='*50}")
        print(f"Running {policy} policy...")
        print(f"{'='*50}")
        
        result = run_weather_driven_simulation(
            location=location,
            season_start=season_start,
            season_days=season_days,
            policy=policy,
            output_dir=Path("logs/weather_sim"),
        )
        
        results[policy] = {
            "total_water_liters": result["total_irrigation_liters"],
            "rainfall_mm": result["total_rainfall_mm"],
            "yield_tons_per_ha": result["final_yield_tons_per_ha"],
            "stress_events": result["total_stress_events"],
        }
    
    # Compare
    baseline = results["baseline"]
    agent = results["growth_stage"]
    
    comparison = {
        "water_saving_liters": baseline["total_water_liters"] - agent["total_water_liters"],
        "water_saving_pct": round((baseline["total_water_liters"] - agent["total_water_liters"]) / max(1, baseline["total_water_liters"]) * 100, 1),
        "yield_delta_tons_per_ha": round(agent["yield_tons_per_ha"] - baseline["yield_tons_per_ha"], 3),
        "stress_delta": agent["stress_events"] - baseline["stress_events"],
    }
    
    return {
        "location": location,
        "season": f"{season_start} + {season_days} days",
        "rainfall_total_mm": baseline["rainfall_mm"],
        "results": results,
        "comparison": comparison,
    }


# CLI
if __name__ == "__main__":
    import sys
    
    location = sys.argv[1] if len(sys.argv) > 1 else "harare"
    
    # Use 2024/25 season (Nov 2024 - Feb 2025)
    # Note: Archive data may have ~5 day lag, so use slightly older dates
    season_start = date(2024, 11, 1)
    season_days = 120  # Full growing season
    
    print(f"\n{'='*60}")
    print(f"AgriMesh Weather-Driven Simulation")
    print(f"Location: {location}")
    print(f"Season: {season_start} to {season_start + timedelta(days=season_days)}")
    print(f"{'='*60}")
    
    comparison = compare_policies_weather_driven(
        location=location,
        season_start=season_start,
        season_days=season_days,
    )
    
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}")
    print(f"Location: {comparison['location']}")
    print(f"Season rainfall: {comparison['rainfall_total_mm']:.1f} mm")
    print()
    print("Policy Performance:")
    for policy, data in comparison["results"].items():
        print(f"  {policy}:")
        print(f"    Water used: {data['total_water_liters']:.0f} L")
        print(f"    Yield: {data['yield_tons_per_ha']:.2f} t/ha")
        print(f"    Stress events: {data['stress_events']}")
    print()
    print("Agent vs Baseline:")
    print(f"  Water savings: {comparison['comparison']['water_saving_liters']:.0f} L ({comparison['comparison']['water_saving_pct']}%)")
    print(f"  Yield delta: {comparison['comparison']['yield_delta_tons_per_ha']:+.2f} t/ha")
    print(f"  Stress delta: {comparison['comparison']['stress_delta']}")
