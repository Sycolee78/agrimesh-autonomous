from datetime import datetime

from src.agents.yield_forecast import YieldForecastAgentV0
from src.common.models import FarmState, KPIState, PlotState, WaterSystemState, WeatherState


def test_yield_forecast_returns_valid_ranges():
    state = FarmState(
        timestamp=datetime(2026, 2, 22, 6, 0, 0),
        plots=[
            PlotState(plot_id="P1", area_m2=300, crop_type="maize", crop_stage="vegetative", soil_moisture=0.41),
            PlotState(plot_id="P2", area_m2=260, crop_type="maize", crop_stage="vegetative", soil_moisture=0.36),
        ],
        water_system=WaterSystemState(tank_level_liters=4000, daily_supply_limit_liters=1200, pump_capacity_lpm=65),
        weather=WeatherState(temperature_c=32, humidity_pct=55, rainfall_mm=0.8),
        kpis=KPIState(),
    )

    model = YieldForecastAgentV0()
    pred = model.predict(state, recent_avg_moisture=[0.4, 0.39, 0.38])

    assert 0 <= pred.stress_risk_7d <= 1
    assert pred.yield_proxy_estimate_tpha > 0
    assert pred.recommendation_tag in {"increase_irrigation", "watch_stress", "stable"}
