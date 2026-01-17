/**
 * Account Summary Component
 * Shows equity, cash, buying power, P&L, and portfolio allocation
 */
import { DollarSign, TrendingUp, TrendingDown, Wallet, PieChart, Activity, Shield } from 'lucide-react';
import type { AccountSummary as AccountSummaryType } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

interface AccountSummaryProps {
  account: AccountSummaryType | null;
  loading?: boolean;
}

export default function AccountSummary({ account, loading }: AccountSummaryProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-40 mb-4"></div>
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!account) {
    return (
      <div className="bg-slate-800 rounded-xl p-4">
        <p className="text-slate-400">Unable to fetch account data</p>
      </div>
    );
  }

  // Calculate portfolio metrics
  const investedAmount = account.equity - account.cash;
  const investedPct = account.equity > 0 ? (investedAmount / account.equity) * 100 : 0;
  const cashPct = 100 - investedPct;

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-white mb-3">Account Summary</h3>

      {/* Main Stats - 2x2 Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {/* Equity */}
        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <DollarSign className="w-3.5 h-3.5" />
            <span className="text-xs">Equity</span>
          </div>
          <p className="text-xl font-bold text-white">{formatCurrency(account.equity)}</p>
        </div>

        {/* Cash */}
        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Wallet className="w-3.5 h-3.5" />
            <span className="text-xs">Cash</span>
          </div>
          <p className="text-xl font-bold text-white">{formatCurrency(account.cash)}</p>
        </div>

        {/* Day P&L */}
        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            {account.day_pnl >= 0 ? (
              <TrendingUp className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5 text-red-500" />
            )}
            <span className="text-xs">Today's P&L</span>
          </div>
          <p className={`text-lg font-bold ${getPnLColor(account.day_pnl)}`}>
            {formatCurrency(account.day_pnl)}
          </p>
          <p className={`text-xs ${getPnLColor(account.day_pnl_pct)}`}>
            {formatPercent(account.day_pnl_pct)}
          </p>
        </div>

        {/* Unrealized P&L */}
        <div className="bg-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            {account.unrealized_pnl >= 0 ? (
              <TrendingUp className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5 text-red-500" />
            )}
            <span className="text-xs">Open P&L</span>
          </div>
          <p className={`text-lg font-bold ${getPnLColor(account.unrealized_pnl)}`}>
            {formatCurrency(account.unrealized_pnl)}
          </p>
          <p className={`text-xs ${getPnLColor(account.unrealized_pnl_pct)}`}>
            {formatPercent(account.unrealized_pnl_pct)}
          </p>
        </div>
      </div>

      {/* Buying Power - Compact */}
      <div className="p-2.5 bg-slate-700/30 rounded-lg mb-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">Buying Power</span>
          <span className="text-base font-semibold text-white">
            {formatCurrency(account.buying_power)}
          </span>
        </div>
      </div>

      {/* Portfolio Allocation Visual */}
      <div className="p-3 bg-slate-700/30 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <PieChart className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs text-slate-400">Portfolio Allocation</span>
        </div>

        {/* Progress bar showing cash vs invested */}
        <div className="h-2 bg-slate-600 rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
            style={{ width: `${investedPct}%` }}
          />
        </div>

        <div className="flex justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500" />
            <span className="text-slate-400">Invested</span>
            <span className="text-white font-medium">{investedPct.toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-slate-600" />
            <span className="text-slate-400">Cash</span>
            <span className="text-white font-medium">{cashPct.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="p-2 bg-slate-700/20 rounded-lg">
          <div className="flex items-center gap-1 text-slate-500 mb-0.5">
            <Activity className="w-3 h-3" />
            <span className="text-[10px]">Day Range</span>
          </div>
          <div className="text-xs font-medium text-white">
            {formatCurrency(account.equity - Math.abs(account.day_pnl))} - {formatCurrency(account.equity)}
          </div>
        </div>
        <div className="p-2 bg-slate-700/20 rounded-lg">
          <div className="flex items-center gap-1 text-slate-500 mb-0.5">
            <Shield className="w-3 h-3" />
            <span className="text-[10px]">Risk Level</span>
          </div>
          <div className={`text-xs font-medium ${
            investedPct > 80 ? 'text-red-400' :
            investedPct > 50 ? 'text-yellow-400' : 'text-green-400'
          }`}>
            {investedPct > 80 ? 'High' : investedPct > 50 ? 'Moderate' : 'Low'}
            <span className="text-slate-500 ml-1">({investedPct.toFixed(0)}% deployed)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
