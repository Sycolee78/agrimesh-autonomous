"use client";

import { useState } from "react";
import {
  Activity,
  TrendingDown,
  History,
  Settings,
  ChevronDown,
} from "lucide-react";
import { ResourceMonitor } from "@/components/resources/ResourceMonitor";
import { BurnDownOverview } from "@/components/resources/BurnDownChart";
import { DecisionReplay } from "@/components/resources/DecisionReplay";

// ============================================================================
// Types
// ============================================================================

type TabId = "monitor" | "burndown" | "decisions";

// ============================================================================
// Tab Configuration
// ============================================================================

const TABS: { id: TabId; label: string; icon: typeof Activity; description: string }[] = [
  {
    id: "monitor",
    label: "Resource Monitor",
    icon: Activity,
    description: "Real-time resource tracking with WebSocket updates",
  },
  {
    id: "burndown",
    label: "Burn-Down Charts",
    icon: TrendingDown,
    description: "Visualize resource consumption over time",
  },
  {
    id: "decisions",
    label: "Decision Replay",
    icon: History,
    description: "Review and analyze agent decisions",
  },
];

// ============================================================================
// Page Component
// ============================================================================

export default function ResourcesPage() {
  const [activeTab, setActiveTab] = useState<TabId>("monitor");
  const [farmId, setFarmId] = useState("default-farm");
  const [showFarmSelector, setShowFarmSelector] = useState(false);

  // Sample farm IDs (in production, fetch from API)
  const farmIds = ["default-farm", "test-farm-1", "demo-farm"];

  const activeTabConfig = TABS.find((t) => t.id === activeTab);
  const ActiveIcon = activeTabConfig?.icon || Activity;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-500 to-lime-500">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Resource Economy
                </h1>
                <p className="text-xs text-gray-500">AgriMesh Phase 5</p>
              </div>
            </div>

            {/* Farm Selector */}
            <div className="relative">
              <button
                onClick={() => setShowFarmSelector(!showFarmSelector)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Farm: {farmId}
                <ChevronDown className="w-4 h-4" />
              </button>

              {showFarmSelector && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-20">
                  {farmIds.map((id) => (
                    <button
                      key={id}
                      onClick={() => {
                        setFarmId(id);
                        setShowFarmSelector(false);
                      }}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                        id === farmId
                          ? "text-emerald-600 font-medium"
                          : "text-gray-700"
                      }`}
                    >
                      {id}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? "border-emerald-500 text-emerald-600 bg-emerald-50/50"
                      : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Tab Description */}
      <div className="bg-gradient-to-r from-emerald-50 to-lime-50 border-b border-emerald-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3">
            <ActiveIcon className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="font-medium text-gray-900">
                {activeTabConfig?.label}
              </h2>
              <p className="text-sm text-gray-600">
                {activeTabConfig?.description}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "monitor" && (
          <ResourceMonitor
            farmId={farmId}
            onAlert={(alert) => {
              console.log("New alert:", alert);
              // Could show toast notification here
            }}
          />
        )}

        {activeTab === "burndown" && <BurnDownOverview farmId={farmId} />}

        {activeTab === "decisions" && <DecisionReplay farmId={farmId} />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <p>AgriMesh Autonomous • Phase 5: Resource Economy</p>
            <p>
              WebSocket: ws://localhost:8000/ws/resources/{farmId}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
