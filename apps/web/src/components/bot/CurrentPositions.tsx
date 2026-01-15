/**
 * Current Positions Component
 * Table showing all open positions
 */
import { X, TrendingUp, TrendingDown } from 'lucide-react';
import type { Position } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

interface CurrentPositionsProps {
  positions: Position[];
  onClosePosition: (symbol: string) => void;
  loading?: boolean;
}

export default function CurrentPositions({
  positions,
  onClosePosition,
  loading,
}: CurrentPositionsProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-40 mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Current Positions ({positions.length})
        </h3>
      </div>

      {positions.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <p>No open positions</p>
          <p className="text-sm mt-1">The bot will open positions when signals are detected</p>
        </div>
      ) : (
        <div className="space-y-3">
          {positions.map((position) => (
            <div
              key={position.symbol}
              className="bg-slate-700/50 rounded-lg p-4 flex items-center justify-between"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <div>
                    <p className="font-semibold text-white">{position.symbol}</p>
                    <p className="text-sm text-slate-400">
                      {position.quantity} shares @ {formatCurrency(position.entry_price)}
                    </p>
                  </div>
                  {position.trade_type && (
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded ${
                        position.trade_type === 'SWING'
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-purple-500/20 text-purple-400'
                      }`}
                    >
                      {position.trade_type}
                    </span>
                  )}
                </div>

                {/* Stop Loss / Target */}
                <div className="flex gap-4 mt-2 text-xs text-slate-500">
                  {position.stop_loss && (
                    <span>SL: {formatCurrency(position.stop_loss)}</span>
                  )}
                  {position.profit_target && (
                    <span>TP: {formatCurrency(position.profit_target)}</span>
                  )}
                </div>
              </div>

              {/* P&L */}
              <div className="text-right mr-4">
                <div className="flex items-center gap-1">
                  {position.unrealized_pnl >= 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-500" />
                  )}
                  <span className={`font-semibold ${getPnLColor(position.unrealized_pnl)}`}>
                    {formatCurrency(position.unrealized_pnl)}
                  </span>
                </div>
                <p className={`text-sm ${getPnLColor(position.unrealized_pnl_pct)}`}>
                  {formatPercent(position.unrealized_pnl_pct)}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  @ {formatCurrency(position.current_price)}
                </p>
              </div>

              {/* Close Button */}
              <button
                onClick={() => onClosePosition(position.symbol)}
                className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/20
                         rounded-lg transition-colors"
                title="Close position"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Total Value */}
      {positions.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Total Market Value</span>
            <span className="font-semibold text-white">
              {formatCurrency(positions.reduce((sum, p) => sum + p.market_value, 0))}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
