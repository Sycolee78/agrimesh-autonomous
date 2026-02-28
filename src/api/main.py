"""
AgriMesh FastAPI Backend

Provides REST API for the React frontend, connecting to the
existing Python simulation engine.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.allocators.aez_lookup import AEZLookupAgent
from src.strategic_planner import StrategicFarmPlanner
from src.sim.yield_model import CROP_PROFILES, calculate_yield_factor
from src.data.weather_client import OpenMeteoClient, ZIMBABWE_LOCATIONS

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="AgriMesh API",
    description="Farm planning and simulation API for Zimbabwe",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
aez_agent = AEZLookupAgent()
strategic_planner = StrategicFarmPlanner()
weather_client = OpenMeteoClient()

# ============================================================================
# Request/Response Models
# ============================================================================

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-25, le=-15, description="Latitude")
    lng: float = Field(..., ge=25, le=35, description="Longitude")


class LivestockConfig(BaseModel):
    chickens: int = 0
    cows: int = 0
    goats: int = 0
    sheep: int = 0
    pigs: int = 0


class CropConfig(BaseModel):
    type: str
    areaHa: float
    irrigated: bool = False


class BuildingConfig(BaseModel):
    id: str
    type: str
    position: Coordinates
    size: Dict[str, float] = {"width": 10, "height": 10}


class FarmZone(BaseModel):
    id: str
    type: str  # "crops", "pasture", "buildings", "water"
    polygon: List[Coordinates]
    cropType: Optional[str] = None
    label: Optional[str] = None


class FarmConfig(BaseModel):
    id: str
    name: str = "My Farm"
    location: Coordinates
    areaHa: float = Field(..., gt=0, le=1000)
    farmType: str = "mixed"  # "crops", "livestock", "mixed"
    livestock: LivestockConfig = LivestockConfig()
    crops: List[CropConfig] = []
    buildings: List[BuildingConfig] = []
    zones: List[FarmZone] = []


class AEZZoneResponse(BaseModel):
    id: str
    name: str
    rainfallRange: str
    description: str
    suitableCrops: List[str]
    livestockCapacity: Dict[str, float]


class WeatherData(BaseModel):
    annualRainfallMm: float
    avgTempC: float
    rainyDays: int
    droughtRisk: str
    frostRisk: bool


class SoilData(BaseModel):
    type: str
    ph: float
    organicMatter: str
    drainage: str


class CropSuitability(BaseModel):
    crop: str
    suitabilityScore: float
    expectedYieldTHa: float
    waterRequirementMm: float
    profitPotentialUsd: float
    risks: List[str]


class LivestockAnalysis(BaseModel):
    type: str
    count: int
    feedRequirementKg: float
    waterRequirementL: float
    manureOutputKg: float
    estimatedRevenueUsd: float


class SynergyBonus(BaseModel):
    source: str
    target: str
    benefit: str
    impactPercent: float


class SustainabilityMetrics(BaseModel):
    overallScore: float
    waterEfficiency: float
    soilHealth: float
    biodiversity: float
    carbonFootprint: float
    synergies: List[SynergyBonus]
    suggestions: List[str]


class ProfitBreakdown(BaseModel):
    enterprise: str
    revenue: float
    costs: float
    profit: float


class ProfitEstimate(BaseModel):
    totalRevenueUsd: float
    totalCostsUsd: float
    netProfitUsd: float
    breakdownByEnterprise: List[ProfitBreakdown]
    scenarios: Dict[str, float]


class ResourceRequirements(BaseModel):
    waterLitersPerDay: float
    feedKgPerDay: float
    fertilizerKgPerSeason: float
    laborHoursPerWeek: float
    fuelLitersPerMonth: float


class SimulationResult(BaseModel):
    farmId: str
    timestamp: str
    location: Coordinates
    aezZone: AEZZoneResponse
    weather: WeatherData
    soil: SoilData
    cropSuitability: List[CropSuitability]
    livestockAnalysis: List[LivestockAnalysis]
    sustainability: SustainabilityMetrics
    profitEstimate: ProfitEstimate
    resources: ResourceRequirements


# ============================================================================
# AEZ Data (Zimbabwe-specific)
# ============================================================================

AEZ_DATA = {
    "I": {
        "id": "I",
        "name": "Specialized & Diversified Farming",
        "rainfallRange": ">1000mm",
        "description": "High rainfall zone suitable for intensive farming, tea, coffee",
        "suitableCrops": ["maize", "vegetables", "potatoes", "tobacco", "wheat", "tea", "coffee"],
        "livestockCapacity": {"cows": 1.5, "goats": 3, "sheep": 2, "chickens": 100, "pigs": 5},
    },
    "IIa": {
        "id": "IIa",
        "name": "Intensive Farming (High)",
        "rainfallRange": "800-1000mm",
        "description": "Good rainfall, suitable for intensive cropping and tobacco",
        "suitableCrops": ["maize", "sorghum", "groundnuts", "cotton", "tobacco", "soybeans"],
        "livestockCapacity": {"cows": 1.2, "goats": 2.5, "sheep": 1.5, "chickens": 80, "pigs": 4},
    },
    "IIb": {
        "id": "IIb",
        "name": "Intensive Farming (Low)",
        "rainfallRange": "750-800mm",
        "description": "Moderate-high rainfall, good for maize and cotton",
        "suitableCrops": ["maize", "sorghum", "groundnuts", "cotton", "sunflower"],
        "livestockCapacity": {"cows": 1.0, "goats": 2, "sheep": 1.5, "chickens": 70, "pigs": 3},
    },
    "III": {
        "id": "III",
        "name": "Semi-Intensive Farming",
        "rainfallRange": "650-800mm",
        "description": "Mixed crop-livestock zone, semi-arid",
        "suitableCrops": ["maize", "sorghum", "groundnuts", "fodder", "millet"],
        "livestockCapacity": {"cows": 0.8, "goats": 2, "sheep": 1.2, "chickens": 60, "pigs": 2},
    },
    "IV": {
        "id": "IV",
        "name": "Semi-Extensive Farming",
        "rainfallRange": "450-650mm",
        "description": "Livestock focus with drought-tolerant crops",
        "suitableCrops": ["sorghum", "millet", "groundnuts", "fodder"],
        "livestockCapacity": {"cows": 0.5, "goats": 1.5, "sheep": 1, "chickens": 40, "pigs": 1},
    },
    "V": {
        "id": "V",
        "name": "Extensive Farming",
        "rainfallRange": "<500mm",
        "description": "Cattle and game ranching only",
        "suitableCrops": ["fodder"],
        "livestockCapacity": {"cows": 0.3, "goats": 1, "sheep": 0.5, "chickens": 20, "pigs": 0.5},
    },
}

# ============================================================================
# Helper Functions
# ============================================================================

def lookup_aez_zone(lat: float, lng: float) -> Dict[str, Any]:
    """Determine AEZ zone from coordinates."""
    # Use actual AEZ lookup if available
    try:
        zone_info = aez_agent.lookup(lat, lng)
        zone_id = zone_info.get("zone", "III")
        if zone_id in AEZ_DATA:
            return AEZ_DATA[zone_id]
    except Exception:
        pass
    
    # Fallback: simplified lookup based on coordinates
    if lat > -18 and lng > 31:
        return AEZ_DATA["I"]  # Eastern Highlands
    elif lat > -18.5:
        return AEZ_DATA["IIa"]  # Mashonaland
    elif lat > -19.5 and lng > 29:
        return AEZ_DATA["IIb"]
    elif lat > -20.5:
        return AEZ_DATA["III"]  # Midlands
    elif lng < 27:
        return AEZ_DATA["V"]  # Victoria Falls area
    else:
        return AEZ_DATA["IV"]  # Matabeleland


def get_weather_data(lat: float, lng: float) -> WeatherData:
    """Fetch weather data for location."""
    # Find nearest known location
    nearest = min(
        ZIMBABWE_LOCATIONS.items(),
        key=lambda x: abs(x[1]["lat"] - lat) + abs(x[1]["lng"] - lng)
        if "lng" in x[1] else abs(x[1]["lat"] - lat) + abs(x[1]["lon"] - lng)
    )
    
    try:
        from datetime import date
        # Get last year's growing season data
        data = weather_client.get_historical(
            location=nearest[0],
            start_date=date(2024, 11, 1),
            end_date=date(2025, 3, 31)
        )
        
        total_rain = sum(d.precipitation_mm for d in data)
        avg_temp = sum(d.temperature_max_c for d in data) / len(data)
        rainy_days = sum(1 for d in data if d.precipitation_mm > 1)
        
        return WeatherData(
            annualRainfallMm=round(total_rain * 2.4),  # Extrapolate to annual
            avgTempC=round(avg_temp, 1),
            rainyDays=rainy_days,
            droughtRisk="low" if total_rain > 300 else "medium" if total_rain > 200 else "high",
            frostRisk=lat > -18 and lng > 31  # Eastern highlands
        )
    except Exception as e:
        print(f"Weather fetch error: {e}")
        # Return estimates based on AEZ
        aez = lookup_aez_zone(lat, lng)
        rainfall_map = {"I": 1100, "IIa": 900, "IIb": 780, "III": 700, "IV": 550, "V": 400}
        rain = rainfall_map.get(aez["id"], 700)
        
        return WeatherData(
            annualRainfallMm=rain,
            avgTempC=24.0,
            rainyDays=int(rain / 8),
            droughtRisk="low" if rain > 800 else "medium" if rain > 600 else "high",
            frostRisk=aez["id"] == "I"
        )


def calculate_crop_suitability(
    crop: str, 
    aez: Dict[str, Any], 
    weather: WeatherData
) -> CropSuitability:
    """Calculate crop suitability score."""
    is_suitable = crop in aez.get("suitableCrops", [])
    base_score = 75 if is_suitable else 35
    
    # Weather modifiers
    if weather.droughtRisk == "low":
        base_score += 10
    elif weather.droughtRisk == "high":
        base_score -= 15
    
    # Crop-specific adjustments
    crop_adjustments = {
        "sorghum": 10 if weather.droughtRisk != "low" else 0,
        "vegetables": 10 if weather.annualRainfallMm > 800 else -5,
        "tobacco": 15 if aez["id"] in ["IIa", "IIb"] else -10,
        "maize": 5 if weather.annualRainfallMm > 700 else -10,
    }
    base_score += crop_adjustments.get(crop, 0)
    
    score = max(0, min(100, base_score))
    
    # Yield estimation
    base_yields = {
        "maize": 5.5, "sorghum": 3.5, "groundnuts": 2.0, "wheat": 4.5,
        "vegetables": 15.0, "tobacco": 2.5, "cotton": 3.0, "fodder": 8.0,
        "potatoes": 25.0, "millet": 2.0, "sunflower": 2.5, "soybeans": 2.8,
    }
    base_yield = base_yields.get(crop, 3.0)
    expected_yield = base_yield * (score / 80)
    
    # Prices
    prices = {
        "maize": 250, "sorghum": 200, "groundnuts": 800, "wheat": 300,
        "vegetables": 500, "tobacco": 4500, "cotton": 1200, "fodder": 100,
        "potatoes": 300, "millet": 180, "sunflower": 400, "soybeans": 450,
    }
    profit = expected_yield * prices.get(crop, 300)
    
    # Risks
    risks = []
    if weather.droughtRisk == "high":
        risks.append("High drought risk")
    if weather.frostRisk and crop in ["vegetables", "potatoes", "tobacco"]:
        risks.append("Frost damage possible")
    if not is_suitable:
        risks.append("Not traditionally grown in this zone")
    if crop == "tobacco" and aez["id"] not in ["I", "IIa", "IIb"]:
        risks.append("Low rainfall for tobacco")
    
    return CropSuitability(
        crop=crop,
        suitabilityScore=round(score, 1),
        expectedYieldTHa=round(expected_yield, 2),
        waterRequirementMm=round(400 + (100 - score) * 3),
        profitPotentialUsd=round(profit),
        risks=risks
    )


def calculate_livestock_analysis(
    type_name: str, 
    count: int
) -> LivestockAnalysis:
    """Calculate livestock requirements and revenue."""
    feed_per_day = {"chickens": 0.12, "cows": 12, "goats": 2, "sheep": 1.5, "pigs": 3}
    water_per_day = {"chickens": 0.25, "cows": 50, "goats": 5, "sheep": 4, "pigs": 8}
    revenue_per_year = {"chickens": 15, "cows": 800, "goats": 150, "sheep": 120, "pigs": 200}
    
    return LivestockAnalysis(
        type=type_name,
        count=count,
        feedRequirementKg=round(count * feed_per_day.get(type_name, 1) * 365),
        waterRequirementL=round(count * water_per_day.get(type_name, 5) * 365),
        manureOutputKg=round(count * feed_per_day.get(type_name, 1) * 365 * 0.4),
        estimatedRevenueUsd=round(count * revenue_per_year.get(type_name, 100))
    )


def calculate_sustainability(
    farm: FarmConfig,
    crop_results: List[CropSuitability],
    livestock_results: List[LivestockAnalysis]
) -> SustainabilityMetrics:
    """Calculate sustainability metrics and synergies."""
    synergies: List[SynergyBonus] = []
    bonus_score = 0
    
    # Manure → fertilizer synergy
    total_manure = sum(l.manureOutputKg for l in livestock_results)
    total_crop_area = sum(c.areaHa for c in farm.crops)
    
    if total_manure > 0 and total_crop_area > 0:
        manure_per_ha = total_manure / total_crop_area
        if manure_per_ha > 1000:
            synergies.append(SynergyBonus(
                source="Livestock manure",
                target="Crop fertilization",
                benefit="Reduces fertilizer costs by 40%",
                impactPercent=40
            ))
            bonus_score += 15
    
    # Crop residue → feed synergy
    feed_crops = ["maize", "sorghum", "fodder", "millet"]
    has_feed_crops = any(c.type in feed_crops for c in farm.crops)
    has_ruminants = farm.livestock.cows > 0 or farm.livestock.goats > 0 or farm.livestock.sheep > 0
    
    if has_feed_crops and has_ruminants:
        synergies.append(SynergyBonus(
            source="Crop residues",
            target="Livestock feed",
            benefit="Reduces feed costs by 25%",
            impactPercent=25
        ))
        bonus_score += 10
    
    # Chickens → pest control
    if farm.livestock.chickens > 50 and total_crop_area > 0:
        synergies.append(SynergyBonus(
            source="Free-range chickens",
            target="Pest control",
            benefit="Reduces pesticide needs by 30%",
            impactPercent=30
        ))
        bonus_score += 8
    
    # Groundnuts → nitrogen fixation
    if any(c.type == "groundnuts" for c in farm.crops):
        synergies.append(SynergyBonus(
            source="Groundnuts (legume)",
            target="Soil nitrogen",
            benefit="Adds 40-60 kg N/ha to soil",
            impactPercent=20
        ))
        bonus_score += 12
    
    # Calculate base scores
    crop_diversity = len(set(c.type for c in farm.crops))
    livestock_diversity = sum(1 for v in [
        farm.livestock.chickens, farm.livestock.cows, 
        farm.livestock.goats, farm.livestock.sheep, farm.livestock.pigs
    ] if v > 0)
    
    diversity_score = min(100, crop_diversity * 15 + livestock_diversity * 10)
    irrigated_ratio = sum(c.areaHa for c in farm.crops if c.irrigated) / max(total_crop_area, 0.1)
    water_score = 85 - irrigated_ratio * 20  # Less irrigation = better score
    
    # Suggestions
    suggestions = []
    if total_manure < total_crop_area * 500:
        suggestions.append("Consider adding more livestock for manure production")
    if not any(c.type == "groundnuts" for c in farm.crops):
        suggestions.append("Add groundnuts for nitrogen fixation benefits")
    if not any(b.type == "water_tank" for b in farm.buildings):
        suggestions.append("Install rainwater harvesting tanks")
    if not any(c.irrigated for c in farm.crops) and farm.areaHa > 2:
        suggestions.append("Consider drip irrigation for vegetable plots")
    if crop_diversity < 2:
        suggestions.append("Add crop rotation for soil health")
    if farm.livestock.cows > 10 and not any(c.type == "fodder" for c in farm.crops):
        suggestions.append("Grow fodder crops to reduce feed costs")
    
    overall = min(100, round(
        diversity_score * 0.3 + 
        water_score * 0.2 + 
        60 * 0.3 + 
        bonus_score * 0.2
    ))
    
    return SustainabilityMetrics(
        overallScore=overall,
        waterEfficiency=round(water_score),
        soilHealth=min(100, 50 + bonus_score),
        biodiversity=diversity_score,
        carbonFootprint=max(0, 100 - farm.livestock.cows * 2),
        synergies=synergies,
        suggestions=suggestions[:5]
    )


def calculate_profit(
    farm: FarmConfig,
    crop_results: List[CropSuitability],
    livestock_results: List[LivestockAnalysis],
    sustainability: SustainabilityMetrics
) -> ProfitEstimate:
    """Calculate profit estimates."""
    breakdown = []
    
    # Crop profits
    for crop in farm.crops:
        suit = next((c for c in crop_results if c.crop == crop.type), None)
        if suit:
            revenue = suit.profitPotentialUsd * crop.areaHa
            costs = revenue * 0.45
            
            # Apply synergy discounts
            for syn in sustainability.synergies:
                if "fertilizer" in syn.target.lower():
                    costs *= 0.85
                    break
            
            breakdown.append(ProfitBreakdown(
                enterprise=crop.type,
                revenue=round(revenue),
                costs=round(costs),
                profit=round(revenue - costs)
            ))
    
    # Livestock profits
    for livestock in livestock_results:
        if livestock.count > 0:
            revenue = livestock.estimatedRevenueUsd
            feed_cost = livestock.feedRequirementKg * 0.3
            other_costs = revenue * 0.2
            costs = feed_cost + other_costs
            
            # Apply feed synergy
            for syn in sustainability.synergies:
                if "feed" in syn.target.lower():
                    costs *= 0.8
                    break
            
            breakdown.append(ProfitBreakdown(
                enterprise=livestock.type,
                revenue=round(revenue),
                costs=round(costs),
                profit=round(revenue - costs)
            ))
    
    total_revenue = sum(b.revenue for b in breakdown)
    total_costs = sum(b.costs for b in breakdown)
    net_profit = total_revenue - total_costs
    
    return ProfitEstimate(
        totalRevenueUsd=total_revenue,
        totalCostsUsd=total_costs,
        netProfitUsd=net_profit,
        breakdownByEnterprise=breakdown,
        scenarios={
            "pessimistic": round(net_profit * 0.6),
            "expected": round(net_profit),
            "optimistic": round(net_profit * 1.4)
        }
    )


def calculate_resources(
    farm: FarmConfig,
    livestock_results: List[LivestockAnalysis]
) -> ResourceRequirements:
    """Calculate resource requirements."""
    total_crop_area = sum(c.areaHa for c in farm.crops)
    irrigated_area = sum(c.areaHa for c in farm.crops if c.irrigated)
    
    livestock_water = sum(l.waterRequirementL for l in livestock_results) / 365
    irrigation_water = irrigated_area * 50  # ~50L/day/ha drip
    
    livestock_feed = sum(l.feedRequirementKg for l in livestock_results) / 365
    
    return ResourceRequirements(
        waterLitersPerDay=round(livestock_water + irrigation_water + 100),
        feedKgPerDay=round(livestock_feed),
        fertilizerKgPerSeason=round(total_crop_area * 150),
        laborHoursPerWeek=round(farm.areaHa * 8 + sum(
            getattr(farm.livestock, k) for k in ["chickens", "cows", "goats", "sheep", "pigs"]
        ) * 0.5),
        fuelLitersPerMonth=round(farm.areaHa * 5 + 20)
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API health check."""
    return {
        "name": "AgriMesh API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/aez/{lat}/{lng}", response_model=AEZZoneResponse)
async def get_aez_zone(lat: float, lng: float):
    """Get AEZ zone for coordinates."""
    zone = lookup_aez_zone(lat, lng)
    return AEZZoneResponse(**zone)


@app.get("/api/weather/{lat}/{lng}", response_model=WeatherData)
async def get_weather(lat: float, lng: float):
    """Get weather data for coordinates."""
    return get_weather_data(lat, lng)


@app.get("/api/crops/suitability/{lat}/{lng}")
async def get_crop_suitability(lat: float, lng: float):
    """Get crop suitability for location."""
    aez = lookup_aez_zone(lat, lng)
    weather = get_weather_data(lat, lng)
    
    all_crops = [
        "maize", "sorghum", "groundnuts", "wheat", "vegetables",
        "tobacco", "cotton", "fodder", "potatoes", "millet", "sunflower"
    ]
    
    results = [calculate_crop_suitability(crop, aez, weather) for crop in all_crops]
    return sorted(results, key=lambda x: x.suitabilityScore, reverse=True)


@app.post("/api/simulate", response_model=SimulationResult)
async def run_simulation(farm: FarmConfig):
    """Run full farm simulation."""
    # Get location data
    aez = lookup_aez_zone(farm.location.lat, farm.location.lng)
    weather = get_weather_data(farm.location.lat, farm.location.lng)
    
    # Soil estimate based on AEZ
    soil_types = {
        "I": "Red clay loam",
        "IIa": "Sandy loam",
        "IIb": "Sandy clay loam",
        "III": "Sandy loam",
        "IV": "Sandy soil",
        "V": "Kalahari sand",
    }
    soil = SoilData(
        type=soil_types.get(aez["id"], "Loam"),
        ph=5.8,
        organicMatter="medium" if aez["id"] in ["I", "IIa", "IIb"] else "low",
        drainage="good"
    )
    
    # Calculate crop suitability
    all_crops = [
        "maize", "sorghum", "groundnuts", "wheat", "vegetables",
        "tobacco", "cotton", "fodder", "potatoes"
    ]
    crop_results = [calculate_crop_suitability(crop, aez, weather) for crop in all_crops]
    crop_results.sort(key=lambda x: x.suitabilityScore, reverse=True)
    
    # Calculate livestock analysis
    livestock_results = []
    for type_name in ["chickens", "cows", "goats", "sheep", "pigs"]:
        count = getattr(farm.livestock, type_name, 0)
        if count > 0:
            livestock_results.append(calculate_livestock_analysis(type_name, count))
    
    # Calculate sustainability
    sustainability = calculate_sustainability(farm, crop_results, livestock_results)
    
    # Calculate profit
    profit = calculate_profit(farm, crop_results, livestock_results, sustainability)
    
    # Calculate resources
    resources = calculate_resources(farm, livestock_results)
    
    return SimulationResult(
        farmId=farm.id,
        timestamp=datetime.now().isoformat(),
        location=farm.location,
        aezZone=AEZZoneResponse(**aez),
        weather=weather,
        soil=soil,
        cropSuitability=crop_results,
        livestockAnalysis=livestock_results,
        sustainability=sustainability,
        profitEstimate=profit,
        resources=resources
    )


@app.post("/api/strategic-plan")
async def get_strategic_plan(
    lat: float,
    lng: float,
    area_ha: float = 5.0,
    budget_usd: float = 10000
):
    """Get strategic farm plan using the full planner."""
    try:
        plan = strategic_planner.plan(
            lat=lat,
            lon=lng,
            area_ha=area_ha,
            budget_usd=budget_usd
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def get_locations():
    """Get Zimbabwe locations with coordinates."""
    return {
        name: {
            "lat": data["lat"],
            "lng": data.get("lng", data.get("lon")),
            "aez": data.get("aez", "III")
        }
        for name, data in ZIMBABWE_LOCATIONS.items()
    }


# ============================================================================
# Run with Uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
