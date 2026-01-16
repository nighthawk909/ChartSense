/**
 * Performance Dashboard
 * Full analytics hub displaying key trading metrics and equity curve
 */
import { useState, useEffect, useMemo } from 'react';
import {
  TrendingUp, TrendingDown, Activity, DollarSign,
  Target, AlertTriangle, BarChart3, Clock, Zap,
  ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PerformanceMetrics {
  // Core Metrics
  netPnl: number;
  netPnlPct: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;

  // Advanced Metrics
  profitFactor: number;
  expectancy: number;
  maxDrawdown: number;
  maxDrawdownPct: number;
  sharpeRatio: number | null;

  // Trade Stats
  avgWin: number;
  avgLoss: number;
  largestWin: number;
  largestLoss: number;
  avgHoldTime: string;

  // Today's Performance
  todayPnl: number;
  todayTrades: number;
  todayWinRate: number;
}

interface EquityPoint {
  date: string;
  equity: number;
  pnl: number;
  cumulativePnl: number;
}

interface BotAction {
  timestamp: string;
  type: 'order_filled' | 'signal_skipped' | 'position_opened' | 'position_closed' | 'signal_generated' | 'ai_decision';
  symbol: string;
  message: string;
  details?: Record<string, unknown>;
  status: 'success' | 'warning' | 'info' | 'error';
}

interface PerformanceDashboardProps {
  compact?: boolean;
}

export default function PerformanceDashboard({ compact = false }: PerformanceDashboardProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [recentActions, setRecentActions] = useState<BotAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'1D' | '1W' | '1M' | '3M' | 'ALL'>('1M');

  // Fetch performance data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch metrics
        const metricsRes = await fetch(`${API_URL}/api/bot/performance/metrics?period=${timeRange}`);
        if (metricsRes.ok) {
          const data = await metricsRes.json();
          setMetrics({
            netPnl: data.total_pnl || 0,
            netPnlPct: data.total_pnl_pct || 0,
            totalTrades: data.total_trades || 0,
            winningTrades: data.winning_trades || 0,
            losingTrades: data.losing_trades || 0,
            winRate: data.win_rate || 0,
            profitFactor: data.profit_factor || 0,
            expectancy: data.expectancy || (data.avg_win * data.win_rate / 100 - data.avg_loss * (1 - data.win_rate / 100)) || 0,
            maxDrawdown: data.max_drawdown || 0,
            maxDrawdownPct: data.max_drawdown_pct || 0,
            sharpeRatio: data.sharpe_ratio,
            avgWin: data.avg_win || 0,
            avgLoss: data.avg_loss || 0,
            largestWin: data.best_trade || 0,
            largestLoss: data.worst_trade || 0,
            avgHoldTime: data.avg_trade_duration_hours ? `${data.avg_trade_duration_hours.toFixed(1)}h` : 'N/A',
            todayPnl: data.today_pnl || 0,
            todayTrades: data.today_trades || 0,
            todayWinRate: data.today_win_rate || 0,
          });
        }

        // Fetch equity curve
        const equityRes = await fetch(`${API_URL}/api/bot/performance/equity-curve?period=${timeRange}`);
        if (equityRes.ok) {
          const data = await equityRes.json();
          setEquityCurve(data.data || []);
        }

        // Fetch recent bot actions from execution log
        const actionsRes = await fetch(`${API_URL}/api/bot/execution-log?limit=20`);
        if (actionsRes.ok) {
          const data = await actionsRes.json();
          const actions: BotAction[] = (data.log || []).map((entry: any) => ({
            timestamp: entry.timestamp,
            type: mapEventType(entry.event_type),
            symbol: entry.symbol,
            message: entry.reason,
            details: entry.details,
            status: entry.executed ? 'success' : mapStatus(entry.event_type),
          }));
          setRecentActions(actions);
        }
      } catch (err) {
        console.error('Failed to fetch performance data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [timeRange]);

  const mapEventType = (type: string): BotAction['type'] => {
    if (type.includes('SUCCESS') || type.includes('FILLED')) return 'order_filled';
    if (type.includes('SKIPPED') || type.includes('REJECTED')) return 'signal_skipped';
    if (type.includes('ENTRY')) return 'position_opened';
    if (type.includes('EXIT')) return 'position_closed';
    if (type.includes('AI') || type.includes('DECISION')) return 'ai_decision';
    return 'signal_generated';
  };

  const mapStatus = (type: string): BotAction['status'] => {
    if (type.includes('FAILED') || type.includes('ERROR')) return 'error';
    if (type.includes('SKIPPED') || type.includes('REJECTED')) return 'warning';
    return 'info';
  };

  // Calculate chart bounds
  const chartBounds = useMemo(() => {
    if (equityCurve.length === 0) return { min: 0, max: 100 };
    const values = equityCurve.map(p => p.equity);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1;
    return { min: min - padding, max: max + padding };
  }, [equityCurve]);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-1/4 mb-4"></div>
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-slate-700 rounded-lg"></div>
          ))}
        </div>
        <div className="h-64 bg-slate-700 rounded-lg"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          Performance Analytics
        </h2>
        <div className="flex gap-1 bg-slate-700 rounded-lg p-1">
          {(['1D', '1W', '1M', '3M', 'ALL'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {/* Net P&L */}
        <MetricCard
          label="Net P&L"
          value={`$${metrics?.netPnl?.toFixed(2) || '0.00'}`}
          subValue={`${metrics?.netPnlPct?.toFixed(2) || '0.00'}%`}
          trend={metrics?.netPnl && metrics.netPnl >= 0 ? 'up' : 'down'}
          icon={DollarSign}
          color={metrics?.netPnl && metrics.netPnl >= 0 ? 'green' : 'red'}
        />

        {/* Win Rate */}
        <MetricCard
          label="Win Rate"
          value={`${metrics?.winRate?.toFixed(1) || '0.0'}%`}
          subValue={`${metrics?.winningTrades || 0}W / ${metrics?.losingTrades || 0}L`}
          trend={metrics?.winRate && metrics.winRate >= 50 ? 'up' : 'down'}
          icon={Target}
          color={metrics?.winRate && metrics.winRate >= 50 ? 'green' : 'yellow'}
        />

        {/* Profit Factor */}
        <MetricCard
          label="Profit Factor"
          value={metrics?.profitFactor?.toFixed(2) || '0.00'}
          subValue={metrics?.profitFactor && metrics.profitFactor >= 1.5 ? 'Healthy' : metrics?.profitFactor && metrics.profitFactor >= 1 ? 'Marginal' : 'Losing'}
          trend={metrics?.profitFactor && metrics.profitFactor >= 1 ? 'up' : 'down'}
          icon={Activity}
          color={metrics?.profitFactor && metrics.profitFactor >= 1.5 ? 'green' : metrics?.profitFactor && metrics.profitFactor >= 1 ? 'yellow' : 'red'}
        />

        {/* Max Drawdown */}
        <MetricCard
          label="Max Drawdown"
          value={`$${Math.abs(metrics?.maxDrawdown || 0).toFixed(2)}`}
          subValue={`${Math.abs(metrics?.maxDrawdownPct || 0).toFixed(2)}%`}
          trend="down"
          icon={AlertTriangle}
          color={Math.abs(metrics?.maxDrawdownPct || 0) <= 5 ? 'green' : Math.abs(metrics?.maxDrawdownPct || 0) <= 10 ? 'yellow' : 'red'}
        />

        {/* Expectancy */}
        <MetricCard
          label="Expectancy"
          value={`$${metrics?.expectancy?.toFixed(2) || '0.00'}`}
          subValue="Per Trade"
          trend={metrics?.expectancy && metrics.expectancy > 0 ? 'up' : 'down'}
          icon={Zap}
          color={metrics?.expectancy && metrics.expectancy > 0 ? 'green' : 'red'}
        />

        {/* Today's P&L */}
        <MetricCard
          label="Today"
          value={`$${metrics?.todayPnl?.toFixed(2) || '0.00'}`}
          subValue={`${metrics?.todayTrades || 0} trades`}
          trend={metrics?.todayPnl && metrics.todayPnl >= 0 ? 'up' : 'down'}
          icon={Clock}
          color={metrics?.todayPnl && metrics.todayPnl >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Equity Curve */}
      <div className="bg-slate-800 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Equity Curve</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getMonth() + 1}/${date.getDate()}`;
                }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 12 }}
                domain={[chartBounds.min, chartBounds.max]}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Equity']}
              />
              <ReferenceLine y={equityCurve[0]?.equity || 0} stroke="#64748b" strokeDasharray="5 5" />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trade Stats & Recent Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trade Statistics */}
        <div className="bg-slate-800 rounded-xl p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Trade Statistics</h3>
          <div className="grid grid-cols-2 gap-4">
            <StatRow label="Total Trades" value={metrics?.totalTrades || 0} />
            <StatRow label="Avg Hold Time" value={metrics?.avgHoldTime || 'N/A'} />
            <StatRow label="Avg Win" value={`$${metrics?.avgWin?.toFixed(2) || '0.00'}`} color="green" />
            <StatRow label="Avg Loss" value={`$${Math.abs(metrics?.avgLoss || 0).toFixed(2)}`} color="red" />
            <StatRow label="Largest Win" value={`$${metrics?.largestWin?.toFixed(2) || '0.00'}`} color="green" />
            <StatRow label="Largest Loss" value={`$${Math.abs(metrics?.largestLoss || 0).toFixed(2)}`} color="red" />
            {metrics?.sharpeRatio !== null && (
              <>
                <StatRow label="Sharpe Ratio" value={metrics?.sharpeRatio?.toFixed(2) || 'N/A'} />
                <StatRow label="Risk/Reward" value={metrics?.avgWin && metrics?.avgLoss ? (metrics.avgWin / Math.abs(metrics.avgLoss)).toFixed(2) : 'N/A'} />
              </>
            )}
          </div>
        </div>

        {/* Recent Bot Actions */}
        <div className="bg-slate-800 rounded-xl p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Bot Actions</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentActions.length === 0 ? (
              <p className="text-slate-400 text-center py-4">No recent actions</p>
            ) : (
              recentActions.map((action, idx) => (
                <ActionItem key={idx} action={action} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Metric Card Component
interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend: 'up' | 'down' | 'neutral';
  icon: React.ComponentType<{ className?: string }>;
  color: 'green' | 'red' | 'yellow' | 'blue';
}

function MetricCard({ label, value, subValue, trend, icon: Icon, color }: MetricCardProps) {
  const colorClasses = {
    green: 'text-green-400 bg-green-500/10',
    red: 'text-red-400 bg-red-500/10',
    yellow: 'text-yellow-400 bg-yellow-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
  };

  const TrendIcon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus;

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-sm">{label}</span>
        <div className={`p-1.5 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-xl font-bold ${color === 'green' ? 'text-green-400' : color === 'red' ? 'text-red-400' : color === 'yellow' ? 'text-yellow-400' : 'text-white'}`}>
          {value}
        </span>
        <TrendIcon className={`w-4 h-4 ${trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400'}`} />
      </div>
      {subValue && (
        <span className="text-xs text-slate-500">{subValue}</span>
      )}
    </div>
  );
}

// Stat Row Component
function StatRow({ label, value, color }: { label: string; value: string | number; color?: 'green' | 'red' }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-700 last:border-0">
      <span className="text-slate-400 text-sm">{label}</span>
      <span className={`font-medium ${color === 'green' ? 'text-green-400' : color === 'red' ? 'text-red-400' : 'text-white'}`}>
        {value}
      </span>
    </div>
  );
}

// Action Item Component
function ActionItem({ action }: { action: BotAction }) {
  const statusColors = {
    success: 'bg-green-500/20 text-green-400 border-green-500/30',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  const typeLabels: Record<BotAction['type'], string> = {
    order_filled: 'Order Filled',
    signal_skipped: 'Signal Skipped',
    position_opened: 'Position Opened',
    position_closed: 'Position Closed',
    signal_generated: 'Signal Generated',
    ai_decision: 'AI Decision',
  };

  const typeIcons: Record<BotAction['type'], React.ReactNode> = {
    order_filled: <TrendingUp className="w-3 h-3" />,
    signal_skipped: <AlertTriangle className="w-3 h-3" />,
    position_opened: <ArrowUpRight className="w-3 h-3" />,
    position_closed: <ArrowDownRight className="w-3 h-3" />,
    signal_generated: <Activity className="w-3 h-3" />,
    ai_decision: <Zap className="w-3 h-3" />,
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className={`p-3 rounded-lg border ${statusColors[action.status]}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          {typeIcons[action.type]}
          <span className="font-medium text-sm">{action.symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
            {typeLabels[action.type]}
          </span>
        </div>
        <span className="text-xs text-slate-500">{formatTime(action.timestamp)}</span>
      </div>
      <p className="text-xs text-slate-300 truncate">{action.message}</p>
    </div>
  );
}
