"""
Pattern Recognition Service
Detects chart patterns like Head & Shoulders, Double Tops/Bottoms, Triangles, etc.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of chart patterns"""
    # Reversal Patterns
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    ROUNDING_TOP = "rounding_top"
    ROUNDING_BOTTOM = "rounding_bottom"

    # Continuation Patterns
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    BULL_PENNANT = "bull_pennant"
    BEAR_PENNANT = "bear_pennant"
    WEDGE_UP = "wedge_up"
    WEDGE_DOWN = "wedge_down"

    # Candlestick Patterns
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    ENGULFING_BULLISH = "engulfing_bullish"
    ENGULFING_BEARISH = "engulfing_bearish"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"


@dataclass
class PatternResult:
    """Result of pattern detection"""
    pattern_type: PatternType
    confidence: float  # 0-100
    direction: str  # "bullish" or "bearish"
    start_index: int
    end_index: int
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    description: str = ""


class PatternRecognitionService:
    """
    Service for detecting chart patterns in price data.
    """

    def __init__(self):
        self.min_pattern_bars = 5
        self.tolerance = 0.02  # 2% tolerance for pattern matching

    def find_local_extrema(
        self,
        prices: List[float],
        window: int = 5
    ) -> Tuple[List[int], List[int]]:
        """
        Find local maxima and minima in price data.

        Returns:
            Tuple of (maxima_indices, minima_indices)
        """
        if len(prices) < window * 2:
            return [], []

        maxima = []
        minima = []

        for i in range(window, len(prices) - window):
            # Check if local maximum
            if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] >= prices[i+j] for j in range(1, window+1)):
                maxima.append(i)

            # Check if local minimum
            if all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
               all(prices[i] <= prices[i+j] for j in range(1, window+1)):
                minima.append(i)

        return maxima, minima

    def detect_head_and_shoulders(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[PatternResult]:
        """
        Detect Head and Shoulders pattern.

        Pattern characteristics:
        - Left shoulder: first peak
        - Head: higher peak in the middle
        - Right shoulder: peak similar to left shoulder
        - Neckline: support connecting the troughs
        """
        maxima, minima = self.find_local_extrema(highs, window=3)

        if len(maxima) < 3 or len(minima) < 2:
            return None

        # Look for H&S pattern in recent maxima
        for i in range(len(maxima) - 2):
            left_shoulder_idx = maxima[i]
            head_idx = maxima[i + 1]
            right_shoulder_idx = maxima[i + 2]

            left_shoulder = highs[left_shoulder_idx]
            head = highs[head_idx]
            right_shoulder = highs[right_shoulder_idx]

            # Head must be higher than both shoulders
            if head <= left_shoulder or head <= right_shoulder:
                continue

            # Shoulders should be roughly equal (within tolerance)
            shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
            if shoulder_diff > self.tolerance * 2:
                continue

            # Find neckline (troughs between shoulders)
            trough_indices = [m for m in minima if left_shoulder_idx < m < right_shoulder_idx]
            if len(trough_indices) < 2:
                continue

            neckline = min(lows[trough_indices[0]], lows[trough_indices[-1]])

            # Calculate confidence based on pattern symmetry
            symmetry = 1 - shoulder_diff
            head_prominence = (head - max(left_shoulder, right_shoulder)) / head
            confidence = (symmetry * 50 + head_prominence * 50) * 100

            # Price target: neckline - (head - neckline)
            price_target = neckline - (head - neckline)

            return PatternResult(
                pattern_type=PatternType.HEAD_AND_SHOULDERS,
                confidence=min(confidence, 95),
                direction="bearish",
                start_index=left_shoulder_idx,
                end_index=right_shoulder_idx,
                price_target=price_target,
                stop_loss=head * 1.02,
                description=f"H&S pattern detected. Neckline at {neckline:.2f}, target {price_target:.2f}"
            )

        return None

    def detect_double_top(
        self,
        highs: List[float],
        closes: List[float]
    ) -> Optional[PatternResult]:
        """
        Detect Double Top pattern.

        Two peaks at roughly the same level with a trough between them.
        Bearish reversal pattern.
        """
        maxima, minima = self.find_local_extrema(highs, window=3)

        if len(maxima) < 2:
            return None

        for i in range(len(maxima) - 1):
            first_top_idx = maxima[i]
            second_top_idx = maxima[i + 1]

            first_top = highs[first_top_idx]
            second_top = highs[second_top_idx]

            # Tops should be roughly equal
            top_diff = abs(first_top - second_top) / first_top
            if top_diff > self.tolerance:
                continue

            # Find trough between tops
            trough_indices = [m for m in minima if first_top_idx < m < second_top_idx]
            if not trough_indices:
                continue

            trough = min(highs[idx] for idx in trough_indices)

            # Trough should be significantly lower than tops
            if (first_top - trough) / first_top < 0.03:
                continue

            confidence = (1 - top_diff) * 100
            price_target = trough - (first_top - trough)

            return PatternResult(
                pattern_type=PatternType.DOUBLE_TOP,
                confidence=min(confidence, 90),
                direction="bearish",
                start_index=first_top_idx,
                end_index=second_top_idx,
                price_target=price_target,
                stop_loss=max(first_top, second_top) * 1.01,
                description=f"Double Top at {first_top:.2f}, target {price_target:.2f}"
            )

        return None

    def detect_double_bottom(
        self,
        lows: List[float],
        closes: List[float]
    ) -> Optional[PatternResult]:
        """
        Detect Double Bottom pattern.

        Two troughs at roughly the same level with a peak between them.
        Bullish reversal pattern.
        """
        maxima, minima = self.find_local_extrema(lows, window=3)

        if len(minima) < 2:
            return None

        for i in range(len(minima) - 1):
            first_bottom_idx = minima[i]
            second_bottom_idx = minima[i + 1]

            first_bottom = lows[first_bottom_idx]
            second_bottom = lows[second_bottom_idx]

            # Bottoms should be roughly equal
            bottom_diff = abs(first_bottom - second_bottom) / first_bottom
            if bottom_diff > self.tolerance:
                continue

            # Find peak between bottoms
            peak_indices = [m for m in maxima if first_bottom_idx < m < second_bottom_idx]
            if not peak_indices:
                continue

            peak = max(lows[idx] for idx in peak_indices)

            # Peak should be significantly higher than bottoms
            if (peak - first_bottom) / first_bottom < 0.03:
                continue

            confidence = (1 - bottom_diff) * 100
            price_target = peak + (peak - first_bottom)

            return PatternResult(
                pattern_type=PatternType.DOUBLE_BOTTOM,
                confidence=min(confidence, 90),
                direction="bullish",
                start_index=first_bottom_idx,
                end_index=second_bottom_idx,
                price_target=price_target,
                stop_loss=min(first_bottom, second_bottom) * 0.99,
                description=f"Double Bottom at {first_bottom:.2f}, target {price_target:.2f}"
            )

        return None

    def detect_triangle(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[PatternResult]:
        """
        Detect triangle patterns (ascending, descending, symmetrical).
        """
        if len(highs) < 20:
            return None

        # Use recent data
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]

        maxima, minima = self.find_local_extrema(recent_highs, window=2)

        if len(maxima) < 2 or len(minima) < 2:
            return None

        # Calculate trendlines
        high_slope = (recent_highs[maxima[-1]] - recent_highs[maxima[0]]) / (maxima[-1] - maxima[0]) if maxima[-1] != maxima[0] else 0

        minima_lows, _ = self.find_local_extrema([-l for l in recent_lows], window=2)
        low_slope = (recent_lows[minima[-1]] - recent_lows[minima[0]]) / (minima[-1] - minima[0]) if minima[-1] != minima[0] else 0

        # Classify triangle type
        if high_slope < -0.001 and low_slope > 0.001:
            # Converging - symmetrical triangle
            pattern_type = PatternType.SYMMETRICAL_TRIANGLE
            direction = "neutral"  # Can break either way
            confidence = 70
        elif abs(high_slope) < 0.001 and low_slope > 0.001:
            # Flat top, rising bottom - ascending triangle (bullish)
            pattern_type = PatternType.ASCENDING_TRIANGLE
            direction = "bullish"
            confidence = 75
        elif high_slope < -0.001 and abs(low_slope) < 0.001:
            # Falling top, flat bottom - descending triangle (bearish)
            pattern_type = PatternType.DESCENDING_TRIANGLE
            direction = "bearish"
            confidence = 75
        else:
            return None

        return PatternResult(
            pattern_type=pattern_type,
            confidence=confidence,
            direction=direction,
            start_index=len(highs) - 20,
            end_index=len(highs) - 1,
            description=f"{pattern_type.value} pattern forming"
        )

    def detect_candlestick_patterns(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> List[PatternResult]:
        """
        Detect single and multi-candle patterns.
        """
        patterns = []

        if len(closes) < 3:
            return patterns

        # Check last few candles
        for i in range(max(0, len(closes) - 5), len(closes)):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            body = abs(c - o)
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            total_range = h - l

            if total_range == 0:
                continue

            # Doji - small body, long wicks
            if body / total_range < 0.1:
                patterns.append(PatternResult(
                    pattern_type=PatternType.DOJI,
                    confidence=80,
                    direction="neutral",
                    start_index=i,
                    end_index=i,
                    description="Doji - indecision candle"
                ))

            # Hammer - small body at top, long lower wick (bullish)
            elif lower_wick > body * 2 and upper_wick < body * 0.5 and c > o:
                patterns.append(PatternResult(
                    pattern_type=PatternType.HAMMER,
                    confidence=75,
                    direction="bullish",
                    start_index=i,
                    end_index=i,
                    description="Hammer - potential bullish reversal"
                ))

            # Inverted Hammer - small body at bottom, long upper wick
            elif upper_wick > body * 2 and lower_wick < body * 0.5 and c < o:
                patterns.append(PatternResult(
                    pattern_type=PatternType.INVERTED_HAMMER,
                    confidence=70,
                    direction="bullish",
                    start_index=i,
                    end_index=i,
                    description="Inverted Hammer - potential bullish reversal"
                ))

        # Multi-candle patterns
        if len(closes) >= 2:
            # Engulfing patterns
            prev_o, prev_c = opens[-2], closes[-2]
            curr_o, curr_c = opens[-1], closes[-1]

            # Bullish engulfing
            if prev_c < prev_o and curr_c > curr_o:  # Red then green
                if curr_o < prev_c and curr_c > prev_o:  # Green engulfs red
                    patterns.append(PatternResult(
                        pattern_type=PatternType.ENGULFING_BULLISH,
                        confidence=80,
                        direction="bullish",
                        start_index=len(closes) - 2,
                        end_index=len(closes) - 1,
                        description="Bullish Engulfing - strong reversal signal"
                    ))

            # Bearish engulfing
            if prev_c > prev_o and curr_c < curr_o:  # Green then red
                if curr_o > prev_c and curr_c < prev_o:  # Red engulfs green
                    patterns.append(PatternResult(
                        pattern_type=PatternType.ENGULFING_BEARISH,
                        confidence=80,
                        direction="bearish",
                        start_index=len(closes) - 2,
                        end_index=len(closes) - 1,
                        description="Bearish Engulfing - strong reversal signal"
                    ))

        return patterns

    def analyze(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Dict[str, Any]:
        """
        Run full pattern analysis on price data.

        Returns all detected patterns sorted by confidence.
        """
        patterns = []

        # Detect chart patterns
        h_and_s = self.detect_head_and_shoulders(highs, lows, closes)
        if h_and_s:
            patterns.append(h_and_s)

        double_top = self.detect_double_top(highs, closes)
        if double_top:
            patterns.append(double_top)

        double_bottom = self.detect_double_bottom(lows, closes)
        if double_bottom:
            patterns.append(double_bottom)

        triangle = self.detect_triangle(highs, lows, closes)
        if triangle:
            patterns.append(triangle)

        # Detect candlestick patterns
        candle_patterns = self.detect_candlestick_patterns(opens, highs, lows, closes)
        patterns.extend(candle_patterns)

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        # Determine overall bias
        bullish_score = sum(p.confidence for p in patterns if p.direction == "bullish")
        bearish_score = sum(p.confidence for p in patterns if p.direction == "bearish")

        if bullish_score > bearish_score + 20:
            bias = "bullish"
        elif bearish_score > bullish_score + 20:
            bias = "bearish"
        else:
            bias = "neutral"

        return {
            "patterns": [
                {
                    "type": p.pattern_type.value,
                    "confidence": p.confidence,
                    "direction": p.direction,
                    "description": p.description,
                    "price_target": p.price_target,
                    "stop_loss": p.stop_loss,
                }
                for p in patterns
            ],
            "pattern_count": len(patterns),
            "bias": bias,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
        }


# Singleton instance
_pattern_service = None

def get_pattern_service() -> PatternRecognitionService:
    """Get singleton pattern service instance"""
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternRecognitionService()
    return _pattern_service
