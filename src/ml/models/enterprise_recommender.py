"""
Enterprise Recommendation Model

Recommends optimal enterprise mix (crops + livestock + CEA) for a location.
Outputs a ranked list of enterprises with allocation suggestions.
"""

from __future__ import annotations

import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class EnterpriseType(Enum):
    CROP = "crop"
    LIVESTOCK = "livestock"
    CEA = "controlled_environment"
    AGROFORESTRY = "agroforestry"


@dataclass
class EnterpriseRecommendation:
    """Recommendation for a single enterprise."""
    enterprise_id: str
    name: str
    type: EnterpriseType
    suitability_score: float  # 0-100
    profit_potential_usd_ha: float
    allocation_pct: float  # Suggested % of farm area
    risk_level: str  # "low", "moderate", "high"
    capital_required_usd_ha: float
    labor_days_per_ha: int
    reasons: List[str]
    constraints: List[str]


@dataclass
class FarmPlanRecommendation:
    """Complete farm plan recommendation."""
    lat: float
    lon: float
    area_ha: float
    aez_zone: str
    enterprises: List[EnterpriseRecommendation]
    total_capital_required: float
    expected_annual_profit: float
    expected_roi_pct: float
    risk_assessment: str
    sustainability_score: float
    circular_economy_opportunities: List[str]


# Enterprise catalog with all options
ENTERPRISE_CATALOG = {
    # Crops
    "maize": {
        "name": "Maize (Grain)",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 350,
        "labor_days_per_ha": 45,
        "profit_per_ha": 800,
        "water_demand": 0.6,
        "temp_tolerance": (0.3, 0.7),
        "aez_suitability": {"I": 0.7, "IIa": 1.0, "IIb": 0.95, "III": 0.75, "IV": 0.4, "V": 0.2},
        "risk_factors": ["drought", "fall_armyworm"],
        "synergies": ["beef_cattle", "poultry", "pigs"],
    },
    "sorghum": {
        "name": "Sorghum",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 280,
        "labor_days_per_ha": 35,
        "profit_per_ha": 500,
        "water_demand": 0.35,
        "temp_tolerance": (0.4, 0.8),
        "aez_suitability": {"I": 0.3, "IIa": 0.5, "IIb": 0.7, "III": 0.95, "IV": 1.0, "V": 0.8},
        "risk_factors": ["bird_damage"],
        "synergies": ["goats", "beef_cattle"],
    },
    "groundnuts": {
        "name": "Groundnuts",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 400,
        "labor_days_per_ha": 55,
        "profit_per_ha": 1200,
        "water_demand": 0.5,
        "temp_tolerance": (0.4, 0.7),
        "aez_suitability": {"I": 0.5, "IIa": 0.9, "IIb": 0.95, "III": 0.8, "IV": 0.5, "V": 0.2},
        "risk_factors": ["aflatoxin"],
        "synergies": ["maize", "poultry"],  # Nitrogen fixing
    },
    "cotton": {
        "name": "Cotton",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 500,
        "labor_days_per_ha": 70,
        "profit_per_ha": 1500,
        "water_demand": 0.55,
        "temp_tolerance": (0.5, 0.8),
        "aez_suitability": {"I": 0.3, "IIa": 0.6, "IIb": 0.9, "III": 1.0, "IV": 0.6, "V": 0.3},
        "risk_factors": ["bollworm", "price_volatility"],
        "synergies": ["beef_cattle"],
    },
    "tobacco": {
        "name": "Tobacco",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 1200,
        "labor_days_per_ha": 120,
        "profit_per_ha": 5500,
        "water_demand": 0.65,
        "temp_tolerance": (0.35, 0.6),
        "aez_suitability": {"I": 0.6, "IIa": 1.0, "IIb": 0.9, "III": 0.5, "IV": 0.2, "V": 0.1},
        "risk_factors": ["disease", "curing_requirements", "market_access"],
        "synergies": [],
    },
    "soybeans": {
        "name": "Soybeans",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 380,
        "labor_days_per_ha": 40,
        "profit_per_ha": 750,
        "water_demand": 0.6,
        "temp_tolerance": (0.3, 0.6),
        "aez_suitability": {"I": 0.6, "IIa": 1.0, "IIb": 0.95, "III": 0.6, "IV": 0.3, "V": 0.1},
        "risk_factors": ["rust"],
        "synergies": ["maize", "poultry", "pigs"],  # Nitrogen fixing + feed
    },
    "vegetables": {
        "name": "Mixed Vegetables",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 2500,
        "labor_days_per_ha": 180,
        "profit_per_ha": 6000,
        "water_demand": 0.75,
        "temp_tolerance": (0.3, 0.6),
        "aez_suitability": {"I": 1.0, "IIa": 0.95, "IIb": 0.85, "III": 0.6, "IV": 0.3, "V": 0.2},
        "risk_factors": ["market_volatility", "perishability"],
        "synergies": ["poultry", "dairy"],  # Manure
    },
    "sunflower": {
        "name": "Sunflower",
        "type": EnterpriseType.CROP,
        "capital_per_ha": 320,
        "labor_days_per_ha": 35,
        "profit_per_ha": 550,
        "water_demand": 0.4,
        "temp_tolerance": (0.4, 0.7),
        "aez_suitability": {"I": 0.4, "IIa": 0.6, "IIb": 0.85, "III": 1.0, "IV": 0.8, "V": 0.4},
        "risk_factors": ["bird_damage"],
        "synergies": ["bees"],
    },
    # Livestock
    "beef_cattle": {
        "name": "Beef Cattle",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 800,  # Per carrying capacity ha
        "labor_days_per_ha": 25,
        "profit_per_ha": 400,
        "water_demand": 0.4,
        "temp_tolerance": (0.3, 0.8),
        "aez_suitability": {"I": 0.7, "IIa": 0.85, "IIb": 0.9, "III": 1.0, "IV": 1.0, "V": 0.9},
        "risk_factors": ["disease", "drought", "theft"],
        "synergies": ["maize", "sorghum", "groundnuts"],  # Crop residues
    },
    "dairy": {
        "name": "Dairy Cattle",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 1500,
        "labor_days_per_ha": 60,
        "profit_per_ha": 1200,
        "water_demand": 0.7,
        "temp_tolerance": (0.2, 0.5),
        "aez_suitability": {"I": 1.0, "IIa": 0.9, "IIb": 0.7, "III": 0.4, "IV": 0.2, "V": 0.1},
        "risk_factors": ["feed_cost", "disease", "cold_chain"],
        "synergies": ["vegetables", "maize"],  # Manure + feed
    },
    "goats": {
        "name": "Goats",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 300,
        "labor_days_per_ha": 20,
        "profit_per_ha": 350,
        "water_demand": 0.25,
        "temp_tolerance": (0.3, 0.9),
        "aez_suitability": {"I": 0.5, "IIa": 0.6, "IIb": 0.75, "III": 0.9, "IV": 1.0, "V": 1.0},
        "risk_factors": ["theft", "predation"],
        "synergies": ["sorghum", "agroforestry"],
    },
    "poultry_layers": {
        "name": "Poultry (Layers)",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 5000,  # Intensive, per effective ha
        "labor_days_per_ha": 100,
        "profit_per_ha": 8000,
        "water_demand": 0.5,
        "temp_tolerance": (0.3, 0.6),
        "aez_suitability": {"I": 0.9, "IIa": 1.0, "IIb": 0.95, "III": 0.8, "IV": 0.6, "V": 0.4},
        "risk_factors": ["disease", "feed_cost", "market_saturation"],
        "synergies": ["maize", "soybeans", "vegetables"],  # Feed + manure
    },
    "poultry_broilers": {
        "name": "Poultry (Broilers)",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 4000,
        "labor_days_per_ha": 80,
        "profit_per_ha": 6000,
        "water_demand": 0.5,
        "temp_tolerance": (0.3, 0.6),
        "aez_suitability": {"I": 0.85, "IIa": 1.0, "IIb": 0.95, "III": 0.75, "IV": 0.5, "V": 0.3},
        "risk_factors": ["disease", "feed_cost"],
        "synergies": ["maize", "soybeans"],
    },
    "pigs": {
        "name": "Pig Production",
        "type": EnterpriseType.LIVESTOCK,
        "capital_per_ha": 3000,
        "labor_days_per_ha": 70,
        "profit_per_ha": 4000,
        "water_demand": 0.6,
        "temp_tolerance": (0.3, 0.65),
        "aez_suitability": {"I": 0.8, "IIa": 1.0, "IIb": 0.9, "III": 0.6, "IV": 0.3, "V": 0.2},
        "risk_factors": ["disease", "feed_cost", "environmental"],
        "synergies": ["maize", "soybeans", "vegetables"],
    },
    # Controlled Environment Agriculture
    "greenhouse_veg": {
        "name": "Greenhouse Vegetables",
        "type": EnterpriseType.CEA,
        "capital_per_ha": 25000,
        "labor_days_per_ha": 300,
        "profit_per_ha": 35000,
        "water_demand": 0.3,  # Efficient water use
        "temp_tolerance": (0.0, 1.0),  # Climate controlled
        "aez_suitability": {"I": 1.0, "IIa": 1.0, "IIb": 0.95, "III": 0.9, "IV": 0.8, "V": 0.7},
        "risk_factors": ["capital_intensive", "technical_skill", "energy_cost"],
        "synergies": ["poultry_layers", "fish_farming"],
    },
    "fish_farming": {
        "name": "Fish Farming (Tilapia)",
        "type": EnterpriseType.CEA,
        "capital_per_ha": 8000,
        "labor_days_per_ha": 80,
        "profit_per_ha": 10000,
        "water_demand": 0.9,
        "temp_tolerance": (0.5, 0.8),
        "aez_suitability": {"I": 0.7, "IIa": 0.85, "IIb": 0.9, "III": 0.8, "IV": 0.6, "V": 0.9},  # V has rivers
        "risk_factors": ["water_quality", "disease", "technical"],
        "synergies": ["vegetables", "poultry_layers"],  # Aquaponics
    },
    # Agroforestry
    "fruit_orchard": {
        "name": "Fruit Orchard (Mixed)",
        "type": EnterpriseType.AGROFORESTRY,
        "capital_per_ha": 3500,
        "labor_days_per_ha": 60,
        "profit_per_ha": 2500,
        "water_demand": 0.5,
        "temp_tolerance": (0.3, 0.7),
        "aez_suitability": {"I": 1.0, "IIa": 0.9, "IIb": 0.75, "III": 0.5, "IV": 0.3, "V": 0.2},
        "risk_factors": ["establishment_time", "disease", "market"],
        "synergies": ["bees", "goats"],
    },
    "timber": {
        "name": "Timber Plantation",
        "type": EnterpriseType.AGROFORESTRY,
        "capital_per_ha": 1500,
        "labor_days_per_ha": 15,
        "profit_per_ha": 600,  # Long-term average
        "water_demand": 0.45,
        "temp_tolerance": (0.2, 0.6),
        "aez_suitability": {"I": 1.0, "IIa": 0.85, "IIb": 0.7, "III": 0.4, "IV": 0.2, "V": 0.1},
        "risk_factors": ["fire", "long_wait", "disease"],
        "synergies": ["beef_cattle", "bees"],
    },
}


class EnterpriseRecommender:
    """
    ML-based enterprise recommendation system.
    
    Given location features, recommends optimal enterprise mix
    considering climate suitability, economics, and synergies.
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.model = None
        self.scaler = None
        self.is_fitted = False
    
    def recommend(
        self,
        features: np.ndarray,
        area_ha: float = 10.0,
        available_capital: Optional[float] = None,
        available_labor_days: int = 1000,
        exclude_enterprises: Optional[List[str]] = None,
        top_k: int = 8,
    ) -> FarmPlanRecommendation:
        """
        Generate enterprise recommendations for a location.
        
        Args:
            features: Feature vector from FeatureExtractor
            area_ha: Total farm area in hectares
            available_capital: Budget constraint (None = unconstrained)
            available_labor_days: Labor days available per year
            exclude_enterprises: Enterprise IDs to exclude
            top_k: Number of top enterprises to return
            
        Returns:
            FarmPlanRecommendation with ranked enterprises and allocations
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        exclude = set(exclude_enterprises or [])
        
        # Score all enterprises
        scored = []
        for ent_id, ent in ENTERPRISE_CATALOG.items():
            if ent_id in exclude:
                continue
            
            score = self._score_enterprise(features[0], ent_id, ent, area_ha)
            if score > 0:
                scored.append((ent_id, ent, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[2], reverse=True)
        
        # Allocate based on scores and constraints
        recommendations = self._allocate_enterprises(
            scored[:top_k * 2],  # Consider more for allocation
            area_ha,
            available_capital,
            available_labor_days,
            top_k,
        )
        
        # Calculate totals
        total_capital = sum(r.capital_required_usd_ha * r.allocation_pct * area_ha / 100 for r in recommendations)
        expected_profit = sum(r.profit_potential_usd_ha * r.allocation_pct * area_ha / 100 for r in recommendations)
        
        # Determine AEZ zone from features
        aez_features = features[0, 15:21]
        aez_idx = np.argmax(aez_features)
        aez_zones = ["I", "IIa", "IIb", "III", "IV", "V"]
        aez_zone = aez_zones[aez_idx] if aez_features[aez_idx] > 0.5 else "III"
        
        # Calculate sustainability score
        sustainability = self._calculate_sustainability(recommendations)
        
        # Identify circular economy opportunities
        circular = self._identify_circular_opportunities(recommendations)
        
        # Risk assessment
        risk_level = self._assess_overall_risk(recommendations, features[0])
        
        return FarmPlanRecommendation(
            lat=0.0,  # Will be set by caller
            lon=0.0,
            area_ha=area_ha,
            aez_zone=aez_zone,
            enterprises=recommendations[:top_k],
            total_capital_required=total_capital,
            expected_annual_profit=expected_profit,
            expected_roi_pct=(expected_profit / total_capital * 100) if total_capital > 0 else 0,
            risk_assessment=risk_level,
            sustainability_score=sustainability,
            circular_economy_opportunities=circular,
        )
    
    def _score_enterprise(
        self, features: np.ndarray, ent_id: str, ent: Dict, area_ha: float
    ) -> float:
        """Score an enterprise for a given location."""
        # Extract features
        rainfall = features[0]
        temp = features[2]
        soil_fertility = features[6]
        water_avail = features[9]
        market_dist = features[12]
        electricity = features[14]
        
        # AEZ scores (indices 15-20)
        aez_scores = {
            "I": features[15],
            "IIa": features[16],
            "IIb": features[17],
            "III": features[18],
            "IV": features[19],
            "V": features[20],
        }
        
        # 1. AEZ suitability (40% weight)
        aez_suit = max(
            ent["aez_suitability"].get(zone, 0) * score
            for zone, score in aez_scores.items()
        )
        
        # 2. Water match (20% weight)
        water_req = ent["water_demand"]
        if rainfall < water_req - 0.3 and water_avail < 0.5:
            water_score = 0.3  # Insufficient water
        elif rainfall >= water_req or water_avail > 0.7:
            water_score = 1.0  # Sufficient water
        else:
            water_score = 0.5 + 0.5 * (rainfall / water_req)
        
        # 3. Temperature match (15% weight)
        temp_min, temp_max = ent["temp_tolerance"]
        if temp_min <= temp <= temp_max:
            temp_score = 1.0
        else:
            temp_score = max(0.2, 1.0 - abs(temp - (temp_min + temp_max) / 2))
        
        # 4. Soil suitability (10% weight)
        if ent["type"] == EnterpriseType.CROP:
            soil_score = 0.4 + 0.6 * soil_fertility
        else:
            soil_score = 0.7 + 0.3 * soil_fertility  # Less dependent
        
        # 5. Market access (10% weight)
        if ent["type"] == EnterpriseType.CROP and "perishability" in ent.get("risk_factors", []):
            market_score = max(0.3, 1.0 - market_dist)
        else:
            market_score = max(0.5, 1.0 - 0.5 * market_dist)
        
        # 6. Infrastructure requirements (5% weight)
        if ent["type"] == EnterpriseType.CEA:
            infra_score = 0.3 + 0.7 * electricity
        elif ent["type"] == EnterpriseType.LIVESTOCK and "cold_chain" in ent.get("risk_factors", []):
            infra_score = 0.5 + 0.5 * electricity
        else:
            infra_score = 0.8 + 0.2 * electricity
        
        # Weighted combination
        total_score = (
            0.40 * aez_suit +
            0.20 * water_score +
            0.15 * temp_score +
            0.10 * soil_score +
            0.10 * market_score +
            0.05 * infra_score
        ) * 100
        
        # Penalty for high capital if small farm
        if area_ha < 5 and ent["capital_per_ha"] > 3000:
            total_score *= 0.7
        
        return total_score
    
    def _allocate_enterprises(
        self,
        scored: List[Tuple[str, Dict, float]],
        area_ha: float,
        capital: Optional[float],
        labor_days: int,
        top_k: int,
    ) -> List[EnterpriseRecommendation]:
        """Allocate farm area to enterprises."""
        recommendations = []
        remaining_area = 100.0  # Percentage
        remaining_capital = capital
        remaining_labor = labor_days
        
        for ent_id, ent, score in scored:
            if len(recommendations) >= top_k:
                break
            if remaining_area <= 5:
                break
            
            # Calculate maximum allocation
            max_alloc = min(40.0, remaining_area)  # No single enterprise > 40%
            
            # Adjust for capital constraint
            if remaining_capital is not None:
                capital_needed = ent["capital_per_ha"] * area_ha * max_alloc / 100
                if capital_needed > remaining_capital:
                    max_alloc = min(max_alloc, remaining_capital / (ent["capital_per_ha"] * area_ha) * 100)
            
            # Adjust for labor constraint
            labor_needed = ent["labor_days_per_ha"] * area_ha * max_alloc / 100
            if labor_needed > remaining_labor:
                max_alloc = min(max_alloc, remaining_labor / (ent["labor_days_per_ha"] * area_ha) * 100)
            
            if max_alloc < 5:
                continue  # Skip if allocation too small
            
            # Determine allocation based on score
            allocation = max(10.0, min(max_alloc, score / 3))  # Higher score = more allocation
            
            # Determine risk level
            risk_factors = ent.get("risk_factors", [])
            if len(risk_factors) >= 3:
                risk_level = "high"
            elif len(risk_factors) >= 2:
                risk_level = "moderate"
            else:
                risk_level = "low"
            
            # Generate reasons
            reasons = []
            if score > 80:
                reasons.append("Excellent climate and soil match")
            elif score > 60:
                reasons.append("Good suitability for this location")
            if ent.get("synergies"):
                existing_ids = [r.enterprise_id for r in recommendations]
                synergy_matches = [s for s in ent["synergies"] if s in existing_ids]
                if synergy_matches:
                    reasons.append(f"Synergies with {', '.join(synergy_matches)}")
            if ent["profit_per_ha"] > 2000:
                reasons.append("High profit potential")
            
            rec = EnterpriseRecommendation(
                enterprise_id=ent_id,
                name=ent["name"],
                type=ent["type"],
                suitability_score=round(score, 1),
                profit_potential_usd_ha=ent["profit_per_ha"],
                allocation_pct=round(allocation, 1),
                risk_level=risk_level,
                capital_required_usd_ha=ent["capital_per_ha"],
                labor_days_per_ha=ent["labor_days_per_ha"],
                reasons=reasons if reasons else ["Suitable for this AEZ"],
                constraints=risk_factors,
            )
            
            recommendations.append(rec)
            
            # Update remaining resources
            remaining_area -= allocation
            if remaining_capital is not None:
                remaining_capital -= ent["capital_per_ha"] * area_ha * allocation / 100
            remaining_labor -= ent["labor_days_per_ha"] * area_ha * allocation / 100
        
        return recommendations
    
    def _calculate_sustainability(self, recommendations: List[EnterpriseRecommendation]) -> float:
        """Calculate overall sustainability score."""
        if not recommendations:
            return 0.0
        
        # Factors: crop diversity, livestock integration, agroforestry
        types = [r.type for r in recommendations]
        
        crop_count = sum(1 for t in types if t == EnterpriseType.CROP)
        livestock_count = sum(1 for t in types if t == EnterpriseType.LIVESTOCK)
        tree_count = sum(1 for t in types if t == EnterpriseType.AGROFORESTRY)
        
        # Diversity score (more diverse = more sustainable)
        diversity = min(1.0, len(set(types)) / 3)
        
        # Integration score (crops + livestock = good)
        integration = 0.5 if crop_count > 0 and livestock_count > 0 else 0.2
        
        # Tree cover bonus
        tree_bonus = 0.2 if tree_count > 0 else 0.0
        
        return round((diversity * 40 + integration * 40 + tree_bonus * 20), 1)
    
    def _identify_circular_opportunities(
        self, recommendations: List[EnterpriseRecommendation]
    ) -> List[str]:
        """Identify circular economy opportunities in the plan."""
        opportunities = []
        enterprise_ids = {r.enterprise_id for r in recommendations}
        
        # Manure loops
        if any(eid in enterprise_ids for eid in ["beef_cattle", "dairy", "goats"]):
            if any(eid in enterprise_ids for eid in ["maize", "vegetables", "soybeans"]):
                opportunities.append("Livestock manure → crop fertilizer")
        
        # Poultry manure
        if any(eid in enterprise_ids for eid in ["poultry_layers", "poultry_broilers"]):
            opportunities.append("Poultry litter → compost for crops")
        
        # Crop residues
        if "maize" in enterprise_ids and "beef_cattle" in enterprise_ids:
            opportunities.append("Maize stover → cattle feed")
        
        if "sorghum" in enterprise_ids and "goats" in enterprise_ids:
            opportunities.append("Sorghum stalks → goat fodder")
        
        # Nitrogen fixation
        if any(eid in enterprise_ids for eid in ["soybeans", "groundnuts"]):
            opportunities.append("Legume nitrogen fixation → reduced fertilizer needs")
        
        # Aquaponics
        if "fish_farming" in enterprise_ids and "vegetables" in enterprise_ids:
            opportunities.append("Fish effluent → vegetable nutrients (aquaponics)")
        
        # Bee integration
        if "fruit_orchard" in enterprise_ids or "sunflower" in enterprise_ids:
            opportunities.append("Pollination services opportunity (bees)")
        
        return opportunities
    
    def _assess_overall_risk(
        self, recommendations: List[EnterpriseRecommendation], features: np.ndarray
    ) -> str:
        """Assess overall farm plan risk."""
        if not recommendations:
            return "unknown"
        
        # Count risk factors
        high_risk_count = sum(1 for r in recommendations if r.risk_level == "high")
        total_count = len(recommendations)
        
        # Climate reliability
        rainfall_reliability = features[1]
        
        # Diversification
        type_diversity = len(set(r.type for r in recommendations))
        
        # Calculate risk score
        risk_score = (
            high_risk_count / total_count * 40 +
            (1 - rainfall_reliability) * 30 +
            (1 - type_diversity / 4) * 30
        )
        
        if risk_score > 60:
            return "high"
        elif risk_score > 35:
            return "moderate"
        else:
            return "low"
    
    def fit(self, X: np.ndarray, y: np.ndarray, **kwargs):
        """Train the recommendation model (optional - heuristics work well)."""
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn required for training")
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, **kwargs)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
    
    def save(self, path: str):
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        if self.model:
            with open(path / "recommender_model.pkl", "wb") as f:
                pickle.dump(self.model, f)
        if self.scaler:
            with open(path / "recommender_scaler.pkl", "wb") as f:
                pickle.dump(self.scaler, f)
        
        with open(path / "recommender_meta.json", "w") as f:
            json.dump({"is_fitted": self.is_fitted}, f)
    
    def load(self, path: str):
        """Load model from disk."""
        path = Path(path)
        
        if (path / "recommender_model.pkl").exists():
            with open(path / "recommender_model.pkl", "rb") as f:
                self.model = pickle.load(f)
            with open(path / "recommender_scaler.pkl", "rb") as f:
                self.scaler = pickle.load(f)
            self.is_fitted = True
