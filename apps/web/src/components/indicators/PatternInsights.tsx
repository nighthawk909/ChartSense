/**
 * PatternInsights - Shows detected chart patterns for short-term trading
 *
 * Displays:
 * - Bull/Bear Flags
 * - Double Top/Bottom
 * - Triangles
 * - Breakouts
 * - Support/Resistance levels
 * - Trend lines
 * - Candlestick patterns
 */

import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Target,
  Activity,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Zap,
  Flag,
  Triangle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Pattern {
  pattern: string;
  confidence: number;
  direction: string;
  description: string;
  price_target?: number;
  target_pct?: number;
  stop_loss?: number;
  risk_pct?: number;
}

interface SupportResistance {
  price: number;
  strength: number;
}

interface TrendLine {
  type: string;
  direction: string;
  strength: number;
  current_value: number;
  touches: number;
}

interface ActiveBreakout {
  type: string;
  description: string;
  confidence: number;
  direction: string;
}

interface PatternData {
  symbol: string;
  current_price: number;
  interval: string;
  timestamp: string;
  trade_signal: string;
  signal_color: string;
  pattern_bias: string;
  bullish_score: number;
  bearish_score: number;
  active_breakout: ActiveBreakout | null;
  patterns_detected: number;
  patterns: Pattern[];
  actionable_patterns: Pattern[];
  support_levels: SupportResistance[];
  resistance_levels: SupportResistance[];
  nearest_support: number | null;
  nearest_resistance: number | null;
  trend_lines: TrendLine[];
  elliott_wave: any;
  summary: {
    signal: string;
    reason: string;
    confidence: number;
    entry: number | null;
    target: number | null;
    stop: number | null;
  };
}

interface PatternInsightsProps {
  symbol: string;
  interval?: string;
  compact?: boolean;
}

const getPatternIcon = (pattern: string) => {
  const patternLower = pattern.toLowerCase();
  if (patternLower.includes('flag')) return <Flag className="h-4 w-4" />;
  if (patternLower.includes('triangle')) return <Triangle className="h-4 w-4" />;
  if (patternLower.includes('breakout') || patternLower.includes('breakdown')) return <Zap className="h-4 w-4" />;
  if (patternLower.includes('double')) return <Activity className="h-4 w-4" />;
  if (patternLower.includes('head')) return <Activity className="h-4 w-4" />;
  return <Target className="h-4 w-4" />;
};

const getDirectionColor = (direction: string) => {
  if (direction === 'bullish') return 'text-green-400';
  if (direction === 'bearish') return 'text-red-400';
  return 'text-yellow-400';
};

const getSignalBg = (signal: string) => {
  if (signal === 'BUY') return 'bg-green-600';
  if (signal === 'SELL') return 'bg-red-600';
  if (signal === 'WATCH') return 'bg-yellow-600';
  return 'bg-slate-600';
};

export default function PatternInsights({ symbol, interval = 'daily', compact = false }: PatternInsightsProps) {
  const [data, setData] = useState<PatternData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(!compact);
  const [selectedInterval, setSelectedInterval] = useState(interval);

  const fetchPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/analysis/patterns/${symbol}?interval=${selectedInterval}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch patterns: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Pattern fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load patterns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatterns();
  }, [symbol, selectedInterval]);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <div className="flex items-center gap-2 animate-pulse">
          <Activity className="h-5 w-5 text-purple-400" />
          <span className="text-slate-400">Scanning patterns for {symbol}...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="h-5 w-5" />
            <span>{error}</span>
          </div>
          <button onClick={fetchPatterns} className="p-1 hover:bg-slate-700 rounded">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header with Signal */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${data.pattern_bias === 'bullish' ? 'bg-green-900/50' : data.pattern_bias === 'bearish' ? 'bg-red-900/50' : 'bg-slate-700'}`}>
              {data.pattern_bias === 'bullish' ? (
                <TrendingUp className="h-5 w-5 text-green-400" />
              ) : data.pattern_bias === 'bearish' ? (
                <TrendingDown className="h-5 w-5 text-red-400" />
              ) : (
                <Activity className="h-5 w-5 text-yellow-400" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-white">Pattern Analysis</h3>
              <p className="text-xs text-slate-400">{data.patterns_detected} patterns detected</p>
            </div>
          </div>

          {/* Trade Signal Badge */}
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-bold text-white ${getSignalBg(data.trade_signal)}`}>
              {data.trade_signal}
            </span>
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 hover:bg-slate-700 rounded"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Interval Selector */}
        <div className="flex items-center gap-1 mt-3">
          {['5min', '15min', '1hour', 'daily'].map((int) => (
            <button
              key={int}
              onClick={() => setSelectedInterval(int)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                selectedInterval === int
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              }`}
            >
              {int === 'daily' ? '1D' : int.replace('min', 'm').replace('hour', 'H')}
            </button>
          ))}
          <button
            onClick={fetchPatterns}
            className="ml-auto p-1 hover:bg-slate-700 rounded"
            title="Refresh patterns"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Active Breakout Alert */}
      {data.active_breakout && (
        <div className={`px-4 py-3 ${data.active_breakout.direction === 'bullish' ? 'bg-green-900/30 border-green-500/30' : 'bg-red-900/30 border-red-500/30'} border-b`}>
          <div className="flex items-center gap-2">
            <Zap className={`h-5 w-5 ${data.active_breakout.direction === 'bullish' ? 'text-green-400' : 'text-red-400'}`} />
            <div>
              <p className={`font-semibold ${data.active_breakout.direction === 'bullish' ? 'text-green-400' : 'text-red-400'}`}>
                {data.active_breakout.type}!
              </p>
              <p className="text-xs text-slate-300">{data.active_breakout.description}</p>
            </div>
            <span className="ml-auto text-xs bg-slate-800 px-2 py-1 rounded">
              {data.active_breakout.confidence}% conf
            </span>
          </div>
        </div>
      )}

      {expanded && (
        <>
          {/* Actionable Patterns */}
          {data.actionable_patterns.length > 0 && (
            <div className="p-4 border-b border-slate-700">
              <h4 className="text-sm font-medium text-slate-400 mb-3">Actionable Patterns</h4>
              <div className="space-y-2">
                {data.actionable_patterns.map((pattern, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg ${
                      pattern.direction === 'bullish'
                        ? 'bg-green-900/20 border border-green-500/30'
                        : pattern.direction === 'bearish'
                        ? 'bg-red-900/20 border border-red-500/30'
                        : 'bg-slate-700/50 border border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getPatternIcon(pattern.pattern)}
                        <span className={`font-medium ${getDirectionColor(pattern.direction)}`}>
                          {pattern.pattern}
                        </span>
                      </div>
                      <span className="text-xs bg-slate-800 px-2 py-1 rounded">
                        {pattern.confidence}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1">{pattern.description}</p>
                    {(pattern.price_target || pattern.stop_loss) && (
                      <div className="flex items-center gap-4 mt-2 text-xs">
                        {pattern.price_target && (
                          <div className="flex items-center gap-1">
                            <ArrowUpRight className="h-3 w-3 text-green-400" />
                            <span className="text-slate-400">Target:</span>
                            <span className="text-green-400">${pattern.price_target.toFixed(2)}</span>
                            {pattern.target_pct && (
                              <span className="text-green-500">({pattern.target_pct > 0 ? '+' : ''}{pattern.target_pct.toFixed(1)}%)</span>
                            )}
                          </div>
                        )}
                        {pattern.stop_loss && (
                          <div className="flex items-center gap-1">
                            <ArrowDownRight className="h-3 w-3 text-red-400" />
                            <span className="text-slate-400">Stop:</span>
                            <span className="text-red-400">${pattern.stop_loss.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Support & Resistance */}
          <div className="p-4 border-b border-slate-700">
            <h4 className="text-sm font-medium text-slate-400 mb-3">Key Levels</h4>
            <div className="grid grid-cols-2 gap-4">
              {/* Resistance */}
              <div>
                <p className="text-xs text-red-400 mb-2">Resistance</p>
                {data.resistance_levels.length > 0 ? (
                  <div className="space-y-1">
                    {data.resistance_levels.map((level, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm font-medium">${level.price.toFixed(2)}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-red-500"
                              style={{ width: `${level.strength}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">{level.strength.toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No resistance detected</p>
                )}
              </div>

              {/* Support */}
              <div>
                <p className="text-xs text-green-400 mb-2">Support</p>
                {data.support_levels.length > 0 ? (
                  <div className="space-y-1">
                    {data.support_levels.map((level, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm font-medium">${level.price.toFixed(2)}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500"
                              style={{ width: `${level.strength}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">{level.strength.toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No support detected</p>
                )}
              </div>
            </div>
          </div>

          {/* Trend Lines */}
          {data.trend_lines.length > 0 && (
            <div className="p-4 border-b border-slate-700">
              <h4 className="text-sm font-medium text-slate-400 mb-3">Trend Lines</h4>
              <div className="space-y-2">
                {data.trend_lines.map((tl, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        tl.type === 'support' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                      }`}>
                        {tl.type}
                      </span>
                      <span className="text-slate-400 capitalize">{tl.direction}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">${tl.current_value.toFixed(2)}</span>
                      <span className="text-xs text-slate-500">({tl.touches} touches)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Patterns List */}
          {data.patterns.length > 0 && (
            <div className="p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3">All Detected Patterns</h4>
              <div className="space-y-1">
                {data.patterns.map((pattern, idx) => (
                  <div key={idx} className="flex items-center justify-between py-1.5 border-b border-slate-700/50 last:border-0">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        pattern.direction === 'bullish' ? 'bg-green-500' :
                        pattern.direction === 'bearish' ? 'bg-red-500' : 'bg-yellow-500'
                      }`} />
                      <span className="text-sm">{pattern.pattern}</span>
                    </div>
                    <span className={`text-xs ${pattern.confidence >= 70 ? 'text-green-400' : pattern.confidence >= 50 ? 'text-yellow-400' : 'text-slate-400'}`}>
                      {pattern.confidence}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bias Score */}
          <div className="px-4 pb-4">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Bullish: {data.bullish_score.toFixed(0)}</span>
              <span>Bearish: {data.bearish_score.toFixed(0)}</span>
            </div>
            <div className="mt-1 h-2 bg-slate-700 rounded-full overflow-hidden flex">
              <div
                className="bg-green-500"
                style={{ width: `${(data.bullish_score / (data.bullish_score + data.bearish_score + 1)) * 100}%` }}
              />
              <div
                className="bg-red-500"
                style={{ width: `${(data.bearish_score / (data.bullish_score + data.bearish_score + 1)) * 100}%` }}
              />
            </div>
          </div>

          {/* Timestamp */}
          <div className="px-4 pb-3 text-xs text-slate-500 text-right">
            Updated: {new Date(data.timestamp).toLocaleTimeString()}
          </div>
        </>
      )}
    </div>
  );
}
