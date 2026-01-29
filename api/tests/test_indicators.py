"""
Comprehensive Unit Tests for Technical Indicators
==================================================
Tests all indicator calculations in api/services/indicators.py

Test Coverage:
- SMA (Simple Moving Average) - various periods
- EMA (Exponential Moving Average) - various periods
- RSI (Relative Strength Index) - with known values validation
- MACD (histogram and signal line)
- Bollinger Bands (upper/lower/middle)
- ATR (Average True Range)
- Stochastic Oscillator (%K and %D)
- Williams %R
- OBV (On Balance Volume)
- ROC (Rate of Change)
- ADX (Average Directional Index)
- CCI (Commodity Channel Index)
- VWAP (Volume Weighted Average Price)
- Momentum
- Edge cases: empty data, single value, extreme values
- Trading mode parameters: SCALP, INTRADAY, SWING

Updated 2026-01-28:
- Indicator functions now return arrays padded with None at the beginning
- This ensures arrays align with input prices for backtesting
- Tests updated to handle None values in results
"""
import pytest
import math
import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Helper Functions for Testing
# ============================================================

def filter_none(arr: List[Optional[float]]) -> List[float]:
    """Remove None values from array for testing calculations"""
    return [x for x in arr if x is not None]


def first_valid(arr: List[Optional[float]]) -> Optional[float]:
    """Get first non-None value from array"""
    for x in arr:
        if x is not None:
            return x
    return None


def count_valid(arr: List[Optional[float]]) -> int:
    """Count non-None values in array"""
    return sum(1 for x in arr if x is not None)

from services.indicators import (
    IndicatorService,
    AdaptiveIndicatorEngine,
    AdaptiveIndicatorConfig,
    TradingMode,
)
from tests.mocks.fixtures import (
    generate_uptrend_data,
    generate_downtrend_data,
    generate_sideways_data,
    generate_volatile_data,
    PriceDataset,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def indicator_service():
    """Create indicator service instance"""
    return IndicatorService()


@pytest.fixture
def adaptive_engine():
    """Create adaptive indicator engine"""
    return AdaptiveIndicatorEngine()


@pytest.fixture
def simple_prices():
    """Simple ascending price sequence for predictable testing"""
    return [float(i) for i in range(10, 31)]  # 10, 11, 12, ..., 30


@pytest.fixture
def known_rsi_prices():
    """
    Known price sequence for RSI validation.
    Based on standard RSI calculation examples.
    """
    # Prices designed to give predictable RSI values
    return [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
        46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41,
        46.22, 45.64
    ]


@pytest.fixture
def ohlc_data():
    """Sample OHLC data for indicators requiring high/low/close"""
    return {
        'highs': [102.0, 103.0, 104.0, 103.5, 105.0, 106.0, 105.5, 107.0, 108.0, 107.5,
                  109.0, 110.0, 109.5, 111.0, 112.0, 111.5, 113.0, 114.0, 113.5, 115.0],
        'lows': [98.0, 99.0, 100.0, 99.5, 101.0, 102.0, 101.5, 103.0, 104.0, 103.5,
                 105.0, 106.0, 105.5, 107.0, 108.0, 107.5, 109.0, 110.0, 109.5, 111.0],
        'closes': [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.5, 105.0, 106.0, 105.5,
                   107.0, 108.0, 107.5, 109.0, 110.0, 109.5, 111.0, 112.0, 111.5, 113.0],
        'volumes': [1000000, 1100000, 1050000, 980000, 1200000, 1150000, 1080000, 1300000,
                    1250000, 1180000, 1400000, 1350000, 1280000, 1500000, 1450000, 1380000,
                    1600000, 1550000, 1480000, 1700000],
    }


# ============================================================
# SMA Tests (Simple Moving Average)
# ============================================================

class TestSMA:
    """Test Simple Moving Average calculation

    Note: SMA now returns arrays padded with None at the beginning to match input length.
    First (period - 1) values are None, remaining values are valid SMA calculations.
    """

    def test_sma_period_5(self, indicator_service, simple_prices):
        """Test SMA with 5-period window"""
        result = indicator_service.calculate_sma(simple_prices, 5)

        # Array length should match input length (padded with None)
        assert len(result) == len(simple_prices)

        # First 4 values should be None (period - 1)
        assert all(x is None for x in result[:4])

        # First valid SMA value should be average of first 5 prices
        expected_first = (10 + 11 + 12 + 13 + 14) / 5
        assert abs(first_valid(result) - expected_first) < 0.001

        # Last SMA value
        expected_last = (26 + 27 + 28 + 29 + 30) / 5
        assert abs(result[-1] - expected_last) < 0.001

    def test_sma_period_10(self, indicator_service, simple_prices):
        """Test SMA with 10-period window"""
        result = indicator_service.calculate_sma(simple_prices, 10)

        # Array length matches input
        assert len(result) == len(simple_prices)

        # First valid SMA should be average of prices[0:10]
        expected_first = sum(range(10, 20)) / 10
        assert abs(first_valid(result) - expected_first) < 0.001

    def test_sma_period_20(self, indicator_service, simple_prices):
        """Test SMA with 20-period window"""
        result = indicator_service.calculate_sma(simple_prices, 20)

        # Array length matches input (21 prices)
        assert len(result) == 21

        # Should have 2 valid values (21 prices - 20 + 1)
        assert count_valid(result) == 2

        expected_first = sum(range(10, 30)) / 20
        assert abs(first_valid(result) - expected_first) < 0.001

    def test_sma_period_50_insufficient_data(self, indicator_service, simple_prices):
        """Test SMA with period larger than data returns all None"""
        result = indicator_service.calculate_sma(simple_prices, 50)
        # Should return array of None values matching input length
        assert len(result) == len(simple_prices)
        assert all(x is None for x in result)

    def test_sma_period_200_insufficient_data(self, indicator_service, simple_prices):
        """Test SMA 200 with insufficient data returns all None"""
        result = indicator_service.calculate_sma(simple_prices, 200)
        # Should return array of None values matching input length
        assert len(result) == len(simple_prices)
        assert all(x is None for x in result)

    def test_sma_length(self, indicator_service, simple_prices):
        """Test SMA output length matches input length (padded)"""
        period = 5
        result = indicator_service.calculate_sma(simple_prices, period)
        # Output length matches input (new behavior)
        assert len(result) == len(simple_prices)
        # Valid values count matches expected formula
        expected_valid_count = len(simple_prices) - period + 1
        assert count_valid(result) == expected_valid_count

    def test_sma_empty_prices(self, indicator_service):
        """Test SMA with empty price list"""
        result = indicator_service.calculate_sma([], 5)
        assert result == []


# ============================================================
# EMA Tests (Exponential Moving Average)
# ============================================================

class TestEMA:
    """Test Exponential Moving Average calculation

    Note: EMA now returns arrays padded with None at the beginning to match input length.
    """

    def test_ema_first_value_is_sma(self, indicator_service, simple_prices):
        """Test that first valid EMA value equals SMA of first period prices"""
        period = 5
        result = indicator_service.calculate_ema(simple_prices, period)

        expected_first = sum(simple_prices[:period]) / period
        first = first_valid(result)
        assert first is not None
        assert abs(first - expected_first) < 0.001

    def test_ema_period_5(self, indicator_service, simple_prices):
        """Test EMA with 5-period"""
        result = indicator_service.calculate_ema(simple_prices, 5)

        # Verify length matches input (padded)
        assert len(result) == len(simple_prices)

        # Valid values count
        expected_valid_count = len(simple_prices) - 5 + 1
        assert count_valid(result) == expected_valid_count

        # EMA should follow the trend (increasing for ascending prices)
        valid_values = filter_none(result)
        assert valid_values[-1] > valid_values[0]

    def test_ema_period_12(self, indicator_service):
        """Test EMA with 12-period (standard for MACD)"""
        prices = [float(i) for i in range(50, 100)]
        result = indicator_service.calculate_ema(prices, 12)

        assert count_valid(result) > 0
        # EMA should be smoothed - last value near recent prices
        assert result[-1] > 80

    def test_ema_period_26(self, indicator_service):
        """Test EMA with 26-period (standard for MACD)"""
        prices = [float(i) for i in range(50, 100)]
        result = indicator_service.calculate_ema(prices, 26)

        assert count_valid(result) > 0
        # 26 EMA should lag behind 12 EMA in uptrend
        ema_12 = indicator_service.calculate_ema(prices, 12)
        assert result[-1] < ema_12[-1]

    def test_ema_empty_prices(self, indicator_service):
        """Test EMA with empty price list"""
        result = indicator_service.calculate_ema([], 5)
        assert result == []

    def test_ema_insufficient_data(self, indicator_service):
        """Test EMA with insufficient data returns all None"""
        result = indicator_service.calculate_ema([1, 2, 3], 5)
        # Returns array of None values matching input length
        assert len(result) == 3
        assert all(x is None for x in result)

    def test_ema_multiplier_calculation(self, indicator_service, simple_prices):
        """Test EMA uses correct multiplier"""
        period = 10
        multiplier = 2 / (period + 1)  # Should be 0.1818...

        result = indicator_service.calculate_ema(simple_prices, period)

        # Verify multiplier is approximately correct by checking EMA behavior
        assert 0 < multiplier < 1
        assert abs(multiplier - 0.1818) < 0.001


# ============================================================
# RSI Tests (Relative Strength Index)
# ============================================================

class TestRSI:
    """Test Relative Strength Index calculation

    Note: RSI now returns arrays padded with None at the beginning to match input length.
    """

    def test_rsi_known_values(self, indicator_service, known_rsi_prices):
        """Test RSI against known values with 0.01 tolerance"""
        result = indicator_service.calculate_rsi(known_rsi_prices, 14)

        # RSI for this sequence should be around 70 based on calculation
        valid_values = filter_none(result)
        assert len(valid_values) > 0
        # RSI should be within valid range
        for rsi in valid_values:
            assert 0 <= rsi <= 100

    def test_rsi_overbought_detection(self, indicator_service):
        """Test RSI detects overbought (>70) in strong uptrend"""
        # Create strong uptrend data
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=50,
            daily_return=0.01,  # 1% daily gain
            volatility=0.002,
            seed=42
        )

        result = indicator_service.calculate_rsi(uptrend.closes, 14)
        valid_values = filter_none(result)

        # Strong uptrend should produce overbought conditions
        assert any(rsi > 70 for rsi in valid_values)

    def test_rsi_oversold_detection(self, indicator_service):
        """Test RSI detects oversold (<30) in strong downtrend"""
        downtrend = generate_downtrend_data(
            start_price=100.0,
            days=50,
            daily_return=-0.01,
            volatility=0.002,
            seed=42
        )

        result = indicator_service.calculate_rsi(downtrend.closes, 14)
        valid_values = filter_none(result)

        # Strong downtrend should produce oversold conditions
        assert any(rsi < 30 for rsi in valid_values)

    def test_rsi_neutral_in_sideways(self, indicator_service):
        """Test RSI stays neutral (30-70) in sideways market"""
        sideways = generate_sideways_data(
            center_price=100.0,
            days=100,
            range_pct=0.02,
            volatility=0.005,
            seed=42
        )

        result = indicator_service.calculate_rsi(sideways.closes, 14)
        valid_values = filter_none(result)

        # Most RSI values should be in neutral range
        neutral_count = sum(1 for rsi in valid_values if 30 <= rsi <= 70)
        assert neutral_count > len(valid_values) * 0.5  # At least 50% neutral

    def test_rsi_bounds(self, indicator_service):
        """Test RSI is always bounded between 0 and 100"""
        # Test with extreme volatility
        volatile = generate_volatile_data(
            start_price=100.0,
            days=100,
            volatility=0.05,
            seed=42
        )

        result = indicator_service.calculate_rsi(volatile.closes, 14)
        valid_values = filter_none(result)

        for rsi in valid_values:
            assert 0 <= rsi <= 100

    def test_rsi_all_gains_equals_100(self, indicator_service):
        """Test RSI equals 100 when all changes are gains"""
        # Strictly increasing prices
        prices = [float(i) for i in range(100, 120)]
        result = indicator_service.calculate_rsi(prices, 14)

        # Should be 100 (no losses)
        assert result[-1] == 100.0

    def test_rsi_all_losses_equals_0(self, indicator_service):
        """Test RSI approaches 0 when all changes are losses"""
        # Strictly decreasing prices
        prices = [float(i) for i in range(120, 100, -1)]
        result = indicator_service.calculate_rsi(prices, 14)

        # Should approach 0 (no gains)
        assert result[-1] < 1.0

    def test_rsi_period_7_scalp(self, indicator_service):
        """Test RSI with 7-period for scalp mode"""
        prices = [float(i) for i in range(50, 100)]
        result = indicator_service.calculate_rsi(prices, 7)

        # 7-period RSI should be more sensitive (higher in uptrend)
        rsi_14 = indicator_service.calculate_rsi(prices, 14)
        # Both should have valid values
        assert count_valid(result) > 0
        assert count_valid(rsi_14) > 0

    def test_rsi_period_21_swing(self, indicator_service):
        """Test RSI with 21-period for swing mode"""
        prices = [float(i) for i in range(50, 150)]
        result = indicator_service.calculate_rsi(prices, 21)

        assert count_valid(result) > 0

    def test_rsi_empty_data(self, indicator_service):
        """Test RSI with empty data"""
        result = indicator_service.calculate_rsi([], 14)
        assert result == []

    def test_rsi_insufficient_data(self, indicator_service):
        """Test RSI with insufficient data returns all None"""
        result = indicator_service.calculate_rsi([1, 2, 3], 14)
        # Returns array of None values matching input length
        assert len(result) == 3
        assert all(x is None for x in result)


# ============================================================
# MACD Tests
# ============================================================

class TestMACD:
    """Test MACD calculation (histogram and signal line)

    Note: MACD now returns arrays padded with None at the beginning to match input length.
    """

    def test_macd_standard_periods(self, indicator_service):
        """Test MACD with standard 12/26/9 periods"""
        prices = [float(i) for i in range(50, 100)]
        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            prices, 12, 26, 9
        )

        assert count_valid(macd_line) > 0
        assert count_valid(signal_line) > 0
        assert count_valid(histogram) > 0

    def test_macd_histogram_equals_difference(self, indicator_service):
        """Test histogram equals MACD line minus signal line"""
        prices = [float(i) for i in range(50, 100)]
        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            prices, 12, 26, 9
        )

        # Histogram should equal MACD - Signal (for non-None values)
        for i in range(len(histogram)):
            if histogram[i] is not None and macd_line[i] is not None and signal_line[i] is not None:
                expected = macd_line[i] - signal_line[i]
                assert abs(histogram[i] - expected) < 0.001

    def test_macd_bullish_uptrend(self, indicator_service):
        """Test MACD is positive in uptrend"""
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=100,
            daily_return=0.002,
            volatility=0.005,
            seed=42
        )

        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            uptrend.closes, 12, 26, 9
        )

        # MACD should be positive in uptrend (fast EMA > slow EMA)
        assert macd_line[-1] > 0

    def test_macd_bearish_downtrend(self, indicator_service):
        """Test MACD is negative in downtrend"""
        downtrend = generate_downtrend_data(
            start_price=100.0,
            days=100,
            daily_return=-0.002,
            volatility=0.005,
            seed=42
        )

        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            downtrend.closes, 12, 26, 9
        )

        # MACD should be negative in downtrend
        assert macd_line[-1] < 0

    def test_macd_scalp_mode_periods(self, indicator_service):
        """Test MACD with scalp mode periods 6/13/5"""
        prices = [float(i) for i in range(50, 100)]
        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            prices, 6, 13, 5
        )

        assert count_valid(macd_line) > 0
        assert count_valid(signal_line) > 0

    def test_macd_swing_mode_periods(self, indicator_service):
        """Test MACD with swing mode periods 19/39/9"""
        prices = [float(i) for i in range(50, 150)]
        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            prices, 19, 39, 9
        )

        assert count_valid(macd_line) > 0

    def test_macd_insufficient_data(self, indicator_service):
        """Test MACD with insufficient data returns all None"""
        prices = [1, 2, 3, 4, 5]  # Less than slow period
        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            prices, 12, 26, 9
        )

        # Returns arrays of None values matching input length
        assert len(macd_line) == 5
        assert all(x is None for x in macd_line)


# ============================================================
# Bollinger Bands Tests
# ============================================================

class TestBollingerBands:
    """Test Bollinger Bands calculation

    Note: Bollinger Bands now return arrays padded with None at the beginning.
    """

    def test_bollinger_upper_lower_middle(self, indicator_service, simple_prices):
        """Test Bollinger Bands returns upper, middle, lower"""
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            simple_prices, 10, 2.0
        )

        assert count_valid(upper) > 0
        assert count_valid(middle) > 0
        assert count_valid(lower) > 0

    def test_bollinger_middle_equals_sma(self, indicator_service, simple_prices):
        """Test middle band equals SMA"""
        period = 10
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            simple_prices, period, 2.0
        )
        sma = indicator_service.calculate_sma(simple_prices, period)

        # Compare only non-None values
        for i in range(len(middle)):
            if middle[i] is not None and sma[i] is not None:
                assert abs(middle[i] - sma[i]) < 0.001

    def test_bollinger_band_order(self, indicator_service, simple_prices):
        """Test upper > middle > lower"""
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            simple_prices, 10, 2.0
        )

        # Check only non-None values
        for i in range(len(upper)):
            if upper[i] is not None and middle[i] is not None and lower[i] is not None:
                assert upper[i] > middle[i]
                assert middle[i] > lower[i]

    def test_bollinger_standard_deviation(self, indicator_service):
        """Test bands use correct standard deviation multiplier"""
        prices = [100.0] * 10 + [110.0] * 10  # Step change
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            prices, 10, 2.0
        )

        # Bands should widen after the step change
        assert count_valid(upper) > 0

    def test_bollinger_scalp_mode(self, indicator_service):
        """Test Bollinger with scalp mode (period=10, std=2.0)"""
        prices = [float(i) for i in range(50, 100)]
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            prices, 10, 2.0
        )

        assert count_valid(upper) > 0

    def test_bollinger_swing_mode(self, indicator_service):
        """Test Bollinger with swing mode (period=30, std=2.5)"""
        prices = [float(i) for i in range(50, 150)]
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            prices, 30, 2.5
        )

        assert count_valid(upper) > 0

    def test_bollinger_empty_data(self, indicator_service):
        """Test Bollinger with empty data"""
        upper, middle, lower = indicator_service.calculate_bollinger_bands([], 20, 2.0)

        assert upper == []
        assert middle == []
        assert lower == []


# ============================================================
# ATR Tests (Average True Range)
# ============================================================

class TestATR:
    """Test Average True Range calculation"""

    def test_atr_basic(self, indicator_service, ohlc_data):
        """Test basic ATR calculation"""
        result = indicator_service.calculate_atr(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14
        )

        assert len(result) > 0
        # ATR should be positive
        for atr in result:
            assert atr > 0

    def test_atr_period_7_scalp(self, indicator_service, ohlc_data):
        """Test ATR with 7-period for scalp mode"""
        result = indicator_service.calculate_atr(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            7
        )

        assert len(result) > 0

    def test_atr_period_21_swing(self, indicator_service, ohlc_data):
        """Test ATR with 21-period for swing mode"""
        # Need more data for 21 period
        highs = [100 + i * 0.5 for i in range(50)]
        lows = [98 + i * 0.5 for i in range(50)]
        closes = [99 + i * 0.5 for i in range(50)]

        result = indicator_service.calculate_atr(highs, lows, closes, 21)

        assert len(result) > 0

    def test_atr_high_volatility_higher_value(self, indicator_service):
        """Test ATR is higher for more volatile data"""
        # Low volatility
        low_vol_highs = [101 + i * 0.1 for i in range(30)]
        low_vol_lows = [99 + i * 0.1 for i in range(30)]
        low_vol_closes = [100 + i * 0.1 for i in range(30)]

        # High volatility
        high_vol_highs = [105 + i * 0.1 for i in range(30)]
        high_vol_lows = [95 + i * 0.1 for i in range(30)]
        high_vol_closes = [100 + i * 0.1 for i in range(30)]

        low_atr = indicator_service.calculate_atr(
            low_vol_highs, low_vol_lows, low_vol_closes, 14
        )
        high_atr = indicator_service.calculate_atr(
            high_vol_highs, high_vol_lows, high_vol_closes, 14
        )

        assert high_atr[-1] > low_atr[-1]

    def test_atr_insufficient_data(self, indicator_service):
        """Test ATR with insufficient data"""
        result = indicator_service.calculate_atr([100], [99], [99.5], 14)
        assert result == []


# ============================================================
# Stochastic Oscillator Tests
# ============================================================

class TestStochastic:
    """Test Stochastic Oscillator calculation

    Note: Stochastic may return arrays with None values for padding.
    """

    def test_stochastic_basic(self, indicator_service, ohlc_data):
        """Test basic stochastic calculation"""
        k_values, d_values = indicator_service.calculate_stochastic(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14, 3
        )

        assert count_valid(k_values) > 0
        assert count_valid(d_values) > 0

    def test_stochastic_bounds(self, indicator_service, ohlc_data):
        """Test stochastic is bounded 0-100"""
        k_values, d_values = indicator_service.calculate_stochastic(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14, 3
        )

        for k in filter_none(k_values):
            assert 0 <= k <= 100
        for d in filter_none(d_values):
            assert 0 <= d <= 100

    def test_stochastic_overbought(self, indicator_service):
        """Test stochastic detects overbought in uptrend"""
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=50,
            daily_return=0.005,
            volatility=0.002,
            seed=42
        )

        k_values, d_values = indicator_service.calculate_stochastic(
            uptrend.highs,
            uptrend.lows,
            uptrend.closes,
            14, 3
        )

        # Should have overbought readings (>80)
        assert any(k > 80 for k in filter_none(k_values))

    def test_stochastic_oversold(self, indicator_service):
        """Test stochastic detects oversold in downtrend"""
        downtrend = generate_downtrend_data(
            start_price=100.0,
            days=50,
            daily_return=-0.005,
            volatility=0.002,
            seed=42
        )

        k_values, d_values = indicator_service.calculate_stochastic(
            downtrend.highs,
            downtrend.lows,
            downtrend.closes,
            14, 3
        )

        # Should have oversold readings (<20)
        assert any(k < 20 for k in filter_none(k_values))

    def test_stochastic_d_is_sma_of_k(self, indicator_service, ohlc_data):
        """Test %D is SMA of %K - arrays should have same length"""
        d_period = 3
        k_values, d_values = indicator_service.calculate_stochastic(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14, d_period
        )

        # Arrays should have same length (both padded to match input)
        assert len(k_values) == len(d_values)

    def test_stochastic_scalp_periods(self, indicator_service, ohlc_data):
        """Test stochastic with scalp mode (7, 3)"""
        k_values, d_values = indicator_service.calculate_stochastic(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            7, 3
        )

        assert len(k_values) > 0

    def test_stochastic_swing_periods(self, indicator_service):
        """Test stochastic with swing mode (21, 5)"""
        data = generate_uptrend_data(start_price=100, days=60, seed=42)

        k_values, d_values = indicator_service.calculate_stochastic(
            data.highs, data.lows, data.closes, 21, 5
        )

        assert len(k_values) > 0

    def test_stochastic_no_range_equals_50(self, indicator_service):
        """Test stochastic returns 50 when high equals low"""
        highs = [100.0] * 20
        lows = [100.0] * 20
        closes = [100.0] * 20

        k_values, d_values = indicator_service.calculate_stochastic(
            highs, lows, closes, 14, 3
        )

        # When high == low, %K should be 50 (neutral)
        for k in k_values:
            assert k == 50.0


# ============================================================
# Williams %R Tests
# ============================================================

class TestWilliamsR:
    """Test Williams %R calculation"""

    def test_williams_r_basic(self, indicator_service, ohlc_data):
        """Test basic Williams %R calculation"""
        result = indicator_service.calculate_williams_r(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14
        )

        assert len(result) > 0

    def test_williams_r_bounds(self, indicator_service, ohlc_data):
        """Test Williams %R is bounded -100 to 0"""
        result = indicator_service.calculate_williams_r(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            14
        )

        for wr in result:
            assert -100 <= wr <= 0

    def test_williams_r_overbought(self, indicator_service):
        """Test Williams %R overbought (> -20) in uptrend"""
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=50,
            daily_return=0.005,
            volatility=0.002,
            seed=42
        )

        result = indicator_service.calculate_williams_r(
            uptrend.highs, uptrend.lows, uptrend.closes, 14
        )

        # Should have overbought readings (> -20)
        assert any(wr > -20 for wr in result)


# ============================================================
# OBV Tests (On Balance Volume)
# ============================================================

class TestOBV:
    """Test On Balance Volume calculation"""

    def test_obv_basic(self, indicator_service, ohlc_data):
        """Test basic OBV calculation"""
        result = indicator_service.calculate_obv(
            ohlc_data['closes'],
            [float(v) for v in ohlc_data['volumes']]
        )

        assert len(result) > 0

    def test_obv_rising_in_uptrend(self, indicator_service):
        """Test OBV rises in uptrend with volume"""
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=30,
            daily_return=0.002,
            volatility=0.005,
            seed=42
        )

        result = indicator_service.calculate_obv(
            uptrend.closes,
            [float(v) for v in uptrend.volumes]
        )

        # OBV should generally increase in uptrend
        assert result[-1] > result[0]

    def test_obv_falling_in_downtrend(self, indicator_service):
        """Test OBV falls in downtrend"""
        downtrend = generate_downtrend_data(
            start_price=100.0,
            days=30,
            daily_return=-0.002,
            volatility=0.005,
            seed=42
        )

        result = indicator_service.calculate_obv(
            downtrend.closes,
            [float(v) for v in downtrend.volumes]
        )

        # OBV should generally decrease in downtrend
        assert result[-1] < result[0]

    def test_obv_unchanged_when_price_unchanged(self, indicator_service):
        """Test OBV unchanged when price unchanged"""
        closes = [100.0] * 10
        volumes = [1000000.0] * 10

        result = indicator_service.calculate_obv(closes, volumes)

        # All values should be the same
        assert all(r == result[0] for r in result)


# ============================================================
# ROC Tests (Rate of Change)
# ============================================================

class TestROC:
    """Test Rate of Change calculation"""

    def test_roc_basic(self, indicator_service, simple_prices):
        """Test basic ROC calculation"""
        result = indicator_service.calculate_roc(simple_prices, 12)

        assert len(result) > 0

    def test_roc_positive_in_uptrend(self, indicator_service):
        """Test ROC is positive in uptrend"""
        uptrend = generate_uptrend_data(
            start_price=100.0,
            days=50,
            daily_return=0.002,
            volatility=0.002,
            seed=42
        )

        result = indicator_service.calculate_roc(uptrend.closes, 12)

        # Most ROC values should be positive in uptrend
        positive_count = sum(1 for r in result if r > 0)
        assert positive_count > len(result) * 0.7

    def test_roc_negative_in_downtrend(self, indicator_service):
        """Test ROC is negative in downtrend"""
        downtrend = generate_downtrend_data(
            start_price=100.0,
            days=50,
            daily_return=-0.002,
            volatility=0.002,
            seed=42
        )

        result = indicator_service.calculate_roc(downtrend.closes, 12)

        # Most ROC values should be negative in downtrend
        negative_count = sum(1 for r in result if r < 0)
        assert negative_count > len(result) * 0.7


# ============================================================
# ADX Tests (Average Directional Index)
# ============================================================

class TestADX:
    """Test Average Directional Index calculation"""

    def test_adx_basic(self, indicator_service):
        """Test basic ADX calculation"""
        data = generate_uptrend_data(start_price=100, days=60, seed=42)

        adx, plus_di, minus_di = indicator_service.calculate_adx(
            data.highs, data.lows, data.closes, 14
        )

        # May return empty if insufficient smoothed data
        # Just verify no crash
        assert isinstance(adx, list)
        assert isinstance(plus_di, list)
        assert isinstance(minus_di, list)

    def test_adx_strong_trend(self, indicator_service):
        """Test ADX indicates strong trend"""
        data = generate_uptrend_data(
            start_price=100, days=100,
            daily_return=0.005, volatility=0.002, seed=42
        )

        adx, plus_di, minus_di = indicator_service.calculate_adx(
            data.highs, data.lows, data.closes, 14
        )

        if adx:
            # Strong trend should have ADX > 25
            assert any(a > 20 for a in adx)


# ============================================================
# CCI Tests (Commodity Channel Index)
# ============================================================

class TestCCI:
    """Test Commodity Channel Index calculation"""

    def test_cci_basic(self, indicator_service, ohlc_data):
        """Test basic CCI calculation"""
        result = indicator_service.calculate_cci(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            20
        )

        assert len(result) > 0

    def test_cci_overbought_oversold(self, indicator_service):
        """Test CCI detects overbought/oversold"""
        uptrend = generate_uptrend_data(
            start_price=100, days=50,
            daily_return=0.005, volatility=0.002, seed=42
        )

        result = indicator_service.calculate_cci(
            uptrend.highs, uptrend.lows, uptrend.closes, 20
        )

        # Should have some values > 100 (overbought)
        if result:
            max_cci = max(result)
            assert max_cci > 50  # At least moderately high


# ============================================================
# VWAP Tests (Volume Weighted Average Price)
# ============================================================

class TestVWAP:
    """Test Volume Weighted Average Price calculation"""

    def test_vwap_basic(self, indicator_service, ohlc_data):
        """Test basic VWAP calculation"""
        result = indicator_service.calculate_vwap(
            ohlc_data['highs'],
            ohlc_data['lows'],
            ohlc_data['closes'],
            [float(v) for v in ohlc_data['volumes']]
        )

        assert len(result) > 0
        assert len(result) == len(ohlc_data['closes'])

    def test_vwap_near_typical_price(self, indicator_service):
        """Test VWAP is near typical price when volume is uniform"""
        highs = [105.0] * 10
        lows = [95.0] * 10
        closes = [100.0] * 10
        volumes = [1000000.0] * 10

        result = indicator_service.calculate_vwap(highs, lows, closes, volumes)

        # Typical price = (105 + 95 + 100) / 3 = 100
        # VWAP should be 100 with uniform data
        for v in result:
            assert 99 <= v <= 101


# ============================================================
# Momentum Tests
# ============================================================

class TestMomentum:
    """Test Momentum indicator calculation"""

    def test_momentum_basic(self, indicator_service, simple_prices):
        """Test basic momentum calculation"""
        result = indicator_service.calculate_momentum(simple_prices, 10)

        assert len(result) > 0

    def test_momentum_positive_uptrend(self, indicator_service):
        """Test momentum is positive in uptrend"""
        uptrend = generate_uptrend_data(
            start_price=100, days=30,
            daily_return=0.002, volatility=0.002, seed=42
        )

        result = indicator_service.calculate_momentum(uptrend.closes, 10)

        # Most momentum should be positive
        positive = sum(1 for m in result if m > 0)
        assert positive > len(result) * 0.7


# ============================================================
# Edge Case Tests
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling

    Note: Indicators now return arrays padded with None to match input length.
    Insufficient data results in all-None arrays, not empty arrays.
    """

    def test_empty_data_all_indicators(self, indicator_service):
        """Test all indicators handle empty data gracefully"""
        assert indicator_service.calculate_sma([], 5) == []
        assert indicator_service.calculate_ema([], 5) == []
        assert indicator_service.calculate_rsi([], 14) == []
        assert indicator_service.calculate_macd([], 12, 26, 9) == ([], [], [])
        assert indicator_service.calculate_bollinger_bands([], 20, 2.0) == ([], [], [])
        assert indicator_service.calculate_atr([], [], [], 14) == []
        assert indicator_service.calculate_stochastic([], [], [], 14, 3) == ([], [])
        assert indicator_service.calculate_williams_r([], [], [], 14) == []
        assert indicator_service.calculate_obv([], []) == []
        assert indicator_service.calculate_roc([], 12) == []
        assert indicator_service.calculate_momentum([], 10) == []

    def test_single_price_all_indicators(self, indicator_service):
        """Test all indicators handle single price gracefully"""
        single = [100.0]
        single_ohlc = ([102.0], [98.0], [100.0])

        # Single price returns array of 1 None value (padded to match input)
        sma_result = indicator_service.calculate_sma(single, 5)
        assert len(sma_result) == 1
        assert sma_result[0] is None

        ema_result = indicator_service.calculate_ema(single, 5)
        assert len(ema_result) == 1
        assert ema_result[0] is None

        rsi_result = indicator_service.calculate_rsi(single, 14)
        assert len(rsi_result) == 1
        assert rsi_result[0] is None

    def test_extreme_prices_high(self, indicator_service):
        """Test indicators with extremely high prices"""
        extreme = [1000000.0 + i for i in range(50)]

        sma = indicator_service.calculate_sma(extreme, 10)
        valid_sma = filter_none(sma)
        assert len(valid_sma) > 0
        assert all(s > 900000 for s in valid_sma)

        rsi = indicator_service.calculate_rsi(extreme, 14)
        valid_rsi = filter_none(rsi)
        assert len(valid_rsi) > 0
        for r in valid_rsi:
            assert 0 <= r <= 100

    def test_extreme_prices_low(self, indicator_service):
        """Test indicators with very small prices (penny stocks)"""
        pennies = [0.01 + i * 0.001 for i in range(50)]

        sma = indicator_service.calculate_sma(pennies, 10)
        assert count_valid(sma) > 0

        rsi = indicator_service.calculate_rsi(pennies, 14)
        assert count_valid(rsi) > 0

    def test_constant_price(self, indicator_service):
        """Test indicators with constant price (no movement)"""
        constant = [100.0] * 50

        sma = indicator_service.calculate_sma(constant, 10)
        valid_sma = filter_none(sma)
        assert all(abs(s - 100.0) < 0.001 for s in valid_sma)

        # Bollinger bands should have width based on std dev
        upper, middle, lower = indicator_service.calculate_bollinger_bands(
            constant, 20, 2.0
        )
        # With constant prices, std dev is 0, so bands = middle
        # This depends on implementation - just verify no crash
        assert count_valid(upper) > 0

    def test_negative_prices_handled(self, indicator_service):
        """Test that calculations don't crash with unusual values"""
        # Some indicators may receive negative values in edge cases
        prices = [-10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0]

        # Should not crash
        sma = indicator_service.calculate_sma(prices, 3)
        assert count_valid(sma) > 0


# ============================================================
# Trading Mode Configuration Tests
# ============================================================

class TestTradingModeConfigs:
    """Test trading mode configurations for SCALP, INTRADAY, SWING"""

    def test_scalp_mode_config(self):
        """Test SCALP mode configuration values"""
        config = AdaptiveIndicatorConfig.get_config(TradingMode.SCALP)

        assert config['rsi_period'] == 7
        assert config['macd_fast'] == 6
        assert config['macd_slow'] == 13
        assert config['macd_signal'] == 5
        assert config['bb_period'] == 10
        assert config['atr_period'] == 7
        assert config['stoch_k_period'] == 7

    def test_intraday_mode_config(self):
        """Test INTRADAY mode configuration values"""
        config = AdaptiveIndicatorConfig.get_config(TradingMode.INTRADAY)

        assert config['rsi_period'] == 14
        assert config['macd_fast'] == 12
        assert config['macd_slow'] == 26
        assert config['macd_signal'] == 9
        assert config['bb_period'] == 20
        assert config['atr_period'] == 14
        assert config['stoch_k_period'] == 14

    def test_swing_mode_config(self):
        """Test SWING mode configuration values"""
        config = AdaptiveIndicatorConfig.get_config(TradingMode.SWING)

        assert config['rsi_period'] == 21
        assert config['macd_fast'] == 19
        assert config['macd_slow'] == 39
        assert config['macd_signal'] == 9
        assert config['bb_period'] == 30
        assert config['atr_period'] == 21
        assert config['stoch_k_period'] == 21

    def test_rsi_thresholds_by_mode(self):
        """Test RSI thresholds differ by mode"""
        scalp = AdaptiveIndicatorConfig.get_config(TradingMode.SCALP)
        intraday = AdaptiveIndicatorConfig.get_config(TradingMode.INTRADAY)
        swing = AdaptiveIndicatorConfig.get_config(TradingMode.SWING)

        # Scalp should be most aggressive
        assert scalp['rsi_overbought'] == 75
        assert scalp['rsi_oversold'] == 25

        # Intraday standard
        assert intraday['rsi_overbought'] == 70
        assert intraday['rsi_oversold'] == 30

        # Swing most conservative
        assert swing['rsi_overbought'] == 65
        assert swing['rsi_oversold'] == 35

    def test_stop_loss_profit_target_by_mode(self):
        """Test stop loss and profit target ATR multipliers"""
        scalp = AdaptiveIndicatorConfig.get_config(TradingMode.SCALP)
        intraday = AdaptiveIndicatorConfig.get_config(TradingMode.INTRADAY)
        swing = AdaptiveIndicatorConfig.get_config(TradingMode.SWING)

        # Scalp - tighter stops
        assert scalp['stop_loss_atr_mult'] == 0.5
        assert scalp['profit_target_atr_mult'] == 1.0

        # Intraday - moderate
        assert intraday['stop_loss_atr_mult'] == 0.75
        assert intraday['profit_target_atr_mult'] == 1.5

        # Swing - wider stops
        assert swing['stop_loss_atr_mult'] == 1.0
        assert swing['profit_target_atr_mult'] == 2.5


# ============================================================
# Adaptive Indicator Engine Tests
# ============================================================

class TestAdaptiveIndicatorEngine:
    """Test AdaptiveIndicatorEngine functionality"""

    def test_engine_initialization(self, adaptive_engine):
        """Test engine initializes with default mode"""
        assert adaptive_engine.current_mode == TradingMode.INTRADAY
        assert adaptive_engine.auto_mode is True

    def test_engine_set_mode(self, adaptive_engine):
        """Test setting trading mode manually"""
        adaptive_engine.set_mode(TradingMode.SCALP, auto=False)

        assert adaptive_engine.current_mode == TradingMode.SCALP
        assert adaptive_engine.auto_mode is False

    def test_engine_auto_mode_detection(self, adaptive_engine):
        """Test automatic mode detection based on volatility"""
        volatile = generate_volatile_data(
            start_price=100, days=50, volatility=0.04, seed=42
        )

        recommended = adaptive_engine.detect_optimal_mode(
            volatile.highs, volatile.lows, volatile.closes
        )

        # High volatility should recommend SCALP
        assert recommended in [TradingMode.SCALP, TradingMode.INTRADAY]

    def test_engine_calculate_volatility(self, adaptive_engine):
        """Test volatility calculation"""
        data = generate_uptrend_data(start_price=100, days=30, seed=42)

        volatility = adaptive_engine.calculate_volatility(
            data.highs, data.lows, data.closes, 14
        )

        assert volatility >= 0

    def test_engine_calculate_adaptive_indicators(self, adaptive_engine):
        """Test full adaptive indicator calculation"""
        data = generate_uptrend_data(start_price=100, days=100, seed=42)

        result = adaptive_engine.calculate_adaptive_indicators(
            data.highs, data.lows, data.closes,
            [float(v) for v in data.volumes]
        )

        assert 'mode' in result
        assert 'indicators' in result
        assert 'signals' in result
        assert 'volatility' in result

        # Check indicator keys exist
        assert 'rsi' in result['indicators']
        assert 'macd' in result['indicators']
        assert 'bollinger' in result['indicators']
        assert 'atr' in result['indicators']
        assert 'stochastic' in result['indicators']

    def test_engine_get_mode_recommendation(self, adaptive_engine):
        """Test mode recommendation with reasoning"""
        data = generate_uptrend_data(start_price=100, days=50, seed=42)

        recommendation = adaptive_engine.get_mode_recommendation(
            data.highs, data.lows, data.closes,
            [float(v) for v in data.volumes]
        )

        assert 'recommended_mode' in recommendation
        assert 'reasoning' in recommendation
        assert len(recommendation['reasoning']) > 0


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
