/**
 * Triple Screen Panel - Alexander Elder's Triple Screen Trading System
 *
 * Displays three-tier analysis:
 * - Screen 1 (Tide): Daily trend direction
 * - Screen 2 (Wave): Hourly pullback identification
 * - Screen 3 (Ripple): 5-minute entry timing
 */
import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Waves,
  Droplet,
  Target,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ScreenData {
  timeframe: string;
  direction?: string;
  entry_ready?: boolean;
  entry_triggered?: boolean;
  strength?: number;
  signals: string[];
  concerns: string[];
  indicators: Record<string, number>;
}

interface TripleScreenData {
  symbol: string;
  current_price: number;
  timestamp: string;
  trade_action: string;
  alignment_score: number;
  trade_rationale: string;
  screens: {
    screen_1_tide: ScreenData;
    screen_2_wave: ScreenData;
    screen_3_ripple: ScreenData;
  };
  methodology: {
    name: string;
    description: string;
    best_for: string[];
  };
}

interface TripleScreenPanelProps {
  symbol: string;
}

const getActionColor = (action: string) => {
  switch (action) {
    case 'STRONG BUY':
      return 'bg-green-600 text-white';
    case 'BUY':
      return 'bg-green-500 text-white';
    case 'STRONG SHORT':
      return 'bg-red-600 text-white';
    case 'SHORT':
      return 'bg-red-500 text-white';
    case 'WAIT':
      return 'bg-yellow-500 text-black';
    default:
      return 'bg-slate-600 text-white';
  }
};

const getDirectionIcon = (direction: string) => {
  if (direction === 'BULLISH') return <TrendingUp className="h-5 w-5 text-green-500" />;
  if (direction === 'BEARISH') return <TrendingDown className="h-5 w-5 text-red-500" />;
  return <Minus className="h-5 w-5 text-slate-400" />;
};

export default function TripleScreenPanel({ symbol }: TripleScreenPanelProps) {
  const [data, setData] = useState<TripleScreenData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedScreen, setExpandedScreen] = useState<string | null>('screen_1_tide');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/analysis/triple-screen/${symbol}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Triple screen fetch error:', err);
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
      <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 rounded-lg p-4 border border-indigo-700/30">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
          <span className="ml-2 text-sm text-slate-400">Running Triple Screen Analysis...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <AlertTriangle className="h-5 w-5" />
          <span className="text-sm">Unable to load Triple Screen analysis</span>
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

  return (
    <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 rounded-lg border border-indigo-700/30 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Waves className="h-5 w-5 text-indigo-400" />
            <h2 className="text-lg font-semibold">Triple Screen System</h2>
          </div>
          <button
            onClick={fetchData}
            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
            title="Refresh analysis"
          >
            <RefreshCw className={`h-4 w-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Trade Action Badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-sm font-bold px-3 py-1.5 rounded ${getActionColor(data.trade_action)}`}>
              {data.trade_action}
            </span>
            <span className="text-sm text-slate-400">@ ${data.current_price.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Alignment</span>
            <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  data.alignment_score >= 70 ? 'bg-green-500' :
                  data.alignment_score >= 50 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${data.alignment_score}%` }}
              />
            </div>
            <span className="text-xs font-medium">{data.alignment_score}%</span>
          </div>
        </div>

        {/* Trade Rationale */}
        <p className="text-sm text-slate-300 mt-3 bg-slate-800/50 rounded p-2">
          {data.trade_rationale}
        </p>
      </div>

      {/* Three Screens */}
      <div className="p-4 space-y-3">
        {/* Screen 1: The Tide */}
        <div
          className={`rounded-lg border transition-all ${
            data.screens.screen_1_tide.direction === 'BULLISH'
              ? 'bg-green-500/10 border-green-500/30'
              : data.screens.screen_1_tide.direction === 'BEARISH'
              ? 'bg-red-500/10 border-red-500/30'
              : 'bg-slate-800 border-slate-700'
          }`}
        >
          <button
            onClick={() => setExpandedScreen(expandedScreen === 'screen_1_tide' ? null : 'screen_1_tide')}
            className="w-full p-3 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-900/50 rounded-lg">
                <Waves className="h-5 w-5 text-blue-400" />
              </div>
              <div className="text-left">
                <span className="text-sm font-medium">Screen 1: The Tide</span>
                <p className="text-xs text-slate-500">{data.screens.screen_1_tide.timeframe}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {getDirectionIcon(data.screens.screen_1_tide.direction || 'NEUTRAL')}
              <span className={`text-sm font-semibold ${
                data.screens.screen_1_tide.direction === 'BULLISH' ? 'text-green-400' :
                data.screens.screen_1_tide.direction === 'BEARISH' ? 'text-red-400' :
                'text-slate-400'
              }`}>
                {data.screens.screen_1_tide.direction}
              </span>
              {expandedScreen === 'screen_1_tide' ? (
                <ChevronUp className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              )}
            </div>
          </button>

          {expandedScreen === 'screen_1_tide' && (
            <div className="px-3 pb-3 space-y-3 border-t border-slate-700/30">
              {/* Strength */}
              <div className="pt-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-400">Trend Strength</span>
                  <span className="text-blue-400">{data.screens.screen_1_tide.strength?.toFixed(0)}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${data.screens.screen_1_tide.strength || 50}%` }}
                  />
                </div>
              </div>

              {/* Signals */}
              {data.screens.screen_1_tide.signals.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-1">Bullish Signals</p>
                  <div className="space-y-1">
                    {data.screens.screen_1_tide.signals.map((signal, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                        <span className="text-green-400">{signal}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Concerns */}
              {data.screens.screen_1_tide.concerns.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-1">Bearish Signals</p>
                  <div className="space-y-1">
                    {data.screens.screen_1_tide.concerns.map((concern, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-red-500 mt-0.5 flex-shrink-0" />
                        <span className="text-red-400">{concern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Key Indicators */}
              <div className="pt-2 border-t border-slate-700/30">
                <p className="text-xs text-slate-400 mb-2">Key Indicators</p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">ADX</span>
                    <span className={`font-medium ${
                      data.screens.screen_1_tide.indicators.adx > 25 ? 'text-blue-400' : 'text-slate-400'
                    }`}>
                      {data.screens.screen_1_tide.indicators.adx}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">+DI</span>
                    <span className="text-green-400 font-medium">
                      {data.screens.screen_1_tide.indicators.plus_di}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">-DI</span>
                    <span className="text-red-400 font-medium">
                      {data.screens.screen_1_tide.indicators.minus_di}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Screen 2: The Wave */}
        <div
          className={`rounded-lg border transition-all ${
            data.screens.screen_2_wave.entry_ready
              ? 'bg-green-500/10 border-green-500/30'
              : 'bg-yellow-500/10 border-yellow-500/30'
          }`}
        >
          <button
            onClick={() => setExpandedScreen(expandedScreen === 'screen_2_wave' ? null : 'screen_2_wave')}
            className="w-full p-3 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-900/50 rounded-lg">
                <Droplet className="h-5 w-5 text-cyan-400" />
              </div>
              <div className="text-left">
                <span className="text-sm font-medium">Screen 2: The Wave</span>
                <p className="text-xs text-slate-500">{data.screens.screen_2_wave.timeframe}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {data.screens.screen_2_wave.entry_ready ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              )}
              <span className={`text-sm font-semibold ${
                data.screens.screen_2_wave.entry_ready ? 'text-green-400' : 'text-yellow-400'
              }`}>
                {data.screens.screen_2_wave.entry_ready ? 'Ready' : 'Waiting'}
              </span>
              {expandedScreen === 'screen_2_wave' ? (
                <ChevronUp className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              )}
            </div>
          </button>

          {expandedScreen === 'screen_2_wave' && (
            <div className="px-3 pb-3 space-y-3 border-t border-slate-700/30">
              {/* Signals */}
              {data.screens.screen_2_wave.signals.length > 0 && (
                <div className="pt-3">
                  <p className="text-xs text-slate-400 mb-1">Wave Signals</p>
                  <div className="space-y-1">
                    {data.screens.screen_2_wave.signals.map((signal, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                        <span className="text-green-400">{signal}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Concerns */}
              {data.screens.screen_2_wave.concerns.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-1">Concerns</p>
                  <div className="space-y-1">
                    {data.screens.screen_2_wave.concerns.map((concern, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-yellow-500 mt-0.5 flex-shrink-0" />
                        <span className="text-yellow-400">{concern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Indicators */}
              <div className="pt-2 border-t border-slate-700/30">
                <p className="text-xs text-slate-400 mb-2">Oscillators</p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">RSI (1H)</span>
                    <span className={`font-medium ${
                      data.screens.screen_2_wave.indicators.rsi_hourly < 30 ? 'text-green-400' :
                      data.screens.screen_2_wave.indicators.rsi_hourly > 70 ? 'text-red-400' :
                      'text-slate-300'
                    }`}>
                      {data.screens.screen_2_wave.indicators.rsi_hourly}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">Stoch %K</span>
                    <span className="text-cyan-400 font-medium">
                      {data.screens.screen_2_wave.indicators.stochastic_k}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">Stoch %D</span>
                    <span className="text-cyan-400 font-medium">
                      {data.screens.screen_2_wave.indicators.stochastic_d}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Screen 3: The Ripple */}
        <div
          className={`rounded-lg border transition-all ${
            data.screens.screen_3_ripple.entry_triggered
              ? 'bg-green-500/10 border-green-500/30'
              : 'bg-slate-800 border-slate-700'
          }`}
        >
          <button
            onClick={() => setExpandedScreen(expandedScreen === 'screen_3_ripple' ? null : 'screen_3_ripple')}
            className="w-full p-3 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-900/50 rounded-lg">
                <Target className="h-5 w-5 text-purple-400" />
              </div>
              <div className="text-left">
                <span className="text-sm font-medium">Screen 3: The Ripple</span>
                <p className="text-xs text-slate-500">{data.screens.screen_3_ripple.timeframe}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {data.screens.screen_3_ripple.entry_triggered ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <Minus className="h-5 w-5 text-slate-400" />
              )}
              <span className={`text-sm font-semibold ${
                data.screens.screen_3_ripple.entry_triggered ? 'text-green-400' : 'text-slate-400'
              }`}>
                {data.screens.screen_3_ripple.entry_triggered ? 'Triggered' : 'Monitoring'}
              </span>
              {expandedScreen === 'screen_3_ripple' ? (
                <ChevronUp className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              )}
            </div>
          </button>

          {expandedScreen === 'screen_3_ripple' && (
            <div className="px-3 pb-3 space-y-3 border-t border-slate-700/30">
              {/* Signals */}
              {data.screens.screen_3_ripple.signals.length > 0 && (
                <div className="pt-3">
                  <p className="text-xs text-slate-400 mb-1">Entry Signals</p>
                  <div className="space-y-1">
                    {data.screens.screen_3_ripple.signals.map((signal, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                        <span className="text-green-400">{signal}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Concerns */}
              {data.screens.screen_3_ripple.concerns.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 mb-1">Concerns</p>
                  <div className="space-y-1">
                    {data.screens.screen_3_ripple.concerns.map((concern, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-slate-500 mt-0.5 flex-shrink-0" />
                        <span className="text-slate-400">{concern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Indicators */}
              <div className="pt-2 border-t border-slate-700/30">
                <p className="text-xs text-slate-400 mb-2">Entry Indicators</p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">RSI (5m)</span>
                    <span className={`font-medium ${
                      data.screens.screen_3_ripple.indicators.rsi_5min < 35 ? 'text-green-400' :
                      data.screens.screen_3_ripple.indicators.rsi_5min > 65 ? 'text-red-400' :
                      'text-slate-300'
                    }`}>
                      {data.screens.screen_3_ripple.indicators.rsi_5min}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">VWAP</span>
                    <span className="text-purple-400 font-medium">
                      ${data.screens.screen_3_ripple.indicators.vwap}
                    </span>
                  </div>
                  <div className="bg-slate-700/50 rounded p-2 text-center">
                    <span className="text-slate-500 block">vs VWAP</span>
                    <span className={`font-medium ${
                      data.screens.screen_3_ripple.indicators.price_vs_vwap_pct < 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {data.screens.screen_3_ripple.indicators.price_vs_vwap_pct > 0 ? '+' : ''}
                      {data.screens.screen_3_ripple.indicators.price_vs_vwap_pct}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Methodology Info */}
      <div className="p-4 border-t border-slate-700/50 bg-slate-800/30">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-indigo-400 mt-0.5" />
          <div>
            <p className="text-xs text-slate-400">{data.methodology.name}</p>
            <p className="text-xs text-slate-500 mt-1">{data.methodology.description}</p>
          </div>
        </div>
      </div>

      {/* Timestamp */}
      <div className="px-4 pb-3">
        <p className="text-xs text-slate-500 text-right">
          Updated: {new Date(data.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
