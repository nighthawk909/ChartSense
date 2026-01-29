/**
 * Current Positions Component
 * Table showing all open positions with exit strategy display
 * Click on any position to see entry insights (reasoning, indicators, confidence)
 * Supports rescanning legacy positions for updated recommendations
 */
import { useState } from 'react';
import { X, TrendingUp, TrendingDown, Clock, Target, Shield, AlertCircle, ChevronRight, Brain, Activity, BarChart3 } from 'lucide-react';
import type { Position } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor } from '../../services/botApi';

// Calculate hold duration in human-readable format
function getHoldDuration(entryTime: string): string {
  if (!entryTime) return 'N/A';

  const entry = new Date(entryTime);
  const now = new Date();

  // Check if date is valid and not from epoch (1970)
  if (isNaN(entry.getTime()) || entry.getFullYear() < 2000) {
    return 'N/A';
  }

  const diffMs = now.getTime() - entry.getTime();

  // If negative (future date) or unreasonably long (> 365 days), show N/A
  if (diffMs < 0 || diffMs > 365 * 24 * 60 * 60 * 1000) {
    return 'N/A';
  }

  const minutes = Math.floor(diffMs / (1000 * 60));
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

// Format entry time for display
function formatEntryTime(entryTime: string): string {
  if (!entryTime) return 'Unknown';

  const entry = new Date(entryTime);

  // Check if date is valid and not from epoch (1970)
  if (isNaN(entry.getTime()) || entry.getFullYear() < 2000) {
    return 'Unknown';
  }

  const now = new Date();
  const isToday = entry.toDateString() === now.toDateString();
  const isYesterday = new Date(now.getTime() - 86400000).toDateString() === entry.toDateString();

  if (isToday) {
    return `Today ${entry.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }
  if (isYesterday) {
    return `Yesterday ${entry.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  return entry.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
    ' ' + entry.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Generate exit strategy description based on position data
function getExitStrategyDisplay(position: Position): { icon: React.ReactNode; text: string; color: string } {
  const pnlPct = position.unrealized_pnl_pct ?? 0;
  const currentPrice = position.current_price ?? 0;

  // If custom exit reason is provided, use it
  if (position.exit_reason) {
    return {
      icon: <Target className="w-3 h-3" />,
      text: position.exit_reason,
      color: 'text-blue-400'
    };
  }

  // Generate based on position state (with null safety)
  if (position.stop_loss && position.profit_target && currentPrice > 0) {
    if (pnlPct >= 0) {
      const distToTarget = ((position.profit_target - currentPrice) / currentPrice) * 100;
      if (distToTarget < 2) {
        return {
          icon: <Target className="w-3 h-3" />,
          text: `Target ${distToTarget.toFixed(1)}% away - consider taking profit`,
          color: 'text-green-400'
        };
      }
      return {
        icon: <TrendingUp className="w-3 h-3" />,
        text: `Holding for target: $${position.profit_target.toFixed(2)} (+${distToTarget.toFixed(1)}%)`,
        color: 'text-green-400'
      };
    } else {
      const distToStop = ((currentPrice - position.stop_loss) / currentPrice) * 100;
      if (distToStop < 2) {
        return {
          icon: <AlertCircle className="w-3 h-3" />,
          text: `Near stop loss - ${distToStop.toFixed(1)}% buffer remaining`,
          color: 'text-red-400'
        };
      }
      return {
        icon: <Shield className="w-3 h-3" />,
        text: `Protected by stop loss at $${position.stop_loss.toFixed(2)}`,
        color: 'text-yellow-400'
      };
    }
  }

  // Default based on trade type
  if (position.trade_type === 'SWING') {
    return {
      icon: <Clock className="w-3 h-3" />,
      text: 'Swing trade - holding for multi-day move',
      color: 'text-blue-400'
    };
  }

  return {
    icon: <Clock className="w-3 h-3" />,
    text: 'Monitoring for exit signal',
    color: 'text-slate-400'
  };
}

// Position Details Modal Component
function PositionDetailsModal({
  position,
  isOpen,
  onClose,
}: {
  position: Position;
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!isOpen) return null;

  const holdDuration = getHoldDuration(position.entry_time);
  const entryTimeFormatted = formatEntryTime(position.entry_time);
  const hasIndicators = position.indicators_snapshot && Object.keys(position.indicators_snapshot).length > 0;
  const hasConfluence = position.confluence_factors && position.confluence_factors.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-slate-800 rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto border border-slate-700">
        {/* Header */}
        <div className="sticky top-0 bg-slate-800 border-b border-slate-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${position.unrealized_pnl >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              {position.unrealized_pnl >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-400" />
              )}
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">{position.symbol}</h3>
              <p className="text-sm text-slate-400">Position Details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Entry Summary */}
          <div className="bg-slate-700/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Entry Information
            </h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500">Entry Time</span>
                <p className="text-white font-medium">{entryTimeFormatted}</p>
              </div>
              <div>
                <span className="text-slate-500">Hold Duration</span>
                <p className="text-white font-medium">{holdDuration}</p>
              </div>
              <div>
                <span className="text-slate-500">Entry Price</span>
                <p className="text-white font-medium">{formatCurrency(position.entry_price ?? 0)}</p>
              </div>
              <div>
                <span className="text-slate-500">Current Price</span>
                <p className="text-white font-medium">{formatCurrency(position.current_price ?? 0)}</p>
              </div>
              <div>
                <span className="text-slate-500">Quantity</span>
                <p className="text-white font-medium">{position.quantity ?? 0}</p>
              </div>
              <div>
                <span className="text-slate-500">Trade Type</span>
                <p className={`font-medium ${
                  position.trade_type === 'SWING' ? 'text-blue-400' :
                  position.trade_type === 'INTRADAY' ? 'text-orange-400' :
                  position.trade_type === 'SCALP' ? 'text-red-400' : 'text-slate-400'
                }`}>
                  {position.trade_type || 'Unknown'}
                </p>
              </div>
            </div>
          </div>

          {/* P&L Summary */}
          <div className="bg-slate-700/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Performance
            </h4>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-slate-500 text-sm">Unrealized P&L</span>
                <p className={`text-2xl font-bold ${getPnLColor(position.unrealized_pnl ?? 0)}`}>
                  {formatCurrency(position.unrealized_pnl ?? 0)}
                </p>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-sm">Return</span>
                <p className={`text-2xl font-bold ${getPnLColor(position.unrealized_pnl_pct ?? 0)}`}>
                  {formatPercent(position.unrealized_pnl_pct ?? 0)}
                </p>
              </div>
            </div>
            {(position.stop_loss != null || position.profit_target != null) && (
              <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-600">
                {position.stop_loss != null && (
                  <div>
                    <span className="text-slate-500 text-xs">Stop Loss</span>
                    <p className="text-red-400 font-medium">{formatCurrency(position.stop_loss)}</p>
                  </div>
                )}
                {position.profit_target != null && (
                  <div>
                    <span className="text-slate-500 text-xs">Take Profit</span>
                    <p className="text-green-400 font-medium">{formatCurrency(position.profit_target)}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Confidence Score */}
          {position.entry_score !== null && position.entry_score !== undefined && (
            <div className="bg-slate-700/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4" />
                AI Confidence at Entry
              </h4>
              <div className="flex items-center gap-4">
                <div className="relative w-16 h-16">
                  <svg className="w-16 h-16 transform -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                      className="text-slate-600"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                      strokeDasharray={`${(position.entry_score / 100) * 176} 176`}
                      className={
                        position.entry_score >= 80 ? 'text-green-500' :
                        position.entry_score >= 65 ? 'text-yellow-500' : 'text-red-500'
                      }
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white">
                    {position.entry_score.toFixed(0)}
                  </span>
                </div>
                <div>
                  <p className={`text-lg font-semibold ${
                    position.entry_score >= 80 ? 'text-green-400' :
                    position.entry_score >= 65 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {position.entry_score >= 80 ? 'Excellent' :
                     position.entry_score >= 65 ? 'Good' : 'Fair'}
                  </p>
                  <p className="text-sm text-slate-400">Entry Signal Quality</p>
                </div>
              </div>
            </div>
          )}

          {/* Entry Reason */}
          {position.entry_reason && (
            <div className="bg-slate-700/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                <Target className="w-4 h-4" />
                Why We Entered
              </h4>
              <p className="text-white text-sm leading-relaxed">{position.entry_reason}</p>
            </div>
          )}

          {/* Confluence Factors */}
          {hasConfluence && (
            <div className="bg-slate-700/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Confluence Factors
              </h4>
              <div className="flex flex-wrap gap-2">
                {position.confluence_factors!.map((factor, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-medium"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Technical Indicators at Entry */}
          {hasIndicators && (
            <div className="bg-slate-700/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                Indicators at Entry
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(position.indicators_snapshot!).slice(0, 12).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center py-1 border-b border-slate-600/50">
                    <span className="text-slate-400 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-white font-medium">
                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No insight data available */}
          {!position.entry_reason && !hasIndicators && !hasConfluence && position.entry_score === null && (
            <div className="bg-slate-700/50 rounded-lg p-4 text-center">
              <Brain className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">
                Entry insight data not available for this position.
              </p>
              <p className="text-slate-500 text-xs mt-1">
                This may be an older position or one that was opened manually.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface CurrentPositionsProps {
  positions: Position[];
  onClosePosition: (symbol: string) => void;
  loading?: boolean;
}

export default function CurrentPositions({
  positions = [],  // Default to empty array
  onClosePosition,
  loading,
}: CurrentPositionsProps) {
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);

  // Safety check - ensure positions is always an array
  const safePositions = Array.isArray(positions) ? positions : [];

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
    <>
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            Current Positions ({safePositions.length})
          </h3>
        </div>

        {safePositions.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p>No open positions</p>
            <p className="text-sm mt-1">The bot will open positions when signals are detected</p>
          </div>
        ) : (
          <div className="space-y-3">
            {safePositions.map((position) => {
              const exitStrategy = getExitStrategyDisplay(position);
              const holdDuration = getHoldDuration(position.entry_time);
              const entryTimeFormatted = formatEntryTime(position.entry_time);

              return (
                <div
                  key={position.symbol}
                  className="bg-slate-700/50 rounded-lg p-4 cursor-pointer hover:bg-slate-700/70 transition-colors group"
                  onClick={() => setSelectedPosition(position)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <div>
                          <p className="font-semibold text-white">{position.symbol}</p>
                          <p className="text-sm text-slate-400">
                            {position.quantity ?? 0} shares @ {formatCurrency(position.entry_price ?? 0)}
                          </p>
                        </div>
                        {position.trade_type && (
                          <span
                            className={`px-2 py-0.5 text-xs font-medium rounded ${
                              position.trade_type === 'SWING'
                                ? 'bg-blue-500/20 text-blue-400'
                                : position.trade_type === 'SCALP'
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-purple-500/20 text-purple-400'
                            }`}
                          >
                            {position.trade_type}
                          </span>
                        )}
                        {/* Show entry time as badge */}
                        <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-600 text-slate-300" title={`Entry: ${entryTimeFormatted}`}>
                          <Clock className="w-3 h-3 inline mr-1" />
                          {holdDuration}
                        </span>
                      </div>

                      {/* Stop Loss / Target */}
                      <div className="flex gap-4 mt-2 text-xs text-slate-500">
                        {position.stop_loss != null && (
                          <span className="text-red-400/70">SL: {formatCurrency(position.stop_loss)}</span>
                        )}
                        {position.profit_target != null && (
                          <span className="text-green-400/70">TP: {formatCurrency(position.profit_target)}</span>
                        )}
                        {/* Show confidence score if available */}
                        {position.entry_score != null && (
                          <span className={`${
                            position.entry_score >= 80 ? 'text-green-400/70' :
                            position.entry_score >= 65 ? 'text-yellow-400/70' : 'text-slate-400/70'
                          }`}>
                            Score: {position.entry_score.toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>

                    {/* P&L */}
                    <div className="text-right mr-4">
                      <div className="flex items-center gap-1">
                        {(position.unrealized_pnl ?? 0) >= 0 ? (
                          <TrendingUp className="w-4 h-4 text-green-500" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-500" />
                        )}
                        <span className={`font-semibold ${getPnLColor(position.unrealized_pnl ?? 0)}`}>
                          {formatCurrency(position.unrealized_pnl ?? 0)}
                        </span>
                      </div>
                      <p className={`text-sm ${getPnLColor(position.unrealized_pnl_pct ?? 0)}`}>
                        {formatPercent(position.unrealized_pnl_pct ?? 0)}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        @ {formatCurrency(position.current_price ?? 0)}
                      </p>
                    </div>

                    {/* Click hint + Close Button */}
                    <div className="flex items-center gap-2">
                      <ChevronRight className="w-4 h-4 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onClosePosition(position.symbol);
                        }}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/20
                                 rounded-lg transition-colors"
                        title="Close position"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Exit Strategy Row */}
                  <div className={`flex items-center gap-2 mt-3 pt-3 border-t border-slate-600/50 text-xs ${exitStrategy.color}`}>
                    {exitStrategy.icon}
                    <span>{exitStrategy.text}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Total Value */}
        {safePositions.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-700">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Total Market Value</span>
              <span className="font-semibold text-white">
                {formatCurrency(safePositions.reduce((sum, p) => sum + (p.market_value ?? 0), 0))}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Position Details Modal */}
      {selectedPosition && (
        <PositionDetailsModal
          position={selectedPosition}
          isOpen={!!selectedPosition}
          onClose={() => setSelectedPosition(null)}
        />
      )}
    </>
  );
}
