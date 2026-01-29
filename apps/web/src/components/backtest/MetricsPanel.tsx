/**
 * MetricsPanel - Displays backtest performance metrics
 */
import { TrendingUp, TrendingDown, Target, BarChart3, Activity, DollarSign } from 'lucide-react';
import type { BacktestResult } from '../../types/backtest';

interface MetricsPanelProps {
  result: BacktestResult;
}

function MetricCard({
  label,
  value,
  format = 'number',
  positive,
  icon: Icon,
}: {
  label: string;
  value: number | undefined;
  format?: 'number' | 'percent' | 'currency' | 'ratio';
  positive?: boolean;
  icon?: React.ElementType;
}) {
  const formatValue = (val: number | undefined) => {
    if (val === undefined || val === null || isNaN(val)) return 'N/A';

    switch (format) {
      case 'percent':
        return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(2)}%`;
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
        }).format(val);
      case 'ratio':
        return val.toFixed(2);
      default:
        return val.toFixed(2);
    }
  };

  const colorClass =
    positive === undefined
      ? 'text-slate-200'
      : positive
      ? 'text-green-400'
      : 'text-red-400';

  return (
    <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
      <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
        {Icon && <Icon className="w-3 h-3" />}
        <span>{label}</span>
      </div>
      <div className={`text-lg font-semibold ${colorClass}`}>
        {formatValue(value)}
      </div>
    </div>
  );
}

export default function MetricsPanel({ result }: MetricsPanelProps) {
  const totalPnL = result.final_capital - result.initial_capital;
  const isProfit = totalPnL >= 0;

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Performance Summary</h3>
          <div className={`flex items-center gap-2 ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
            {isProfit ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            <span className="text-xl font-bold">
              {isProfit ? '+' : ''}{(result.total_return_pct * 100).toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-slate-400 text-xs">Initial Capital</div>
            <div className="text-white font-semibold">
              ${result.initial_capital.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-slate-400 text-xs">Final Capital</div>
            <div className={`font-semibold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
              ${result.final_capital.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <div className="text-slate-400 text-xs">Net P&L</div>
            <div className={`font-semibold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
              {isProfit ? '+' : ''}${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Total Trades"
          value={result.total_trades}
          icon={Activity}
        />
        <MetricCard
          label="Win Rate"
          value={result.win_rate}
          format="percent"
          positive={result.win_rate >= 0.5}
          icon={Target}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={result.sharpe_ratio}
          format="ratio"
          positive={result.sharpe_ratio > 1}
          icon={BarChart3}
        />
        <MetricCard
          label="Profit Factor"
          value={result.profit_factor}
          format="ratio"
          positive={result.profit_factor > 1}
        />
        <MetricCard
          label="Max Drawdown"
          value={-Math.abs(result.max_drawdown_pct)}
          format="percent"
          positive={result.max_drawdown_pct < 0.1}
        />
        <MetricCard
          label="Avg Trade P&L"
          value={result.avg_trade_pnl}
          format="currency"
          positive={result.avg_trade_pnl > 0}
        />
        <MetricCard
          label="Avg Win"
          value={result.avg_win}
          format="currency"
          positive={true}
          icon={DollarSign}
        />
        <MetricCard
          label="Avg Loss"
          value={-Math.abs(result.avg_loss)}
          format="currency"
          positive={false}
        />
        <MetricCard
          label="Largest Win"
          value={result.largest_win}
          format="currency"
          positive={true}
        />
        <MetricCard
          label="Largest Loss"
          value={-Math.abs(result.largest_loss)}
          format="currency"
          positive={false}
        />
        <MetricCard
          label="Winning Trades"
          value={result.winning_trades}
          positive={true}
        />
        <MetricCard
          label="Losing Trades"
          value={result.losing_trades}
          positive={false}
        />
      </div>

      {/* Date Range */}
      <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
        <div className="flex justify-between items-center text-sm">
          <span className="text-slate-400">Backtest Period:</span>
          <span className="text-white">
            {result.start_date} to {result.end_date}
          </span>
        </div>
      </div>
    </div>
  );
}
