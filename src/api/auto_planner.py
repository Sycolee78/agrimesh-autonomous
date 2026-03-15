"""
Automatic Farm Planner

Given only coordinates and optional land size, automatically generates
a complete optimal farm plan with all decisions explained.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Coordinates:
    lat: float
    lng: float


@dataclass
class ClimateProfile:
    annual_rainfall_mm: float
    avg_temp_c: float
    rainy_season_months: List[str]
    dry_season_months: List[str]
    drought_probability: float  # 0-1
    frost_risk: bool
    growing_days: int


@dataclass
class SoilProfile:
    type: str
    ph: float
    organic_matter: str  # low/medium/high
    drainage: str  # poor/moderate/good
    fertility: str  # low/medium/high


@dataclass
class WaterAssessment:
    groundwater_depth_m: float
    borehole_feasibility: str  # excellent/good/moderate/poor
    river_proximity_km: float
    dam_feasibility: bool
    rainwater_potential_liters: float


@dataclass
class AEZInfo:
    zone_id: str
    zone_name: str
    rainfall_range: str
    description: str
    suitable_crops: List[str]
    livestock_capacity: Dict[str, float]


@dataclass
class CropAllocation:
    crop: str
    area_ha: float
    expected_yield_t: float
    revenue_usd: float
    water_need_mm: float
    reason: str


@dataclass
class LivestockAllocation:
    type: str
    count: int
    revenue_usd: float
    feed_requirement_kg_year: float
    water_requirement_l_day: float
    reason: str


@dataclass
class Building:
    type: str
    size_m2: float
    position: Coordinates
    cost_usd: float
    reason: str


@dataclass
class FarmZone:
    id: str
    type: str  # crops/pasture/buildings/water
    polygon: List[Coordinates]
    label: str
    area_ha: float
    color: str


@dataclass
class IntegrationLoop:
    source: str
    target: str
    flow: str
    annual_value_usd: float
    description: str


@dataclass
class ProfitProjection:
    year: int
    revenue_usd: float
    costs_usd: float
    profit_usd: float
    scenario: str  # best/expected/worst


@dataclass
class RiskAssessment:
    overall_risk_index: float  # 0-100, lower is better
    climate_risk: float
    market_risk: float
    water_risk: float
    factors: List[str]


@dataclass
class SustainabilityScore:
    overall: float  # 0-100
    water_efficiency: float
    soil_health: float
    biodiversity: float
    carbon_footprint: float
    circular_economy: float


@dataclass
class DecisionExplanation:
    category: str
    decision: str
    reasoning: str
    alternatives_considered: List[str]
    confidence: float


@dataclass
class AutoFarmPlan:
    id: str
    generated_at: str
    location: Coordinates
    area_ha: float
    
    # Environmental Analysis
    aez: AEZInfo
    climate: ClimateProfile
    soil: SoilProfile
    water: WaterAssessment
    
    # Farm Plan
    crops: List[CropAllocation]
    livestock: List[LivestockAllocation]
    buildings: List[Building]
    zones: List[FarmZone]
    integration_loops: List[IntegrationLoop]
    
    # Projections
    profit_projections: List[ProfitProjection]
    risk_assessment: RiskAssessment
    sustainability: SustainabilityScore
    
    # Explanations
    explanations: List[DecisionExplanation]
    
    # Summary
    summary: Dict[str, Any]


# ============================================================================
# AEZ Database
# ============================================================================

AEZ_DATA = {
    "I": {
        "zone_id": "I",
        "zone_name": "Specialized & Diversified Farming",
        "rainfall_range": ">1000mm",
        "description": "High rainfall, suitable for intensive farming, horticulture, and dairy",
        "suitable_crops": ["maize", "vegetables", "potatoes", "tobacco", "wheat", "tea", "coffee", "fruits"],
        "livestock_capacity": {"cattle": 1.5, "goats": 3, "sheep": 2, "chickens": 100, "pigs": 5},
    },
    "IIa": {
        "zone_id": "IIa",
        "zone_name": "Intensive Farming (High)",
        "rainfall_range": "800-1000mm",
        "description": "Good rainfall, prime agricultural land for crops and mixed farming",
        "suitable_crops": ["maize", "sorghum", "groundnuts", "cotton", "tobacco", "soybeans", "sunflower"],
        "livestock_capacity": {"cattle": 1.2, "goats": 2.5, "sheep": 1.5, "chickens": 80, "pigs": 4},
    },
    "IIb": {
        "zone_id": "IIb",
        "zone_name": "Intensive Farming (Low)",
        "rainfall_range": "750-800mm",
        "description": "Moderate-high rainfall, good for maize and cotton with some risk",
        "suitable_crops": ["maize", "sorghum", "groundnuts", "cotton", "sunflower", "cowpeas"],
        "livestock_capacity": {"cattle": 1.0, "goats": 2, "sheep": 1.5, "chickens": 70, "pigs": 3},
    },
    "III": {
        "zone_id": "III",
        "zone_name": "Semi-Intensive Farming",
        "rainfall_range": "650-800mm",
        "description": "Semi-arid, requires drought-tolerant varieties and mixed farming",
        "suitable_crops": ["sorghum", "millet", "groundnuts", "cowpeas", "fodder", "maize_drought_tolerant"],
        "livestock_capacity": {"cattle": 0.8, "goats": 2, "sheep": 1.2, "chickens": 60, "pigs": 2},
    },
    "IV": {
        "zone_id": "IV",
        "zone_name": "Semi-Extensive Farming",
        "rainfall_range": "450-650mm",
        "description": "Low rainfall, livestock-focused with limited cropping",
        "suitable_crops": ["sorghum", "millet", "fodder", "drought_resistant_vegetables"],
        "livestock_capacity": {"cattle": 0.5, "goats": 1.5, "sheep": 1, "chickens": 40, "pigs": 1},
    },
    "V": {
        "zone_id": "V",
        "zone_name": "Extensive Farming",
        "rainfall_range": "<500mm",
        "description": "Very low rainfall, suitable only for ranching and wildlife",
        "suitable_crops": ["fodder"],
        "livestock_capacity": {"cattle": 0.3, "goats": 1, "sheep": 0.5, "chickens": 20, "pigs": 0.5},
    },
}

# ============================================================================
# Crop Economics Database
# ============================================================================

CROP_DATA = {
    "maize": {"yield_t_ha": 5.5, "price_usd_t": 250, "water_mm": 500, "labor_days_ha": 45, "input_cost_ha": 400},
    "sorghum": {"yield_t_ha": 3.5, "price_usd_t": 200, "water_mm": 350, "labor_days_ha": 35, "input_cost_ha": 250},
    "groundnuts": {"yield_t_ha": 2.0, "price_usd_t": 800, "water_mm": 450, "labor_days_ha": 50, "input_cost_ha": 350},
    "vegetables": {"yield_t_ha": 15.0, "price_usd_t": 400, "water_mm": 600, "labor_days_ha": 120, "input_cost_ha": 800},
    "potatoes": {"yield_t_ha": 25.0, "price_usd_t": 200, "water_mm": 550, "labor_days_ha": 80, "input_cost_ha": 600},
    "tobacco": {"yield_t_ha": 2.5, "price_usd_t": 4500, "water_mm": 500, "labor_days_ha": 150, "input_cost_ha": 1500},
    "cotton": {"yield_t_ha": 3.0, "price_usd_t": 600, "water_mm": 450, "labor_days_ha": 60, "input_cost_ha": 400},
    "fodder": {"yield_t_ha": 8.0, "price_usd_t": 80, "water_mm": 400, "labor_days_ha": 25, "input_cost_ha": 150},
    "sunflower": {"yield_t_ha": 2.5, "price_usd_t": 450, "water_mm": 400, "labor_days_ha": 35, "input_cost_ha": 300},
    "soybeans": {"yield_t_ha": 2.8, "price_usd_t": 500, "water_mm": 450, "labor_days_ha": 40, "input_cost_ha": 350},
    "millet": {"yield_t_ha": 2.0, "price_usd_t": 180, "water_mm": 300, "labor_days_ha": 30, "input_cost_ha": 180},
    "cowpeas": {"yield_t_ha": 1.5, "price_usd_t": 600, "water_mm": 350, "labor_days_ha": 40, "input_cost_ha": 200},
}

LIVESTOCK_DATA = {
    "cattle": {"revenue_head_year": 800, "feed_kg_day": 12, "water_l_day": 50, "purchase_cost": 600},
    "goats": {"revenue_head_year": 150, "feed_kg_day": 2, "water_l_day": 5, "purchase_cost": 80},
    "sheep": {"revenue_head_year": 120, "feed_kg_day": 1.5, "water_l_day": 4, "purchase_cost": 70},
    "chickens": {"revenue_head_year": 15, "feed_kg_day": 0.12, "water_l_day": 0.25, "purchase_cost": 5},
    "pigs": {"revenue_head_year": 200, "feed_kg_day": 3, "water_l_day": 8, "purchase_cost": 100},
}


# ============================================================================
# Core Planner Class
# ============================================================================

class AutoFarmPlanner:
    """Automatic farm planner that generates optimal plans from coordinates."""
    
    def __init__(self):
        self.rng = random.Random(42)
    
    def plan(self, lat: float, lng: float, area_ha: float = 7.0) -> AutoFarmPlan:
        """Generate complete farm plan from coordinates."""
        
        # Step 1: Environmental Analysis
        aez = self._detect_aez(lat, lng)
        climate = self._analyze_climate(lat, lng, aez)
        soil = self._analyze_soil(lat, lng, aez)
        water = self._assess_water(lat, lng, climate)
        
        # Step 2: Generate Optimal Allocations
        crops, crop_explanations = self._plan_crops(area_ha, aez, climate, soil)
        livestock, livestock_explanations = self._plan_livestock(area_ha, aez, climate, crops)
        buildings, building_explanations = self._plan_buildings(area_ha, crops, livestock, water)
        
        # Step 3: Generate Zones for Visualization
        zones = self._generate_zones(lat, lng, area_ha, crops, livestock, buildings)
        
        # Step 4: Calculate Integration Loops
        integration = self._calculate_integration(crops, livestock)
        
        # Step 5: Financial Projections
        projections = self._project_profits(crops, livestock, integration, climate)
        
        # Step 6: Risk & Sustainability Assessment
        risk = self._assess_risk(climate, water, crops)
        sustainability = self._calculate_sustainability(crops, livestock, integration, water)
        
        # Compile explanations
        explanations = crop_explanations + livestock_explanations + building_explanations
        
        # Generate summary
        summary = self._generate_summary(crops, livestock, projections, sustainability)
        
        return AutoFarmPlan(
            id=f"farm-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now().isoformat(),
            location=Coordinates(lat=lat, lng=lng),
            area_ha=area_ha,
            aez=AEZInfo(**aez),
            climate=climate,
            soil=soil,
            water=water,
            crops=crops,
            livestock=livestock,
            buildings=buildings,
            zones=zones,
            integration_loops=integration,
            profit_projections=projections,
            risk_assessment=risk,
            sustainability=sustainability,
            explanations=explanations,
            summary=summary,
        )
    
    def _detect_aez(self, lat: float, lng: float) -> Dict:
        """Detect agro-ecological zone from coordinates."""
        # Zimbabwe AEZ approximation
        if lat > -18 and lng > 31:
            return AEZ_DATA["I"]
        elif lat > -18.5:
            return AEZ_DATA["IIa"]
        elif lat > -19.5 and lng > 29:
            return AEZ_DATA["IIb"]
        elif lat > -20.5:
            return AEZ_DATA["III"]
        elif lng < 27:
            return AEZ_DATA["V"]
        else:
            return AEZ_DATA["IV"]
    
    def _analyze_climate(self, lat: float, lng: float, aez: Dict) -> ClimateProfile:
        """Analyze climate profile for location."""
        rainfall_map = {"I": 1100, "IIa": 900, "IIb": 780, "III": 700, "IV": 550, "V": 400}
        base_rainfall = rainfall_map.get(aez["zone_id"], 700)
        
        # Add some variation based on exact location
        rainfall = base_rainfall + (lng - 29) * 15 + self.rng.uniform(-50, 50)
        
        drought_prob = 0.1 if rainfall > 900 else 0.2 if rainfall > 700 else 0.35 if rainfall > 500 else 0.5
        
        return ClimateProfile(
            annual_rainfall_mm=round(rainfall),
            avg_temp_c=round(22 + (abs(lat) - 18) * 0.5 + self.rng.uniform(-1, 1), 1),
            rainy_season_months=["November", "December", "January", "February", "March"],
            dry_season_months=["May", "June", "July", "August", "September"],
            drought_probability=round(drought_prob, 2),
            frost_risk=aez["zone_id"] == "I" and lat > -18,
            growing_days=int(rainfall / 5),
        )
    
    def _analyze_soil(self, lat: float, lng: float, aez: Dict) -> SoilProfile:
        """Analyze soil profile for location."""
        soil_types = {
            "I": ("Red clay loam", 5.8, "high", "moderate", "high"),
            "IIa": ("Sandy loam", 6.0, "medium", "good", "medium"),
            "IIb": ("Sandy clay loam", 5.9, "medium", "good", "medium"),
            "III": ("Sandy loam", 6.2, "medium", "good", "low"),
            "IV": ("Sandy soil", 6.5, "low", "good", "low"),
            "V": ("Kalahari sand", 7.0, "low", "good", "low"),
        }
        
        soil_info = soil_types.get(aez["zone_id"], soil_types["III"])
        
        return SoilProfile(
            type=soil_info[0],
            ph=soil_info[1] + self.rng.uniform(-0.3, 0.3),
            organic_matter=soil_info[2],
            drainage=soil_info[3],
            fertility=soil_info[4],
        )
    
    def _assess_water(self, lat: float, lng: float, climate: ClimateProfile) -> WaterAssessment:
        """Assess water availability and infrastructure feasibility."""
        # Estimate based on rainfall and location
        groundwater_depth = 15 + (800 - climate.annual_rainfall_mm) / 20
        
        if groundwater_depth < 20:
            borehole = "excellent"
        elif groundwater_depth < 35:
            borehole = "good"
        elif groundwater_depth < 50:
            borehole = "moderate"
        else:
            borehole = "poor"
        
        # Simplified river proximity (would use real GIS data)
        river_km = 5 + self.rng.uniform(0, 20)
        
        # Rainwater harvesting potential
        roof_area_m2 = 200  # Assumed buildings
        rainwater_l = climate.annual_rainfall_mm * roof_area_m2 * 0.8  # 80% collection efficiency
        
        return WaterAssessment(
            groundwater_depth_m=round(groundwater_depth, 1),
            borehole_feasibility=borehole,
            river_proximity_km=round(river_km, 1),
            dam_feasibility=climate.annual_rainfall_mm > 600 and river_km < 10,
            rainwater_potential_liters=round(rainwater_l),
        )
    
    def _plan_crops(
        self, 
        area_ha: float, 
        aez: Dict, 
        climate: ClimateProfile, 
        soil: SoilProfile
    ) -> Tuple[List[CropAllocation], List[DecisionExplanation]]:
        """Plan optimal crop portfolio."""
        explanations = []
        crops = []
        
        # Reserve land for livestock and buildings
        crop_area = area_ha * 0.6  # 60% for crops
        remaining_area = crop_area
        
        suitable_crops = aez["suitable_crops"]
        
        # Score each crop
        crop_scores = []
        for crop_name in suitable_crops:
            if crop_name not in CROP_DATA:
                continue
            
            data = CROP_DATA[crop_name]
            
            # Calculate score based on multiple factors
            water_score = 1.0 if data["water_mm"] <= climate.annual_rainfall_mm * 0.8 else 0.6
            profit_per_ha = data["yield_t_ha"] * data["price_usd_t"] - data["input_cost_ha"]
            profit_score = profit_per_ha / 2000  # Normalize
            
            # Soil suitability
            soil_score = 1.0 if soil.fertility == "high" else 0.8 if soil.fertility == "medium" else 0.6
            
            # Risk adjustment
            risk_score = 1.0 - climate.drought_probability * 0.5
            
            total_score = (water_score * 0.3 + profit_score * 0.4 + soil_score * 0.15 + risk_score * 0.15)
            
            crop_scores.append((crop_name, total_score, profit_per_ha, data))
        
        # Sort by score and allocate
        crop_scores.sort(key=lambda x: x[1], reverse=True)
        
        for crop_name, score, profit, data in crop_scores[:4]:  # Top 4 crops
            if remaining_area <= 0:
                break
            
            # Allocate based on score (higher score = more area)
            allocation = min(remaining_area, crop_area * (score / sum(s[1] for s in crop_scores[:4])))
            allocation = round(allocation, 1)
            
            if allocation < 0.5:
                continue
            
            expected_yield = data["yield_t_ha"] * allocation * (1 - climate.drought_probability * 0.3)
            revenue = expected_yield * data["price_usd_t"]
            
            reason = f"Ranked #{crop_scores.index((crop_name, score, profit, data)) + 1} for this zone. "
            reason += f"Water needs ({data['water_mm']}mm) match rainfall ({climate.annual_rainfall_mm}mm). "
            reason += f"Expected profit: ${int(profit)}/ha."
            
            crops.append(CropAllocation(
                crop=crop_name,
                area_ha=allocation,
                expected_yield_t=round(expected_yield, 1),
                revenue_usd=round(revenue),
                water_need_mm=data["water_mm"],
                reason=reason,
            ))
            
            remaining_area -= allocation
            
            explanations.append(DecisionExplanation(
                category="Crops",
                decision=f"Allocate {allocation} ha to {crop_name}",
                reasoning=reason,
                alternatives_considered=[c[0] for c in crop_scores if c[0] != crop_name][:3],
                confidence=min(0.95, score),
            ))
        
        # Add legume if not present (for nitrogen fixation)
        has_legume = any(c.crop in ["groundnuts", "soybeans", "cowpeas"] for c in crops)
        if not has_legume and remaining_area >= 0.5:
            legume = "groundnuts" if "groundnuts" in suitable_crops else "cowpeas"
            if legume in CROP_DATA:
                data = CROP_DATA[legume]
                allocation = min(remaining_area, 1.0)
                
                crops.append(CropAllocation(
                    crop=legume,
                    area_ha=allocation,
                    expected_yield_t=round(data["yield_t_ha"] * allocation, 1),
                    revenue_usd=round(data["yield_t_ha"] * allocation * data["price_usd_t"]),
                    water_need_mm=data["water_mm"],
                    reason="Added for nitrogen fixation - reduces fertilizer needs by 30-40%.",
                ))
                
                explanations.append(DecisionExplanation(
                    category="Crops",
                    decision=f"Add {allocation} ha of {legume} for nitrogen fixation",
                    reasoning="Legumes fix atmospheric nitrogen, reducing fertilizer costs and improving soil health",
                    alternatives_considered=["chemical fertilizers", "crop rotation without legumes"],
                    confidence=0.9,
                ))
        
        return crops, explanations
    
    def _plan_livestock(
        self,
        area_ha: float,
        aez: Dict,
        climate: ClimateProfile,
        crops: List[CropAllocation]
    ) -> Tuple[List[LivestockAllocation], List[DecisionExplanation]]:
        """Plan optimal livestock composition."""
        explanations = []
        livestock = []
        
        # Pasture area (30% of farm)
        pasture_ha = area_ha * 0.3
        
        # Get livestock capacity from AEZ
        capacity = aez["livestock_capacity"]
        
        # Calculate how much fodder/residues we have from crops
        crop_residue_t = sum(c.expected_yield_t * 1.5 for c in crops if c.crop in ["maize", "sorghum", "millet"])
        fodder_t = sum(c.expected_yield_t for c in crops if c.crop == "fodder")
        
        total_feed_available = (crop_residue_t + fodder_t) * 1000  # Convert to kg
        
        # Always include chickens (low risk, quick returns)
        chicken_count = min(int(capacity.get("chickens", 50) * pasture_ha * 0.3), 100)
        if chicken_count >= 20:
            data = LIVESTOCK_DATA["chickens"]
            livestock.append(LivestockAllocation(
                type="chickens",
                count=chicken_count,
                revenue_usd=round(chicken_count * data["revenue_head_year"]),
                feed_requirement_kg_year=round(chicken_count * data["feed_kg_day"] * 365),
                water_requirement_l_day=round(chicken_count * data["water_l_day"]),
                reason="Low investment, quick returns, provide eggs and meat. Manure excellent for crops.",
            ))
            
            explanations.append(DecisionExplanation(
                category="Livestock",
                decision=f"Keep {chicken_count} chickens",
                reasoning="Chickens have fastest ROI, provide pest control, and manure for fertilizer",
                alternatives_considered=["ducks", "guinea fowl"],
                confidence=0.9,
            ))
        
        # Add cattle or goats based on zone
        if capacity.get("cattle", 0) >= 0.5 and pasture_ha >= 2:
            cattle_count = min(int(capacity["cattle"] * pasture_ha), 10)
            if cattle_count >= 2:
                data = LIVESTOCK_DATA["cattle"]
                livestock.append(LivestockAllocation(
                    type="cattle",
                    count=cattle_count,
                    revenue_usd=round(cattle_count * data["revenue_head_year"]),
                    feed_requirement_kg_year=round(cattle_count * data["feed_kg_day"] * 365),
                    water_requirement_l_day=round(cattle_count * data["water_l_day"]),
                    reason=f"Zone {aez['zone_id']} supports {capacity['cattle']:.1f} cattle/ha. Provides draught power, milk, manure.",
                ))
                
                explanations.append(DecisionExplanation(
                    category="Livestock",
                    decision=f"Keep {cattle_count} cattle",
                    reasoning=f"AEZ {aez['zone_id']} carrying capacity supports this. Cattle provide multiple income streams.",
                    alternatives_considered=["more goats", "sheep", "no cattle"],
                    confidence=0.85,
                ))
        
        # Add goats (hardy, good for all zones)
        goat_capacity = capacity.get("goats", 1) * pasture_ha
        goat_count = min(int(goat_capacity * 0.5), 20)
        if goat_count >= 5:
            data = LIVESTOCK_DATA["goats"]
            livestock.append(LivestockAllocation(
                type="goats",
                count=goat_count,
                revenue_usd=round(goat_count * data["revenue_head_year"]),
                feed_requirement_kg_year=round(goat_count * data["feed_kg_day"] * 365),
                water_requirement_l_day=round(goat_count * data["water_l_day"]),
                reason="Hardy, drought-tolerant, browse on vegetation cattle won't eat. Good for meat and milk.",
            ))
            
            explanations.append(DecisionExplanation(
                category="Livestock",
                decision=f"Keep {goat_count} goats",
                reasoning="Goats are drought-tolerant and utilize browse vegetation, complementing cattle",
                alternatives_considered=["sheep", "more cattle"],
                confidence=0.85,
            ))
        
        return livestock, explanations
    
    def _plan_buildings(
        self,
        area_ha: float,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation],
        water: WaterAssessment
    ) -> Tuple[List[Building], List[DecisionExplanation]]:
        """Plan farm infrastructure."""
        explanations = []
        buildings = []
        
        # Calculate storage needs
        total_crop_yield = sum(c.expected_yield_t for c in crops)
        storage_m2_needed = total_crop_yield * 3  # 3 m² per tonne
        
        # Main storage barn
        if storage_m2_needed > 0:
            buildings.append(Building(
                type="storage_barn",
                size_m2=max(50, round(storage_m2_needed)),
                position=Coordinates(lat=0, lng=0),  # Will be placed in zone generation
                cost_usd=int(storage_m2_needed * 50),
                reason=f"Required for {total_crop_yield:.1f} tonnes of produce. Protects harvest from pests and weather.",
            ))
        
        # Livestock housing
        has_chickens = any(l.type == "chickens" for l in livestock)
        has_cattle = any(l.type == "cattle" for l in livestock)
        
        if has_chickens:
            chicken_count = next(l.count for l in livestock if l.type == "chickens")
            buildings.append(Building(
                type="poultry_house",
                size_m2=max(20, int(chicken_count * 0.3)),
                position=Coordinates(lat=0, lng=0),
                cost_usd=int(chicken_count * 15),
                reason="Protects chickens from predators, improves egg production by 20-30%.",
            ))
        
        if has_cattle:
            buildings.append(Building(
                type="cattle_kraal",
                size_m2=100,
                position=Coordinates(lat=0, lng=0),
                cost_usd=2000,
                reason="Night shelter, protects from theft and predators, enables manure collection.",
            ))
        
        # Water infrastructure
        if water.borehole_feasibility in ["excellent", "good"]:
            buildings.append(Building(
                type="borehole",
                size_m2=4,
                position=Coordinates(lat=0, lng=0),
                cost_usd=5000 if water.borehole_feasibility == "excellent" else 8000,
                reason=f"Groundwater at {water.groundwater_depth_m}m - {water.borehole_feasibility} feasibility. Year-round water security.",
            ))
            
            explanations.append(DecisionExplanation(
                category="Infrastructure",
                decision="Install borehole",
                reasoning=f"Groundwater depth ({water.groundwater_depth_m}m) makes drilling feasible",
                alternatives_considered=["rainwater only", "river abstraction", "dam"],
                confidence=0.9 if water.borehole_feasibility == "excellent" else 0.75,
            ))
        
        # Water storage tanks
        buildings.append(Building(
            type="water_tank",
            size_m2=10,
            position=Coordinates(lat=0, lng=0),
            cost_usd=1500,
            reason=f"Stores {water.rainwater_potential_liters:,}L rainwater potential. Critical for dry season.",
        ))
        
        return buildings, explanations
    
    def _generate_zones(
        self,
        lat: float,
        lng: float,
        area_ha: float,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation],
        buildings: List[Building]
    ) -> List[FarmZone]:
        """Generate visual zones for map display."""
        zones = []
        
        # Calculate farm boundary (approximate rectangle)
        # 1 hectare ≈ 100m x 100m, so sqrt(area_ha) * 100m per side
        side_m = math.sqrt(area_ha) * 100
        side_deg = side_m / 111000  # Approximate meters to degrees
        
        # Farm boundary
        farm_boundary = [
            Coordinates(lat=lat - side_deg/2, lng=lng - side_deg/2),
            Coordinates(lat=lat - side_deg/2, lng=lng + side_deg/2),
            Coordinates(lat=lat + side_deg/2, lng=lng + side_deg/2),
            Coordinates(lat=lat + side_deg/2, lng=lng - side_deg/2),
        ]
        
        zones.append(FarmZone(
            id="boundary",
            type="boundary",
            polygon=farm_boundary,
            label="Farm Boundary",
            area_ha=area_ha,
            color="#333333",
        ))
        
        # Divide into crop zones (left side)
        crop_offset = 0
        for i, crop in enumerate(crops):
            crop_height = (crop.area_ha / sum(c.area_ha for c in crops)) * side_deg * 0.6
            
            zone = FarmZone(
                id=f"crop-{crop.crop}",
                type="crops",
                polygon=[
                    Coordinates(lat=lat - side_deg/2 + crop_offset, lng=lng - side_deg/2),
                    Coordinates(lat=lat - side_deg/2 + crop_offset, lng=lng),
                    Coordinates(lat=lat - side_deg/2 + crop_offset + crop_height, lng=lng),
                    Coordinates(lat=lat - side_deg/2 + crop_offset + crop_height, lng=lng - side_deg/2),
                ],
                label=f"{crop.crop.title()} ({crop.area_ha} ha)",
                area_ha=crop.area_ha,
                color="#22c55e",
            )
            zones.append(zone)
            crop_offset += crop_height
        
        # Pasture zone (right side)
        pasture_ha = area_ha * 0.3
        zones.append(FarmZone(
            id="pasture",
            type="pasture",
            polygon=[
                Coordinates(lat=lat - side_deg/2, lng=lng),
                Coordinates(lat=lat - side_deg/2, lng=lng + side_deg/2),
                Coordinates(lat=lat + side_deg/4, lng=lng + side_deg/2),
                Coordinates(lat=lat + side_deg/4, lng=lng),
            ],
            label=f"Pasture ({pasture_ha:.1f} ha)",
            area_ha=pasture_ha,
            color="#eab308",
        ))
        
        # Building zone (top right corner)
        zones.append(FarmZone(
            id="buildings",
            type="buildings",
            polygon=[
                Coordinates(lat=lat + side_deg/4, lng=lng),
                Coordinates(lat=lat + side_deg/4, lng=lng + side_deg/2),
                Coordinates(lat=lat + side_deg/2, lng=lng + side_deg/2),
                Coordinates(lat=lat + side_deg/2, lng=lng),
            ],
            label="Buildings & Homestead",
            area_ha=area_ha * 0.1,
            color="#64748b",
        ))
        
        return zones
    
    def _calculate_integration(
        self,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation]
    ) -> List[IntegrationLoop]:
        """Calculate circular economy integration loops."""
        loops = []
        
        # Manure to fertilizer
        total_manure_kg = 0
        for l in livestock:
            if l.type == "cattle":
                total_manure_kg += l.count * 12 * 365 * 0.4  # 40% of feed becomes manure
            elif l.type == "chickens":
                total_manure_kg += l.count * 0.12 * 365 * 0.5
            elif l.type == "goats":
                total_manure_kg += l.count * 2 * 365 * 0.4
        
        if total_manure_kg > 0:
            crop_area = sum(c.area_ha for c in crops)
            fertilizer_saved = min(total_manure_kg / 1000 * 30, crop_area * 150 * 0.4)  # Up to 40% savings
            value = fertilizer_saved * 0.8  # $0.80/kg fertilizer
            
            loops.append(IntegrationLoop(
                source="Livestock manure",
                target="Crop fertilization",
                flow=f"{int(total_manure_kg):,} kg manure/year",
                annual_value_usd=round(value),
                description=f"Replaces {int(fertilizer_saved)} kg of chemical fertilizer, saving ${int(value)}/year",
            ))
        
        # Crop residues to feed
        crop_residue_kg = sum(c.expected_yield_t * 1500 for c in crops if c.crop in ["maize", "sorghum", "millet"])
        livestock_feed_need = sum(l.feed_requirement_kg_year for l in livestock)
        
        if crop_residue_kg > 0 and livestock_feed_need > 0:
            feed_replaced = min(crop_residue_kg, livestock_feed_need * 0.3)  # Up to 30% of diet
            value = feed_replaced * 0.15  # $0.15/kg feed
            
            loops.append(IntegrationLoop(
                source="Crop residues",
                target="Livestock feed",
                flow=f"{int(feed_replaced):,} kg/year",
                annual_value_usd=round(value),
                description=f"Maize/sorghum stover provides {int(feed_replaced/livestock_feed_need*100)}% of livestock feed",
            ))
        
        # Chickens for pest control
        has_chickens = any(l.type == "chickens" and l.count >= 30 for l in livestock)
        crop_area = sum(c.area_ha for c in crops)
        
        if has_chickens and crop_area > 0:
            pesticide_saved = crop_area * 50 * 0.25  # 25% less pesticide, $50/ha typical
            
            loops.append(IntegrationLoop(
                source="Free-range chickens",
                target="Pest control",
                flow="Natural pest management",
                annual_value_usd=round(pesticide_saved),
                description="Chickens consume insects and grubs, reducing pesticide needs by 20-30%",
            ))
        
        # Legumes for nitrogen fixation
        legume_area = sum(c.area_ha for c in crops if c.crop in ["groundnuts", "soybeans", "cowpeas"])
        if legume_area > 0:
            n_fixed = legume_area * 50  # ~50 kg N/ha
            value = n_fixed * 1.2  # $1.20/kg N
            
            loops.append(IntegrationLoop(
                source="Legume crops",
                target="Soil nitrogen",
                flow=f"{int(n_fixed)} kg N/year",
                annual_value_usd=round(value),
                description="Biological nitrogen fixation reduces fertilizer needs for following crops",
            ))
        
        return loops
    
    def _project_profits(
        self,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation],
        integration: List[IntegrationLoop],
        climate: ClimateProfile
    ) -> List[ProfitProjection]:
        """Generate 3-year profit projections with scenarios."""
        projections = []
        
        integration_value = sum(i.annual_value_usd for i in integration)
        
        for year in range(1, 4):
            # Calculate base revenue
            crop_revenue = sum(c.revenue_usd for c in crops)
            livestock_revenue = sum(l.revenue_usd for l in livestock)
            
            # Growth factors
            year_factor = 1 + (year - 1) * 0.05  # 5% improvement per year as systems mature
            
            # Calculate costs
            crop_costs = sum(c.area_ha * 400 for c in crops)  # Average $400/ha
            livestock_costs = sum(l.feed_requirement_kg_year * 0.2 for l in livestock)  # $0.20/kg feed
            
            for scenario, multiplier in [("best", 1.3), ("expected", 1.0), ("worst", 0.6)]:
                # Adjust for scenario
                if scenario == "worst":
                    revenue = (crop_revenue * 0.5 + livestock_revenue * 0.8) * year_factor
                    costs = (crop_costs + livestock_costs) * 1.1  # Higher costs in drought
                elif scenario == "best":
                    revenue = (crop_revenue * 1.2 + livestock_revenue * 1.1) * year_factor
                    costs = (crop_costs + livestock_costs) * 0.95
                else:
                    revenue = (crop_revenue + livestock_revenue) * year_factor
                    costs = crop_costs + livestock_costs
                
                # Add integration benefits
                revenue += integration_value * year_factor
                
                projections.append(ProfitProjection(
                    year=year,
                    revenue_usd=round(revenue),
                    costs_usd=round(costs),
                    profit_usd=round(revenue - costs),
                    scenario=scenario,
                ))
        
        return projections
    
    def _assess_risk(
        self,
        climate: ClimateProfile,
        water: WaterAssessment,
        crops: List[CropAllocation]
    ) -> RiskAssessment:
        """Assess overall risk profile."""
        factors = []
        
        # Climate risk
        climate_risk = climate.drought_probability * 80
        if climate_risk > 30:
            factors.append(f"Drought probability: {int(climate.drought_probability*100)}%")
        
        # Water risk
        if water.borehole_feasibility in ["moderate", "poor"]:
            water_risk = 60 if water.borehole_feasibility == "poor" else 40
            factors.append(f"Limited groundwater access")
        else:
            water_risk = 20
        
        # Market risk (simplified)
        market_risk = 25
        
        # Crop diversity reduces risk
        crop_diversity = len(crops)
        diversity_reduction = min(20, crop_diversity * 5)
        
        overall = (climate_risk * 0.4 + water_risk * 0.3 + market_risk * 0.3) - diversity_reduction
        overall = max(10, min(90, overall))
        
        return RiskAssessment(
            overall_risk_index=round(overall),
            climate_risk=round(climate_risk),
            market_risk=round(market_risk),
            water_risk=round(water_risk),
            factors=factors if factors else ["Risk profile within acceptable range"],
        )
    
    def _calculate_sustainability(
        self,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation],
        integration: List[IntegrationLoop],
        water: WaterAssessment
    ) -> SustainabilityScore:
        """Calculate sustainability metrics."""
        # Water efficiency
        total_water_need = sum(c.water_need_mm * c.area_ha * 10 for c in crops)  # m³
        water_eff = 80 if total_water_need < 5000 else 60 if total_water_need < 10000 else 40
        if water.borehole_feasibility in ["excellent", "good"]:
            water_eff += 10
        
        # Soil health
        has_legumes = any(c.crop in ["groundnuts", "soybeans", "cowpeas"] for c in crops)
        has_manure = any("manure" in i.source.lower() for i in integration)
        soil_health = 50 + (20 if has_legumes else 0) + (20 if has_manure else 0)
        
        # Biodiversity
        biodiversity = min(100, len(crops) * 15 + len(livestock) * 10)
        
        # Carbon footprint (lower is better, but we invert for score)
        cattle_count = sum(l.count for l in livestock if l.type == "cattle")
        carbon = max(0, 100 - cattle_count * 3)
        
        # Circular economy
        circular = min(100, len(integration) * 25)
        
        overall = (water_eff + soil_health + biodiversity + carbon + circular) / 5
        
        return SustainabilityScore(
            overall=round(overall),
            water_efficiency=round(water_eff),
            soil_health=round(min(100, soil_health)),
            biodiversity=round(biodiversity),
            carbon_footprint=round(carbon),
            circular_economy=round(circular),
        )
    
    def _generate_summary(
        self,
        crops: List[CropAllocation],
        livestock: List[LivestockAllocation],
        projections: List[ProfitProjection],
        sustainability: SustainabilityScore
    ) -> Dict[str, Any]:
        """Generate executive summary."""
        expected_y1 = next((p for p in projections if p.year == 1 and p.scenario == "expected"), None)
        expected_y3 = next((p for p in projections if p.year == 3 and p.scenario == "expected"), None)
        worst_y1 = next((p for p in projections if p.year == 1 and p.scenario == "worst"), None)
        best_y1 = next((p for p in projections if p.year == 1 and p.scenario == "best"), None)
        
        return {
            "total_crop_area_ha": round(sum(c.area_ha for c in crops), 1),
            "primary_crops": [c.crop for c in crops[:3]],
            "livestock_types": [l.type for l in livestock],
            "year_1_expected_profit": expected_y1.profit_usd if expected_y1 else 0,
            "year_1_range": f"${worst_y1.profit_usd:,} - ${best_y1.profit_usd:,}" if worst_y1 and best_y1 else "N/A",
            "year_3_expected_profit": expected_y3.profit_usd if expected_y3 else 0,
            "sustainability_score": sustainability.overall,
            "key_strength": "Diversified mixed farming with multiple income streams",
        }


# ============================================================================
# Singleton Instance
# ============================================================================

auto_planner = AutoFarmPlanner()


def generate_auto_plan(lat: float, lng: float, area_ha: float = 7.0) -> Dict:
    """Generate auto plan and return as dict."""
    plan = auto_planner.plan(lat, lng, area_ha)
    return asdict(plan)
