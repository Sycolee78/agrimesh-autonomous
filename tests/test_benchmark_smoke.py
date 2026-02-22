from src.sim.benchmark import run_benchmark


def test_benchmark_smoke(tmp_path):
    report = run_benchmark(days=5, out_dir=str(tmp_path))
    assert "baseline" in report
    assert "agent" in report
    assert "comparison" in report
    assert (tmp_path / "benchmark_report.json").exists()
