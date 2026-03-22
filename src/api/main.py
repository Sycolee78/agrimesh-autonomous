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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.allocators.aez_lookup import AEZLookupAgent
from src.strategic_planner import StrategicFarmPlanner
from src.sim.yield_model import CROP_PROFILES, calculate_yield_factor
from src.data.weather_client import OpenMeteoClient, ZIMBABWE_LOCATIONS
from src.common.models import FarmState, PlotState, WaterSystemState, WeatherState, KPIState
from src.orchestration import FarmManagementOrchestrator, AgentContext
from src.resources.pool import ResourcePool, ResourceType, AllocationPriority
from src.resources.bidding import BiddingEngine, BidStatus
from src.resources.budget import BudgetManager, BudgetPeriod, BudgetStatus
from src.resources.logger import DecisionLogger, DecisionType, DecisionOutcome
import random

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
# Multi-Day Orchestrator Simulation Models
# ============================================================================

class OrchestratorConfig(BaseModel):
    """Configuration for multi-day orchestrator simulation."""
    days: int = Field(30, ge=1, le=365, description="Number of days to simulate")
    mode: str = Field("dry_season", description="Season mode: dry_season or wet_season")
    waterBudget: float = Field(1200, ge=0, description="Daily water budget in liters")
    baseTemp: float = Field(28, description="Base temperature in Celsius")
    baseRain: float = Field(2.0, ge=0, description="Base daily rainfall in mm")
    variability: float = Field(2.0, ge=0, description="Weather variability factor")


class DayWeather(BaseModel):
    """Weather for a single day."""
    temp: float
    rain: float
    humidity: float


class DayResult(BaseModel):
    """Results for a single simulation day."""
    day: int
    waterApplied: float
    tankLevel: float
    stressEvents: int
    yieldProxy: float
    wue: float  # Water use efficiency
    weather: DayWeather
    plotMoisture: Dict[str, float]
    actions: List[Dict[str, Any]] = []
    alerts: List[str] = []


class SimulationAlert(BaseModel):
    """Alert generated during simulation."""
    day: int
    message: str
    severity: str  # "info", "warning", "critical"


class OrchestratorSimulationResult(BaseModel):
    """Complete multi-day orchestrator simulation result."""
    farmId: str
    config: OrchestratorConfig
    startedAt: str
    completedAt: str
    totalDays: int
    results: List[DayResult]
    alerts: List[SimulationAlert]
    summary: Dict[str, Any]


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
# Multi-Day Orchestrator Simulation
# ============================================================================

@app.post("/api/orchestrator/simulate", response_model=OrchestratorSimulationResult)
async def run_orchestrator_simulation(farm: FarmConfig, config: OrchestratorConfig):
    """
    Run multi-day orchestrator simulation.
    
    This simulates the farm over multiple days, running the orchestrator
    each day to make irrigation decisions, track yields, and detect issues.
    """
    started_at = datetime.now()
    
    # Convert FarmConfig to internal FarmState
    aez = lookup_aez_zone(farm.location.lat, farm.location.lng)
    
    # Create plots from crops
    plots = []
    for i, crop in enumerate(farm.crops):
        plots.append(PlotState(
            plot_id=f"P{i+1}",
            area_m2=crop.areaHa * 10000,  # Convert ha to m²
            crop_type=crop.type,
            crop_stage="vegetative",
            soil_moisture=0.40,  # Starting moisture
            aez_zone=aez["id"],
            day_of_season=1,
            cumulative_stress_days=0,
        ))
    
    # If no crops defined, create a default plot
    if not plots:
        plots.append(PlotState(
            plot_id="P1",
            area_m2=farm.areaHa * 10000 * 0.5,
            crop_type="maize",
            crop_stage="vegetative",
            soil_moisture=0.40,
            aez_zone=aez["id"],
            day_of_season=1,
            cumulative_stress_days=0,
        ))
    
    # Initial tank level based on water budget
    initial_tank = config.waterBudget * 10  # 10 days reserve
    
    # Initialize orchestrator
    orchestrator = FarmManagementOrchestrator()
    
    # Simulation state
    results: List[DayResult] = []
    alerts: List[SimulationAlert] = []
    tank_level = initial_tank
    cumulative_yield = 0.0
    total_water_used = 0.0
    total_stress = 0
    
    # Run simulation for each day
    for day in range(1, config.days + 1):
        # Generate weather for this day
        temp_variation = (random.random() - 0.5) * config.variability * 2
        rain_variation = (random.random() - 0.5) * config.variability * 2
        
        day_temp = config.baseTemp + temp_variation
        day_rain = max(0, config.baseRain + rain_variation)
        day_humidity = 55 + (random.random() - 0.5) * 20
        
        # Wet season has more rain
        if config.mode == "wet_season":
            day_rain *= 2.5
            day_humidity += 15
        
        weather = WeatherState(
            temperature_c=day_temp,
            humidity_pct=day_humidity,
            rainfall_mm=day_rain,
        )
        
        # Update plot moisture from rainfall
        for plot in plots:
            # Rain adds moisture, evaporation removes it
            rain_contribution = day_rain / 50  # ~2mm rain = 0.04 moisture
            evaporation = (day_temp - 20) / 200 + 0.02  # Higher temp = more evap
            plot.soil_moisture = max(0.1, min(0.7, plot.soil_moisture + rain_contribution - evaporation))
            plot.day_of_season = day
        
        # Refill tank from rain collection (simple model)
        rain_collection = day_rain * farm.areaHa * 100  # Simplified collection
        tank_level = min(initial_tank * 1.2, tank_level + rain_collection)
        
        # Create context for orchestrator
        farm_state = FarmState(
            timestamp=datetime(2026, 1, 1 + day, 6, 0, 0),
            plots=plots,
            water_system=WaterSystemState(
                tank_level_liters=tank_level,
                daily_supply_limit_liters=config.waterBudget,
                pump_capacity_lpm=70,
            ),
            weather=weather,
            kpis=KPIState(
                water_use_efficiency=total_water_used / max(1, cumulative_yield) if cumulative_yield > 0 else 0,
                crop_stress_events=total_stress,
                yield_estimate_tons_per_ha=cumulative_yield / max(1, len(plots)),
            ),
        )
        
        ctx = AgentContext(
            cycle_id=f"day-{day:03d}",
            mode=config.mode,
            farm_state=farm_state,
            budgets={"water_liters_day": config.waterBudget},
        )
        
        # Run orchestrator cycle
        try:
            cycle_result = orchestrator.run_cycle(ctx, out_file=f"/tmp/agrimesh_sim/day_{day:03d}.json")
        except Exception as e:
            # If orchestrator fails, use simple fallback
            cycle_result = {"action_queue": {}, "alerts": [str(e)], "observations": {}}
        
        # Process irrigation actions
        water_applied = 0.0
        day_actions = []
        
        action_queue = cycle_result.get("action_queue", {})
        for priority, actions in action_queue.items():
            for action in actions:
                if action.get("action_type") == "irrigate":
                    liters = float(action.get("params", {}).get("liters", 0))
                    plot_id = action.get("plot_id", "")
                    
                    # Apply irrigation
                    if tank_level >= liters:
                        water_applied += liters
                        tank_level -= liters
                        
                        # Update plot moisture
                        for plot in plots:
                            if plot.plot_id == plot_id:
                                plot.soil_moisture = min(0.65, plot.soil_moisture + liters / (plot.area_m2 * 10))
                        
                        day_actions.append({
                            "type": "irrigate",
                            "plot": plot_id,
                            "liters": liters,
                        })
        
        total_water_used += water_applied
        
        # Check for stress events
        day_stress = 0
        for plot in plots:
            # Stress if moisture too low
            critical_threshold = 0.25
            if plot.soil_moisture < critical_threshold:
                day_stress += 1
                plot.cumulative_stress_days += 1
        
        total_stress += day_stress
        
        # Calculate yield proxy (simplified model)
        # Yield increases daily based on moisture and stage
        base_growth = 0.02  # Base daily yield increment
        for plot in plots:
            moisture_factor = min(1.0, plot.soil_moisture / 0.4)  # Optimal at 0.4
            stress_penalty = max(0.5, 1 - plot.cumulative_stress_days * 0.02)
            stage_factor = min(1.0, plot.day_of_season / 60)  # Peak at 60 days
            
            daily_yield = base_growth * moisture_factor * stress_penalty * stage_factor
            cumulative_yield += daily_yield
        
        # Water use efficiency
        wue = cumulative_yield / max(1, total_water_used / 1000)  # kg/m³
        
        # Collect plot moisture
        plot_moisture = {plot.plot_id: round(plot.soil_moisture, 3) for plot in plots}
        
        # Generate alerts
        cycle_alerts = cycle_result.get("alerts", [])
        for alert_msg in cycle_alerts:
            alerts.append(SimulationAlert(
                day=day,
                message=alert_msg,
                severity="warning",
            ))
        
        # Temperature alert
        if day_temp > 35:
            alerts.append(SimulationAlert(
                day=day,
                message=f"Heat stress: {day_temp:.1f}°C",
                severity="warning",
            ))
        
        # Low moisture alert
        for plot in plots:
            if plot.soil_moisture < 0.2:
                alerts.append(SimulationAlert(
                    day=day,
                    message=f"Critical moisture in {plot.plot_id}: {plot.soil_moisture:.0%}",
                    severity="critical",
                ))
        
        # Low tank alert
        if tank_level < config.waterBudget * 2:
            alerts.append(SimulationAlert(
                day=day,
                message=f"Low water reserves: {tank_level:.0f}L remaining",
                severity="warning",
            ))
        
        # Record day result
        results.append(DayResult(
            day=day,
            waterApplied=round(water_applied, 1),
            tankLevel=round(tank_level, 1),
            stressEvents=day_stress,
            yieldProxy=round(cumulative_yield, 3),
            wue=round(wue, 3),
            weather=DayWeather(
                temp=round(day_temp, 1),
                rain=round(day_rain, 1),
                humidity=round(day_humidity, 1),
            ),
            plotMoisture=plot_moisture,
            actions=day_actions,
            alerts=[a.message for a in alerts if a.day == day],
        ))
    
    completed_at = datetime.now()
    
    # Summary statistics
    summary = {
        "totalWaterUsed": round(total_water_used, 1),
        "totalStressEvents": total_stress,
        "finalYield": round(cumulative_yield, 3),
        "avgWUE": round(total_water_used / max(1, cumulative_yield) if cumulative_yield > 0 else 0, 2),
        "finalTankLevel": round(tank_level, 1),
        "avgDailyWater": round(total_water_used / config.days, 1),
        "rainyDays": sum(1 for r in results if r.weather.rain > 1),
        "hotDays": sum(1 for r in results if r.weather.temp > 32),
        "criticalAlerts": sum(1 for a in alerts if a.severity == "critical"),
    }
    
    return OrchestratorSimulationResult(
        farmId=farm.id,
        config=config,
        startedAt=started_at.isoformat(),
        completedAt=completed_at.isoformat(),
        totalDays=config.days,
        results=results,
        alerts=alerts,
        summary=summary,
    )


# ============================================================================
# Run with Uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
