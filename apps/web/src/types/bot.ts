/**
 * Trading Bot TypeScript Types
 * Matches the API response models from the backend
 */

// ============== Enums ==============

export type BotState = 'RUNNING' | 'STOPPED' | 'PAUSED' | 'ERROR';
export type TradeType = 'SCALP' | 'INTRADAY' | 'SWING' | 'LONG_TERM';
export type OrderSide = 'BUY' | 'SELL';
export type ExitReason = 'PROFIT_TARGET' | 'STOP_LOSS' | 'SIGNAL' | 'MANUAL' | 'TIME_STOP';

// ============== Bot Status ==============

export type TimeHorizon = 'SCALP' | 'INTRADAY' | 'SWING';

export interface AIDecision {
  timestamp: string;
  symbol: string;
  decision: 'APPROVE' | 'REJECT' | 'WAIT';
  confidence: number;
  reasoning: string;
  concerns: string[];
  ai_generated: boolean;
  model: string;
  technical_score: number;
  technical_signal: string;
  suggested_position_size_pct?: number;
  suggested_stop_loss_pct?: number;
  suggested_take_profit_pct?: number;
  wait_for?: string;
  // Time horizon for the trade strategy
  time_horizon?: TimeHorizon;
  // Confidence breakdown for reasoning modal
  confidence_breakdown?: {
    technical_weight: number;
    technical_contribution: string;
    sentiment_weight: number;
    sentiment_contribution: string;
    historical_accuracy: number;
    volume_weight: number;
    volume_contribution: string;
  };
}

export interface CryptoAnalysisResult {
  signal: string;
  confidence: number;
  threshold: number;
  meets_threshold?: boolean;
  reason: string;
  timestamp: string;
  indicators?: Record<string, number>;
  signals?: string[];
  ai_decision?: AIDecision;
}

export interface StockAnalysisResult {
  signal: string;
  confidence: number;
  threshold: number;
  meets_threshold?: boolean;
  reason: string;
  timestamp: string;
  indicators?: Record<string, number>;
  current_price?: number;
  trade_type?: string;
  ai_decision?: AIDecision;
}

export interface CryptoBestOpportunity {
  symbol: string;
  confidence: number;
  threshold: number;
  meets_threshold: boolean;
}

export interface CryptoScanProgress {
  total: number;
  scanned: number;
  current_symbol: string | null;
  signals_found: number;
  best_opportunity: CryptoBestOpportunity | null;
  scan_status: 'idle' | 'scanning' | 'exhausted' | 'found_opportunity';
  scan_summary: string;
  last_scan_completed: string | null;
  next_scan_in_seconds: number;
}

export interface StockBestOpportunity {
  symbol: string;
  confidence: number;
  threshold: number;
  meets_threshold: boolean;
}

export interface StockScanProgress {
  total: number;
  scanned: number;
  current_symbol: string | null;
  signals_found: number;
  best_opportunity: StockBestOpportunity | null;
  scan_status: 'idle' | 'scanning' | 'exhausted' | 'found_opportunity' | 'market_closed' | 'disabled' | 'extended_hours_waiting';
  scan_summary: string;
  last_scan_completed: string | null;
  next_scan_in_seconds: number;
  market_status: string;
}

export interface ExecutionLogEntry {
  timestamp: string;
  symbol: string;
  event_type: string;
  executed: boolean;
  reason: string;
  details: Record<string, unknown>;
}

export interface PriorityTierSummary {
  total_symbols: number;
  tier_distribution: {
    high: number;
    standard: number;
    low: number;
  };
  total_scans: number;
  scans_by_tier: {
    high: number;
    standard: number;
    low: number;
  };
}

export interface BotStatus {
  state: BotState;
  uptime_seconds: number;
  uptime_formatted?: string;
  last_trade_time: string | null;
  current_cycle: string;
  current_session?: string;
  error_message: string | null;
  paper_trading: boolean;
  active_symbols: string[];
  // Asset Class Mode
  asset_class_mode?: 'crypto' | 'stocks' | 'both';
  // Auto trade mode
  auto_trade_mode?: boolean;
  ai_risk_tolerance?: string;
  // Crypto trading fields
  crypto_trading_enabled?: boolean;
  crypto_symbols?: string[];
  crypto_max_positions?: number;
  crypto_positions?: number;
  crypto_analysis_results?: Record<string, CryptoAnalysisResult>;
  last_crypto_analysis_time?: string | null;
  // Crypto scan progress tracking
  crypto_scan_progress?: CryptoScanProgress;
  // Stock scan progress tracking
  stock_scan_progress?: StockScanProgress;
  // Stock analysis results (similar to crypto)
  stock_analysis_results?: Record<string, StockAnalysisResult>;
  last_stock_analysis_time?: string | null;
  // Entry threshold
  entry_threshold?: number;
  // AI Decision Tracking
  last_ai_decision?: AIDecision | null;
  ai_decisions_history?: AIDecision[];
  // Tactical Controls
  execution_log?: ExecutionLogEntry[];
  new_entries_paused?: boolean;
  strategy_override?: string | null;
  total_scans_today?: number;
  priority_tier_summary?: PriorityTierSummary;
}

export interface BotActionResponse {
  success: boolean;
  message: string;
  state: BotState;
}

export interface BotStartRequest {
  paper_trading?: boolean;
  symbols?: string[];
}

// ============== Account ==============

export interface AccountSummary {
  equity: number;
  cash: number;
  buying_power: number;
  portfolio_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  day_pnl: number;
  day_pnl_pct: number;
}

// ============== Positions ==============

export interface Position {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_loss: number | null;
  profit_target: number | null;
  trade_type: TradeType | null;
  entry_time: string;
  entry_score: number | null;
}

export interface PositionsList {
  positions: Position[];
  total_value: number;
  total_unrealized_pnl: number;
}

export interface ClosePositionResponse {
  success: boolean;
  message: string;
  symbol: string;
  quantity_closed: number;
  exit_price: number | null;
  realized_pnl: number | null;
}

// ============== Trades ==============

export interface Trade {
  id: number;
  symbol: string;
  side: OrderSide;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  entry_time: string;
  exit_time: string | null;
  profit_loss: number | null;
  profit_loss_pct: number | null;
  exit_reason: ExitReason | null;
  trade_type: TradeType | null;
  entry_score: number | null;
}

export interface TradeHistory {
  trades: Trade[];
  total_count: number;
  page: number;
  page_size: number;
}

// ============== Performance ==============

export interface PerformanceSummary {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
}

export interface PerformanceMetrics {
  period_days: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  profit_factor: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  max_drawdown_pct: number;
  avg_win: number;
  avg_loss: number;
  avg_trade_duration_hours: number;
  best_trade: number;
  worst_trade: number;
  swing_trades: number;
  swing_win_rate: number;
  longterm_trades: number;
  longterm_win_rate: number;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
  pnl: number;
  cumulative_pnl: number;
}

export interface EquityCurve {
  data: EquityCurvePoint[];
  starting_equity: number;
  current_equity: number;
  total_return_pct: number;
}

// ============== Settings ==============

export interface BotSettings {
  enabled_symbols: string[];
  max_positions: number;
  max_position_size_pct: number;
  risk_per_trade_pct: number;
  max_daily_loss_pct: number;
  default_stop_loss_pct: number;
  entry_score_threshold: number;
  swing_profit_target_pct: number;
  longterm_profit_target_pct: number;
  paper_trading: boolean;
  trading_hours_only: boolean;
  auto_optimize: boolean;
}

export interface BotSettingsResponse {
  settings: BotSettings;
  config_name: string;
  last_updated: string | null;
}

export interface SettingsPreset {
  name: string;
  description: string;
  settings: Partial<BotSettings>;
}

// ============== Optimization ==============

export interface OptimizationLogEntry {
  timestamp: string;
  parameter: string;
  old_value: number;
  new_value: number;
  reason: string;
  applied: boolean;
}

export interface OptimizationHistory {
  entries: OptimizationLogEntry[];
  total_adjustments: number;
}

// ============== Health ==============

export interface BotHealth {
  status: 'healthy' | 'unhealthy';
  bot_state: BotState;
  alpaca_connected: boolean;
  market_open?: boolean;
  account_equity?: number;
  buying_power?: number;
  error?: string;
}

// ============== Post-Mortem Analysis ==============

export interface TradeSummary {
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  side: string;
  entry_time: string | null;
  exit_time: string | null;
  duration: {
    hours: number;
    days: number;
    formatted: string;
  } | null;
  profit_loss: number | null;
  profit_loss_pct: number | null;
  exit_reason: string | null;
  trade_type: string | null;
  entry_score: number | null;
  was_profitable: boolean;
}

export interface OptimalExitAnalysis {
  type: string;
  best_possible_exit: number;
  worst_possible_exit: number;
  actual_exit: number;
  best_possible_pnl: number;
  worst_possible_pnl: number;
  actual_pnl: number;
  exit_efficiency_pct: number;
}

export interface TradeAnalysis {
  trade_id: number;
  symbol: string;
  analyzed_at: string;
  trade_summary: TradeSummary;
  price_context?: {
    dates: string[];
    prices: number[];
    highs: number[];
    lows: number[];
    max_price_during_trade: number;
    min_price_during_trade: number;
  };
  optimal_exit_price: number | null;
  missed_profit: number | null;
  could_have_done_better: boolean | null;
  optimal_exit_analysis: OptimalExitAnalysis | null;
  what_went_well: string[];
  what_went_wrong: string[];
  lessons_learned: string;
  ai_summary?: string;
}

export interface DailySummary {
  date: string;
  message?: string;
  total_trades: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate?: number;
  total_pnl?: number;
  best_trade?: {
    symbol: string;
    pnl: number;
  };
  worst_trade?: {
    symbol: string;
    pnl: number;
  };
  trades?: Array<{
    id: number;
    symbol: string;
    pnl: number | null;
    pnl_pct: number | null;
    exit_reason: string | null;
  }>;
}

export interface WeeklyReport {
  period: string;
  message?: string;
  total_trades: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate?: number;
  total_pnl?: number;
  avg_pnl_per_trade?: number;
  best_symbol?: string;
  worst_symbol?: string;
  by_symbol?: Record<string, { trades: number; pnl: number }>;
  by_exit_reason?: Record<string, number>;
  ai_insights?: string;
}
