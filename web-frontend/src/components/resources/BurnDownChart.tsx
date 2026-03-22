"use client";

import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { TrendingDown, Droplets, Clock, DollarSign, Zap } from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface BurnDownDataPoint {
  timestamp: string;
  resources: {
    [key: string]: {
      daily_consumed: number;
      weekly_consumed: number;
      daily_limit: number | null;
      weekly_limit: number | null;
      daily_remaining: number | null;
      utilization: number;
      daily_utilization: number;
      weekly_utilization: number;
    };
  };
}

interface BurnDownChartProps {
  farmId: string;
  resourceType?: "water" | "budget" | "labour" | "electricity" | "feed";
  hours?: number;
  showLimits?: boolean;
}

// Resource display config
const RESOURCE_CONFIG: Record<
  string,
  { label: string; color: string; icon: typeof Droplets; unit: string }
> = {
  water: {
    label: "Water",
    color: "#3b82f6",
    icon: Droplets,
    unit: "L",
  },
  budget: {
    label: "Budget",
    color: "#10b981",
    icon: DollarSign,
    unit: "USD",
  },
  labour: {
    label: "Labour",
    color: "#f59e0b",
    icon: Clock,
    unit: "hrs",
  },
  electricity: {
    label: "Electricity",
    color: "#8b5cf6",
    icon: Zap,
    unit: "kWh",
  },
  feed: {
    label: "Feed",
    color: "#ef4444",
    icon: TrendingDown,
    unit: "kg",
  },
};

// ============================================================================
// Component
// ============================================================================

export function BurnDownChart({
  farmId,
  resourceType = "water",
  hours = 24,
  showLimits = true,
}: BurnDownChartProps) {
  const [data, setData] = useState<BurnDownDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const config = RESOURCE_CONFIG[resourceType] || RESOURCE_CONFIG.water;

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `http://localhost:8000/api/resources/${farmId}/burn-down?hours=${hours}`
        );
        if (!response.ok) throw new Error("Failed to fetch burn-down data");
        const result = await response.json();
        setData(result.data || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    
    // Poll every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [farmId, hours]);

  // Transform data for chart
  const chartData = data.map((point) => {
    const resource = point.resources[resourceType];
    const time = new Date(point.timestamp);
    return {
      time: time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      fullTime: time.toLocaleString(),
      consumed: resource?.daily_consumed || 0,
      remaining: resource?.daily_remaining || 0,
      limit: resource?.daily_limit || 0,
      utilization: (resource?.daily_utilization || 0) * 100,
    };
  });

  // Get current stats
  const latestData = data[data.length - 1];
  const currentResource = latestData?.resources[resourceType];
  const dailyLimit = currentResource?.daily_limit || 0;
  const consumed = currentResource?.daily_consumed || 0;
  const remaining = currentResource?.daily_remaining || 0;
  const utilizationPercent = (currentResource?.daily_utilization || 0) * 100;

  // Calculate projected depletion
  const avgConsumptionRate =
    chartData.length > 1
      ? (chartData[chartData.length - 1].consumed - chartData[0].consumed) /
        chartData.length
      : 0;
  const hoursUntilDepletion =
    avgConsumptionRate > 0 ? remaining / avgConsumptionRate : Infinity;

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-red-100 p-6">
        <div className="text-center text-red-600">
          <p className="font-medium">Error loading burn-down data</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const Icon = config.icon;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon className="w-5 h-5" style={{ color: config.color }} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">
              {config.label} Burn-Down
            </h3>
            <p className="text-sm text-gray-500">Daily consumption tracking</p>
          </div>
        </div>

        {/* Status Badge */}
        <div
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            utilizationPercent >= 90
              ? "bg-red-100 text-red-700"
              : utilizationPercent >= 75
              ? "bg-amber-100 text-amber-700"
              : "bg-emerald-100 text-emerald-700"
          }`}
        >
          {utilizationPercent.toFixed(1)}% used
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Daily Limit</p>
          <p className="text-lg font-semibold text-gray-900">
            {dailyLimit.toLocaleString()} {config.unit}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Consumed</p>
          <p className="text-lg font-semibold" style={{ color: config.color }}>
            {consumed.toLocaleString()} {config.unit}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Remaining</p>
          <p className="text-lg font-semibold text-gray-900">
            {remaining.toLocaleString()} {config.unit}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Est. Depletion</p>
          <p
            className={`text-lg font-semibold ${
              hoursUntilDepletion < 4
                ? "text-red-600"
                : hoursUntilDepletion < 8
                ? "text-amber-600"
                : "text-gray-900"
            }`}
          >
            {hoursUntilDepletion === Infinity
              ? "—"
              : `${hoursUntilDepletion.toFixed(1)}h`}
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient
                id={`gradient-${resourceType}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="5%" stopColor={config.color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={config.color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
              tickFormatter={(v) => `${v.toLocaleString()}`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const data = payload[0].payload;
                return (
                  <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-100">
                    <p className="text-xs text-gray-500 mb-1">{data.fullTime}</p>
                    <p className="text-sm font-semibold">
                      Consumed: {data.consumed.toLocaleString()} {config.unit}
                    </p>
                    <p className="text-sm text-gray-600">
                      Remaining: {data.remaining.toLocaleString()} {config.unit}
                    </p>
                    <p className="text-sm text-gray-600">
                      Utilization: {data.utilization.toFixed(1)}%
                    </p>
                  </div>
                );
              }}
            />
            {showLimits && dailyLimit > 0 && (
              <>
                <ReferenceLine
                  y={dailyLimit * 0.75}
                  stroke="#f59e0b"
                  strokeDasharray="5 5"
                  label={{
                    value: "75%",
                    position: "right",
                    fontSize: 10,
                    fill: "#f59e0b",
                  }}
                />
                <ReferenceLine
                  y={dailyLimit * 0.9}
                  stroke="#ef4444"
                  strokeDasharray="5 5"
                  label={{
                    value: "90%",
                    position: "right",
                    fontSize: 10,
                    fill: "#ef4444",
                  }}
                />
              </>
            )}
            <Area
              type="monotone"
              dataKey="consumed"
              stroke={config.color}
              strokeWidth={2}
              fill={`url(#gradient-${resourceType})`}
              name="Consumed"
            />
            <Legend />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Multi-resource overview component
export function BurnDownOverview({ farmId }: { farmId: string }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingDown className="w-5 h-5 text-emerald-600" />
        <h2 className="text-xl font-semibold text-gray-900">
          Resource Burn-Down
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BurnDownChart farmId={farmId} resourceType="water" />
        <BurnDownChart farmId={farmId} resourceType="budget" />
        <BurnDownChart farmId={farmId} resourceType="labour" />
        <BurnDownChart farmId={farmId} resourceType="electricity" />
      </div>
    </div>
  );
}
