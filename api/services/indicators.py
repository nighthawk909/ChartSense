"""
Technical Indicator Calculations
Pure Python implementations of common technical indicators
"""
from typing import List, Tuple, Optional
import statistics


class IndicatorService:
    """Service for calculating technical indicators"""

    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """
        Calculate Simple Moving Average

        Args:
            prices: List of closing prices
            period: Number of periods for the average

        Returns:
            List of SMA values (shorter than input by period-1)
        """
        if len(prices) < period:
            return []

        sma_values = []
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma_values.append(sum(window) / period)

        return sma_values

    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average

        Args:
            prices: List of closing prices
            period: Number of periods for the average

        Returns:
            List of EMA values
        """
        if len(prices) < period:
            return []

        multiplier = 2 / (period + 1)
        ema_values = []

        # First EMA is SMA
        first_sma = sum(prices[:period]) / period
        ema_values.append(first_sma)

        # Calculate subsequent EMAs
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """
        Calculate Relative Strength Index

        Args:
            prices: List of closing prices
            period: RSI period (default 14)

        Returns:
            List of RSI values (0-100 scale)
        """
        if len(prices) < period + 1:
            return []

        # Calculate price changes
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [max(0, change) for change in changes]
        losses = [abs(min(0, change)) for change in changes]

        rsi_values = []

        # First RSI calculation uses simple average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

        # Subsequent RSI calculations use smoothed average
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

        return rsi_values

    def calculate_macd(
        self,
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            prices: List of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        if len(prices) < slow_period:
            return [], [], []

        fast_ema = self.calculate_ema(prices, fast_period)
        slow_ema = self.calculate_ema(prices, slow_period)

        # Align EMAs (slow EMA starts later)
        offset = slow_period - fast_period
        fast_ema = fast_ema[offset:]

        # MACD line = Fast EMA - Slow EMA
        macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]

        if len(macd_line) < signal_period:
            return macd_line, [], []

        # Signal line = EMA of MACD line
        signal_line = self.calculate_ema(macd_line, signal_period)

        # Align MACD line with signal line
        macd_aligned = macd_line[signal_period - 1:]

        # Histogram = MACD line - Signal line
        histogram = [macd - signal for macd, signal in zip(macd_aligned, signal_line)]

        return macd_aligned, signal_line, histogram

    def calculate_bollinger_bands(
        self,
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate Bollinger Bands

        Args:
            prices: List of closing prices
            period: Moving average period (default 20)
            std_dev: Number of standard deviations (default 2.0)

        Returns:
            Tuple of (Upper band, Middle band (SMA), Lower band)
        """
        if len(prices) < period:
            return [], [], []

        middle_band = self.calculate_sma(prices, period)
        upper_band = []
        lower_band = []

        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            std = statistics.stdev(window)
            sma = middle_band[i - period + 1]

            upper_band.append(sma + (std_dev * std))
            lower_band.append(sma - (std_dev * std))

        return upper_band, middle_band, lower_band

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """
        Calculate Average True Range

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: ATR period (default 14)

        Returns:
            List of ATR values
        """
        if len(closes) < period + 1:
            return []

        true_ranges = []

        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(high_low, high_close, low_close))

        # First ATR is simple average
        atr_values = [sum(true_ranges[:period]) / period]

        # Subsequent ATRs use smoothed average
        for i in range(period, len(true_ranges)):
            atr = (atr_values[-1] * (period - 1) + true_ranges[i]) / period
            atr_values.append(atr)

        return atr_values

    def calculate_stochastic(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[List[float], List[float]]:
        """
        Calculate Stochastic Oscillator

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            k_period: %K period (default 14)
            d_period: %D period (default 3)

        Returns:
            Tuple of (%K values, %D values)
        """
        if len(closes) < k_period:
            return [], []

        k_values = []

        for i in range(k_period - 1, len(closes)):
            period_highs = highs[i - k_period + 1:i + 1]
            period_lows = lows[i - k_period + 1:i + 1]

            highest_high = max(period_highs)
            lowest_low = min(period_lows)

            if highest_high == lowest_low:
                k_values.append(50.0)  # Neutral if no range
            else:
                k = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100
                k_values.append(k)

        # %D is SMA of %K
        d_values = self.calculate_sma(k_values, d_period)

        return k_values, d_values

    def calculate_williams_r(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> List[float]:
        """
        Calculate Williams %R

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: Lookback period (default 14)

        Returns:
            List of Williams %R values (-100 to 0)
        """
        if len(closes) < period:
            return []

        wr_values = []

        for i in range(period - 1, len(closes)):
            period_highs = highs[i - period + 1:i + 1]
            period_lows = lows[i - period + 1:i + 1]

            highest_high = max(period_highs)
            lowest_low = min(period_lows)

            if highest_high == lowest_low:
                wr_values.append(-50.0)
            else:
                wr = ((highest_high - closes[i]) / (highest_high - lowest_low)) * -100
                wr_values.append(wr)

        return wr_values
