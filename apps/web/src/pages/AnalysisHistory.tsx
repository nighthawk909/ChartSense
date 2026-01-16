/**
 * Analysis History Page
 * Stores every scan the AI performs with Confidence Score and Reasoning
 * Even for signals that didn't lead to a trade
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Search, Brain, TrendingUp,
  ChevronDown, ChevronUp, AlertTriangle, CheckCircle,
  XCircle, BarChart3, Activity, Zap, RefreshCw
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface AnalysisEntry {
  id: string;
  timestamp: string;
  symbol: string;
  assetClass: 'stock' | 'crypto';
  analysisMode: 'scalp' | 'intraday' | 'swing';
  // Signal Data
  signal: 'BUY' | 'SELL' | 'HOLD' | 'NEUTRAL';
  confidence: number;
  threshold: number;
  meetsThreshold: boolean;
  // Technical Indicators
  indicators: {
    rsi?: number;
    macd?: number;
    macdSignal?: number;
    sma20?: number;
    sma50?: number;
    bbPosition?: number;
    atr?: number;
    volumeRatio?: number;
  };
  technicalSignals: string[];
  // AI Decision
  aiDecision?: {
    decision: 'APPROVE' | 'REJECT' | 'WAIT';
    reasoning: string;
    concerns: string[];
    confidence: number;
    timeHorizon?: string;
  };
  // Outcome (if trade was executed)
  executed: boolean;
  executionReason?: string;
  outcome?: {
    entryPrice: number;
    exitPrice?: number;
    pnl?: number;
    pnlPct?: number;
  };
}

interface FilterState {
  symbol: string;
  assetClass: 'all' | 'stock' | 'crypto';
  signal: 'all' | 'BUY' | 'SELL' | 'HOLD';
  executed: 'all' | 'yes' | 'no';
  dateRange: '1D' | '1W' | '1M' | 'ALL';
}

export default function AnalysisHistory() {
  const [entries, setEntries] = useState<AnalysisEntry[]>([]);
  const [filteredEntries, setFilteredEntries] = useState<AnalysisEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<FilterState>({
    symbol: '',
    assetClass: 'all',
    signal: 'all',
    executed: 'all',
    dateRange: '1W',
  });

  // Fetch analysis history
  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch from execution log
      const execRes = await fetch(`${API_URL}/api/bot/execution-log?limit=100`);
      let execData: any[] = [];
      if (execRes.ok) {
        const data = await execRes.json();
        execData = data.log || [];
      }

      // Fetch from bot status for recent analysis
      const statusRes = await fetch(`${API_URL}/api/bot/status`);
      let cryptoAnalysis: Record<string, any> = {};
      if (statusRes.ok) {
        const status = await statusRes.json();
        cryptoAnalysis = status.crypto_analysis_results || {};
      }

      // Combine and format entries
      const formattedEntries: AnalysisEntry[] = [];

      // Add execution log entries
      execData.forEach((entry, idx) => {
        const isCrypto = entry.symbol?.includes('/USD') || entry.symbol?.includes('USD');
        formattedEntries.push({
          id: `exec-${idx}-${entry.timestamp}`,
          timestamp: entry.timestamp,
          symbol: entry.symbol,
          assetClass: isCrypto ? 'crypto' : 'stock',
          analysisMode: determineMode(entry.details),
          signal: entry.details?.signal || 'NEUTRAL',
          confidence: entry.details?.confidence || entry.details?.score || 50,
          threshold: entry.details?.threshold || 70,
          meetsThreshold: entry.executed || (entry.details?.score >= (entry.details?.threshold || 70)),
          indicators: entry.details?.indicators || {},
          technicalSignals: entry.details?.signals || [],
          aiDecision: entry.details?.ai_decision,
          executed: entry.executed,
          executionReason: entry.reason,
          outcome: entry.details?.outcome,
        });
      });

      // Add current crypto analysis
      Object.entries(cryptoAnalysis).forEach(([symbol, analysis]: [string, any]) => {
        const existing = formattedEntries.find(e => e.symbol === symbol && e.timestamp === analysis.timestamp);
        if (!existing) {
          formattedEntries.push({
            id: `analysis-${symbol}-${analysis.timestamp}`,
            timestamp: analysis.timestamp,
            symbol,
            assetClass: 'crypto',
            analysisMode: 'intraday',
            signal: analysis.signal || 'NEUTRAL',
            confidence: analysis.confidence || 50,
            threshold: analysis.threshold || 70,
            meetsThreshold: analysis.meets_threshold || false,
            indicators: analysis.indicators || {},
            technicalSignals: analysis.signals || [],
            aiDecision: analysis.ai_decision,
            executed: false,
            executionReason: analysis.reason,
          });
        }
      });

      // Sort by timestamp descending
      formattedEntries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      setEntries(formattedEntries);
    } catch (err) {
      console.error('Failed to fetch analysis history:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 30000);
    return () => clearInterval(interval);
  }, [fetchHistory]);

  // Apply filters
  useEffect(() => {
    let filtered = [...entries];

    // Symbol filter
    if (filters.symbol) {
      filtered = filtered.filter(e =>
        e.symbol.toLowerCase().includes(filters.symbol.toLowerCase())
      );
    }

    // Asset class filter
    if (filters.assetClass !== 'all') {
      filtered = filtered.filter(e => e.assetClass === filters.assetClass);
    }

    // Signal filter
    if (filters.signal !== 'all') {
      filtered = filtered.filter(e => e.signal === filters.signal);
    }

    // Executed filter
    if (filters.executed !== 'all') {
      filtered = filtered.filter(e => filters.executed === 'yes' ? e.executed : !e.executed);
    }

    // Date range filter
    const now = new Date();
    let cutoff: Date;
    switch (filters.dateRange) {
      case '1D': cutoff = new Date(now.getTime() - 24 * 60 * 60 * 1000); break;
      case '1W': cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000); break;
      case '1M': cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000); break;
      default: cutoff = new Date(0);
    }
    filtered = filtered.filter(e => new Date(e.timestamp) >= cutoff);

    setFilteredEntries(filtered);
  }, [entries, filters]);

  const determineMode = (details: any): 'scalp' | 'intraday' | 'swing' => {
    if (details?.trade_type === 'SCALP') return 'scalp';
    if (details?.trade_type === 'SWING') return 'swing';
    return 'intraday';
  };

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedIds(newExpanded);
  };

  // Stats
  const stats = {
    total: filteredEntries.length,
    buySignals: filteredEntries.filter(e => e.signal === 'BUY').length,
    executed: filteredEntries.filter(e => e.executed).length,
    avgConfidence: filteredEntries.length > 0
      ? (filteredEntries.reduce((sum, e) => sum + e.confidence, 0) / filteredEntries.length).toFixed(1)
      : '0',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple-400" />
            Analysis History
          </h1>
          <p className="text-slate-400">Every AI scan with confidence scores and reasoning</p>
        </div>
        <button
          onClick={fetchHistory}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Total Scans" value={stats.total} color="blue" />
        <StatCard icon={TrendingUp} label="Buy Signals" value={stats.buySignals} color="green" />
        <StatCard icon={CheckCircle} label="Executed" value={stats.executed} color="purple" />
        <StatCard icon={Zap} label="Avg Confidence" value={`${stats.avgConfidence}%`} color="yellow" />
      </div>

      {/* Filters */}
      <div className="bg-slate-800 rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Symbol Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search symbol..."
              value={filters.symbol}
              onChange={(e) => setFilters(f => ({ ...f, symbol: e.target.value }))}
              className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Asset Class */}
          <FilterSelect
            value={filters.assetClass}
            onChange={(v) => setFilters(f => ({ ...f, assetClass: v as FilterState['assetClass'] }))}
            options={[
              { value: 'all', label: 'All Assets' },
              { value: 'stock', label: 'Stocks' },
              { value: 'crypto', label: 'Crypto' },
            ]}
          />

          {/* Signal */}
          <FilterSelect
            value={filters.signal}
            onChange={(v) => setFilters(f => ({ ...f, signal: v as FilterState['signal'] }))}
            options={[
              { value: 'all', label: 'All Signals' },
              { value: 'BUY', label: 'Buy' },
              { value: 'SELL', label: 'Sell' },
              { value: 'HOLD', label: 'Hold' },
            ]}
          />

          {/* Executed */}
          <FilterSelect
            value={filters.executed}
            onChange={(v) => setFilters(f => ({ ...f, executed: v as FilterState['executed'] }))}
            options={[
              { value: 'all', label: 'All' },
              { value: 'yes', label: 'Executed' },
              { value: 'no', label: 'Not Executed' },
            ]}
          />

          {/* Date Range */}
          <FilterSelect
            value={filters.dateRange}
            onChange={(v) => setFilters(f => ({ ...f, dateRange: v as FilterState['dateRange'] }))}
            options={[
              { value: '1D', label: '24 Hours' },
              { value: '1W', label: '7 Days' },
              { value: '1M', label: '30 Days' },
              { value: 'ALL', label: 'All Time' },
            ]}
          />
        </div>
      </div>

      {/* Analysis List */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400 mb-2" />
            <p className="text-slate-400">Loading analysis history...</p>
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="p-8 text-center">
            <Brain className="w-8 h-8 mx-auto text-slate-600 mb-2" />
            <p className="text-slate-400">No analysis records found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {filteredEntries.map((entry) => (
              <AnalysisRow
                key={entry.id}
                entry={entry}
                expanded={expandedIds.has(entry.id)}
                onToggle={() => toggleExpanded(entry.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Stat Card
function StatCard({
  icon: Icon,
  label,
  value,
  color
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  color: 'blue' | 'green' | 'purple' | 'yellow';
}) {
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-500/10',
    green: 'text-green-400 bg-green-500/10',
    purple: 'text-purple-400 bg-purple-500/10',
    yellow: 'text-yellow-400 bg-yellow-500/10',
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-slate-400 text-sm">{label}</p>
          <p className="text-xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

// Filter Select
function FilterSelect({
  value,
  onChange,
  options
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// Analysis Row
function AnalysisRow({
  entry,
  expanded,
  onToggle
}: {
  entry: AnalysisEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-400 bg-green-500/20';
      case 'SELL': return 'text-red-400 bg-red-500/20';
      case 'HOLD': return 'text-yellow-400 bg-yellow-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 75) return 'text-green-400';
    if (confidence >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'scalp': return 'text-orange-400 bg-orange-500/20';
      case 'swing': return 'text-blue-400 bg-blue-500/20';
      default: return 'text-purple-400 bg-purple-500/20';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="hover:bg-slate-700/30 transition-colors">
      {/* Main Row */}
      <div
        onClick={onToggle}
        className="px-4 py-3 cursor-pointer flex items-center gap-4"
      >
        {/* Expand Icon */}
        <button className="p-1 hover:bg-slate-600 rounded transition-colors">
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        {/* Symbol */}
        <div className="w-24">
          <div className="font-semibold text-white">{entry.symbol}</div>
          <div className="text-xs text-slate-500">{entry.assetClass}</div>
        </div>

        {/* Signal */}
        <div className="w-20">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSignalColor(entry.signal)}`}>
            {entry.signal}
          </span>
        </div>

        {/* Confidence */}
        <div className="w-24">
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  entry.confidence >= 75 ? 'bg-green-500' :
                  entry.confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${entry.confidence}%` }}
              ></div>
            </div>
            <span className={`text-sm font-medium ${getConfidenceColor(entry.confidence)}`}>
              {entry.confidence.toFixed(0)}%
            </span>
          </div>
          <div className="text-xs text-slate-500">
            Threshold: {entry.threshold}%
          </div>
        </div>

        {/* Mode */}
        <div className="w-20">
          <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${getModeColor(entry.analysisMode)}`}>
            {entry.analysisMode}
          </span>
        </div>

        {/* Executed */}
        <div className="w-20">
          {entry.executed ? (
            <span className="flex items-center gap-1 text-green-400 text-sm">
              <CheckCircle className="w-3 h-3" />
              Executed
            </span>
          ) : (
            <span className="flex items-center gap-1 text-slate-400 text-sm">
              <XCircle className="w-3 h-3" />
              Skipped
            </span>
          )}
        </div>

        {/* Time */}
        <div className="flex-1 text-right">
          <span className="text-sm text-slate-400">{formatTime(entry.timestamp)}</span>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 pl-12 space-y-4">
          {/* Technical Indicators */}
          {entry.indicators && Object.keys(entry.indicators).length > 0 && (
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-blue-400" />
                Technical Indicators
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {entry.indicators.rsi !== undefined && (
                  <div>
                    <span className="text-slate-400">RSI:</span>{' '}
                    <span className={entry.indicators.rsi < 30 ? 'text-green-400' : entry.indicators.rsi > 70 ? 'text-red-400' : 'text-white'}>
                      {entry.indicators.rsi.toFixed(1)}
                    </span>
                  </div>
                )}
                {entry.indicators.macd !== undefined && (
                  <div>
                    <span className="text-slate-400">MACD:</span>{' '}
                    <span className={entry.indicators.macd > 0 ? 'text-green-400' : 'text-red-400'}>
                      {entry.indicators.macd.toFixed(4)}
                    </span>
                  </div>
                )}
                {entry.indicators.sma20 !== undefined && (
                  <div>
                    <span className="text-slate-400">SMA20:</span>{' '}
                    <span className="text-white">${entry.indicators.sma20.toFixed(2)}</span>
                  </div>
                )}
                {entry.indicators.volumeRatio !== undefined && (
                  <div>
                    <span className="text-slate-400">Volume:</span>{' '}
                    <span className={entry.indicators.volumeRatio > 1.5 ? 'text-green-400' : 'text-white'}>
                      {entry.indicators.volumeRatio.toFixed(1)}x
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Technical Signals */}
          {entry.technicalSignals.length > 0 && (
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-400" />
                Signals Detected
              </h4>
              <div className="flex flex-wrap gap-2">
                {entry.technicalSignals.map((signal, idx) => (
                  <span key={idx} className="px-2 py-1 bg-slate-600 rounded text-xs text-slate-300">
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* AI Decision */}
          {entry.aiDecision && (
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-400" />
                AI Decision: {entry.aiDecision.decision}
              </h4>
              <p className="text-sm text-slate-300 mb-2">{entry.aiDecision.reasoning}</p>
              {entry.aiDecision.concerns.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {entry.aiDecision.concerns.map((concern, idx) => (
                    <span key={idx} className="px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {concern}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Execution Reason */}
          {entry.executionReason && (
            <div className="text-sm text-slate-400">
              <strong>Reason:</strong> {entry.executionReason}
            </div>
          )}

          {/* Outcome */}
          {entry.outcome && (
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h4 className="text-sm font-medium text-white mb-2">Trade Outcome</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-slate-400">Entry:</span>{' '}
                  <span className="text-white">${entry.outcome.entryPrice.toFixed(2)}</span>
                </div>
                {entry.outcome.exitPrice && (
                  <div>
                    <span className="text-slate-400">Exit:</span>{' '}
                    <span className="text-white">${entry.outcome.exitPrice.toFixed(2)}</span>
                  </div>
                )}
                {entry.outcome.pnlPct !== undefined && (
                  <div>
                    <span className="text-slate-400">P&L:</span>{' '}
                    <span className={entry.outcome.pnlPct >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {entry.outcome.pnlPct >= 0 ? '+' : ''}{entry.outcome.pnlPct.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
