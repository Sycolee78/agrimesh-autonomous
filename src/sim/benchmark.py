from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
from statistics import mean
from typing import Dict, List

from src.agents.yield_forecast import YieldForecastAgentV0
from src.sim.runner import run


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _summarize(rows: List[Dict]) -> Dict[str, float]:
    water = [r["outcome"]["actual_changes"]["total_water_applied_liters"] for r in rows]
    stress_total = rows[-1]["outcome"]["kpi_delta"]["crop_stress_events_total"] if rows else 0
    final_wue = rows[-1]["outcome"]["kpi_delta"]["water_use_efficiency"] if rows else 0.0
    final_yield = rows[-1]["outcome"]["kpi_delta"]["yield_estimate_tons_per_ha"] if rows else 0.0

    return {
        "days": len(rows),
        "total_water_applied_liters": round(sum(water), 2),
        "avg_daily_water_applied_liters": round(mean(water), 2) if water else 0.0,
        "crop_stress_events_total": stress_total,
        "final_water_use_efficiency": final_wue,
        "final_yield_estimate_tons_per_ha": final_yield,
    }


def run_benchmark(days: int = 30, out_dir: str = "logs", agent_config: dict | None = None) -> Dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    baseline_file = out / "baseline.jsonl"
    agent_file = out / "agent.jsonl"

    run(days=days, policy="baseline", out_file=str(baseline_file))
    run(days=days, policy="agent", out_file=str(agent_file), agent_config=agent_config)

    baseline_rows = _load_jsonl(baseline_file)
    agent_rows = _load_jsonl(agent_file)

    baseline_summary = _summarize(baseline_rows)
    agent_summary = _summarize(agent_rows)

    # Yield forecast snapshot on final cycle state proxy from KPIs
    forecast_agent = YieldForecastAgentV0()
    forecast_summary = {
        "note": "Yield forecast agent integrated; run-time state hookup will be added in next cycle.",
        "model_version": forecast_agent.model_version,
    }

    comparison = {
        "water_saving_liters": round(
            baseline_summary["total_water_applied_liters"] - agent_summary["total_water_applied_liters"], 2
        ),
        "stress_event_delta": agent_summary["crop_stress_events_total"] - baseline_summary["crop_stress_events_total"],
        "yield_delta_tpha": round(
            agent_summary["final_yield_estimate_tons_per_ha"] - baseline_summary["final_yield_estimate_tons_per_ha"], 3
        ),
    }

    result = {
        "agent_config": agent_config or {},
        "baseline": baseline_summary,
        "agent": agent_summary,
        "comparison": comparison,
        "yield_forecast": forecast_summary,
    }

    report_file = out / "benchmark_report.json"
    report_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    report = run_benchmark(days=30, out_dir="logs")
    print(json.dumps(report, indent=2))
