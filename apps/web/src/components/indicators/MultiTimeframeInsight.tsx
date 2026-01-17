/**
 * Multi-Timeframe AI Insight Component
 * Shows AI analysis across different trading timeframes: Scalp, Intraday, Swing, Long-term
 */
import { useState, useEffect } from 'react';
import {
  Zap,
  Clock,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  Activity,
  RefreshCw,
  Loader2,
  Info,
  AlertTriangle,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface TimeframeAnalysis {
  timeframe: string;
  label: string;
  recommendation: string;
  confidence: number;
  signals: string[];
  concerns: string[];
  key_levels?: {
    entry?: number;
    target?: number;
    stop?: number;
  };
}

interface ElliottWaveAnalysis {
  wave_count: number;
  wave_type: string;
  current_wave?: string;
  current_position?: string;  // API returns this instead of current_wave
  direction: string;
  confidence: number;
  description: string;
  next_target?: number;
  swings_detected?: number;
  fib_targets?: {
    extension_1618?: number;
    retracement_382?: number;
    retracement_618?: number;
  };
}

interface MultiTimeframeData {
  symbol: string;
  current_price: number;
  overall_recommendation: string;
  overall_score: number;
  timeframes: {
    scalp: TimeframeAnalysis;
    intraday: TimeframeAnalysis;
    swing: TimeframeAnalysis;
    longterm: TimeframeAnalysis;
  };
  elliott_wave?: ElliottWaveAnalysis;
  indicators: {
    rsi_daily: number;
    rsi_hourly: number;
    rsi_15min: number;
    macd_histogram: number;
    sma_20: number;
    sma_50: number;
    sma_200: number;
    ema_12: number;
    ema_26: number;
    bb_upper: number;
    bb_lower: number;
    atr_14: number;
    volume_ratio: number;
  };
  timestamp: string;
}

interface MultiTimeframeInsightProps {
  symbol: string;
  compact?: boolean;
}

const TIMEFRAME_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  SCALP: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
  INTRADAY: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
  SWING: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
  'LONG-TERM': { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
};

const getRecommendationStyle = (rec: string) => {
  switch (rec) {
    case 'STRONG BUY':
      return 'bg-green-600 text-white';
    case 'BUY':
      return 'bg-green-500/80 text-white';
    case 'HOLD':
      return 'bg-yellow-500/80 text-black';
    case 'SELL':
      return 'bg-red-500/80 text-white';
    case 'STRONG SELL':
      return 'bg-red-600 text-white';
    default:
      return 'bg-slate-600 text-white';
  }
};

export default function MultiTimeframeInsight({ symbol, compact = false }: MultiTimeframeInsightProps) {
  const [data, setData] = useState<MultiTimeframeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTimeframe, setExpandedTimeframe] = useState<string | null>(null);
  const [showElliottWave, setShowElliottWave] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/analysis/ai-insight-multi/${symbol}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Multi-timeframe fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch analysis');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (symbol) {
      fetchData();
    }
  }, [symbol]);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg p-4 border border-blue-700/30">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
          <span className="ml-2 text-sm text-slate-400">Analyzing timeframes...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <AlertTriangle className="h-5 w-5" />
          <span className="text-sm">Unable to load multi-timeframe analysis</span>
        </div>
        <button
          onClick={fetchData}
          className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
        >
          <RefreshCw className="h-3 w-3" /> Try again
        </button>
      </div>
    );
  }

  const timeframes = [
    { key: 'scalp', data: data.timeframes.scalp },
    { key: 'intraday', data: data.timeframes.intraday },
    { key: 'swing', data: data.timeframes.swing },
    { key: 'longterm', data: data.timeframes.longterm },
  ];

  return (
    <div className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 rounded-lg border border-blue-700/30 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-400" />
            <h2 className="text-lg font-semibold">Multi-Timeframe AI Insight</h2>
          </div>
          <button
            onClick={fetchData}
            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
            title="Refresh analysis"
          >
            <RefreshCw className={`h-4 w-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Overall Score */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-sm font-bold px-3 py-1 rounded ${getRecommendationStyle(data.overall_recommendation)}`}>
              {data.overall_recommendation}
            </span>
            <span className="text-sm text-slate-400">@ ${data.current_price.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Score</span>
            <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  data.overall_score >= 70 ? 'bg-green-500' :
                  data.overall_score >= 50 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${data.overall_score}%` }}
              />
            </div>
            <span className="text-xs font-medium">{data.overall_score}</span>
          </div>
        </div>
      </div>

      {/* Timeframe Grid */}
      <div className={`p-4 ${compact ? 'space-y-2' : 'grid grid-cols-2 gap-3'}`}>
        {timeframes.map(({ key, data: tf }) => {
          const colors = TIMEFRAME_COLORS[tf.timeframe] || TIMEFRAME_COLORS['SWING'];
          const isExpanded = expandedTimeframe === key;

          return (
            <div
              key={key}
              className={`rounded-lg border transition-all ${colors.bg} ${colors.border} ${
                isExpanded ? 'col-span-2' : ''
              }`}
            >
              {/* Timeframe Header */}
              <button
                onClick={() => setExpandedTimeframe(isExpanded ? null : key)}
                className="w-full p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Clock className={`h-4 w-4 ${colors.text}`} />
                  <div className="text-left">
                    <span className={`text-sm font-medium ${colors.text}`}>{tf.label}</span>
                    <span className="text-xs text-slate-500 ml-2">({tf.timeframe})</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${getRecommendationStyle(tf.recommendation)}`}>
                    {tf.recommendation}
                  </span>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-3 pb-3 space-y-3 border-t border-slate-700/30">
                  {/* Confidence */}
                  <div className="pt-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Confidence</span>
                      <span className={colors.text}>{tf.confidence}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          tf.confidence >= 70 ? 'bg-green-500' :
                          tf.confidence >= 50 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${tf.confidence}%` }}
                      />
                    </div>
                  </div>

                  {/* Signals */}
                  {tf.signals.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Bullish Signals</p>
                      <div className="space-y-1">
                        {tf.signals.map((signal, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            <TrendingUp className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                            <span className="text-green-400">{signal}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Concerns */}
                  {tf.concerns.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Concerns</p>
                      <div className="space-y-1">
                        {tf.concerns.map((concern, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            <TrendingDown className="h-3 w-3 text-red-500 mt-0.5 flex-shrink-0" />
                            <span className="text-red-400">{concern}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Levels */}
                  {tf.key_levels && (
                    <div className="pt-2 border-t border-slate-700/30">
                      <p className="text-xs text-slate-400 mb-2">Key Levels</p>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        {tf.key_levels.entry && (
                          <div className="bg-slate-700/50 rounded p-2 text-center">
                            <span className="text-slate-500 block">Entry</span>
                            <span className="text-blue-400 font-medium">${tf.key_levels.entry.toFixed(2)}</span>
                          </div>
                        )}
                        {tf.key_levels.target && (
                          <div className="bg-slate-700/50 rounded p-2 text-center">
                            <span className="text-slate-500 block">Target</span>
                            <span className="text-green-400 font-medium">${tf.key_levels.target.toFixed(2)}</span>
                          </div>
                        )}
                        {tf.key_levels.stop && (
                          <div className="bg-slate-700/50 rounded p-2 text-center">
                            <span className="text-slate-500 block">Stop</span>
                            <span className="text-red-400 font-medium">${tf.key_levels.stop.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Elliott Wave Section */}
      {data.elliott_wave && (
        <div className="border-t border-slate-700/50">
          <button
            onClick={() => setShowElliottWave(!showElliottWave)}
            className="w-full p-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-400" />
              <span className="text-sm font-medium">Elliott Wave Analysis</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                data.elliott_wave.direction === 'bullish' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
              }`}>
                {data.elliott_wave.wave_type} ({data.elliott_wave.direction})
              </span>
            </div>
            {showElliottWave ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </button>

          {showElliottWave && (
            <div className="px-4 pb-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">Current Position</p>
                  <p className="text-lg font-semibold text-purple-400">{data.elliott_wave.current_wave || data.elliott_wave.current_position}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">Wave Count</p>
                  <p className="text-lg font-semibold">{data.elliott_wave.wave_count}</p>
                </div>
              </div>

              {/* Next Target */}
              {data.elliott_wave.next_target && (
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">Next Target</p>
                  <p className="text-lg font-semibold text-blue-400">${data.elliott_wave.next_target.toFixed(2)}</p>
                </div>
              )}

              <div className="bg-slate-800/50 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-1">Analysis</p>
                <p className="text-sm text-slate-300">{data.elliott_wave.description}</p>
              </div>

              {/* Fibonacci Targets - only show if fib_targets exists and has values */}
              {data.elliott_wave.fib_targets && Object.keys(data.elliott_wave.fib_targets).length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-2">Fibonacci Targets</p>
                  <div className="grid grid-cols-3 gap-2">
                    {data.elliott_wave.fib_targets.extension_1618 && (
                      <div className="bg-purple-900/30 rounded p-2 text-center">
                        <span className="text-xs text-slate-500 block">1.618 Ext</span>
                        <span className="text-purple-400 text-sm font-medium">
                          ${data.elliott_wave.fib_targets.extension_1618.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {data.elliott_wave.fib_targets.retracement_382 && (
                      <div className="bg-blue-900/30 rounded p-2 text-center">
                        <span className="text-xs text-slate-500 block">38.2% Ret</span>
                        <span className="text-blue-400 text-sm font-medium">
                          ${data.elliott_wave.fib_targets.retracement_382.toFixed(2)}
                        </span>
                      </div>
                    )}
                    {data.elliott_wave.fib_targets.retracement_618 && (
                      <div className="bg-cyan-900/30 rounded p-2 text-center">
                        <span className="text-xs text-slate-500 block">61.8% Ret</span>
                        <span className="text-cyan-400 text-sm font-medium">
                          ${data.elliott_wave.fib_targets.retracement_618.toFixed(2)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Confidence */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-400">Pattern Confidence</span>
                  <span className="text-purple-400">{data.elliott_wave.confidence}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500"
                    style={{ width: `${data.elliott_wave.confidence}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Key Indicators Summary */}
      {!compact && (
        <div className="p-4 border-t border-slate-700/50">
          <div className="flex items-center gap-2 mb-3">
            <Info className="h-4 w-4 text-slate-400" />
            <span className="text-xs text-slate-400">Multi-Timeframe RSI</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <span className="text-slate-500 block">15m RSI</span>
              <span className={`font-medium ${
                data.indicators.rsi_15min > 70 ? 'text-red-400' :
                data.indicators.rsi_15min < 30 ? 'text-green-400' :
                'text-slate-300'
              }`}>
                {data.indicators.rsi_15min?.toFixed(1) || 'N/A'}
              </span>
            </div>
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <span className="text-slate-500 block">1H RSI</span>
              <span className={`font-medium ${
                data.indicators.rsi_hourly > 70 ? 'text-red-400' :
                data.indicators.rsi_hourly < 30 ? 'text-green-400' :
                'text-slate-300'
              }`}>
                {data.indicators.rsi_hourly?.toFixed(1) || 'N/A'}
              </span>
            </div>
            <div className="bg-slate-800/50 rounded p-2 text-center">
              <span className="text-slate-500 block">Daily RSI</span>
              <span className={`font-medium ${
                data.indicators.rsi_daily > 70 ? 'text-red-400' :
                data.indicators.rsi_daily < 30 ? 'text-green-400' :
                'text-slate-300'
              }`}>
                {data.indicators.rsi_daily?.toFixed(1) || 'N/A'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Timestamp */}
      <div className="px-4 pb-3">
        <p className="text-xs text-slate-500 text-right">
          Updated: {new Date(data.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
