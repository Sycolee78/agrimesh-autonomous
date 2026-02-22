from src.sim.runner import run


def test_simulation_smoke(tmp_path):
    out = tmp_path / "smoke.jsonl"
    run(days=3, policy="agent", out_file=str(out))
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
