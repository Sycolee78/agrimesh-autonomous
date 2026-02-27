"""
Non-linear crop yield response model.

Replaces the simplistic linear moisture→yield model with agronomically realistic curves.

Key concepts:
- Optimal moisture range: crops have a "sweet spot" (not "more is always better")
- Critical thresholds: yield drops sharply below wilting point
- Growth stage sensitivity: water needs vary through crop lifecycle
- Waterlogging penalty: excess water hurts yield
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class GrowthStage(Enum):
    """Crop growth stages with different water sensitivity."""
    GERMINATION = "germination"      # 0-10 days: moderate need
    VEGETATIVE = "vegetative"        # 10-40 days: moderate need
    FLOWERING = "flowering"          # 40-60 days: CRITICAL - highest need
    GRAIN_FILL = "grain_fill"        # 60-90 days: high need
    MATURITY = "maturity"            # 90-120 days: reduced need


@dataclass
class CropWaterProfile:
    """Water response parameters for a crop type."""
    name: str
    optimal_moisture_min: float      # Lower bound of optimal range
    optimal_moisture_max: float      # Upper bound of optimal range
    wilting_point: float             # Below this, yield drops sharply
    saturation_point: float          # Above this, waterlogging risk
    max_yield_potential: float       # t/ha under perfect conditions
    drought_sensitivity: float       # 0-1, how much yield drops per % below wilting
    waterlog_sensitivity: float      # 0-1, how much yield drops per % above saturation
    
    # Growth stage water demand multipliers
    stage_demand: Dict[GrowthStage, float] = None
    
    def __post_init__(self):
        if self.stage_demand is None:
            # Default demand profile (normalized to flowering = 1.0)
            self.stage_demand = {
                GrowthStage.GERMINATION: 0.6,
                GrowthStage.VEGETATIVE: 0.7,
                GrowthStage.FLOWERING: 1.0,      # Peak demand
                GrowthStage.GRAIN_FILL: 0.9,
                GrowthStage.MATURITY: 0.4,
            }


# Zimbabwe crop profiles (calibrated to local varieties)
CROP_PROFILES: Dict[str, CropWaterProfile] = {
    "maize": CropWaterProfile(
        name="maize",
        optimal_moisture_min=0.50,
        optimal_moisture_max=0.70,
        wilting_point=0.30,
        saturation_point=0.85,
        max_yield_potential=6.0,  # t/ha, good Zimbabwe conditions
        drought_sensitivity=0.8,
        waterlog_sensitivity=0.5,
    ),
    "sorghum": CropWaterProfile(
        name="sorghum",
        optimal_moisture_min=0.40,
        optimal_moisture_max=0.65,
        wilting_point=0.25,  # More drought tolerant
        saturation_point=0.80,
        max_yield_potential=4.5,
        drought_sensitivity=0.5,  # More resilient
        waterlog_sensitivity=0.6,
    ),
    "groundnuts": CropWaterProfile(
        name="groundnuts",
        optimal_moisture_min=0.45,
        optimal_moisture_max=0.65,
        wilting_point=0.28,
        saturation_point=0.80,
        max_yield_potential=2.5,
        drought_sensitivity=0.7,
        waterlog_sensitivity=0.7,
    ),
    "potato": CropWaterProfile(
        name="potato",
        optimal_moisture_min=0.60,
        optimal_moisture_max=0.80,
        wilting_point=0.35,  # Sensitive to drought
        saturation_point=0.90,
        max_yield_potential=25.0,  # t/ha (tuber crop)
        drought_sensitivity=0.9,  # Very sensitive
        waterlog_sensitivity=0.8,
    ),
    "vegetables": CropWaterProfile(
        name="vegetables",
        optimal_moisture_min=0.55,
        optimal_moisture_max=0.75,
        wilting_point=0.35,
        saturation_point=0.85,
        max_yield_potential=15.0,
        drought_sensitivity=0.85,
        waterlog_sensitivity=0.7,
    ),
}


def get_growth_stage(day_of_season: int, crop: str = "maize") -> GrowthStage:
    """
    Determine growth stage based on days since planting.
    
    Timings are approximate and crop-specific. Default is maize.
    """
    # Maize typical schedule (Zimbabwe rainy season: Nov-Apr)
    if crop in ("maize", "sorghum"):
        if day_of_season < 10:
            return GrowthStage.GERMINATION
        elif day_of_season < 40:
            return GrowthStage.VEGETATIVE
        elif day_of_season < 65:
            return GrowthStage.FLOWERING
        elif day_of_season < 100:
            return GrowthStage.GRAIN_FILL
        else:
            return GrowthStage.MATURITY
    elif crop == "groundnuts":
        if day_of_season < 15:
            return GrowthStage.GERMINATION
        elif day_of_season < 45:
            return GrowthStage.VEGETATIVE
        elif day_of_season < 75:
            return GrowthStage.FLOWERING
        elif day_of_season < 110:
            return GrowthStage.GRAIN_FILL
        else:
            return GrowthStage.MATURITY
    else:
        # Generic vegetables / potato
        if day_of_season < 10:
            return GrowthStage.GERMINATION
        elif day_of_season < 35:
            return GrowthStage.VEGETATIVE
        elif day_of_season < 55:
            return GrowthStage.FLOWERING
        elif day_of_season < 80:
            return GrowthStage.GRAIN_FILL
        else:
            return GrowthStage.MATURITY


def calculate_yield_factor(
    soil_moisture: float,
    crop: str = "maize",
    day_of_season: int = 30,
    cumulative_stress_days: int = 0,
) -> float:
    """
    Calculate yield factor (0-1) based on current moisture and crop profile.
    
    Returns a multiplier against max_yield_potential.
    
    The response curve:
    - Below wilting point: sharp exponential drop
    - Between wilting and optimal_min: gradual recovery
    - Within optimal range: 1.0 (full potential)
    - Above optimal_max but below saturation: slight reduction
    - Above saturation: waterlogging penalty
    """
    profile = CROP_PROFILES.get(crop, CROP_PROFILES["maize"])
    stage = get_growth_stage(day_of_season, crop)
    
    # Stage-based sensitivity multiplier
    # During flowering, stress has bigger impact
    stage_sensitivity = {
        GrowthStage.GERMINATION: 0.8,
        GrowthStage.VEGETATIVE: 0.7,
        GrowthStage.FLOWERING: 1.0,  # Most sensitive
        GrowthStage.GRAIN_FILL: 0.9,
        GrowthStage.MATURITY: 0.5,
    }.get(stage, 0.8)
    
    # Calculate base yield factor from moisture
    if soil_moisture < profile.wilting_point:
        # Severe drought stress - exponential drop
        deficit = profile.wilting_point - soil_moisture
        factor = max(0.1, 1.0 - (deficit * profile.drought_sensitivity * 3.0) ** 1.5)
    elif soil_moisture < profile.optimal_moisture_min:
        # Mild stress - linear reduction
        range_size = profile.optimal_moisture_min - profile.wilting_point
        position = (soil_moisture - profile.wilting_point) / range_size
        factor = 0.7 + (0.3 * position)  # 70% to 100%
    elif soil_moisture <= profile.optimal_moisture_max:
        # Optimal zone - full potential
        factor = 1.0
    elif soil_moisture < profile.saturation_point:
        # Slightly wet - minor reduction
        excess = soil_moisture - profile.optimal_moisture_max
        range_size = profile.saturation_point - profile.optimal_moisture_max
        factor = 1.0 - (excess / range_size * 0.15)  # Up to 15% reduction
    else:
        # Waterlogged - significant penalty
        excess = soil_moisture - profile.saturation_point
        factor = max(0.3, 0.85 - (excess * profile.waterlog_sensitivity * 2.0))
    
    # Apply stage sensitivity (stress during flowering hurts more)
    if factor < 1.0:
        stress_magnitude = 1.0 - factor
        factor = 1.0 - (stress_magnitude * stage_sensitivity)
    
    # Cumulative stress penalty (persistent stress compounds)
    if cumulative_stress_days > 0:
        cumulative_penalty = min(0.3, cumulative_stress_days * 0.01)
        factor = factor * (1.0 - cumulative_penalty)
    
    return max(0.0, min(1.0, factor))


def calculate_yield(
    avg_moisture: float,
    crop: str = "maize",
    day_of_season: int = 30,
    cumulative_stress_days: int = 0,
    area_ha: float = 1.0,
) -> float:
    """
    Calculate expected yield in tons for given conditions.
    """
    profile = CROP_PROFILES.get(crop, CROP_PROFILES["maize"])
    factor = calculate_yield_factor(avg_moisture, crop, day_of_season, cumulative_stress_days)
    return round(profile.max_yield_potential * factor * area_ha, 3)


def get_target_moisture(crop: str, day_of_season: int) -> float:
    """
    Get the irrigation target moisture for current growth stage.
    
    During critical stages (flowering), target higher end of optimal.
    During low-demand stages, target lower end (conserve water).
    """
    profile = CROP_PROFILES.get(crop, CROP_PROFILES["maize"])
    stage = get_growth_stage(day_of_season, crop)
    
    optimal_mid = (profile.optimal_moisture_min + profile.optimal_moisture_max) / 2
    optimal_range = profile.optimal_moisture_max - profile.optimal_moisture_min
    
    # Adjust target based on stage
    stage_offset = {
        GrowthStage.GERMINATION: 0.0,
        GrowthStage.VEGETATIVE: -0.1,    # Slightly drier OK
        GrowthStage.FLOWERING: 0.15,      # Target higher
        GrowthStage.GRAIN_FILL: 0.1,
        GrowthStage.MATURITY: -0.2,       # Can be drier
    }.get(stage, 0.0)
    
    target = optimal_mid + (optimal_range * stage_offset)
    return max(profile.optimal_moisture_min, min(profile.optimal_moisture_max, target))


def get_critical_threshold(crop: str) -> float:
    """Get the moisture level below which stress accumulates."""
    profile = CROP_PROFILES.get(crop, CROP_PROFILES["maize"])
    # Critical threshold is between wilting point and optimal min
    return profile.wilting_point + (profile.optimal_moisture_min - profile.wilting_point) * 0.5
