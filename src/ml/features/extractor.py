"""
Feature Extraction for ML Models

Converts geographic coordinates into feature vectors for ML models.
Fetches real climate data from Open-Meteo API.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json

# Try to import weather client (optional - falls back to estimates)
try:
    from src.data.weather_client import WeatherClient
    HAS_WEATHER_CLIENT = True
except ImportError:
    HAS_WEATHER_CLIENT = False


@dataclass
class LocationFeatures:
    """Feature vector for a location."""
    lat: float
    lon: float
    
    # Climate features (normalized 0-1)
    annual_rainfall_norm: float  # 0=250mm, 1=1400mm
    rainfall_reliability: float
    mean_temp_norm: float  # 0=15°C, 1=30°C
    temp_range_norm: float  # 0=5°C range, 1=20°C range
    growing_days_norm: float  # 0=80 days, 1=210 days
    frost_risk_score: float  # 0=none, 1=high
    
    # Soil features (estimated from AEZ)
    soil_fertility_score: float
    soil_depth_score: float
    drainage_score: float
    
    # Water features
    water_availability_score: float
    flood_risk_score: float
    borehole_feasibility_score: float
    
    # Accessibility features
    market_distance_norm: float  # 0=0km, 1=200km
    road_quality_score: float
    electricity_access_score: float
    
    # Derived AEZ encoding (one-hot)
    aez_I: float = 0.0
    aez_IIa: float = 0.0
    aez_IIb: float = 0.0
    aez_III: float = 0.0
    aez_IV: float = 0.0
    aez_V: float = 0.0
    
    # Geographic encodings
    lat_norm: float = 0.0  # Normalized latitude
    lon_norm: float = 0.0  # Normalized longitude
    elevation_norm: float = 0.5  # Estimated elevation
    
    def to_vector(self) -> np.ndarray:
        """Convert to numpy array for ML models."""
        return np.array([
            self.annual_rainfall_norm,
            self.rainfall_reliability,
            self.mean_temp_norm,
            self.temp_range_norm,
            self.growing_days_norm,
            self.frost_risk_score,
            self.soil_fertility_score,
            self.soil_depth_score,
            self.drainage_score,
            self.water_availability_score,
            self.flood_risk_score,
            self.borehole_feasibility_score,
            self.market_distance_norm,
            self.road_quality_score,
            self.electricity_access_score,
            self.aez_I,
            self.aez_IIa,
            self.aez_IIb,
            self.aez_III,
            self.aez_IV,
            self.aez_V,
            self.lat_norm,
            self.lon_norm,
            self.elevation_norm,
        ], dtype=np.float32)
    
    @staticmethod
    def feature_names() -> List[str]:
        """Return feature names for interpretability."""
        return [
            "annual_rainfall_norm",
            "rainfall_reliability",
            "mean_temp_norm",
            "temp_range_norm",
            "growing_days_norm",
            "frost_risk_score",
            "soil_fertility_score",
            "soil_depth_score",
            "drainage_score",
            "water_availability_score",
            "flood_risk_score",
            "borehole_feasibility_score",
            "market_distance_norm",
            "road_quality_score",
            "electricity_access_score",
            "aez_I",
            "aez_IIa",
            "aez_IIb",
            "aez_III",
            "aez_IV",
            "aez_V",
            "lat_norm",
            "lon_norm",
            "elevation_norm",
        ]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {name: float(val) for name, val in zip(self.feature_names(), self.to_vector())}


# Zimbabwe bounds for normalization
ZIM_LAT_RANGE = (-22.5, -15.5)  # South to North
ZIM_LON_RANGE = (25.0, 33.0)    # West to East

# AEZ Zone definitions (simplified)
AEZ_ZONES = {
    "I": {
        "rainfall": (1000, 1400),
        "growing_days": (180, 210),
        "frost_risk": 0.6,
        "soil_fertility": 0.85,
        "regions": [(-18.5, -17.5, 32.0, 33.0), (-19.5, -18.5, 32.3, 33.0)],
    },
    "IIa": {
        "rainfall": (800, 1000),
        "growing_days": (150, 180),
        "frost_risk": 0.2,
        "soil_fertility": 0.8,
        "regions": [(-18.5, -17.0, 30.5, 32.0), (-17.5, -16.5, 29.5, 31.0)],
    },
    "IIb": {
        "rainfall": (700, 850),
        "growing_days": (140, 160),
        "frost_risk": 0.15,
        "soil_fertility": 0.75,
        "regions": [(-18.5, -17.0, 30.0, 32.0), (-19.5, -18.5, 29.5, 31.5)],
    },
    "III": {
        "rainfall": (500, 700),
        "growing_days": (120, 140),
        "frost_risk": 0.1,
        "soil_fertility": 0.6,
        "regions": [(-20.5, -19.0, 29.0, 31.0), (-21.0, -20.0, 29.5, 31.0)],
    },
    "IV": {
        "rainfall": (400, 550),
        "growing_days": (100, 120),
        "frost_risk": 0.0,
        "soil_fertility": 0.4,
        "regions": [(-20.5, -19.5, 28.0, 29.5), (-22.0, -20.5, 28.5, 30.0)],
    },
    "V": {
        "rainfall": (250, 450),
        "growing_days": (80, 100),
        "frost_risk": 0.0,
        "soil_fertility": 0.3,
        "regions": [(-17.5, -16.0, 28.0, 29.0), (-22.5, -21.5, 29.0, 32.0)],
    },
}

# Major market centers for distance calculation
MARKET_CENTERS = [
    {"name": "Harare", "lat": -17.8292, "lon": 31.0522},
    {"name": "Bulawayo", "lat": -20.1539, "lon": 28.5802},
    {"name": "Mutare", "lat": -18.9707, "lon": 32.6709},
    {"name": "Masvingo", "lat": -20.0744, "lon": 30.8328},
    {"name": "Gweru", "lat": -19.4500, "lon": 29.8167},
    {"name": "Chinhoyi", "lat": -17.3667, "lon": 30.2000},
    {"name": "Kwekwe", "lat": -18.9281, "lon": 29.8147},
]


class FeatureExtractor:
    """
    Extracts ML features from geographic coordinates.
    
    Uses a combination of:
    - AEZ zone lookup (rule-based)
    - Open-Meteo weather data (real API)
    - Distance calculations (to markets)
    - Terrain estimation (from lat/lon patterns)
    """
    
    def __init__(self, use_weather_api: bool = True, cache_dir: str = None):
        self.use_weather_api = use_weather_api and HAS_WEATHER_CLIENT
        self.cache_dir = cache_dir
        self._weather_client = None
        
        if self.use_weather_api:
            try:
                self._weather_client = WeatherClient()
            except Exception:
                self.use_weather_api = False
    
    def extract(self, lat: float, lon: float, area_ha: float = 10.0) -> LocationFeatures:
        """
        Extract features for a given location.
        
        Args:
            lat: Latitude (-22.5 to -15.5 for Zimbabwe)
            lon: Longitude (25.0 to 33.0 for Zimbabwe)
            area_ha: Farm area in hectares (for context)
            
        Returns:
            LocationFeatures with normalized feature values
        """
        # Determine AEZ zone
        aez_zone = self._determine_aez(lat, lon)
        zone_data = AEZ_ZONES.get(aez_zone, AEZ_ZONES["III"])  # Default to Zone III
        
        # Get climate data
        if self.use_weather_api:
            climate = self._fetch_climate_data(lat, lon)
        else:
            climate = self._estimate_climate(lat, lon, zone_data)
        
        # Calculate market distance
        market_dist = self._nearest_market_distance(lat, lon)
        
        # Estimate other features from zone
        soil = self._estimate_soil(zone_data, lat, lon)
        water = self._estimate_water(zone_data, lat, lon, climate)
        access = self._estimate_access(lat, lon, market_dist)
        
        # Create one-hot AEZ encoding
        aez_encoding = {f"aez_{z}": 1.0 if z == aez_zone else 0.0 for z in AEZ_ZONES.keys()}
        
        # Normalize lat/lon
        lat_norm = (lat - ZIM_LAT_RANGE[0]) / (ZIM_LAT_RANGE[1] - ZIM_LAT_RANGE[0])
        lon_norm = (lon - ZIM_LON_RANGE[0]) / (ZIM_LON_RANGE[1] - ZIM_LON_RANGE[0])
        
        # Estimate elevation (higher in east/north)
        elevation_norm = 0.3 + 0.4 * lon_norm + 0.3 * lat_norm
        elevation_norm = max(0.0, min(1.0, elevation_norm))
        
        return LocationFeatures(
            lat=lat,
            lon=lon,
            annual_rainfall_norm=climate["rainfall_norm"],
            rainfall_reliability=climate["reliability"],
            mean_temp_norm=climate["temp_norm"],
            temp_range_norm=climate["temp_range_norm"],
            growing_days_norm=climate["growing_days_norm"],
            frost_risk_score=zone_data["frost_risk"],
            soil_fertility_score=soil["fertility"],
            soil_depth_score=soil["depth"],
            drainage_score=soil["drainage"],
            water_availability_score=water["availability"],
            flood_risk_score=water["flood_risk"],
            borehole_feasibility_score=water["borehole"],
            market_distance_norm=min(1.0, market_dist / 200.0),
            road_quality_score=access["road_quality"],
            electricity_access_score=access["electricity"],
            aez_I=aez_encoding.get("aez_I", 0.0),
            aez_IIa=aez_encoding.get("aez_IIa", 0.0),
            aez_IIb=aez_encoding.get("aez_IIb", 0.0),
            aez_III=aez_encoding.get("aez_III", 0.0),
            aez_IV=aez_encoding.get("aez_IV", 0.0),
            aez_V=aez_encoding.get("aez_V", 0.0),
            lat_norm=lat_norm,
            lon_norm=lon_norm,
            elevation_norm=elevation_norm,
        )
    
    def _determine_aez(self, lat: float, lon: float) -> str:
        """Determine AEZ zone from coordinates."""
        for zone_id, zone in AEZ_ZONES.items():
            for region in zone["regions"]:
                lat_min, lat_max, lon_min, lon_max = region
                if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                    return zone_id
        
        # Fallback: use distance-based heuristics
        # Eastern highlands (Zone I) if high longitude
        if lon > 32.0 and -20.0 <= lat <= -17.0:
            return "I"
        # Northern plateau (Zone II) if mid-latitude, moderate longitude
        elif lat > -18.5 and 29.5 <= lon <= 32.0:
            return "IIa" if lon > 30.5 else "IIb"
        # Southern/western dry zones
        elif lon < 29.0:
            return "V" if lat < -21.0 or lat > -17.5 else "IV"
        # Default to Zone III (semi-intensive)
        return "III"
    
    def _fetch_climate_data(self, lat: float, lon: float) -> Dict:
        """Fetch real climate data from Open-Meteo."""
        try:
            # Get historical weather for the past year
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            data = self._weather_client.get_historical(
                lat=lat,
                lon=lon,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
            
            if data and "daily" in data:
                daily = data["daily"]
                precip = daily.get("precipitation_sum", [0])
                temp_max = daily.get("temperature_2m_max", [25])
                temp_min = daily.get("temperature_2m_min", [15])
                
                annual_rainfall = sum(precip)
                mean_temp = (sum(temp_max) + sum(temp_min)) / (2 * len(temp_max))
                temp_range = max(temp_max) - min(temp_min)
                
                # Estimate growing days (days with >10mm rain in growing season)
                growing_days = sum(1 for p in precip if p > 0.5)
                
                return {
                    "rainfall_norm": min(1.0, (annual_rainfall - 250) / (1400 - 250)),
                    "reliability": self._calc_rainfall_reliability(precip),
                    "temp_norm": (mean_temp - 15) / (30 - 15),
                    "temp_range_norm": (temp_range - 5) / (20 - 5),
                    "growing_days_norm": (growing_days - 80) / (210 - 80),
                }
        except Exception:
            pass
        
        # Fallback to estimates
        return self._estimate_climate(lat, lon, AEZ_ZONES["III"])
    
    def _estimate_climate(self, lat: float, lon: float, zone: Dict) -> Dict:
        """Estimate climate from AEZ zone data."""
        rain_min, rain_max = zone["rainfall"]
        rainfall = (rain_min + rain_max) / 2
        
        days_min, days_max = zone["growing_days"]
        growing_days = (days_min + days_max) / 2
        
        # Higher rainfall in east
        rainfall_adj = rainfall * (1.0 + 0.1 * (lon - 30.0) / 3.0)
        
        return {
            "rainfall_norm": min(1.0, max(0.0, (rainfall_adj - 250) / (1400 - 250))),
            "reliability": 0.7 + 0.2 * (rainfall_adj - 250) / 1150,
            "temp_norm": 0.5 + 0.3 * (lat + 20) / 5,  # Warmer in lowlands/north
            "temp_range_norm": 0.5,
            "growing_days_norm": (growing_days - 80) / (210 - 80),
        }
    
    def _calc_rainfall_reliability(self, precip: List[float]) -> float:
        """Calculate rainfall reliability from precipitation data."""
        if not precip or sum(precip) == 0:
            return 0.5
        
        # CV of rainfall (lower = more reliable)
        mean_precip = sum(precip) / len(precip)
        if mean_precip == 0:
            return 0.5
        
        variance = sum((p - mean_precip) ** 2 for p in precip) / len(precip)
        cv = math.sqrt(variance) / mean_precip
        
        # Convert CV to reliability score (lower CV = higher reliability)
        return max(0.0, min(1.0, 1.0 - cv / 2.0))
    
    def _nearest_market_distance(self, lat: float, lon: float) -> float:
        """Calculate distance to nearest market center in km."""
        min_dist = float("inf")
        
        for market in MARKET_CENTERS:
            dist = self._haversine(lat, lon, market["lat"], market["lon"])
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance in km."""
        R = 6371  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _estimate_soil(self, zone: Dict, lat: float, lon: float) -> Dict:
        """Estimate soil properties from AEZ zone."""
        base_fertility = zone["soil_fertility"]
        
        # Adjust for position (higher fertility near rivers, lower on hillsides)
        fertility_adj = base_fertility + 0.1 * math.sin(lat * 10) * math.cos(lon * 10)
        fertility = max(0.0, min(1.0, fertility_adj))
        
        return {
            "fertility": fertility,
            "depth": 0.5 + 0.3 * fertility,  # Fertile soil tends to be deeper
            "drainage": 0.6 + 0.2 * (1 - zone["frost_risk"]),  # Better drainage in warm areas
        }
    
    def _estimate_water(self, zone: Dict, lat: float, lon: float, climate: Dict) -> Dict:
        """Estimate water availability from zone and climate."""
        rainfall_score = climate["rainfall_norm"]
        
        # Near rivers (heuristic: lower elevation, valley areas)
        river_proximity = 0.3 + 0.4 * math.sin(lon * 5) * math.cos(lat * 3)
        
        return {
            "availability": 0.3 * rainfall_score + 0.4 * climate["reliability"] + 0.3 * river_proximity,
            "flood_risk": max(0.0, rainfall_score - 0.6) * 0.5 + 0.2 * river_proximity,
            "borehole": 0.5 + 0.3 * rainfall_score + 0.2 * (1 - zone["frost_risk"]),
        }
    
    def _estimate_access(self, lat: float, lon: float, market_dist: float) -> Dict:
        """Estimate infrastructure access."""
        # Closer to urban centers = better infrastructure
        urban_proximity = max(0.0, 1.0 - market_dist / 100.0)
        
        return {
            "road_quality": 0.3 + 0.5 * urban_proximity + 0.2 * (lon - 25) / 8,
            "electricity": 0.2 + 0.6 * urban_proximity,
        }
    
    def batch_extract(self, locations: List[Tuple[float, float]], area_ha: float = 10.0) -> np.ndarray:
        """
        Extract features for multiple locations.
        
        Args:
            locations: List of (lat, lon) tuples
            area_ha: Farm area in hectares
            
        Returns:
            Array of shape (n_locations, n_features)
        """
        features = [self.extract(lat, lon, area_ha) for lat, lon in locations]
        return np.stack([f.to_vector() for f in features])
