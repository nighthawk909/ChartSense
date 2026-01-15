/**
 * Account Summary Component
 * Shows equity, cash, buying power, and P&L
 */
import { DollarSign, TrendingUp, TrendingDown, Wallet } from 'lucide-react';
import type { AccountSummary as AccountSummaryType } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

interface AccountSummaryProps {
  account: AccountSummaryType | null;
  loading?: boolean;
}

export default function AccountSummary({ account, loading }: AccountSummaryProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-40 mb-4"></div>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!account) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <p className="text-slate-400">Unable to fetch account data</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Account Summary</h3>

      <div className="grid grid-cols-2 gap-4">
        {/* Equity */}
        <div className="bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <DollarSign className="w-4 h-4" />
            <span className="text-sm">Equity</span>
          </div>
          <p className="text-2xl font-bold text-white">{formatCurrency(account.equity)}</p>
        </div>

        {/* Cash */}
        <div className="bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Wallet className="w-4 h-4" />
            <span className="text-sm">Cash</span>
          </div>
          <p className="text-2xl font-bold text-white">{formatCurrency(account.cash)}</p>
        </div>

        {/* Day P&L */}
        <div className="bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            {account.day_pnl >= 0 ? (
              <TrendingUp className="w-4 h-4 text-green-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm">Today's P&L</span>
          </div>
          <p className={`text-xl font-bold ${getPnLColor(account.day_pnl)}`}>
            {formatCurrency(account.day_pnl)}
          </p>
          <p className={`text-sm ${getPnLColor(account.day_pnl_pct)}`}>
            {formatPercent(account.day_pnl_pct)}
          </p>
        </div>

        {/* Unrealized P&L */}
        <div className="bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            {account.unrealized_pnl >= 0 ? (
              <TrendingUp className="w-4 h-4 text-green-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-500" />
            )}
            <span className="text-sm">Open P&L</span>
          </div>
          <p className={`text-xl font-bold ${getPnLColor(account.unrealized_pnl)}`}>
            {formatCurrency(account.unrealized_pnl)}
          </p>
          <p className={`text-sm ${getPnLColor(account.unrealized_pnl_pct)}`}>
            {formatPercent(account.unrealized_pnl_pct)}
          </p>
        </div>
      </div>

      {/* Buying Power */}
      <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Buying Power</span>
          <span className="text-lg font-semibold text-white">
            {formatCurrency(account.buying_power)}
          </span>
        </div>
      </div>
    </div>
  );
}
