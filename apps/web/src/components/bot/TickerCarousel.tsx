/**
 * Ticker Carousel Component
 * Quick-flip navigation through watchlist symbols with AI insights
 */
import { useState } from 'react';
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, Minus, Brain, Clock } from 'lucide-react';
import type { CryptoAnalysisResult, AIDecision, TimeHorizon } from '../../types/bot';

interface TickerItem {
  symbol: string;
  price?: number;
  change24h?: number;
  analysis?: CryptoAnalysisResult;
  aiDecision?: AIDecision;
}

interface TickerCarouselProps {
  items: TickerItem[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onTickerClick?: (symbol: string) => void;
}

export default function TickerCarousel({
  items,
  currentIndex,
  onIndexChange,
  onTickerClick,
}: TickerCarouselProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  if (items.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 text-center text-slate-400">
        No symbols in watchlist
      </div>
    );
  }

  const currentItem = items[currentIndex] || items[0];

  const handlePrev = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    const newIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
    onIndexChange(newIndex);
    setTimeout(() => setIsAnimating(false), 200);
  };

  const handleNext = () => {
    if (isAnimating) return;
    setIsAnimating(true);
    const newIndex = currentIndex === items.length - 1 ? 0 : currentIndex + 1;
    onIndexChange(newIndex);
    setTimeout(() => setIsAnimating(false), 200);
  };

  const getSignalIcon = (signal?: string) => {
    if (signal === 'BUY' || signal === 'STRONG_BUY') return <TrendingUp className="w-4 h-4 text-green-500" />;
    if (signal === 'SELL' || signal === 'STRONG_SELL') return <TrendingDown className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-slate-400" />;
  };

  const getHorizonBadge = (horizon?: TimeHorizon) => {
    switch (horizon) {
      case 'SCALP': return <span className="px-1.5 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">Scalp</span>;
      case 'INTRADAY': return <span className="px-1.5 py-0.5 text-xs bg-orange-500/20 text-orange-400 rounded">Intraday</span>;
      case 'SWING': return <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">Swing</span>;
      default: return null;
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-slate-400">Quick Navigation</h3>
        <span className="text-xs text-slate-500">
          {currentIndex + 1} / {items.length}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {/* Previous Button */}
        <button
          onClick={handlePrev}
          disabled={isAnimating}
          className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-5 h-5 text-white" />
        </button>

        {/* Current Ticker Card */}
        <div
          className={`flex-1 bg-slate-700/50 rounded-lg p-4 cursor-pointer hover:bg-slate-700 transition-all
                    ${isAnimating ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}`}
          onClick={() => onTickerClick?.(currentItem.symbol)}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {getSignalIcon(currentItem.analysis?.signal)}
              <span className="text-lg font-bold text-white">
                {currentItem.symbol.replace('/', '')}
              </span>
              {currentItem.aiDecision?.time_horizon && getHorizonBadge(currentItem.aiDecision.time_horizon)}
            </div>
            {currentItem.price && (
              <span className="text-lg font-semibold text-white">
                ${currentItem.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            )}
          </div>

          {/* 24h Change */}
          {currentItem.change24h !== undefined && (
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-sm font-medium ${currentItem.change24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {currentItem.change24h >= 0 ? '+' : ''}{currentItem.change24h.toFixed(2)}%
              </span>
              <span className="text-xs text-slate-500">24h</span>
            </div>
          )}

          {/* Analysis Summary */}
          {currentItem.analysis && (
            <div className="flex items-center justify-between text-sm">
              <span className={`font-medium ${
                currentItem.analysis.meets_threshold ? 'text-green-400' :
                currentItem.analysis.signal === 'BUY' ? 'text-yellow-400' : 'text-slate-400'
              }`}>
                {currentItem.analysis.confidence.toFixed(0)}% confidence
              </span>
              <span className="text-slate-500">
                Threshold: {currentItem.analysis.threshold}%
              </span>
            </div>
          )}

          {/* AI Decision Preview */}
          {currentItem.aiDecision && (
            <div className="mt-2 pt-2 border-t border-slate-600">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span className={`text-sm font-medium ${
                  currentItem.aiDecision.decision === 'APPROVE' ? 'text-green-400' :
                  currentItem.aiDecision.decision === 'WAIT' ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {currentItem.aiDecision.decision}
                </span>
                {currentItem.aiDecision.wait_for && (
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {currentItem.aiDecision.wait_for}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Next Button */}
        <button
          onClick={handleNext}
          disabled={isAnimating}
          className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Dot Indicators */}
      <div className="flex justify-center gap-1.5 mt-3">
        {items.slice(0, 10).map((_, idx) => (
          <button
            key={idx}
            onClick={() => onIndexChange(idx)}
            className={`w-2 h-2 rounded-full transition-all ${
              idx === currentIndex
                ? 'bg-blue-500 w-4'
                : 'bg-slate-600 hover:bg-slate-500'
            }`}
          />
        ))}
        {items.length > 10 && (
          <span className="text-xs text-slate-500 ml-1">+{items.length - 10}</span>
        )}
      </div>
    </div>
  );
}
