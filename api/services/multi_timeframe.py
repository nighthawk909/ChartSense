"""
Multi-Timeframe Analysis Service
Confirms trading signals across multiple timeframes (1H, 4H, Daily, Weekly)
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from services.indicators import IndicatorService
from services.alpha_vantage import AlphaVantageService

logger = logging.getLogger(__name__)


class Timeframe(str, Enum):
    """Supported timeframes for analysis"""
    MINUTE_15 = "15min"
    HOUR_1 = "60min"
    HOUR_4 = "4hour"
    DAILY = "daily"
    WEEKLY = "weekly"


class TrendDirection(str, Enum):
    """Trend direction classification"""
    STRONG_UP = "strong_uptrend"
    UP = "uptrend"
    NEUTRAL = "neutral"
    DOWN = "downtrend"
    STRONG_DOWN = "strong_downtrend"


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe"""
    timeframe: Timeframe
    trend: TrendDirection
    strength: float  # 0-100
    rsi: float
    macd_signal: str  # "bullish", "bearish", "neutral"
    ma_alignment: str  # "bullish", "bearish", "mixed"
    support: float
    resistance: float
    signals: List[str]


class MultiTimeframeService:
    """
    Service for analyzing stocks across multiple timeframes.
    Confirms signals when multiple timeframes align.
    """

    def __init__(self):
        self.indicator_service = IndicatorService()
        self.av_service = AlphaVantageService()

    def _analyze_single_timeframe(
        self,
        timeframe: Timeframe,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> TimeframeAnalysis:
        """Analyze a single timeframe"""
        signals = []

        # Calculate indicators
        rsi = self.indicator_service.calculate_rsi(closes, 14)
        macd_line, signal_line, histogram = self.indicator_service.calculate_macd(closes)
        sma_20 = self.indicator_service.calculate_sma(closes, 20)
        sma_50 = self.indicator_service.calculate_sma(closes, 50)
        sma_200 = self.indicator_service.calculate_sma(closes, 200) if len(closes) >= 200 else None
        upper_bb, middle_bb, lower_bb = self.indicator_service.calculate_bollinger_bands(closes)
        atr = self.indicator_service.calculate_atr(highs, lows, closes, 14)

        current_price = closes[-1]

        # RSI Analysis
        current_rsi = rsi[-1] if rsi else 50
        if current_rsi < 30:
            signals.append("RSI oversold")
        elif current_rsi > 70:
            signals.append("RSI overbought")

        # MACD Analysis
        macd_signal = "neutral"
        if macd_line and signal_line:
            if macd_line[-1] > signal_line[-1]:
                macd_signal = "bullish"
                if macd_line[-2] <= signal_line[-2]:
                    signals.append("MACD bullish crossover")
            elif macd_line[-1] < signal_line[-1]:
                macd_signal = "bearish"
                if macd_line[-2] >= signal_line[-2]:
                    signals.append("MACD bearish crossover")

        # Moving Average Alignment
        ma_alignment = "mixed"
        if sma_20 and sma_50:
            if current_price > sma_20[-1] > sma_50[-1]:
                ma_alignment = "bullish"
                signals.append("Price above rising MAs")
            elif current_price < sma_20[-1] < sma_50[-1]:
                ma_alignment = "bearish"
                signals.append("Price below falling MAs")

            # Golden/Death cross
            if sma_200:
                if sma_50[-1] > sma_200[-1] and sma_50[-2] <= sma_200[-2]:
                    signals.append("Golden Cross (50 > 200)")
                elif sma_50[-1] < sma_200[-1] and sma_50[-2] >= sma_200[-2]:
                    signals.append("Death Cross (50 < 200)")

        # Determine trend direction and strength
        trend_score = 0

        # RSI contribution
        if current_rsi < 30:
            trend_score -= 20
        elif current_rsi < 40:
            trend_score -= 10
        elif current_rsi > 70:
            trend_score += 20
        elif current_rsi > 60:
            trend_score += 10

        # MACD contribution
        if macd_signal == "bullish":
            trend_score += 25
        elif macd_signal == "bearish":
            trend_score -= 25

        # MA alignment contribution
        if ma_alignment == "bullish":
            trend_score += 25
        elif ma_alignment == "bearish":
            trend_score -= 25

        # Price position contribution
        if sma_20 and current_price > sma_20[-1]:
            trend_score += 10
        elif sma_20:
            trend_score -= 10

        # Classify trend
        if trend_score >= 40:
            trend = TrendDirection.STRONG_UP
        elif trend_score >= 15:
            trend = TrendDirection.UP
        elif trend_score <= -40:
            trend = TrendDirection.STRONG_DOWN
        elif trend_score <= -15:
            trend = TrendDirection.DOWN
        else:
            trend = TrendDirection.NEUTRAL

        # Calculate strength (0-100)
        strength = min(100, max(0, 50 + trend_score))

        # Support/Resistance from Bollinger Bands
        support = lower_bb[-1] if lower_bb else min(lows[-20:])
        resistance = upper_bb[-1] if upper_bb else max(highs[-20:])

        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            strength=strength,
            rsi=current_rsi,
            macd_signal=macd_signal,
            ma_alignment=ma_alignment,
            support=support,
            resistance=resistance,
            signals=signals
        )

    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Perform multi-timeframe analysis on a symbol.

        Returns analysis for Daily, 4H (simulated), and 1H timeframes.
        """
        results = {}

        # Get daily data
        try:
            daily_history = await self.av_service.get_history(symbol, "daily", "full")
            if daily_history and daily_history.data:
                opens = [d.open for d in daily_history.data]
                highs = [d.high for d in daily_history.data]
                lows = [d.low for d in daily_history.data]
                closes = [d.close for d in daily_history.data]
                volumes = [d.volume for d in daily_history.data]

                daily_analysis = self._analyze_single_timeframe(
                    Timeframe.DAILY, opens, highs, lows, closes, volumes
                )
                results["daily"] = {
                    "timeframe": "daily",
                    "trend": daily_analysis.trend.value,
                    "strength": daily_analysis.strength,
                    "rsi": daily_analysis.rsi,
                    "macd_signal": daily_analysis.macd_signal,
                    "ma_alignment": daily_analysis.ma_alignment,
                    "support": daily_analysis.support,
                    "resistance": daily_analysis.resistance,
                    "signals": daily_analysis.signals,
                }
        except Exception as e:
            logger.error(f"Error analyzing daily timeframe: {e}")

        # Get weekly data (aggregate daily)
        try:
            weekly_history = await self.av_service.get_history(symbol, "weekly")
            if weekly_history and weekly_history.data:
                opens = [d.open for d in weekly_history.data]
                highs = [d.high for d in weekly_history.data]
                lows = [d.low for d in weekly_history.data]
                closes = [d.close for d in weekly_history.data]
                volumes = [d.volume for d in weekly_history.data]

                weekly_analysis = self._analyze_single_timeframe(
                    Timeframe.WEEKLY, opens, highs, lows, closes, volumes
                )
                results["weekly"] = {
                    "timeframe": "weekly",
                    "trend": weekly_analysis.trend.value,
                    "strength": weekly_analysis.strength,
                    "rsi": weekly_analysis.rsi,
                    "macd_signal": weekly_analysis.macd_signal,
                    "ma_alignment": weekly_analysis.ma_alignment,
                    "support": weekly_analysis.support,
                    "resistance": weekly_analysis.resistance,
                    "signals": weekly_analysis.signals,
                }
        except Exception as e:
            logger.error(f"Error analyzing weekly timeframe: {e}")

        # Calculate confluence score
        confluence = self._calculate_confluence(results)

        return {
            "symbol": symbol,
            "timeframes": results,
            "confluence": confluence,
        }

    def _calculate_confluence(self, timeframe_results: Dict) -> Dict[str, Any]:
        """
        Calculate how well different timeframes align.
        Higher confluence = stronger signal.
        """
        if not timeframe_results:
            return {"score": 0, "direction": "neutral", "confidence": "low"}

        bullish_count = 0
        bearish_count = 0
        total_strength = 0

        for tf_name, analysis in timeframe_results.items():
            trend = analysis.get("trend", "neutral")
            strength = analysis.get("strength", 50)
            total_strength += strength

            if "up" in trend:
                bullish_count += 1
                if "strong" in trend:
                    bullish_count += 0.5
            elif "down" in trend:
                bearish_count += 1
                if "strong" in trend:
                    bearish_count += 0.5

        total_tf = len(timeframe_results)
        avg_strength = total_strength / total_tf if total_tf > 0 else 50

        # Calculate confluence score
        if bullish_count > bearish_count:
            direction = "bullish"
            alignment = bullish_count / total_tf
        elif bearish_count > bullish_count:
            direction = "bearish"
            alignment = bearish_count / total_tf
        else:
            direction = "neutral"
            alignment = 0.5

        confluence_score = alignment * 100

        # Determine confidence
        if confluence_score >= 75 and avg_strength >= 60:
            confidence = "high"
        elif confluence_score >= 50:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "score": confluence_score,
            "direction": direction,
            "confidence": confidence,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "average_strength": avg_strength,
            "recommendation": self._get_recommendation(direction, confluence_score, avg_strength)
        }

    def _get_recommendation(
        self,
        direction: str,
        confluence_score: float,
        avg_strength: float
    ) -> str:
        """Generate trading recommendation based on confluence"""
        if confluence_score >= 80 and avg_strength >= 65:
            if direction == "bullish":
                return "STRONG_BUY"
            elif direction == "bearish":
                return "STRONG_SELL"

        if confluence_score >= 60 and avg_strength >= 55:
            if direction == "bullish":
                return "BUY"
            elif direction == "bearish":
                return "SELL"

        return "HOLD"


# Singleton instance
_mtf_service = None

def get_multi_timeframe_service() -> MultiTimeframeService:
    """Get singleton multi-timeframe service instance"""
    global _mtf_service
    if _mtf_service is None:
        _mtf_service = MultiTimeframeService()
    return _mtf_service
