/**
 * AgriMesh API Service
 * 
 * Connects to the FastAPI backend for simulation.
 * Falls back to mock data if backend is unavailable.
 */

import type {
  Coordinates,
  FarmConfig,
  SimulationResult,
  AEZZone,
  WeatherData,
  CropSuitability,
} from "@/types/farm";

// ============================================================================
// API Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// API Client
// ============================================================================

class ApiClient {
  private baseUrl: string;
  private useBackend: boolean = true;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.warn(`API call failed: ${endpoint}`, error);
      this.useBackend = false;
      throw error;
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      await this.fetch("/");
      this.useBackend = true;
      return true;
    } catch {
      this.useBackend = false;
      return false;
    }
  }

  async getAEZZone(lat: number, lng: number): Promise<AEZZone> {
    return this.fetch(`/api/aez/${lat}/${lng}`);
  }

  async getWeather(lat: number, lng: number): Promise<WeatherData> {
    return this.fetch(`/api/weather/${lat}/${lng}`);
  }

  async getCropSuitability(lat: number, lng: number): Promise<CropSuitability[]> {
    return this.fetch(`/api/crops/suitability/${lat}/${lng}`);
  }

  async simulate(farm: FarmConfig): Promise<SimulationResult> {
    return this.fetch("/api/simulate", {
      method: "POST",
      body: JSON.stringify(farm),
    });
  }

  async getLocations(): Promise<Record<string, { lat: number; lng: number; aez: string }>> {
    return this.fetch("/api/locations");
  }

  isBackendAvailable(): boolean {
    return this.useBackend;
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

// ============================================================================
// Zimbabwe AEZ Data (fallback for offline use)
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
// Fallback AEZ Lookup (used when API unavailable)
// ============================================================================

export function lookupAEZZone(lat: number, lng: number): AEZZone {
  if (lat > -18 && lng > 31) {
    return ZIMBABWE_AEZ_ZONES.I;
  } else if (lat > -18.5) {
    return ZIMBABWE_AEZ_ZONES.IIa;
  } else if (lat > -19.5 && lng > 29) {
    return ZIMBABWE_AEZ_ZONES.IIb;
  } else if (lat > -20.5) {
    return ZIMBABWE_AEZ_ZONES.III;
  } else if (lng < 27) {
    return ZIMBABWE_AEZ_ZONES.V;
  }
  return ZIMBABWE_AEZ_ZONES.IV;
}

// ============================================================================
// Mock Simulation (fallback when API unavailable)
// ============================================================================

import type {
  SoilData,
  LivestockAnalysis,
  SustainabilityMetrics,
  ProfitEstimate,
  ResourceRequirements,
  CropType,
} from "@/types/farm";

function generateMockWeather(aez: AEZZone): WeatherData {
  const rainfallBase: Record<string, number> = {
    I: 1100, IIa: 900, IIb: 780, III: 700, IV: 550, V: 400,
  };
  const rainfall = rainfallBase[aez.id] || 700;
  
  return {
    annualRainfallMm: rainfall,
    avgTempC: 24,
    rainyDays: Math.round(rainfall / 8),
    droughtRisk: rainfall < 500 ? "high" : rainfall < 700 ? "medium" : "low",
    frostRisk: aez.id === "I",
  };
}

function generateMockSoil(aez: AEZZone): SoilData {
  const soilTypes: Record<string, string> = {
    I: "Red clay loam", IIa: "Sandy loam", IIb: "Sandy clay loam",
    III: "Sandy loam", IV: "Sandy soil", V: "Kalahari sand",
  };
  
  return {
    type: soilTypes[aez.id] || "Loam",
    ph: 5.8,
    organicMatter: ["I", "IIa"].includes(aez.id) ? "high" : aez.id === "V" ? "low" : "medium",
    drainage: "good",
  };
}

const CROP_BASE_YIELDS: Record<string, number> = {
  maize: 5.5, sorghum: 3.5, groundnuts: 2.0, wheat: 4.5,
  vegetables: 15.0, tobacco: 2.5, cotton: 3.0, fodder: 8.0, potatoes: 25.0,
};

const CROP_PRICES: Record<string, number> = {
  maize: 250, sorghum: 200, groundnuts: 800, wheat: 300,
  vegetables: 500, tobacco: 4500, cotton: 1200, fodder: 100, potatoes: 300,
};

function calculateMockCropSuitability(
  crop: string,
  aez: AEZZone,
  weather: WeatherData
): CropSuitability {
  const isSuitable = aez.suitableCrops.includes(crop);
  let score = isSuitable ? 75 : 35;
  
  if (weather.droughtRisk === "low") score += 10;
  else if (weather.droughtRisk === "high") score -= 15;
  
  score = Math.max(0, Math.min(100, score));
  const baseYield = CROP_BASE_YIELDS[crop] || 3;
  const expectedYield = baseYield * (score / 80);
  
  return {
    crop: crop as CropType,
    suitabilityScore: score,
    expectedYieldTHa: Math.round(expectedYield * 10) / 10,
    waterRequirementMm: Math.round(400 + (100 - score) * 3),
    profitPotentialUsd: Math.round(expectedYield * (CROP_PRICES[crop] || 300)),
    risks: isSuitable ? [] : ["Not traditionally grown in this zone"],
  };
}

function calculateMockLivestock(type: string, count: number): LivestockAnalysis {
  const feed = { chickens: 0.12, cows: 12, goats: 2, sheep: 1.5, pigs: 3 };
  const water = { chickens: 0.25, cows: 50, goats: 5, sheep: 4, pigs: 8 };
  const revenue = { chickens: 15, cows: 800, goats: 150, sheep: 120, pigs: 200 };
  
  return {
    type: type as keyof typeof feed,
    count,
    feedRequirementKg: Math.round(count * (feed[type as keyof typeof feed] || 1) * 365),
    waterRequirementL: Math.round(count * (water[type as keyof typeof water] || 5) * 365),
    manureOutputKg: Math.round(count * (feed[type as keyof typeof feed] || 1) * 365 * 0.4),
    estimatedRevenueUsd: Math.round(count * (revenue[type as keyof typeof revenue] || 100)),
  };
}

function calculateMockSustainability(
  farm: FarmConfig,
  livestockResults: LivestockAnalysis[]
): SustainabilityMetrics {
  const synergies: SustainabilityMetrics["synergies"] = [];
  let bonus = 0;
  
  const totalManure = livestockResults.reduce((s, l) => s + l.manureOutputKg, 0);
  const totalCropArea = farm.crops.reduce((s, c) => s + c.areaHa, 0);
  
  if (totalManure > 1000 && totalCropArea > 0) {
    synergies.push({
      source: "Livestock manure",
      target: "Crop fertilization",
      benefit: "Reduces fertilizer costs by 40%",
      impactPercent: 40,
    });
    bonus += 15;
  }
  
  if (farm.crops.some(c => ["maize", "sorghum", "fodder"].includes(c.type))) {
    if (farm.livestock.cows > 0 || farm.livestock.goats > 0) {
      synergies.push({
        source: "Crop residues",
        target: "Livestock feed",
        benefit: "Reduces feed costs by 25%",
        impactPercent: 25,
      });
      bonus += 10;
    }
  }
  
  if (farm.livestock.chickens > 50 && totalCropArea > 0) {
    synergies.push({
      source: "Free-range chickens",
      target: "Pest control",
      benefit: "Reduces pesticide needs by 30%",
      impactPercent: 30,
    });
    bonus += 8;
  }
  
  if (farm.crops.some(c => c.type === "groundnuts")) {
    synergies.push({
      source: "Groundnuts (legume)",
      target: "Soil nitrogen",
      benefit: "Adds 40-60 kg N/ha to soil",
      impactPercent: 20,
    });
    bonus += 12;
  }
  
  const diversity = farm.crops.length * 15 + 
    Object.values(farm.livestock).filter(v => v > 0).length * 10;
  
  const suggestions: string[] = [];
  if (totalManure < totalCropArea * 500) suggestions.push("Add more livestock for manure");
  if (!farm.crops.some(c => c.type === "groundnuts")) suggestions.push("Add groundnuts for N-fixation");
  if (!farm.buildings.some(b => b.type === "water_tank")) suggestions.push("Install rainwater tanks");
  
  return {
    overallScore: Math.min(100, Math.round(diversity * 0.3 + 70 * 0.3 + bonus * 0.4)),
    waterEfficiency: 75,
    soilHealth: Math.min(100, 50 + bonus),
    biodiversity: Math.min(100, diversity),
    carbonFootprint: Math.max(0, 100 - farm.livestock.cows * 2),
    synergies,
    suggestions: suggestions.slice(0, 4),
  };
}

function calculateMockProfit(
  farm: FarmConfig,
  cropResults: CropSuitability[],
  livestockResults: LivestockAnalysis[]
): ProfitEstimate {
  const breakdown: ProfitEstimate["breakdownByEnterprise"] = [];
  
  for (const crop of farm.crops) {
    const suit = cropResults.find(c => c.crop === crop.type);
    if (suit) {
      const revenue = suit.profitPotentialUsd * crop.areaHa;
      const costs = revenue * 0.45;
      breakdown.push({
        enterprise: crop.type,
        revenue: Math.round(revenue),
        costs: Math.round(costs),
        profit: Math.round(revenue - costs),
      });
    }
  }
  
  for (const livestock of livestockResults) {
    if (livestock.count > 0) {
      const revenue = livestock.estimatedRevenueUsd;
      const costs = livestock.feedRequirementKg * 0.3 + revenue * 0.2;
      breakdown.push({
        enterprise: livestock.type,
        revenue: Math.round(revenue),
        costs: Math.round(costs),
        profit: Math.round(revenue - costs),
      });
    }
  }
  
  const totalRevenue = breakdown.reduce((s, b) => s + b.revenue, 0);
  const totalCosts = breakdown.reduce((s, b) => s + b.costs, 0);
  const netProfit = totalRevenue - totalCosts;
  
  return {
    totalRevenueUsd: totalRevenue,
    totalCostsUsd: totalCosts,
    netProfitUsd: netProfit,
    breakdownByEnterprise: breakdown,
    scenarios: {
      pessimistic: Math.round(netProfit * 0.6),
      expected: netProfit,
      optimistic: Math.round(netProfit * 1.4),
    },
  };
}

function calculateMockResources(
  farm: FarmConfig,
  livestockResults: LivestockAnalysis[]
): ResourceRequirements {
  const irrigatedArea = farm.crops.filter(c => c.irrigated).reduce((s, c) => s + c.areaHa, 0);
  const livestockWater = livestockResults.reduce((s, l) => s + l.waterRequirementL, 0) / 365;
  const livestockFeed = livestockResults.reduce((s, l) => s + l.feedRequirementKg, 0) / 365;
  
  return {
    waterLitersPerDay: Math.round(livestockWater + irrigatedArea * 50 + 100),
    feedKgPerDay: Math.round(livestockFeed),
    fertilizerKgPerSeason: Math.round(farm.crops.reduce((s, c) => s + c.areaHa, 0) * 150),
    laborHoursPerWeek: Math.round(farm.areaHa * 8 + Object.values(farm.livestock).reduce((a, b) => a + b, 0) * 0.5),
    fuelLitersPerMonth: Math.round(farm.areaHa * 5 + 20),
  };
}

async function runMockSimulation(farm: FarmConfig): Promise<SimulationResult> {
  await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
  
  const aez = lookupAEZZone(farm.location.lat, farm.location.lng);
  const weather = generateMockWeather(aez);
  const soil = generateMockSoil(aez);
  
  const allCrops = ["maize", "sorghum", "groundnuts", "wheat", "vegetables", "tobacco", "cotton", "fodder", "potatoes"];
  const cropSuitability = allCrops.map(c => calculateMockCropSuitability(c, aez, weather))
    .sort((a, b) => b.suitabilityScore - a.suitabilityScore);
  
  const livestockAnalysis: LivestockAnalysis[] = [];
  for (const [type, count] of Object.entries(farm.livestock)) {
    if (count > 0) {
      livestockAnalysis.push(calculateMockLivestock(type, count));
    }
  }
  
  const sustainability = calculateMockSustainability(farm, livestockAnalysis);
  const profitEstimate = calculateMockProfit(farm, cropSuitability, livestockAnalysis);
  const resources = calculateMockResources(farm, livestockAnalysis);
  
  return {
    farmId: farm.id,
    timestamp: new Date().toISOString(),
    location: farm.location,
    aezZone: aez,
    weather,
    soil,
    cropSuitability,
    livestockAnalysis,
    sustainability,
    profitEstimate,
    resources,
  };
}

// ============================================================================
// Main Simulation Function
// ============================================================================

export async function runSimulation(farm: FarmConfig): Promise<SimulationResult> {
  // Try backend first
  try {
    const isAvailable = await apiClient.checkHealth();
    if (isAvailable) {
      console.log("Using backend API for simulation");
      return await apiClient.simulate(farm);
    }
  } catch (error) {
    console.warn("Backend unavailable, using mock simulation");
  }
  
  // Fallback to mock
  console.log("Using mock simulation");
  return runMockSimulation(farm);
}

// ============================================================================
// Export Farm Plan
// ============================================================================

export function exportFarmPlan(farm: FarmConfig, result: SimulationResult): string {
  return JSON.stringify({
    exportedAt: new Date().toISOString(),
    version: "1.0",
    farm,
    simulation: result,
  }, null, 2);
}
