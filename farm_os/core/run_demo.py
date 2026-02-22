from datetime import datetime
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from farm_os.agents.irrigation_agent import IrrigationAgentV0
from farm_os.env.simulator import FarmState, Simulator


if __name__ == "__main__":
    sim = Simulator()
    agent = IrrigationAgentV0()

    state = FarmState(
        timestamp=datetime.utcnow(),
        soil_moisture_pct=30.0,
        forecast_rain_12h_mm=1.0,
        temp_c=31.0,
        crop_stage="vegetative",
        water_available_m3=150.0,
        max_irrigation_mm_day=16.0,
    )

    for day in range(1, 8):
        action = agent.decide(state)
        print(f"Day {day}: moisture={state.soil_moisture_pct:.1f}% | action={action.target_mm}mm | reason={action.reason}")
        state = sim.step(state, action)
