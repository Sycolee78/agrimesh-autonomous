"""
Geospatial Land Analysis Engine

Analyzes land coordinates to determine:
- AEZ zone classification
- Soil suitability
- Water access
- Terrain characteristics
- Market accessibility
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LandAnalysis:
    """Complete land analysis result."""
    lat: float
    lon: float
    area_ha: float
    
    # AEZ classification
    aez_zone: str
    aez_subzone: str
    
    # Climate
    annual_rainfall_mm: int
    rainfall_reliability: float  # 0-1
    temperature_range: Tuple[float, float]  # min, max annual avg
    growing_days: int
    frost_risk: str  # "none", "low", "moderate", "high"
    
    # Soil
    soil_type: str
    soil_fertility: str  # "poor", "moderate", "good", "excellent"
    soil_depth_cm: int
    drainage: str  # "poor", "moderate", "good", "excessive"
    
    # Terrain
    slope_percent: float
    terrain_classification: str
    erosion_risk: str
    
    # Water
    water_source: str
    water_reliability: str
    borehole_feasibility: str
    flood_risk: str
    
    # Access
    market_distance_km: float
    road_quality: str
    electricity_access: bool
    
    # Derived recommendations
    land_class: str  # "prime_arable", "semi_arable", "marginal", "pastoral", "non_agricultural"
    recommended_systems: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


# Zimbabwe AEZ boundaries (approximate lat/lon ranges)
# In production, this would use proper GIS data
ZIMBABWE_AEZ_ZONES = {
    "I": {
        "description": "Eastern Highlands - High rainfall",
        "rainfall_range": (1000, 1400),
        "growing_days": (180, 210),
        "regions": [
            {"lat_range": (-18.5, -17.5), "lon_range": (32.0, 33.0)},  # Nyanga
            {"lat_range": (-19.5, -18.5), "lon_range": (32.3, 33.0)},  # Mutare highlands
            {"lat_range": (-20.5, -19.5), "lon_range": (32.5, 33.0)},  # Chimanimani
        ],
        "soil_types": ["red_clay", "humic_soil"],
        "frost_risk": "moderate",
        "suitable_crops": ["tea", "coffee", "timber", "potatoes", "temperate_fruits", "vegetables", "maize"],
        "suitable_livestock": ["dairy_cattle", "sheep", "pigs"],
    },
    "IIa": {
        "description": "High rainfall areas",
        "rainfall_range": (800, 1000),
        "growing_days": (150, 180),
        "regions": [
            {"lat_range": (-18.5, -17.0), "lon_range": (30.5, 32.0)},  # Northern plateau
            {"lat_range": (-17.5, -16.5), "lon_range": (29.5, 31.0)},  # Mashonaland
        ],
        "soil_types": ["red_clay", "sandy_loam"],
        "frost_risk": "low",
        "suitable_crops": ["maize", "tobacco", "soybeans", "groundnuts", "wheat", "vegetables"],
        "suitable_livestock": ["beef_cattle", "dairy_cattle", "pigs", "poultry"],
    },
    "IIb": {
        "description": "Reliable rainfall areas",
        "rainfall_range": (700, 850),
        "growing_days": (140, 160),
        "regions": [
            {"lat_range": (-18.5, -17.0), "lon_range": (30.0, 32.0)},  # Harare region
            {"lat_range": (-19.5, -18.5), "lon_range": (29.5, 31.5)},  # Midlands north
        ],
        "soil_types": ["sandy_loam", "red_clay"],
        "frost_risk": "low",
        "suitable_crops": ["maize", "tobacco", "cotton", "groundnuts", "sorghum", "vegetables"],
        "suitable_livestock": ["beef_cattle", "goats", "poultry", "pigs"],
    },
    "III": {
        "description": "Semi-intensive farming region",
        "rainfall_range": (500, 700),
        "growing_days": (120, 140),
        "regions": [
            {"lat_range": (-20.5, -19.0), "lon_range": (29.0, 31.0)},  # Midlands south
            {"lat_range": (-21.0, -20.0), "lon_range": (29.5, 31.0)},  # Masvingo region
        ],
        "soil_types": ["sandy_loam", "sandy"],
        "frost_risk": "low",
        "suitable_crops": ["maize", "sorghum", "millet", "groundnuts", "cotton", "sunflower"],
        "suitable_livestock": ["beef_cattle", "goats", "sheep", "poultry"],
    },
    "IV": {
        "description": "Semi-extensive farming",
        "rainfall_range": (400, 550),
        "growing_days": (100, 120),
        "regions": [
            {"lat_range": (-20.5, -19.5), "lon_range": (28.0, 29.5)},  # Bulawayo region
            {"lat_range": (-22.0, -20.5), "lon_range": (28.5, 30.0)},  # Southern lowlands
        ],
        "soil_types": ["sandy", "kalahari_sand"],
        "frost_risk": "none",
        "suitable_crops": ["sorghum", "millet", "groundnuts", "drought_resistant_maize"],
        "suitable_livestock": ["beef_cattle", "goats", "sheep", "donkeys"],
    },
    "V": {
        "description": "Extensive farming - Low rainfall",
        "rainfall_range": (250, 450),
        "growing_days": (80, 100),
        "regions": [
            {"lat_range": (-17.5, -16.0), "lon_range": (28.0, 29.0)},  # Zambezi valley
            {"lat_range": (-22.5, -21.5), "lon_range": (29.0, 32.0)},  # Limpopo valley
            {"lat_range": (-18.5, -17.5), "lon_range": (25.0, 27.0)},  # Victoria Falls
        ],
        "soil_types": ["sandy", "alluvial", "vertisol"],
        "frost_risk": "none",
        "suitable_crops": ["sorghum", "millet", "fodder", "irrigated_vegetables"],
        "suitable_livestock": ["beef_cattle", "goats", "game_ranching"],
    },
}


# Market towns with coordinates
MARKET_CENTERS = [
    {"name": "Harare", "lat": -17.83, "lon": 31.05, "tier": 1},
    {"name": "Bulawayo", "lat": -20.15, "lon": 28.58, "tier": 1},
    {"name": "Mutare", "lat": -18.97, "lon": 32.67, "tier": 2},
    {"name": "Gweru", "lat": -19.45, "lon": 29.82, "tier": 2},
    {"name": "Masvingo", "lat": -20.06, "lon": 30.83, "tier": 2},
    {"name": "Chinhoyi", "lat": -17.37, "lon": 30.20, "tier": 3},
    {"name": "Marondera", "lat": -18.19, "lon": 31.55, "tier": 3},
    {"name": "Kwekwe", "lat": -18.93, "lon": 29.82, "tier": 3},
    {"name": "Kadoma", "lat": -18.33, "lon": 29.92, "tier": 3},
    {"name": "Chiredzi", "lat": -21.05, "lon": 31.67, "tier": 3},
    {"name": "Kariba", "lat": -16.52, "lon": 28.80, "tier": 3},
    {"name": "Victoria Falls", "lat": -17.93, "lon": 25.85, "tier": 3},
]


class GeospatialAnalyzer:
    """
    Analyzes land parcels to determine agricultural potential.
    """
    
    def __init__(self):
        self.aez_data = ZIMBABWE_AEZ_ZONES
        self.markets = MARKET_CENTERS
    
    def analyze(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        polygon: Optional[List[Tuple[float, float]]] = None,
    ) -> LandAnalysis:
        """
        Perform complete land analysis.
        
        Args:
            lat: Latitude (centroid if polygon provided)
            lon: Longitude (centroid if polygon provided)
            area_ha: Total area in hectares
            polygon: Optional polygon boundary [(lat, lon), ...]
        
        Returns:
            Complete LandAnalysis object
        """
        
        # Determine AEZ zone
        aez_zone, aez_subzone = self._determine_aez(lat, lon)
        zone_data = self.aez_data.get(aez_zone, self.aez_data["III"])
        
        # Get climate data
        rainfall = self._estimate_rainfall(lat, lon, zone_data)
        rainfall_reliability = self._calc_rainfall_reliability(aez_zone)
        temp_range = self._estimate_temperature(lat, lon, aez_zone)
        growing_days = self._estimate_growing_days(zone_data)
        frost_risk = zone_data.get("frost_risk", "low")
        
        # Soil analysis (simplified - would use actual soil maps)
        soil_type, soil_fertility, soil_depth = self._analyze_soil(lat, lon, aez_zone)
        drainage = self._estimate_drainage(soil_type, self._estimate_slope(lat, lon))
        
        # Terrain
        slope = self._estimate_slope(lat, lon)
        terrain_class = self._classify_terrain(slope, aez_zone)
        erosion_risk = self._assess_erosion_risk(slope, rainfall, soil_type)
        
        # Water
        water_source, water_reliability = self._assess_water(lat, lon, aez_zone)
        borehole_feasibility = self._assess_borehole(lat, lon, aez_zone)
        flood_risk = self._assess_flood_risk(lat, lon, slope)
        
        # Market access
        market_distance, road_quality = self._assess_market_access(lat, lon)
        electricity = self._check_electricity(lat, lon, market_distance)
        
        # Classification
        land_class = self._classify_land(
            aez_zone, slope, soil_fertility, water_reliability, rainfall
        )
        
        # Recommendations
        recommended_systems = self._recommend_systems(
            land_class, aez_zone, water_source, slope, area_ha
        )
        
        constraints = self._identify_constraints(
            aez_zone, slope, water_reliability, soil_fertility, market_distance
        )
        
        return LandAnalysis(
            lat=lat,
            lon=lon,
            area_ha=area_ha,
            aez_zone=aez_zone,
            aez_subzone=aez_subzone,
            annual_rainfall_mm=rainfall,
            rainfall_reliability=rainfall_reliability,
            temperature_range=temp_range,
            growing_days=growing_days,
            frost_risk=frost_risk,
            soil_type=soil_type,
            soil_fertility=soil_fertility,
            soil_depth_cm=soil_depth,
            drainage=drainage,
            slope_percent=slope,
            terrain_classification=terrain_class,
            erosion_risk=erosion_risk,
            water_source=water_source,
            water_reliability=water_reliability,
            borehole_feasibility=borehole_feasibility,
            flood_risk=flood_risk,
            market_distance_km=market_distance,
            road_quality=road_quality,
            electricity_access=electricity,
            land_class=land_class,
            recommended_systems=recommended_systems,
            constraints=constraints,
        )
    
    def _determine_aez(self, lat: float, lon: float) -> Tuple[str, str]:
        """Determine AEZ zone from coordinates."""
        
        for zone_id, zone_data in self.aez_data.items():
            for region in zone_data.get("regions", []):
                lat_range = region["lat_range"]
                lon_range = region["lon_range"]
                
                if (lat_range[0] <= lat <= lat_range[1] and
                    lon_range[0] <= lon <= lon_range[1]):
                    return zone_id, zone_id
        
        # Default based on general location
        if lat > -18.5:
            return "IIb", "IIb"
        elif lat > -20.0:
            return "III", "III"
        elif lat > -21.0:
            return "IV", "IV"
        else:
            return "V", "V"
    
    def _estimate_rainfall(self, lat: float, lon: float, zone_data: Dict) -> int:
        """Estimate annual rainfall."""
        rain_range = zone_data.get("rainfall_range", (500, 700))
        
        # Higher rainfall toward east
        east_factor = (lon - 28) / 5  # 0-1 scale
        rainfall = rain_range[0] + (rain_range[1] - rain_range[0]) * east_factor
        
        return int(max(rain_range[0], min(rain_range[1], rainfall)))
    
    def _calc_rainfall_reliability(self, aez_zone: str) -> float:
        """Calculate rainfall reliability score."""
        reliability_map = {
            "I": 0.85,
            "IIa": 0.80,
            "IIb": 0.75,
            "III": 0.65,
            "IV": 0.50,
            "V": 0.35,
        }
        return reliability_map.get(aez_zone, 0.5)
    
    def _estimate_temperature(self, lat: float, lon: float, aez_zone: str) -> Tuple[float, float]:
        """Estimate annual temperature range."""
        # Base temperatures adjusted by altitude/zone
        temp_map = {
            "I": (10, 22),    # Highlands - cooler
            "IIa": (12, 26),
            "IIb": (14, 28),
            "III": (15, 30),
            "IV": (16, 32),
            "V": (18, 35),    # Lowveld - hotter
        }
        return temp_map.get(aez_zone, (15, 28))
    
    def _estimate_growing_days(self, zone_data: Dict) -> int:
        """Estimate growing season length."""
        days_range = zone_data.get("growing_days", (120, 140))
        return int((days_range[0] + days_range[1]) / 2)
    
    def _analyze_soil(self, lat: float, lon: float, aez_zone: str) -> Tuple[str, str, int]:
        """Analyze soil characteristics."""
        soil_map = {
            "I": ("red_clay", "good", 120),
            "IIa": ("red_clay", "good", 100),
            "IIb": ("sandy_loam", "moderate", 90),
            "III": ("sandy_loam", "moderate", 80),
            "IV": ("sandy", "poor", 70),
            "V": ("sandy", "poor", 60),
        }
        return soil_map.get(aez_zone, ("sandy_loam", "moderate", 80))
    
    def _estimate_slope(self, lat: float, lon: float) -> float:
        """Estimate terrain slope percentage."""
        # Eastern highlands have steeper slopes
        if lon > 32.0:
            return 12.0 + (lon - 32) * 5
        elif lon > 31.0:
            return 5.0
        else:
            return 2.5
    
    def _estimate_drainage(self, soil_type: str, slope: float) -> str:
        """Estimate soil drainage."""
        if slope > 10:
            return "excessive"
        elif soil_type == "red_clay" and slope < 2:
            return "poor"
        elif soil_type in ("sandy", "sandy_loam"):
            return "good"
        else:
            return "moderate"
    
    def _classify_terrain(self, slope: float, aez_zone: str) -> str:
        """Classify terrain type."""
        if slope > 15:
            return "steep_hillside"
        elif slope > 8:
            return "rolling_hills"
        elif slope > 3:
            return "gentle_slopes"
        else:
            return "flat_plains"
    
    def _assess_erosion_risk(self, slope: float, rainfall: int, soil_type: str) -> str:
        """Assess erosion risk."""
        risk_score = 0
        
        if slope > 10:
            risk_score += 3
        elif slope > 5:
            risk_score += 2
        elif slope > 2:
            risk_score += 1
        
        if rainfall > 800:
            risk_score += 2
        elif rainfall > 600:
            risk_score += 1
        
        if soil_type in ("sandy", "sandy_loam"):
            risk_score += 1
        
        if risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "moderate"
        else:
            return "low"
    
    def _assess_water(self, lat: float, lon: float, aez_zone: str) -> Tuple[str, str]:
        """Assess water availability."""
        water_map = {
            "I": ("perennial_stream", "reliable"),
            "IIa": ("seasonal_river", "seasonal"),
            "IIb": ("seasonal_river", "seasonal"),
            "III": ("seasonal_stream", "unreliable"),
            "IV": ("borehole_required", "unreliable"),
            "V": ("borehole_required", "scarce"),
        }
        return water_map.get(aez_zone, ("seasonal_stream", "seasonal"))
    
    def _assess_borehole(self, lat: float, lon: float, aez_zone: str) -> str:
        """Assess borehole drilling feasibility."""
        # Generally feasible across Zimbabwe with varying depths
        if aez_zone in ("I", "IIa", "IIb"):
            return "excellent"
        elif aez_zone == "III":
            return "good"
        elif aez_zone == "IV":
            return "moderate"
        else:
            return "challenging"
    
    def _assess_flood_risk(self, lat: float, lon: float, slope: float) -> str:
        """Assess flood risk."""
        if slope < 1:
            return "moderate"
        elif slope < 2:
            return "low"
        else:
            return "none"
    
    def _assess_market_access(self, lat: float, lon: float) -> Tuple[float, str]:
        """Calculate distance to nearest market and road quality."""
        min_distance = float('inf')
        nearest_tier = 3
        
        for market in self.markets:
            dist = self._haversine(lat, lon, market["lat"], market["lon"])
            if dist < min_distance:
                min_distance = dist
                nearest_tier = market["tier"]
        
        # Road quality based on distance and market tier
        if min_distance < 20 and nearest_tier <= 2:
            road_quality = "paved"
        elif min_distance < 50:
            road_quality = "gravel"
        else:
            road_quality = "dirt_track"
        
        return round(min_distance, 1), road_quality
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _check_electricity(self, lat: float, lon: float, market_distance: float) -> bool:
        """Check grid electricity availability."""
        # Simple heuristic: closer to cities = more likely
        return market_distance < 30
    
    def _classify_land(
        self,
        aez_zone: str,
        slope: float,
        soil_fertility: str,
        water_reliability: str,
        rainfall: int,
    ) -> str:
        """Classify overall land suitability."""
        
        score = 0
        
        # AEZ scoring
        aez_scores = {"I": 5, "IIa": 5, "IIb": 4, "III": 3, "IV": 2, "V": 1}
        score += aez_scores.get(aez_zone, 2)
        
        # Slope scoring
        if slope < 3:
            score += 3
        elif slope < 8:
            score += 2
        elif slope < 15:
            score += 1
        
        # Soil scoring
        soil_scores = {"excellent": 3, "good": 2, "moderate": 1, "poor": 0}
        score += soil_scores.get(soil_fertility, 1)
        
        # Water scoring
        water_scores = {"reliable": 3, "seasonal": 2, "unreliable": 1, "scarce": 0}
        score += water_scores.get(water_reliability, 1)
        
        # Classification
        if score >= 12:
            return "prime_arable"
        elif score >= 9:
            return "semi_arable"
        elif score >= 6:
            return "marginal"
        elif score >= 4:
            return "pastoral"
        else:
            return "non_agricultural"
    
    def _recommend_systems(
        self,
        land_class: str,
        aez_zone: str,
        water_source: str,
        slope: float,
        area_ha: float,
    ) -> List[str]:
        """Recommend farming systems based on land analysis."""
        
        systems = []
        
        if land_class == "prime_arable":
            systems.extend(["intensive_cropping", "mixed_farming", "dairy", "commercial_vegetables"])
        
        elif land_class == "semi_arable":
            systems.extend(["mixed_cropping", "beef_cattle", "goats", "poultry"])
            if water_source in ("perennial_stream", "seasonal_river"):
                systems.append("irrigated_vegetables")
        
        elif land_class == "marginal":
            systems.extend(["drought_resistant_crops", "goats", "sheep"])
            if slope > 8:
                systems.append("terraced_farming")
            # Recommend protected cultivation for marginal land
            systems.extend(["greenhouse_vegetables", "aeroponics", "hydroponics"])
        
        elif land_class == "pastoral":
            systems.extend(["extensive_cattle", "goats", "game_ranching"])
            if water_source == "borehole_required":
                systems.append("solar_powered_borehole")
            # CEA for pastoral zones with water
            systems.append("container_farming")
        
        else:  # non_agricultural
            systems.extend(["game_ranching", "conservation", "solar_farm"])
            # Only CEA systems viable
            systems.extend(["aeroponics", "hydroponics", "vertical_farming"])
        
        # Size-based adjustments
        if area_ha < 5:
            systems = [s for s in systems if s not in ("extensive_cattle", "game_ranching")]
            systems.append("intensive_small_scale")
        
        return systems
    
    def _identify_constraints(
        self,
        aez_zone: str,
        slope: float,
        water_reliability: str,
        soil_fertility: str,
        market_distance: float,
    ) -> List[str]:
        """Identify key constraints for farming."""
        
        constraints = []
        
        if aez_zone in ("IV", "V"):
            constraints.append("low_rainfall")
        
        if water_reliability in ("unreliable", "scarce"):
            constraints.append("water_scarcity")
        
        if slope > 8:
            constraints.append("steep_terrain")
        
        if soil_fertility == "poor":
            constraints.append("poor_soil")
        
        if market_distance > 50:
            constraints.append("remote_location")
        
        if aez_zone == "I":
            constraints.append("frost_risk")
        
        return constraints
