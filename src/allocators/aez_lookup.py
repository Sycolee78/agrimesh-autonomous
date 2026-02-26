"""
AEZLookupAgent - Agro-Ecological Zone lookup for Zimbabwe.
Given coordinates, returns zone classification, climate profile, and suitability parameters.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import json

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "aez"


@dataclass
class AEZProfile:
    """Complete agro-ecological zone profile for a location."""
    zone: str  # I, II, III, IV, V
    zone_name: str
    lat: float
    lon: float
    rainfall_mm: Dict[str, float]  # min, max, mean
    rainfall_reliability: float  # 0-1
    growing_season_days: Dict[str, int]  # min, max
    soil_types: List[str]
    elevation_m: Dict[str, int]  # min, max
    provinces: List[str]
    description: str
    
    # Derived recommendations
    crop_suitability: Dict[str, Dict] = field(default_factory=dict)
    livestock_capacity: Dict[str, Dict] = field(default_factory=dict)
    
    def drought_risk(self) -> str:
        """Categorize drought risk based on rainfall reliability."""
        if self.rainfall_reliability >= 0.85:
            return "low"
        elif self.rainfall_reliability >= 0.7:
            return "moderate"
        elif self.rainfall_reliability >= 0.55:
            return "high"
        else:
            return "very_high"
    
    def recommended_enterprises(self) -> List[str]:
        """Return list of recommended enterprises for this zone."""
        recommended = []
        for crop, data in self.crop_suitability.items():
            if data.get("recommendation") in ["highly_suitable", "suitable"]:
                recommended.append(crop)
        for livestock, data in self.livestock_capacity.items():
            if data.get("recommended_system") not in ["not_recommended", "extensive_ranching"]:
                recommended.append(livestock)
        return recommended
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.zone,
            "zone_name": self.zone_name,
            "coordinates": {"lat": self.lat, "lon": self.lon},
            "rainfall_mm": self.rainfall_mm,
            "rainfall_reliability": self.rainfall_reliability,
            "growing_season_days": self.growing_season_days,
            "soil_types": self.soil_types,
            "elevation_m": self.elevation_m,
            "drought_risk": self.drought_risk(),
            "recommended_enterprises": self.recommended_enterprises(),
            "crop_suitability": self.crop_suitability,
            "livestock_capacity": self.livestock_capacity,
        }


class AEZLookupAgent:
    """
    Agent for looking up AEZ data for Zimbabwe coordinates.
    Uses local AEZ dataset with simplified zone boundaries.
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATA_DIR / "zimbabwe_aez.json"
        self._aez_data = None
        self._boundaries = None
        self._load_data()
    
    def _load_data(self):
        """Load AEZ data from JSON file."""
        with open(self.data_path, "r") as f:
            self._aez_data = json.load(f)
        
        boundaries_path = self.data_path.parent / "zimbabwe_boundaries.geojson"
        if boundaries_path.exists():
            with open(boundaries_path, "r") as f:
                self._boundaries = json.load(f)
    
    def _point_in_bbox(self, lat: float, lon: float, bbox: Dict) -> bool:
        """Check if point is within bounding box."""
        return (bbox["minLat"] <= lat <= bbox["maxLat"] and 
                bbox["minLon"] <= lon <= bbox["maxLon"])
    
    def _find_zone_by_coords(self, lat: float, lon: float) -> str:
        """
        Find AEZ zone for coordinates using simplified bbox matching.
        For production, use proper point-in-polygon with shapely.
        """
        # Priority order: I -> II -> III -> IV -> V (most specific first)
        zones = self._aez_data["zones"]
        
        # Check each zone's bbox
        for zone_id in ["I", "II", "III", "IV", "V"]:
            zone_data = zones[zone_id]
            if self._point_in_bbox(lat, lon, zone_data["bbox"]):
                # Additional check: is it closer to representative coords?
                for rep in zone_data.get("representative_coords", []):
                    dist = ((lat - rep["lat"])**2 + (lon - rep["lon"])**2)**0.5
                    if dist < 1.5:  # Within ~165km
                        return zone_id
        
        # Fallback: find closest zone by representative coords
        min_dist = float("inf")
        closest_zone = "III"  # Default to middle zone
        
        for zone_id, zone_data in zones.items():
            for rep in zone_data.get("representative_coords", []):
                dist = ((lat - rep["lat"])**2 + (lon - rep["lon"])**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_zone = zone_id
        
        return closest_zone
    
    def lookup(self, lat: float, lon: float) -> AEZProfile:
        """
        Look up AEZ profile for given coordinates.
        
        Args:
            lat: Latitude (negative for southern hemisphere)
            lon: Longitude
            
        Returns:
            AEZProfile with complete zone data
        """
        # Validate coordinates are within Zimbabwe
        if not (-22.5 <= lat <= -15.5 and 25.0 <= lon <= 33.0):
            raise ValueError(f"Coordinates ({lat}, {lon}) are outside Zimbabwe")
        
        zone_id = self._find_zone_by_coords(lat, lon)
        zone_data = self._aez_data["zones"][zone_id]
        
        # Build crop suitability map for this zone
        crop_suitability = {}
        for crop, zone_map in self._aez_data.get("crop_suitability", {}).items():
            if zone_id in zone_map:
                crop_suitability[crop] = zone_map[zone_id]
        
        # Build livestock capacity map for this zone
        livestock_capacity = {}
        for livestock, zone_map in self._aez_data.get("livestock_carrying_capacity", {}).items():
            if zone_id in zone_map:
                livestock_capacity[livestock] = zone_map[zone_id]
        
        return AEZProfile(
            zone=zone_id,
            zone_name=zone_data["name"],
            lat=lat,
            lon=lon,
            rainfall_mm=zone_data["rainfall_mm"],
            rainfall_reliability=zone_data["rainfall_reliability"],
            growing_season_days=zone_data["growing_season_days"],
            soil_types=zone_data["soil_types"],
            elevation_m=zone_data["elevation_m"],
            provinces=zone_data["provinces"],
            description=zone_data["description"],
            crop_suitability=crop_suitability,
            livestock_capacity=livestock_capacity,
        )
    
    def lookup_by_district(self, district_name: str) -> AEZProfile:
        """
        Look up AEZ by district name.
        Maps district to representative coordinates.
        """
        # District -> approximate coords mapping
        district_coords = {
            "harare": (-17.83, 31.05),
            "bulawayo": (-20.13, 28.63),
            "mutare": (-18.97, 32.67),
            "gweru": (-19.45, 29.82),
            "masvingo": (-20.07, 30.83),
            "chinhoyi": (-17.36, 30.19),
            "kwekwe": (-18.93, 29.81),
            "kadoma": (-18.33, 29.92),
            "victoria falls": (-17.93, 25.83),
            "hwange": (-18.36, 26.50),
            "chipinge": (-20.19, 32.62),
            "beitbridge": (-22.22, 30.00),
            "kariba": (-16.52, 28.80),
            "bindura": (-17.30, 31.33),
            "chegutu": (-18.13, 30.13),
        }
        
        key = district_name.lower().strip()
        if key not in district_coords:
            raise ValueError(f"Unknown district: {district_name}")
        
        lat, lon = district_coords[key]
        return self.lookup(lat, lon)
    
    def get_all_zones(self) -> Dict[str, Dict]:
        """Return summary of all AEZ zones."""
        return self._aez_data["zones"]
    
    def get_market_prices(self) -> Dict[str, Dict]:
        """Return current market price data."""
        return self._aez_data.get("market_prices_usd", {})
    
    def get_input_costs(self) -> Dict[str, Dict]:
        """Return input cost data per hectare."""
        return self._aez_data.get("input_costs_usd_per_ha", {})
    
    def get_livestock_costs(self) -> Dict[str, Dict]:
        """Return livestock costs per head per year."""
        return self._aez_data.get("livestock_costs_usd_per_head_per_year", {})


# Convenience function
def lookup_aez(lat: float, lon: float) -> AEZProfile:
    """Quick lookup for AEZ profile."""
    agent = AEZLookupAgent()
    return agent.lookup(lat, lon)


if __name__ == "__main__":
    # Test lookup
    agent = AEZLookupAgent()
    
    # Test Harare (Zone II)
    profile = agent.lookup(-17.83, 31.05)
    print(f"Harare: Zone {profile.zone} - {profile.zone_name}")
    print(f"  Rainfall: {profile.rainfall_mm['mean']}mm, Reliability: {profile.rainfall_reliability}")
    print(f"  Drought risk: {profile.drought_risk()}")
    print(f"  Recommended: {profile.recommended_enterprises()[:5]}")
    
    # Test Bulawayo (Zone IV)
    profile = agent.lookup(-20.13, 28.63)
    print(f"\nBulawayo: Zone {profile.zone} - {profile.zone_name}")
    print(f"  Rainfall: {profile.rainfall_mm['mean']}mm, Reliability: {profile.rainfall_reliability}")
    print(f"  Drought risk: {profile.drought_risk()}")
    
    # Test Mutare (Zone I)
    profile = agent.lookup(-18.97, 32.67)
    print(f"\nMutare: Zone {profile.zone} - {profile.zone_name}")
    print(f"  Rainfall: {profile.rainfall_mm['mean']}mm, Reliability: {profile.rainfall_reliability}")
