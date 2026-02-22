from src.orchestration.yield_targets import get_yield_band, midpoint_target


def test_yield_band_lookup():
    b = get_yield_band("maize", "II")
    assert b.low_tpha > 0
    assert b.high_tpha > b.low_tpha


def test_midpoint_target_valid():
    mid = midpoint_target("sorghum", "IV")
    assert mid > 0
