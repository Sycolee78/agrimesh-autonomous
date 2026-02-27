"""
Multi-objective Pareto optimization for irrigation policy tuning.

Generates Pareto frontier showing trade-offs between:
- Water usage (minimize)
- Yield (maximize)
- Stress events (minimize)

Outputs visualization data for frontend display.
"""

from __future__ import annotations

import json
import itertools
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math

from src.sim.runner import run_simulation


@dataclass
class ParetoPoint:
    """A point in the objective space."""
    config: Dict
    water_used: float
    yield_tons_per_ha: float
    stress_events: int
    is_pareto_optimal: bool = False


def dominates(a: ParetoPoint, b: ParetoPoint) -> bool:
    """
    Check if point 'a' dominates point 'b'.
    
    A dominates B if A is at least as good in all objectives
    and strictly better in at least one.
    
    Objectives:
    - water_used: minimize (lower is better)
    - yield: maximize (higher is better)
    - stress_events: minimize (lower is better)
    """
    a_better_water = a.water_used <= b.water_used
    a_better_yield = a.yield_tons_per_ha >= b.yield_tons_per_ha
    a_better_stress = a.stress_events <= b.stress_events
    
    all_at_least_as_good = a_better_water and a_better_yield and a_better_stress
    
    strictly_better = (
        a.water_used < b.water_used or
        a.yield_tons_per_ha > b.yield_tons_per_ha or
        a.stress_events < b.stress_events
    )
    
    return all_at_least_as_good and strictly_better


def find_pareto_frontier(points: List[ParetoPoint]) -> List[ParetoPoint]:
    """
    Find Pareto-optimal points (non-dominated solutions).
    """
    pareto_points = []
    
    for candidate in points:
        is_dominated = False
        for other in points:
            if other is not candidate and dominates(other, candidate):
                is_dominated = True
                break
        
        if not is_dominated:
            candidate.is_pareto_optimal = True
            pareto_points.append(candidate)
    
    return pareto_points


def run_pareto_tuning(
    param_grid: Optional[Dict[str, List]] = None,
    days: int = 30,
    output_dir: Optional[Path] = None,
    max_trials: int = 200,
) -> Dict:
    """
    Run multi-objective tuning and find Pareto frontier.
    
    Args:
        param_grid: Parameter grid for tuning
        days: Simulation days per trial
        output_dir: Output directory for results
        max_trials: Maximum number of trials
    
    Returns:
        Dictionary with all points and Pareto frontier
    """
    
    if param_grid is None:
        param_grid = {
            "target_moisture": [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80],
            "stress_threshold": [0.30, 0.35, 0.40, 0.45],
            "liters_per_moisture_point": [300, 400, 500, 600],
            "min_daily_liters_per_plot": [20, 40, 60],
        }
    
    # Generate all combinations
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    if len(combinations) > max_trials:
        # Sample uniformly if too many combinations
        import random
        random.seed(42)
        combinations = random.sample(combinations, max_trials)
    
    print(f"Running {len(combinations)} parameter combinations...")
    
    all_points: List[ParetoPoint] = []
    
    for i, combo in enumerate(combinations):
        config = dict(zip(keys, combo))
        
        if (i + 1) % 20 == 0:
            print(f"  Trial {i + 1}/{len(combinations)}...")
        
        try:
            result = run_simulation(
                days=days,
                policy="agent",
                agent_config=config,
                verbose=False,
            )
            
            point = ParetoPoint(
                config=config,
                water_used=result["total_water_applied_liters"],
                yield_tons_per_ha=result["final_yield_estimate_tons_per_ha"],
                stress_events=result["crop_stress_events_total"],
            )
            all_points.append(point)
            
        except Exception as e:
            print(f"  Error with config {config}: {e}")
            continue
    
    # Find Pareto frontier
    pareto_frontier = find_pareto_frontier(all_points)
    
    print(f"\nFound {len(pareto_frontier)} Pareto-optimal solutions out of {len(all_points)} trials")
    
    # Prepare output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_trials": len(all_points),
            "pareto_optimal_count": len(pareto_frontier),
            "simulation_days": days,
            "param_grid": param_grid,
        },
        "all_points": [
            {
                "config": p.config,
                "water_used": round(p.water_used, 2),
                "yield_tons_per_ha": round(p.yield_tons_per_ha, 3),
                "stress_events": p.stress_events,
                "is_pareto_optimal": p.is_pareto_optimal,
            }
            for p in all_points
        ],
        "pareto_frontier": [
            {
                "config": p.config,
                "water_used": round(p.water_used, 2),
                "yield_tons_per_ha": round(p.yield_tons_per_ha, 3),
                "stress_events": p.stress_events,
            }
            for p in sorted(pareto_frontier, key=lambda x: x.water_used)
        ],
        "extreme_points": {
            "min_water": min(pareto_frontier, key=lambda x: x.water_used).config if pareto_frontier else None,
            "max_yield": max(pareto_frontier, key=lambda x: x.yield_tons_per_ha).config if pareto_frontier else None,
            "min_stress": min(pareto_frontier, key=lambda x: x.stress_events).config if pareto_frontier else None,
        },
    }
    
    # Save output
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "pareto_frontier.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {output_file}")
        
        # Generate visualization data (for Streamlit/frontend)
        viz_file = output_dir / "pareto_viz.json"
        viz_data = {
            "scatter_data": [
                {
                    "x": p.water_used,
                    "y": p.yield_tons_per_ha,
                    "size": max(5, 15 - p.stress_events),
                    "color": "pareto" if p.is_pareto_optimal else "dominated",
                    "label": f"Water: {p.water_used:.0f}L, Yield: {p.yield_tons_per_ha:.2f}t/ha",
                }
                for p in all_points
            ],
            "pareto_line": [
                {"x": p.water_used, "y": p.yield_tons_per_ha}
                for p in sorted(pareto_frontier, key=lambda x: x.water_used)
            ],
        }
        with open(viz_file, "w") as f:
            json.dump(viz_data, f, indent=2)
        print(f"Visualization data saved to {viz_file}")
    
    return output


def recommend_config(
    pareto_results: Dict,
    preference: str = "balanced",
) -> Dict:
    """
    Recommend a configuration based on user preference.
    
    Preferences:
    - "water_saver": Minimize water, accept some yield loss
    - "yield_maximizer": Maximize yield, accept more water
    - "balanced": Balance between water and yield
    - "stress_averse": Prioritize zero stress events
    """
    
    frontier = pareto_results["pareto_frontier"]
    if not frontier:
        return {}
    
    if preference == "water_saver":
        # First quartile by water usage
        sorted_by_water = sorted(frontier, key=lambda x: x["water_used"])
        return sorted_by_water[0]["config"]
    
    elif preference == "yield_maximizer":
        # Highest yield
        return max(frontier, key=lambda x: x["yield_tons_per_ha"])["config"]
    
    elif preference == "stress_averse":
        # Zero stress, then highest yield
        zero_stress = [p for p in frontier if p["stress_events"] == 0]
        if zero_stress:
            return max(zero_stress, key=lambda x: x["yield_tons_per_ha"])["config"]
        return min(frontier, key=lambda x: x["stress_events"])["config"]
    
    else:  # balanced
        # Normalize and find best combined score
        waters = [p["water_used"] for p in frontier]
        yields = [p["yield_tons_per_ha"] for p in frontier]
        
        water_min, water_max = min(waters), max(waters)
        yield_min, yield_max = min(yields), max(yields)
        
        best_score = -float("inf")
        best_config = None
        
        for p in frontier:
            # Normalize to 0-1 (higher is better)
            water_score = 1 - (p["water_used"] - water_min) / max(1, water_max - water_min)
            yield_score = (p["yield_tons_per_ha"] - yield_min) / max(0.1, yield_max - yield_min)
            
            # Equal weighting
            combined = water_score * 0.5 + yield_score * 0.5
            
            if combined > best_score:
                best_score = combined
                best_config = p["config"]
        
        return best_config


# CLI
if __name__ == "__main__":
    import sys
    
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    
    print(f"\n{'='*60}")
    print("AgriMesh Multi-Objective Pareto Optimization")
    print(f"Simulation days per trial: {days}")
    print(f"{'='*60}\n")
    
    results = run_pareto_tuning(
        days=days,
        output_dir=Path("logs/tuning"),
    )
    
    print(f"\n{'='*60}")
    print("PARETO FRONTIER SUMMARY")
    print(f"{'='*60}")
    
    print("\nExtreme configurations:")
    print(f"  Min water: {results['extreme_points']['min_water']}")
    print(f"  Max yield: {results['extreme_points']['max_yield']}")
    print(f"  Min stress: {results['extreme_points']['min_stress']}")
    
    print("\nRecommended configurations by preference:")
    for pref in ["water_saver", "yield_maximizer", "balanced", "stress_averse"]:
        config = recommend_config(results, preference=pref)
        print(f"  {pref}: {config}")
    
    print("\nPareto frontier points:")
    for i, p in enumerate(results["pareto_frontier"][:10]):
        print(f"  {i+1}. Water: {p['water_used']:>7.0f}L | Yield: {p['yield_tons_per_ha']:.2f} t/ha | Stress: {p['stress_events']}")
    
    if len(results["pareto_frontier"]) > 10:
        print(f"  ... and {len(results['pareto_frontier']) - 10} more")
