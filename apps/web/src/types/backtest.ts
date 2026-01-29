/**
 * Backtest Types
 * TypeScript types for backtesting API
 */

export interface BacktestRequest {
  symbol: string;
  strategy: string;
  initial_capital: number;
  position_size_pct: number;
  stop_loss_pct: number;
  take_profit_pct: number;
}

export interface BacktestResult {
  strategy: string;
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  total_return_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  avg_trade_pnl: number;
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;
}

export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
}
