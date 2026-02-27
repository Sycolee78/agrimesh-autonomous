"""
Pilot validation dataset generator and loader.

Creates realistic Zimbabwe farm historical data for validation,
based on actual farming patterns and weather conditions.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from src.data.weather_client import OpenMeteoClient, DailyWeather, ZIMBABWE_LOCATIONS


@dataclass
class FarmEvent:
    """A recorded farm event/observation."""
    date: str
    event_type: str  # "planting", "irrigation", "observation", "harvest", "pest", "fertilizer"
    details: Dict


@dataclass
class DailyRecord:
    """Daily record from a real/simulated farm."""
    date: str
    weather: Dict  # temp, rain, humidity
    soil_moisture_measured: Optional[float]  # If measured that day
    irrigation_applied_liters: float
    observations: List[str]
    crop_stage: str
    growth_day: int


@dataclass
class PilotFarmData:
    """Complete pilot farm dataset."""
    farm_id: str
    location: str
    aez_zone: str
    season: str  # e.g., "2024-2025"
    crop: str
    area_ha: float
    planting_date: str
    harvest_date: Optional[str]
    final_yield_tons: Optional[float]
    daily_records: List[DailyRecord]
    events: List[FarmEvent]
    metadata: Dict


def generate_pilot_dataset(
    location: str = "harare",
    season_year: int = 2024,
    crop: str = "maize",
    area_ha: float = 5.0,
    irrigation_style: str = "traditional",  # "traditional", "efficient", "erratic"
    output_dir: Optional[Path] = None,
) -> PilotFarmData:
    """
    Generate a realistic pilot farm dataset using real weather data.
    
    The irrigation decisions are simulated based on typical farmer behavior,
    which can then be compared against what the AgriMesh agent would recommend.
    
    Args:
        location: Zimbabwe location
        season_year: Year season starts (Nov of this year)
        crop: Primary crop
        area_ha: Farm area in hectares
        irrigation_style: How the farmer irrigates
        output_dir: Where to save the dataset
    
    Returns:
        Complete farm dataset
    """
    
    random.seed(42 + season_year)  # Reproducible but varied by season
    
    # Fetch real weather
    client = OpenMeteoClient()
    season_start = date(season_year, 11, 1)
    season_end = date(season_year + 1, 4, 15)  # ~165 days
    
    try:
        weather_data = client.get_historical(location, season_start, season_end)
    except Exception as e:
        print(f"Could not fetch weather: {e}")
        # Generate synthetic weather as fallback
        weather_data = generate_synthetic_weather(season_start, season_end)
    
    # Planting date (typically early November after first good rains)
    planting_date = find_planting_date(weather_data, season_start)
    
    # Generate daily records
    daily_records = []
    events = []
    
    # Track state
    soil_moisture = 0.45  # Start dry
    cumulative_rain = 0.0
    growth_day = 0
    
    # Irrigation behavior parameters by style
    if irrigation_style == "traditional":
        # Fixed schedule, regardless of conditions
        irrigation_interval = 7  # Every 7 days
        irrigation_amount = 150 * area_ha  # liters per ha
        rain_threshold = 5  # Skip if >5mm rain
    elif irrigation_style == "efficient":
        # More responsive to conditions
        irrigation_interval = 5
        irrigation_amount = 100 * area_ha
        rain_threshold = 3
    else:  # erratic
        irrigation_interval = random.randint(5, 14)
        irrigation_amount = random.uniform(80, 200) * area_ha
        rain_threshold = random.uniform(2, 10)
    
    days_since_irrigation = 0
    
    for weather in weather_data:
        growth_day += 1
        days_since_irrigation += 1
        
        # Update soil moisture (simplified model)
        rain_contribution = weather.precipitation_mm / 100 * 0.3
        evap_loss = weather.evapotranspiration_mm / 100 * 0.15
        soil_moisture = max(0.1, min(0.95, soil_moisture + rain_contribution - evap_loss))
        
        cumulative_rain += weather.precipitation_mm
        
        # Determine irrigation
        irrigation = 0.0
        observations = []
        
        # Planting event
        if weather.date == planting_date:
            events.append(FarmEvent(
                date=weather.date.isoformat(),
                event_type="planting",
                details={"crop": crop, "area_ha": area_ha},
            ))
            observations.append("Planting completed")
        
        # Traditional farmer irrigation logic
        should_irrigate = (
            days_since_irrigation >= irrigation_interval and
            weather.precipitation_mm < rain_threshold and
            growth_day > 7  # After germination
        )
        
        if irrigation_style == "erratic":
            # Sometimes forgets, sometimes over-irrigates
            if random.random() < 0.15:
                should_irrigate = not should_irrigate
            if should_irrigate and random.random() < 0.2:
                irrigation_amount *= random.uniform(1.2, 1.8)
        
        if should_irrigate:
            irrigation = irrigation_amount
            soil_moisture = min(0.95, soil_moisture + irrigation / (area_ha * 10000) * 0.1)
            days_since_irrigation = 0
            observations.append(f"Irrigated {irrigation:.0f}L")
        
        # Crop stage
        crop_stage = get_crop_stage_name(growth_day)
        
        # Random observations
        if weather.precipitation_mm > 20:
            observations.append("Heavy rain")
        if soil_moisture < 0.35:
            observations.append("Soil appears dry")
        if soil_moisture > 0.8 and weather.precipitation_mm > 10:
            observations.append("Waterlogging concern")
        
        # Pest/disease events (random)
        if random.random() < 0.02:
            pest = random.choice(["Fall armyworm spotted", "Leaf rust observed", "Aphids on lower leaves"])
            observations.append(pest)
            events.append(FarmEvent(
                date=weather.date.isoformat(),
                event_type="pest",
                details={"observation": pest},
            ))
        
        # Fertilizer application (at key stages)
        if growth_day in [14, 35, 55]:
            fert_type = {14: "Basal", 35: "Top-dress 1", 55: "Top-dress 2"}[growth_day]
            observations.append(f"{fert_type} fertilizer applied")
            events.append(FarmEvent(
                date=weather.date.isoformat(),
                event_type="fertilizer",
                details={"type": fert_type, "growth_day": growth_day},
            ))
        
        # Soil moisture measurement (occasional)
        measured_moisture = None
        if random.random() < 0.15:  # ~15% of days
            measured_moisture = round(soil_moisture + random.uniform(-0.05, 0.05), 3)
            observations.append(f"Soil moisture check: {measured_moisture*100:.0f}%")
        
        daily_records.append(DailyRecord(
            date=weather.date.isoformat(),
            weather={
                "temp_max_c": weather.temperature_max_c,
                "temp_min_c": weather.temperature_min_c,
                "rain_mm": weather.precipitation_mm,
                "humidity_pct": weather.humidity_mean_pct,
                "et0_mm": weather.evapotranspiration_mm,
            },
            soil_moisture_measured=measured_moisture,
            irrigation_applied_liters=round(irrigation, 1),
            observations=observations,
            crop_stage=crop_stage,
            growth_day=growth_day,
        ))
    
    # Estimate final yield based on cumulative conditions
    stress_days = sum(1 for r in daily_records if r.soil_moisture_measured and r.soil_moisture_measured < 0.35)
    base_yield = 5.5 if crop == "maize" else 3.0
    yield_factor = max(0.4, 1.0 - stress_days * 0.02 - (0.1 if irrigation_style == "erratic" else 0))
    final_yield = round(base_yield * yield_factor * area_ha, 2)
    
    harvest_date = (planting_date + timedelta(days=130)).isoformat()
    events.append(FarmEvent(
        date=harvest_date,
        event_type="harvest",
        details={"yield_tons": final_yield, "yield_per_ha": final_yield / area_ha},
    ))
    
    # Build dataset
    loc_info = ZIMBABWE_LOCATIONS.get(location.lower(), {"aez": "II"})
    
    pilot_data = PilotFarmData(
        farm_id=f"pilot-{location}-{season_year}-{crop}",
        location=location,
        aez_zone=loc_info.get("aez", "II"),
        season=f"{season_year}-{season_year + 1}",
        crop=crop,
        area_ha=area_ha,
        planting_date=planting_date.isoformat(),
        harvest_date=harvest_date,
        final_yield_tons=final_yield,
        daily_records=daily_records,
        events=events,
        metadata={
            "generated_at": str(date.today()),
            "irrigation_style": irrigation_style,
            "weather_source": "open-meteo",
            "total_rainfall_mm": round(cumulative_rain, 1),
            "total_irrigation_liters": round(sum(r.irrigation_applied_liters for r in daily_records), 1),
        },
    )
    
    # Save if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{pilot_data.farm_id}.json"
        with open(output_file, "w") as f:
            json.dump({
                "farm_id": pilot_data.farm_id,
                "location": pilot_data.location,
                "aez_zone": pilot_data.aez_zone,
                "season": pilot_data.season,
                "crop": pilot_data.crop,
                "area_ha": pilot_data.area_ha,
                "planting_date": pilot_data.planting_date,
                "harvest_date": pilot_data.harvest_date,
                "final_yield_tons": pilot_data.final_yield_tons,
                "metadata": pilot_data.metadata,
                "events": [asdict(e) for e in pilot_data.events],
                "daily_records": [asdict(r) for r in pilot_data.daily_records],
            }, f, indent=2)
        print(f"Pilot data saved to {output_file}")
    
    return pilot_data


def get_crop_stage_name(growth_day: int) -> str:
    """Get crop stage name from growth day."""
    if growth_day < 10:
        return "germination"
    elif growth_day < 40:
        return "vegetative"
    elif growth_day < 65:
        return "flowering"
    elif growth_day < 100:
        return "grain_fill"
    else:
        return "maturity"


def find_planting_date(weather_data: List[DailyWeather], season_start: date) -> date:
    """Find optimal planting date based on rainfall."""
    cumulative = 0.0
    for w in weather_data[:30]:  # First 30 days of season
        cumulative += w.precipitation_mm
        if cumulative > 25 and w.precipitation_mm > 5:
            return w.date
    return season_start + timedelta(days=10)


def generate_synthetic_weather(start: date, end: date) -> List[DailyWeather]:
    """Generate synthetic weather as fallback."""
    from datetime import datetime
    
    weather = []
    current = start
    while current <= end:
        month = current.month
        
        # Zimbabwe seasonal patterns
        if month in [11, 12, 1, 2, 3]:  # Wet season
            rain_prob = 0.4
            rain_amount = random.uniform(0, 30) if random.random() < rain_prob else 0
            temp_base = 25
        else:  # Dry season
            rain_prob = 0.1
            rain_amount = random.uniform(0, 10) if random.random() < rain_prob else 0
            temp_base = 20
        
        weather.append(DailyWeather(
            date=current,
            temperature_max_c=temp_base + random.uniform(3, 8),
            temperature_min_c=temp_base - random.uniform(5, 10),
            temperature_mean_c=temp_base,
            precipitation_mm=rain_amount,
            humidity_mean_pct=random.uniform(50, 80),
            wind_speed_max_kmh=random.uniform(5, 25),
            solar_radiation_mj_m2=random.uniform(15, 25),
            evapotranspiration_mm=random.uniform(3, 6),
        ))
        current += timedelta(days=1)
    
    return weather


def load_pilot_data(filepath: Path) -> PilotFarmData:
    """Load pilot data from JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    
    return PilotFarmData(
        farm_id=data["farm_id"],
        location=data["location"],
        aez_zone=data["aez_zone"],
        season=data["season"],
        crop=data["crop"],
        area_ha=data["area_ha"],
        planting_date=data["planting_date"],
        harvest_date=data.get("harvest_date"),
        final_yield_tons=data.get("final_yield_tons"),
        daily_records=[DailyRecord(**r) for r in data["daily_records"]],
        events=[FarmEvent(**e) for e in data["events"]],
        metadata=data.get("metadata", {}),
    )


# CLI
if __name__ == "__main__":
    import sys
    
    location = sys.argv[1] if len(sys.argv) > 1 else "harare"
    style = sys.argv[2] if len(sys.argv) > 2 else "traditional"
    
    print(f"\n{'='*60}")
    print(f"Generating pilot farm dataset")
    print(f"Location: {location}, Style: {style}")
    print(f"{'='*60}\n")
    
    pilot = generate_pilot_dataset(
        location=location,
        season_year=2024,
        crop="maize",
        area_ha=5.0,
        irrigation_style=style,
        output_dir=Path("data/pilots"),
    )
    
    print(f"\nDataset summary:")
    print(f"  Farm ID: {pilot.farm_id}")
    print(f"  Season: {pilot.season}")
    print(f"  Days recorded: {len(pilot.daily_records)}")
    print(f"  Total irrigation: {pilot.metadata.get('total_irrigation_liters', 0):.0f} L")
    print(f"  Total rainfall: {pilot.metadata.get('total_rainfall_mm', 0):.0f} mm")
    print(f"  Final yield: {pilot.final_yield_tons} tons ({pilot.final_yield_tons/pilot.area_ha:.2f} t/ha)")
    print(f"  Events logged: {len(pilot.events)}")
