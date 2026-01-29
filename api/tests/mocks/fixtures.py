"""
Price Data Fixtures for Testing
===============================
Provides sample price datasets for testing technical indicators and trading logic.

This module provides:
- PriceDataset: Named tuple for price data (opens, highs, lows, closes, volumes)
- Generate functions for different market conditions:
  - Uptrend: Consistent price increase
  - Downtrend: Consistent price decrease
  - Sideways: Range-bound movement
  - Volatile: High volatility (good for testing scalp mode)

Usage:
    from tests.mocks.fixtures import generate_uptrend_data, PriceDataset

    data = generate_uptrend_data(start_price=100.0, days=100)
    rsi = indicator_service.calculate_rsi(data.closes)
"""

import random
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class PriceDataset:
    """
    Container for OHLCV price data.

    Provides convenient access to price arrays for indicator testing.

    Attributes:
        opens: List of opening prices
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        volumes: List of trading volumes
        dates: List of date strings
    """
    opens: List[float]
    highs: List[float]
    lows: List[float]
    closes: List[float]
    volumes: List[int]
    dates: List[str]

    def __len__(self) -> int:
        return len(self.closes)

    def to_dict(self) -> Dict[str, List]:
        """Convert to dictionary format"""
        return {
            "opens": self.opens,
            "highs": self.highs,
            "lows": self.lows,
            "closes": self.closes,
            "volumes": self.volumes,
            "dates": self.dates,
        }

    def get_ohlcv_tuple(self) -> Tuple[List[float], List[float], List[float], List[float], List[int]]:
        """Return OHLCV as tuple for unpacking"""
        return self.opens, self.highs, self.lows, self.closes, self.volumes

    def slice(self, start: int, end: Optional[int] = None) -> 'PriceDataset':
        """Return a slice of the dataset"""
        return PriceDataset(
            opens=self.opens[start:end],
            highs=self.highs[start:end],
            lows=self.lows[start:end],
            closes=self.closes[start:end],
            volumes=self.volumes[start:end],
            dates=self.dates[start:end],
        )


def _generate_base_prices(
    start_price: float,
    days: int,
    trend: float,
    volatility: float,
    seed: Optional[int] = None,
) -> List[float]:
    """
    Generate base close prices with trend and volatility.

    Args:
        start_price: Starting price
        days: Number of days
        trend: Daily trend (e.g., 0.002 = 0.2% daily gain)
        volatility: Daily volatility as decimal
        seed: Random seed for reproducibility

    Returns:
        List of close prices
    """
    if seed is not None:
        random.seed(seed)

    prices = [start_price]
    price = start_price

    for _ in range(days - 1):
        # Random return with trend bias
        daily_return = trend + random.gauss(0, volatility)
        price = price * (1 + daily_return)
        # Ensure price stays positive
        price = max(price, 0.01)
        prices.append(round(price, 2))

    return prices


def _generate_ohlc_from_closes(
    closes: List[float],
    intraday_volatility: float = 0.01,
    seed: Optional[int] = None,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Generate Open, High, Low from close prices.

    Args:
        closes: List of close prices
        intraday_volatility: Intraday price range volatility
        seed: Random seed

    Returns:
        Tuple of (opens, highs, lows)
    """
    if seed is not None:
        random.seed(seed)

    opens = []
    highs = []
    lows = []

    for i, close in enumerate(closes):
        # Open is previous close with small gap
        if i == 0:
            open_price = close * (1 + random.gauss(0, 0.002))
        else:
            open_price = closes[i - 1] * (1 + random.gauss(0, 0.005))

        # High and low based on open-close range
        oc_range = abs(close - open_price)
        extra_range = close * intraday_volatility

        if close > open_price:
            # Bullish day
            high_price = close + random.uniform(0, extra_range)
            low_price = open_price - random.uniform(0, extra_range * 0.5)
        else:
            # Bearish day
            high_price = open_price + random.uniform(0, extra_range * 0.5)
            low_price = close - random.uniform(0, extra_range)

        # Ensure OHLC relationships
        high_price = max(high_price, open_price, close)
        low_price = min(low_price, open_price, close)
        low_price = max(low_price, 0.01)  # Keep positive

        opens.append(round(open_price, 2))
        highs.append(round(high_price, 2))
        lows.append(round(low_price, 2))

    return opens, highs, lows


def _generate_volumes(
    days: int,
    base_volume: int = 1000000,
    volatility: float = 0.3,
    seed: Optional[int] = None,
) -> List[int]:
    """
    Generate realistic trading volumes.

    Args:
        days: Number of days
        base_volume: Average daily volume
        volatility: Volume volatility
        seed: Random seed

    Returns:
        List of volumes
    """
    if seed is not None:
        random.seed(seed)

    volumes = []
    for _ in range(days):
        # Log-normal distribution for volumes
        vol = int(base_volume * math.exp(random.gauss(0, volatility)))
        vol = max(vol, 10000)  # Minimum volume
        volumes.append(vol)

    return volumes


def _generate_dates(days: int, start_date: Optional[datetime] = None) -> List[str]:
    """
    Generate date strings for price data.

    Args:
        days: Number of days
        start_date: Starting date (default: days ago from today)

    Returns:
        List of date strings
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    dates = []
    current = start_date
    for _ in range(days):
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def generate_uptrend_data(
    start_price: float = 100.0,
    days: int = 100,
    daily_return: float = 0.002,
    volatility: float = 0.01,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate price data showing a clear uptrend.

    Use for testing:
    - Bullish signal detection
    - Trend following strategies
    - Golden cross patterns

    Args:
        start_price: Starting price
        days: Number of days
        daily_return: Average daily return (0.002 = 0.2%)
        volatility: Daily volatility
        seed: Random seed for reproducibility

    Returns:
        PriceDataset with uptrend characteristics

    Example:
        >>> data = generate_uptrend_data(start_price=100, days=100)
        >>> data.closes[-1] > data.closes[0]  # Price increased
        True
    """
    closes = _generate_base_prices(start_price, days, daily_return, volatility, seed)
    opens, highs, lows = _generate_ohlc_from_closes(closes, volatility, seed)
    volumes = _generate_volumes(days, seed=seed)
    dates = _generate_dates(days)

    return PriceDataset(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
        dates=dates,
    )


def generate_downtrend_data(
    start_price: float = 100.0,
    days: int = 100,
    daily_return: float = -0.002,
    volatility: float = 0.01,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate price data showing a clear downtrend.

    Use for testing:
    - Bearish signal detection
    - Death cross patterns
    - Stop loss triggers

    Args:
        start_price: Starting price
        days: Number of days
        daily_return: Average daily return (-0.002 = -0.2%)
        volatility: Daily volatility
        seed: Random seed for reproducibility

    Returns:
        PriceDataset with downtrend characteristics

    Example:
        >>> data = generate_downtrend_data(start_price=100, days=100)
        >>> data.closes[-1] < data.closes[0]  # Price decreased
        True
    """
    closes = _generate_base_prices(start_price, days, daily_return, volatility, seed)
    opens, highs, lows = _generate_ohlc_from_closes(closes, volatility, seed)
    volumes = _generate_volumes(days, seed=seed)
    dates = _generate_dates(days)

    return PriceDataset(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
        dates=dates,
    )


def generate_sideways_data(
    center_price: float = 100.0,
    days: int = 100,
    range_pct: float = 0.05,
    volatility: float = 0.01,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate price data showing sideways/ranging movement.

    Use for testing:
    - Range-bound strategies
    - Bollinger Band squeeze
    - Low volatility detection

    Args:
        center_price: Center of the range
        days: Number of days
        range_pct: Range as percentage of price (+/- 5% = 10% total range)
        volatility: Daily volatility
        seed: Random seed for reproducibility

    Returns:
        PriceDataset with sideways characteristics

    Example:
        >>> data = generate_sideways_data(center_price=100, range_pct=0.05)
        >>> abs(data.closes[-1] - data.closes[0]) < center_price * 0.1
        True
    """
    if seed is not None:
        random.seed(seed)

    closes = []
    price = center_price

    for _ in range(days):
        # Mean-reversion to center price
        deviation = (price - center_price) / center_price
        mean_reversion = -deviation * 0.1  # Pull back toward center

        # Random walk with mean reversion
        daily_return = mean_reversion + random.gauss(0, volatility)
        price = price * (1 + daily_return)

        # Clamp to range
        upper = center_price * (1 + range_pct)
        lower = center_price * (1 - range_pct)
        price = max(lower, min(upper, price))

        closes.append(round(price, 2))

    opens, highs, lows = _generate_ohlc_from_closes(closes, volatility * 0.5, seed)
    volumes = _generate_volumes(days, base_volume=800000, seed=seed)
    dates = _generate_dates(days)

    return PriceDataset(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
        dates=dates,
    )


def generate_volatile_data(
    start_price: float = 100.0,
    days: int = 100,
    volatility: float = 0.03,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate highly volatile price data.

    Use for testing:
    - Scalp mode detection
    - High ATR scenarios
    - Volatility-based position sizing

    Args:
        start_price: Starting price
        days: Number of days
        volatility: Daily volatility (0.03 = 3% daily)
        seed: Random seed for reproducibility

    Returns:
        PriceDataset with high volatility characteristics

    Example:
        >>> data = generate_volatile_data(volatility=0.03)
        >>> # ATR should be higher than low volatility data
    """
    closes = _generate_base_prices(start_price, days, 0, volatility, seed)
    opens, highs, lows = _generate_ohlc_from_closes(closes, volatility * 1.5, seed)
    volumes = _generate_volumes(days, base_volume=2000000, volatility=0.5, seed=seed)
    dates = _generate_dates(days)

    return PriceDataset(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
        dates=dates,
    )


def generate_ohlcv_dataframe(
    start_price: float = 100.0,
    days: int = 100,
    trend: str = 'neutral',
    volatility: float = 0.015,
    seed: Optional[int] = None,
) -> Dict[str, List[float]]:
    """
    Generate OHLCV data as a dictionary suitable for indicator testing.

    Args:
        start_price: Starting price
        days: Number of data points
        trend: 'up', 'down', or 'neutral'
        volatility: Price volatility
        seed: Random seed

    Returns:
        Dictionary with keys: 'opens', 'highs', 'lows', 'closes', 'volumes'

    Example:
        >>> data = generate_ohlcv_dataframe(trend='up')
        >>> rsi = indicator_service.calculate_rsi(data['closes'])
    """
    trend_map = {
        'up': 0.002,
        'down': -0.002,
        'neutral': 0.0,
    }
    daily_return = trend_map.get(trend, 0.0)

    if trend == 'up':
        dataset = generate_uptrend_data(start_price, days, daily_return, volatility, seed)
    elif trend == 'down':
        dataset = generate_downtrend_data(start_price, days, daily_return, volatility, seed)
    else:
        dataset = generate_sideways_data(start_price, days, 0.03, volatility, seed)

    return {
        'opens': dataset.opens,
        'highs': dataset.highs,
        'lows': dataset.lows,
        'closes': dataset.closes,
        'volumes': [float(v) for v in dataset.volumes],  # Convert to float for consistency
    }


# ============================================================
# Specific Pattern Fixtures
# ============================================================

def generate_rsi_oversold_setup(
    days: int = 50,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate data that should produce RSI < 30 (oversold).

    Creates a sharp downtrend followed by consolidation.

    Returns:
        PriceDataset designed to trigger oversold RSI
    """
    if seed is not None:
        random.seed(seed)

    # Sharp decline for first 30 days
    decline_data = generate_downtrend_data(
        start_price=100.0,
        days=35,
        daily_return=-0.008,
        volatility=0.005,
        seed=seed,
    )

    # Mild recovery for remaining days
    if days > 35:
        recovery_data = generate_uptrend_data(
            start_price=decline_data.closes[-1],
            days=days - 35,
            daily_return=0.001,
            volatility=0.005,
            seed=seed,
        )

        return PriceDataset(
            opens=decline_data.opens + recovery_data.opens,
            highs=decline_data.highs + recovery_data.highs,
            lows=decline_data.lows + recovery_data.lows,
            closes=decline_data.closes + recovery_data.closes,
            volumes=decline_data.volumes + recovery_data.volumes,
            dates=_generate_dates(days),
        )

    return decline_data


def generate_rsi_overbought_setup(
    days: int = 50,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate data that should produce RSI > 70 (overbought).

    Creates a sharp uptrend followed by consolidation.

    Returns:
        PriceDataset designed to trigger overbought RSI
    """
    if seed is not None:
        random.seed(seed)

    # Sharp rally for first 30 days
    rally_data = generate_uptrend_data(
        start_price=100.0,
        days=35,
        daily_return=0.008,
        volatility=0.005,
        seed=seed,
    )

    # Mild pullback for remaining days
    if days > 35:
        pullback_data = generate_downtrend_data(
            start_price=rally_data.closes[-1],
            days=days - 35,
            daily_return=-0.001,
            volatility=0.005,
            seed=seed,
        )

        return PriceDataset(
            opens=rally_data.opens + pullback_data.opens,
            highs=rally_data.highs + pullback_data.highs,
            lows=rally_data.lows + pullback_data.lows,
            closes=rally_data.closes + pullback_data.closes,
            volumes=rally_data.volumes + pullback_data.volumes,
            dates=_generate_dates(days),
        )

    return rally_data


def generate_macd_bullish_crossover_setup(
    days: int = 60,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate data that should produce a bullish MACD crossover.

    Creates a downtrend followed by reversal.

    Returns:
        PriceDataset designed to trigger MACD bullish crossover
    """
    # Downtrend first half
    down_data = generate_downtrend_data(
        start_price=100.0,
        days=days // 2,
        daily_return=-0.003,
        volatility=0.008,
        seed=seed,
    )

    # Strong uptrend second half
    up_data = generate_uptrend_data(
        start_price=down_data.closes[-1],
        days=days - days // 2,
        daily_return=0.005,
        volatility=0.008,
        seed=seed,
    )

    return PriceDataset(
        opens=down_data.opens + up_data.opens,
        highs=down_data.highs + up_data.highs,
        lows=down_data.lows + up_data.lows,
        closes=down_data.closes + up_data.closes,
        volumes=down_data.volumes + up_data.volumes,
        dates=_generate_dates(days),
    )


def generate_bollinger_squeeze_setup(
    days: int = 50,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate data that should produce a Bollinger Band squeeze.

    Creates low volatility consolidation.

    Returns:
        PriceDataset with very low volatility
    """
    return generate_sideways_data(
        center_price=100.0,
        days=days,
        range_pct=0.02,  # Tight range
        volatility=0.003,  # Very low volatility
        seed=seed,
    )


def generate_golden_cross_setup(
    days: int = 250,
    seed: Optional[int] = None,
) -> PriceDataset:
    """
    Generate data that should produce a golden cross (50 SMA crossing above 200 SMA).

    Creates extended downtrend followed by strong recovery.

    Returns:
        PriceDataset designed for golden cross detection
    """
    # Extended downtrend
    down_data = generate_downtrend_data(
        start_price=120.0,
        days=150,
        daily_return=-0.001,
        volatility=0.01,
        seed=seed,
    )

    # Strong recovery
    up_data = generate_uptrend_data(
        start_price=down_data.closes[-1],
        days=100,
        daily_return=0.003,
        volatility=0.01,
        seed=seed,
    )

    return PriceDataset(
        opens=down_data.opens + up_data.opens,
        highs=down_data.highs + up_data.highs,
        lows=down_data.lows + up_data.lows,
        closes=down_data.closes + up_data.closes,
        volumes=down_data.volumes + up_data.volumes,
        dates=_generate_dates(days),
    )


# ============================================================
# Utility Functions
# ============================================================

def calculate_expected_rsi(closes: List[float], period: int = 14) -> float:
    """
    Calculate expected RSI for validation.

    Args:
        closes: List of close prices
        period: RSI period

    Returns:
        Expected RSI value
    """
    if len(closes) < period + 1:
        return 50.0

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0, c) for c in changes]
    losses = [abs(min(0, c)) for c in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_expected_sma(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate expected SMA for validation.

    Args:
        prices: List of prices
        period: SMA period

    Returns:
        Expected SMA value or None
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period
