/**
 * AgriMesh API Service
 * 
 * Handles communication with the backend simulation engine.
 * Currently includes mock data for development; will connect to
 * the Python backend API in production.
 */

import type {
  Coordinates,
  FarmConfig,
  SimulationResult,
  AEZZone,
  WeatherData,
  SoilData,
  CropSuitability,
  LivestockAnalysis,
  SustainabilityMetrics,
  ProfitEstimate,
  ResourceRequirements,
  CropType,
} from "@/types/farm";

// ============================================================================
// API Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Zimbabwe AEZ Data (embedded for offline use)
// ============================================================================

export const ZIMBABWE_AEZ_ZONES: Record<string, AEZZone> = {
  I: {
    id: "I",
    name: "Specialized & Diversified Farming",
    rainfallRange: ">1000mm",
    description: "High rainfall zone suitable for intensive farming",
    suitableCrops: ["maize", "vegetables", "potatoes", "tobacco", "wheat"],
    livestockCapacity: { cows: 1.5, goats: 3, sheep: 2, chickens: 100, pigs: 5 },
  },
  IIa: {
    id: "IIa",
    name: "Intensive Farming (High)",
    rainfallRange: "800-1000mm",
    description: "Good rainfall, suitable for intensive cropping",
    suitableCrops: ["maize", "sorghum", "groundnuts", "cotton", "tobacco"],
    livestockCapacity: { cows: 1.2, goats: 2.5, sheep: 1.5, chickens: 80, pigs: 4 },
  },
  IIb: {
    id: "IIb",
    name: "Intensive Farming (Low)",
    rainfallRange: "750-800mm",
    description: "Moderate-high rainfall zone",
    suitableCrops: ["maize", "sorghum", "groundnuts", "cotton"],
    livestockCapacity: { cows: 1.0, goats: 2, sheep: 1.5, chickens: 70, pigs: 3 },
  },
  III: {
    id: "III",
    name: "Semi-Intensive Farming",
    rainfallRange: "650-800mm",
    description: "Mixed crop-livestock zone",
    suitableCrops: ["maize", "sorghum", "groundnuts", "fodder"],
    livestockCapacity: { cows: 0.8, goats: 2, sheep: 1.2, chickens: 60, pigs: 2 },
  },
  IV: {
    id: "IV",
    name: "Semi-Extensive Farming",
    rainfallRange: "450-650mm",
    description: "Livestock focus with drought-tolerant crops",
    suitableCrops: ["sorghum", "groundnuts", "fodder"],
    livestockCapacity: { cows: 0.5, goats: 1.5, sheep: 1, chickens: 40, pigs: 1 },
  },
  V: {
    id: "V",
    name: "Extensive Farming",
    rainfallRange: "<500mm",
    description: "Cattle/game ranching only",
    suitableCrops: ["fodder"],
    livestockCapacity: { cows: 0.3, goats: 1, sheep: 0.5, chickens: 20, pigs: 0.5 },
  },
};

// ============================================================================
// AEZ Lookup (uses lat/lon to approximate zone)
// ============================================================================

export function lookupAEZZone(lat: number, lng: number): AEZZone {
  // Simplified Zimbabwe AEZ lookup based on latitude and longitude
  // In production, this would use proper geospatial boundaries
  
  if (lat > -18 && lng > 30) {
    return ZIMBABWE_AEZ_ZONES.I; // Eastern Highlands
  } else if (lat > -18.5 && lat < -17) {
    return ZIMBABWE_AEZ_ZONES.IIa; // Mashonaland
  } else if (lat >= -18.5 && lat < -19.5 && lng > 29) {
    return ZIMBABWE_AEZ_ZONES.IIb;
  } else if (lat >= -19.5 && lat < -20.5) {
    return ZIMBABWE_AEZ_ZONES.III; // Midlands
  } else if (lat >= -20.5 || lng < 28) {
    if (lng < 27) {
      return ZIMBABWE_AEZ_ZONES.V; // Victoria Falls area
    }
    return ZIMBABWE_AEZ_ZONES.IV; // Matabeleland
  }
  
  return ZIMBABWE_AEZ_ZONES.III; // Default
}

// ============================================================================
// Mock Weather Data Generator
// ============================================================================

function generateWeatherData(aez: AEZZone): WeatherData {
  const rainfallBase: Record<string, number> = {
    I: 1100,
    IIa: 900,
    IIb: 780,
    III: 700,
    IV: 550,
    V: 400,
  };
  
  const rainfall = rainfallBase[aez.id] + (Math.random() - 0.5) * 100;
  
  return {
    annualRainfallMm: Math.round(rainfall),
    avgTempC: 22 + (Math.random() - 0.5) * 4,
    rainyDays: Math.round(rainfall / 8),
    droughtRisk: rainfall < 500 ? "high" : rainfall < 700 ? "medium" : "low",
    frostRisk: aez.id === "I", // Eastern highlands have frost risk
  };
}

// ============================================================================
// Mock Soil Data Generator
// ============================================================================

function generateSoilData(aez: AEZZone): SoilData {
  const soilTypes: Record<string, string> = {
    I: "Red clay loam",
    IIa: "Sandy loam",
    IIb: "Sandy clay loam",
    III: "Sandy loam",
    IV: "Sandy soil",
    V: "Kalahari sand",
  };
  
  return {
    type: soilTypes[aez.id] || "Loam",
    ph: 5.5 + Math.random() * 1.5,
    organicMatter: aez.id === "I" || aez.id === "IIa" ? "high" : aez.id === "V" ? "low" : "medium",
    drainage: aez.id === "I" ? "moderate" : "good",
  };
}

// ============================================================================
// Crop Suitability Calculator
// ============================================================================

const CROP_BASE_YIELDS: Record<CropType, number> = {
  maize: 5.5,
  sorghum: 3.5,
  groundnuts: 2.0,
  wheat: 4.5,
  vegetables: 15.0,
  tobacco: 2.5,
  cotton: 3.0,
  fodder: 8.0,
  potatoes: 25.0,
};

const CROP_PRICES_USD: Record<CropType, number> = {
  maize: 250,
  sorghum: 200,
  groundnuts: 800,
  wheat: 300,
  vegetables: 500,
  tobacco: 4500,
  cotton: 1200,
  fodder: 100,
  potatoes: 300,
};

function calculateCropSuitability(
  crop: CropType,
  aez: AEZZone,
  weather: WeatherData
): CropSuitability {
  const isSuitable = aez.suitableCrops.includes(crop);
  const baseScore = isSuitable ? 70 : 30;
  
  // Weather modifiers
  let weatherModifier = 0;
  if (weather.droughtRisk === "low") weatherModifier += 15;
  else if (weather.droughtRisk === "high") weatherModifier -= 20;
  
  // Crop-specific modifiers
  let cropModifier = 0;
  if (crop === "sorghum" && weather.droughtRisk !== "low") cropModifier += 10;
  if (crop === "vegetables" && weather.annualRainfallMm > 800) cropModifier += 10;
  if (crop === "tobacco" && aez.id === "IIa") cropModifier += 15;
  
  const suitabilityScore = Math.min(100, Math.max(0, baseScore + weatherModifier + cropModifier));
  const yieldMultiplier = suitabilityScore / 80;
  const expectedYield = CROP_BASE_YIELDS[crop] * yieldMultiplier;
  
  const risks: string[] = [];
  if (weather.droughtRisk === "high") risks.push("High drought risk");
  if (weather.frostRisk && ["vegetables", "potatoes"].includes(crop)) risks.push("Frost damage possible");
  if (!isSuitable) risks.push("Not traditionally grown in this zone");
  
  return {
    crop,
    suitabilityScore,
    expectedYieldTHa: Math.round(expectedYield * 10) / 10,
    waterRequirementMm: Math.round(400 + (100 - suitabilityScore) * 3),
    profitPotentialUsd: Math.round(expectedYield * CROP_PRICES_USD[crop]),
    risks,
  };
}

// ============================================================================
// Livestock Analysis Calculator
// ============================================================================

const LIVESTOCK_REVENUE: Record<string, number> = {
  chickens: 15, // per bird per year
  cows: 800, // per head per year (milk + calves)
  goats: 150,
  sheep: 120,
  pigs: 200,
};

const LIVESTOCK_FEED_KG: Record<string, number> = {
  chickens: 0.12, // per day
  cows: 12,
  goats: 2,
  sheep: 1.5,
  pigs: 3,
};

const LIVESTOCK_WATER_L: Record<string, number> = {
  chickens: 0.25, // per day
  cows: 50,
  goats: 5,
  sheep: 4,
  pigs: 8,
};

function calculateLivestockAnalysis(
  type: keyof typeof LIVESTOCK_REVENUE,
  count: number
): LivestockAnalysis {
  return {
    type,
    count,
    feedRequirementKg: Math.round(count * LIVESTOCK_FEED_KG[type] * 365),
    waterRequirementL: Math.round(count * LIVESTOCK_WATER_L[type] * 365),
    manureOutputKg: Math.round(count * LIVESTOCK_FEED_KG[type] * 365 * 0.4), // ~40% conversion
    estimatedRevenueUsd: Math.round(count * LIVESTOCK_REVENUE[type]),
  };
}

// ============================================================================
// Sustainability Calculator
// ============================================================================

function calculateSustainability(
  farm: FarmConfig,
  cropResults: CropSuitability[],
  livestockResults: LivestockAnalysis[]
): SustainabilityMetrics {
  const synergies: SustainabilityMetrics["synergies"] = [];
  let bonusScore = 0;
  
  // Manure → fertilizer synergy
  const totalManure = livestockResults.reduce((sum, l) => sum + l.manureOutputKg, 0);
  const totalCropArea = farm.crops.reduce((sum, c) => sum + c.areaHa, 0);
  
  if (totalManure > 0 && totalCropArea > 0) {
    const manurePerHa = totalManure / totalCropArea;
    if (manurePerHa > 1000) {
      synergies.push({
        source: "Livestock manure",
        target: "Crop fertilization",
        benefit: "Reduces fertilizer costs by 40%",
        impactPercent: 40,
      });
      bonusScore += 15;
    }
  }
  
  // Crop residue → feed synergy
  if (farm.crops.some((c) => ["maize", "sorghum", "fodder"].includes(c.type))) {
    if (farm.livestock.cows > 0 || farm.livestock.goats > 0) {
      synergies.push({
        source: "Crop residues",
        target: "Livestock feed",
        benefit: "Reduces feed costs by 25%",
        impactPercent: 25,
      });
      bonusScore += 10;
    }
  }
  
  // Chickens → pest control
  if (farm.livestock.chickens > 50 && totalCropArea > 0) {
    synergies.push({
      source: "Free-range chickens",
      target: "Pest control",
      benefit: "Reduces pesticide needs by 30%",
      impactPercent: 30,
    });
    bonusScore += 8;
  }
  
  // Groundnuts → nitrogen fixation
  if (farm.crops.some((c) => c.type === "groundnuts")) {
    synergies.push({
      source: "Groundnuts (legume)",
      target: "Soil nitrogen",
      benefit: "Adds 40-60 kg N/ha to soil",
      impactPercent: 20,
    });
    bonusScore += 12;
  }
  
  // Base scores
  const diversityScore = Math.min(100, farm.crops.length * 15 + Object.values(farm.livestock).filter((v) => v > 0).length * 10);
  const waterScore = farm.crops.filter((c) => c.irrigated).length > 0 ? 70 : 85;
  
  const suggestions: string[] = [];
  if (totalManure < totalCropArea * 500) {
    suggestions.push("Consider adding more livestock for manure production");
  }
  if (!farm.crops.some((c) => c.type === "groundnuts")) {
    suggestions.push("Add groundnuts for nitrogen fixation benefits");
  }
  if (farm.buildings.filter((b) => b.type === "water_tank").length === 0) {
    suggestions.push("Install rainwater harvesting tanks");
  }
  if (farm.crops.filter((c) => c.irrigated).length === 0 && farm.areaHa > 2) {
    suggestions.push("Consider drip irrigation for vegetable plots");
  }
  
  const overallScore = Math.min(100, Math.round(
    (diversityScore * 0.3 + waterScore * 0.2 + 60 * 0.3 + bonusScore * 0.2)
  ));
  
  return {
    overallScore,
    waterEfficiency: waterScore,
    soilHealth: Math.min(100, 50 + bonusScore),
    biodiversity: diversityScore,
    carbonFootprint: 100 - (farm.livestock.cows * 2), // Cattle have higher carbon footprint
    synergies,
    suggestions,
  };
}

// ============================================================================
// Profit Calculator
// ============================================================================

function calculateProfit(
  farm: FarmConfig,
  cropResults: CropSuitability[],
  livestockResults: LivestockAnalysis[],
  sustainability: SustainabilityMetrics
): ProfitEstimate {
  const breakdown: ProfitEstimate["breakdownByEnterprise"] = [];
  
  // Crop profits
  for (const crop of farm.crops) {
    const suitability = cropResults.find((c) => c.crop === crop.type);
    if (suitability) {
      const revenue = suitability.profitPotentialUsd * crop.areaHa;
      const costs = revenue * 0.45; // ~45% cost ratio
      breakdown.push({
        enterprise: crop.type,
        revenue: Math.round(revenue),
        costs: Math.round(costs),
        profit: Math.round(revenue - costs),
      });
    }
  }
  
  // Livestock profits
  for (const livestock of livestockResults) {
    if (livestock.count > 0) {
      const revenue = livestock.estimatedRevenueUsd;
      const feedCost = livestock.feedRequirementKg * 0.3; // $0.30/kg feed
      const otherCosts = revenue * 0.2;
      const costs = feedCost + otherCosts;
      
      // Apply synergy discounts
      const feedDiscount = sustainability.synergies.find((s) => s.target === "Livestock feed");
      const adjustedCosts = feedDiscount ? costs * (1 - feedDiscount.impactPercent / 100 * 0.5) : costs;
      
      breakdown.push({
        enterprise: livestock.type,
        revenue: Math.round(revenue),
        costs: Math.round(adjustedCosts),
        profit: Math.round(revenue - adjustedCosts),
      });
    }
  }
  
  const totalRevenue = breakdown.reduce((sum, b) => sum + b.revenue, 0);
  const totalCosts = breakdown.reduce((sum, b) => sum + b.costs, 0);
  const netProfit = totalRevenue - totalCosts;
  
  return {
    totalRevenueUsd: totalRevenue,
    totalCostsUsd: totalCosts,
    netProfitUsd: netProfit,
    breakdownByEnterprise: breakdown,
    scenarios: {
      pessimistic: Math.round(netProfit * 0.6),
      expected: Math.round(netProfit),
      optimistic: Math.round(netProfit * 1.4),
    },
  };
}

// ============================================================================
// Resource Requirements Calculator
// ============================================================================

function calculateResources(
  farm: FarmConfig,
  livestockResults: LivestockAnalysis[]
): ResourceRequirements {
  const totalCropArea = farm.crops.reduce((sum, c) => sum + c.areaHa, 0);
  const irrigatedArea = farm.crops.filter((c) => c.irrigated).reduce((sum, c) => sum + c.areaHa, 0);
  
  const livestockWater = livestockResults.reduce((sum, l) => sum + l.waterRequirementL, 0) / 365;
  const irrigationWater = irrigatedArea * 50; // ~50L/day/ha for drip
  
  const livestockFeed = livestockResults.reduce((sum, l) => sum + l.feedRequirementKg, 0) / 365;
  
  return {
    waterLitersPerDay: Math.round(livestockWater + irrigationWater + 100), // +100 for household
    feedKgPerDay: Math.round(livestockFeed),
    fertilizerKgPerSeason: Math.round(totalCropArea * 150), // ~150 kg/ha
    laborHoursPerWeek: Math.round(farm.areaHa * 8 + Object.values(farm.livestock).reduce((a, b) => a + b, 0) * 0.5),
    fuelLitersPerMonth: Math.round(farm.areaHa * 5 + 20),
  };
}

// ============================================================================
// Main Simulation Function
// ============================================================================

export async function runSimulation(farm: FarmConfig): Promise<SimulationResult> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 1500));
  
  const aez = lookupAEZZone(farm.location.lat, farm.location.lng);
  const weather = generateWeatherData(aez);
  const soil = generateSoilData(aez);
  
  // Calculate crop suitability for all possible crops
  const allCrops: CropType[] = ["maize", "sorghum", "groundnuts", "wheat", "vegetables", "tobacco", "cotton", "fodder", "potatoes"];
  const cropSuitability = allCrops.map((crop) => calculateCropSuitability(crop, aez, weather));
  
  // Calculate livestock analysis
  const livestockAnalysis: LivestockAnalysis[] = [];
  for (const [type, count] of Object.entries(farm.livestock)) {
    if (count > 0) {
      livestockAnalysis.push(calculateLivestockAnalysis(type as keyof typeof LIVESTOCK_REVENUE, count));
    }
  }
  
  // Calculate sustainability
  const sustainability = calculateSustainability(farm, cropSuitability, livestockAnalysis);
  
  // Calculate profit
  const profitEstimate = calculateProfit(farm, cropSuitability, livestockAnalysis, sustainability);
  
  // Calculate resources
  const resources = calculateResources(farm, livestockAnalysis);
  
  return {
    farmId: farm.id,
    timestamp: new Date().toISOString(),
    location: farm.location,
    aezZone: aez,
    weather,
    soil,
    cropSuitability: cropSuitability.sort((a, b) => b.suitabilityScore - a.suitabilityScore),
    livestockAnalysis,
    sustainability,
    profitEstimate,
    resources,
  };
}

// ============================================================================
// Export Farm Plan
// ============================================================================

export function exportFarmPlan(farm: FarmConfig, result: SimulationResult): string {
  const exportData = {
    exportedAt: new Date().toISOString(),
    version: "1.0",
    farm,
    simulation: result,
  };
  
  return JSON.stringify(exportData, null, 2);
}
