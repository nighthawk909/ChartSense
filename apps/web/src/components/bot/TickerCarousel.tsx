/**
 * Ticker Carousel Component - Enhanced Version
 * Multi-card grid navigation with sparklines, priority ranking, and keyboard controls
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Brain,
  Clock,
  Zap,
  Play,
  Pause,
  ArrowUpRight,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import type { CryptoAnalysisResult, StockAnalysisResult, AIDecision, TimeHorizon } from '../../types/bot';

// Mini sparkline component
function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const height = 24;
  const width = 60;

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="opacity-60">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export interface TickerItem {
  symbol: string;
  price?: number;
  change24h?: number;
  analysis?: CryptoAnalysisResult | StockAnalysisResult;
  aiDecision?: AIDecision;
  sparklineData?: number[];
  assetType: 'crypto' | 'stock';
}

// Helper to extract key technical signals from indicators
function getTechnicalSummary(analysis?: CryptoAnalysisResult | StockAnalysisResult): string[] {
  if (!analysis) return [];

  const signals: string[] = [];
  const indicators = analysis.indicators || {};

  // RSI Status
  const rsi = indicators.rsi || indicators.rsi_14;
  if (rsi !== undefined) {
    if (rsi < 30) signals.push('RSI Oversold');
    else if (rsi > 70) signals.push('RSI Overbought');
    else if (rsi > 50) signals.push('RSI Bullish');
    else signals.push('RSI Bearish');
  }

  // MACD Status
  const macdHist = indicators.macd_histogram;
  if (macdHist !== undefined) {
    if (macdHist > 0) signals.push('MACD+');
    else signals.push('MACD-');
  }

  // Golden/Death Cross
  if (indicators.golden_cross) signals.push('Golden Cross');
  if (indicators.death_cross) signals.push('Death Cross');

  // INTRADAY SIGNALS - VWAP, Volume Spikes, Breakouts
  // VWAP position
  const vwap = indicators.vwap;
  const price = indicators.current_price || indicators.close;
  if (vwap && price) {
    if (price > vwap * 1.01) signals.push('Above VWAP');
    else if (price < vwap * 0.99) signals.push('Below VWAP');
  }

  // Volume spike detection
  const volRatio = indicators.volume_ratio;
  if (volRatio !== undefined) {
    if (volRatio > 2.0) signals.push('Vol Spike 🚀');
    else if (volRatio > 1.5) signals.push('High Vol');
    else if (volRatio < 0.5) signals.push('Low Vol');
  }

  // Bollinger Band breakout
  const bbUpper = indicators.bb_upper;
  const bbLower = indicators.bb_lower;
  if (bbUpper && bbLower && price) {
    if (price > bbUpper) signals.push('BB Breakout ↑');
    else if (price < bbLower) signals.push('BB Breakdown ↓');
  }

  // ADX trend strength (intraday momentum)
  const adx = indicators.adx;
  if (adx !== undefined) {
    if (adx > 40) signals.push('Strong Trend');
    else if (adx > 25) signals.push('Trending');
  }

  // Stochastic oversold/overbought (intraday reversal)
  const stochK = indicators.stoch_k || indicators.stochastic_k;
  if (stochK !== undefined) {
    if (stochK < 20) signals.push('Stoch Oversold');
    else if (stochK > 80) signals.push('Stoch Overbought');
  }

  // Use signals array if available (from crypto analysis)
  const analysisSignals = (analysis as { signals?: string[] }).signals;
  if (analysisSignals && analysisSignals.length > 0) {
    // Pick the first 2 most relevant signals
    const relevantSignals = analysisSignals
      .filter((s: string) => !s.includes('Low volume'))
      .slice(0, 2)
      .map((s: string) => {
        if (s.includes('bullish')) return 'Bullish';
        if (s.includes('bearish')) return 'Bearish';
        if (s.includes('uptrend')) return 'Uptrend';
        if (s.includes('overbought')) return 'Overbought';
        if (s.includes('oversold')) return 'Oversold';
        return s.split(' ')[0]; // First word
      });
    if (relevantSignals.length > 0 && signals.length < 4) {
      signals.push(...relevantSignals.slice(0, 4 - signals.length));
    }
  }

  return signals.slice(0, 4); // Max 4 indicators for intraday
}

interface TickerCarouselProps {
  items: TickerItem[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onTickerClick?: (symbol: string, assetType: 'crypto' | 'stock') => void;
  cardsPerView?: number;
  autoAdvance?: boolean;
  autoAdvanceInterval?: number;
}

export default function TickerCarousel({
  items,
  currentIndex,
  onIndexChange,
  onTickerClick,
  cardsPerView = 4,
  autoAdvance: initialAutoAdvance = false,
  autoAdvanceInterval = 5000,
}: TickerCarouselProps) {
  const navigate = useNavigate();
  const [isAnimating, setIsAnimating] = useState(false);
  const [autoAdvance, setAutoAdvance] = useState(initialAutoAdvance);
  const containerRef = useRef<HTMLDivElement>(null);
  const autoAdvanceRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sort items by confidence (highest first) - memoized
  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const confA = a.analysis?.confidence ?? 0;
      const confB = b.analysis?.confidence ?? 0;
      return confB - confA;
    });
  }, [items]);

  // Calculate pagination values
  const totalPages = Math.max(1, Math.ceil(sortedItems.length / cardsPerView));
  const currentPage = Math.floor(currentIndex / cardsPerView);
  const visibleItems = sortedItems.slice(
    currentPage * cardsPerView,
    (currentPage + 1) * cardsPerView
  );

  // Navigation handlers - ALL HOOKS MUST BE BEFORE ANY CONDITIONAL RETURNS
  const handlePrev = useCallback(() => {
    if (isAnimating || totalPages <= 1) return;
    setIsAnimating(true);
    const newPage = currentPage === 0 ? totalPages - 1 : currentPage - 1;
    onIndexChange(newPage * cardsPerView);
    setTimeout(() => setIsAnimating(false), 300);
  }, [isAnimating, currentPage, totalPages, cardsPerView, onIndexChange]);

  const handleNext = useCallback(() => {
    if (isAnimating || totalPages <= 1) return;
    setIsAnimating(true);
    const newPage = currentPage === totalPages - 1 ? 0 : currentPage + 1;
    onIndexChange(newPage * cardsPerView);
    setTimeout(() => setIsAnimating(false), 300);
  }, [isAnimating, currentPage, totalPages, cardsPerView, onIndexChange]);

  const handleCardClick = useCallback((item: TickerItem) => {
    if (onTickerClick) {
      onTickerClick(item.symbol, item.assetType);
    } else {
      // Default navigation - crypto goes to /crypto page, stocks go to /stock/:symbol
      if (item.assetType === 'crypto') {
        navigate('/crypto');
      } else {
        navigate(`/stock/${item.symbol}`);
      }
    }
  }, [onTickerClick, navigate]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if not in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePrev, handleNext]);

  // Auto-advance
  useEffect(() => {
    if (autoAdvance && totalPages > 1 && items.length > 0) {
      autoAdvanceRef.current = setInterval(() => {
        handleNext();
      }, autoAdvanceInterval);
    }

    return () => {
      if (autoAdvanceRef.current) {
        clearInterval(autoAdvanceRef.current);
      }
    };
  }, [autoAdvance, handleNext, autoAdvanceInterval, totalPages, items.length]);

  // Helper functions for rendering
  // Updated to show more accurate labels based on AI decision
  const getSignalBadge = (signal?: string, meetsThreshold?: boolean, aiDecision?: AIDecision) => {
    const baseClasses = "px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide";

    // If AI has made a decision, use that instead of simple threshold
    if (aiDecision) {
      if (aiDecision.decision === 'APPROVE') {
        return (
          <span className={`${baseClasses} bg-green-500/20 text-green-400 border border-green-500/30`}>
            <TrendingUp className="w-3 h-3 inline mr-1" />
            AI Approved
          </span>
        );
      }
      if (aiDecision.decision === 'WAIT') {
        return (
          <span className={`${baseClasses} bg-yellow-500/20 text-yellow-400 border border-yellow-500/30`}>
            <Clock className="w-3 h-3 inline mr-1" />
            Wait
          </span>
        );
      }
      if (aiDecision.decision === 'REJECT') {
        return (
          <span className={`${baseClasses} bg-red-500/20 text-red-400 border border-red-500/30`}>
            <AlertTriangle className="w-3 h-3 inline mr-1" />
            AI Rejected
          </span>
        );
      }
    }

    // Fallback to threshold-based if no AI decision
    // These are just TECHNICAL signals - not guaranteed buys
    if (signal === 'STRONG_BUY' || (signal === 'BUY' && meetsThreshold)) {
      return (
        <span className={`${baseClasses} bg-blue-500/20 text-blue-400 border border-blue-500/30`}>
          <TrendingUp className="w-3 h-3 inline mr-1" />
          Tech Signal
        </span>
      );
    }
    if (signal === 'BUY') {
      return (
        <span className={`${baseClasses} bg-blue-500/20 text-blue-300 border border-blue-500/30`}>
          <TrendingUp className="w-3 h-3 inline mr-1" />
          Weak Signal
        </span>
      );
    }
    if (signal === 'STRONG_SELL' || signal === 'SELL') {
      return (
        <span className={`${baseClasses} bg-red-500/20 text-red-400 border border-red-500/30`}>
          <TrendingDown className="w-3 h-3 inline mr-1" />
          {signal === 'STRONG_SELL' ? 'Strong Sell' : 'Sell'}
        </span>
      );
    }
    return (
      <span className={`${baseClasses} bg-slate-500/20 text-slate-400 border border-slate-500/30`}>
        <Minus className="w-3 h-3 inline mr-1" />
        Hold
      </span>
    );
  };

  const getHorizonBadge = (horizon?: TimeHorizon) => {
    const baseClasses = "px-1.5 py-0.5 text-[10px] font-medium rounded uppercase";
    switch (horizon) {
      case 'SCALP':
        return <span className={`${baseClasses} bg-red-500/20 text-red-400`}>Scalp</span>;
      case 'INTRADAY':
        return <span className={`${baseClasses} bg-orange-500/20 text-orange-400`}>Intraday</span>;
      case 'SWING':
        return <span className={`${baseClasses} bg-blue-500/20 text-blue-400`}>Swing</span>;
      default:
        return null;
    }
  };

  const getConfidenceColor = (confidence: number, threshold: number) => {
    if (confidence >= threshold) return 'text-green-400';
    if (confidence >= threshold - 10) return 'text-yellow-400';
    return 'text-slate-400';
  };

  const getConfidenceBarColor = (confidence: number, threshold: number) => {
    if (confidence >= threshold) return 'bg-green-500';
    if (confidence >= threshold - 10) return 'bg-yellow-500';
    return 'bg-slate-500';
  };

  // Empty state - AFTER all hooks
  if (items.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 sm:p-6 text-center">
        <Activity className="w-6 h-6 sm:w-8 sm:h-8 text-slate-500 mx-auto mb-2" />
        <p className="text-slate-400 text-sm sm:text-base">No signals detected yet</p>
        <p className="text-slate-500 text-xs sm:text-sm mt-1">Scanner is analyzing symbols...</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-3 sm:p-4" ref={containerRef}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 sm:mb-4">
        <div className="flex items-center gap-2 sm:gap-3">
          <h3 className="text-xs sm:text-sm font-semibold text-white flex items-center gap-1.5 sm:gap-2">
            <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-yellow-400" />
            <span className="hidden xs:inline">Quick Navigation</span>
            <span className="xs:hidden">Signals</span>
          </h3>
          <span className="text-[10px] sm:text-xs text-slate-500 bg-slate-700 px-1.5 sm:px-2 py-0.5 rounded">
            {sortedItems.length}
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Auto-advance toggle */}
          <button
            onClick={() => setAutoAdvance(!autoAdvance)}
            className={`p-1 sm:p-1.5 rounded transition-colors ${
              autoAdvance
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
            title={autoAdvance ? 'Pause auto-advance' : 'Start auto-advance'}
          >
            {autoAdvance ? <Pause className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> : <Play className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
          </button>

          {/* Page indicator */}
          <span className="text-[10px] sm:text-xs text-slate-500">
            {currentPage + 1}/{totalPages}
          </span>

          {/* Keyboard hint */}
          <span className="hidden sm:flex text-xs text-slate-600 gap-1">
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">←</kbd>
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">→</kbd>
          </span>
        </div>
      </div>

      {/* Carousel Container */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Previous Button */}
        <button
          onClick={handlePrev}
          disabled={isAnimating || totalPages <= 1}
          className="flex-shrink-0 p-1.5 sm:p-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors
                   disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </button>

        {/* Cards Grid */}
        <div
          className={`flex-1 grid gap-2 sm:gap-3 transition-opacity duration-300 ${
            isAnimating ? 'opacity-50' : 'opacity-100'
          }`}
          style={{
            gridTemplateColumns: `repeat(${Math.min(cardsPerView, visibleItems.length || 1)}, minmax(0, 1fr))`
          }}
        >
          {visibleItems.map((item, idx) => {
            const globalIdx = currentPage * cardsPerView + idx;
            const isSelected = globalIdx === currentIndex;
            const confidence = item.analysis?.confidence ?? 0;
            const threshold = item.analysis?.threshold ?? 65;

            return (
              <div
                key={item.symbol}
                onClick={() => handleCardClick(item)}
                className={`relative bg-slate-700/50 rounded-lg p-2 sm:p-3 cursor-pointer transition-all
                          hover:bg-slate-700 hover:scale-[1.02] group
                          ${isSelected ? 'ring-2 ring-blue-500 bg-slate-700' : ''}`}
              >
                {/* Rank badge */}
                <div className="absolute -top-1 -left-1 sm:-top-1.5 sm:-left-1.5 w-4 h-4 sm:w-5 sm:h-5 bg-slate-600 rounded-full
                              flex items-center justify-center text-[8px] sm:text-[10px] font-bold text-slate-300">
                  {globalIdx + 1}
                </div>

                {/* Asset type badge - more visible */}
                <div className={`absolute top-1.5 right-1.5 sm:top-2 sm:right-2 px-1 sm:px-1.5 py-0.5 rounded text-[8px] sm:text-[9px] font-bold uppercase ${
                  item.assetType === 'crypto'
                    ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                    : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                }`}>
                  {item.assetType === 'crypto' ? '₿' : '📈'}
                  <span className="hidden sm:inline"> {item.assetType === 'crypto' ? 'Crypto' : 'Stock'}</span>
                </div>

                {/* Symbol & Price Row */}
                <div className="flex items-start justify-between mb-1.5 sm:mb-2 mt-1 sm:mt-0">
                  <div>
                    <div className="flex items-center gap-1 sm:gap-1.5">
                      <span className="text-sm sm:text-base font-bold text-white">
                        {item.symbol.replace('/', '').replace('USD', '')}
                      </span>
                      {item.aiDecision?.time_horizon && getHorizonBadge(item.aiDecision.time_horizon)}
                    </div>
                    {item.price !== undefined && (
                      <span className="text-xs sm:text-sm text-slate-300">
                        ${item.price.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: item.price < 1 ? 6 : 2
                        })}
                      </span>
                    )}
                  </div>

                  {/* Sparkline - hidden on mobile for space */}
                  {item.sparklineData && item.sparklineData.length > 1 && (
                    <div className="hidden sm:block">
                      <MiniSparkline
                        data={item.sparklineData}
                        color={(item.change24h ?? 0) >= 0 ? '#22c55e' : '#ef4444'}
                      />
                    </div>
                  )}
                </div>

                {/* 24h Change */}
                {item.change24h !== undefined && (
                  <div className={`text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2 ${
                    item.change24h >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {item.change24h >= 0 ? '+' : ''}{item.change24h.toFixed(2)}%
                    <span className="text-slate-500 text-[10px] sm:text-xs ml-1">24h</span>
                  </div>
                )}

                {/* Signal Badge */}
                <div className="mb-1.5 sm:mb-2">
                  {getSignalBadge(item.analysis?.signal, item.analysis?.meets_threshold, item.aiDecision)}
                </div>

                {/* Confidence Bar */}
                <div className="mb-1.5 sm:mb-2">
                  <div className="flex items-center justify-between text-[10px] sm:text-xs mb-0.5 sm:mb-1">
                    <span className={getConfidenceColor(confidence, threshold)}>
                      {confidence.toFixed(0)}%
                    </span>
                    <span className="text-slate-500">
                      /{threshold}%
                    </span>
                  </div>
                  <div className="h-1 sm:h-1.5 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${getConfidenceBarColor(confidence, threshold)}`}
                      style={{ width: `${Math.min(confidence, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Technical Indicators Summary - hidden on smallest screens */}
                {(() => {
                  const techSummary = getTechnicalSummary(item.analysis);
                  const indicators = item.analysis?.indicators || {};
                  const rsi = indicators.rsi || indicators.rsi_14;
                  const macdHist = indicators.macd_histogram;

                  return techSummary.length > 0 || rsi !== undefined ? (
                    <div className="mb-1.5 sm:mb-2 flex flex-wrap gap-0.5 sm:gap-1">
                      {/* RSI Badge */}
                      {rsi !== undefined && (
                        <span className={`px-1 sm:px-1.5 py-0.5 rounded text-[8px] sm:text-[9px] font-medium ${
                          rsi < 30 ? 'bg-green-500/20 text-green-400' :
                          rsi > 70 ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-600 text-slate-300'
                        }`}>
                          RSI {rsi.toFixed(0)}
                        </span>
                      )}
                      {/* MACD Badge - hidden on mobile for space */}
                      {macdHist !== undefined && (
                        <span className={`hidden sm:inline-block px-1.5 py-0.5 rounded text-[9px] font-medium ${
                          macdHist > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          MACD {macdHist > 0 ? '+' : ''}{macdHist.toFixed(2)}
                        </span>
                      )}
                      {/* Golden/Death Cross */}
                      {indicators.golden_cross && (
                        <span className="px-1 sm:px-1.5 py-0.5 rounded text-[8px] sm:text-[9px] font-medium bg-yellow-500/20 text-yellow-400">
                          Golden ✕
                        </span>
                      )}
                      {indicators.death_cross && (
                        <span className="px-1 sm:px-1.5 py-0.5 rounded text-[8px] sm:text-[9px] font-medium bg-red-500/20 text-red-400">
                          Death ✕
                        </span>
                      )}
                      {/* Volume - hidden on mobile */}
                      {indicators.volume_ratio !== undefined && indicators.volume_ratio > 1.5 && (
                        <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[9px] font-medium bg-blue-500/20 text-blue-400">
                          Vol {indicators.volume_ratio.toFixed(1)}x
                        </span>
                      )}
                    </div>
                  ) : null;
                })()}

                {/* AI Decision Preview - Shows why trade won't execute */}
                {item.aiDecision && (
                  <div className="flex items-center gap-1 sm:gap-1.5 pt-1.5 sm:pt-2 border-t border-slate-600">
                    <Brain className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-purple-400 flex-shrink-0" />
                    <span className={`text-[10px] sm:text-xs font-medium ${
                      item.aiDecision.decision === 'APPROVE' ? 'text-green-400' :
                      item.aiDecision.decision === 'WAIT' ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {item.aiDecision.decision}
                    </span>
                    {item.aiDecision.concerns && item.aiDecision.concerns.length > 0 && (
                      <span className="hidden sm:inline text-[9px] text-red-400/70 ml-auto truncate max-w-[80px]" title={item.aiDecision.concerns[0]}>
                        {item.aiDecision.concerns[0].slice(0, 20)}...
                      </span>
                    )}
                    {item.aiDecision.wait_for && (
                      <span className="hidden sm:flex text-[10px] text-slate-500 items-center gap-0.5 ml-auto">
                        <Clock className="w-2.5 h-2.5" />
                        {item.aiDecision.wait_for}
                      </span>
                    )}
                  </div>
                )}

                {/* Show status when signal is BUY but no AI decision yet - hidden on mobile */}
                {!item.aiDecision && item.analysis?.signal === 'BUY' && item.analysis?.meets_threshold && (
                  <div className="hidden sm:flex items-center gap-1.5 pt-2 border-t border-slate-600 text-[10px] text-yellow-400/80">
                    <Clock className="w-3 h-3" />
                    <span>Technical signal only - Enable Auto Trade for execution</span>
                  </div>
                )}

                {/* Hover arrow */}
                <ArrowUpRight className="absolute bottom-1.5 right-1.5 sm:bottom-2 sm:right-2 w-3 h-3 sm:w-4 sm:h-4 text-slate-500
                                        opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            );
          })}
        </div>

        {/* Next Button */}
        <button
          onClick={handleNext}
          disabled={isAnimating || totalPages <= 1}
          className="flex-shrink-0 p-1.5 sm:p-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors
                   disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </button>
      </div>

      {/* Page Dots */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-1 sm:gap-1.5 mt-3 sm:mt-4">
          {Array.from({ length: totalPages }).map((_, idx) => (
            <button
              key={idx}
              onClick={() => onIndexChange(idx * cardsPerView)}
              className={`transition-all rounded-full ${
                idx === currentPage
                  ? 'bg-blue-500 w-4 sm:w-6 h-1.5 sm:h-2'
                  : 'bg-slate-600 hover:bg-slate-500 w-1.5 sm:w-2 h-1.5 sm:h-2'
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
