/**
 * Analysis TypeScript Types
 * Types for pattern recognition, technical analysis, and chart data
 */

// ============== Pattern Detection Types ==============

/**
 * Key point on a pattern visualization
 */
export interface PatternKeyPoint {
  index: number;
  price: number;
  label: string;
}

/**
 * Line connecting pattern points for visualization
 */
export interface PatternLine {
  start_index: number;
  start_price: number;
  end_index: number;
  end_price: number;
  label: string;
  style: 'solid' | 'dashed';
}

/**
 * Entry zone for a pattern trade
 */
export interface PatternEntryZone {
  low: number;
  high: number;
}

/**
 * Detected chart pattern (flags, triangles, head & shoulders, etc.)
 */
export interface Pattern {
  pattern: string;
  confidence: number;
  direction: 'bullish' | 'bearish' | 'neutral';
  description: string;
  price_target?: number;
  target_pct?: number;
  stop_loss?: number;
  risk_pct?: number;
  timeframe_relevance?: number;
  relevance_label?: 'High' | 'Medium' | 'Low';
  entry_zone?: PatternEntryZone;
  start_index?: number;
  end_index?: number;
  key_points?: PatternKeyPoint[];
  pattern_lines?: PatternLine[];
}

/**
 * Support or resistance level
 */
export interface SupportResistanceLevel {
  price: number;
  strength: number;
  type?: 'support' | 'resistance';
  touches?: number;
  distance_pct?: number;
}

/**
 * Trend line information
 */
export interface TrendLine {
  type: 'support' | 'resistance';
  direction: 'ascending' | 'descending' | 'horizontal';
  strength: number;
  current_value: number;
  touches: number;
}

/**
 * Active breakout alert
 */
export interface ActiveBreakout {
  type: string;
  description: string;
  confidence: number;
  direction: 'bullish' | 'bearish';
}

/**
 * Elliott Wave analysis data
 */
export interface ElliottWaveData {
  wave_count: number;
  wave_type?: string;
  current_wave?: string;
  current_position?: string;
  direction: 'bullish' | 'bearish' | 'neutral';
  confidence: number;
  description?: string;
  next_target?: number;
  swings_detected?: number;
  trading_action?: string;
  action_reason?: string;
  buy_zone?: { low: number; high: number };
  sell_zone?: { low: number; high: number };
  fib_targets?: {
    extension_1618?: number;
    retracement_382?: number;
    retracement_618?: number;
  };
  key_levels?: {
    recent_high?: number;
    recent_low?: number;
    sma_20?: number;
    sma_50?: number;
  };
  timeframes?: {
    '15min'?: ElliottWaveData;
    'hourly'?: ElliottWaveData;
    'daily'?: ElliottWaveData;
  };
}

/**
 * Pattern summary with trade signal
 */
export interface PatternSummary {
  signal: string;
  reason: string;
  confidence: number;
  entry: number | null;
  target: number | null;
  stop: number | null;
}

/**
 * Complete pattern analysis data from API
 */
export interface PatternData {
  symbol: string;
  current_price: number;
  interval: string;
  timestamp: string;
  trade_signal: 'BUY' | 'SELL' | 'WATCH' | 'NEUTRAL';
  signal_color: 'green' | 'red' | 'yellow';
  pattern_bias: 'bullish' | 'bearish' | 'neutral';
  bullish_score: number;
  bearish_score: number;
  active_breakout: ActiveBreakout | null;
  patterns_detected: number;
  patterns: Pattern[];
  actionable_patterns: Pattern[];
  support_levels: SupportResistanceLevel[];
  resistance_levels: SupportResistanceLevel[];
  nearest_support: number | null;
  nearest_resistance: number | null;
  trend_lines: TrendLine[];
  elliott_wave: ElliottWaveData | null;
  summary: PatternSummary;
}

// ============== Multi-Timeframe Analysis Types ==============

/**
 * Key levels for trade execution
 */
export interface KeyLevels {
  entry?: number;
  target?: number;
  stop?: number;
}

/**
 * Analysis for a specific timeframe
 */
export interface TimeframeAnalysis {
  timeframe: string;
  label: string;
  recommendation: string;
  confidence: number;
  signals: string[];
  concerns: string[];
  key_levels?: KeyLevels;
}

/**
 * Multi-timeframe indicators
 */
export interface MultiTimeframeIndicators {
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
}

/**
 * Complete multi-timeframe analysis data
 */
export interface MultiTimeframeData {
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
  elliott_wave?: ElliottWaveData;
  indicators: MultiTimeframeIndicators;
  timestamp: string;
}

// ============== Triple Screen Types ==============

/**
 * Data for a single screen in Triple Screen system
 */
export interface ScreenData {
  timeframe: string;
  direction?: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  entry_ready?: boolean;
  entry_triggered?: boolean;
  strength?: number;
  signals: string[];
  concerns: string[];
  indicators: Record<string, number>;
}

/**
 * Triple Screen methodology info
 */
export interface TripleScreenMethodology {
  name: string;
  description: string;
  best_for: string[];
}

/**
 * Complete Triple Screen analysis data
 */
export interface TripleScreenData {
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
  methodology: TripleScreenMethodology;
}

// ============== API Response Types ==============

/**
 * Raw API pattern response before transformation
 */
export interface ApiPatternResponse {
  symbol: string;
  patterns?: Array<{
    type: string;
    confidence: number;
    direction: string;
    description: string;
    price_target?: number;
    stop_loss?: number;
    start_index?: number;
    end_index?: number;
    key_points?: PatternKeyPoint[];
    pattern_lines?: PatternLine[];
  }>;
  support_resistance?: Array<{
    type: 'support' | 'resistance';
    price: number;
    strength: number;
  }>;
  trend_lines?: TrendLine[];
  elliott_wave?: ElliottWaveData;
  bias?: 'bullish' | 'bearish' | 'neutral';
  bullish_score?: number;
  bearish_score?: number;
  pattern_count?: number;
}

/**
 * Crypto analysis response from API
 */
export interface CryptoAnalysisResponse {
  symbol: string;
  current_price: number;
  recommendation: string;
  score: number;
  signals?: string[];
  indicators?: {
    rsi?: number;
    rsi_14?: number;
    macd?: number;
    macd_histogram?: number;
    sma_20?: number;
    sma_50?: number;
    sma_200?: number;
    ema_12?: number;
    ema_26?: number;
    bb_upper?: number;
    bb_lower?: number;
    atr?: number;
    volume_ratio?: number;
    vwap?: number;
    adx?: number;
    stoch_k?: number;
    stochastic_k?: number;
    golden_cross?: boolean;
    death_cross?: boolean;
    current_price?: number;
    close?: number;
  };
}
