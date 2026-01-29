"""
MACD Crossover Strategy for backtesting.

This is a trend-following strategy that trades MACD signal line crossovers.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from models.backtest import Signal
from ..portfolio import SimulatedPortfolio
from ..data_loader import BacktestData, Bar

logger = logging.getLogger(__name__)


class MACDCrossoverStrategy:
    """
    MACD Crossover Strategy for backtesting.

    Rules:
    - BUY when MACD line crosses ABOVE signal line (bullish crossover)
    - SELL when MACD line crosses BELOW signal line (bearish crossover)
    - One position per symbol

    This is a trend-following strategy that assumes:
    - Bullish crossovers indicate upward momentum
    - Bearish crossovers indicate downward momentum
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        """
        Initialize the MACD strategy.

        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        # Store params for reporting
        self.params = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
        }

        # Track previous MACD values for crossover detection
        self._prev_macd: Dict[str, Tuple[float, float]] = {}

    async def generate_signals(
        self,
        bars: Dict[str, Bar],
        portfolio: SimulatedPortfolio,
        lookback_data: BacktestData,
        current_timestamp: datetime
    ) -> List[Signal]:
        """
        Generate trading signals based on MACD crossovers.

        Args:
            bars: Current bars for each symbol
            portfolio: Current portfolio state
            lookback_data: Historical data for lookback
            current_timestamp: Current timestamp

        Returns:
            List of signals to execute
        """
        signals = []

        # Need enough data for slow EMA + signal period
        min_periods = self.slow_period + self.signal_period

        for symbol, bar in bars.items():
            # Get historical closes
            closes = lookback_data.get_lookback(symbol, current_timestamp, min_periods + 10)

            if len(closes) < min_periods:
                continue  # Not enough data

            # Calculate MACD
            macd_line, signal_line = self._calculate_macd(closes)

            if macd_line is None or signal_line is None:
                continue

            # Check for crossover
            prev = self._prev_macd.get(symbol)

            if prev is not None:
                prev_macd, prev_signal = prev

                # Bullish crossover: MACD crosses above signal
                if prev_macd <= prev_signal and macd_line > signal_line:
                    if symbol not in portfolio.positions:
                        signals.append(Signal(
                            symbol=symbol,
                            action="BUY",
                            timestamp=current_timestamp,
                            reason=f"MACD bullish crossover (MACD={macd_line:.2f} > Signal={signal_line:.2f})",
                            confidence=min(1.0, abs(macd_line - signal_line) * 10)
                        ))

                # Bearish crossover: MACD crosses below signal
                elif prev_macd >= prev_signal and macd_line < signal_line:
                    if symbol in portfolio.positions:
                        signals.append(Signal(
                            symbol=symbol,
                            action="SELL",
                            timestamp=current_timestamp,
                            reason=f"MACD bearish crossover (MACD={macd_line:.2f} < Signal={signal_line:.2f})",
                            confidence=min(1.0, abs(macd_line - signal_line) * 10)
                        ))

            # Store current values for next iteration
            self._prev_macd[symbol] = (macd_line, signal_line)

        return signals

    def _calculate_macd(self, closes: List[float]) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate MACD line and signal line.

        MACD Line = Fast EMA - Slow EMA
        Signal Line = EMA of MACD Line

        Returns:
            Tuple of (macd_line, signal_line)
        """
        if len(closes) < self.slow_period:
            return None, None

        # Calculate EMAs
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)

        if fast_ema is None or slow_ema is None:
            return None, None

        # Calculate MACD line history
        macd_history = []
        fast_emas = self._calculate_ema_series(closes, self.fast_period)
        slow_emas = self._calculate_ema_series(closes, self.slow_period)

        for i in range(len(slow_emas)):
            if i < len(fast_emas):
                macd_history.append(fast_emas[i] - slow_emas[i])

        if len(macd_history) < self.signal_period:
            return None, None

        # Current MACD line
        macd_line = fast_ema - slow_ema

        # Signal line is EMA of MACD history
        signal_line = self._calculate_ema(macd_history, self.signal_period)

        return macd_line, signal_line

    def _calculate_ema(self, values: List[float], period: int) -> Optional[float]:
        """Calculate exponential moving average."""
        if len(values) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period  # Start with SMA

        for value in values[period:]:
            ema = (value - ema) * multiplier + ema

        return ema

    def _calculate_ema_series(self, values: List[float], period: int) -> List[float]:
        """Calculate EMA series (all EMA values, not just the last one)."""
        if len(values) < period:
            return []

        multiplier = 2 / (period + 1)
        emas = []

        # Start with SMA
        ema = sum(values[:period]) / period
        emas.append(ema)

        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
            emas.append(ema)

        return emas
