"""
SuitabilityAgent - Ranks crops and livestock based on AEZ, soil, market access.
Uses FAO crop suitability guidelines adapted for Zimbabwe.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from .aez_lookup import AEZProfile, AEZLookupAgent


class SuitabilityLevel(Enum):
    HIGHLY_SUITABLE = "highly_suitable"
    SUITABLE = "suitable"
    SUITABLE_WITH_MANAGEMENT = "suitable_with_management"
    MARGINAL = "marginal"
    NOT_RECOMMENDED = "not_recommended"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class CropSuitability:
    """Suitability assessment for a single crop."""
    crop: str
    zone: str
    suitability: SuitabilityLevel
    risk: RiskLevel
    yield_expected: float  # t/ha
    yield_range: Dict[str, float]  # min, max
    price_per_ton: float
    cost_per_ha: float
    profit_per_ha: float  # expected
    profit_range: Dict[str, float]  # pessimistic, optimistic
    labor_days_per_ha: int
    water_requirement: str  # rainfed, supplemental, irrigated
    n_fixation: float  # kg N/ha (for legumes)
    crop_residue_fodder: float  # t/ha usable as feed
    notes: List[str] = field(default_factory=list)
    score: float = 0.0  # Composite ranking score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop": self.crop,
            "zone": self.zone,
            "suitability": self.suitability.value,
            "risk": self.risk.value,
            "yield_expected_t_ha": self.yield_expected,
            "yield_range": self.yield_range,
            "price_per_ton_usd": self.price_per_ton,
            "cost_per_ha_usd": self.cost_per_ha,
            "profit_per_ha_usd": self.profit_per_ha,
            "profit_range": self.profit_range,
            "labor_days_per_ha": self.labor_days_per_ha,
            "water_requirement": self.water_requirement,
            "n_fixation_kg_ha": self.n_fixation,
            "crop_residue_fodder_t_ha": self.crop_residue_fodder,
            "notes": self.notes,
            "score": self.score,
        }


@dataclass
class LivestockSuitability:
    """Suitability assessment for a livestock type."""
    livestock: str
    zone: str
    suitability: SuitabilityLevel
    recommended_system: str
    carrying_capacity: float  # heads per ha (or LSU for cattle)
    revenue_per_head: float
    cost_per_head: float
    profit_per_head: float
    labor_days_per_head: int
    feed_requirement_kg_day: float  # dry matter
    water_requirement_l_day: float
    integration_value: str  # manure, draft, etc.
    notes: List[str] = field(default_factory=list)
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "livestock": self.livestock,
            "zone": self.zone,
            "suitability": self.suitability.value,
            "recommended_system": self.recommended_system,
            "carrying_capacity_per_ha": self.carrying_capacity,
            "revenue_per_head_usd": self.revenue_per_head,
            "cost_per_head_usd": self.cost_per_head,
            "profit_per_head_usd": self.profit_per_head,
            "labor_days_per_head": self.labor_days_per_head,
            "feed_requirement_kg_day": self.feed_requirement_kg_day,
            "water_requirement_l_day": self.water_requirement_l_day,
            "integration_value": self.integration_value,
            "notes": self.notes,
            "score": self.score,
        }


# Crop characteristics (Zimbabwe-specific)
CROP_PARAMS = {
    "maize": {
        "labor_days_per_ha": 45,
        "water_requirement": "rainfed",
        "n_fixation": 0,
        "residue_factor": 1.2,  # t residue per t grain
        "market_weight": 1.0,  # always has market
    },
    "sorghum": {
        "labor_days_per_ha": 35,
        "water_requirement": "rainfed",
        "n_fixation": 0,
        "residue_factor": 1.5,
        "market_weight": 0.8,
    },
    "groundnuts": {
        "labor_days_per_ha": 50,
        "water_requirement": "rainfed",
        "n_fixation": 80,  # kg N/ha fixed
        "residue_factor": 1.0,
        "market_weight": 1.2,  # high value
    },
    "sunflower": {
        "labor_days_per_ha": 30,
        "water_requirement": "rainfed",
        "n_fixation": 0,
        "residue_factor": 0.5,
        "market_weight": 0.9,
    },
    "cotton": {
        "labor_days_per_ha": 60,
        "water_requirement": "rainfed",
        "n_fixation": 0,
        "residue_factor": 0.8,
        "market_weight": 1.0,
    },
    "tobacco": {
        "labor_days_per_ha": 120,
        "water_requirement": "supplemental",
        "n_fixation": 0,
        "residue_factor": 0,
        "market_weight": 1.3,  # high value but labor intensive
    },
    "vegetables": {
        "labor_days_per_ha": 150,
        "water_requirement": "irrigated",
        "n_fixation": 0,
        "residue_factor": 0.3,
        "market_weight": 1.5,  # high value, quick turnover
    },
    "fodder": {
        "labor_days_per_ha": 25,
        "water_requirement": "rainfed",
        "n_fixation": 0,
        "residue_factor": 0,  # IS the fodder
        "market_weight": 0.3,  # mostly on-farm use
    },
}

# Livestock characteristics
LIVESTOCK_PARAMS = {
    "cattle": {
        "feed_dm_kg_day": 10,
        "water_l_day": 50,
        "integration": "manure,draft,savings",
        "cycle_months": 24,
    },
    "goats": {
        "feed_dm_kg_day": 2,
        "water_l_day": 5,
        "integration": "manure,browse_control",
        "cycle_months": 8,
    },
    "sheep": {
        "feed_dm_kg_day": 1.5,
        "water_l_day": 4,
        "integration": "manure,wool",
        "cycle_months": 10,
    },
    "poultry": {
        "feed_dm_kg_day": 0.12,
        "water_l_day": 0.3,
        "integration": "manure,pest_control",
        "cycle_months": 2,  # broilers
    },
    "pigs": {
        "feed_dm_kg_day": 3,
        "water_l_day": 10,
        "integration": "manure,waste_conversion",
        "cycle_months": 6,
    },
}


class SuitabilityAgent:
    """
    Agent that ranks crops and livestock based on location-specific factors.
    """
    
    def __init__(self, aez_agent: Optional[AEZLookupAgent] = None):
        self.aez_agent = aez_agent or AEZLookupAgent()
    
    def _parse_risk(self, risk_str: str) -> RiskLevel:
        """Convert risk string to enum."""
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "very_high": RiskLevel.VERY_HIGH,
        }
        return mapping.get(risk_str.lower(), RiskLevel.MEDIUM)
    
    def _parse_suitability(self, suit_str: str) -> SuitabilityLevel:
        """Convert suitability string to enum."""
        mapping = {
            "highly_suitable": SuitabilityLevel.HIGHLY_SUITABLE,
            "suitable": SuitabilityLevel.SUITABLE,
            "suitable_with_management": SuitabilityLevel.SUITABLE_WITH_MANAGEMENT,
            "suitable_with_irrigation": SuitabilityLevel.SUITABLE_WITH_MANAGEMENT,
            "irrigation_required": SuitabilityLevel.MARGINAL,
            "marginal": SuitabilityLevel.MARGINAL,
            "not_recommended": SuitabilityLevel.NOT_RECOMMENDED,
        }
        return mapping.get(suit_str.lower(), SuitabilityLevel.MARGINAL)
    
    def _calculate_crop_score(
        self, 
        crop: CropSuitability, 
        objective: str,
        market_distance_km: float
    ) -> float:
        """
        Calculate composite score for crop ranking.
        Higher is better.
        """
        # Base score from suitability
        suit_scores = {
            SuitabilityLevel.HIGHLY_SUITABLE: 1.0,
            SuitabilityLevel.SUITABLE: 0.8,
            SuitabilityLevel.SUITABLE_WITH_MANAGEMENT: 0.6,
            SuitabilityLevel.MARGINAL: 0.3,
            SuitabilityLevel.NOT_RECOMMENDED: 0.0,
        }
        base = suit_scores.get(crop.suitability, 0.5)
        
        # Risk penalty
        risk_penalty = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: -0.1,
            RiskLevel.HIGH: -0.25,
            RiskLevel.VERY_HIGH: -0.4,
        }
        risk_adj = risk_penalty.get(crop.risk, -0.15)
        
        # Profit factor (normalized)
        profit_factor = min(crop.profit_per_ha / 500, 1.0) * 0.3  # cap at 500 USD/ha
        
        # Market access adjustment
        market_adj = max(0, (50 - market_distance_km) / 100) * 0.1
        
        # Objective-specific weights
        if objective == "maximize_profit":
            profit_weight = 0.4
            risk_weight = 0.2
        elif objective == "food_security":
            profit_weight = 0.2
            risk_weight = 0.4
            # Boost staples
            if crop.crop in ["maize", "sorghum", "groundnuts"]:
                base += 0.15
        elif objective == "soil_building":
            profit_weight = 0.15
            risk_weight = 0.2
            # Boost legumes
            if crop.n_fixation > 0:
                base += 0.2
        else:
            profit_weight = 0.3
            risk_weight = 0.3
        
        score = (
            base * 0.4 +
            risk_adj * risk_weight +
            profit_factor * profit_weight +
            market_adj
        )
        
        return max(0, min(1, score))
    
    def _calculate_livestock_score(
        self,
        livestock: LivestockSuitability,
        objective: str,
        available_fodder_ha: float
    ) -> float:
        """Calculate composite score for livestock ranking."""
        suit_scores = {
            SuitabilityLevel.HIGHLY_SUITABLE: 1.0,
            SuitabilityLevel.SUITABLE: 0.8,
            SuitabilityLevel.SUITABLE_WITH_MANAGEMENT: 0.6,
            SuitabilityLevel.MARGINAL: 0.3,
            SuitabilityLevel.NOT_RECOMMENDED: 0.0,
        }
        base = suit_scores.get(livestock.suitability, 0.5)
        
        # Profit factor
        profit_factor = min(livestock.profit_per_head / 200, 1.0) * 0.25
        
        # Feed efficiency (smaller animals = easier to feed)
        feed_factor = max(0, (10 - livestock.feed_requirement_kg_day) / 10) * 0.15
        
        # Integration bonus
        integration_points = len(livestock.integration_value.split(","))
        integration_bonus = integration_points * 0.05
        
        if objective == "maximize_profit":
            score = base * 0.35 + profit_factor * 0.4 + feed_factor * 0.15 + integration_bonus
        elif objective == "food_security":
            # Prefer faster turnover (poultry, goats)
            if livestock.livestock in ["poultry", "goats"]:
                base += 0.15
            score = base * 0.4 + profit_factor * 0.25 + feed_factor * 0.2 + integration_bonus
        else:
            score = base * 0.35 + profit_factor * 0.3 + feed_factor * 0.2 + integration_bonus
        
        return max(0, min(1, score))
    
    def assess_crops(
        self,
        aez_profile: AEZProfile,
        allowed_crops: Optional[List[str]] = None,
        objective: str = "maximize_profit",
        market_distance_km: float = 20,
    ) -> List[CropSuitability]:
        """
        Assess all suitable crops for a location.
        
        Args:
            aez_profile: AEZ profile from AEZLookupAgent
            allowed_crops: Optional filter for specific crops
            objective: maximize_profit | food_security | soil_building
            market_distance_km: Distance to nearest market
            
        Returns:
            List of CropSuitability, ranked by score
        """
        prices = self.aez_agent.get_market_prices()
        costs = self.aez_agent.get_input_costs()
        
        results = []
        
        for crop, zone_data in aez_profile.crop_suitability.items():
            if allowed_crops and crop not in allowed_crops:
                continue
            
            params = CROP_PARAMS.get(crop, {})
            price_data = prices.get(crop, {"typical": 300})
            cost_data = costs.get(crop, {"total": 200})
            
            yield_expected = zone_data["yield_t_ha"]["expected"]
            yield_min = zone_data["yield_t_ha"]["min"]
            yield_max = zone_data["yield_t_ha"]["max"]
            
            price = price_data.get("typical", 300)
            cost = cost_data.get("total", 200)
            
            profit_expected = yield_expected * price - cost
            profit_min = yield_min * price * 0.8 - cost  # Price also lower in bad years
            profit_max = yield_max * price * 1.1 - cost
            
            # Crop residue for fodder
            residue = yield_expected * params.get("residue_factor", 0)
            
            crop_suit = CropSuitability(
                crop=crop,
                zone=aez_profile.zone,
                suitability=self._parse_suitability(zone_data["recommendation"]),
                risk=self._parse_risk(zone_data["risk"]),
                yield_expected=yield_expected,
                yield_range={"min": yield_min, "max": yield_max},
                price_per_ton=price,
                cost_per_ha=cost,
                profit_per_ha=profit_expected,
                profit_range={"pessimistic": profit_min, "optimistic": profit_max},
                labor_days_per_ha=params.get("labor_days_per_ha", 40),
                water_requirement=params.get("water_requirement", "rainfed"),
                n_fixation=params.get("n_fixation", 0),
                crop_residue_fodder=residue,
            )
            
            # Add notes based on conditions
            if crop_suit.risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                crop_suit.notes.append(f"High drought risk in Zone {aez_profile.zone}")
            if crop_suit.n_fixation > 0:
                crop_suit.notes.append(f"Fixes ~{crop_suit.n_fixation} kg N/ha - soil building benefit")
            if crop_suit.water_requirement == "irrigated":
                crop_suit.notes.append("Requires irrigation infrastructure")
            
            # Calculate score
            crop_suit.score = self._calculate_crop_score(crop_suit, objective, market_distance_km)
            
            results.append(crop_suit)
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def assess_livestock(
        self,
        aez_profile: AEZProfile,
        allowed_livestock: Optional[List[str]] = None,
        objective: str = "maximize_profit",
        available_fodder_ha: float = 0,
    ) -> List[LivestockSuitability]:
        """
        Assess all suitable livestock for a location.
        
        Args:
            aez_profile: AEZ profile from AEZLookupAgent
            allowed_livestock: Optional filter for specific types
            objective: maximize_profit | food_security | soil_building
            available_fodder_ha: Hectares dedicated to fodder production
            
        Returns:
            List of LivestockSuitability, ranked by score
        """
        livestock_costs = self.aez_agent.get_livestock_costs()
        prices = self.aez_agent.get_market_prices()
        
        results = []
        
        for livestock, zone_data in aez_profile.livestock_capacity.items():
            if allowed_livestock and livestock not in allowed_livestock:
                continue
            
            params = LIVESTOCK_PARAMS.get(livestock, {})
            
            # Map livestock to price key
            price_keys = {
                "cattle": "cattle_beef",
                "goats": "goat_meat",
                "sheep": "goat_meat",  # Similar market
                "poultry": "poultry_broiler",
                "pigs": "pig_meat",
            }
            price_key = price_keys.get(livestock, livestock)
            price_data = prices.get(price_key, {"typical": 100})
            
            # Get cost data
            cost_key = livestock if livestock != "poultry" else "poultry_broilers"
            cost_data = livestock_costs.get(cost_key, {"total": 50})
            
            revenue = price_data.get("typical", 100)
            cost = cost_data.get("total", 50)
            
            # Determine suitability level
            system = zone_data.get("recommended_system", "semi_extensive")
            if system == "not_recommended":
                suit_level = SuitabilityLevel.NOT_RECOMMENDED
            elif "intensive" in system:
                suit_level = SuitabilityLevel.HIGHLY_SUITABLE
            elif "semi" in system:
                suit_level = SuitabilityLevel.SUITABLE
            else:
                suit_level = SuitabilityLevel.MARGINAL
            
            # Get carrying capacity
            if livestock == "cattle":
                capacity = zone_data.get("lsu_per_ha", 0.5)
            elif livestock == "goats":
                capacity = zone_data.get("heads_per_ha", 1.5)
            elif livestock == "sheep":
                capacity = zone_data.get("heads_per_ha", 1.2)
            elif livestock == "poultry":
                capacity = zone_data.get("birds_per_ha", 200)
            elif livestock == "pigs":
                capacity = zone_data.get("heads_per_ha", 3)
            else:
                capacity = 1.0
            
            ls = LivestockSuitability(
                livestock=livestock,
                zone=aez_profile.zone,
                suitability=suit_level,
                recommended_system=system,
                carrying_capacity=capacity,
                revenue_per_head=revenue,
                cost_per_head=cost,
                profit_per_head=revenue - cost,
                labor_days_per_head=cost_data.get("labor_days", 10),
                feed_requirement_kg_day=params.get("feed_dm_kg_day", 2),
                water_requirement_l_day=params.get("water_l_day", 5),
                integration_value=params.get("integration", "manure"),
            )
            
            # Add notes
            if zone_data.get("notes"):
                ls.notes.append(zone_data["notes"])
            
            # Calculate score
            ls.score = self._calculate_livestock_score(ls, objective, available_fodder_ha)
            
            results.append(ls)
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def recommend_enterprise_mix(
        self,
        lat: float,
        lon: float,
        area_ha: float,
        objective: str = "maximize_profit",
        allowed_enterprises: Optional[List[str]] = None,
        market_distance_km: float = 20,
    ) -> Dict[str, Any]:
        """
        High-level recommendation for enterprise mix at a location.
        
        Returns dict with ranked crops and livestock, plus initial allocation hints.
        """
        profile = self.aez_agent.lookup(lat, lon)
        
        # Split allowed enterprises
        allowed_crops = None
        allowed_livestock = None
        if allowed_enterprises:
            crop_names = set(CROP_PARAMS.keys())
            livestock_names = set(LIVESTOCK_PARAMS.keys())
            allowed_crops = [e for e in allowed_enterprises if e in crop_names]
            allowed_livestock = [e for e in allowed_enterprises if e in livestock_names]
        
        crops = self.assess_crops(profile, allowed_crops, objective, market_distance_km)
        livestock = self.assess_livestock(profile, allowed_livestock, objective)
        
        # Initial allocation hints
        top_crops = [c for c in crops if c.score >= 0.5][:4]
        top_livestock = [l for l in livestock if l.score >= 0.4][:2]
        
        return {
            "aez_profile": profile.to_dict(),
            "crop_rankings": [c.to_dict() for c in crops],
            "livestock_rankings": [l.to_dict() for l in livestock],
            "recommended_crops": [c.crop for c in top_crops],
            "recommended_livestock": [l.livestock for l in top_livestock],
            "objective": objective,
            "market_distance_km": market_distance_km,
        }


if __name__ == "__main__":
    agent = SuitabilityAgent()
    
    # Test for Harare area (Zone II)
    result = agent.recommend_enterprise_mix(
        lat=-17.83,
        lon=31.05,
        area_ha=7.0,
        objective="maximize_profit",
        market_distance_km=15,
    )
    
    print(f"Zone: {result['aez_profile']['zone']} - {result['aez_profile']['zone_name']}")
    print(f"\nTop crops for {result['objective']}:")
    for crop in result['crop_rankings'][:4]:
        print(f"  {crop['crop']}: score={crop['score']:.2f}, profit=${crop['profit_per_ha_usd']:.0f}/ha")
    
    print(f"\nTop livestock:")
    for ls in result['livestock_rankings'][:3]:
        print(f"  {ls['livestock']}: score={ls['score']:.2f}, capacity={ls['carrying_capacity_per_ha']}/ha")
