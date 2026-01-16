/**
 * Trade History Component
 * Table showing completed trades with expandable post-mortem analysis
 */
import { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Brain,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Target,
  Clock
} from 'lucide-react';
import type { Trade, TradeAnalysis } from '../../types/bot';
import { formatCurrency, formatPercent, getPnLColor, performanceApi } from '../../services/botApi';

interface TradeHistoryProps {
  trades: Trade[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

// Post-mortem analysis panel component
function PostMortemPanel({
  analysis,
  loading,
  onReanalyze
}: {
  analysis: TradeAnalysis | null;
  loading: boolean;
  onReanalyze: () => void;
}) {
  if (loading) {
    return (
      <div className="p-4 bg-slate-900/50 border-t border-slate-700 animate-pulse">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-slate-400">Analyzing trade...</span>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-slate-700 rounded w-3/4"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="p-4 bg-slate-900/50 border-t border-slate-700">
        <p className="text-sm text-slate-400">Unable to load analysis.</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-slate-900/50 border-t border-slate-700 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-white">Post-Mortem Analysis</span>
        </div>
        <button
          onClick={onReanalyze}
          className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400
                   hover:text-white hover:bg-slate-700 rounded"
        >
          <RefreshCw className="w-3 h-3" />
          Re-analyze
        </button>
      </div>

      {/* AI Summary */}
      {analysis.ai_summary && (
        <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg">
          <p className="text-sm text-purple-200">{analysis.ai_summary}</p>
        </div>
      )}

      {/* Trade Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-slate-400">Duration</p>
          <p className="text-sm text-white flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-500" />
            {analysis.trade_summary?.duration?.formatted || '--'}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Entry Score</p>
          <p className="text-sm text-white">
            {analysis.trade_summary?.entry_score
              ? `${analysis.trade_summary.entry_score.toFixed(0)}/100`
              : '--'}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Optimal Exit</p>
          <p className="text-sm text-white flex items-center gap-1">
            <Target className="w-3 h-3 text-slate-500" />
            {analysis.optimal_exit_price
              ? formatCurrency(analysis.optimal_exit_price)
              : '--'}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Missed Profit</p>
          <p className={`text-sm ${analysis.missed_profit && analysis.missed_profit > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
            {analysis.missed_profit !== null
              ? (analysis.missed_profit > 0 ? `$${analysis.missed_profit.toFixed(2)}` : '$0.00')
              : '--'}
          </p>
        </div>
      </div>

      {/* Exit Efficiency */}
      {analysis.optimal_exit_analysis && (
        <div>
          <p className="text-xs text-slate-400 mb-2">Exit Efficiency</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  analysis.optimal_exit_analysis.exit_efficiency_pct >= 70
                    ? 'bg-green-500'
                    : analysis.optimal_exit_analysis.exit_efficiency_pct >= 50
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${Math.max(0, Math.min(100, analysis.optimal_exit_analysis.exit_efficiency_pct))}%` }}
              />
            </div>
            <span className="text-sm text-white font-medium">
              {analysis.optimal_exit_analysis.exit_efficiency_pct.toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      {/* What Went Well / Wrong */}
      <div className="grid md:grid-cols-2 gap-4">
        {analysis.what_went_well && analysis.what_went_well.length > 0 && (
          <div>
            <p className="text-xs text-green-400 mb-2 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" />
              What Went Well
            </p>
            <ul className="space-y-1">
              {analysis.what_went_well.map((item, i) => (
                <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
        {analysis.what_went_wrong && analysis.what_went_wrong.length > 0 && (
          <div>
            <p className="text-xs text-red-400 mb-2 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              What Went Wrong
            </p>
            <ul className="space-y-1">
              {analysis.what_went_wrong.map((item, i) => (
                <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="text-red-500 mt-1">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Lessons Learned */}
      {analysis.lessons_learned && (
        <div className="p-3 bg-slate-800 rounded-lg">
          <p className="text-xs text-slate-400 mb-1">Key Lessons</p>
          <p className="text-sm text-slate-200">{analysis.lessons_learned}</p>
        </div>
      )}
    </div>
  );
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
  const [expandedTrade, setExpandedTrade] = useState<number | null>(null);
  const [analysisData, setAnalysisData] = useState<Record<number, TradeAnalysis | null>>({});
  const [analysisLoading, setAnalysisLoading] = useState<Record<number, boolean>>({});

  const toggleExpand = async (tradeId: number) => {
    if (expandedTrade === tradeId) {
      setExpandedTrade(null);
      return;
    }

    setExpandedTrade(tradeId);

    // Fetch analysis if not already loaded
    if (!analysisData[tradeId] && !analysisLoading[tradeId]) {
      setAnalysisLoading(prev => ({ ...prev, [tradeId]: true }));
      try {
        const analysis = await performanceApi.getTradeAnalysis(tradeId);
        setAnalysisData(prev => ({ ...prev, [tradeId]: analysis }));
      } catch (err) {
        console.error('Failed to load analysis:', err);
        setAnalysisData(prev => ({ ...prev, [tradeId]: null }));
      } finally {
        setAnalysisLoading(prev => ({ ...prev, [tradeId]: false }));
      }
    }
  };

  const reanalyze = async (tradeId: number) => {
    setAnalysisLoading(prev => ({ ...prev, [tradeId]: true }));
    try {
      const analysis = await performanceApi.analyzeTradeAgain(tradeId);
      setAnalysisData(prev => ({ ...prev, [tradeId]: analysis }));
    } catch (err) {
      console.error('Failed to re-analyze:', err);
    } finally {
      setAnalysisLoading(prev => ({ ...prev, [tradeId]: false }));
    }
  };

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
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <Brain className="w-4 h-4 text-purple-400" />
          <span>Click a trade for AI analysis</span>
        </div>
      </div>

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
                  <th className="pb-2 font-medium w-8"></th>
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
                  <>
                    <tr
                      key={trade.id}
                      onClick={() => toggleExpand(trade.id)}
                      className={`border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors ${
                        expandedTrade === trade.id ? 'bg-slate-700/20' : ''
                      }`}
                    >
                      <td className="py-3">
                        {expandedTrade === trade.id ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </td>
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
                    {/* Expanded Analysis Panel */}
                    {expandedTrade === trade.id && (
                      <tr key={`${trade.id}-analysis`}>
                        <td colSpan={8} className="p-0">
                          <PostMortemPanel
                            analysis={analysisData[trade.id]}
                            loading={analysisLoading[trade.id] || false}
                            onReanalyze={() => reanalyze(trade.id)}
                          />
                        </td>
                      </tr>
                    )}
                  </>
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
