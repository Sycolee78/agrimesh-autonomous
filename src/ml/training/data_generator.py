"""
Training Data Generator

Generates synthetic training data for ML models using:
1. Zimbabwe AEZ knowledge (domain rules)
2. Real weather data from Open-Meteo
3. Random sampling with noise for diversity
"""

from __future__ import annotations

import json
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

from src.ml.features.extractor import FeatureExtractor, ZIM_LAT_RANGE, ZIM_LON_RANGE, CROP_CATALOG
from src.ml.models.yield_predictor import CROP_CATALOG as YIELD_CATALOG


@dataclass
class TrainingSample:
    """A single training sample."""
    lat: float
    lon: float
    features: List[float]
    yields: Dict[str, float]  # crop_id -> yield
    best_enterprises: List[str]  # Top 5 enterprise IDs
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TrainingDataGenerator:
    """
    Generates training data for AgriMesh ML models.
    
    Uses a combination of:
    - Grid sampling across Zimbabwe
    - Random jittering for diversity
    - Domain knowledge for yield estimation
    - Weather data for realism
    """
    
    def __init__(self, use_weather: bool = True, seed: int = 42):
        self.extractor = FeatureExtractor(use_weather_api=use_weather)
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
    
    def generate_grid(
        self,
        n_lat: int = 20,
        n_lon: int = 20,
        jitter: float = 0.1,
    ) -> List[TrainingSample]:
        """
        Generate training samples on a grid across Zimbabwe.
        
        Args:
            n_lat: Number of latitude divisions
            n_lon: Number of longitude divisions
            jitter: Random jitter as fraction of grid cell
            
        Returns:
            List of TrainingSample objects
        """
        samples = []
        
        lat_step = (ZIM_LAT_RANGE[1] - ZIM_LAT_RANGE[0]) / n_lat
        lon_step = (ZIM_LON_RANGE[1] - ZIM_LON_RANGE[0]) / n_lon
        
        for i in range(n_lat):
            for j in range(n_lon):
                base_lat = ZIM_LAT_RANGE[0] + (i + 0.5) * lat_step
                base_lon = ZIM_LON_RANGE[0] + (j + 0.5) * lon_step
                
                # Add jitter
                lat = base_lat + self.rng.uniform(-jitter, jitter) * lat_step
                lon = base_lon + self.rng.uniform(-jitter, jitter) * lon_step
                
                # Clamp to bounds
                lat = max(ZIM_LAT_RANGE[0], min(ZIM_LAT_RANGE[1], lat))
                lon = max(ZIM_LON_RANGE[0], min(ZIM_LON_RANGE[1], lon))
                
                try:
                    sample = self._generate_sample(lat, lon)
                    samples.append(sample)
                except Exception as e:
                    print(f"Warning: Failed to generate sample at ({lat}, {lon}): {e}")
        
        return samples
    
    def generate_random(self, n_samples: int = 1000) -> List[TrainingSample]:
        """
        Generate random training samples across Zimbabwe.
        
        Args:
            n_samples: Number of samples to generate
            
        Returns:
            List of TrainingSample objects
        """
        samples = []
        
        for _ in range(n_samples):
            lat = self.rng.uniform(*ZIM_LAT_RANGE)
            lon = self.rng.uniform(*ZIM_LON_RANGE)
            
            try:
                sample = self._generate_sample(lat, lon)
                samples.append(sample)
            except Exception as e:
                print(f"Warning: Failed to generate sample: {e}")
        
        return samples
    
    def generate_aez_stratified(
        self,
        samples_per_zone: int = 100,
    ) -> List[TrainingSample]:
        """
        Generate stratified samples ensuring coverage of all AEZ zones.
        
        Args:
            samples_per_zone: Number of samples per AEZ zone
            
        Returns:
            List of TrainingSample objects
        """
        from src.ml.features.extractor import AEZ_ZONES
        
        samples = []
        
        for zone_id, zone in AEZ_ZONES.items():
            for _ in range(samples_per_zone):
                # Pick a random region within this zone
                region = self.rng.choice(zone["regions"])
                lat_min, lat_max, lon_min, lon_max = region
                
                lat = self.rng.uniform(lat_min, lat_max)
                lon = self.rng.uniform(lon_min, lon_max)
                
                try:
                    sample = self._generate_sample(lat, lon)
                    samples.append(sample)
                except Exception as e:
                    print(f"Warning: Failed for zone {zone_id}: {e}")
        
        return samples
    
    def _generate_sample(self, lat: float, lon: float) -> TrainingSample:
        """Generate a single training sample."""
        # Extract features
        features = self.extractor.extract(lat, lon)
        feature_vec = features.to_vector()
        
        # Estimate yields using domain knowledge
        yields = self._estimate_yields(feature_vec)
        
        # Determine best enterprises
        best_enterprises = self._rank_enterprises(feature_vec, yields)
        
        return TrainingSample(
            lat=round(lat, 4),
            lon=round(lon, 4),
            features=feature_vec.tolist(),
            yields=yields,
            best_enterprises=best_enterprises,
        )
    
    def _estimate_yields(self, features: np.ndarray) -> Dict[str, float]:
        """
        Estimate crop yields from features using domain knowledge.
        
        Adds realistic noise to create training signal.
        """
        yields = {}
        
        # Extract key features
        rainfall = features[0]
        reliability = features[1]
        temp = features[2]
        growing_days = features[4]
        soil_fertility = features[6]
        water_avail = features[9]
        
        # AEZ encoding (indices 15-20)
        aez_vec = features[15:21]
        aez_idx = np.argmax(aez_vec)
        aez_zones = ["I", "IIa", "IIb", "III", "IV", "V"]
        current_aez = aez_zones[aez_idx] if aez_vec[aez_idx] > 0.5 else "III"
        
        for crop_id, crop in YIELD_CATALOG.items():
            base_yield = crop["base_yield"]
            
            # AEZ suitability
            preferred = crop.get("aez_preference", [])
            if current_aez in preferred:
                aez_mod = 1.0
            elif any(z in preferred for z in ["IIa", "IIb", "III"] if aez_idx == aez_zones.index(z)):
                aez_mod = 0.8
            else:
                aez_mod = 0.5
            
            # Water modifier
            water_req = crop["water_requirement"]
            if rainfall >= water_req:
                water_mod = 1.0
            else:
                water_mod = 0.6 + 0.4 * (rainfall / water_req)
            
            # Boost with irrigation
            if water_avail > 0.7:
                water_mod = min(1.0, water_mod * 1.2)
            
            # Temperature modifier
            temp_opt = crop["temp_optimal"]
            temp_diff = abs(temp - temp_opt)
            temp_mod = max(0.5, 1.0 - 0.7 * temp_diff)
            
            # Soil modifier
            soil_mod = 0.6 + 0.4 * soil_fertility
            
            # Growing season modifier
            min_days = crop["min_growing_days"]
            actual_days = 80 + growing_days * 130
            if actual_days >= min_days:
                season_mod = min(1.1, 1.0 + 0.1 * (actual_days - min_days) / 50)
            else:
                season_mod = actual_days / min_days
            
            # Calculate yield
            total_mod = aez_mod * water_mod * temp_mod * soil_mod * season_mod
            
            # Add noise (±15%)
            noise = 1.0 + self.np_rng.uniform(-0.15, 0.15)
            
            final_yield = base_yield * total_mod * noise
            yields[crop_id] = round(max(0.1, final_yield), 2)
        
        return yields
    
    def _rank_enterprises(
        self, features: np.ndarray, yields: Dict[str, float]
    ) -> List[str]:
        """Rank enterprises based on expected profitability."""
        from src.ml.models.enterprise_recommender import ENTERPRISE_CATALOG
        
        scores = []
        
        for ent_id, ent in ENTERPRISE_CATALOG.items():
            if ent_id in yields:
                # Crop: use yield prediction
                profit = yields[ent_id] * YIELD_CATALOG.get(ent_id, {}).get("price_per_ton", 300)
                capital = ent.get("capital_per_ha", 500)
                score = profit / capital  # ROI proxy
            else:
                # Non-crop: use base profit
                profit = ent.get("profit_per_ha", 500)
                capital = ent.get("capital_per_ha", 500)
                score = profit / capital
            
            # Adjust for suitability
            aez_vec = features[15:21]
            aez_idx = np.argmax(aez_vec)
            aez_zones = ["I", "IIa", "IIb", "III", "IV", "V"]
            current_aez = aez_zones[aez_idx] if aez_vec[aez_idx] > 0.5 else "III"
            
            aez_suit = ent.get("aez_suitability", {}).get(current_aez, 0.5)
            score *= aez_suit
            
            scores.append((ent_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scores[:5]]
    
    def save(self, samples: List[TrainingSample], path: str):
        """Save training data to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [s.to_dict() for s in samples]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(samples)} samples to {path}")
    
    def load(self, path: str) -> List[TrainingSample]:
        """Load training data from JSON."""
        with open(path) as f:
            data = json.load(f)
        
        return [TrainingSample(**d) for d in data]
    
    def to_arrays(
        self, samples: List[TrainingSample]
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]:
        """
        Convert samples to numpy arrays for training.
        
        Returns:
            - X: Feature matrix (n_samples, n_features)
            - y_yields: Dict of crop yields {crop_id: (n_samples,)}
            - y_enterprises: Enterprise labels (n_samples, 5) - top 5 enterprise indices
        """
        X = np.array([s.features for s in samples])
        
        y_yields = {}
        for crop_id in YIELD_CATALOG.keys():
            y_yields[crop_id] = np.array([s.yields.get(crop_id, 0) for s in samples])
        
        # Enterprise labels (indices)
        from src.ml.models.enterprise_recommender import ENTERPRISE_CATALOG
        ent_ids = list(ENTERPRISE_CATALOG.keys())
        y_enterprises = np.array([
            [ent_ids.index(e) if e in ent_ids else 0 for e in s.best_enterprises]
            for s in samples
        ])
        
        return X, y_yields, y_enterprises
