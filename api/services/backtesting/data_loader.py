"""
Historical data loader for backtesting.

Fetches OHLCV data from Alpaca API and organizes it for backtesting.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Bar:
    """A single OHLCV bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SymbolData:
    """Historical data for a single symbol."""
    symbol: str
    bars: List[Bar] = field(default_factory=list)

    @property
    def closes(self) -> List[float]:
        return [b.close for b in self.bars]

    @property
    def highs(self) -> List[float]:
        return [b.high for b in self.bars]

    @property
    def lows(self) -> List[float]:
        return [b.low for b in self.bars]

    @property
    def volumes(self) -> List[float]:
        return [b.volume for b in self.bars]


@dataclass
class BacktestData:
    """
    Container for all historical data needed for a backtest.

    Organizes data by timestamp for easy iteration.
    """
    symbols: List[str]
    start_date: date
    end_date: date
    symbol_data: Dict[str, SymbolData] = field(default_factory=dict)
    _timestamps: List[datetime] = field(default_factory=list)

    @property
    def timestamps(self) -> List[datetime]:
        """Get all unique timestamps in chronological order."""
        if not self._timestamps and self.symbol_data:
            # Collect all timestamps from all symbols
            all_timestamps = set()
            for sd in self.symbol_data.values():
                for bar in sd.bars:
                    all_timestamps.add(bar.timestamp)
            self._timestamps = sorted(all_timestamps)
        return self._timestamps

    def get_bars_at(self, timestamp: datetime) -> Dict[str, Bar]:
        """Get the bar for each symbol at a specific timestamp."""
        result = {}
        for symbol, sd in self.symbol_data.items():
            # Find bar at or before this timestamp
            for bar in reversed(sd.bars):
                if bar.timestamp <= timestamp:
                    result[symbol] = bar
                    break
        return result

    def get_lookback(self, symbol: str, timestamp: datetime, periods: int) -> List[float]:
        """Get the last N closing prices for a symbol up to timestamp."""
        if symbol not in self.symbol_data:
            return []

        closes = []
        for bar in self.symbol_data[symbol].bars:
            if bar.timestamp <= timestamp:
                closes.append(bar.close)

        return closes[-periods:] if len(closes) >= periods else closes


class DataLoader:
    """
    Loads historical data from Alpaca for backtesting.
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize the data loader.

        Args:
            alpaca_service: Optional AlpacaService instance. If None, creates one.
        """
        self.alpaca = alpaca_service

    async def _get_alpaca(self):
        """Lazy load alpaca service."""
        if self.alpaca is None:
            from services.alpaca_service import get_alpaca_service
            self.alpaca = get_alpaca_service()
        return self.alpaca

    async def load(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        timeframe: str = "1Day"
    ) -> BacktestData:
        """
        Load historical data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data
            timeframe: Bar timeframe ("1Day", "1Hour", etc.)

        Returns:
            BacktestData containing all historical bars
        """
        logger.info(f"Loading historical data for {len(symbols)} symbols from {start_date} to {end_date}")

        alpaca = await self._get_alpaca()
        data = BacktestData(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )

        for symbol in symbols:
            try:
                # Fetch bars from Alpaca
                bars = await alpaca.get_bars(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=datetime.combine(start_date, datetime.min.time()),
                    end=datetime.combine(end_date, datetime.max.time()),
                    limit=10000  # Get as much data as possible
                )

                # Convert to Bar objects
                symbol_bars = []
                for bar in bars:
                    symbol_bars.append(Bar(
                        timestamp=bar.get("timestamp") or bar.get("t"),
                        open=float(bar.get("open") or bar.get("o", 0)),
                        high=float(bar.get("high") or bar.get("h", 0)),
                        low=float(bar.get("low") or bar.get("l", 0)),
                        close=float(bar.get("close") or bar.get("c", 0)),
                        volume=float(bar.get("volume") or bar.get("v", 0))
                    ))

                data.symbol_data[symbol] = SymbolData(symbol=symbol, bars=symbol_bars)
                logger.info(f"Loaded {len(symbol_bars)} bars for {symbol}")

            except Exception as e:
                logger.error(f"Failed to load data for {symbol}: {e}")
                # Continue with other symbols

        logger.info(f"Loaded data for {len(data.symbol_data)} symbols, {len(data.timestamps)} timestamps")
        return data

    async def load_benchmark(self, start_date: date, end_date: date) -> SymbolData:
        """
        Load S&P 500 (SPY) data for benchmark comparison.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            SymbolData for SPY
        """
        data = await self.load(["SPY"], start_date, end_date)
        return data.symbol_data.get("SPY", SymbolData(symbol="SPY"))
