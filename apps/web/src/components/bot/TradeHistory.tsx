/**
 * Trade History Component
 * Table showing completed trades
 */
import { TrendingUp, TrendingDown, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Trade } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

interface TradeHistoryProps {
  trades: Trade[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

export default function TradeHistory({
  trades,
  totalCount,
  page,
  pageSize,
  onPageChange,
  loading,
}: TradeHistoryProps) {
  const totalPages = Math.ceil(totalCount / pageSize);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-40 mb-4"></div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Recent Trades</h3>

      {trades.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <p>No completed trades yet</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-slate-400 border-b border-slate-700">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Symbol</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium text-right">Entry</th>
                  <th className="pb-2 font-medium text-right">Exit</th>
                  <th className="pb-2 font-medium text-right">P&L</th>
                  <th className="pb-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {trades.map((trade) => (
                  <tr
                    key={trade.id}
                    className="border-b border-slate-700/50 hover:bg-slate-700/30"
                  >
                    <td className="py-3 text-slate-400">
                      {trade.exit_time
                        ? new Date(trade.exit_time).toLocaleDateString()
                        : '--'}
                    </td>
                    <td className="py-3">
                      <span className="font-medium text-white">{trade.symbol}</span>
                    </td>
                    <td className="py-3">
                      {trade.trade_type && (
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            trade.trade_type === 'SWING'
                              ? 'bg-blue-500/20 text-blue-400'
                              : 'bg-purple-500/20 text-purple-400'
                          }`}
                        >
                          {trade.trade_type}
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-right text-slate-300">
                      {formatCurrency(trade.entry_price)}
                    </td>
                    <td className="py-3 text-right text-slate-300">
                      {trade.exit_price ? formatCurrency(trade.exit_price) : '--'}
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {trade.profit_loss !== null && (
                          <>
                            {trade.profit_loss >= 0 ? (
                              <TrendingUp className="w-3 h-3 text-green-500" />
                            ) : (
                              <TrendingDown className="w-3 h-3 text-red-500" />
                            )}
                            <span className={getPnLColor(trade.profit_loss)}>
                              {formatCurrency(trade.profit_loss)}
                            </span>
                          </>
                        )}
                      </div>
                      {trade.profit_loss_pct !== null && (
                        <p className={`text-xs ${getPnLColor(trade.profit_loss_pct)}`}>
                          {formatPercent(trade.profit_loss_pct * 100)}
                        </p>
                      )}
                    </td>
                    <td className="py-3">
                      {trade.exit_reason && (
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            trade.exit_reason === 'PROFIT_TARGET'
                              ? 'bg-green-500/20 text-green-400'
                              : trade.exit_reason === 'STOP_LOSS'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-slate-500/20 text-slate-400'
                          }`}
                        >
                          {trade.exit_reason.replace(/_/g, ' ')}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-700">
              <p className="text-sm text-slate-400">
                Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalCount)} of{' '}
                {totalCount}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onPageChange(page - 1)}
                  disabled={page === 1}
                  className="p-2 text-slate-400 hover:text-white disabled:opacity-50
                           disabled:cursor-not-allowed rounded-lg hover:bg-slate-700"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-slate-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => onPageChange(page + 1)}
                  disabled={page === totalPages}
                  className="p-2 text-slate-400 hover:text-white disabled:opacity-50
                           disabled:cursor-not-allowed rounded-lg hover:bg-slate-700"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
