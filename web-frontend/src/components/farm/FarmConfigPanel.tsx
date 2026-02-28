"use client";

import { useState } from "react";
import { useFarmStore } from "@/store/farmStore";
import { runSimulation } from "@/lib/api";
import type { CropType, BuildingType, FarmType } from "@/types/farm";
import {
  ChevronDown,
  ChevronUp,
  Wheat,
  Bird,
  Building2,
  Droplets,
  Leaf,
  Trash2,
  Plus,
  Play,
} from "lucide-react";

// ============================================================================
// Section Components
// ============================================================================

interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function CollapsibleSection({
  title,
  icon,
  children,
  defaultOpen = false,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium">{title}</span>
        </div>
        {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>
      {isOpen && <div className="p-4 space-y-4">{children}</div>}
    </div>
  );
}

// ============================================================================
// Farm Type Selector
// ============================================================================

function FarmTypeSelector() {
  const { farmConfig, updateFarmType } = useFarmStore();

  const types: { value: FarmType; label: string; icon: string }[] = [
    { value: "crops", label: "Crops Only", icon: "🌾" },
    { value: "livestock", label: "Livestock Only", icon: "🐄" },
    { value: "mixed", label: "Mixed Farm", icon: "🏡" },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {types.map((type) => (
        <button
          key={type.value}
          onClick={() => updateFarmType(type.value)}
          className={`p-3 rounded-lg border-2 text-center transition-all ${
            farmConfig?.farmType === type.value
              ? "border-green-500 bg-green-50"
              : "border-gray-200 hover:border-gray-300"
          }`}
        >
          <div className="text-2xl">{type.icon}</div>
          <div className="text-xs mt-1 font-medium">{type.label}</div>
        </button>
      ))}
    </div>
  );
}

// ============================================================================
// Livestock Configuration
// ============================================================================

function LivestockConfig() {
  const { farmConfig, updateLivestock } = useFarmStore();

  if (!farmConfig || farmConfig.farmType === "crops") return null;

  const livestockTypes = [
    { key: "chickens", label: "Chickens", icon: "🐔", max: 500, step: 10 },
    { key: "cows", label: "Cattle", icon: "🐄", max: 50, step: 1 },
    { key: "goats", label: "Goats", icon: "🐐", max: 100, step: 5 },
    { key: "sheep", label: "Sheep", icon: "🐑", max: 100, step: 5 },
    { key: "pigs", label: "Pigs", icon: "🐷", max: 50, step: 5 },
  ] as const;

  return (
    <div className="space-y-3">
      {livestockTypes.map(({ key, label, icon, max, step }) => (
        <div key={key} className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 min-w-[100px]">
            <span>{icon}</span>
            <span className="text-sm font-medium">{label}</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0}
              max={max}
              step={step}
              value={farmConfig.livestock[key]}
              onChange={(e) => updateLivestock({ [key]: Number(e.target.value) })}
              className="w-24 accent-green-600"
            />
            <input
              type="number"
              min={0}
              max={max}
              value={farmConfig.livestock[key]}
              onChange={(e) => updateLivestock({ [key]: Number(e.target.value) })}
              className="w-16 text-center border rounded px-2 py-1 text-sm"
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Crops Configuration
// ============================================================================

function CropsConfig() {
  const { farmConfig, addCrop, removeCrop } = useFarmStore();
  const [newCrop, setNewCrop] = useState<CropType>("maize");
  const [newArea, setNewArea] = useState(1);

  if (!farmConfig || farmConfig.farmType === "livestock") return null;

  const availableCrops: { value: CropType; label: string; icon: string }[] = [
    { value: "maize", label: "Maize", icon: "🌽" },
    { value: "sorghum", label: "Sorghum", icon: "🌾" },
    { value: "groundnuts", label: "Groundnuts", icon: "🥜" },
    { value: "vegetables", label: "Vegetables", icon: "🥬" },
    { value: "potatoes", label: "Potatoes", icon: "🥔" },
    { value: "tobacco", label: "Tobacco", icon: "🍃" },
    { value: "cotton", label: "Cotton", icon: "☁️" },
    { value: "fodder", label: "Fodder", icon: "🌿" },
    { value: "wheat", label: "Wheat", icon: "🌾" },
  ];

  const usedArea = farmConfig.crops.reduce((sum, c) => sum + c.areaHa, 0);
  const remainingArea = farmConfig.areaHa - usedArea;

  const handleAddCrop = () => {
    if (newArea > 0 && newArea <= remainingArea) {
      addCrop({
        type: newCrop,
        areaHa: newArea,
        irrigated: false,
      });
      setNewArea(Math.min(1, remainingArea - newArea));
    }
  };

  return (
    <div className="space-y-4">
      {/* Existing crops */}
      {farmConfig.crops.length > 0 && (
        <div className="space-y-2">
          {farmConfig.crops.map((crop) => {
            const cropInfo = availableCrops.find((c) => c.value === crop.type);
            return (
              <div
                key={crop.type}
                className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <span>{cropInfo?.icon}</span>
                  <span className="font-medium">{cropInfo?.label}</span>
                  <span className="text-sm text-gray-500">{crop.areaHa} ha</span>
                  {crop.irrigated && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      💧 Irrigated
                    </span>
                  )}
                </div>
                <button
                  onClick={() => removeCrop(crop.type)}
                  className="text-red-500 hover:text-red-700 p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Add new crop */}
      <div className="border-t pt-4">
        <p className="text-sm text-gray-600 mb-2">
          Available area: <strong>{remainingArea.toFixed(1)} ha</strong> of {farmConfig.areaHa} ha
        </p>
        <div className="flex gap-2">
          <select
            value={newCrop}
            onChange={(e) => setNewCrop(e.target.value as CropType)}
            className="flex-1 border rounded-md px-3 py-2 text-sm"
          >
            {availableCrops
              .filter((c) => !farmConfig.crops.some((fc) => fc.type === c.value))
              .map((crop) => (
                <option key={crop.value} value={crop.value}>
                  {crop.icon} {crop.label}
                </option>
              ))}
          </select>
          <input
            type="number"
            min={0.5}
            max={remainingArea}
            step={0.5}
            value={newArea}
            onChange={(e) => setNewArea(Number(e.target.value))}
            className="w-20 border rounded-md px-2 py-2 text-sm text-center"
          />
          <button
            onClick={handleAddCrop}
            disabled={remainingArea <= 0}
            className="bg-green-600 text-white px-3 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <Plus size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Buildings Configuration
// ============================================================================

function BuildingsConfig() {
  const { farmConfig, addBuilding, removeBuilding } = useFarmStore();

  if (!farmConfig) return null;

  const buildingTypes: { value: BuildingType; label: string; icon: string }[] = [
    { value: "barn", label: "Barn", icon: "🏠" },
    { value: "shed", label: "Shed", icon: "🛖" },
    { value: "storage", label: "Storage", icon: "📦" },
    { value: "greenhouse", label: "Greenhouse", icon: "🏡" },
    { value: "poultry_house", label: "Poultry House", icon: "🐔" },
    { value: "dairy_parlor", label: "Dairy Parlor", icon: "🥛" },
    { value: "water_tank", label: "Water Tank", icon: "💧" },
    { value: "borehole", label: "Borehole", icon: "🕳️" },
  ];

  const handleAddBuilding = (type: BuildingType) => {
    addBuilding({
      id: `building-${Date.now()}`,
      type,
      position: farmConfig.location, // Default to farm center
      size: { width: 10, height: 10 },
    });
  };

  return (
    <div className="space-y-4">
      {/* Existing buildings */}
      {farmConfig.buildings.length > 0 && (
        <div className="space-y-2">
          {farmConfig.buildings.map((building) => {
            const buildingInfo = buildingTypes.find((b) => b.value === building.type);
            return (
              <div
                key={building.id}
                className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <span>{buildingInfo?.icon}</span>
                  <span className="font-medium">{buildingInfo?.label}</span>
                </div>
                <button
                  onClick={() => removeBuilding(building.id)}
                  className="text-red-500 hover:text-red-700 p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Add building buttons */}
      <div className="grid grid-cols-4 gap-2">
        {buildingTypes.map((building) => (
          <button
            key={building.value}
            onClick={() => handleAddBuilding(building.value)}
            className="p-2 border rounded-lg hover:bg-gray-50 transition-colors text-center"
            title={building.label}
          >
            <div className="text-xl">{building.icon}</div>
            <div className="text-xs mt-1 truncate">{building.label}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Main Config Panel
// ============================================================================

export default function FarmConfigPanel() {
  const {
    farmConfig,
    isSimulating,
    setIsSimulating,
    setSimulationResult,
    setActiveTab,
    resetFarm,
  } = useFarmStore();

  if (!farmConfig) {
    return (
      <div className="p-6 text-center text-gray-500">
        <div className="text-4xl mb-4">🗺️</div>
        <h3 className="font-semibold text-lg mb-2">Select a Location</h3>
        <p className="text-sm">
          Click anywhere on the map to select a location for your farm.
        </p>
      </div>
    );
  }

  const handleRunSimulation = async () => {
    setIsSimulating(true);
    try {
      const result = await runSimulation(farmConfig);
      setSimulationResult(result);
      setActiveTab("results");
    } catch (error) {
      console.error("Simulation failed:", error);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-lg">{farmConfig.name}</h2>
            <p className="text-sm text-gray-500">{farmConfig.areaHa} hectares</p>
          </div>
          <button
            onClick={resetFarm}
            className="text-red-500 hover:text-red-700 text-sm"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Config Sections */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Farm Type */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Farm Type</h3>
          <FarmTypeSelector />
        </div>

        {/* Livestock */}
        <CollapsibleSection
          title="Livestock"
          icon={<Bird size={18} className="text-yellow-600" />}
          defaultOpen={farmConfig.farmType !== "crops"}
        >
          <LivestockConfig />
        </CollapsibleSection>

        {/* Crops */}
        <CollapsibleSection
          title="Crops"
          icon={<Wheat size={18} className="text-green-600" />}
          defaultOpen={farmConfig.farmType !== "livestock"}
        >
          <CropsConfig />
        </CollapsibleSection>

        {/* Buildings */}
        <CollapsibleSection
          title="Buildings & Infrastructure"
          icon={<Building2 size={18} className="text-gray-600" />}
        >
          <BuildingsConfig />
        </CollapsibleSection>
      </div>

      {/* Run Simulation Button */}
      <div className="p-4 border-t bg-gray-50">
        <button
          onClick={handleRunSimulation}
          disabled={isSimulating}
          className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 disabled:bg-green-400 disabled:cursor-wait transition-colors flex items-center justify-center gap-2 font-medium"
        >
          {isSimulating ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
              Simulating...
            </>
          ) : (
            <>
              <Play size={20} />
              Run Simulation
            </>
          )}
        </button>
      </div>
    </div>
  );
}
