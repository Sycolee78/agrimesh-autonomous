"""
DeploymentAgent - Maps allocations to geo-tiles and assigns tasks to field agents.
Integrates with the AgriMesh agent ecosystem.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class AgentType(Enum):
    """Available agent types in AgriMesh."""
    FARM_ORCHESTRATOR = "FarmManagementOrchestrator"
    CROP_OPS = "CropOperationsAgent"
    LIVESTOCK_OPS = "LivestockOperationsAgent"
    WEATHER_WATER = "WeatherWaterAgent"
    MAINTENANCE = "MaintenanceAgent"
    SECURITY = "SecurityBiosecurityAgent"
    IRRIGATION = "IrrigationAgent"
    PLANT = "PlantAgent"
    HERD = "HerdAgent"
    POULTRY = "PoultryAgent"
    FODDER = "FodderAgent"
    YIELD_FORECAST = "YieldForecastAgent"


@dataclass
class GeoTile:
    """A spatial unit on the farm."""
    tile_id: str
    name: str
    area_ha: float
    centroid: Dict[str, float]  # lat, lon
    enterprise: str
    tile_type: str  # "field", "paddock", "infrastructure", "water_point"
    soil_type: Optional[str] = None
    irrigation: bool = False
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "name": self.name,
            "area_ha": self.area_ha,
            "centroid": self.centroid,
            "enterprise": self.enterprise,
            "tile_type": self.tile_type,
            "soil_type": self.soil_type,
            "irrigation": self.irrigation,
            "notes": self.notes,
        }


@dataclass
class AgentAssignment:
    """Assignment of an agent to farm area/enterprise."""
    agent_type: AgentType
    agent_id: str
    assigned_tiles: List[str]
    assigned_enterprises: List[str]
    responsibilities: List[str]
    schedule_frequency: str  # "continuous", "daily", "weekly", "as_needed"
    priority: int  # 1-5, 1 highest
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "agent_id": self.agent_id,
            "assigned_tiles": self.assigned_tiles,
            "assigned_enterprises": self.assigned_enterprises,
            "responsibilities": self.responsibilities,
            "schedule_frequency": self.schedule_frequency,
            "priority": self.priority,
        }


@dataclass
class AgentDeploymentPlan:
    """Complete agent deployment plan for the farm."""
    farm_id: str
    location: Dict[str, float]
    total_area_ha: float
    tiles: List[GeoTile]
    agents: List[AgentAssignment]
    communication_hierarchy: Dict[str, List[str]]
    alert_routing: Dict[str, str]
    
    def _format_agents_for_ui(self) -> List[Dict[str, Any]]:
        """Format agents for frontend display."""
        formatted = []
        for a in self.agents:
            formatted.append({
                "agent_type": a.agent_type.value,
                "agent_id": a.agent_id,
                "assigned_to": a.assigned_enterprises,
                "priority": ["Critical", "High", "Medium", "Low", "Background"][min(a.priority - 1, 4)],
                "schedule": a.schedule_frequency.replace("_", " ").title(),
                "config": {
                    "tiles": a.assigned_tiles,
                    "responsibilities": a.responsibilities,
                },
            })
        return formatted
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get deployment summary for UI."""
        total_agents = len(self.agents)
        covered_area = sum(t.area_ha for t in self.tiles if t.tile_type in ["field", "paddock"])
        coverage = (covered_area / self.total_area_ha * 100) if self.total_area_ha > 0 else 0
        return {
            "total_agents": total_agents,
            "coverage_percent": min(100, coverage),
            "total_tiles": len(self.tiles),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "farm_id": self.farm_id,
            "location": self.location,
            "total_area_ha": self.total_area_ha,
            "summary": self._get_summary(),
            "tiles": [t.to_dict() for t in self.tiles],
            "agents": self._format_agents_for_ui(),
            "communication_hierarchy": self.communication_hierarchy,
            "alert_routing": self.alert_routing,
        }
    
    def get_agent_for_enterprise(self, enterprise: str) -> Optional[AgentAssignment]:
        """Find the primary agent for an enterprise."""
        for agent in self.agents:
            if enterprise in agent.assigned_enterprises:
                return agent
        return None


class DeploymentAgent:
    """
    Agent for creating farm layouts and deploying AgriMesh agents.
    """
    
    def __init__(self):
        self._tile_counter = 0
        self._agent_counter = 0
    
    def _next_tile_id(self) -> str:
        self._tile_counter += 1
        return f"TILE_{self._tile_counter:03d}"
    
    def _next_agent_id(self, agent_type: AgentType) -> str:
        self._agent_counter += 1
        return f"{agent_type.value}_{self._agent_counter:02d}"
    
    def create_farm_layout(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        infra_ha: float = 0.5,
    ) -> List[GeoTile]:
        """
        Create a simple farm layout with geo-tiles.
        
        For MVP, creates a grid-like layout. Production version would
        use actual cadastral/parcel data.
        """
        tiles = []
        
        # Calculate approximate farm dimensions (assume square)
        side_m = (area_ha * 10000) ** 0.5
        
        # Infrastructure tile (center)
        tiles.append(GeoTile(
            tile_id=self._next_tile_id(),
            name="Homestead & Infrastructure",
            area_ha=infra_ha,
            centroid={"lat": lat, "lon": lon},
            enterprise="infrastructure",
            tile_type="infrastructure",
            notes=["Storage", "Housing", "Processing area"],
        ))
        
        # Create crop field tiles
        offset = 0.001  # ~100m in degrees (approximate)
        field_positions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1),
        ]
        
        pos_idx = 0
        for crop, area in crop_allocations.items():
            if area <= 0:
                continue
            
            # Split large areas into multiple tiles
            remaining = area
            while remaining > 0:
                tile_area = min(remaining, 2.0)  # Max 2ha per tile
                
                if pos_idx < len(field_positions):
                    dx, dy = field_positions[pos_idx]
                    pos_idx += 1
                else:
                    dx, dy = pos_idx // 3, pos_idx % 3
                    pos_idx += 1
                
                tile_lat = lat + dx * offset
                tile_lon = lon + dy * offset
                
                tiles.append(GeoTile(
                    tile_id=self._next_tile_id(),
                    name=f"{crop.title()} Field {pos_idx}",
                    area_ha=tile_area,
                    centroid={"lat": tile_lat, "lon": tile_lon},
                    enterprise=crop,
                    tile_type="field",
                    irrigation=crop in ["vegetables", "tobacco"],
                ))
                
                remaining -= tile_area
        
        # Create livestock paddocks
        for livestock, count in livestock_counts.items():
            if count <= 0:
                continue
            
            # Paddock area based on count and type
            if livestock == "cattle":
                paddock_area = count * 0.5  # 0.5 ha per head (minimal)
            elif livestock == "poultry":
                paddock_area = 0.1  # Fixed small area for housing
            else:
                paddock_area = count * 0.1
            
            if pos_idx < len(field_positions):
                dx, dy = field_positions[pos_idx]
                pos_idx += 1
            else:
                dx, dy = pos_idx // 3 - 1, pos_idx % 3 - 1
                pos_idx += 1
            
            tiles.append(GeoTile(
                tile_id=self._next_tile_id(),
                name=f"{livestock.title()} Paddock",
                area_ha=min(paddock_area, area_ha * 0.3),
                centroid={"lat": lat + dx * offset, "lon": lon + dy * offset},
                enterprise=livestock,
                tile_type="paddock",
                notes=[f"Housing for {count} {livestock}"],
            ))
        
        # Water point
        tiles.append(GeoTile(
            tile_id=self._next_tile_id(),
            name="Water Point",
            area_ha=0.05,
            centroid={"lat": lat - offset * 0.5, "lon": lon},
            enterprise="water",
            tile_type="water_point",
            notes=["Borehole/tank", "Livestock drinking", "Irrigation source"],
        ))
        
        return tiles
    
    def create_agent_assignments(
        self,
        tiles: List[GeoTile],
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
    ) -> List[AgentAssignment]:
        """
        Create agent assignments based on farm layout and enterprises.
        """
        assignments = []
        
        # Get tile IDs by enterprise
        crop_tiles = {}
        livestock_tiles = {}
        
        for tile in tiles:
            if tile.tile_type == "field":
                if tile.enterprise not in crop_tiles:
                    crop_tiles[tile.enterprise] = []
                crop_tiles[tile.enterprise].append(tile.tile_id)
            elif tile.tile_type == "paddock":
                if tile.enterprise not in livestock_tiles:
                    livestock_tiles[tile.enterprise] = []
                livestock_tiles[tile.enterprise].append(tile.tile_id)
        
        # Farm Management Orchestrator (always deployed)
        all_tiles = [t.tile_id for t in tiles]
        all_enterprises = list(crop_allocations.keys()) + list(livestock_counts.keys())
        
        assignments.append(AgentAssignment(
            agent_type=AgentType.FARM_ORCHESTRATOR,
            agent_id=self._next_agent_id(AgentType.FARM_ORCHESTRATOR),
            assigned_tiles=all_tiles,
            assigned_enterprises=all_enterprises,
            responsibilities=[
                "Overall farm coordination",
                "Conflict resolution",
                "Resource allocation",
                "Human escalation",
                "Daily planning",
            ],
            schedule_frequency="continuous",
            priority=1,
        ))
        
        # Crop Operations Agent
        if crop_allocations:
            crop_tile_ids = [tid for tids in crop_tiles.values() for tid in tids]
            assignments.append(AgentAssignment(
                agent_type=AgentType.CROP_OPS,
                agent_id=self._next_agent_id(AgentType.CROP_OPS),
                assigned_tiles=crop_tile_ids,
                assigned_enterprises=list(crop_allocations.keys()),
                responsibilities=[
                    "Planting decisions",
                    "Fertilizer application",
                    "Pest scouting",
                    "Harvest timing",
                    "Crop rotation planning",
                ],
                schedule_frequency="daily",
                priority=2,
            ))
        
        # Livestock Operations Agent
        if livestock_counts:
            ls_tile_ids = [tid for tids in livestock_tiles.values() for tid in tids]
            assignments.append(AgentAssignment(
                agent_type=AgentType.LIVESTOCK_OPS,
                agent_id=self._next_agent_id(AgentType.LIVESTOCK_OPS),
                assigned_tiles=ls_tile_ids,
                assigned_enterprises=list(livestock_counts.keys()),
                responsibilities=[
                    "Feeding schedules",
                    "Health monitoring",
                    "Breeding management",
                    "Weight tracking",
                    "Marketing decisions",
                ],
                schedule_frequency="daily",
                priority=2,
            ))
        
        # Weather & Water Agent
        water_tiles = [t.tile_id for t in tiles if t.tile_type == "water_point" or t.irrigation]
        assignments.append(AgentAssignment(
            agent_type=AgentType.WEATHER_WATER,
            agent_id=self._next_agent_id(AgentType.WEATHER_WATER),
            assigned_tiles=water_tiles + crop_tile_ids if crop_allocations else water_tiles,
            assigned_enterprises=["water", "weather"] + list(crop_allocations.keys()),
            responsibilities=[
                "Weather monitoring",
                "Rainfall tracking",
                "Water level monitoring",
                "Drought alerts",
                "Irrigation scheduling",
            ],
            schedule_frequency="continuous",
            priority=2,
        ))
        
        # Irrigation Agent (if irrigated crops)
        irrigated_tiles = [t.tile_id for t in tiles if t.irrigation]
        if irrigated_tiles:
            assignments.append(AgentAssignment(
                agent_type=AgentType.IRRIGATION,
                agent_id=self._next_agent_id(AgentType.IRRIGATION),
                assigned_tiles=irrigated_tiles,
                assigned_enterprises=[t.enterprise for t in tiles if t.irrigation],
                responsibilities=[
                    "Soil moisture monitoring",
                    "Irrigation scheduling",
                    "Water efficiency",
                    "System maintenance alerts",
                ],
                schedule_frequency="continuous",
                priority=2,
            ))
        
        # Yield Forecast Agent
        assignments.append(AgentAssignment(
            agent_type=AgentType.YIELD_FORECAST,
            agent_id=self._next_agent_id(AgentType.YIELD_FORECAST),
            assigned_tiles=all_tiles,
            assigned_enterprises=list(crop_allocations.keys()),
            responsibilities=[
                "Yield prediction",
                "Growth stage tracking",
                "Harvest forecasting",
                "Performance benchmarking",
            ],
            schedule_frequency="weekly",
            priority=3,
        ))
        
        # Security & Biosecurity Agent
        assignments.append(AgentAssignment(
            agent_type=AgentType.SECURITY,
            agent_id=self._next_agent_id(AgentType.SECURITY),
            assigned_tiles=all_tiles,
            assigned_enterprises=all_enterprises,
            responsibilities=[
                "Perimeter monitoring",
                "Disease surveillance",
                "Quarantine protocols",
                "Vaccination scheduling",
                "Incident response",
            ],
            schedule_frequency="continuous",
            priority=2,
        ))
        
        # Maintenance Agent
        infra_tiles = [t.tile_id for t in tiles if t.tile_type == "infrastructure"]
        assignments.append(AgentAssignment(
            agent_type=AgentType.MAINTENANCE,
            agent_id=self._next_agent_id(AgentType.MAINTENANCE),
            assigned_tiles=all_tiles,
            assigned_enterprises=["infrastructure", "equipment"],
            responsibilities=[
                "Equipment maintenance",
                "Fence inspection",
                "Building maintenance",
                "Spare parts inventory",
            ],
            schedule_frequency="weekly",
            priority=3,
        ))
        
        return assignments
    
    def create_communication_hierarchy(
        self,
        agents: List[AgentAssignment],
    ) -> Dict[str, List[str]]:
        """
        Define communication hierarchy between agents.
        """
        hierarchy = {}
        
        # Find orchestrator
        orchestrator = None
        for a in agents:
            if a.agent_type == AgentType.FARM_ORCHESTRATOR:
                orchestrator = a.agent_id
                break
        
        if not orchestrator:
            return {}
        
        # Orchestrator supervises all
        hierarchy[orchestrator] = []
        
        for agent in agents:
            if agent.agent_id != orchestrator:
                hierarchy[orchestrator].append(agent.agent_id)
                hierarchy[agent.agent_id] = [orchestrator]  # Report to orchestrator
        
        # Peer connections
        crop_agent = next((a for a in agents if a.agent_type == AgentType.CROP_OPS), None)
        weather_agent = next((a for a in agents if a.agent_type == AgentType.WEATHER_WATER), None)
        irrigation_agent = next((a for a in agents if a.agent_type == AgentType.IRRIGATION), None)
        livestock_agent = next((a for a in agents if a.agent_type == AgentType.LIVESTOCK_OPS), None)
        
        # Weather informs crop and irrigation
        if weather_agent:
            if crop_agent:
                hierarchy[weather_agent.agent_id].append(crop_agent.agent_id)
            if irrigation_agent:
                hierarchy[weather_agent.agent_id].append(irrigation_agent.agent_id)
            if livestock_agent:
                hierarchy[weather_agent.agent_id].append(livestock_agent.agent_id)
        
        return hierarchy
    
    def create_alert_routing(
        self,
        agents: List[AgentAssignment],
    ) -> Dict[str, str]:
        """
        Define alert routing rules.
        """
        routing = {}
        
        for agent in agents:
            if agent.agent_type == AgentType.FARM_ORCHESTRATOR:
                routing["critical_all"] = agent.agent_id
                routing["human_escalation"] = agent.agent_id
                routing["resource_conflict"] = agent.agent_id
            elif agent.agent_type == AgentType.CROP_OPS:
                routing["pest_alert"] = agent.agent_id
                routing["crop_stress"] = agent.agent_id
                routing["harvest_ready"] = agent.agent_id
            elif agent.agent_type == AgentType.LIVESTOCK_OPS:
                routing["animal_health"] = agent.agent_id
                routing["feeding_alert"] = agent.agent_id
                routing["breeding_event"] = agent.agent_id
            elif agent.agent_type == AgentType.WEATHER_WATER:
                routing["weather_warning"] = agent.agent_id
                routing["water_low"] = agent.agent_id
                routing["drought_alert"] = agent.agent_id
            elif agent.agent_type == AgentType.SECURITY:
                routing["biosecurity_alert"] = agent.agent_id
                routing["intrusion_alert"] = agent.agent_id
                routing["disease_suspected"] = agent.agent_id
            elif agent.agent_type == AgentType.IRRIGATION:
                routing["irrigation_failure"] = agent.agent_id
                routing["soil_moisture_critical"] = agent.agent_id
        
        return routing
    
    def create_deployment_plan(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        farm_id: Optional[str] = None,
    ) -> AgentDeploymentPlan:
        """
        Create complete deployment plan for a farm.
        
        Args:
            lat, lon: Farm center coordinates
            area_ha: Total farm area
            crop_allocations: Dict of crop -> hectares
            livestock_counts: Dict of livestock -> count
            farm_id: Optional farm identifier
            
        Returns:
            Complete AgentDeploymentPlan
        """
        self._tile_counter = 0
        self._agent_counter = 0
        
        farm_id = farm_id or f"FARM_{abs(hash((lat, lon))) % 10000:04d}"
        
        # Create layout
        tiles = self.create_farm_layout(
            lat, lon, area_ha, crop_allocations, livestock_counts
        )
        
        # Create agent assignments
        agents = self.create_agent_assignments(
            tiles, crop_allocations, livestock_counts
        )
        
        # Create communication hierarchy
        hierarchy = self.create_communication_hierarchy(agents)
        
        # Create alert routing
        routing = self.create_alert_routing(agents)
        
        return AgentDeploymentPlan(
            farm_id=farm_id,
            location={"lat": lat, "lon": lon},
            total_area_ha=area_ha,
            tiles=tiles,
            agents=agents,
            communication_hierarchy=hierarchy,
            alert_routing=routing,
        )


if __name__ == "__main__":
    agent = DeploymentAgent()
    
    crops = {"maize": 2.5, "groundnuts": 1.0, "vegetables": 0.5, "fodder": 1.0}
    livestock = {"goats": 12, "poultry": 100}
    
    plan = agent.create_deployment_plan(
        lat=-17.83,
        lon=31.05,
        area_ha=7.0,
        crop_allocations=crops,
        livestock_counts=livestock,
    )
    
    print(f"Farm: {plan.farm_id}")
    print(f"\nTiles ({len(plan.tiles)}):")
    for tile in plan.tiles:
        print(f"  {tile.tile_id}: {tile.name} ({tile.area_ha:.2f} ha) - {tile.enterprise}")
    
    print(f"\nAgents ({len(plan.agents)}):")
    for agent_assign in plan.agents:
        print(f"  {agent_assign.agent_id}: {', '.join(agent_assign.responsibilities[:2])}...")
