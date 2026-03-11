#!/usr/bin/env python3
"""
Demo script for AgriMesh ML Farm Planner

Usage:
    python scripts/demo_ml_planner.py
    python scripts/demo_ml_planner.py --lat -17.83 --lon 31.05 --area 10
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.planner import MLFarmPlanner


def main():
    parser = argparse.ArgumentParser(description="AgriMesh ML Farm Planner Demo")
    parser.add_argument("--lat", type=float, default=-17.8292, help="Latitude")
    parser.add_argument("--lon", type=float, default=31.0522, help="Longitude")
    parser.add_argument("--area", type=float, default=10.0, help="Farm area in hectares")
    parser.add_argument("--capital", type=float, default=None, help="Available capital (USD)")
    parser.add_argument("--labor", type=int, default=1000, help="Available labor days/year")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--compare", action="store_true", help="Compare multiple locations")
    args = parser.parse_args()
    
    print("🤖 AgriMesh ML Farm Planner")
    print("=" * 50)
    
    # Initialize planner
    print("\nInitializing ML planner...")
    planner = MLFarmPlanner(use_weather=True)
    
    if args.compare:
        # Compare multiple Zimbabwe locations
        locations = [
            (-17.8292, 31.0522),  # Harare
            (-20.1539, 28.5802),  # Bulawayo
            (-18.9707, 32.6709),  # Mutare
            (-20.0744, 30.8328),  # Masvingo
        ]
        
        print(f"\nComparing {len(locations)} locations...")
        comparison = planner.compare_locations(locations, area_ha=args.area)
        
        print("\n📊 Comparison Results:")
        print(f"  Best by Profit: {comparison['best_by_profit']}")
        print(f"  Best by ROI: {comparison['best_by_roi']}")
        print(f"  Best by Sustainability: {comparison['best_by_sustainability']}")
        
    else:
        # Generate single plan
        print(f"\nGenerating plan for:")
        print(f"  📍 Location: ({args.lat:.4f}, {args.lon:.4f})")
        print(f"  🌾 Area: {args.area} ha")
        if args.capital:
            print(f"  💰 Capital: ${args.capital:,.0f}")
        print(f"  👷 Labor: {args.labor} days/year")
        
        plan = planner.generate_plan(
            lat=args.lat,
            lon=args.lon,
            area_ha=args.area,
            available_capital=args.capital,
            available_labor_days=args.labor,
        )
        
        if args.json:
            print(plan.to_json())
        else:
            print("\n" + plan.summary())
            
            # Extra details
            print("\n" + "=" * 50)
            print("📋 Top 5 Yield Predictions:")
            for yp in plan.yield_predictions[:5]:
                print(f"  • {yp['crop_name']}: {yp['predicted_yield_tons_ha']:.1f} t/ha "
                      f"(confidence: {yp['confidence']*100:.0f}%)")
            
            print("\n💡 Key Recommendations:")
            for i, ent in enumerate(plan.recommended_enterprises[:3], 1):
                reasons = ", ".join(ent.get("reasons", [])[:2])
                print(f"  {i}. {ent['name']} - {reasons}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
