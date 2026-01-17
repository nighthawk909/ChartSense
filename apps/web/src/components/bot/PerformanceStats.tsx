/**
 * Performance Stats Component
 * Shows key performance metrics
 */
import { TrendingUp, Target, AlertTriangle, Award } from 'lucide-react';
import type { PerformanceMetrics } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

interface PerformanceStatsProps {
  metrics: PerformanceMetrics | null;
  loading?: boolean;
}

export default function PerformanceStats({ metrics, loading }: PerformanceStatsProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-48 mb-4"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <p className="text-slate-400">No performance data available</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Performance ({metrics.period_days} days)
        </h3>
        <span className="text-sm text-slate-400">
          {metrics.total_trades} trades
        </span>
      </div>

      {/* Main Stats Grid - responsive with min-width */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {/* Win Rate */}
        <div className="bg-slate-700/50 rounded-lg p-3 min-w-0">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Target className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-xs truncate">Win Rate</span>
          </div>
          <p className={`text-xl font-bold ${
            metrics.win_rate >= 0.5 ? 'text-green-500' : 'text-red-500'
          }`}>
            {(metrics.win_rate * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {metrics.winning_trades}W / {metrics.losing_trades}L
          </p>
        </div>

        {/* Total P&L */}
        <div className="bg-slate-700/50 rounded-lg p-3 min-w-0">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <TrendingUp className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-xs truncate">Total P&L</span>
          </div>
          <p className={`text-xl font-bold truncate ${getPnLColor(metrics.total_pnl)}`}>
            {formatCurrency(metrics.total_pnl)}
          </p>
          <p className={`text-[10px] ${getPnLColor(metrics.total_pnl_pct)}`}>
            {formatPercent(metrics.total_pnl_pct)}
          </p>
        </div>

        {/* Profit Factor */}
        <div className="bg-slate-700/50 rounded-lg p-3 min-w-0">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Award className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-xs truncate">Profit Factor</span>
          </div>
          <p className={`text-xl font-bold ${
            metrics.profit_factor >= 1.5 ? 'text-green-500' :
            metrics.profit_factor >= 1 ? 'text-yellow-500' : 'text-red-500'
          }`}>
            {metrics.profit_factor.toFixed(2)}
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {metrics.profit_factor >= 1.5 ? 'Good' :
             metrics.profit_factor >= 1 ? 'Break-even' : 'Losing'}
          </p>
        </div>

        {/* Max Drawdown */}
        <div className="bg-slate-700/50 rounded-lg p-3 min-w-0">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-xs truncate">Max DD</span>
          </div>
          <p className={`text-xl font-bold ${
            metrics.max_drawdown_pct <= 5 ? 'text-green-500' :
            metrics.max_drawdown_pct <= 10 ? 'text-yellow-500' : 'text-red-500'
          }`}>
            {metrics.max_drawdown_pct.toFixed(1)}%
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5 truncate">
            {formatCurrency(metrics.max_drawdown)}
          </p>
        </div>
      </div>

      {/* Additional Stats - more compact */}
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="bg-slate-700/30 rounded-lg p-2 min-w-0">
          <p className="text-slate-400 truncate">Avg Win</p>
          <p className="font-semibold text-green-500 truncate">{formatCurrency(metrics.avg_win)}</p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-2 min-w-0">
          <p className="text-slate-400 truncate">Avg Loss</p>
          <p className="font-semibold text-red-500 truncate">{formatCurrency(metrics.avg_loss)}</p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-2 min-w-0">
          <p className="text-slate-400 truncate">Best</p>
          <p className="font-semibold text-green-500 truncate">{formatCurrency(metrics.best_trade)}</p>
        </div>
        <div className="bg-slate-700/30 rounded-lg p-2 min-w-0">
          <p className="text-slate-400 truncate">Worst</p>
          <p className="font-semibold text-red-500 truncate">{formatCurrency(metrics.worst_trade)}</p>
        </div>
      </div>

      {/* Sharpe Ratio */}
      {metrics.sharpe_ratio !== null && (
        <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Sharpe Ratio</span>
            <span className={`font-semibold ${
              metrics.sharpe_ratio >= 1 ? 'text-green-500' :
              metrics.sharpe_ratio >= 0 ? 'text-yellow-500' : 'text-red-500'
            }`}>
              {metrics.sharpe_ratio.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Trade Type Breakdown */}
      {(metrics.swing_trades > 0 || metrics.longterm_trades > 0) && (
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <p className="text-sm text-blue-400">Swing Trades</p>
            <p className="font-semibold text-white">{metrics.swing_trades}</p>
            <p className="text-xs text-slate-400">
              Win rate: {(metrics.swing_win_rate * 100).toFixed(0)}%
            </p>
          </div>
          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3">
            <p className="text-sm text-purple-400">Long-term Trades</p>
            <p className="font-semibold text-white">{metrics.longterm_trades}</p>
            <p className="text-xs text-slate-400">
              Win rate: {(metrics.longterm_win_rate * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
