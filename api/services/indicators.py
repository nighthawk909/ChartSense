"""
Technical Indicator Calculations
Pure Python implementations of common technical indicators
"""
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import statistics


class TradingMode(str, Enum):
    SCALP = "scalp"
    INTRADAY = "intraday"
    SWING = "swing"


class AdaptiveIndicatorConfig:
    """Configuration for adaptive indicator settings by trading mode"""

    MODE_CONFIGS = {
        TradingMode.SCALP: {
            "rsi_period": 7,
            "rsi_overbought": 75,
            "rsi_oversold": 25,
            "macd_fast": 6,
            "macd_slow": 13,
            "macd_signal": 5,
            "bb_period": 10,
            "bb_std_dev": 2.0,
            "atr_period": 7,
            "stoch_k_period": 7,
            "stoch_d_period": 3,
            "ema_fast": 5,
            "ema_slow": 13,
            "min_volume_multiplier": 1.5,
            "profit_target_atr_mult": 1.0,
            "stop_loss_atr_mult": 0.5,
            "hold_time_max_minutes": 60,
            "volatility_threshold_high": 3.0,  # ATR %
            "volatility_threshold_low": 0.5,
        },
        TradingMode.INTRADAY: {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "atr_period": 14,
            "stoch_k_period": 14,
            "stoch_d_period": 3,
            "ema_fast": 9,
            "ema_slow": 21,
            "min_volume_multiplier": 1.2,
            "profit_target_atr_mult": 1.5,
            "stop_loss_atr_mult": 0.75,
            "hold_time_max_minutes": 480,
            "volatility_threshold_high": 2.5,
            "volatility_threshold_low": 0.8,
        },
        TradingMode.SWING: {
            "rsi_period": 21,
            "rsi_overbought": 65,
            "rsi_oversold": 35,
            "macd_fast": 19,
            "macd_slow": 39,
            "macd_signal": 9,
            "bb_period": 30,
            "bb_std_dev": 2.5,
            "atr_period": 21,
            "stoch_k_period": 21,
            "stoch_d_period": 5,
            "ema_fast": 12,
            "ema_slow": 26,
            "min_volume_multiplier": 1.0,
            "profit_target_atr_mult": 2.5,
            "stop_loss_atr_mult": 1.0,
            "hold_time_max_minutes": 10080,  # 7 days
            "volatility_threshold_high": 2.0,
            "volatility_threshold_low": 1.0,
        }
    }

    @classmethod
    def get_config(cls, mode: TradingMode) -> Dict[str, Any]:
        return cls.MODE_CONFIGS.get(mode, cls.MODE_CONFIGS[TradingMode.INTRADAY])


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

    def calculate_obv(self, closes: List[float], volumes: List[float]) -> List[float]:
        """
        Calculate On Balance Volume (OBV)

        Args:
            closes: List of closing prices
            volumes: List of volumes

        Returns:
            List of OBV values
        """
        if len(closes) < 2 or len(volumes) < 2:
            return []

        obv_values = [0.0]

        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv_values.append(obv_values[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                obv_values.append(obv_values[-1] - volumes[i])
            else:
                obv_values.append(obv_values[-1])

        return obv_values

    def calculate_roc(self, prices: List[float], period: int = 12) -> List[float]:
        """
        Calculate Rate of Change (ROC)

        Args:
            prices: List of closing prices
            period: ROC period (default 12)

        Returns:
            List of ROC values (percentage)
        """
        if len(prices) < period + 1:
            return []

        roc_values = []
        for i in range(period, len(prices)):
            if prices[i - period] != 0:
                roc = ((prices[i] - prices[i - period]) / prices[i - period]) * 100
            else:
                roc = 0.0
            roc_values.append(roc)

        return roc_values

    def calculate_adx(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14,
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate Average Directional Index (ADX) with +DI and -DI

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: ADX period (default 14)

        Returns:
            Tuple of (ADX, +DI, -DI)
        """
        if len(closes) < period + 1:
            return [], [], []

        # Calculate True Range and Directional Movement
        plus_dm = []
        minus_dm = []
        tr = []

        for i in range(1, len(closes)):
            high_diff = highs[i] - highs[i - 1]
            low_diff = lows[i - 1] - lows[i]

            # +DM
            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)

            # -DM
            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)

            # True Range
            tr_val = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            tr.append(tr_val)

        # Smooth with Wilder's moving average
        def wilder_smooth(data: List[float], period: int) -> List[float]:
            if len(data) < period:
                return []
            smoothed = [sum(data[:period])]
            for i in range(period, len(data)):
                smoothed.append(smoothed[-1] - (smoothed[-1] / period) + data[i])
            return smoothed

        atr_smooth = wilder_smooth(tr, period)
        plus_dm_smooth = wilder_smooth(plus_dm, period)
        minus_dm_smooth = wilder_smooth(minus_dm, period)

        if not atr_smooth:
            return [], [], []

        # Calculate +DI and -DI
        plus_di = []
        minus_di = []
        for i in range(len(atr_smooth)):
            if atr_smooth[i] != 0:
                plus_di.append((plus_dm_smooth[i] / atr_smooth[i]) * 100)
                minus_di.append((minus_dm_smooth[i] / atr_smooth[i]) * 100)
            else:
                plus_di.append(0)
                minus_di.append(0)

        # Calculate DX
        dx = []
        for i in range(len(plus_di)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum != 0:
                dx.append(abs(plus_di[i] - minus_di[i]) / di_sum * 100)
            else:
                dx.append(0)

        # Calculate ADX (smoothed DX)
        adx = wilder_smooth(dx, period) if len(dx) >= period else []

        return adx, plus_di, minus_di

    def calculate_cci(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 20,
    ) -> List[float]:
        """
        Calculate Commodity Channel Index (CCI)

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: CCI period (default 20)

        Returns:
            List of CCI values
        """
        if len(closes) < period:
            return []

        # Calculate Typical Price
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]

        cci_values = []
        constant = 0.015

        for i in range(period - 1, len(tp)):
            window = tp[i - period + 1:i + 1]
            sma = sum(window) / period
            mean_dev = sum(abs(x - sma) for x in window) / period

            if mean_dev != 0:
                cci = (tp[i] - sma) / (constant * mean_dev)
            else:
                cci = 0

            cci_values.append(cci)

        return cci_values

    def calculate_vwap(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
    ) -> List[float]:
        """
        Calculate Volume Weighted Average Price (VWAP)

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            volumes: List of volumes

        Returns:
            List of VWAP values
        """
        if len(closes) < 1 or len(volumes) < 1:
            return []

        # Calculate Typical Price
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]

        vwap_values = []
        cumulative_tp_vol = 0.0
        cumulative_vol = 0.0

        for i in range(len(tp)):
            cumulative_tp_vol += tp[i] * volumes[i]
            cumulative_vol += volumes[i]

            if cumulative_vol != 0:
                vwap_values.append(cumulative_tp_vol / cumulative_vol)
            else:
                vwap_values.append(tp[i])

        return vwap_values

    def calculate_momentum(self, prices: List[float], period: int = 10) -> List[float]:
        """
        Calculate Momentum indicator

        Args:
            prices: List of closing prices
            period: Momentum period (default 10)

        Returns:
            List of Momentum values
        """
        if len(prices) < period + 1:
            return []

        momentum_values = []
        for i in range(period, len(prices)):
            momentum_values.append(prices[i] - prices[i - period])

        return momentum_values


class AdaptiveIndicatorEngine:
    """
    Adaptive Indicator Engine that dynamically adjusts indicator parameters
    based on current market volatility and trading mode.
    """

    def __init__(self):
        self.indicator_service = IndicatorService()
        self._current_mode: TradingMode = TradingMode.INTRADAY
        self._auto_mode: bool = True
        self._last_volatility: float = 0.0
        self._mode_history: List[Dict[str, Any]] = []

    @property
    def current_mode(self) -> TradingMode:
        return self._current_mode

    @property
    def auto_mode(self) -> bool:
        return self._auto_mode

    def set_mode(self, mode: TradingMode, auto: bool = False):
        """Manually set trading mode or enable auto-switching"""
        self._auto_mode = auto
        if not auto:
            self._current_mode = mode

    def get_config(self) -> Dict[str, Any]:
        """Get current mode configuration"""
        return AdaptiveIndicatorConfig.get_config(self._current_mode)

    def calculate_volatility(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """
        Calculate current market volatility as ATR percentage of price.

        Returns:
            Volatility as percentage (e.g., 2.5 = 2.5%)
        """
        if len(closes) < period + 1:
            return 0.0

        atr_values = self.indicator_service.calculate_atr(highs, lows, closes, period)
        if not atr_values:
            return 0.0

        current_atr = atr_values[-1]
        current_price = closes[-1]

        if current_price <= 0:
            return 0.0

        volatility_pct = (current_atr / current_price) * 100
        self._last_volatility = volatility_pct
        return volatility_pct

    def detect_optimal_mode(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> TradingMode:
        """
        Automatically detect the optimal trading mode based on volatility and volume.

        Returns:
            Recommended TradingMode
        """
        volatility = self.calculate_volatility(highs, lows, closes)

        # High volatility favors scalping
        if volatility >= 2.5:
            recommended = TradingMode.SCALP
        # Low volatility favors swing trading
        elif volatility <= 1.0:
            recommended = TradingMode.SWING
        # Medium volatility favors intraday
        else:
            recommended = TradingMode.INTRADAY

        # Consider volume patterns if available
        if volumes and len(volumes) >= 20:
            avg_volume = sum(volumes[-20:]) / 20
            recent_volume = volumes[-1] if volumes else 0

            # High relative volume suggests more active trading
            if recent_volume > avg_volume * 2.0 and recommended != TradingMode.SCALP:
                # Bump up activity level
                if recommended == TradingMode.SWING:
                    recommended = TradingMode.INTRADAY
                elif recommended == TradingMode.INTRADAY:
                    recommended = TradingMode.SCALP

        if self._auto_mode:
            self._current_mode = recommended

        return recommended

    def calculate_adaptive_indicators(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate all indicators using adaptive parameters based on current mode.

        Returns:
            Dictionary with all calculated indicators and metadata
        """
        # Auto-detect mode if enabled
        if self._auto_mode:
            self.detect_optimal_mode(highs, lows, closes, volumes)

        config = self.get_config()

        # Calculate RSI
        rsi_values = self.indicator_service.calculate_rsi(closes, config["rsi_period"])

        # Calculate MACD
        macd_line, signal_line, histogram = self.indicator_service.calculate_macd(
            closes,
            config["macd_fast"],
            config["macd_slow"],
            config["macd_signal"]
        )

        # Calculate Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.indicator_service.calculate_bollinger_bands(
            closes,
            config["bb_period"],
            config["bb_std_dev"]
        )

        # Calculate ATR
        atr_values = self.indicator_service.calculate_atr(
            highs, lows, closes,
            config["atr_period"]
        )

        # Calculate Stochastic
        stoch_k, stoch_d = self.indicator_service.calculate_stochastic(
            highs, lows, closes,
            config["stoch_k_period"],
            config["stoch_d_period"]
        )

        # Calculate EMAs
        ema_fast = self.indicator_service.calculate_ema(closes, config["ema_fast"])
        ema_slow = self.indicator_service.calculate_ema(closes, config["ema_slow"])

        # Calculate additional indicators for cycling display
        williams_r = self.indicator_service.calculate_williams_r(highs, lows, closes, 14)
        roc_values = self.indicator_service.calculate_roc(closes, 12)
        cci_values = self.indicator_service.calculate_cci(highs, lows, closes, 20)
        adx_values, plus_di, minus_di = self.indicator_service.calculate_adx(highs, lows, closes, 14)
        momentum_values = self.indicator_service.calculate_momentum(closes, 10)

        # Volume-based indicators (only if volumes available)
        obv_values = []
        vwap_values = []
        if volumes and len(volumes) > 0:
            obv_values = self.indicator_service.calculate_obv(closes, volumes)
            vwap_values = self.indicator_service.calculate_vwap(highs, lows, closes, volumes)

        # Get latest values
        result = {
            "mode": self._current_mode.value,
            "auto_mode": self._auto_mode,
            "volatility": self._last_volatility,
            "config": config,
            "indicators": {
                "rsi": {
                    "value": rsi_values[-1] if rsi_values else None,
                    "period": config["rsi_period"],
                    "overbought": config["rsi_overbought"],
                    "oversold": config["rsi_oversold"],
                    "is_overbought": rsi_values[-1] > config["rsi_overbought"] if rsi_values else False,
                    "is_oversold": rsi_values[-1] < config["rsi_oversold"] if rsi_values else False,
                },
                "macd": {
                    "macd_line": macd_line[-1] if macd_line else None,
                    "signal_line": signal_line[-1] if signal_line else None,
                    "histogram": histogram[-1] if histogram else None,
                    "is_bullish": (histogram[-1] > 0 if histogram else False),
                    "is_bearish": (histogram[-1] < 0 if histogram else False),
                    "crossover": self._detect_macd_crossover(macd_line, signal_line),
                },
                "bollinger": {
                    "upper": bb_upper[-1] if bb_upper else None,
                    "middle": bb_middle[-1] if bb_middle else None,
                    "lower": bb_lower[-1] if bb_lower else None,
                    "price_position": self._get_bb_position(closes[-1], bb_upper, bb_middle, bb_lower),
                },
                "atr": {
                    "value": atr_values[-1] if atr_values else None,
                    "profit_target": (atr_values[-1] * config["profit_target_atr_mult"]) if atr_values else None,
                    "stop_loss": (atr_values[-1] * config["stop_loss_atr_mult"]) if atr_values else None,
                },
                "stochastic": {
                    "k": stoch_k[-1] if stoch_k else None,
                    "d": stoch_d[-1] if stoch_d else None,
                    "is_overbought": (stoch_k[-1] > 80 if stoch_k else False),
                    "is_oversold": (stoch_k[-1] < 20 if stoch_k else False),
                },
                "ema": {
                    "fast": ema_fast[-1] if ema_fast else None,
                    "slow": ema_slow[-1] if ema_slow else None,
                    "trend": "bullish" if (ema_fast and ema_slow and ema_fast[-1] > ema_slow[-1]) else "bearish",
                },
                # Additional indicators for cycling display
                "williams_r": {
                    "value": williams_r[-1] if williams_r else None,
                    "period": 14,
                    "is_overbought": (williams_r[-1] > -20 if williams_r else False),
                    "is_oversold": (williams_r[-1] < -80 if williams_r else False),
                },
                "roc": {
                    "value": roc_values[-1] if roc_values else None,
                    "period": 12,
                    "is_positive": (roc_values[-1] > 0 if roc_values else False),
                },
                "cci": {
                    "value": cci_values[-1] if cci_values else None,
                    "period": 20,
                    "is_overbought": (cci_values[-1] > 100 if cci_values else False),
                    "is_oversold": (cci_values[-1] < -100 if cci_values else False),
                },
                "adx": {
                    "value": adx_values[-1] if adx_values else None,
                    "plus_di": plus_di[-1] if plus_di else None,
                    "minus_di": minus_di[-1] if minus_di else None,
                    "trend_strength": "strong" if (adx_values and adx_values[-1] > 25) else "weak" if (adx_values and adx_values[-1] < 20) else "moderate",
                },
                "momentum": {
                    "value": momentum_values[-1] if momentum_values else None,
                    "period": 10,
                    "is_positive": (momentum_values[-1] > 0 if momentum_values else False),
                },
                "obv": {
                    "value": obv_values[-1] if obv_values else None,
                    "trend": "rising" if (len(obv_values) >= 2 and obv_values[-1] > obv_values[-2]) else "falling" if (len(obv_values) >= 2 and obv_values[-1] < obv_values[-2]) else "flat",
                },
                "vwap": {
                    "value": vwap_values[-1] if vwap_values else None,
                    "price_vs_vwap": "above" if (vwap_values and closes[-1] > vwap_values[-1]) else "below" if (vwap_values and closes[-1] < vwap_values[-1]) else "at",
                },
            },
            "signals": self._generate_signals(
                rsi_values, macd_line, signal_line, histogram,
                bb_upper, bb_middle, bb_lower, closes,
                stoch_k, stoch_d, ema_fast, ema_slow, config
            ),
        }

        # Record mode history
        self._mode_history.append({
            "mode": self._current_mode.value,
            "volatility": self._last_volatility,
            "timestamp": None  # Caller should add timestamp
        })

        # Keep only last 100 entries
        if len(self._mode_history) > 100:
            self._mode_history = self._mode_history[-100:]

        return result

    def _detect_macd_crossover(
        self,
        macd_line: List[float],
        signal_line: List[float]
    ) -> Optional[str]:
        """Detect MACD crossover signal"""
        if len(macd_line) < 2 or len(signal_line) < 2:
            return None

        prev_macd = macd_line[-2]
        curr_macd = macd_line[-1]
        prev_signal = signal_line[-2]
        curr_signal = signal_line[-1]

        # Bullish crossover: MACD crosses above signal
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            return "bullish"
        # Bearish crossover: MACD crosses below signal
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            return "bearish"

        return None

    def _get_bb_position(
        self,
        price: float,
        upper: List[float],
        middle: List[float],
        lower: List[float]
    ) -> str:
        """Determine price position relative to Bollinger Bands"""
        if not upper or not middle or not lower:
            return "unknown"

        if price >= upper[-1]:
            return "above_upper"
        elif price <= lower[-1]:
            return "below_lower"
        elif price > middle[-1]:
            return "upper_half"
        else:
            return "lower_half"

    def _generate_signals(
        self,
        rsi_values: List[float],
        macd_line: List[float],
        signal_line: List[float],
        histogram: List[float],
        bb_upper: List[float],
        bb_middle: List[float],
        bb_lower: List[float],
        closes: List[float],
        stoch_k: List[float],
        stoch_d: List[float],
        ema_fast: List[float],
        ema_slow: List[float],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signals based on all indicators"""
        signals = {
            "buy_signals": [],
            "sell_signals": [],
            "neutral_signals": [],
            "overall": "neutral",
            "strength": 0,
            "confidence": 0.0,
        }

        buy_score = 0
        sell_score = 0
        total_checks = 0

        # RSI signals
        if rsi_values:
            rsi = rsi_values[-1]
            total_checks += 1
            if rsi < config["rsi_oversold"]:
                signals["buy_signals"].append(f"RSI oversold ({rsi:.1f})")
                buy_score += 1
            elif rsi > config["rsi_overbought"]:
                signals["sell_signals"].append(f"RSI overbought ({rsi:.1f})")
                sell_score += 1
            else:
                signals["neutral_signals"].append(f"RSI neutral ({rsi:.1f})")

        # MACD signals
        if histogram:
            total_checks += 1
            crossover = self._detect_macd_crossover(macd_line, signal_line)
            if crossover == "bullish":
                signals["buy_signals"].append("MACD bullish crossover")
                buy_score += 2  # Crossovers are strong signals
            elif crossover == "bearish":
                signals["sell_signals"].append("MACD bearish crossover")
                sell_score += 2
            elif histogram[-1] > 0:
                signals["buy_signals"].append("MACD histogram positive")
                buy_score += 0.5
            else:
                signals["sell_signals"].append("MACD histogram negative")
                sell_score += 0.5

        # Bollinger Band signals
        if closes and bb_upper and bb_lower:
            total_checks += 1
            price = closes[-1]
            if price <= bb_lower[-1]:
                signals["buy_signals"].append("Price at lower Bollinger Band")
                buy_score += 1
            elif price >= bb_upper[-1]:
                signals["sell_signals"].append("Price at upper Bollinger Band")
                sell_score += 1
            else:
                signals["neutral_signals"].append("Price within Bollinger Bands")

        # Stochastic signals
        if stoch_k and stoch_d:
            total_checks += 1
            k, d = stoch_k[-1], stoch_d[-1]
            if k < 20 and d < 20:
                signals["buy_signals"].append(f"Stochastic oversold (K:{k:.1f}, D:{d:.1f})")
                buy_score += 1
            elif k > 80 and d > 80:
                signals["sell_signals"].append(f"Stochastic overbought (K:{k:.1f}, D:{d:.1f})")
                sell_score += 1
            else:
                signals["neutral_signals"].append(f"Stochastic neutral (K:{k:.1f})")

        # EMA trend signals
        if ema_fast and ema_slow:
            total_checks += 1
            if ema_fast[-1] > ema_slow[-1]:
                signals["buy_signals"].append("EMA trend bullish")
                buy_score += 0.5
            else:
                signals["sell_signals"].append("EMA trend bearish")
                sell_score += 0.5

        # Calculate overall signal and confidence
        net_score = buy_score - sell_score
        max_score = total_checks * 2  # Maximum possible score

        if max_score > 0:
            signals["confidence"] = min(abs(net_score) / max_score, 1.0) * 100

        if net_score >= 2:
            signals["overall"] = "strong_buy"
            signals["strength"] = min(net_score, 5)
        elif net_score >= 1:
            signals["overall"] = "buy"
            signals["strength"] = net_score
        elif net_score <= -2:
            signals["overall"] = "strong_sell"
            signals["strength"] = max(net_score, -5)
        elif net_score <= -1:
            signals["overall"] = "sell"
            signals["strength"] = net_score
        else:
            signals["overall"] = "neutral"
            signals["strength"] = 0

        return signals

    def get_mode_recommendation(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Get a detailed mode recommendation with reasoning.

        Returns:
            Dictionary with recommendation and reasoning
        """
        volatility = self.calculate_volatility(highs, lows, closes)
        recommended = self.detect_optimal_mode(highs, lows, closes, volumes)

        reasoning = []
        if volatility >= 2.5:
            reasoning.append(f"High volatility ({volatility:.2f}%) favors quick scalp trades")
        elif volatility <= 1.0:
            reasoning.append(f"Low volatility ({volatility:.2f}%) favors swing positions")
        else:
            reasoning.append(f"Moderate volatility ({volatility:.2f}%) suits intraday trading")

        if volumes and len(volumes) >= 20:
            avg_volume = sum(volumes[-20:]) / 20
            recent_volume = volumes[-1] if volumes else 0
            vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

            if vol_ratio > 2.0:
                reasoning.append(f"High relative volume ({vol_ratio:.1f}x avg) indicates active market")
            elif vol_ratio < 0.5:
                reasoning.append(f"Low relative volume ({vol_ratio:.1f}x avg) indicates quiet market")

        return {
            "recommended_mode": recommended.value,
            "current_mode": self._current_mode.value,
            "volatility": volatility,
            "auto_mode": self._auto_mode,
            "reasoning": reasoning,
            "config": AdaptiveIndicatorConfig.get_config(recommended),
        }
