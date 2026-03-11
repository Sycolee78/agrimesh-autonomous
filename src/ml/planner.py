"""
ML Farm Planner

High-level interface for generating sustainable farm plans from location.
Combines feature extraction, yield prediction, and enterprise recommendation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from src.ml.features.extractor import FeatureExtractor, LocationFeatures
from src.ml.models.yield_predictor import CropYieldPredictor, YieldPrediction
from src.ml.models.enterprise_recommender import (
    EnterpriseRecommender,
    FarmPlanRecommendation,
    EnterpriseRecommendation,
)


@dataclass
class MLFarmPlan:
    """Complete ML-generated farm plan."""
    # Location info
    lat: float
    lon: float
    area_ha: float
    
    # Analysis results
    location_features: Dict[str, float]
    aez_zone: str
    
    # Yield predictions for all crops
    yield_predictions: List[Dict]
    
    # Enterprise recommendations
    recommended_enterprises: List[Dict]
    
    # Aggregated metrics
    total_capital_required: float
    expected_annual_revenue: float
    expected_annual_profit: float
    expected_roi_pct: float
    
    # Risk and sustainability
    risk_assessment: str
    sustainability_score: float
    circular_economy_opportunities: List[str]
    
    # Metadata
    generated_at: str
    model_version: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"=== AgriMesh ML Farm Plan ===",
            f"Location: ({self.lat:.4f}, {self.lon:.4f})",
            f"Area: {self.area_ha} ha",
            f"AEZ Zone: {self.aez_zone}",
            "",
            f"💰 Capital Required: ${self.total_capital_required:,.0f}",
            f"📈 Expected Profit: ${self.expected_annual_profit:,.0f}/year",
            f"📊 Expected ROI: {self.expected_roi_pct:.1f}%",
            f"⚠️ Risk Level: {self.risk_assessment}",
            f"🌱 Sustainability: {self.sustainability_score:.0f}/100",
            "",
            "🏆 Top Enterprises:",
        ]
        
        for i, ent in enumerate(self.recommended_enterprises[:5], 1):
            lines.append(
                f"  {i}. {ent['name']} ({ent['allocation_pct']:.0f}% area) - "
                f"Score: {ent['suitability_score']:.0f}"
            )
        
        if self.circular_economy_opportunities:
            lines.append("")
            lines.append("♻️ Circular Economy:")
            for opp in self.circular_economy_opportunities[:3]:
                lines.append(f"  • {opp}")
        
        return "\n".join(lines)


class MLFarmPlanner:
    """
    ML-powered sustainable farm planner.
    
    Given a location (lat, lon) and area, generates a comprehensive
    farm plan using machine learning models.
    
    Usage:
        planner = MLFarmPlanner()
        plan = planner.generate_plan(lat=-17.83, lon=31.05, area_ha=10)
        print(plan.summary())
    """
    
    MODEL_VERSION = "1.0.0"
    
    def __init__(self, model_dir: Optional[str] = None, use_weather: bool = True):
        """
        Initialize the ML planner.
        
        Args:
            model_dir: Directory containing trained models (optional)
            use_weather: Whether to fetch real weather data
        """
        self.model_dir = Path(model_dir) if model_dir else None
        self.feature_extractor = FeatureExtractor(use_weather_api=use_weather)
        self.yield_predictor = CropYieldPredictor(model_dir=model_dir)
        self.enterprise_recommender = EnterpriseRecommender(model_dir=model_dir)
        
        # Load trained models if available
        if model_dir and Path(model_dir).exists():
            try:
                self.yield_predictor.load(model_dir)
                self.enterprise_recommender.load(model_dir)
            except Exception as e:
                print(f"Note: Could not load trained models ({e}). Using heuristics.")
    
    def generate_plan(
        self,
        lat: float,
        lon: float,
        area_ha: float = 10.0,
        available_capital: Optional[float] = None,
        available_labor_days: int = 1000,
        preferred_enterprises: Optional[List[str]] = None,
        exclude_enterprises: Optional[List[str]] = None,
    ) -> MLFarmPlan:
        """
        Generate a sustainable farm plan for the given location.
        
        Args:
            lat: Latitude (Zimbabwe: -22.5 to -15.5)
            lon: Longitude (Zimbabwe: 25.0 to 33.0)
            area_ha: Total farm area in hectares
            available_capital: Budget constraint (USD, optional)
            available_labor_days: Labor availability per year
            preferred_enterprises: Enterprise IDs to prioritize
            exclude_enterprises: Enterprise IDs to exclude
            
        Returns:
            MLFarmPlan with complete recommendations
        """
        # 1. Extract location features
        features = self.feature_extractor.extract(lat, lon, area_ha)
        feature_vec = features.to_vector()
        
        # 2. Predict yields for all crops
        yield_predictions = self.yield_predictor.predict(feature_vec)
        
        # 3. Get enterprise recommendations
        enterprise_rec = self.enterprise_recommender.recommend(
            features=feature_vec,
            area_ha=area_ha,
            available_capital=available_capital,
            available_labor_days=available_labor_days,
            exclude_enterprises=exclude_enterprises,
        )
        
        # 4. Boost preferred enterprises if specified
        if preferred_enterprises:
            enterprise_rec = self._boost_preferred(enterprise_rec, preferred_enterprises)
        
        # 5. Calculate aggregated metrics
        revenue, profit = self._calculate_economics(
            enterprise_rec.enterprises,
            yield_predictions,
            area_ha,
        )
        
        # 6. Build the plan
        plan = MLFarmPlan(
            lat=lat,
            lon=lon,
            area_ha=area_ha,
            location_features=features.to_dict(),
            aez_zone=enterprise_rec.aez_zone,
            yield_predictions=[
                {
                    "crop_id": y.crop_id,
                    "crop_name": y.crop_name,
                    "predicted_yield_tons_ha": y.predicted_yield_tons_ha,
                    "confidence": y.confidence,
                    "yield_range": y.yield_range,
                    "limiting_factors": y.limiting_factors,
                }
                for y in yield_predictions[:10]  # Top 10 crops
            ],
            recommended_enterprises=[
                {
                    "enterprise_id": e.enterprise_id,
                    "name": e.name,
                    "type": e.type.value,
                    "suitability_score": e.suitability_score,
                    "profit_potential_usd_ha": e.profit_potential_usd_ha,
                    "allocation_pct": e.allocation_pct,
                    "risk_level": e.risk_level,
                    "capital_required_usd_ha": e.capital_required_usd_ha,
                    "labor_days_per_ha": e.labor_days_per_ha,
                    "reasons": e.reasons,
                    "constraints": e.constraints,
                }
                for e in enterprise_rec.enterprises
            ],
            total_capital_required=enterprise_rec.total_capital_required,
            expected_annual_revenue=revenue,
            expected_annual_profit=profit,
            expected_roi_pct=enterprise_rec.expected_roi_pct,
            risk_assessment=enterprise_rec.risk_assessment,
            sustainability_score=enterprise_rec.sustainability_score,
            circular_economy_opportunities=enterprise_rec.circular_economy_opportunities,
            generated_at=datetime.now().isoformat(),
            model_version=self.MODEL_VERSION,
        )
        
        return plan
    
    def _boost_preferred(
        self,
        rec: FarmPlanRecommendation,
        preferred: List[str],
    ) -> FarmPlanRecommendation:
        """Boost scores for preferred enterprises."""
        for ent in rec.enterprises:
            if ent.enterprise_id in preferred:
                ent.suitability_score *= 1.2  # 20% boost
                ent.reasons.append("User preference")
        
        # Re-sort by score
        rec.enterprises.sort(key=lambda e: e.suitability_score, reverse=True)
        return rec
    
    def _calculate_economics(
        self,
        enterprises: List[EnterpriseRecommendation],
        yields: List[YieldPrediction],
        area_ha: float,
    ) -> tuple[float, float]:
        """Calculate expected revenue and profit."""
        from src.ml.models.yield_predictor import CROP_CATALOG
        
        yield_map = {y.crop_id: y.predicted_yield_tons_ha for y in yields}
        
        total_revenue = 0.0
        total_cost = 0.0
        
        for ent in enterprises:
            allocated_area = area_ha * ent.allocation_pct / 100
            
            if ent.enterprise_id in yield_map:
                # Use predicted yield for crops
                yield_per_ha = yield_map[ent.enterprise_id]
                price = CROP_CATALOG.get(ent.enterprise_id, {}).get("price_per_ton", 300)
                revenue = yield_per_ha * price * allocated_area
            else:
                # Use base profit for non-crops
                revenue = ent.profit_potential_usd_ha * allocated_area
            
            cost = ent.capital_required_usd_ha * allocated_area * 0.3  # Annual cost ~30% of capital
            
            total_revenue += revenue
            total_cost += cost
        
        profit = total_revenue - total_cost
        return total_revenue, profit
    
    def batch_generate(
        self,
        locations: List[tuple[float, float]],
        area_ha: float = 10.0,
        **kwargs,
    ) -> List[MLFarmPlan]:
        """
        Generate plans for multiple locations.
        
        Args:
            locations: List of (lat, lon) tuples
            area_ha: Farm area for each location
            **kwargs: Additional arguments passed to generate_plan
            
        Returns:
            List of MLFarmPlan objects
        """
        plans = []
        for lat, lon in locations:
            try:
                plan = self.generate_plan(lat, lon, area_ha, **kwargs)
                plans.append(plan)
            except Exception as e:
                print(f"Warning: Failed to generate plan for ({lat}, {lon}): {e}")
        return plans
    
    def compare_locations(
        self,
        locations: List[tuple[float, float]],
        area_ha: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Compare farm potential across multiple locations.
        
        Returns:
            Comparison summary with rankings
        """
        plans = self.batch_generate(locations, area_ha)
        
        if not plans:
            return {"error": "No plans generated"}
        
        # Rank by different metrics
        by_profit = sorted(plans, key=lambda p: p.expected_annual_profit, reverse=True)
        by_roi = sorted(plans, key=lambda p: p.expected_roi_pct, reverse=True)
        by_sustainability = sorted(plans, key=lambda p: p.sustainability_score, reverse=True)
        
        return {
            "locations_analyzed": len(plans),
            "best_by_profit": {
                "lat": by_profit[0].lat,
                "lon": by_profit[0].lon,
                "profit": by_profit[0].expected_annual_profit,
            },
            "best_by_roi": {
                "lat": by_roi[0].lat,
                "lon": by_roi[0].lon,
                "roi_pct": by_roi[0].expected_roi_pct,
            },
            "best_by_sustainability": {
                "lat": by_sustainability[0].lat,
                "lon": by_sustainability[0].lon,
                "score": by_sustainability[0].sustainability_score,
            },
            "all_plans": [p.to_dict() for p in plans],
        }
    
    def train_models(
        self,
        training_data_path: Optional[str] = None,
        n_samples: int = 600,
        save_dir: Optional[str] = None,
    ):
        """
        Train ML models on generated or provided data.
        
        Args:
            training_data_path: Path to existing training data JSON
            n_samples: Number of samples to generate if no data provided
            save_dir: Directory to save trained models
        """
        from src.ml.training.data_generator import TrainingDataGenerator
        
        generator = TrainingDataGenerator(use_weather=False)  # Faster without API
        
        if training_data_path:
            samples = generator.load(training_data_path)
        else:
            print(f"Generating {n_samples} training samples...")
            samples = generator.generate_aez_stratified(samples_per_zone=n_samples // 6)
        
        print(f"Training on {len(samples)} samples...")
        
        X, y_yields, y_enterprises = generator.to_arrays(samples)
        
        # Train yield predictor
        self.yield_predictor.fit(X, y_yields)
        
        # Enterprise recommender uses heuristics (no training needed)
        # But we could train a classifier for top-enterprise prediction
        
        if save_dir:
            save_path = Path(save_dir)
            self.yield_predictor.save(save_path)
            print(f"Models saved to {save_path}")
