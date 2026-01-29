"""
Performance metrics calculation for backtesting.

Calculates key metrics like win rate, Sharpe ratio, max drawdown, etc.
"""

import math
import logging
from typing import List, Optional
from datetime import datetime

from models.backtest import SimulatedTrade, EquityPoint, PerformanceMetricsResult

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Calculate performance metrics from backtest results.
    """

    # Risk-free rate for Sharpe/Sortino (annualized, e.g., 4% = 0.04)
    RISK_FREE_RATE = 0.04

    # Trading days per year
    TRADING_DAYS_PER_YEAR = 252

    @classmethod
    def calculate(
        cls,
        trades: List[SimulatedTrade],
        equity_curve: List[EquityPoint],
        initial_capital: float,
        benchmark_return_pct: Optional[float] = None
    ) -> PerformanceMetricsResult:
        """
        Calculate all performance metrics.

        Args:
            trades: List of completed trades
            equity_curve: Equity values over time
            initial_capital: Starting capital
            benchmark_return_pct: Optional benchmark return for alpha calculation

        Returns:
            PerformanceMetricsResult with all metrics
        """
        # Filter to completed trades only
        completed = [t for t in trades if t.exit_price is not None]

        # Basic stats
        total_trades = len(completed)
        winning_trades = sum(1 for t in completed if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in completed if t.pnl and t.pnl <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Extract equity values
        equities = [e.equity for e in equity_curve] if equity_curve else [initial_capital]
        final_equity = equities[-1] if equities else initial_capital

        # Returns
        total_return_pct = (final_equity - initial_capital) / initial_capital * 100
        annualized_return = cls._calculate_annualized_return(equity_curve, initial_capital)

        # Risk metrics
        max_drawdown = cls._calculate_max_drawdown(equities)
        sharpe = cls._calculate_sharpe_ratio(equity_curve)
        sortino = cls._calculate_sortino_ratio(equity_curve)

        # Trade metrics
        wins = [t.pnl for t in completed if t.pnl and t.pnl > 0]
        losses = [t.pnl for t in completed if t.pnl and t.pnl <= 0]

        average_win = sum(wins) / len(wins) if wins else 0
        average_loss = sum(losses) / len(losses) if losses else 0

        total_wins = sum(wins)
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        expectancy = (win_rate * average_win) - ((1 - win_rate) * abs(average_loss))

        # Alpha (outperformance vs benchmark)
        alpha = None
        if benchmark_return_pct is not None:
            alpha = total_return_pct - benchmark_return_pct

        return PerformanceMetricsResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 4),
            total_return_pct=round(total_return_pct, 2),
            annualized_return_pct=round(annualized_return, 2),
            max_drawdown_pct=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            average_win=round(average_win, 2),
            average_loss=round(average_loss, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
            expectancy=round(expectancy, 2),
            benchmark_return_pct=round(benchmark_return_pct, 2) if benchmark_return_pct else None,
            alpha=round(alpha, 2) if alpha else None
        )

    @classmethod
    def _calculate_max_drawdown(cls, equities: List[float]) -> float:
        """
        Calculate maximum drawdown percentage.

        Max drawdown is the largest peak-to-trough decline.
        """
        if not equities:
            return 0

        peak = equities[0]
        max_dd = 0

        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)

        return max_dd

    @classmethod
    def _calculate_annualized_return(
        cls,
        equity_curve: List[EquityPoint],
        initial_capital: float
    ) -> float:
        """Calculate annualized return percentage."""
        if not equity_curve or len(equity_curve) < 2:
            return 0

        final_equity = equity_curve[-1].equity
        total_return = final_equity / initial_capital

        # Calculate days in backtest
        start = equity_curve[0].timestamp
        end = equity_curve[-1].timestamp
        days = (end - start).days

        if days <= 0:
            return 0

        # Annualize: (1 + total_return)^(365/days) - 1
        years = days / 365
        if years > 0:
            annualized = (total_return ** (1 / years)) - 1
            return annualized * 100
        return 0

    @classmethod
    def _calculate_sharpe_ratio(cls, equity_curve: List[EquityPoint]) -> float:
        """
        Calculate Sharpe ratio.

        Sharpe = (Return - RiskFreeRate) / StdDev(Returns)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0

        # Calculate daily returns
        daily_returns = cls._calculate_daily_returns(equity_curve)
        if not daily_returns:
            return 0

        # Mean and std of daily returns
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_return = math.sqrt(variance) if variance > 0 else 0

        if std_return == 0:
            return 0

        # Annualize
        daily_rf = cls.RISK_FREE_RATE / cls.TRADING_DAYS_PER_YEAR
        excess_return = mean_return - daily_rf
        sharpe = (excess_return / std_return) * math.sqrt(cls.TRADING_DAYS_PER_YEAR)

        return sharpe

    @classmethod
    def _calculate_sortino_ratio(cls, equity_curve: List[EquityPoint]) -> float:
        """
        Calculate Sortino ratio.

        Like Sharpe but only penalizes downside volatility.
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0

        daily_returns = cls._calculate_daily_returns(equity_curve)
        if not daily_returns:
            return 0

        mean_return = sum(daily_returns) / len(daily_returns)

        # Downside deviation (std of negative returns only)
        negative_returns = [r for r in daily_returns if r < 0]
        if not negative_returns:
            return float('inf')  # No downside = infinite Sortino

        variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_std = math.sqrt(variance) if variance > 0 else 0

        if downside_std == 0:
            return 0

        daily_rf = cls.RISK_FREE_RATE / cls.TRADING_DAYS_PER_YEAR
        excess_return = mean_return - daily_rf
        sortino = (excess_return / downside_std) * math.sqrt(cls.TRADING_DAYS_PER_YEAR)

        return sortino

    @classmethod
    def _calculate_daily_returns(cls, equity_curve: List[EquityPoint]) -> List[float]:
        """Calculate daily return percentages."""
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1].equity
            curr = equity_curve[i].equity
            if prev > 0:
                returns.append((curr - prev) / prev)

        return returns

    @classmethod
    def calculate_benchmark_return(
        cls,
        benchmark_bars: List,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """
        Calculate buy-and-hold return for benchmark (e.g., SPY).

        Args:
            benchmark_bars: List of bars for benchmark
            start_date: Start date
            end_date: End date

        Returns:
            Total return percentage
        """
        if not benchmark_bars or len(benchmark_bars) < 2:
            return 0

        start_price = benchmark_bars[0].close if hasattr(benchmark_bars[0], 'close') else benchmark_bars[0].get('close', 0)
        end_price = benchmark_bars[-1].close if hasattr(benchmark_bars[-1], 'close') else benchmark_bars[-1].get('close', 0)

        if start_price <= 0:
            return 0

        return (end_price - start_price) / start_price * 100
