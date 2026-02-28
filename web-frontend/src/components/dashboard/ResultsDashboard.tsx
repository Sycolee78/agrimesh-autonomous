"use client";

import { useFarmStore } from "@/store/farmStore";
import { exportFarmPlan } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import {
  Download,
  TrendingUp,
  Droplets,
  Leaf,
  AlertTriangle,
  CheckCircle,
  Lightbulb,
} from "lucide-react";

// ============================================================================
// Utility Components
// ============================================================================

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  color?: "green" | "blue" | "yellow" | "red";
}

function MetricCard({ title, value, subtitle, icon, trend, color = "green" }: MetricCardProps) {
  const colorClasses = {
    green: "bg-green-50 border-green-200 text-green-700",
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
    red: "bg-red-50 border-red-200 text-red-700",
  };

  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium opacity-80">{title}</span>
        {icon}
      </div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
      {subtitle && <div className="text-xs mt-1 opacity-70">{subtitle}</div>}
    </div>
  );
}

// ============================================================================
// Sustainability Score
// ============================================================================

interface SustainabilityScoreProps {
  score: number;
}

function SustainabilityScore({ score }: SustainabilityScoreProps) {
  const getScoreColor = (s: number) => {
    if (s >= 80) return "text-green-500";
    if (s >= 60) return "text-lime-500";
    if (s >= 40) return "text-yellow-500";
    return "text-red-500";
  };

  const getScoreLabel = (s: number) => {
    if (s >= 80) return "Excellent";
    if (s >= 60) return "Good";
    if (s >= 40) return "Moderate";
    return "Needs Improvement";
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="64"
            cy="64"
            r="56"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-200"
          />
          <circle
            cx="64"
            cy="64"
            r="56"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeDasharray={`${(score / 100) * 352} 352`}
            className={getScoreColor(score)}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${getScoreColor(score)}`}>{score}</span>
          <span className="text-xs text-gray-500">/ 100</span>
        </div>
      </div>
      <span className={`mt-2 font-medium ${getScoreColor(score)}`}>
        {getScoreLabel(score)}
      </span>
    </div>
  );
}

// ============================================================================
// Crop Suitability Chart
// ============================================================================

function CropSuitabilityChart() {
  const { simulationResult } = useFarmStore();
  if (!simulationResult) return null;

  const data = simulationResult.cropSuitability.slice(0, 6).map((c) => ({
    name: c.crop.charAt(0).toUpperCase() + c.crop.slice(1),
    score: c.suitabilityScore,
    yield: c.expectedYieldTHa,
  }));

  const COLORS = ["#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444", "#8b5cf6"];

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 100]} />
          <YAxis type="category" dataKey="name" />
          <Tooltip
            formatter={(value: number, name: string) =>
              name === "score" ? [`${value}%`, "Suitability"] : [`${value} t/ha`, "Expected Yield"]
            }
          />
          <Bar dataKey="score" fill="#22c55e" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// Profit Breakdown Chart
// ============================================================================

function ProfitBreakdownChart() {
  const { simulationResult } = useFarmStore();
  if (!simulationResult) return null;

  const data = simulationResult.profitEstimate.breakdownByEnterprise
    .filter((e) => e.profit !== 0)
    .map((e) => ({
      name: e.enterprise.charAt(0).toUpperCase() + e.enterprise.slice(1),
      profit: e.profit,
    }));

  const COLORS = ["#22c55e", "#3b82f6", "#eab308", "#f97316", "#8b5cf6", "#ec4899"];

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={80}
            paddingAngle={2}
            dataKey="profit"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, "Profit"]} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// Sustainability Radar Chart
// ============================================================================

function SustainabilityRadar() {
  const { simulationResult } = useFarmStore();
  if (!simulationResult) return null;

  const { sustainability } = simulationResult;
  const data = [
    { metric: "Water", value: sustainability.waterEfficiency },
    { metric: "Soil", value: sustainability.soilHealth },
    { metric: "Biodiversity", value: sustainability.biodiversity },
    { metric: "Carbon", value: sustainability.carbonFootprint },
    { metric: "Overall", value: sustainability.overallScore },
  ];

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#22c55e"
            fill="#22c55e"
            fillOpacity={0.5}
          />
          <Tooltip formatter={(value: number) => [`${value}%`, "Score"]} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================================
// Synergies Section
// ============================================================================

function SynergiesSection() {
  const { simulationResult } = useFarmStore();
  if (!simulationResult || simulationResult.sustainability.synergies.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="font-medium text-gray-700 flex items-center gap-2">
        <Leaf size={16} className="text-green-500" />
        Active Synergies
      </h4>
      <div className="space-y-2">
        {simulationResult.sustainability.synergies.map((synergy, i) => (
          <div
            key={i}
            className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3"
          >
            <CheckCircle size={18} className="text-green-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium text-green-800">
                {synergy.source} → {synergy.target}
              </div>
              <div className="text-sm text-green-600">{synergy.benefit}</div>
            </div>
            <div className="ml-auto text-green-700 font-semibold">
              +{synergy.impactPercent}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Suggestions Section
// ============================================================================

function SuggestionsSection() {
  const { simulationResult } = useFarmStore();
  if (!simulationResult || simulationResult.sustainability.suggestions.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="font-medium text-gray-700 flex items-center gap-2">
        <Lightbulb size={16} className="text-yellow-500" />
        Improvement Suggestions
      </h4>
      <div className="space-y-2">
        {simulationResult.sustainability.suggestions.map((suggestion, i) => (
          <div
            key={i}
            className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3"
          >
            <AlertTriangle size={18} className="text-yellow-500 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-yellow-800">{suggestion}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Main Dashboard
// ============================================================================

export default function ResultsDashboard() {
  const { farmConfig, simulationResult, setActiveTab } = useFarmStore();

  if (!simulationResult || !farmConfig) {
    return (
      <div className="p-6 text-center text-gray-500">
        <div className="text-4xl mb-4">📊</div>
        <h3 className="font-semibold text-lg mb-2">No Results Yet</h3>
        <p className="text-sm mb-4">
          Configure your farm and run a simulation to see results.
        </p>
        <button
          onClick={() => setActiveTab("config")}
          className="text-green-600 hover:text-green-700 font-medium"
        >
          Go to Configuration →
        </button>
      </div>
    );
  }

  const handleExport = () => {
    const data = exportFarmPlan(farmConfig, simulationResult);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `farm-plan-${farmConfig.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b bg-white sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-lg">Simulation Results</h2>
            <p className="text-sm text-gray-500">
              AEZ Zone {simulationResult.aezZone.id} · {simulationResult.weather.annualRainfallMm}mm rainfall
            </p>
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
          >
            <Download size={18} />
            Export
          </button>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <MetricCard
            title="Net Profit"
            value={`$${simulationResult.profitEstimate.netProfitUsd.toLocaleString()}`}
            subtitle={`$${simulationResult.profitEstimate.scenarios.pessimistic.toLocaleString()} - $${simulationResult.profitEstimate.scenarios.optimistic.toLocaleString()}`}
            icon={<TrendingUp size={20} />}
            color="green"
          />
          <MetricCard
            title="Water/Day"
            value={`${simulationResult.resources.waterLitersPerDay.toLocaleString()}L`}
            subtitle={`${simulationResult.resources.feedKgPerDay}kg feed/day`}
            icon={<Droplets size={20} />}
            color="blue"
          />
        </div>

        {/* Sustainability Score */}
        <div className="bg-white rounded-xl border p-4">
          <h3 className="font-semibold mb-4 text-center">Sustainability Score</h3>
          <div className="flex justify-center">
            <SustainabilityScore score={simulationResult.sustainability.overallScore} />
          </div>
        </div>

        {/* Charts */}
        <div className="bg-white rounded-xl border p-4">
          <h3 className="font-semibold mb-4">Crop Suitability</h3>
          <CropSuitabilityChart />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <h3 className="font-semibold mb-4">Profit Breakdown</h3>
            <ProfitBreakdownChart />
          </div>
          <div className="bg-white rounded-xl border p-4">
            <h3 className="font-semibold mb-4">Sustainability Metrics</h3>
            <SustainabilityRadar />
          </div>
        </div>

        {/* Synergies */}
        <SynergiesSection />

        {/* Suggestions */}
        <SuggestionsSection />

        {/* Resource Requirements */}
        <div className="bg-white rounded-xl border p-4">
          <h3 className="font-semibold mb-4">Resource Requirements</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between p-2 bg-gray-50 rounded">
              <span>Water</span>
              <span className="font-medium">{simulationResult.resources.waterLitersPerDay} L/day</span>
            </div>
            <div className="flex justify-between p-2 bg-gray-50 rounded">
              <span>Feed</span>
              <span className="font-medium">{simulationResult.resources.feedKgPerDay} kg/day</span>
            </div>
            <div className="flex justify-between p-2 bg-gray-50 rounded">
              <span>Fertilizer</span>
              <span className="font-medium">{simulationResult.resources.fertilizerKgPerSeason} kg/season</span>
            </div>
            <div className="flex justify-between p-2 bg-gray-50 rounded">
              <span>Labor</span>
              <span className="font-medium">{simulationResult.resources.laborHoursPerWeek} hrs/week</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
