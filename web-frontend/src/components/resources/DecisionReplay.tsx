"use client";

import { useState, useEffect } from "react";
import {
  History,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Filter,
  Calendar,
  Search,
  Download,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Settings,
} from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface Decision {
  decision_id: string;
  agent_id: string;
  agent_name: string;
  decision_type: string;
  action: string;
  parameters: Record<string, unknown>;
  context: Record<string, unknown>;
  outcome: string | null;
  timestamp: string;
  success: boolean;
}

interface DecisionSummary {
  date: string;
  total_decisions: number;
  by_agent: Record<string, { count: number; success: number }>;
  by_type: Record<string, number>;
}

interface DecisionReplayProps {
  farmId: string;
}

// Decision type colors
const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  irrigation: { bg: "bg-blue-50", text: "text-blue-700" },
  resource_bid: { bg: "bg-emerald-50", text: "text-emerald-700" },
  alert: { bg: "bg-amber-50", text: "text-amber-700" },
  feed_livestock: { bg: "bg-orange-50", text: "text-orange-700" },
  maintenance: { bg: "bg-purple-50", text: "text-purple-700" },
  default: { bg: "bg-gray-50", text: "text-gray-700" },
};

// ============================================================================
// Decision Card Component
// ============================================================================

function DecisionCard({
  decision,
  isExpanded,
  onToggle,
}: {
  decision: Decision;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const colors = TYPE_COLORS[decision.decision_type] || TYPE_COLORS.default;
  const time = new Date(decision.timestamp);

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden hover:shadow-sm transition-shadow">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-3 flex items-center gap-3 text-left hover:bg-gray-50"
      >
        <div className="flex-shrink-0">
          {decision.success ? (
            <CheckCircle className="w-5 h-5 text-emerald-500" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
              {decision.decision_type}
            </span>
            <span className="text-xs text-gray-500">{decision.agent_name}</span>
          </div>
          <p className="text-sm text-gray-900 truncate">{decision.action}</p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-400">
            {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-100 bg-gray-50">
          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Parameters</p>
              <pre className="text-xs bg-white p-2 rounded border border-gray-100 overflow-auto max-h-32">
                {JSON.stringify(decision.parameters, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Context</p>
              <pre className="text-xs bg-white p-2 rounded border border-gray-100 overflow-auto max-h-32">
                {JSON.stringify(decision.context, null, 2)}
              </pre>
            </div>
          </div>
          {decision.outcome && (
            <div className="mt-3">
              <p className="text-xs font-medium text-gray-500 mb-1">Outcome</p>
              <p className="text-sm text-gray-700">{decision.outcome}</p>
            </div>
          )}
          <div className="mt-3 text-xs text-gray-400">
            Decision ID: {decision.decision_id} • {time.toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Summary Panel Component
// ============================================================================

function SummaryPanel({ summary }: { summary: DecisionSummary }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h4 className="font-medium text-gray-900 mb-3">Daily Summary</h4>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">
            {summary.total_decisions}
          </p>
          <p className="text-xs text-gray-500">Total Decisions</p>
        </div>
        <div className="bg-emerald-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-emerald-600">
            {Object.values(summary.by_agent).reduce(
              (acc, a) => acc + a.success,
              0
            )}
          </p>
          <p className="text-xs text-gray-500">Successful</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-red-600">
            {Object.values(summary.by_agent).reduce(
              (acc, a) => acc + (a.count - a.success),
              0
            )}
          </p>
          <p className="text-xs text-gray-500">Failed</p>
        </div>
      </div>

      {/* By Agent */}
      <div className="mb-4">
        <p className="text-xs font-medium text-gray-500 mb-2">By Agent</p>
        <div className="space-y-2">
          {Object.entries(summary.by_agent).map(([agent, stats]) => (
            <div key={agent} className="flex items-center justify-between text-sm">
              <span className="text-gray-700">{agent}</span>
              <div className="flex items-center gap-2">
                <span className="text-emerald-600">{stats.success}</span>
                <span className="text-gray-300">/</span>
                <span className="text-gray-500">{stats.count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* By Type */}
      <div>
        <p className="text-xs font-medium text-gray-500 mb-2">By Type</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(summary.by_type).map(([type, count]) => {
            const colors = TYPE_COLORS[type] || TYPE_COLORS.default;
            return (
              <span
                key={type}
                className={`px-2 py-1 rounded text-xs ${colors.bg} ${colors.text}`}
              >
                {type}: {count}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Replay Controls Component
// ============================================================================

function ReplayControls({
  isPlaying,
  speed,
  currentIndex,
  totalCount,
  onPlay,
  onPause,
  onNext,
  onPrev,
  onSpeedChange,
}: {
  isPlaying: boolean;
  speed: number;
  currentIndex: number;
  totalCount: number;
  onPlay: () => void;
  onPause: () => void;
  onNext: () => void;
  onPrev: () => void;
  onSpeedChange: (speed: number) => void;
}) {
  return (
    <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
      {/* Playback Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          disabled={currentIndex <= 0}
          className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={isPlaying ? onPause : onPlay}
          className="p-2 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600"
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4" />
          )}
        </button>

        <button
          onClick={onNext}
          disabled={currentIndex >= totalCount - 1}
          className="p-2 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <SkipForward className="w-4 h-4" />
        </button>
      </div>

      {/* Progress */}
      <div className="flex-1">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-300"
            style={{
              width: `${totalCount > 0 ? ((currentIndex + 1) / totalCount) * 100 : 0}%`,
            }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{currentIndex + 1}</span>
          <span>{totalCount} decisions</span>
        </div>
      </div>

      {/* Speed Control */}
      <div className="flex items-center gap-2">
        <Settings className="w-4 h-4 text-gray-400" />
        <select
          value={speed}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
          className="text-sm border border-gray-200 rounded px-2 py-1"
        >
          <option value={500}>0.5x</option>
          <option value={1000}>1x</option>
          <option value={2000}>2x</option>
          <option value={5000}>5x</option>
        </select>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function DecisionReplay({ farmId }: DecisionReplayProps) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [summary, setSummary] = useState<DecisionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  // Replay state
  const [isPlaying, setIsPlaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [replaySpeed, setReplaySpeed] = useState(1000);

  // Expanded decisions
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Fetch decisions
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [decisionsRes, summaryRes] = await Promise.all([
          fetch(
            `http://localhost:8000/api/decisions/${farmId}/history?limit=100`
          ),
          fetch(`http://localhost:8000/api/decisions/${farmId}/summary`),
        ]);

        if (!decisionsRes.ok || !summaryRes.ok) {
          throw new Error("Failed to fetch decision data");
        }

        const decisionsData = await decisionsRes.json();
        const summaryData = await summaryRes.json();

        setDecisions(decisionsData.decisions || []);
        setSummary(summaryData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [farmId]);

  // Replay timer
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setReplayIndex((prev) => {
        if (prev >= filteredDecisions.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, replaySpeed);

    return () => clearInterval(timer);
  }, [isPlaying, replaySpeed]);

  // Filter decisions
  const filteredDecisions = decisions.filter((d) => {
    if (agentFilter && d.agent_id !== agentFilter) return false;
    if (typeFilter && d.decision_type !== typeFilter) return false;
    if (
      searchQuery &&
      !d.action.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  // Toggle decision expansion
  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Export decisions
  const exportDecisions = () => {
    const data = JSON.stringify(filteredDecisions, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `decisions-${farmId}-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  };

  // Get unique agents and types for filters
  const uniqueAgents = [...new Set(decisions.map((d) => d.agent_id))];
  const uniqueTypes = [...new Set(decisions.map((d) => d.decision_type))];

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-red-100 p-6">
        <div className="text-center text-red-600">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
          <p className="font-medium">Error loading decisions</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-50">
            <History className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Decision Replay</h3>
            <p className="text-sm text-gray-500">
              Review and analyze agent decisions
            </p>
          </div>
        </div>

        <button
          onClick={exportDecisions}
          className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="flex items-center gap-4">
              <Filter className="w-4 h-4 text-gray-400" />

              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search actions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <select
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="">All Agents</option>
                {uniqueAgents.map((agent) => (
                  <option key={agent} value={agent}>
                    {agent}
                  </option>
                ))}
              </select>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
              >
                <option value="">All Types</option>
                {uniqueTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Replay Controls */}
          <ReplayControls
            isPlaying={isPlaying}
            speed={replaySpeed}
            currentIndex={replayIndex}
            totalCount={filteredDecisions.length}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onNext={() =>
              setReplayIndex((prev) =>
                Math.min(prev + 1, filteredDecisions.length - 1)
              )
            }
            onPrev={() => setReplayIndex((prev) => Math.max(prev - 1, 0))}
            onSpeedChange={setReplaySpeed}
          />

          {/* Decision List */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredDecisions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No decisions found</p>
                </div>
              ) : (
                filteredDecisions.map((decision, index) => (
                  <div
                    key={decision.decision_id}
                    className={`transition-all duration-300 ${
                      index === replayIndex && isPlaying
                        ? "ring-2 ring-emerald-500 rounded-lg"
                        : ""
                    }`}
                  >
                    <DecisionCard
                      decision={decision}
                      isExpanded={expandedIds.has(decision.decision_id)}
                      onToggle={() => toggleExpanded(decision.decision_id)}
                    />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Side Panel */}
        <div>
          {summary && <SummaryPanel summary={summary} />}
        </div>
      </div>
    </div>
  );
}
