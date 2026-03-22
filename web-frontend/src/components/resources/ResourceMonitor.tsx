"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Droplets,
  Clock,
  DollarSign,
  Zap,
  Wheat,
  Bell,
  BellOff,
  RefreshCw,
  Wifi,
  WifiOff,
} from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface ResourceStatus {
  available: number;
  total: number;
  utilization: string;
  unit: string;
  cost_per_unit: number;
  daily_consumed: number;
  weekly_consumed: number;
  daily_limit: number | null;
  weekly_limit: number | null;
  daily_utilization: string;
  budget_status: "ok" | "warning" | "critical" | "blocked" | "unconstrained";
}

interface BudgetAlert {
  alert_id: string;
  level: "INFO" | "WARNING" | "CRITICAL" | "EMERGENCY";
  resource_type: string;
  message: string;
  threshold_percent: number;
  current_percent: number;
  acknowledged: boolean;
}

interface PoolStatus {
  farm_id: string;
  timestamp: string;
  resources: Record<string, ResourceStatus>;
  pending_requests: number;
  active_allocations: number;
  budget_spent: number;
  active_alerts: BudgetAlert[];
}

interface ResourceMonitorProps {
  farmId: string;
  onAlert?: (alert: BudgetAlert) => void;
}

// Resource icons
const RESOURCE_ICONS: Record<string, typeof Droplets> = {
  water: Droplets,
  labour: Clock,
  budget: DollarSign,
  electricity: Zap,
  feed: Wheat,
};

// Status colors
const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ok: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  warning: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  critical: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
  blocked: { bg: "bg-red-100", text: "text-red-800", border: "border-red-300" },
  unconstrained: { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200" },
};

// ============================================================================
// Resource Card Component
// ============================================================================

function ResourceCard({
  name,
  status,
}: {
  name: string;
  status: ResourceStatus;
}) {
  const Icon = RESOURCE_ICONS[name] || Activity;
  const colors = STATUS_COLORS[status.budget_status] || STATUS_COLORS.unconstrained;
  const utilizationNum = parseFloat(status.utilization);

  return (
    <div
      className={`rounded-xl p-4 border ${colors.bg} ${colors.border} transition-all duration-300`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${colors.text}`} />
          <span className="font-medium text-gray-900 capitalize">{name}</span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors.bg} ${colors.text}`}
        >
          {status.budget_status}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              utilizationNum >= 90
                ? "bg-red-500"
                : utilizationNum >= 75
                ? "bg-amber-500"
                : "bg-emerald-500"
            }`}
            style={{ width: `${Math.min(utilizationNum, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0%</span>
          <span className="font-medium">{status.utilization}</span>
          <span>100%</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-gray-500">Available</p>
          <p className="font-semibold text-gray-900">
            {status.available.toLocaleString()} {status.unit}
          </p>
        </div>
        <div>
          <p className="text-gray-500">Total</p>
          <p className="font-semibold text-gray-900">
            {status.total.toLocaleString()} {status.unit}
          </p>
        </div>
        {status.daily_limit && (
          <>
            <div>
              <p className="text-gray-500">Daily Used</p>
              <p className="font-semibold text-gray-900">
                {status.daily_consumed.toLocaleString()} {status.unit}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Daily Budget</p>
              <p className="font-semibold text-gray-900">{status.daily_utilization}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Alert Card Component
// ============================================================================

function AlertCard({
  alert,
  onAcknowledge,
}: {
  alert: BudgetAlert;
  onAcknowledge: (alertId: string) => void;
}) {
  const levelColors: Record<string, { bg: string; icon: string; border: string }> = {
    INFO: { bg: "bg-blue-50", icon: "text-blue-500", border: "border-blue-200" },
    WARNING: { bg: "bg-amber-50", icon: "text-amber-500", border: "border-amber-200" },
    CRITICAL: { bg: "bg-red-50", icon: "text-red-500", border: "border-red-200" },
    EMERGENCY: { bg: "bg-red-100", icon: "text-red-700", border: "border-red-300" },
  };

  const colors = levelColors[alert.level] || levelColors.INFO;
  const Icon = RESOURCE_ICONS[alert.resource_type] || AlertTriangle;

  return (
    <div
      className={`rounded-lg p-3 border ${colors.bg} ${colors.border} flex items-start gap-3`}
    >
      <div className={`p-1.5 rounded-full ${colors.bg}`}>
        <Icon className={`w-4 h-4 ${colors.icon}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-medium ${colors.icon}`}>
            {alert.level}
          </span>
          <span className="text-xs text-gray-500">
            {alert.current_percent.toFixed(1)}% / {alert.threshold_percent}%
          </span>
        </div>
        <p className="text-sm text-gray-700">{alert.message}</p>
      </div>
      {!alert.acknowledged && (
        <button
          onClick={() => onAcknowledge(alert.alert_id)}
          className="p-1.5 hover:bg-white rounded-lg transition-colors"
          title="Acknowledge"
        >
          <CheckCircle className="w-4 h-4 text-gray-400 hover:text-emerald-500" />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ResourceMonitor({ farmId, onAlert }: ResourceMonitorProps) {
  const [status, setStatus] = useState<PoolStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [muteAlerts, setMuteAlerts] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket connection
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`ws://localhost:8000/ws/resources/${farmId}`);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === "status") {
            setStatus(message.data);
          } else if (message.type === "alert" && !muteAlerts) {
            // Handle new alert
            if (onAlert) {
              onAlert(message.alert);
            }
            // Play notification sound (optional)
            // new Audio('/notification.mp3').play();
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnection after 5 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      };

      ws.onerror = (e) => {
        setError("Connection error");
        console.error("WebSocket error:", e);
      };

      wsRef.current = ws;
    } catch (e) {
      setError("Failed to connect");
      console.error("WebSocket connection failed:", e);
    }
  }, [farmId, muteAlerts, onAlert]);

  // Initial connection
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  // Manual refresh
  const requestStatus = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: "get_status" }));
    }
  };

  // Acknowledge alert
  const acknowledgeAlert = async (alertId: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/resources/${farmId}/alerts/${alertId}/acknowledge`,
        { method: "POST" }
      );
      if (response.ok) {
        requestStatus(); // Refresh status
      }
    } catch (e) {
      console.error("Failed to acknowledge alert:", e);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-50">
            <Activity className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Resource Monitor</h3>
            <p className="text-sm text-gray-500">
              Real-time resource tracking • Farm: {farmId}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
              isConnected
                ? "bg-emerald-50 text-emerald-600"
                : "bg-red-50 text-red-600"
            }`}
          >
            {isConnected ? (
              <Wifi className="w-3 h-3" />
            ) : (
              <WifiOff className="w-3 h-3" />
            )}
            {isConnected ? "Live" : "Offline"}
          </div>

          {/* Mute Alerts */}
          <button
            onClick={() => setMuteAlerts(!muteAlerts)}
            className={`p-2 rounded-lg transition-colors ${
              muteAlerts
                ? "bg-gray-100 text-gray-400"
                : "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
            }`}
            title={muteAlerts ? "Unmute alerts" : "Mute alerts"}
          >
            {muteAlerts ? (
              <BellOff className="w-4 h-4" />
            ) : (
              <Bell className="w-4 h-4" />
            )}
          </button>

          {/* Refresh */}
          <button
            onClick={requestStatus}
            className="p-2 rounded-lg bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <XCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
          <button
            onClick={connect}
            className="ml-auto text-sm underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {!status && !error && (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
        </div>
      )}

      {/* Resource Grid */}
      {status && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {Object.entries(status.resources).map(([name, resourceStatus]) => (
              <ResourceCard key={name} name={name} status={resourceStatus} />
            ))}
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-500">Pending Requests</p>
              <p className="text-xl font-semibold text-gray-900">
                {status.pending_requests}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Active Allocations</p>
              <p className="text-xl font-semibold text-gray-900">
                {status.active_allocations}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Budget Spent</p>
              <p className="text-xl font-semibold text-emerald-600">
                ${status.budget_spent.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Active Alerts */}
          {status.active_alerts.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Active Alerts ({status.active_alerts.length})
              </h4>
              <div className="space-y-2">
                {status.active_alerts.map((alert) => (
                  <AlertCard
                    key={alert.alert_id}
                    alert={alert}
                    onAcknowledge={acknowledgeAlert}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Last Update */}
          <div className="mt-4 text-xs text-gray-400 text-right">
            Last update: {new Date(status.timestamp).toLocaleString()}
          </div>
        </>
      )}
    </div>
  );
}
