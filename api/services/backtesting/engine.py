"""
Core backtesting engine.

Simulates time progression through historical data and executes strategy signals.
"""

import logging
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Protocol

from models.backtest import BacktestRequest, BacktestResult, Signal
from .data_loader import DataLoader, BacktestData, Bar
from .portfolio import SimulatedPortfolio
from .metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class Strategy(Protocol):
    """Protocol for backtestable strategies."""

    async def generate_signals(
        self,
        bars: Dict[str, Bar],
        portfolio: SimulatedPortfolio,
        lookback_data: BacktestData,
        current_timestamp: datetime
    ) -> List[Signal]:
        """Generate trading signals based on current market data."""
        ...


class BacktestEngine:
    """
    Core backtesting engine that simulates time progression.

    Flow:
    1. Load historical data for date range
    2. For each bar (day/hour/minute):
       - Update portfolio with current prices
       - Run strategy to generate signals
       - Execute simulated trades
       - Record metrics
    3. Calculate final performance
    """

    def __init__(
        self,
        strategy: Strategy,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000,
        position_size_pct: float = 10.0,
    ):
        """
        Initialize the backtest engine.

        Args:
            strategy: The strategy to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital
            position_size_pct: Position size as % of portfolio
        """
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct

        self.data_loader = DataLoader()
        self.portfolio = SimulatedPortfolio(
            initial_capital=initial_capital,
            position_size_pct=position_size_pct
        )

    async def run(self, symbols: List[str]) -> BacktestResult:
        """
        Run the backtest.

        Args:
            symbols: List of symbols to trade

        Returns:
            BacktestResult with performance metrics and trade history
        """
        start_time = time.time()
        logger.info(f"Starting backtest: {len(symbols)} symbols, {self.start_date} to {self.end_date}")

        # Load all historical data upfront
        data = await self.data_loader.load(
            symbols=symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            timeframe="1Day"
        )

        # Load benchmark data for comparison
        benchmark_data = await self.data_loader.load_benchmark(self.start_date, self.end_date)

        bars_processed = 0

        # Iterate through time
        for timestamp in data.timestamps:
            current_bars = data.get_bars_at(timestamp)

            if not current_bars:
                continue

            # Update portfolio with current prices
            self.portfolio.update_prices(current_bars)

            # Generate signals from strategy
            try:
                signals = await self.strategy.generate_signals(
                    bars=current_bars,
                    portfolio=self.portfolio,
                    lookback_data=data,
                    current_timestamp=timestamp
                )
            except Exception as e:
                logger.error(f"Strategy error at {timestamp}: {e}")
                signals = []

            # Execute simulated trades
            for signal in signals:
                if signal.symbol in current_bars:
                    price = current_bars[signal.symbol].close
                    self.portfolio.execute(signal, price)

            # Record equity
            self.portfolio.record_equity(timestamp)
            bars_processed += 1

        # Close any remaining positions at end of backtest
        if data.timestamps:
            final_timestamp = data.timestamps[-1]
            self.portfolio.close_all_positions(final_timestamp)
            self.portfolio.record_equity(final_timestamp)

        # Calculate benchmark return
        benchmark_return = None
        if benchmark_data.bars:
            benchmark_return = PerformanceMetrics.calculate_benchmark_return(
                benchmark_data.bars,
                datetime.combine(self.start_date, datetime.min.time()),
                datetime.combine(self.end_date, datetime.max.time())
            )

        # Calculate performance metrics
        metrics = PerformanceMetrics.calculate(
            trades=self.portfolio.trades,
            equity_curve=self.portfolio.equity_curve,
            initial_capital=self.initial_capital,
            benchmark_return_pct=benchmark_return
        )

        run_time = time.time() - start_time

        logger.info(f"Backtest complete: {bars_processed} bars, {metrics.total_trades} trades, "
                   f"{metrics.total_return_pct:.1f}% return, {run_time:.2f}s")

        return BacktestResult(
            symbols=symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital,
            strategy=self.strategy.__class__.__name__,
            strategy_params=getattr(self.strategy, 'params', {}),
            final_equity=self.portfolio.equity,
            metrics=metrics,
            equity_curve=self.portfolio.equity_curve,
            trades=self.portfolio.get_completed_trades(),
            run_time_seconds=run_time,
            bars_processed=bars_processed
        )


async def run_backtest(request: BacktestRequest) -> BacktestResult:
    """
    Convenience function to run a backtest from a request.

    Args:
        request: BacktestRequest with configuration

    Returns:
        BacktestResult with performance data
    """
    # Import strategies
    from .strategies import SimpleRSIStrategy, MACDCrossoverStrategy

    # Map strategy names to classes
    strategy_map = {
        "simple_rsi": SimpleRSIStrategy,
        "macd_crossover": MACDCrossoverStrategy,
    }

    # Get strategy class
    strategy_class = strategy_map.get(request.strategy)
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {request.strategy}")

    # Instantiate strategy with params
    strategy = strategy_class(**request.strategy_params)

    # Create and run engine
    engine = BacktestEngine(
        strategy=strategy,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        position_size_pct=request.position_size_pct
    )

    return await engine.run(request.symbols)
