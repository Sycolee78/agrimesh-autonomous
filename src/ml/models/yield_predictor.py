"""
Crop Yield Prediction Model

Predicts expected yield for different crops given location features.
Uses gradient boosting for interpretable predictions.
"""

from __future__ import annotations

import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class YieldPrediction:
    """Prediction result for a single crop."""
    crop_id: str
    crop_name: str
    predicted_yield_tons_ha: float
    confidence: float  # 0-1
    yield_range: Tuple[float, float]  # (low, high)
    limiting_factors: List[str]
    optimal_conditions: Dict[str, float]


# Crop metadata with base yields and requirements
CROP_CATALOG = {
    "maize": {
        "name": "Maize",
        "base_yield": 4.5,  # tons/ha under optimal conditions
        "water_requirement": 0.6,  # 0-1 normalized
        "temp_optimal": 0.5,  # normalized temp preference
        "min_growing_days": 120,
        "aez_preference": ["IIa", "IIb", "III"],
        "price_per_ton": 280,
    },
    "sorghum": {
        "name": "Sorghum",
        "base_yield": 3.0,
        "water_requirement": 0.35,
        "temp_optimal": 0.6,
        "min_growing_days": 90,
        "aez_preference": ["III", "IV", "V"],
        "price_per_ton": 250,
    },
    "groundnuts": {
        "name": "Groundnuts",
        "base_yield": 2.0,
        "water_requirement": 0.5,
        "temp_optimal": 0.55,
        "min_growing_days": 100,
        "aez_preference": ["IIa", "IIb", "III"],
        "price_per_ton": 800,
    },
    "cotton": {
        "name": "Cotton",
        "base_yield": 1.5,
        "water_requirement": 0.55,
        "temp_optimal": 0.6,
        "min_growing_days": 150,
        "aez_preference": ["IIb", "III"],
        "price_per_ton": 1500,
    },
    "tobacco": {
        "name": "Tobacco",
        "base_yield": 2.2,
        "water_requirement": 0.65,
        "temp_optimal": 0.5,
        "min_growing_days": 140,
        "aez_preference": ["IIa", "IIb"],
        "price_per_ton": 3500,
    },
    "soybeans": {
        "name": "Soybeans",
        "base_yield": 2.5,
        "water_requirement": 0.6,
        "temp_optimal": 0.45,
        "min_growing_days": 110,
        "aez_preference": ["IIa", "IIb"],
        "price_per_ton": 450,
    },
    "wheat": {
        "name": "Wheat",
        "base_yield": 4.0,
        "water_requirement": 0.5,
        "temp_optimal": 0.3,
        "min_growing_days": 100,
        "aez_preference": ["I", "IIa"],
        "price_per_ton": 320,
    },
    "vegetables": {
        "name": "Mixed Vegetables",
        "base_yield": 15.0,
        "water_requirement": 0.75,
        "temp_optimal": 0.45,
        "min_growing_days": 60,
        "aez_preference": ["I", "IIa", "IIb"],
        "price_per_ton": 400,
    },
    "potatoes": {
        "name": "Potatoes",
        "base_yield": 20.0,
        "water_requirement": 0.65,
        "temp_optimal": 0.35,
        "min_growing_days": 90,
        "aez_preference": ["I", "IIa"],
        "price_per_ton": 350,
    },
    "sunflower": {
        "name": "Sunflower",
        "base_yield": 1.8,
        "water_requirement": 0.4,
        "temp_optimal": 0.55,
        "min_growing_days": 90,
        "aez_preference": ["IIb", "III", "IV"],
        "price_per_ton": 420,
    },
}


class CropYieldPredictor:
    """
    ML model for predicting crop yields from location features.
    
    Architecture:
    - Separate model per crop (GradientBoosting)
    - Shared feature extractor
    - Ensemble for uncertainty estimation
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.is_fitted = False
        
        if not HAS_SKLEARN:
            print("Warning: scikit-learn not installed. Using heuristic predictions.")
    
    def predict(self, features: np.ndarray, crops: Optional[List[str]] = None) -> List[YieldPrediction]:
        """
        Predict yields for given location features.
        
        Args:
            features: Feature vector from FeatureExtractor (shape: (n_features,))
            crops: List of crop IDs to predict (default: all)
            
        Returns:
            List of YieldPrediction objects
        """
        if crops is None:
            crops = list(CROP_CATALOG.keys())
        
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        predictions = []
        
        for crop_id in crops:
            if crop_id not in CROP_CATALOG:
                continue
            
            crop_info = CROP_CATALOG[crop_id]
            
            if HAS_SKLEARN and self.is_fitted and crop_id in self.models:
                # Use trained ML model
                pred = self._predict_ml(features, crop_id)
            else:
                # Use heuristic model
                pred = self._predict_heuristic(features[0], crop_id, crop_info)
            
            predictions.append(pred)
        
        # Sort by predicted yield * price (economic value)
        predictions.sort(
            key=lambda p: p.predicted_yield_tons_ha * CROP_CATALOG[p.crop_id]["price_per_ton"],
            reverse=True,
        )
        
        return predictions
    
    def _predict_heuristic(
        self, features: np.ndarray, crop_id: str, crop_info: Dict
    ) -> YieldPrediction:
        """
        Heuristic yield prediction based on feature analysis.
        
        Uses domain knowledge to estimate yield without ML training.
        """
        base_yield = crop_info["base_yield"]
        
        # Extract relevant features
        rainfall_norm = features[0]
        rainfall_reliability = features[1]
        temp_norm = features[2]
        growing_days_norm = features[4]
        soil_fertility = features[6]
        water_availability = features[9]
        
        # AEZ one-hot encoding (indices 15-20)
        aez_scores = {
            "I": features[15],
            "IIa": features[16],
            "IIb": features[17],
            "III": features[18],
            "IV": features[19],
            "V": features[20],
        }
        
        # Calculate yield modifiers
        modifiers = []
        limiting_factors = []
        
        # 1. Water availability modifier
        water_req = crop_info["water_requirement"]
        water_diff = abs(rainfall_norm - water_req)
        if rainfall_norm < water_req - 0.2:
            water_mod = 0.5 + 0.5 * (rainfall_norm / water_req)
            limiting_factors.append("insufficient_rainfall")
        elif rainfall_norm > water_req + 0.3:
            water_mod = 0.9  # Too much water
            limiting_factors.append("excess_moisture")
        else:
            water_mod = 1.0 - 0.3 * water_diff
        modifiers.append(("water", water_mod))
        
        # 2. Temperature modifier
        temp_optimal = crop_info["temp_optimal"]
        temp_diff = abs(temp_norm - temp_optimal)
        temp_mod = max(0.4, 1.0 - 0.8 * temp_diff)
        if temp_diff > 0.3:
            limiting_factors.append("suboptimal_temperature")
        modifiers.append(("temperature", temp_mod))
        
        # 3. Growing season modifier
        min_days = crop_info["min_growing_days"]
        actual_days = 80 + growing_days_norm * 130  # Denormalize
        if actual_days < min_days:
            season_mod = actual_days / min_days
            limiting_factors.append("short_growing_season")
        else:
            season_mod = min(1.1, 1.0 + 0.1 * (actual_days - min_days) / 50)
        modifiers.append(("growing_season", season_mod))
        
        # 4. Soil fertility modifier
        soil_mod = 0.5 + 0.5 * soil_fertility
        if soil_fertility < 0.4:
            limiting_factors.append("poor_soil_fertility")
        modifiers.append(("soil", soil_mod))
        
        # 5. AEZ suitability modifier
        preferred_zones = crop_info["aez_preference"]
        aez_mod = 0.6  # Base if not in preferred zone
        for zone in preferred_zones:
            if aez_scores.get(zone, 0) > 0.5:
                aez_mod = 1.0
                break
        if aez_mod < 1.0:
            limiting_factors.append("suboptimal_aez")
        modifiers.append(("aez", aez_mod))
        
        # 6. Water availability bonus (irrigation potential)
        if water_availability > 0.7:
            water_bonus = 1.1
        else:
            water_bonus = 0.9 + 0.2 * water_availability
        modifiers.append(("water_access", water_bonus))
        
        # Calculate final yield
        total_modifier = 1.0
        for name, mod in modifiers:
            total_modifier *= mod
        
        predicted_yield = base_yield * total_modifier
        
        # Calculate confidence based on data quality and limiting factors
        confidence = max(0.3, 0.9 - 0.1 * len(limiting_factors))
        confidence *= rainfall_reliability  # Adjust for climate reliability
        
        # Calculate yield range (±20% base, wider for low confidence)
        range_factor = 0.15 + 0.15 * (1 - confidence)
        yield_low = predicted_yield * (1 - range_factor)
        yield_high = predicted_yield * (1 + range_factor)
        
        # Optimal conditions for this crop at this location
        optimal_conditions = {
            "rainfall_needed": water_req,
            "temperature_optimal": temp_optimal,
            "soil_fertility_min": 0.6,
            "growing_days_min": min_days,
        }
        
        return YieldPrediction(
            crop_id=crop_id,
            crop_name=crop_info["name"],
            predicted_yield_tons_ha=round(predicted_yield, 2),
            confidence=round(confidence, 2),
            yield_range=(round(yield_low, 2), round(yield_high, 2)),
            limiting_factors=limiting_factors,
            optimal_conditions=optimal_conditions,
        )
    
    def _predict_ml(self, features: np.ndarray, crop_id: str) -> YieldPrediction:
        """Predict using trained ML model."""
        model = self.models[crop_id]
        scaler = self.scalers.get(crop_id)
        
        if scaler:
            features_scaled = scaler.transform(features)
        else:
            features_scaled = features
        
        pred = model.predict(features_scaled)[0]
        
        # Use model's built-in uncertainty if available
        if hasattr(model, "staged_predict"):
            # GradientBoosting: use staged predictions for uncertainty
            staged = list(model.staged_predict(features_scaled))
            std = np.std([s[0] for s in staged[-10:]])
        else:
            std = pred * 0.15  # Fallback: 15% uncertainty
        
        crop_info = CROP_CATALOG[crop_id]
        
        return YieldPrediction(
            crop_id=crop_id,
            crop_name=crop_info["name"],
            predicted_yield_tons_ha=round(float(pred), 2),
            confidence=round(float(max(0.3, 1.0 - std / pred)), 2),
            yield_range=(round(float(pred - 2*std), 2), round(float(pred + 2*std), 2)),
            limiting_factors=[],
            optimal_conditions={},
        )
    
    def fit(self, X: np.ndarray, y: Dict[str, np.ndarray], **kwargs):
        """
        Train yield prediction models.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Dictionary mapping crop_id to yield array (n_samples,)
        """
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn required for training")
        
        for crop_id, yields in y.items():
            if crop_id not in CROP_CATALOG:
                continue
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train model
            model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                **kwargs,
            )
            model.fit(X_scaled, yields)
            
            self.models[crop_id] = model
            self.scalers[crop_id] = scaler
        
        self.is_fitted = True
    
    def save(self, path: str):
        """Save trained models to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        for crop_id in self.models:
            with open(path / f"{crop_id}_model.pkl", "wb") as f:
                pickle.dump(self.models[crop_id], f)
            with open(path / f"{crop_id}_scaler.pkl", "wb") as f:
                pickle.dump(self.scalers[crop_id], f)
        
        # Save metadata
        meta = {
            "crops": list(self.models.keys()),
            "is_fitted": self.is_fitted,
        }
        with open(path / "metadata.json", "w") as f:
            json.dump(meta, f)
    
    def load(self, path: str):
        """Load trained models from disk."""
        path = Path(path)
        
        if not (path / "metadata.json").exists():
            raise FileNotFoundError(f"No model found at {path}")
        
        with open(path / "metadata.json") as f:
            meta = json.load(f)
        
        for crop_id in meta["crops"]:
            with open(path / f"{crop_id}_model.pkl", "rb") as f:
                self.models[crop_id] = pickle.load(f)
            with open(path / f"{crop_id}_scaler.pkl", "rb") as f:
                self.scalers[crop_id] = pickle.load(f)
        
        self.is_fitted = meta["is_fitted"]
    
    def get_feature_importance(self, crop_id: str) -> Dict[str, float]:
        """Get feature importance for a trained model."""
        if not self.is_fitted or crop_id not in self.models:
            return {}
        
        from src.ml.features.extractor import LocationFeatures
        
        model = self.models[crop_id]
        importance = model.feature_importances_
        feature_names = LocationFeatures.feature_names()
        
        return dict(sorted(
            zip(feature_names, importance),
            key=lambda x: x[1],
            reverse=True,
        ))
