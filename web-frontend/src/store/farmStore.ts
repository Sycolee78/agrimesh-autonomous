import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type {
  Coordinates,
  FarmConfig,
  FarmType,
  LivestockConfig,
  CropConfig,
  BuildingConfig,
  FarmZone,
  SimulationResult,
  MapMode,
} from "@/types/farm";

// ============================================================================
// Store Interface
// ============================================================================

interface FarmStore {
  // Map State
  mapCenter: Coordinates;
  mapZoom: number;
  mapMode: MapMode;
  selectedLocation: Coordinates | null;

  // Farm Configuration
  farmConfig: FarmConfig | null;
  
  // Simulation Results
  simulationResult: SimulationResult | null;
  isSimulating: boolean;

  // UI State
  sidebarOpen: boolean;
  activeTab: "config" | "simulation" | "results";

  // Map Actions
  setMapCenter: (center: Coordinates) => void;
  setMapZoom: (zoom: number) => void;
  setMapMode: (mode: MapMode) => void;
  selectLocation: (location: Coordinates | null) => void;

  // Farm Config Actions
  initializeFarm: (location: Coordinates, areaHa: number) => void;
  updateFarmType: (type: FarmType) => void;
  updateLivestock: (livestock: Partial<LivestockConfig>) => void;
  addCrop: (crop: CropConfig) => void;
  removeCrop: (cropType: string) => void;
  addBuilding: (building: BuildingConfig) => void;
  removeBuilding: (buildingId: string) => void;
  addZone: (zone: FarmZone) => void;
  removeZone: (zoneId: string) => void;
  updateZone: (zoneId: string, updates: Partial<FarmZone>) => void;
  resetFarm: () => void;

  // Simulation Actions
  setSimulationResult: (result: SimulationResult | null) => void;
  setIsSimulating: (loading: boolean) => void;

  // UI Actions
  toggleSidebar: () => void;
  setActiveTab: (tab: "config" | "simulation" | "results") => void;
}

// ============================================================================
// Default Values
// ============================================================================

const defaultLivestock: LivestockConfig = {
  chickens: 0,
  cows: 0,
  goats: 0,
  sheep: 0,
  pigs: 0,
};

const createDefaultFarmConfig = (
  location: Coordinates,
  areaHa: number
): FarmConfig => ({
  id: `farm-${Date.now()}`,
  name: "My Farm",
  location,
  areaHa,
  farmType: "mixed",
  livestock: { ...defaultLivestock },
  crops: [],
  buildings: [],
  zones: [],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
});

// Zimbabwe center coordinates
const ZIMBABWE_CENTER: Coordinates = { lat: -19.0, lng: 29.0 };

// ============================================================================
// Store Implementation
// ============================================================================

export const useFarmStore = create<FarmStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        mapCenter: ZIMBABWE_CENTER,
        mapZoom: 6,
        mapMode: "view",
        selectedLocation: null,
        farmConfig: null,
        simulationResult: null,
        isSimulating: false,
        sidebarOpen: true,
        activeTab: "config",

        // Map Actions
        setMapCenter: (center) => set({ mapCenter: center }),
        setMapZoom: (zoom) => set({ mapZoom: zoom }),
        setMapMode: (mode) => set({ mapMode: mode }),
        selectLocation: (location) =>
          set({
            selectedLocation: location,
            mapMode: location ? "select" : "view",
          }),

        // Farm Config Actions
        initializeFarm: (location, areaHa) =>
          set({
            farmConfig: createDefaultFarmConfig(location, areaHa),
            selectedLocation: location,
            mapCenter: location,
            mapZoom: 15,
            activeTab: "config",
            sidebarOpen: true,
          }),

        updateFarmType: (type) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  farmType: type,
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        updateLivestock: (livestock) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  livestock: { ...state.farmConfig.livestock, ...livestock },
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        addCrop: (crop) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  crops: [...state.farmConfig.crops, crop],
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        removeCrop: (cropType) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  crops: state.farmConfig.crops.filter(
                    (c) => c.type !== cropType
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        addBuilding: (building) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  buildings: [...state.farmConfig.buildings, building],
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        removeBuilding: (buildingId) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  buildings: state.farmConfig.buildings.filter(
                    (b) => b.id !== buildingId
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        addZone: (zone) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  zones: [...state.farmConfig.zones, zone],
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        removeZone: (zoneId) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  zones: state.farmConfig.zones.filter((z) => z.id !== zoneId),
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        updateZone: (zoneId, updates) =>
          set((state) => ({
            farmConfig: state.farmConfig
              ? {
                  ...state.farmConfig,
                  zones: state.farmConfig.zones.map((z) =>
                    z.id === zoneId ? { ...z, ...updates } : z
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : null,
          })),

        resetFarm: () =>
          set({
            farmConfig: null,
            simulationResult: null,
            selectedLocation: null,
            mapMode: "view",
            activeTab: "config",
          }),

        // Simulation Actions
        setSimulationResult: (result) => set({ simulationResult: result }),
        setIsSimulating: (loading) => set({ isSimulating: loading }),

        // UI Actions
        toggleSidebar: () =>
          set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setActiveTab: (tab) => set({ activeTab: tab }),
      }),
      {
        name: "agrimesh-farm-storage",
        partialize: (state) => ({
          farmConfig: state.farmConfig,
          mapCenter: state.mapCenter,
          mapZoom: state.mapZoom,
        }),
      }
    )
  )
);
