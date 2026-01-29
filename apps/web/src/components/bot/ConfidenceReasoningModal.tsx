/**
 * Confidence Reasoning Modal
 * Shows detailed breakdown of AI confidence score calculation
 */
import { X, TrendingUp, MessageSquare, History, BarChart3, Target, Info } from 'lucide-react';
import type { AIDecision, TimeHorizon } from '../../types/bot';

interface ConfidenceReasoningModalProps {
  decision: AIDecision;
  isOpen: boolean;
  onClose: () => void;
}

interface WeightCategory {
  label: string;
  weight: number;
  contribution: string;
  icon: typeof TrendingUp;
  color: string;
}

export default function ConfidenceReasoningModal({
  decision,
  isOpen,
  onClose,
}: ConfidenceReasoningModalProps) {
  if (!isOpen) return null;

  // Build weight categories from breakdown or use defaults
  const breakdown = decision.confidence_breakdown;

  const categories: WeightCategory[] = [
    {
      label: 'Technical Analysis',
      weight: breakdown?.technical_weight ?? Math.round(decision.technical_score * 0.45),
      contribution: breakdown?.technical_contribution ??
        `Score: ${decision.technical_score}, Signal: ${decision.technical_signal}`,
      icon: TrendingUp,
      color: 'text-blue-400',
    },
    {
      label: 'Order Flow / Volume',
      weight: breakdown?.volume_weight ?? Math.round(decision.confidence * 0.2),
      contribution: breakdown?.volume_contribution ?? 'Volume analysis from technical indicators',
      icon: BarChart3,
      color: 'text-purple-400',
    },
    {
      label: 'Sentiment',
      weight: breakdown?.sentiment_weight ?? Math.round(decision.confidence * 0.15),
      contribution: breakdown?.sentiment_contribution ?? 'Market sentiment factored into decision',
      icon: MessageSquare,
      color: 'text-green-400',
    },
    {
      label: 'Historical Win-Rate',
      weight: breakdown?.historical_accuracy ?? Math.round(decision.confidence * 0.05),
      contribution: `Pattern accuracy at this confidence level`,
      icon: History,
      color: 'text-yellow-400',
    },
  ];

  const totalWeight = categories.reduce((sum, cat) => sum + cat.weight, 0);

  const getHorizonLabel = (horizon?: TimeHorizon) => {
    switch (horizon) {
      case 'SCALP': return { label: 'Scalp', color: 'bg-red-500/20 text-red-400', desc: '< 5 minutes' };
      case 'INTRADAY': return { label: 'Intraday', color: 'bg-orange-500/20 text-orange-400', desc: 'Same day' };
      case 'SWING': return { label: 'Swing', color: 'bg-blue-500/20 text-blue-400', desc: '1-5 days' };
      default: return { label: 'Swing', color: 'bg-blue-500/20 text-blue-400', desc: '1-5 days' };
    }
  };

  const horizon = getHorizonLabel(decision.time_horizon);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal - scrollable on small screens */}
      <div className="relative bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg max-h-[95vh] overflow-hidden flex flex-col border border-slate-700">
        {/* Header - sticky */}
        <div className="flex items-center justify-between p-3 sm:p-4 border-b border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3">
            <Target className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400" />
            <div>
              <h2 className="text-base sm:text-lg font-semibold text-white">
                Confidence: {decision.symbol}
              </h2>
              <div className="flex items-center gap-2 mt-0.5 sm:mt-1">
                <span className={`px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-xs font-medium rounded ${horizon.color}`}>
                  {horizon.label}
                </span>
                <span className="text-[10px] sm:text-xs text-slate-500">{horizon.desc}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content - scrollable */}
        <div className="p-3 sm:p-4 space-y-3 sm:space-y-4 overflow-y-auto flex-1">
          {/* Overall Confidence */}
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Overall Confidence</span>
              <span className={`text-2xl font-bold ${
                decision.confidence >= 75 ? 'text-green-400' :
                decision.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {decision.confidence}%
              </span>
            </div>
            <div className="w-full bg-slate-600 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all ${
                  decision.confidence >= 75 ? 'bg-green-500' :
                  decision.confidence >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${decision.confidence}%` }}
              />
            </div>
          </div>

          {/* Weight Breakdown Table */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Info className="w-4 h-4" />
              Confidence Breakdown
            </h3>
            <div className="bg-slate-700/30 rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-700">
                    <th className="text-left p-3">Category</th>
                    <th className="text-right p-3">Weight</th>
                    <th className="text-left p-3">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((cat, idx) => (
                    <tr key={idx} className="border-b border-slate-700/50 last:border-0">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <cat.icon className={`w-4 h-4 ${cat.color}`} />
                          <span className="text-sm text-white">{cat.label}</span>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <span className={`text-sm font-medium ${cat.color}`}>
                          +{cat.weight}%
                        </span>
                      </td>
                      <td className="p-3">
                        <span className="text-xs text-slate-400">{cat.contribution}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-700/50">
                    <td className="p-3">
                      <span className="text-sm font-medium text-white">Total</span>
                    </td>
                    <td className="p-3 text-right">
                      <span className="text-sm font-bold text-white">{totalWeight}%</span>
                    </td>
                    <td className="p-3"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* AI Reasoning */}
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-slate-300">AI Reasoning</h3>
            <div className="bg-slate-700/30 rounded-lg p-3">
              <p className="text-sm text-slate-300 leading-relaxed">
                "{decision.reasoning}"
              </p>
            </div>
          </div>

          {/* Concerns */}
          {decision.concerns && decision.concerns.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-slate-300">Concerns</h3>
              <ul className="space-y-1">
                {decision.concerns.map((concern, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-yellow-400">
                    <span className="text-yellow-500">•</span>
                    {concern}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trade Parameters (if approved) */}
          {decision.decision === 'APPROVE' && (
            <div className="grid grid-cols-3 gap-3">
              {decision.suggested_position_size_pct && (
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <span className="text-xs text-slate-400 block mb-1">Position Size</span>
                  <span className="text-lg font-bold text-white">
                    {(decision.suggested_position_size_pct * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              {decision.suggested_stop_loss_pct && (
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <span className="text-xs text-slate-400 block mb-1">Stop Loss</span>
                  <span className="text-lg font-bold text-red-400">
                    -{(decision.suggested_stop_loss_pct * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              {decision.suggested_take_profit_pct && (
                <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                  <span className="text-xs text-slate-400 block mb-1">Take Profit</span>
                  <span className="text-lg font-bold text-green-400">
                    +{(decision.suggested_take_profit_pct * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer - sticky */}
        <div className="p-3 sm:p-4 border-t border-slate-700 flex items-center justify-between flex-shrink-0">
          <div className="text-[10px] sm:text-xs text-slate-500">
            {decision.ai_generated ? (
              <span>Generated by {decision.model}</span>
            ) : (
              <span>Technical fallback (AI unavailable)</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-3 sm:px-4 py-1.5 sm:py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-xs sm:text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
