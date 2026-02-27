"""
Energy & Sustainability Planning Engine

Plans sustainable energy and resource systems:
- Solar power sizing
- Borehole/water systems
- Biogas from livestock
- Rainwater harvesting
- Crop residue utilization
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SolarSystem:
    """Solar power system specification."""
    capacity_kw: float
    panel_count: int
    battery_capacity_kwh: float
    estimated_daily_generation_kwh: float
    estimated_cost_usd: float
    payback_years: float


@dataclass
class WaterSystem:
    """Water harvesting and storage system."""
    borehole_depth_m: Optional[int]
    borehole_yield_lph: Optional[int]
    pump_type: str
    pump_power_kw: float
    tank_capacity_liters: int
    rainwater_harvest_liters_year: int
    estimated_cost_usd: float


@dataclass
class BiogasSystem:
    """Biogas production system."""
    digester_volume_m3: float
    daily_gas_production_m3: float
    daily_cooking_hours: float
    daily_electricity_kwh: float
    manure_input_kg_day: float
    estimated_cost_usd: float


@dataclass
class ResourceLoop:
    """Circular resource loop."""
    name: str
    input_source: str
    output_use: str
    annual_value_usd: float
    notes: str


@dataclass
class EnergySustainabilityPlan:
    """Complete energy and sustainability plan."""
    
    # Power systems
    solar_system: Optional[SolarSystem]
    grid_connection: bool
    backup_generator: bool
    total_power_demand_kw: float
    
    # Water systems
    water_system: WaterSystem
    irrigation_type: str
    water_self_sufficiency_pct: float
    
    # Biogas
    biogas_system: Optional[BiogasSystem]
    
    # Resource loops
    resource_loops: List[ResourceLoop]
    
    # Scores
    energy_self_sufficiency_score: float
    water_self_sufficiency_score: float
    circularity_score: float
    overall_sustainability_score: float
    
    # Economics
    total_infrastructure_cost_usd: float
    annual_savings_usd: float
    carbon_offset_tons_year: float
    
    # Recommendations
    recommended_model: str
    implementation_phases: List[Dict]


class EnergySustainabilityPlanner:
    """
    Plans energy and sustainability infrastructure.
    """
    
    # Zimbabwe solar constants
    SOLAR_HOURS_PER_DAY = 5.5  # Average peak sun hours
    SOLAR_COST_PER_KW = 1200   # USD per kW installed
    BATTERY_COST_PER_KWH = 200
    
    # Water constants
    BOREHOLE_COST_PER_METER = 50
    TANK_COST_PER_1000L = 80
    
    def plan(
        self,
        enterprise_allocations: Dict[str, Tuple["Enterprise", float]],
        land_analysis: "LandAnalysis",
        layout: Optional["SpatialLayout"] = None,
    ) -> EnergySustainabilityPlan:
        """
        Generate energy and sustainability plan.
        """
        
        # Calculate power demand
        power_demand = self._calc_power_demand(enterprise_allocations, land_analysis)
        
        # Design solar system
        solar = self._design_solar_system(power_demand, land_analysis)
        
        # Design water system
        water = self._design_water_system(enterprise_allocations, land_analysis)
        
        # Design biogas if livestock present
        biogas = self._design_biogas_system(enterprise_allocations)
        
        # Identify resource loops
        loops = self._identify_resource_loops(enterprise_allocations)
        
        # Calculate scores
        energy_score = self._calc_energy_score(solar, power_demand, land_analysis)
        water_score = self._calc_water_score(water, land_analysis)
        circularity = self._calc_circularity_score(loops, biogas)
        overall = (energy_score + water_score + circularity) / 3
        
        # Economics
        total_cost = (
            (solar.estimated_cost_usd if solar else 0) +
            water.estimated_cost_usd +
            (biogas.estimated_cost_usd if biogas else 0)
        )
        
        annual_savings = self._calc_annual_savings(solar, water, biogas, loops)
        carbon_offset = self._calc_carbon_offset(solar, biogas, loops)
        
        # Recommended model
        model, phases = self._recommend_implementation(
            solar, water, biogas, land_analysis, total_cost
        )
        
        return EnergySustainabilityPlan(
            solar_system=solar,
            grid_connection=land_analysis.electricity_access,
            backup_generator=power_demand > 3 and not land_analysis.electricity_access,
            total_power_demand_kw=round(power_demand, 1),
            water_system=water,
            irrigation_type="drip" if any(e.requires_irrigation for e, _ in enterprise_allocations.values()) else "manual",
            water_self_sufficiency_pct=round(water_score, 0),
            biogas_system=biogas,
            resource_loops=loops,
            energy_self_sufficiency_score=round(energy_score, 0),
            water_self_sufficiency_score=round(water_score, 0),
            circularity_score=round(circularity, 0),
            overall_sustainability_score=round(overall, 0),
            total_infrastructure_cost_usd=round(total_cost, 0),
            annual_savings_usd=round(annual_savings, 0),
            carbon_offset_tons_year=round(carbon_offset, 1),
            recommended_model=model,
            implementation_phases=phases,
        )
    
    def _calc_power_demand(
        self,
        allocations: Dict,
        land: "LandAnalysis",
    ) -> float:
        """Calculate total power demand in kW."""
        
        demand = 0.5  # Base (lighting, admin)
        
        for eid, (enterprise, alloc) in allocations.items():
            if enterprise.requires_electricity:
                # CEA systems have high power demand
                if enterprise.category.value == "controlled_environment":
                    demand += alloc * 10  # kW per ha
                elif "dairy" in eid:
                    demand += alloc * 0.5  # kW per animal
                elif "poultry" in eid:
                    demand += alloc * 0.01  # kW per bird
        
        # Water pumping
        if land.water_reliability in ("unreliable", "scarce"):
            demand += 1.5  # Borehole pump
        
        return max(2, demand)
    
    def _design_solar_system(
        self,
        power_demand: float,
        land: "LandAnalysis",
    ) -> Optional[SolarSystem]:
        """Design solar power system."""
        
        # Size for 80% of demand (grid/generator backup)
        target_kw = power_demand * 0.8
        
        # Oversize for cloudy days
        installed_kw = target_kw * 1.3
        
        daily_generation = installed_kw * self.SOLAR_HOURS_PER_DAY
        
        # Battery for evening use (50% of daily)
        battery_kwh = daily_generation * 0.5
        
        # Costs
        panel_cost = installed_kw * self.SOLAR_COST_PER_KW
        battery_cost = battery_kwh * self.BATTERY_COST_PER_KWH
        install_cost = (panel_cost + battery_cost) * 0.2
        total_cost = panel_cost + battery_cost + install_cost
        
        # Payback
        annual_savings = daily_generation * 365 * 0.15  # $0.15/kWh avoided
        payback = total_cost / max(1, annual_savings)
        
        return SolarSystem(
            capacity_kw=round(installed_kw, 1),
            panel_count=int(installed_kw / 0.4),  # 400W panels
            battery_capacity_kwh=round(battery_kwh, 0),
            estimated_daily_generation_kwh=round(daily_generation, 1),
            estimated_cost_usd=round(total_cost, 0),
            payback_years=round(payback, 1),
        )
    
    def _design_water_system(
        self,
        allocations: Dict,
        land: "LandAnalysis",
    ) -> WaterSystem:
        """Design water harvesting and storage system."""
        
        # Calculate daily water demand
        daily_demand = 0
        for eid, (enterprise, alloc) in allocations.items():
            daily_demand += enterprise.water_liters_per_ha_day * alloc
        
        daily_demand += 200  # Domestic use
        
        # Borehole sizing
        borehole_depth = None
        borehole_yield = None
        pump_type = "none"
        pump_power = 0
        
        if land.water_reliability in ("unreliable", "scarce"):
            # Need borehole
            borehole_depth = {
                "excellent": 30,
                "good": 50,
                "moderate": 80,
                "challenging": 120,
            }.get(land.borehole_feasibility, 60)
            
            borehole_yield = 2000  # liters per hour typical
            pump_type = "solar_submersible"
            pump_power = 1.5
        
        # Tank sizing (3 days storage)
        tank_capacity = int(daily_demand * 3)
        tank_capacity = max(5000, min(50000, tank_capacity))
        
        # Rainwater harvesting
        roof_area = 200  # m2 assumed
        rainwater = int(land.annual_rainfall_mm * roof_area * 0.8)
        
        # Costs
        borehole_cost = (borehole_depth or 0) * self.BOREHOLE_COST_PER_METER
        pump_cost = 1500 if pump_type != "none" else 0
        tank_cost = (tank_capacity / 1000) * self.TANK_COST_PER_1000L
        gutters_cost = 500
        
        total_cost = borehole_cost + pump_cost + tank_cost + gutters_cost
        
        return WaterSystem(
            borehole_depth_m=borehole_depth,
            borehole_yield_lph=borehole_yield,
            pump_type=pump_type,
            pump_power_kw=pump_power,
            tank_capacity_liters=tank_capacity,
            rainwater_harvest_liters_year=rainwater,
            estimated_cost_usd=round(total_cost, 0),
        )
    
    def _design_biogas_system(
        self,
        allocations: Dict,
    ) -> Optional[BiogasSystem]:
        """Design biogas system from livestock manure."""
        
        from src.strategic_planner.enterprise_ranker import ALL_ENTERPRISES
        
        # Calculate daily manure
        daily_manure = 0
        
        manure_rates = {
            "beef_cattle": 25,   # kg/day per animal
            "dairy_cattle": 35,
            "pigs": 5,
            "goats": 2,
            "sheep": 2,
            "poultry_layers": 0.1,
            "poultry_broilers": 0.08,
        }
        
        for eid, (enterprise, alloc) in allocations.items():
            if enterprise.category.value == "livestock":
                rate = manure_rates.get(eid, 1)
                daily_manure += rate * alloc
        
        if daily_manure < 20:
            return None  # Not enough for viable biogas
        
        # Biogas production (0.04 m3 gas per kg manure)
        daily_gas = daily_manure * 0.04
        
        # Digester sizing (20-day retention)
        digester_volume = daily_manure * 1.2 * 20 / 1000  # m3
        
        # Usage
        cooking_hours = daily_gas / 0.3  # 0.3 m3/hour for cooking
        electricity = daily_gas * 1.5  # kWh per m3 gas
        
        # Cost
        cost = digester_volume * 150 + 500  # $150/m3 + accessories
        
        return BiogasSystem(
            digester_volume_m3=round(digester_volume, 1),
            daily_gas_production_m3=round(daily_gas, 1),
            daily_cooking_hours=round(cooking_hours, 1),
            daily_electricity_kwh=round(electricity, 1),
            manure_input_kg_day=round(daily_manure, 0),
            estimated_cost_usd=round(cost, 0),
        )
    
    def _identify_resource_loops(
        self,
        allocations: Dict,
    ) -> List[ResourceLoop]:
        """Identify circular resource loops."""
        
        loops = []
        
        # Check for crop-livestock integration
        has_crops = any(e.category.value == "crop" for e, _ in allocations.values())
        has_livestock = any(e.category.value == "livestock" for e, _ in allocations.values())
        
        if has_crops and has_livestock:
            # Manure to crops
            loops.append(ResourceLoop(
                name="Manure Fertilizer",
                input_source="Livestock manure",
                output_use="Crop fertilization",
                annual_value_usd=500,
                notes="Reduces synthetic fertilizer cost by 30-50%",
            ))
            
            # Crop residues to feed
            if any("maize" in eid or "sorghum" in eid for eid in allocations.keys()):
                loops.append(ResourceLoop(
                    name="Crop Residue Feed",
                    input_source="Crop residues (stover, stalks)",
                    output_use="Livestock feed supplement",
                    annual_value_usd=300,
                    notes="Reduces feed costs, improves dry season nutrition",
                ))
        
        # Nitrogen fixation
        if any("groundnut" in eid for eid in allocations.keys()):
            loops.append(ResourceLoop(
                name="Nitrogen Fixation",
                input_source="Groundnut crop",
                output_use="Soil nitrogen for next crop",
                annual_value_usd=200,
                notes="40-60 kg N/ha fixed",
            ))
        
        # Compost loop
        if has_livestock or has_crops:
            loops.append(ResourceLoop(
                name="Composting",
                input_source="Crop waste + manure",
                output_use="Soil amendment",
                annual_value_usd=400,
                notes="Improves soil structure and water retention",
            ))
        
        return loops
    
    def _calc_energy_score(
        self,
        solar: Optional[SolarSystem],
        demand: float,
        land: "LandAnalysis",
    ) -> float:
        """Calculate energy self-sufficiency score."""
        
        score = 30 if land.electricity_access else 0
        
        if solar:
            supply_ratio = solar.estimated_daily_generation_kwh / max(1, demand * 8)
            score += min(70, supply_ratio * 70)
        
        return min(100, score)
    
    def _calc_water_score(
        self,
        water: WaterSystem,
        land: "LandAnalysis",
    ) -> float:
        """Calculate water self-sufficiency score."""
        
        score = 40  # Base
        
        if water.borehole_depth_m:
            score += 30
        
        if water.tank_capacity_liters > 10000:
            score += 15
        
        if land.rainfall_reliability > 0.7:
            score += 15
        
        return min(100, score)
    
    def _calc_circularity_score(
        self,
        loops: List[ResourceLoop],
        biogas: Optional[BiogasSystem],
    ) -> float:
        """Calculate circular economy score."""
        
        score = len(loops) * 15
        
        if biogas:
            score += 25
        
        return min(100, score)
    
    def _calc_annual_savings(
        self,
        solar: Optional[SolarSystem],
        water: WaterSystem,
        biogas: Optional[BiogasSystem],
        loops: List[ResourceLoop],
    ) -> float:
        """Calculate annual cost savings."""
        
        savings = 0
        
        # Solar savings
        if solar:
            savings += solar.estimated_daily_generation_kwh * 365 * 0.15
        
        # Water savings (reduced purchases)
        savings += water.rainwater_harvest_liters_year * 0.001  # $1 per 1000L
        
        # Biogas savings
        if biogas:
            savings += biogas.daily_cooking_hours * 365 * 0.5  # Gas equivalent
            savings += biogas.daily_electricity_kwh * 365 * 0.15
        
        # Resource loop savings
        savings += sum(l.annual_value_usd for l in loops)
        
        return savings
    
    def _calc_carbon_offset(
        self,
        solar: Optional[SolarSystem],
        biogas: Optional[BiogasSystem],
        loops: List[ResourceLoop],
    ) -> float:
        """Calculate annual carbon offset in tons CO2."""
        
        offset = 0
        
        if solar:
            # 0.5 kg CO2 per kWh avoided
            offset += solar.estimated_daily_generation_kwh * 365 * 0.0005
        
        if biogas:
            # Methane capture
            offset += biogas.daily_gas_production_m3 * 365 * 0.002
        
        # Composting
        offset += 0.5 * len(loops)
        
        return offset
    
    def _recommend_implementation(
        self,
        solar: Optional[SolarSystem],
        water: WaterSystem,
        biogas: Optional[BiogasSystem],
        land: "LandAnalysis",
        total_cost: float,
    ) -> Tuple[str, List[Dict]]:
        """Recommend implementation model and phases."""
        
        components = []
        if solar:
            components.append("Solar")
        if water.borehole_depth_m:
            components.append("Borehole")
        if biogas:
            components.append("Biogas")
        
        model = " + ".join(components) if components else "Grid + Municipal"
        
        phases = [
            {
                "phase": 1,
                "name": "Water Security",
                "actions": ["Install water tank", "Setup rainwater harvesting"],
                "cost_usd": water.estimated_cost_usd * 0.3,
                "timeline_months": 2,
            },
            {
                "phase": 2,
                "name": "Power Foundation",
                "actions": ["Install solar panels", "Setup battery storage"] if solar else ["Grid connection"],
                "cost_usd": (solar.estimated_cost_usd if solar else 500) * 0.6,
                "timeline_months": 3,
            },
        ]
        
        if water.borehole_depth_m:
            phases.append({
                "phase": 3,
                "name": "Borehole Installation",
                "actions": ["Drill borehole", "Install pump", "Connect to tanks"],
                "cost_usd": water.estimated_cost_usd * 0.7,
                "timeline_months": 2,
            })
        
        if biogas:
            phases.append({
                "phase": 4,
                "name": "Biogas System",
                "actions": ["Construct digester", "Install piping", "Setup generator"],
                "cost_usd": biogas.estimated_cost_usd,
                "timeline_months": 3,
            })
        
        return model, phases
