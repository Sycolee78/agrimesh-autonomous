"use client";

import dynamic from "next/dynamic";
import { useFarmStore } from "@/store/farmStore";
import FarmConfigPanel from "@/components/farm/FarmConfigPanel";
import ResultsDashboard from "@/components/dashboard/ResultsDashboard";
import {
  MapPin,
  Settings,
  BarChart3,
  Menu,
  X,
  Leaf,
  Github,
} from "lucide-react";

// Dynamic import for map (no SSR - Leaflet requires window)
const FarmMap = dynamic(() => import("@/components/map/FarmMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-gray-100 flex items-center justify-center">
      <div className="flex flex-col items-center gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-500 border-t-transparent" />
        <span className="text-gray-500">Loading map...</span>
      </div>
    </div>
  ),
});

// ============================================================================
// Sidebar Tab Button
// ============================================================================

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}

function TabButton({ active, onClick, icon, label, badge }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
        active
          ? "bg-green-100 text-green-700"
          : "text-gray-600 hover:bg-gray-100"
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className="bg-green-500 text-white text-xs px-1.5 py-0.5 rounded-full">
          {badge}
        </span>
      )}
    </button>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function HomePage() {
  const {
    sidebarOpen,
    toggleSidebar,
    activeTab,
    setActiveTab,
    farmConfig,
    simulationResult,
  } = useFarmStore();

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <button
            onClick={toggleSidebar}
            className="p-2 hover:bg-gray-100 rounded-lg lg:hidden"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <Leaf className="text-white" size={20} />
            </div>
            <div>
              <h1 className="font-bold text-lg text-gray-800">AgriMesh</h1>
              <p className="text-xs text-gray-500 -mt-1">Farm Planner</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {farmConfig && (
            <div className="hidden md:flex items-center gap-2 text-sm text-gray-600">
              <MapPin size={16} />
              <span>
                {farmConfig.location.lat.toFixed(4)}, {farmConfig.location.lng.toFixed(4)}
              </span>
            </div>
          )}
          <a
            href="https://github.com/Sycolee78/agrimesh-autonomous"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <Github size={20} className="text-gray-600" />
          </a>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside
          className={`
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
            lg:translate-x-0
            fixed lg:relative
            inset-y-0 left-0
            w-80 lg:w-96
            bg-white border-r
            z-30 lg:z-auto
            transition-transform duration-300
            flex flex-col
            mt-14 lg:mt-0
          `}
        >
          {/* Tabs */}
          <div className="p-2 border-b flex gap-2">
            <TabButton
              active={activeTab === "config"}
              onClick={() => setActiveTab("config")}
              icon={<Settings size={18} />}
              label="Configure"
            />
            <TabButton
              active={activeTab === "results"}
              onClick={() => setActiveTab("results")}
              icon={<BarChart3 size={18} />}
              label="Results"
              badge={simulationResult ? 1 : undefined}
            />
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "config" && <FarmConfigPanel />}
            {activeTab === "results" && <ResultsDashboard />}
          </div>
        </aside>

        {/* Overlay for mobile sidebar */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-20 lg:hidden"
            onClick={toggleSidebar}
          />
        )}

        {/* Map */}
        <main className="flex-1 relative">
          <FarmMap />

          {/* Map Controls */}
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
            <button
              onClick={() => useFarmStore.getState().setMapZoom(useFarmStore.getState().mapZoom + 1)}
              className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50"
            >
              +
            </button>
            <button
              onClick={() => useFarmStore.getState().setMapZoom(useFarmStore.getState().mapZoom - 1)}
              className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50"
            >
              -
            </button>
          </div>

          {/* Instructions overlay */}
          {!farmConfig && (
            <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 bg-white px-6 py-3 rounded-full shadow-lg z-10">
              <p className="text-gray-700 font-medium">
                👆 Click anywhere on the map to select your farm location
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
