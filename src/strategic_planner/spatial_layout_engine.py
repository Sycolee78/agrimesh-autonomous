"""
Spatial Layout Engine

Generates optimized farm spatial layouts including:
- Crop field zones
- Livestock paddocks
- Infrastructure placement
- Water systems
- Access roads
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ZoneType(Enum):
    CROP_FIELD = "crop_field"
    LIVESTOCK_PADDOCK = "livestock_paddock"
    GREENHOUSE = "greenhouse"
    HYDROPONICS = "hydroponics"
    ORCHARD = "orchard"
    FODDER = "fodder"
    PASTURE = "pasture"
    WATER_SOURCE = "water_source"
    WATER_STORAGE = "water_storage"
    IRRIGATION_MAIN = "irrigation_main"
    ADMIN_BLOCK = "admin_block"
    STORAGE = "storage"
    LIVESTOCK_HOUSING = "livestock_housing"
    POULTRY_HOUSE = "poultry_house"
    FEED_STORAGE = "feed_storage"
    COMPOST_AREA = "compost_area"
    SOLAR_ARRAY = "solar_array"
    BOREHOLE = "borehole"
    ACCESS_ROAD = "access_road"
    BUFFER_ZONE = "buffer_zone"
    WINDBREAK = "windbreak"


@dataclass
class LayoutZone:
    """A zone within the farm layout."""
    zone_id: str
    zone_type: ZoneType
    name: str
    area_ha: float
    
    # Position (relative coordinates, 0-100 scale)
    x: float
    y: float
    width: float
    height: float
    
    # Optional polygon for irregular shapes
    polygon: Optional[List[Tuple[float, float]]] = None
    
    # Attributes
    enterprise_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    color: str = "#808080"


@dataclass
class SpatialLayout:
    """Complete farm spatial layout."""
    total_area_ha: float
    utilized_area_ha: float
    
    # Zones
    zones: List[LayoutZone]
    
    # Infrastructure
    water_network: Dict  # Water flow design
    road_network: Dict   # Access roads
    power_network: Dict  # Electrical/solar
    
    # Optimization metrics
    water_efficiency_score: float
    biosecurity_score: float
    labor_efficiency_score: float
    
    # Layout metadata
    orientation: str  # "N", "NE", etc.
    slope_direction: str
    design_notes: List[str]


class SpatialLayoutEngine:
    """
    Generates optimized spatial farm layouts.
    """
    
    # Zone colors for visualization
    ZONE_COLORS = {
        ZoneType.CROP_FIELD: "#90EE90",      # Light green
        ZoneType.LIVESTOCK_PADDOCK: "#DEB887", # Burlywood
        ZoneType.GREENHOUSE: "#E0FFFF",       # Light cyan
        ZoneType.HYDROPONICS: "#87CEEB",      # Sky blue
        ZoneType.FODDER: "#98FB98",           # Pale green
        ZoneType.PASTURE: "#9ACD32",          # Yellow green
        ZoneType.WATER_SOURCE: "#4169E1",     # Royal blue
        ZoneType.WATER_STORAGE: "#1E90FF",    # Dodger blue
        ZoneType.ADMIN_BLOCK: "#D3D3D3",      # Light gray
        ZoneType.STORAGE: "#A9A9A9",          # Dark gray
        ZoneType.LIVESTOCK_HOUSING: "#CD853F", # Peru
        ZoneType.POULTRY_HOUSE: "#F4A460",    # Sandy brown
        ZoneType.FEED_STORAGE: "#DAA520",     # Goldenrod
        ZoneType.COMPOST_AREA: "#8B4513",     # Saddle brown
        ZoneType.SOLAR_ARRAY: "#FFD700",      # Gold
        ZoneType.BOREHOLE: "#0000CD",         # Medium blue
        ZoneType.ACCESS_ROAD: "#696969",      # Dim gray
        ZoneType.BUFFER_ZONE: "#228B22",      # Forest green
        ZoneType.WINDBREAK: "#006400",        # Dark green
    }
    
    def generate_layout(
        self,
        enterprise_allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
        infrastructure_requirements: List[str],
    ) -> SpatialLayout:
        """
        Generate optimized spatial layout.
        
        Layout principles:
        1. Water flows downhill (if slope)
        2. Livestock downwind from crops
        3. Biosecurity separation
        4. Minimize travel distances
        5. Infrastructure centrally located
        """
        
        zones = []
        total_area = land_analysis.area_ha
        
        # Determine orientation based on slope
        orientation = self._determine_orientation(land_analysis)
        slope_direction = self._get_slope_direction(land_analysis)
        
        # Reserve areas for infrastructure (5-10% of total)
        infra_area = total_area * 0.08
        
        # Generate zone layout
        current_y = 5  # Start from top with margin
        current_x = 5
        
        # 1. Place infrastructure at entrance/center
        infra_zones = self._place_infrastructure(
            land_analysis, infrastructure_requirements, total_area
        )
        zones.extend(infra_zones)
        
        # 2. Place water systems near water source or high ground
        water_zones = self._place_water_systems(
            land_analysis, enterprise_allocations, total_area
        )
        zones.extend(water_zones)
        
        # 3. Place crop fields (upwind, near water)
        crop_zones = self._place_crop_zones(
            enterprise_allocations, land_analysis, total_area
        )
        zones.extend(crop_zones)
        
        # 4. Place livestock (downwind, separated)
        livestock_zones = self._place_livestock_zones(
            enterprise_allocations, land_analysis, total_area
        )
        zones.extend(livestock_zones)
        
        # 5. Place CEA systems (near infrastructure/power)
        cea_zones = self._place_cea_zones(
            enterprise_allocations, land_analysis, total_area
        )
        zones.extend(cea_zones)
        
        # 6. Add buffer zones and windbreaks
        buffer_zones = self._add_buffer_zones(zones, land_analysis)
        zones.extend(buffer_zones)
        
        # 7. Generate networks
        water_network = self._design_water_network(zones, land_analysis)
        road_network = self._design_road_network(zones, land_analysis)
        power_network = self._design_power_network(zones, land_analysis)
        
        # Calculate metrics
        utilized = sum(z.area_ha for z in zones if z.zone_type not in (ZoneType.BUFFER_ZONE, ZoneType.ACCESS_ROAD))
        water_eff = self._calc_water_efficiency(zones, water_network)
        biosecurity = self._calc_biosecurity_score(zones)
        labor_eff = self._calc_labor_efficiency(zones)
        
        design_notes = self._generate_design_notes(zones, land_analysis)
        
        return SpatialLayout(
            total_area_ha=total_area,
            utilized_area_ha=round(utilized, 2),
            zones=zones,
            water_network=water_network,
            road_network=road_network,
            power_network=power_network,
            water_efficiency_score=round(water_eff, 1),
            biosecurity_score=round(biosecurity, 1),
            labor_efficiency_score=round(labor_eff, 1),
            orientation=orientation,
            slope_direction=slope_direction,
            design_notes=design_notes,
        )
    
    def _determine_orientation(self, land: "LandAnalysis") -> str:
        """Determine optimal farm orientation."""
        # In Zimbabwe (southern hemisphere), north-facing slopes get more sun
        if land.slope_percent > 3:
            return "N"  # Face north for sun
        return "NE"  # Default
    
    def _get_slope_direction(self, land: "LandAnalysis") -> str:
        """Get slope direction for water flow."""
        if land.slope_percent < 2:
            return "flat"
        return "north_to_south"  # Default assumption
    
    def _place_infrastructure(
        self,
        land: "LandAnalysis",
        requirements: List[str],
        total_area: float,
    ) -> List[LayoutZone]:
        """Place core infrastructure."""
        
        zones = []
        
        # Admin block (entrance area)
        admin_size = min(0.2, total_area * 0.02)
        zones.append(LayoutZone(
            zone_id="admin-1",
            zone_type=ZoneType.ADMIN_BLOCK,
            name="Administration & Housing",
            area_ha=admin_size,
            x=5, y=5, width=15, height=10,
            notes=["Office", "Worker housing", "Parking"],
            color=self.ZONE_COLORS[ZoneType.ADMIN_BLOCK],
        ))
        
        # Storage facility
        storage_size = min(0.15, total_area * 0.015)
        zones.append(LayoutZone(
            zone_id="storage-1",
            zone_type=ZoneType.STORAGE,
            name="Main Storage",
            area_ha=storage_size,
            x=22, y=5, width=12, height=8,
            notes=["Crop storage", "Equipment shed", "Input storage"],
            color=self.ZONE_COLORS[ZoneType.STORAGE],
        ))
        
        # Feed storage if livestock
        if any("feed" in r.lower() or "livestock" in r.lower() for r in requirements):
            zones.append(LayoutZone(
                zone_id="feed-storage-1",
                zone_type=ZoneType.FEED_STORAGE,
                name="Feed Storage",
                area_ha=0.1,
                x=36, y=5, width=10, height=6,
                notes=["Hay barn", "Feed silos"],
                color=self.ZONE_COLORS[ZoneType.FEED_STORAGE],
            ))
        
        # Compost area (downwind)
        zones.append(LayoutZone(
            zone_id="compost-1",
            zone_type=ZoneType.COMPOST_AREA,
            name="Compost & Manure",
            area_ha=0.1,
            x=85, y=85, width=10, height=10,
            notes=["Manure processing", "Compost windrows"],
            color=self.ZONE_COLORS[ZoneType.COMPOST_AREA],
        ))
        
        # Solar array if needed
        if not land.electricity_access or "solar" in " ".join(requirements).lower():
            zones.append(LayoutZone(
                zone_id="solar-1",
                zone_type=ZoneType.SOLAR_ARRAY,
                name="Solar Power Array",
                area_ha=0.05,
                x=48, y=5, width=8, height=6,
                notes=["5kW solar system", "Battery storage"],
                color=self.ZONE_COLORS[ZoneType.SOLAR_ARRAY],
            ))
        
        return zones
    
    def _place_water_systems(
        self,
        land: "LandAnalysis",
        allocations: Dict,
        total_area: float,
    ) -> List[LayoutZone]:
        """Place water infrastructure."""
        
        zones = []
        
        # Borehole (if needed)
        if land.water_reliability in ("unreliable", "scarce") or land.borehole_feasibility in ("excellent", "good"):
            zones.append(LayoutZone(
                zone_id="borehole-1",
                zone_type=ZoneType.BOREHOLE,
                name="Borehole & Pump",
                area_ha=0.01,
                x=50, y=15, width=4, height=4,
                notes=["Solar-powered pump", "50m depth estimated"],
                color=self.ZONE_COLORS[ZoneType.BOREHOLE],
            ))
        
        # Main water storage (elevated for gravity feed)
        tank_size = min(0.05, total_area * 0.005)
        zones.append(LayoutZone(
            zone_id="water-tank-1",
            zone_type=ZoneType.WATER_STORAGE,
            name="Main Water Tank",
            area_ha=tank_size,
            x=55, y=12, width=6, height=6,
            notes=["10,000L tank", "Elevated for gravity feed"],
            color=self.ZONE_COLORS[ZoneType.WATER_STORAGE],
        ))
        
        # Secondary tank for livestock
        if any("livestock" in str(e).lower() or "cattle" in str(e).lower() or "goat" in str(e).lower() 
               for e in allocations.keys()):
            zones.append(LayoutZone(
                zone_id="water-tank-2",
                zone_type=ZoneType.WATER_STORAGE,
                name="Livestock Water Tank",
                area_ha=0.02,
                x=75, y=50, width=5, height=5,
                notes=["5,000L tank", "Auto-fill troughs"],
                color=self.ZONE_COLORS[ZoneType.WATER_STORAGE],
            ))
        
        return zones
    
    def _place_crop_zones(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land: "LandAnalysis",
        total_area: float,
    ) -> List[LayoutZone]:
        """Place crop production zones."""
        
        from src.strategic_planner.enterprise_ranker import EnterpriseCategory
        
        zones = []
        crop_start_y = 20
        current_x = 5
        current_y = crop_start_y
        
        for eid, (enterprise, alloc) in allocations.items():
            if enterprise.category != EnterpriseCategory.CROP:
                continue
            
            if alloc < 0.1:
                continue
            
            # Calculate zone dimensions
            area_pct = (alloc / total_area) * 100
            
            # Aspect ratio for efficient irrigation
            width = min(40, math.sqrt(area_pct) * 10)
            height = area_pct * 100 / width if width > 0 else 10
            
            # Wrap to next row if needed
            if current_x + width > 70:
                current_x = 5
                current_y += height + 3
            
            zone_type = ZoneType.FODDER if enterprise.id == "fodder" else ZoneType.CROP_FIELD
            
            zones.append(LayoutZone(
                zone_id=f"crop-{eid}",
                zone_type=zone_type,
                name=f"{enterprise.name} Field",
                area_ha=round(alloc, 2),
                x=current_x,
                y=current_y,
                width=width,
                height=min(height, 25),
                enterprise_id=eid,
                notes=[f"{alloc:.1f} ha", f"Yield target: {enterprise.expected_yield_per_ha} {enterprise.yield_unit}/ha"],
                color=self.ZONE_COLORS[zone_type],
            ))
            
            current_x += width + 3
        
        return zones
    
    def _place_livestock_zones(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land: "LandAnalysis",
        total_area: float,
    ) -> List[LayoutZone]:
        """Place livestock zones (downwind, separated)."""
        
        from src.strategic_planner.enterprise_ranker import EnterpriseCategory
        
        zones = []
        livestock_y = 55  # Lower portion of farm
        current_x = 5
        
        for eid, (enterprise, alloc) in allocations.items():
            if enterprise.category != EnterpriseCategory.LIVESTOCK:
                continue
            
            # Determine zone type
            if "poultry" in eid:
                zone_type = ZoneType.POULTRY_HOUSE
                width = 15
                height = 10
            elif eid in ("beef_cattle", "dairy_cattle"):
                zone_type = ZoneType.LIVESTOCK_PADDOCK
                width = 30
                height = 25
            else:  # goats, sheep, pigs
                zone_type = ZoneType.LIVESTOCK_PADDOCK
                width = 20
                height = 15
            
            # Calculate area based on stocking
            if enterprise.land_per_unit > 0:
                area = alloc * enterprise.land_per_unit
            else:
                area = 0.5  # Default small area for intensive
            
            zones.append(LayoutZone(
                zone_id=f"livestock-{eid}",
                zone_type=zone_type,
                name=f"{enterprise.name} Area",
                area_ha=round(area, 2),
                x=current_x,
                y=livestock_y,
                width=width,
                height=height,
                enterprise_id=eid,
                notes=[f"{int(alloc)} head", "Rotational grazing" if "cattle" in eid else "Intensive housing"],
                color=self.ZONE_COLORS[zone_type],
            ))
            
            current_x += width + 5
            
            # Add housing structure for intensive livestock
            if zone_type == ZoneType.POULTRY_HOUSE or eid == "pigs":
                zones.append(LayoutZone(
                    zone_id=f"housing-{eid}",
                    zone_type=ZoneType.LIVESTOCK_HOUSING,
                    name=f"{enterprise.name} Housing",
                    area_ha=0.05,
                    x=current_x - width - 3,
                    y=livestock_y - 8,
                    width=8,
                    height=6,
                    notes=["Climate controlled", "Automated feeders"],
                    color=self.ZONE_COLORS[ZoneType.LIVESTOCK_HOUSING],
                ))
        
        return zones
    
    def _place_cea_zones(
        self,
        allocations: Dict[str, Tuple["Enterprise", float]],
        land: "LandAnalysis",
        total_area: float,
    ) -> List[LayoutZone]:
        """Place controlled environment agriculture zones."""
        
        from src.strategic_planner.enterprise_ranker import EnterpriseCategory
        
        zones = []
        cea_x = 60
        cea_y = 20
        
        for eid, (enterprise, alloc) in allocations.items():
            if enterprise.category != EnterpriseCategory.CEA:
                continue
            
            if "greenhouse" in eid:
                zone_type = ZoneType.GREENHOUSE
                width = 15
                height = 12
            else:
                zone_type = ZoneType.HYDROPONICS
                width = 10
                height = 8
            
            zones.append(LayoutZone(
                zone_id=f"cea-{eid}",
                zone_type=zone_type,
                name=enterprise.name,
                area_ha=round(alloc, 3),
                x=cea_x,
                y=cea_y,
                width=width,
                height=height,
                enterprise_id=eid,
                notes=["Climate controlled", "Drip fertigation", f"{alloc*10000:.0f} m²"],
                color=self.ZONE_COLORS[zone_type],
            ))
            
            cea_y += height + 3
        
        return zones
    
    def _add_buffer_zones(
        self,
        existing_zones: List[LayoutZone],
        land: "LandAnalysis",
    ) -> List[LayoutZone]:
        """Add biosecurity buffers and windbreaks."""
        
        zones = []
        
        # Windbreak on prevailing wind side
        zones.append(LayoutZone(
            zone_id="windbreak-1",
            zone_type=ZoneType.WINDBREAK,
            name="Windbreak Trees",
            area_ha=0.2,
            x=0, y=0, width=3, height=100,
            notes=["Indigenous trees", "Wind protection"],
            color=self.ZONE_COLORS[ZoneType.WINDBREAK],
        ))
        
        # Buffer between livestock and crops
        has_livestock = any(z.zone_type in (ZoneType.LIVESTOCK_PADDOCK, ZoneType.POULTRY_HOUSE) 
                          for z in existing_zones)
        if has_livestock:
            zones.append(LayoutZone(
                zone_id="buffer-1",
                zone_type=ZoneType.BUFFER_ZONE,
                name="Biosecurity Buffer",
                area_ha=0.1,
                x=3, y=50, width=92, height=3,
                notes=["Separation zone", "No vehicle crossing"],
                color=self.ZONE_COLORS[ZoneType.BUFFER_ZONE],
            ))
        
        return zones
    
    def _design_water_network(
        self,
        zones: List[LayoutZone],
        land: "LandAnalysis",
    ) -> Dict:
        """Design water distribution network."""
        
        # Find water source
        source = next((z for z in zones if z.zone_type == ZoneType.BOREHOLE), None)
        tank = next((z for z in zones if z.zone_type == ZoneType.WATER_STORAGE), None)
        
        return {
            "source": source.zone_id if source else "external",
            "main_tank": tank.zone_id if tank else None,
            "distribution": "gravity_drip",
            "pipes": [
                {"from": "main_tank", "to": "crop_zones", "type": "main_line"},
                {"from": "main_tank", "to": "livestock_zones", "type": "branch_line"},
            ],
            "estimated_daily_demand_liters": sum(
                z.area_ha * 500 for z in zones 
                if z.zone_type in (ZoneType.CROP_FIELD, ZoneType.GREENHOUSE)
            ),
        }
    
    def _design_road_network(
        self,
        zones: List[LayoutZone],
        land: "LandAnalysis",
    ) -> Dict:
        """Design internal road network."""
        
        return {
            "main_entrance": {"x": 5, "y": 0},
            "main_road": {
                "path": [(5, 0), (5, 50), (50, 50)],
                "width_m": 4,
                "surface": "gravel",
            },
            "service_roads": [
                {"to": "storage", "width_m": 3},
                {"to": "livestock", "width_m": 3},
            ],
            "total_road_length_m": 500,
        }
    
    def _design_power_network(
        self,
        zones: List[LayoutZone],
        land: "LandAnalysis",
    ) -> Dict:
        """Design electrical/solar network."""
        
        solar = next((z for z in zones if z.zone_type == ZoneType.SOLAR_ARRAY), None)
        
        return {
            "source": "solar" if solar else "grid",
            "capacity_kw": 5 if solar else 10,
            "battery_kwh": 10 if solar else 0,
            "distribution_points": [
                "admin_block",
                "borehole_pump",
                "greenhouse",
                "cold_storage",
            ],
            "backup": "generator" if not solar else "battery",
        }
    
    def _calc_water_efficiency(self, zones: List[LayoutZone], water_network: Dict) -> float:
        """Calculate water system efficiency score."""
        # Based on gravity feed, drip irrigation, etc.
        score = 70  # Base
        
        if water_network.get("distribution") == "gravity_drip":
            score += 15
        
        if any(z.zone_type == ZoneType.WATER_STORAGE for z in zones):
            score += 10
        
        return min(100, score)
    
    def _calc_biosecurity_score(self, zones: List[LayoutZone]) -> float:
        """Calculate biosecurity arrangement score."""
        score = 60  # Base
        
        # Check for buffers
        if any(z.zone_type == ZoneType.BUFFER_ZONE for z in zones):
            score += 20
        
        # Check livestock separation
        livestock_zones = [z for z in zones if z.zone_type in (ZoneType.LIVESTOCK_PADDOCK, ZoneType.POULTRY_HOUSE)]
        crop_zones = [z for z in zones if z.zone_type == ZoneType.CROP_FIELD]
        
        if livestock_zones and crop_zones:
            # Check if they're separated (livestock at higher y values)
            avg_livestock_y = sum(z.y for z in livestock_zones) / len(livestock_zones)
            avg_crop_y = sum(z.y for z in crop_zones) / len(crop_zones)
            
            if avg_livestock_y > avg_crop_y + 20:
                score += 15
        
        return min(100, score)
    
    def _calc_labor_efficiency(self, zones: List[LayoutZone]) -> float:
        """Calculate labor movement efficiency."""
        score = 65  # Base
        
        # Central infrastructure is good
        infra_zones = [z for z in zones if z.zone_type in (ZoneType.ADMIN_BLOCK, ZoneType.STORAGE)]
        if infra_zones:
            avg_x = sum(z.x for z in infra_zones) / len(infra_zones)
            if 20 < avg_x < 50:
                score += 15
        
        # Compact layout
        production_zones = [z for z in zones if z.zone_type in 
                          (ZoneType.CROP_FIELD, ZoneType.LIVESTOCK_PADDOCK, ZoneType.GREENHOUSE)]
        if production_zones:
            x_spread = max(z.x for z in production_zones) - min(z.x for z in production_zones)
            if x_spread < 60:
                score += 10
        
        return min(100, score)
    
    def _generate_design_notes(
        self,
        zones: List[LayoutZone],
        land: "LandAnalysis",
    ) -> List[str]:
        """Generate layout design notes."""
        
        notes = []
        
        notes.append(f"Layout optimized for AEZ {land.aez_zone} conditions")
        
        if land.slope_percent > 3:
            notes.append("Contour planting recommended on sloped areas")
        
        if any(z.zone_type == ZoneType.GREENHOUSE for z in zones):
            notes.append("Greenhouses oriented E-W for optimal light")
        
        if any(z.zone_type == ZoneType.LIVESTOCK_PADDOCK for z in zones):
            notes.append("Livestock zones positioned downwind for odor management")
        
        notes.append("Access roads allow machinery movement to all zones")
        
        return notes
