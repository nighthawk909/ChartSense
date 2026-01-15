/**
 * Trading Bot TypeScript Types
 * Matches the API response models from the backend
 */

// ============== Enums ==============

export type BotState = 'RUNNING' | 'STOPPED' | 'PAUSED' | 'ERROR';
export type TradeType = 'SWING' | 'LONG_TERM';
export type OrderSide = 'BUY' | 'SELL';
export type ExitReason = 'PROFIT_TARGET' | 'STOP_LOSS' | 'SIGNAL' | 'MANUAL' | 'TIME_STOP';

// ============== Bot Status ==============

export interface BotStatus {
  state: BotState;
  uptime_seconds: number;
  last_trade_time: string | null;
  current_cycle: string;
  error_message: string | null;
  paper_trading: boolean;
  active_symbols: string[];
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
