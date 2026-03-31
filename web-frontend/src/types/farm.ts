// ============================================================================
// Core Types for AgriMesh Farm Planning
// ============================================================================

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface AEZZone {
  id: string; // "I", "IIa", "IIb", "III", "IV", "V"
  name: string;
  rainfallRange: string;
  description: string;
  suitableCrops: string[];
  livestockCapacity: Record<string, number>; // animals per hectare
}

// ============================================================================
// Farm Configuration
// ============================================================================

export type FarmType = "crops" | "livestock" | "mixed";

export interface LivestockConfig {
  chickens: number;
  cows: number;
  goats: number;
  sheep: number;
  pigs: number;
}

export interface CropConfig {
  type: CropType;
  areaHa: number;
  irrigated: boolean;
}

export type CropType =
  | "maize"
  | "sorghum"
  | "groundnuts"
  | "wheat"
  | "vegetables"
  | "tobacco"
  | "cotton"
  | "fodder"
  | "potatoes";

export interface BuildingConfig {
  id: string;
  type: BuildingType;
  position: Coordinates;
  size: { width: number; height: number }; // meters
}

export type BuildingType =
  | "barn"
  | "shed"
  | "storage"
  | "greenhouse"
  | "poultry_house"
  | "dairy_parlor"
  | "water_tank"
  | "borehole";

export interface FarmZone {
  id: string;
  type: "crops" | "pasture" | "buildings" | "water";
  polygon: Coordinates[]; // GeoJSON-style polygon
  cropType?: CropType;
  label?: string;
}

export interface FarmConfig {
  id: string;
  name: string;
  location: Coordinates;
  areaHa: number;
  farmType: FarmType;
  aezZone?: string;
  livestock: LivestockConfig;
  crops: CropConfig[];
  buildings: BuildingConfig[];
  zones: FarmZone[];
  createdAt: string;
  updatedAt: string;
}

// ============================================================================
// Farm Profiles
// ============================================================================

export interface FarmProfile {
  profileId: string;
  profileName: string;
  description?: string;
  farmConfig: FarmConfig;
  createdAt: string;
  updatedAt: string;
}

// ============================================================================
// Simulation & Results
// ============================================================================

export interface WeatherData {
  annualRainfallMm: number;
  avgTempC: number;
  rainyDays: number;
  droughtRisk: "low" | "medium" | "high";
  frostRisk: boolean;
}

export interface SoilData {
  type: string;
  ph: number;
  organicMatter: "low" | "medium" | "high";
  drainage: "poor" | "moderate" | "good";
}

export interface CropSuitability {
  crop: CropType;
  suitabilityScore: number; // 0-100
  expectedYieldTHa: number;
  waterRequirementMm: number;
  profitPotentialUsd: number;
  risks: string[];
}

export interface LivestockAnalysis {
  type: keyof LivestockConfig;
  count: number;
  feedRequirementKg: number;
  waterRequirementL: number;
  manureOutputKg: number;
  estimatedRevenueUsd: number;
}

export interface SustainabilityMetrics {
  overallScore: number; // 0-100
  waterEfficiency: number;
  soilHealth: number;
  biodiversity: number;
  carbonFootprint: number;
  synergies: SynergyBonus[];
  suggestions: string[];
}

export interface SynergyBonus {
  source: string;
  target: string;
  benefit: string;
  impactPercent: number;
}

export interface ProfitEstimate {
  totalRevenueUsd: number;
  totalCostsUsd: number;
  netProfitUsd: number;
  breakdownByEnterprise: {
    enterprise: string;
    revenue: number;
    costs: number;
    profit: number;
  }[];
  scenarios: {
    pessimistic: number;
    expected: number;
    optimistic: number;
  };
}

export interface ResourceRequirements {
  waterLitersPerDay: number;
  feedKgPerDay: number;
  fertilizerKgPerSeason: number;
  laborHoursPerWeek: number;
  fuelLitersPerMonth: number;
}

export interface SimulationResult {
  farmId: string;
  timestamp: string;
  location: Coordinates;
  aezZone: AEZZone;
  weather: WeatherData;
  soil: SoilData;
  cropSuitability: CropSuitability[];
  livestockAnalysis: LivestockAnalysis[];
  sustainability: SustainabilityMetrics;
  profitEstimate: ProfitEstimate;
  resources: ResourceRequirements;
}

// ============================================================================
// UI State
// ============================================================================

export type MapMode = "view" | "select" | "draw" | "place";

export interface MapState {
  center: Coordinates;
  zoom: number;
  mode: MapMode;
  selectedLocation: Coordinates | null;
  drawingZone: FarmZone | null;
}

export interface UIState {
  sidebarOpen: boolean;
  activeTab: "config" | "simulation" | "results";
  loading: boolean;
  error: string | null;
}
