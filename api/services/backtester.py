"""
Backtesting Engine
Test trading strategies on historical data
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics

from services.indicators import IndicatorService

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    """Available backtest strategies"""
    RSI_OVERSOLD = "rsi_oversold"
    MACD_CROSSOVER = "macd_crossover"
    GOLDEN_CROSS = "golden_cross"
    BOLLINGER_BOUNCE = "bollinger_bounce"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    CUSTOM = "custom"


@dataclass
class Trade:
    """Represents a single backtest trade"""
    entry_date: str
    entry_price: float
    exit_date: str = ""
    exit_price: float = 0
    side: str = "long"  # "long" or "short"
    quantity: int = 1
    pnl: float = 0
    pnl_pct: float = 0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    strategy: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_trade_pnl: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration_days: float
    trades: List[Trade] = field(default_factory=list)


class BacktestEngine:
    """
    Engine for backtesting trading strategies on historical data.
    """

    def __init__(self):
        self.indicator_service = IndicatorService()

    def run_backtest(
        self,
        symbol: str,
        strategy: StrategyType,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        dates: List[str],
        initial_capital: float = 10000,
        position_size_pct: float = 0.1,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
        **strategy_params
    ) -> BacktestResult:
        """
        Run a backtest on historical data.

        Args:
            symbol: Stock symbol
            strategy: Strategy to test
            opens, highs, lows, closes, volumes: Price data
            dates: Date strings
            initial_capital: Starting capital
            position_size_pct: Position size as % of capital
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            **strategy_params: Strategy-specific parameters
        """
        # Calculate indicators
        rsi = self.indicator_service.calculate_rsi(closes, 14)
        macd_line, signal_line, histogram = self.indicator_service.calculate_macd(closes)
        sma_20 = self.indicator_service.calculate_sma(closes, 20)
        sma_50 = self.indicator_service.calculate_sma(closes, 50)
        sma_200 = self.indicator_service.calculate_sma(closes, 200)
        upper_bb, middle_bb, lower_bb = self.indicator_service.calculate_bollinger_bands(closes)
        atr = self.indicator_service.calculate_atr(highs, lows, closes, 14)

        # Initialize tracking
        capital = initial_capital
        position = None  # Current position
        trades = []
        equity_curve = [initial_capital]
        peak_equity = initial_capital
        max_drawdown = 0

        # Minimum bars needed for indicators
        min_bars = 200 if sma_200 else 50

        # Run through each bar
        for i in range(min_bars, len(closes)):
            current_price = closes[i]
            current_date = dates[i]

            # Update equity curve
            if position:
                unrealized_pnl = (current_price - position.entry_price) * position.quantity
                if position.side == "short":
                    unrealized_pnl = -unrealized_pnl
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital

            equity_curve.append(current_equity)

            # Track max drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity
            drawdown = (peak_equity - current_equity) / peak_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

            # Check exit conditions if in position
            if position:
                exit_signal = False
                exit_reason = ""

                # Stop loss
                if position.side == "long":
                    if current_price <= position.entry_price * (1 - stop_loss_pct):
                        exit_signal = True
                        exit_reason = "stop_loss"
                    elif current_price >= position.entry_price * (1 + take_profit_pct):
                        exit_signal = True
                        exit_reason = "take_profit"
                else:  # Short
                    if current_price >= position.entry_price * (1 + stop_loss_pct):
                        exit_signal = True
                        exit_reason = "stop_loss"
                    elif current_price <= position.entry_price * (1 - take_profit_pct):
                        exit_signal = True
                        exit_reason = "take_profit"

                # Strategy-specific exit
                if not exit_signal:
                    exit_signal, exit_reason = self._check_exit_signal(
                        strategy, i, position.side,
                        rsi, macd_line, signal_line, sma_20, sma_50, upper_bb, lower_bb,
                        closes, strategy_params
                    )

                if exit_signal:
                    # Close position
                    if position.side == "long":
                        pnl = (current_price - position.entry_price) * position.quantity
                    else:
                        pnl = (position.entry_price - current_price) * position.quantity

                    pnl_pct = pnl / (position.entry_price * position.quantity) * 100

                    position.exit_date = current_date
                    position.exit_price = current_price
                    position.pnl = pnl
                    position.pnl_pct = pnl_pct
                    position.exit_reason = exit_reason

                    trades.append(position)
                    capital += pnl
                    position = None

            # Check entry conditions if not in position
            if not position:
                entry_signal, side = self._check_entry_signal(
                    strategy, i,
                    rsi, macd_line, signal_line, sma_20, sma_50, sma_200,
                    upper_bb, lower_bb, closes, strategy_params
                )

                if entry_signal:
                    # Calculate position size
                    position_value = capital * position_size_pct
                    quantity = int(position_value / current_price)

                    if quantity > 0:
                        position = Trade(
                            entry_date=current_date,
                            entry_price=current_price,
                            side=side,
                            quantity=quantity
                        )

        # Close any remaining position at end
        if position:
            current_price = closes[-1]
            if position.side == "long":
                pnl = (current_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - current_price) * position.quantity

            position.exit_date = dates[-1]
            position.exit_price = current_price
            position.pnl = pnl
            position.pnl_pct = pnl / (position.entry_price * position.quantity) * 100
            position.exit_reason = "end_of_data"
            trades.append(position)
            capital += pnl

        # Calculate metrics
        return self._calculate_metrics(
            strategy.value, symbol, dates[min_bars], dates[-1],
            initial_capital, capital, trades, max_drawdown, equity_curve
        )

    def _check_entry_signal(
        self,
        strategy: StrategyType,
        i: int,
        rsi, macd_line, signal_line, sma_20, sma_50, sma_200,
        upper_bb, lower_bb, closes, params
    ) -> tuple[bool, str]:
        """Check for entry signals based on strategy"""
        current_price = closes[i]

        # Helper to safely get indicator value (handles None and index bounds)
        def safe_get(arr, idx):
            if arr is None or idx >= len(arr):
                return None
            return arr[idx]

        if strategy == StrategyType.RSI_OVERSOLD:
            threshold = params.get("rsi_threshold", 30)
            rsi_val = safe_get(rsi, i)
            if rsi_val is not None and rsi_val < threshold:
                return True, "long"
            if rsi_val is not None and rsi_val > (100 - threshold):
                return True, "short"

        elif strategy == StrategyType.MACD_CROSSOVER:
            macd_curr = safe_get(macd_line, i)
            macd_prev = safe_get(macd_line, i-1)
            sig_curr = safe_get(signal_line, i)
            sig_prev = safe_get(signal_line, i-1)
            if all(v is not None for v in [macd_curr, macd_prev, sig_curr, sig_prev]):
                # Bullish crossover
                if macd_curr > sig_curr and macd_prev <= sig_prev:
                    return True, "long"
                # Bearish crossover
                if macd_curr < sig_curr and macd_prev >= sig_prev:
                    return True, "short"

        elif strategy == StrategyType.GOLDEN_CROSS:
            sma50_curr = safe_get(sma_50, i)
            sma50_prev = safe_get(sma_50, i-1)
            sma200_curr = safe_get(sma_200, i)
            sma200_prev = safe_get(sma_200, i-1)
            if all(v is not None for v in [sma50_curr, sma50_prev, sma200_curr, sma200_prev]):
                # Golden cross
                if sma50_curr > sma200_curr and sma50_prev <= sma200_prev:
                    return True, "long"
                # Death cross
                if sma50_curr < sma200_curr and sma50_prev >= sma200_prev:
                    return True, "short"

        elif strategy == StrategyType.BOLLINGER_BOUNCE:
            lower = safe_get(lower_bb, i)
            upper = safe_get(upper_bb, i)
            if lower is not None and upper is not None:
                if current_price <= lower:
                    return True, "long"
                if current_price >= upper:
                    return True, "short"

        elif strategy == StrategyType.MOMENTUM:
            lookback = params.get("lookback", 20)
            if i >= lookback:
                momentum = (current_price - closes[i - lookback]) / closes[i - lookback]
                if momentum > 0.05:  # 5% momentum
                    return True, "long"
                elif momentum < -0.05:
                    return True, "short"

        elif strategy == StrategyType.MEAN_REVERSION:
            sma20_val = safe_get(sma_20, i)
            if sma20_val is not None:
                deviation = (current_price - sma20_val) / sma20_val
                if deviation < -0.03:  # 3% below MA
                    return True, "long"
                elif deviation > 0.03:  # 3% above MA
                    return True, "short"

        return False, ""

    def _check_exit_signal(
        self,
        strategy: StrategyType,
        i: int,
        side: str,
        rsi, macd_line, signal_line, sma_20, sma_50, upper_bb, lower_bb,
        closes, params
    ) -> tuple[bool, str]:
        """Check for exit signals based on strategy"""
        # Helper to safely get indicator value (handles None and index bounds)
        def safe_get(arr, idx):
            if arr is None or idx >= len(arr):
                return None
            return arr[idx]

        if strategy == StrategyType.RSI_OVERSOLD:
            rsi_val = safe_get(rsi, i)
            if side == "long" and rsi_val is not None and rsi_val > 70:
                return True, "rsi_overbought"
            if side == "short" and rsi_val is not None and rsi_val < 30:
                return True, "rsi_oversold"

        elif strategy == StrategyType.MACD_CROSSOVER:
            macd_val = safe_get(macd_line, i)
            sig_val = safe_get(signal_line, i)
            if macd_val is not None and sig_val is not None:
                if side == "long" and macd_val < sig_val:
                    return True, "macd_bearish"
                if side == "short" and macd_val > sig_val:
                    return True, "macd_bullish"

        elif strategy == StrategyType.BOLLINGER_BOUNCE:
            current_price = closes[i]
            upper = safe_get(upper_bb, i)
            lower = safe_get(lower_bb, i)
            if side == "long" and upper is not None and current_price >= upper:
                return True, "upper_band"
            if side == "short" and lower is not None and current_price <= lower:
                return True, "lower_band"

        elif strategy == StrategyType.MEAN_REVERSION:
            sma20_val = safe_get(sma_20, i)
            if sma20_val is not None:
                current_price = closes[i]
                if side == "long" and current_price >= sma20_val:
                    return True, "mean_reached"
                if side == "short" and current_price <= sma20_val:
                    return True, "mean_reached"

        return False, ""

    def _calculate_metrics(
        self,
        strategy: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        final_capital: float,
        trades: List[Trade],
        max_drawdown: float,
        equity_curve: List[float]
    ) -> BacktestResult:
        """Calculate backtest performance metrics"""
        total_return = final_capital - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        if not trades:
            return BacktestResult(
                strategy=strategy,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=final_capital,
                total_return=total_return,
                total_return_pct=total_return_pct,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                profit_factor=0,
                max_drawdown=max_drawdown * initial_capital,
                max_drawdown_pct=max_drawdown * 100,
                sharpe_ratio=0,
                avg_trade_pnl=0,
                avg_win=0,
                avg_loss=0,
                largest_win=0,
                largest_loss=0,
                avg_trade_duration_days=0,
                trades=[]
            )

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        win_rate = len(wins) / len(trades) * 100 if trades else 0

        total_wins = sum(t.pnl for t in wins)
        total_losses = abs(sum(t.pnl for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        avg_win = statistics.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = statistics.mean([t.pnl for t in losses]) if losses else 0

        # Calculate Sharpe ratio (simplified)
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)

        if returns and len(returns) > 1:
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            sharpe_ratio = (avg_return * 252) / (std_return * (252 ** 0.5)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        return BacktestResult(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown * initial_capital,
            max_drawdown_pct=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            avg_trade_pnl=statistics.mean([t.pnl for t in trades]),
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=max([t.pnl for t in trades]) if trades else 0,
            largest_loss=min([t.pnl for t in trades]) if trades else 0,
            avg_trade_duration_days=0,  # Would need date parsing
            trades=trades
        )


# Singleton instance
_backtest_engine = None

def get_backtest_engine() -> BacktestEngine:
    """Get singleton backtest engine instance"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine()
    return _backtest_engine
