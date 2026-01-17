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

    # Elliott Wave
    ELLIOTT_IMPULSE = "elliott_impulse"
    ELLIOTT_CORRECTIVE = "elliott_corrective"

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


@dataclass
class SupportResistanceLevel:
    """Support or resistance level"""
    price: float
    level_type: str  # "support" or "resistance"
    strength: float  # 0-100
    touches: int
    first_touch_index: int
    last_touch_index: int


@dataclass
class TrendLine:
    """Trend line data"""
    slope: float
    intercept: float
    line_type: str  # "support", "resistance", "channel_upper", "channel_lower"
    direction: str  # "up", "down", "horizontal"
    strength: float
    start_index: int
    end_index: int
    touches: int


@dataclass
class ElliottWave:
    """Elliott Wave analysis result"""
    wave_count: int  # Current wave number (1-5 for impulse, A-C for corrective)
    wave_type: str  # "impulse" or "corrective"
    wave_degree: str  # "primary", "intermediate", "minor"
    direction: str  # "bullish" or "bearish"
    current_position: str  # Description of current wave position
    wave_points: List[Dict[str, Any]]  # Price points for each wave
    confidence: float
    next_target: Optional[float] = None
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

    def detect_bull_flag(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> Optional[PatternResult]:
        """
        Detect Bull Flag pattern.

        Characteristics:
        - Strong upward move (flagpole)
        - Consolidation with slight downward drift (flag)
        - Volume typically decreases during flag formation
        - Bullish continuation pattern
        """
        if len(closes) < 20:
            return None

        # Look for flagpole - strong upward move in recent data
        lookback = min(30, len(closes))
        recent_closes = closes[-lookback:]
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]

        # Find the highest point (potential end of flagpole)
        max_idx = recent_highs.index(max(recent_highs))

        # Flagpole should be in the first 60% of the lookback
        if max_idx < 5 or max_idx > lookback * 0.6:
            return None

        # Calculate flagpole move
        pole_start_idx = 0
        pole_start_price = min(recent_lows[:max_idx+1])
        pole_end_price = recent_highs[max_idx]
        pole_move = (pole_end_price - pole_start_price) / pole_start_price

        # Flagpole should be at least 5% move
        if pole_move < 0.05:
            return None

        # Check for flag consolidation after flagpole
        flag_data = recent_closes[max_idx:]
        if len(flag_data) < 3:
            return None

        # Flag should drift slightly down or sideways
        flag_start = flag_data[0]
        flag_end = flag_data[-1]
        flag_drift = (flag_end - flag_start) / flag_start

        # Flag should not retrace more than 50% of the pole
        flag_low = min(recent_lows[max_idx:])
        retracement = (pole_end_price - flag_low) / (pole_end_price - pole_start_price)

        if retracement > 0.5 or flag_drift > 0.02:  # Flag drifting up too much
            return None

        # Calculate confidence
        confidence = 60
        if retracement < 0.38:  # Shallow retracement is better
            confidence += 15
        if -0.05 < flag_drift < 0:  # Slight downward drift
            confidence += 10
        if volumes and len(volumes) >= lookback:
            # Volume should decrease during flag
            pole_volume = sum(volumes[-lookback:-lookback+max_idx])
            flag_volume = sum(volumes[-lookback+max_idx:])
            if flag_volume < pole_volume * 0.7:
                confidence += 15

        # Price target: flagpole height projected from flag breakout
        price_target = flag_end + (pole_end_price - pole_start_price)

        return PatternResult(
            pattern_type=PatternType.BULL_FLAG,
            confidence=min(confidence, 90),
            direction="bullish",
            start_index=len(closes) - lookback,
            end_index=len(closes) - 1,
            price_target=price_target,
            stop_loss=flag_low * 0.98,
            description=f"Bull Flag forming. Target: ${price_target:.2f}. Pole: +{pole_move*100:.1f}%"
        )

    def detect_bear_flag(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> Optional[PatternResult]:
        """
        Detect Bear Flag pattern.

        Characteristics:
        - Strong downward move (flagpole)
        - Consolidation with slight upward drift (flag)
        - Volume typically decreases during flag formation
        - Bearish continuation pattern
        """
        if len(closes) < 20:
            return None

        lookback = min(30, len(closes))
        recent_closes = closes[-lookback:]
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]

        # Find the lowest point (potential end of flagpole)
        min_idx = recent_lows.index(min(recent_lows))

        if min_idx < 5 or min_idx > lookback * 0.6:
            return None

        # Calculate flagpole move (downward)
        pole_start_price = max(recent_highs[:min_idx+1])
        pole_end_price = recent_lows[min_idx]
        pole_move = (pole_start_price - pole_end_price) / pole_start_price

        if pole_move < 0.05:
            return None

        # Check for flag consolidation
        flag_data = recent_closes[min_idx:]
        if len(flag_data) < 3:
            return None

        flag_start = flag_data[0]
        flag_end = flag_data[-1]
        flag_drift = (flag_end - flag_start) / flag_start

        # Flag should not retrace more than 50%
        flag_high = max(recent_highs[min_idx:])
        retracement = (flag_high - pole_end_price) / (pole_start_price - pole_end_price)

        if retracement > 0.5 or flag_drift < -0.02:
            return None

        confidence = 60
        if retracement < 0.38:
            confidence += 15
        if 0 < flag_drift < 0.05:
            confidence += 10
        if volumes and len(volumes) >= lookback:
            pole_volume = sum(volumes[-lookback:-lookback+min_idx])
            flag_volume = sum(volumes[-lookback+min_idx:])
            if flag_volume < pole_volume * 0.7:
                confidence += 15

        price_target = flag_end - (pole_start_price - pole_end_price)

        return PatternResult(
            pattern_type=PatternType.BEAR_FLAG,
            confidence=min(confidence, 90),
            direction="bearish",
            start_index=len(closes) - lookback,
            end_index=len(closes) - 1,
            price_target=price_target,
            stop_loss=flag_high * 1.02,
            description=f"Bear Flag forming. Target: ${price_target:.2f}. Pole: -{pole_move*100:.1f}%"
        )

    def detect_breakout(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> Optional[PatternResult]:
        """
        Detect price breakouts from consolidation or key levels.

        Types of breakouts detected:
        - Range breakout (breaking out of consolidation)
        - Resistance breakout (breaking above key resistance)
        - Support breakdown (breaking below key support)
        """
        if len(closes) < 20:
            return None

        # Get support/resistance levels
        sr_levels = self.detect_support_resistance(highs, lows, closes)
        current_price = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current_price

        # Check for resistance breakout
        for sr in sr_levels:
            if sr.level_type == "resistance" and sr.strength >= 50:
                # Price broke above resistance
                if prev_close < sr.price and current_price > sr.price:
                    breakout_pct = (current_price - sr.price) / sr.price * 100

                    # Confirm with volume if available
                    volume_confirmed = True
                    if volumes and len(volumes) >= 20:
                        avg_volume = sum(volumes[-20:-1]) / 19
                        current_volume = volumes[-1]
                        volume_confirmed = current_volume > avg_volume * 1.3

                    confidence = 60 + (sr.strength * 0.2)
                    if volume_confirmed:
                        confidence += 15

                    # Target: resistance + (resistance - nearest support)
                    supports = [s for s in sr_levels if s.level_type == "support"]
                    if supports:
                        nearest_support = max(s.price for s in supports if s.price < sr.price)
                        price_target = sr.price + (sr.price - nearest_support)
                    else:
                        price_target = sr.price * 1.05

                    return PatternResult(
                        pattern_type=PatternType.ASCENDING_TRIANGLE,  # Use as breakout proxy
                        confidence=min(confidence, 90),
                        direction="bullish",
                        start_index=len(closes) - 5,
                        end_index=len(closes) - 1,
                        price_target=price_target,
                        stop_loss=sr.price * 0.98,
                        description=f"BREAKOUT! Price broke above ${sr.price:.2f} resistance (+{breakout_pct:.1f}%)"
                    )

            # Check for support breakdown
            elif sr.level_type == "support" and sr.strength >= 50:
                if prev_close > sr.price and current_price < sr.price:
                    breakdown_pct = (sr.price - current_price) / sr.price * 100

                    volume_confirmed = True
                    if volumes and len(volumes) >= 20:
                        avg_volume = sum(volumes[-20:-1]) / 19
                        current_volume = volumes[-1]
                        volume_confirmed = current_volume > avg_volume * 1.3

                    confidence = 60 + (sr.strength * 0.2)
                    if volume_confirmed:
                        confidence += 15

                    resistances = [s for s in sr_levels if s.level_type == "resistance"]
                    if resistances:
                        nearest_resistance = min(s.price for s in resistances if s.price > sr.price)
                        price_target = sr.price - (nearest_resistance - sr.price)
                    else:
                        price_target = sr.price * 0.95

                    return PatternResult(
                        pattern_type=PatternType.DESCENDING_TRIANGLE,  # Use as breakdown proxy
                        confidence=min(confidence, 90),
                        direction="bearish",
                        start_index=len(closes) - 5,
                        end_index=len(closes) - 1,
                        price_target=price_target,
                        stop_loss=sr.price * 1.02,
                        description=f"BREAKDOWN! Price broke below ${sr.price:.2f} support (-{breakdown_pct:.1f}%)"
                    )

        # Check for range breakout (consolidation breakout)
        lookback = 20
        if len(closes) >= lookback:
            recent_highs = highs[-lookback:-1]
            recent_lows = lows[-lookback:-1]
            range_high = max(recent_highs)
            range_low = min(recent_lows)
            range_size = (range_high - range_low) / range_low

            # Tight consolidation (less than 5% range)
            if range_size < 0.05:
                if current_price > range_high:
                    # Bullish breakout from consolidation
                    breakout_pct = (current_price - range_high) / range_high * 100
                    confidence = 70

                    if volumes and len(volumes) >= lookback:
                        avg_volume = sum(volumes[-lookback:-1]) / (lookback - 1)
                        if volumes[-1] > avg_volume * 1.5:
                            confidence += 15

                    return PatternResult(
                        pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                        confidence=min(confidence, 85),
                        direction="bullish",
                        start_index=len(closes) - lookback,
                        end_index=len(closes) - 1,
                        price_target=range_high + (range_high - range_low),
                        stop_loss=range_high * 0.98,
                        description=f"RANGE BREAKOUT! Broke above ${range_high:.2f} consolidation"
                    )

                elif current_price < range_low:
                    breakdown_pct = (range_low - current_price) / range_low * 100
                    confidence = 70

                    if volumes and len(volumes) >= lookback:
                        avg_volume = sum(volumes[-lookback:-1]) / (lookback - 1)
                        if volumes[-1] > avg_volume * 1.5:
                            confidence += 15

                    return PatternResult(
                        pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                        confidence=min(confidence, 85),
                        direction="bearish",
                        start_index=len(closes) - lookback,
                        end_index=len(closes) - 1,
                        price_target=range_low - (range_high - range_low),
                        stop_loss=range_low * 1.02,
                        description=f"RANGE BREAKDOWN! Broke below ${range_low:.2f} consolidation"
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

    def detect_support_resistance(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        tolerance: float = 0.02
    ) -> List[SupportResistanceLevel]:
        """
        Detect support and resistance levels based on price clusters.

        Uses pivot points and price clustering to identify key levels.
        """
        levels = []

        if len(closes) < 20:
            return levels

        # Find pivot highs and lows
        maxima, minima = self.find_local_extrema(closes, window=5)

        # Group similar price levels
        all_pivots = []
        for idx in maxima:
            all_pivots.append({'price': highs[idx], 'type': 'high', 'index': idx})
        for idx in minima:
            all_pivots.append({'price': lows[idx], 'type': 'low', 'index': idx})

        if not all_pivots:
            return levels

        # Cluster pivots by price proximity
        all_pivots.sort(key=lambda x: x['price'])
        clusters = []
        current_cluster = [all_pivots[0]]

        for pivot in all_pivots[1:]:
            if abs(pivot['price'] - current_cluster[-1]['price']) / current_cluster[-1]['price'] < tolerance:
                current_cluster.append(pivot)
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [pivot]

        if len(current_cluster) >= 2:
            clusters.append(current_cluster)

        # Create S/R levels from clusters
        current_price = closes[-1]
        for cluster in clusters:
            avg_price = sum(p['price'] for p in cluster) / len(cluster)
            touches = len(cluster)
            first_touch = min(p['index'] for p in cluster)
            last_touch = max(p['index'] for p in cluster)

            # Determine if support or resistance
            if avg_price < current_price:
                level_type = "support"
            else:
                level_type = "resistance"

            # Calculate strength based on touches and recency
            recency_factor = 1 - (len(closes) - last_touch) / len(closes)
            strength = min(100, touches * 20 + recency_factor * 30)

            levels.append(SupportResistanceLevel(
                price=round(avg_price, 2),
                level_type=level_type,
                strength=strength,
                touches=touches,
                first_touch_index=first_touch,
                last_touch_index=last_touch
            ))

        # Sort by strength
        levels.sort(key=lambda x: x.strength, reverse=True)
        return levels[:10]  # Return top 10 levels

    def detect_trend_lines(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> List[TrendLine]:
        """
        Detect trend lines using linear regression on pivot points.
        """
        trend_lines = []

        if len(closes) < 20:
            return trend_lines

        maxima, minima = self.find_local_extrema(closes, window=3)

        # Support trend line (connecting lows)
        if len(minima) >= 2:
            # Use linear regression on minima
            x_vals = np.array(minima)
            y_vals = np.array([lows[i] for i in minima])

            if len(x_vals) >= 2:
                slope, intercept = np.polyfit(x_vals, y_vals, 1)

                # Count touches (points close to the line)
                touches = 0
                for i, idx in enumerate(minima):
                    expected = slope * idx + intercept
                    if abs(lows[idx] - expected) / expected < 0.01:
                        touches += 1

                direction = "up" if slope > 0.001 else "down" if slope < -0.001 else "horizontal"
                strength = min(100, touches * 25 + 25)

                trend_lines.append(TrendLine(
                    slope=float(slope),
                    intercept=float(intercept),
                    line_type="support",
                    direction=direction,
                    strength=strength,
                    start_index=minima[0],
                    end_index=minima[-1],
                    touches=touches
                ))

        # Resistance trend line (connecting highs)
        if len(maxima) >= 2:
            x_vals = np.array(maxima)
            y_vals = np.array([highs[i] for i in maxima])

            if len(x_vals) >= 2:
                slope, intercept = np.polyfit(x_vals, y_vals, 1)

                touches = 0
                for idx in maxima:
                    expected = slope * idx + intercept
                    if abs(highs[idx] - expected) / expected < 0.01:
                        touches += 1

                direction = "up" if slope > 0.001 else "down" if slope < -0.001 else "horizontal"
                strength = min(100, touches * 25 + 25)

                trend_lines.append(TrendLine(
                    slope=float(slope),
                    intercept=float(intercept),
                    line_type="resistance",
                    direction=direction,
                    strength=strength,
                    start_index=maxima[0],
                    end_index=maxima[-1],
                    touches=touches
                ))

        return trend_lines

    def detect_elliott_wave(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[ElliottWave]:
        """
        Detect Elliott Wave patterns.

        Elliott Wave Theory:
        - Impulse waves: 5 waves in the direction of the trend (1-2-3-4-5)
        - Corrective waves: 3 waves against the trend (A-B-C)

        Rules:
        1. Wave 2 cannot retrace more than 100% of Wave 1
        2. Wave 3 cannot be the shortest of waves 1, 3, 5
        3. Wave 4 cannot overlap Wave 1 (except in diagonals)
        """
        if len(closes) < 30:
            return None

        # Find significant pivot points
        maxima, minima = self.find_local_extrema(closes, window=5)

        if len(maxima) < 3 or len(minima) < 3:
            return None

        # Combine and sort all pivots
        all_pivots = []
        for idx in maxima:
            all_pivots.append({'index': idx, 'price': highs[idx], 'type': 'high'})
        for idx in minima:
            all_pivots.append({'index': idx, 'price': lows[idx], 'type': 'low'})

        all_pivots.sort(key=lambda x: x['index'])

        # Determine overall trend
        start_price = closes[0]
        end_price = closes[-1]
        trend_direction = "bullish" if end_price > start_price else "bearish"

        # Try to identify 5-wave impulse pattern
        wave_points = []
        confidence = 0

        # For bullish trend: Low -> High -> Low -> High -> Low -> High
        # For bearish trend: High -> Low -> High -> Low -> High -> Low
        if trend_direction == "bullish":
            expected_sequence = ['low', 'high', 'low', 'high', 'low', 'high']
        else:
            expected_sequence = ['high', 'low', 'high', 'low', 'high', 'low']

        # Find matching sequence
        sequence_idx = 0
        for pivot in all_pivots:
            if sequence_idx < len(expected_sequence):
                if pivot['type'] == expected_sequence[sequence_idx]:
                    wave_points.append({
                        'wave': sequence_idx,
                        'index': pivot['index'],
                        'price': pivot['price'],
                        'type': pivot['type']
                    })
                    sequence_idx += 1

        # Validate Elliott Wave rules
        if len(wave_points) >= 5:
            # This is a potential impulse wave
            wave_type = "impulse"

            # Wave 1: point 0 to 1
            # Wave 2: point 1 to 2
            # Wave 3: point 2 to 3
            # Wave 4: point 3 to 4
            # Wave 5: point 4 to 5

            if len(wave_points) >= 6:
                w1 = abs(wave_points[1]['price'] - wave_points[0]['price'])
                w2 = abs(wave_points[2]['price'] - wave_points[1]['price'])
                w3 = abs(wave_points[3]['price'] - wave_points[2]['price'])
                w4 = abs(wave_points[4]['price'] - wave_points[3]['price'])
                w5 = abs(wave_points[5]['price'] - wave_points[4]['price'])

                # Rule 1: Wave 2 < Wave 1
                rule1 = w2 < w1
                # Rule 2: Wave 3 is not the shortest
                rule2 = not (w3 < w1 and w3 < w5)
                # Rule 3: Wave 4 doesn't overlap Wave 1
                if trend_direction == "bullish":
                    rule3 = wave_points[4]['price'] > wave_points[1]['price']
                else:
                    rule3 = wave_points[4]['price'] < wave_points[1]['price']

                confidence = 0
                if rule1:
                    confidence += 30
                if rule2:
                    confidence += 40
                if rule3:
                    confidence += 30

                # Determine current wave position
                current_wave = len(wave_points)
                if current_wave >= 6:
                    current_position = "Wave 5 complete - expect correction"
                    # Fibonacci targets for correction
                    if trend_direction == "bullish":
                        next_target = wave_points[5]['price'] - (w3 * 0.382)
                    else:
                        next_target = wave_points[5]['price'] + (w3 * 0.382)
                else:
                    current_position = f"In Wave {current_wave}"
                    # Project next wave using Fibonacci
                    if current_wave % 2 == 0:  # In corrective sub-wave
                        next_target = wave_points[-1]['price']
                    else:
                        if trend_direction == "bullish":
                            next_target = wave_points[-1]['price'] + (w3 * 1.618 if w3 else w1 * 1.618)
                        else:
                            next_target = wave_points[-1]['price'] - (w3 * 1.618 if w3 else w1 * 1.618)

                return ElliottWave(
                    wave_count=min(len(wave_points) - 1, 5),
                    wave_type=wave_type,
                    wave_degree="intermediate",
                    direction=trend_direction,
                    current_position=current_position,
                    wave_points=wave_points,
                    confidence=confidence,
                    next_target=round(next_target, 2) if next_target else None,
                    description=f"Elliott {wave_type.title()} Wave - {current_position}"
                )

        # Check for corrective pattern (3 waves)
        elif len(wave_points) >= 3:
            wave_type = "corrective"
            current_position = f"Wave {chr(65 + len(wave_points) - 1)}"  # A, B, C

            return ElliottWave(
                wave_count=len(wave_points),
                wave_type=wave_type,
                wave_degree="intermediate",
                direction="bearish" if trend_direction == "bullish" else "bullish",
                current_position=current_position,
                wave_points=wave_points,
                confidence=60,
                description=f"Elliott Corrective Wave - {current_position}"
            )

        return None

    def analyze(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
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

        # Detect flag patterns
        bull_flag = self.detect_bull_flag(highs, lows, closes, volumes)
        if bull_flag:
            patterns.append(bull_flag)

        bear_flag = self.detect_bear_flag(highs, lows, closes, volumes)
        if bear_flag:
            patterns.append(bear_flag)

        # Detect breakouts
        breakout = self.detect_breakout(highs, lows, closes, volumes)
        if breakout:
            patterns.append(breakout)

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

        # Detect support/resistance levels
        sr_levels = self.detect_support_resistance(highs, lows, closes)

        # Detect trend lines
        trend_lines = self.detect_trend_lines(highs, lows, closes)

        # Detect Elliott Wave
        elliott = self.detect_elliott_wave(highs, lows, closes)

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
            "support_resistance": [
                {
                    "price": sr.price,
                    "type": sr.level_type,
                    "strength": sr.strength,
                    "touches": sr.touches,
                }
                for sr in sr_levels
            ],
            "trend_lines": [
                {
                    "slope": tl.slope,
                    "intercept": tl.intercept,
                    "type": tl.line_type,
                    "direction": tl.direction,
                    "strength": tl.strength,
                    "touches": tl.touches,
                    "start_index": tl.start_index,
                    "end_index": tl.end_index,
                }
                for tl in trend_lines
            ],
            "elliott_wave": {
                "wave_count": elliott.wave_count,
                "wave_type": elliott.wave_type,
                "wave_degree": elliott.wave_degree,
                "direction": elliott.direction,
                "current_position": elliott.current_position,
                "confidence": elliott.confidence,
                "next_target": elliott.next_target,
                "description": elliott.description,
                "wave_points": elliott.wave_points,
            } if elliott else None,
        }


# Singleton instance
_pattern_service = None

def get_pattern_service() -> PatternRecognitionService:
    """Get singleton pattern service instance"""
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternRecognitionService()
    return _pattern_service
