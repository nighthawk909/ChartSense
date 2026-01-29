"""
Simple RSI Strategy for backtesting.

This is a basic mean-reversion strategy that buys oversold
and sells overbought conditions.
"""

import logging
from datetime import datetime
from typing import List, Dict

from models.backtest import Signal
from ..portfolio import SimulatedPortfolio
from ..data_loader import BacktestData, Bar

logger = logging.getLogger(__name__)


class SimpleRSIStrategy:
    """
    Simple RSI strategy for backtesting.

    Rules:
    - BUY when RSI < oversold (default 30)
    - SELL when RSI > overbought (default 70)
    - One position per symbol

    This is a mean-reversion strategy that assumes:
    - Oversold conditions lead to price rebounds
    - Overbought conditions lead to price pullbacks
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
    ):
        """
        Initialize the RSI strategy.

        Args:
            rsi_period: Number of periods for RSI calculation
            oversold: RSI level below which to buy
            overbought: RSI level above which to sell
        """
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

        # Store params for reporting
        self.params = {
            "rsi_period": rsi_period,
            "oversold": oversold,
            "overbought": overbought,
        }

    async def generate_signals(
        self,
        bars: Dict[str, Bar],
        portfolio: SimulatedPortfolio,
        lookback_data: BacktestData,
        current_timestamp: datetime
    ) -> List[Signal]:
        """
        Generate trading signals based on RSI.

        Args:
            bars: Current bars for each symbol
            portfolio: Current portfolio state
            lookback_data: Historical data for lookback
            current_timestamp: Current timestamp

        Returns:
            List of signals to execute
        """
        signals = []

        for symbol, bar in bars.items():
            # Get historical closes for RSI calculation
            closes = lookback_data.get_lookback(symbol, current_timestamp, self.rsi_period + 1)

            if len(closes) < self.rsi_period + 1:
                continue  # Not enough data

            # Calculate RSI
            rsi = self._calculate_rsi(closes)

            if rsi is None:
                continue

            # Generate signals
            if rsi < self.oversold and symbol not in portfolio.positions:
                signals.append(Signal(
                    symbol=symbol,
                    action="BUY",
                    timestamp=current_timestamp,
                    reason=f"RSI={rsi:.1f} < {self.oversold} (oversold)",
                    confidence=1.0 - (rsi / 100)  # Lower RSI = higher confidence
                ))

            elif rsi > self.overbought and symbol in portfolio.positions:
                signals.append(Signal(
                    symbol=symbol,
                    action="SELL",
                    timestamp=current_timestamp,
                    reason=f"RSI={rsi:.1f} > {self.overbought} (overbought)",
                    confidence=rsi / 100  # Higher RSI = higher confidence to sell
                ))

        return signals

    def _calculate_rsi(self, closes: List[float]) -> float:
        """
        Calculate RSI from closing prices.

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        if len(closes) < 2:
            return None

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if not gains:
            return 50  # Neutral if no data

        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)

        if avg_loss == 0:
            return 100  # All gains

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
