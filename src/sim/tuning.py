from __future__ import annotations

from itertools import product
from pathlib import Path
import json
from typing import Dict, List

from src.sim.benchmark import run_benchmark


def score_result(report: Dict[str, object]) -> float:
    cmp = report["comparison"]
    agent = report["agent"]

    # Higher is better: reward yield, penalize stress and excess water.
    return (
        (agent["final_yield_estimate_tons_per_ha"] * 10.0)
        - (agent["crop_stress_events_total"] * 2.0)
        - (agent["avg_daily_water_applied_liters"] / 60.0)
        + (cmp["water_saving_liters"] / 1000.0)
    )


def grid_search(days: int = 30, out_dir: str = "logs/tuning") -> Dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    targets = [0.64, 0.68, 0.72]
    stress_thresholds = [0.38, 0.40, 0.42]
    liters_per_point = [320.0, 380.0, 450.0]
    floors = [25.0, 45.0, 65.0]

    all_runs: List[Dict[str, object]] = []

    for target, stress, lpp, floor in product(targets, stress_thresholds, liters_per_point, floors):
        cfg = {
            "target_moisture": target,
            "stress_threshold": stress,
            "liters_per_moisture_point": lpp,
            "min_daily_liters_per_plot": floor,
        }
        report = run_benchmark(days=days, out_dir=str(out / f"t{target}_s{stress}_l{int(lpp)}_f{int(floor)}"), agent_config=cfg)
        run_row = {
            "agent_config": cfg,
            "score": round(score_result(report), 4),
            "comparison": report["comparison"],
            "agent": report["agent"],
            "baseline": report["baseline"],
        }
        all_runs.append(run_row)

    all_runs.sort(key=lambda x: x["score"], reverse=True)
    best = all_runs[0]

    summary = {
        "days": days,
        "trials": len(all_runs),
        "best": best,
        "top5": all_runs[:5],
    }

    (out / "tuning_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = grid_search(days=30)
    print(json.dumps(result["best"], indent=2))
