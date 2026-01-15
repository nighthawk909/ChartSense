"""
Strategy Engine for Trading Bot
Combines technical indicators into entry/exit signals with scoring
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from .indicators import IndicatorService

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Type of trading signal"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradeType(str, Enum):
    """Type of trade based on expected holding period"""
    SWING = "SWING"  # Days to 2 weeks
    LONG_TERM = "LONG_TERM"  # Weeks to months


@dataclass
class TradingSignal:
    """Generated trading signal with all details"""
    symbol: str
    signal_type: SignalType
    score: float  # 0-100 confidence score
    trade_type: TradeType
    current_price: float
    suggested_stop_loss: float
    suggested_profit_target: float
    indicators: Dict[str, Any]
    reasons: List[str]


# Default indicator weights for entry scoring
DEFAULT_WEIGHTS = {
    "rsi": 0.20,
    "macd": 0.25,
    "sma_crossover": 0.20,
    "price_vs_sma20": 0.15,
    "bollinger": 0.10,
    "volume": 0.10,
}


class StrategyEngine:
    """
    Analyzes market data and generates trading signals.
    Uses weighted scoring of multiple technical indicators.
    """

    def __init__(
        self,
        indicator_service: Optional[IndicatorService] = None,
        weights: Optional[Dict[str, float]] = None,
        entry_threshold: float = 70.0,
        swing_profit_target_pct: float = 0.08,
        longterm_profit_target_pct: float = 0.15,
        default_stop_loss_pct: float = 0.05,
    ):
        """
        Initialize strategy engine.

        Args:
            indicator_service: IndicatorService instance
            weights: Custom indicator weights (must sum to 1.0)
            entry_threshold: Minimum score to generate BUY signal
            swing_profit_target_pct: Profit target for swing trades
            longterm_profit_target_pct: Profit target for long-term trades
            default_stop_loss_pct: Default stop-loss percentage
        """
        self.indicators = indicator_service or IndicatorService()
        self.weights = weights or DEFAULT_WEIGHTS
        self.entry_threshold = entry_threshold
        self.swing_profit_target_pct = swing_profit_target_pct
        self.longterm_profit_target_pct = longterm_profit_target_pct
        self.default_stop_loss_pct = default_stop_loss_pct

    def analyze(
        self,
        symbol: str,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[int],
    ) -> TradingSignal:
        """
        Analyze price data and generate a trading signal.

        Args:
            symbol: Stock symbol
            prices: List of closing prices (oldest to newest)
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes

        Returns:
            TradingSignal with recommendation
        """
        if len(prices) < 50:
            logger.warning(f"Insufficient data for {symbol}: {len(prices)} bars")
            return self._create_hold_signal(symbol, prices[-1] if prices else 0, {}, ["Insufficient data"])

        current_price = prices[-1]

        # Calculate all indicators
        indicator_values = self._calculate_all_indicators(prices, highs, lows, volumes)

        # Score each indicator component
        component_scores, reasons = self._score_indicators(indicator_values, current_price)

        # Calculate weighted total score
        total_score = self._calculate_total_score(component_scores)

        # Determine trade type (swing vs long-term)
        trade_type = self._classify_trade_type(indicator_values, component_scores)

        # Determine signal type
        signal_type = self._determine_signal(total_score, indicator_values)

        # Calculate stop-loss and profit target
        stop_loss = self._calculate_stop_loss(current_price, indicator_values, trade_type)
        profit_target = self._calculate_profit_target(current_price, trade_type)

        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            score=total_score,
            trade_type=trade_type,
            current_price=current_price,
            suggested_stop_loss=stop_loss,
            suggested_profit_target=profit_target,
            indicators=indicator_values,
            reasons=reasons,
        )

    def _calculate_all_indicators(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[int],
    ) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        indicators = {}

        # RSI
        rsi_values = self.indicators.calculate_rsi(prices, 14)
        indicators["rsi_14"] = rsi_values[-1] if rsi_values else 50.0
        indicators["rsi_values"] = rsi_values[-30:] if rsi_values else []

        # MACD
        macd_line, signal_line, histogram = self.indicators.calculate_macd(prices)
        indicators["macd_line"] = macd_line[-1] if macd_line else 0
        indicators["macd_signal"] = signal_line[-1] if signal_line else 0
        indicators["macd_histogram"] = histogram[-1] if histogram else 0
        indicators["macd_histogram_prev"] = histogram[-2] if len(histogram) > 1 else 0

        # Moving Averages
        sma_20 = self.indicators.calculate_sma(prices, 20)
        sma_50 = self.indicators.calculate_sma(prices, 50)
        sma_200 = self.indicators.calculate_sma(prices, 200) if len(prices) >= 200 else []

        indicators["sma_20"] = sma_20[-1] if sma_20 else prices[-1]
        indicators["sma_50"] = sma_50[-1] if sma_50 else prices[-1]
        indicators["sma_200"] = sma_200[-1] if sma_200 else prices[-1]

        # Golden/Death Cross detection
        if sma_50 and sma_200:
            indicators["golden_cross"] = sma_50[-1] > sma_200[-1]
            indicators["death_cross"] = sma_50[-1] < sma_200[-1]
        else:
            indicators["golden_cross"] = False
            indicators["death_cross"] = False

        # Bollinger Bands
        upper, middle, lower = self.indicators.calculate_bollinger_bands(prices, 20, 2.0)
        indicators["bb_upper"] = upper[-1] if upper else prices[-1] * 1.02
        indicators["bb_middle"] = middle[-1] if middle else prices[-1]
        indicators["bb_lower"] = lower[-1] if lower else prices[-1] * 0.98

        # Bollinger position (0 = lower band, 1 = upper band)
        if upper and lower:
            bb_range = upper[-1] - lower[-1]
            if bb_range > 0:
                indicators["bb_position"] = (prices[-1] - lower[-1]) / bb_range
            else:
                indicators["bb_position"] = 0.5
        else:
            indicators["bb_position"] = 0.5

        # ATR for volatility
        atr_values = self.indicators.calculate_atr(highs, lows, prices, 14)
        indicators["atr"] = atr_values[-1] if atr_values else 0
        indicators["atr_pct"] = (atr_values[-1] / prices[-1] * 100) if atr_values and prices[-1] > 0 else 0

        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        indicators["volume_current"] = volumes[-1]
        indicators["volume_avg"] = avg_volume
        indicators["volume_ratio"] = volumes[-1] / avg_volume if avg_volume > 0 else 1.0

        # Stochastic
        k_values, d_values = self.indicators.calculate_stochastic(highs, lows, prices, 14, 3)
        indicators["stoch_k"] = k_values[-1] if k_values else 50.0
        indicators["stoch_d"] = d_values[-1] if d_values else 50.0

        # Williams %R
        wr_values = self.indicators.calculate_williams_r(highs, lows, prices, 14)
        indicators["williams_r"] = wr_values[-1] if wr_values else -50.0

        # EMA for trend
        ema_12 = self.indicators.calculate_ema(prices, 12)
        ema_26 = self.indicators.calculate_ema(prices, 26)
        indicators["ema_12"] = ema_12[-1] if ema_12 else prices[-1]
        indicators["ema_26"] = ema_26[-1] if ema_26 else prices[-1]

        # Price momentum (5-day rate of change)
        if len(prices) >= 5:
            indicators["momentum_5d"] = ((prices[-1] - prices[-5]) / prices[-5]) * 100
        else:
            indicators["momentum_5d"] = 0

        return indicators

    def _score_indicators(
        self,
        indicators: Dict[str, Any],
        current_price: float
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Score each indicator component (0-100 scale).
        Returns dict of scores and list of reasons.
        """
        scores = {}
        reasons = []

        # RSI Score (oversold = bullish, overbought = bearish)
        rsi = indicators["rsi_14"]
        if rsi < 30:
            scores["rsi"] = 90  # Oversold - strong buy
            reasons.append(f"RSI oversold at {rsi:.1f}")
        elif rsi < 40:
            scores["rsi"] = 70  # Getting oversold
            reasons.append(f"RSI approaching oversold at {rsi:.1f}")
        elif rsi > 70:
            scores["rsi"] = 20  # Overbought - avoid
            reasons.append(f"RSI overbought at {rsi:.1f}")
        elif rsi > 60:
            scores["rsi"] = 40  # Getting overbought
        else:
            scores["rsi"] = 50  # Neutral

        # MACD Score (bullish crossover = buy signal)
        macd = indicators["macd_line"]
        signal = indicators["macd_signal"]
        histogram = indicators["macd_histogram"]
        histogram_prev = indicators["macd_histogram_prev"]

        if macd > signal and histogram > 0:
            if histogram > histogram_prev:  # Increasing histogram
                scores["macd"] = 85
                reasons.append("MACD bullish with increasing momentum")
            else:
                scores["macd"] = 70
                reasons.append("MACD bullish crossover")
        elif macd < signal and histogram < 0:
            if histogram < histogram_prev:  # Decreasing histogram
                scores["macd"] = 15
                reasons.append("MACD bearish with increasing downward momentum")
            else:
                scores["macd"] = 30
        else:
            scores["macd"] = 50  # Neutral/crossing

        # SMA Crossover Score (golden cross = bullish)
        if indicators["golden_cross"]:
            scores["sma_crossover"] = 85
            reasons.append("Golden cross (50 SMA > 200 SMA)")
        elif indicators["death_cross"]:
            scores["sma_crossover"] = 20
            reasons.append("Death cross (50 SMA < 200 SMA)")
        else:
            # Check trend direction
            if indicators["sma_50"] > indicators["sma_200"]:
                scores["sma_crossover"] = 65
            else:
                scores["sma_crossover"] = 40

        # Price vs SMA20 Score
        sma_20 = indicators["sma_20"]
        if current_price > sma_20 * 1.02:
            scores["price_vs_sma20"] = 75
            reasons.append(f"Price above 20 SMA (bullish trend)")
        elif current_price < sma_20 * 0.98:
            scores["price_vs_sma20"] = 25
        else:
            scores["price_vs_sma20"] = 50

        # Bollinger Bands Score (near lower band = oversold)
        bb_position = indicators["bb_position"]
        if bb_position < 0.1:
            scores["bollinger"] = 90
            reasons.append("Price near lower Bollinger Band (oversold)")
        elif bb_position < 0.25:
            scores["bollinger"] = 75
            reasons.append("Price in lower Bollinger zone")
        elif bb_position > 0.9:
            scores["bollinger"] = 15
            reasons.append("Price near upper Bollinger Band (overbought)")
        elif bb_position > 0.75:
            scores["bollinger"] = 30
        else:
            scores["bollinger"] = 50

        # Volume Score (high volume confirms moves)
        volume_ratio = indicators["volume_ratio"]
        if volume_ratio > 2.0:
            scores["volume"] = 85
            reasons.append(f"High volume ({volume_ratio:.1f}x average)")
        elif volume_ratio > 1.5:
            scores["volume"] = 70
            reasons.append(f"Above average volume ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.5:
            scores["volume"] = 30
        else:
            scores["volume"] = 50

        return scores, reasons

    def _calculate_total_score(self, component_scores: Dict[str, float]) -> float:
        """Calculate weighted total score"""
        total = 0.0
        for component, score in component_scores.items():
            weight = self.weights.get(component, 0)
            total += score * weight

        # Ensure score is in valid range
        return max(0, min(100, total))

    def _classify_trade_type(
        self,
        indicators: Dict[str, Any],
        scores: Dict[str, float]
    ) -> TradeType:
        """
        Determine if this should be a swing trade or long-term trade.

        Swing trades: RSI extremes, high volatility, mean reversion plays
        Long-term: Strong trend, golden cross, steady momentum
        """
        swing_score = 0
        longterm_score = 0

        # RSI extremes favor swing trading
        rsi = indicators["rsi_14"]
        if rsi < 30 or rsi > 70:
            swing_score += 30

        # High volatility (ATR) favors swing
        atr_pct = indicators["atr_pct"]
        if atr_pct > 3:
            swing_score += 25
        elif atr_pct < 1.5:
            longterm_score += 20

        # Bollinger near bands favors swing
        bb_position = indicators["bb_position"]
        if bb_position < 0.15 or bb_position > 0.85:
            swing_score += 25

        # Golden cross favors long-term
        if indicators["golden_cross"]:
            longterm_score += 30

        # Strong price above SMA 200 favors long-term
        if indicators.get("sma_200") and indicators["sma_200"] > 0:
            price_vs_200 = (indicators["sma_20"] - indicators["sma_200"]) / indicators["sma_200"]
            if price_vs_200 > 0.05:
                longterm_score += 20

        # Steady momentum favors long-term
        momentum = indicators["momentum_5d"]
        if 1 < momentum < 5:  # Moderate positive momentum
            longterm_score += 15
        elif momentum > 8:  # Strong momentum - might be overbought, swing it
            swing_score += 15

        return TradeType.SWING if swing_score > longterm_score else TradeType.LONG_TERM

    def _determine_signal(
        self,
        score: float,
        indicators: Dict[str, Any]
    ) -> SignalType:
        """Determine the signal type based on score and indicators"""
        if score >= self.entry_threshold:
            return SignalType.BUY
        elif score < 35:
            return SignalType.SELL
        else:
            return SignalType.HOLD

    def _calculate_stop_loss(
        self,
        current_price: float,
        indicators: Dict[str, Any],
        trade_type: TradeType
    ) -> float:
        """
        Calculate stop-loss price using ATR-based or percentage method.
        """
        atr = indicators.get("atr", 0)

        if atr > 0:
            # ATR-based stop loss (2x ATR for swing, 2.5x for long-term)
            multiplier = 2.0 if trade_type == TradeType.SWING else 2.5
            stop_loss = current_price - (atr * multiplier)

            # Ensure stop loss is at least the minimum percentage
            min_stop = current_price * (1 - self.default_stop_loss_pct)
            stop_loss = max(stop_loss, min_stop)
        else:
            # Percentage-based stop loss
            stop_pct = 0.04 if trade_type == TradeType.SWING else self.default_stop_loss_pct
            stop_loss = current_price * (1 - stop_pct)

        return round(stop_loss, 2)

    def _calculate_profit_target(
        self,
        current_price: float,
        trade_type: TradeType
    ) -> float:
        """Calculate profit target based on trade type"""
        if trade_type == TradeType.SWING:
            target_pct = self.swing_profit_target_pct
        else:
            target_pct = self.longterm_profit_target_pct

        return round(current_price * (1 + target_pct), 2)

    def _create_hold_signal(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, Any],
        reasons: List[str]
    ) -> TradingSignal:
        """Create a HOLD signal (no action)"""
        return TradingSignal(
            symbol=symbol,
            signal_type=SignalType.HOLD,
            score=50.0,
            trade_type=TradeType.SWING,
            current_price=current_price,
            suggested_stop_loss=current_price * 0.95,
            suggested_profit_target=current_price * 1.08,
            indicators=indicators,
            reasons=reasons,
        )

    # ============== Exit Signal Analysis ==============

    def should_exit(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        profit_target: float,
        trade_type: TradeType,
        entry_time_days: int,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[int],
    ) -> Tuple[bool, str]:
        """
        Determine if we should exit a position.

        Args:
            symbol: Stock symbol
            entry_price: Price we entered at
            current_price: Current price
            stop_loss: Stop-loss price
            profit_target: Profit target price
            trade_type: SWING or LONG_TERM
            entry_time_days: Days since entry
            prices, highs, lows, volumes: Recent price data

        Returns:
            Tuple of (should_exit, reason)
        """
        pnl_pct = (current_price - entry_price) / entry_price

        # 1. Stop-loss hit - IMMEDIATE EXIT
        if current_price <= stop_loss:
            return True, "STOP_LOSS"

        # 2. Profit target hit
        if current_price >= profit_target:
            return True, "PROFIT_TARGET"

        # 3. Calculate indicators for signal reversal check
        if len(prices) >= 50:
            indicators = self._calculate_all_indicators(prices, highs, lows, volumes)

            # Check for bearish reversal signals
            rsi = indicators["rsi_14"]
            macd_hist = indicators["macd_histogram"]
            macd_hist_prev = indicators["macd_histogram_prev"]

            # Strong overbought with MACD turning down
            if rsi > 75 and macd_hist < macd_hist_prev and pnl_pct > 0.03:
                return True, "SIGNAL"

            # Death cross while in profit
            if indicators["death_cross"] and pnl_pct > 0.02:
                return True, "SIGNAL"

        # 4. Time-based exit for swing trades
        if trade_type == TradeType.SWING:
            # Swing trade held > 10 days with less than 3% gain
            if entry_time_days > 10 and pnl_pct < 0.03:
                return True, "TIME_STOP"

            # Swing trade held > 15 days regardless
            if entry_time_days > 15:
                return True, "TIME_STOP"

        # 5. Time-based exit for long-term trades
        if trade_type == TradeType.LONG_TERM:
            # Long-term held > 60 days with loss
            if entry_time_days > 60 and pnl_pct < 0:
                return True, "TIME_STOP"

        return False, ""

    def update_parameters(
        self,
        entry_threshold: Optional[float] = None,
        swing_profit_target_pct: Optional[float] = None,
        longterm_profit_target_pct: Optional[float] = None,
        default_stop_loss_pct: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """Update strategy parameters (used by self-optimizer)"""
        if entry_threshold is not None:
            self.entry_threshold = entry_threshold
        if swing_profit_target_pct is not None:
            self.swing_profit_target_pct = swing_profit_target_pct
        if longterm_profit_target_pct is not None:
            self.longterm_profit_target_pct = longterm_profit_target_pct
        if default_stop_loss_pct is not None:
            self.default_stop_loss_pct = default_stop_loss_pct
        if weights is not None:
            self.weights = weights

        logger.info(f"Strategy parameters updated: threshold={self.entry_threshold}, "
                   f"swing_target={self.swing_profit_target_pct}, longterm_target={self.longterm_profit_target_pct}")
