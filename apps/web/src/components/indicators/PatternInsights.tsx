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
  timeframe_relevance?: number;
  relevance_label?: 'High' | 'Medium' | 'Low';
  entry_zone?: {
    low: number;
    high: number;
  };
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
      const response = await fetch(`${API_URL}/api/advanced/patterns/${symbol}?interval=${selectedInterval}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch patterns: ${response.statusText}`);
      }
      const result = await response.json();

      // Transform API response to match component interface
      const supportLevels = (result.support_resistance || [])
        .filter((sr: any) => sr.type === 'support')
        .map((sr: any) => ({ price: sr.price, strength: sr.strength }));
      const resistanceLevels = (result.support_resistance || [])
        .filter((sr: any) => sr.type === 'resistance')
        .map((sr: any) => ({ price: sr.price, strength: sr.strength }));

      // Transform patterns to expected format
      const transformedPatterns = (result.patterns || []).map((p: any) => ({
        pattern: p.type.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
        confidence: p.confidence,
        direction: p.direction,
        description: p.description,
        price_target: p.price_target,
        stop_loss: p.stop_loss,
      }));

      // Determine trade signal based on bias and confidence
      const highConfPatterns = transformedPatterns.filter((p: any) => p.confidence >= 70);
      let tradeSignal = 'NEUTRAL';
      if (result.bias === 'bullish' && highConfPatterns.some((p: any) => p.direction === 'bullish')) {
        tradeSignal = 'BUY';
      } else if (result.bias === 'bearish' && highConfPatterns.some((p: any) => p.direction === 'bearish')) {
        tradeSignal = 'SELL';
      } else if (highConfPatterns.length > 0) {
        tradeSignal = 'WATCH';
      }

      const transformedData: PatternData = {
        symbol: result.symbol,
        current_price: 0, // Not provided by this endpoint
        interval: selectedInterval,
        timestamp: new Date().toISOString(),
        trade_signal: tradeSignal,
        signal_color: tradeSignal === 'BUY' ? 'green' : tradeSignal === 'SELL' ? 'red' : 'yellow',
        pattern_bias: result.bias || 'neutral',
        bullish_score: result.bullish_score || 0,
        bearish_score: result.bearish_score || 0,
        active_breakout: null,
        patterns_detected: result.pattern_count || transformedPatterns.length,
        patterns: transformedPatterns,
        actionable_patterns: transformedPatterns.filter((p: any) => p.confidence >= 65),
        support_levels: supportLevels,
        resistance_levels: resistanceLevels,
        nearest_support: supportLevels.length > 0 ? supportLevels[0].price : null,
        nearest_resistance: resistanceLevels.length > 0 ? resistanceLevels[0].price : null,
        trend_lines: result.trend_lines || [],
        elliott_wave: result.elliott_wave || null,
        summary: {
          signal: tradeSignal,
          reason: result.bias === 'bullish' ? 'Bullish patterns detected' :
                  result.bias === 'bearish' ? 'Bearish patterns detected' : 'Mixed signals',
          confidence: Math.max(...transformedPatterns.map((p: any) => p.confidence), 0),
          entry: null,
          target: transformedPatterns[0]?.price_target || null,
          stop: transformedPatterns[0]?.stop_loss || null,
        },
      };

      setData(transformedData);
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
                        {/* Timeframe Relevance Badge */}
                        {pattern.relevance_label && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                            pattern.relevance_label === 'High' ? 'bg-green-900/50 text-green-400' :
                            pattern.relevance_label === 'Low' ? 'bg-red-900/50 text-red-400' :
                            'bg-slate-700 text-slate-400'
                          }`}>
                            {pattern.relevance_label === 'High' ? '★' : pattern.relevance_label === 'Low' ? '○' : '◐'} {pattern.relevance_label}
                          </span>
                        )}
                      </div>
                      <span className="text-xs bg-slate-800 px-2 py-1 rounded">
                        {pattern.confidence.toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1">{pattern.description}</p>

                    {/* Entry Zone - Buy/Sell Range */}
                    {pattern.entry_zone && (
                      <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">
                            {pattern.direction === 'bullish' ? '🟢 Buy Zone:' : '🔴 Sell Zone:'}
                          </span>
                          <span className={pattern.direction === 'bullish' ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>
                            ${pattern.entry_zone.low.toFixed(2)} - ${pattern.entry_zone.high.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    )}

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
                        <span className="text-sm font-medium">${(level.price ?? 0).toFixed(2)}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-red-500"
                              style={{ width: `${level.strength ?? 0}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">{(level.strength ?? 0).toFixed(0)}%</span>
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
                        <span className="text-sm font-medium">${(level.price ?? 0).toFixed(2)}</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500"
                              style={{ width: `${level.strength ?? 0}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">{(level.strength ?? 0).toFixed(0)}%</span>
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
                      <span className="font-medium">${(tl.current_value ?? 0).toFixed(2)}</span>
                      <span className="text-xs text-slate-500">({tl.touches ?? 0} touches)</span>
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

          {/* Overall Sentiment Summary */}
          <div className="px-4 pb-4">
            {/* Net Sentiment Explanation */}
            {(() => {
              const bullish = data.bullish_score ?? 0;
              const bearish = data.bearish_score ?? 0;
              const netSentiment = bullish - bearish;

              // Find strongest pattern
              const strongestPattern = data.patterns.length > 0
                ? data.patterns.reduce((a, b) => a.confidence > b.confidence ? a : b)
                : null;

              // Determine overall verdict
              let verdict = 'NEUTRAL';
              let verdictColor = 'text-yellow-400';
              let verdictBg = 'bg-yellow-900/30';

              if (netSentiment > 50) {
                verdict = 'STRONGLY BULLISH';
                verdictColor = 'text-green-400';
                verdictBg = 'bg-green-900/30';
              } else if (netSentiment > 20) {
                verdict = 'BULLISH';
                verdictColor = 'text-green-400';
                verdictBg = 'bg-green-900/30';
              } else if (netSentiment < -50) {
                verdict = 'STRONGLY BEARISH';
                verdictColor = 'text-red-400';
                verdictBg = 'bg-red-900/30';
              } else if (netSentiment < -20) {
                verdict = 'BEARISH';
                verdictColor = 'text-red-400';
                verdictBg = 'bg-red-900/30';
              } else {
                verdict = 'MIXED SIGNALS';
                verdictColor = 'text-yellow-400';
                verdictBg = 'bg-yellow-900/30';
              }

              return (
                <div className={`rounded-lg p-3 mb-3 ${verdictBg} border border-slate-700`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400">Overall Sentiment</span>
                    <span className={`text-sm font-bold ${verdictColor}`}>{verdict}</span>
                  </div>

                  {strongestPattern && (
                    <p className="text-xs text-slate-300 mb-2">
                      <span className="text-slate-500">Dominant signal: </span>
                      <span className={strongestPattern.direction === 'bullish' ? 'text-green-400' : 'text-red-400'}>
                        {strongestPattern.pattern}
                      </span>
                      <span className="text-slate-500"> ({strongestPattern.confidence}% confidence)</span>
                    </p>
                  )}

                  {data.patterns.length > 1 && Math.abs(netSentiment) < 30 && (
                    <p className="text-xs text-yellow-400/80 italic">
                      Conflicting patterns detected - consider waiting for clearer signals
                    </p>
                  )}
                </div>
              );
            })()}

            {/* Bias Score Bar */}
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="text-green-400">Bullish: {(data.bullish_score ?? 0).toFixed(0)}</span>
              <span className="text-red-400">Bearish: {(data.bearish_score ?? 0).toFixed(0)}</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden flex">
              <div
                className="bg-green-500"
                style={{ width: `${((data.bullish_score ?? 0) / ((data.bullish_score ?? 0) + (data.bearish_score ?? 0) + 1)) * 100}%` }}
              />
              <div
                className="bg-red-500"
                style={{ width: `${((data.bearish_score ?? 0) / ((data.bullish_score ?? 0) + (data.bearish_score ?? 0) + 1)) * 100}%` }}
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
