"""
Pre-market Gap Scanner Service
Identifies stocks with significant overnight gaps for trading opportunities

This service provides:
1. Pre-market gap detection
2. Gap classification (full gap, partial gap, up/down)
3. Gap fill probability analysis
4. Trading signals based on gap patterns
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
import pytz

logger = logging.getLogger(__name__)


class GapType(str, Enum):
    """Type of price gap"""
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    FULL_GAP_UP = "full_gap_up"      # Open above previous high
    FULL_GAP_DOWN = "full_gap_down"  # Open below previous low
    NO_GAP = "no_gap"


class GapStrategy(str, Enum):
    """Trading strategy for the gap"""
    FADE = "fade"              # Trade against the gap (gap fill expected)
    FOLLOW = "follow"          # Trade with the gap (continuation expected)
    WAIT = "wait"              # Wait for confirmation
    AVOID = "avoid"            # Too risky


@dataclass
class GapScanResult:
    """Result of gap scan for a symbol"""
    symbol: str
    gap_type: GapType
    gap_percent: float
    gap_amount: float  # Dollar amount

    # Previous day data
    prev_close: float
    prev_high: float
    prev_low: float

    # Current pre-market data
    pre_market_price: float
    pre_market_volume: int
    pre_market_high: float
    pre_market_low: float

    # Analysis
    is_full_gap: bool  # Above prev high (up) or below prev low (down)
    relative_volume: float  # Compared to avg pre-market volume
    atr: Optional[float]  # Average True Range
    gap_atr_ratio: float  # Gap size relative to ATR

    # Prediction
    fill_probability: float  # 0-100, likelihood of gap fill
    suggested_strategy: GapStrategy
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None

    # Confidence
    signal_strength: float = 0  # 0-100

    # Metadata
    scan_time: datetime = None
    notes: List[str] = None

    def __post_init__(self):
        if self.scan_time is None:
            self.scan_time = datetime.now()
        if self.notes is None:
            self.notes = []


class GapScanner:
    """
    Scans for pre-market gaps and provides trading signals.

    Best run between 4:00 AM - 9:30 AM ET when pre-market data is available.
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize gap scanner.

        Args:
            alpaca_service: AlpacaService for market data
        """
        self.alpaca = alpaca_service

        # Configuration
        self.min_gap_percent = 1.0     # Minimum gap to consider (%)
        self.max_gap_percent = 10.0    # Maximum gap (above this = too risky)
        self.min_price = 5.0           # Minimum stock price
        self.min_volume = 10000        # Minimum pre-market volume

        # Historical gap fill statistics (simplified)
        # In reality, these would be calculated from historical data
        self._gap_fill_rates = {
            "small_up": 0.65,      # 1-3% gap up fills 65% of time
            "medium_up": 0.55,    # 3-5% gap up fills 55%
            "large_up": 0.40,     # >5% gap up fills 40%
            "small_down": 0.70,   # 1-3% gap down fills 70%
            "medium_down": 0.60,  # 3-5% gap down fills 60%
            "large_down": 0.45,   # >5% gap down fills 45%
        }

        # Cache
        self._scan_results: Dict[str, GapScanResult] = {}
        self._last_scan_time: Optional[datetime] = None

    def set_alpaca_service(self, alpaca_service):
        """Set the Alpaca service"""
        self.alpaca = alpaca_service

    # ==================== SCANNING ====================

    async def scan_symbols(
        self,
        symbols: List[str],
        min_gap_pct: Optional[float] = None,
    ) -> List[GapScanResult]:
        """
        Scan multiple symbols for gaps.

        Args:
            symbols: List of symbols to scan
            min_gap_pct: Minimum gap percentage to include

        Returns:
            List of GapScanResult objects for stocks with gaps
        """
        min_gap = min_gap_pct or self.min_gap_percent
        results = []

        for symbol in symbols:
            try:
                result = await self.scan_symbol(symbol)
                if result and abs(result.gap_percent) >= min_gap:
                    results.append(result)
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")

        # Sort by absolute gap size
        results.sort(key=lambda x: abs(x.gap_percent), reverse=True)

        self._last_scan_time = datetime.now()
        return results

    async def scan_symbol(self, symbol: str) -> Optional[GapScanResult]:
        """
        Scan a single symbol for gaps.

        Args:
            symbol: Stock symbol

        Returns:
            GapScanResult or None if no significant gap
        """
        if not self.alpaca:
            logger.warning("Alpaca service not set")
            return None

        try:
            # Get previous day's data
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1day",
                limit=5,
            )

            if not bars or len(bars) < 2:
                return None

            prev_bar = bars[-2]  # Previous day
            prev_close = prev_bar["close"]
            prev_high = prev_bar["high"]
            prev_low = prev_bar["low"]

            # Get current pre-market data
            try:
                quote = await self.alpaca.get_latest_quote(symbol)
                current_price = (quote["bid_price"] + quote["ask_price"]) / 2
            except:
                # Fall back to latest trade
                trade = await self.alpaca.get_latest_trade(symbol)
                current_price = trade["price"]

            # Skip if price too low
            if current_price < self.min_price:
                return None

            # Calculate gap
            gap_amount = current_price - prev_close
            gap_percent = (gap_amount / prev_close) * 100

            # Skip if gap too small
            if abs(gap_percent) < self.min_gap_percent:
                return None

            # Determine gap type
            if gap_percent > 0:
                if current_price > prev_high:
                    gap_type = GapType.FULL_GAP_UP
                    is_full_gap = True
                else:
                    gap_type = GapType.GAP_UP
                    is_full_gap = False
            else:
                if current_price < prev_low:
                    gap_type = GapType.FULL_GAP_DOWN
                    is_full_gap = True
                else:
                    gap_type = GapType.GAP_DOWN
                    is_full_gap = False

            # Calculate ATR for context
            atr = self._calculate_atr(bars)
            gap_atr_ratio = abs(gap_amount) / atr if atr else 0

            # Get fill probability
            fill_prob = self._calculate_fill_probability(gap_percent, gap_type, is_full_gap)

            # Determine strategy
            strategy, entry, stop, target = self._determine_strategy(
                gap_type=gap_type,
                gap_percent=gap_percent,
                current_price=current_price,
                prev_close=prev_close,
                prev_high=prev_high,
                prev_low=prev_low,
                fill_probability=fill_prob,
                atr=atr,
            )

            # Calculate signal strength
            signal_strength = self._calculate_signal_strength(
                gap_percent=gap_percent,
                fill_probability=fill_prob,
                gap_atr_ratio=gap_atr_ratio,
                strategy=strategy,
            )

            result = GapScanResult(
                symbol=symbol,
                gap_type=gap_type,
                gap_percent=gap_percent,
                gap_amount=gap_amount,
                prev_close=prev_close,
                prev_high=prev_high,
                prev_low=prev_low,
                pre_market_price=current_price,
                pre_market_volume=0,  # Would need separate call
                pre_market_high=current_price,
                pre_market_low=current_price,
                is_full_gap=is_full_gap,
                relative_volume=0,
                atr=atr,
                gap_atr_ratio=gap_atr_ratio,
                fill_probability=fill_prob,
                suggested_strategy=strategy,
                entry_price=entry,
                stop_loss=stop,
                target_price=target,
                signal_strength=signal_strength,
            )

            # Add notes
            result.notes = self._generate_notes(result)

            # Cache result
            self._scan_results[symbol] = result

            return result

        except Exception as e:
            logger.error(f"Error scanning {symbol} for gaps: {e}")
            return None

    def _calculate_atr(self, bars: List[Dict]) -> float:
        """Calculate Average True Range from bars"""
        if len(bars) < 2:
            return 0

        true_ranges = []
        for i in range(1, len(bars)):
            high = bars[i]["high"]
            low = bars[i]["low"]
            prev_close = bars[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        return sum(true_ranges) / len(true_ranges) if true_ranges else 0

    def _calculate_fill_probability(
        self,
        gap_percent: float,
        gap_type: GapType,
        is_full_gap: bool,
    ) -> float:
        """Calculate probability of gap filling"""
        abs_gap = abs(gap_percent)
        is_up = gap_type in [GapType.GAP_UP, GapType.FULL_GAP_UP]

        # Base probabilities from historical statistics
        if abs_gap <= 3:
            key = "small_up" if is_up else "small_down"
        elif abs_gap <= 5:
            key = "medium_up" if is_up else "medium_down"
        else:
            key = "large_up" if is_up else "large_down"

        base_prob = self._gap_fill_rates.get(key, 0.5)

        # Adjust for full gaps (less likely to fill)
        if is_full_gap:
            base_prob *= 0.8

        # Convert to percentage
        return min(95, max(5, base_prob * 100))

    def _determine_strategy(
        self,
        gap_type: GapType,
        gap_percent: float,
        current_price: float,
        prev_close: float,
        prev_high: float,
        prev_low: float,
        fill_probability: float,
        atr: Optional[float],
    ) -> Tuple[GapStrategy, Optional[float], Optional[float], Optional[float]]:
        """
        Determine trading strategy for the gap.

        Returns:
            (strategy, entry_price, stop_loss, target_price)
        """
        abs_gap = abs(gap_percent)

        # Too large = avoid
        if abs_gap > self.max_gap_percent:
            return GapStrategy.AVOID, None, None, None

        # Full gaps are often continuation patterns
        if gap_type == GapType.FULL_GAP_UP:
            if fill_probability < 40:
                # Low fill probability = follow the gap
                entry = current_price
                stop = prev_high * 0.995  # Just below previous high
                target = current_price * (1 + abs_gap / 200)  # Target based on gap size
                return GapStrategy.FOLLOW, entry, stop, target
            else:
                return GapStrategy.WAIT, None, None, None

        elif gap_type == GapType.FULL_GAP_DOWN:
            if fill_probability < 40:
                # Short opportunity
                return GapStrategy.FOLLOW, current_price, prev_low * 1.005, current_price * 0.97
            else:
                return GapStrategy.WAIT, None, None, None

        # Regular gaps often fill
        elif gap_type == GapType.GAP_UP:
            if fill_probability > 60:
                # Fade the gap (short or wait for pullback)
                entry = current_price * 0.995  # Enter on slight pullback
                stop = current_price * 1.02     # Stop above high
                target = prev_close * 1.002    # Target near gap fill
                return GapStrategy.FADE, entry, stop, target
            else:
                return GapStrategy.WAIT, None, None, None

        elif gap_type == GapType.GAP_DOWN:
            if fill_probability > 60:
                # Fade the gap (buy for gap fill)
                entry = current_price * 1.005  # Enter on slight bounce
                stop = current_price * 0.98    # Stop below low
                target = prev_close * 0.998   # Target near gap fill
                return GapStrategy.FADE, entry, stop, target
            else:
                return GapStrategy.WAIT, None, None, None

        return GapStrategy.WAIT, None, None, None

    def _calculate_signal_strength(
        self,
        gap_percent: float,
        fill_probability: float,
        gap_atr_ratio: float,
        strategy: GapStrategy,
    ) -> float:
        """Calculate signal strength (0-100)"""
        if strategy in [GapStrategy.AVOID, GapStrategy.WAIT]:
            return 0

        strength = 50

        # Optimal gap size (2-4%) adds strength
        abs_gap = abs(gap_percent)
        if 2 <= abs_gap <= 4:
            strength += 15
        elif 1 <= abs_gap < 2:
            strength += 5
        elif abs_gap > 4:
            strength -= 10

        # High fill probability for fade strategy adds strength
        if strategy == GapStrategy.FADE:
            strength += (fill_probability - 50) * 0.5

        # Reasonable ATR ratio adds strength
        if 0.5 <= gap_atr_ratio <= 2:
            strength += 10

        return max(0, min(100, strength))

    def _generate_notes(self, result: GapScanResult) -> List[str]:
        """Generate analysis notes"""
        notes = []

        if result.is_full_gap:
            if result.gap_type in [GapType.FULL_GAP_UP]:
                notes.append("Full gap up - potential continuation or exhaustion")
            else:
                notes.append("Full gap down - potential continuation or exhaustion")

        if result.fill_probability > 65:
            notes.append(f"High fill probability ({result.fill_probability:.0f}%) - fade setup")
        elif result.fill_probability < 35:
            notes.append(f"Low fill probability ({result.fill_probability:.0f}%) - trend continuation")

        if result.gap_atr_ratio > 2:
            notes.append("Large gap relative to ATR - higher volatility expected")

        if abs(result.gap_percent) > 5:
            notes.append("Large gap - wait for first 15 minutes of action")

        return notes

    # ==================== QUERIES ====================

    def get_top_gaps(self, direction: str = "both", limit: int = 10) -> List[GapScanResult]:
        """
        Get top gaps from recent scan.

        Args:
            direction: "up", "down", or "both"
            limit: Maximum results

        Returns:
            List of GapScanResult
        """
        results = list(self._scan_results.values())

        if direction == "up":
            results = [r for r in results if r.gap_percent > 0]
        elif direction == "down":
            results = [r for r in results if r.gap_percent < 0]

        results.sort(key=lambda x: abs(x.gap_percent), reverse=True)
        return results[:limit]

    def get_actionable_gaps(self) -> List[GapScanResult]:
        """Get gaps with actionable trading strategies"""
        results = list(self._scan_results.values())
        return [
            r for r in results
            if r.suggested_strategy in [GapStrategy.FADE, GapStrategy.FOLLOW]
            and r.signal_strength >= 60
        ]

    # ==================== MARKET HOURS ====================

    def is_premarket_hours(self) -> bool:
        """Check if currently in pre-market hours"""
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)

        # Pre-market: 4:00 AM - 9:30 AM ET
        pre_market_start = time(4, 0)
        pre_market_end = time(9, 30)

        current_time = now.time()
        return pre_market_start <= current_time < pre_market_end

    def should_scan(self) -> Tuple[bool, str]:
        """Check if gap scanning is appropriate right now"""
        if self.is_premarket_hours():
            return True, "Pre-market hours - gap scanning active"

        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()

        if current_time < time(4, 0):
            return False, "Too early - pre-market not yet open"
        elif current_time >= time(9, 30) and current_time < time(10, 0):
            return True, "First 30 min of market - gaps may still trade"
        else:
            return False, "Outside optimal gap scanning hours"

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get scanner status"""
        can_scan, reason = self.should_scan()

        return {
            "enabled": self.alpaca is not None,
            "can_scan": can_scan,
            "scan_reason": reason,
            "is_premarket": self.is_premarket_hours(),
            "last_scan": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "cached_results": len(self._scan_results),
            "config": {
                "min_gap_percent": self.min_gap_percent,
                "max_gap_percent": self.max_gap_percent,
                "min_price": self.min_price,
            },
            "top_gaps": [
                {
                    "symbol": r.symbol,
                    "gap_percent": r.gap_percent,
                    "gap_type": r.gap_type.value,
                    "strategy": r.suggested_strategy.value,
                    "signal_strength": r.signal_strength,
                }
                for r in self.get_top_gaps(limit=5)
            ],
        }


# Singleton instance
_gap_scanner: Optional[GapScanner] = None


def get_gap_scanner() -> GapScanner:
    """Get the global gap scanner instance"""
    global _gap_scanner
    if _gap_scanner is None:
        _gap_scanner = GapScanner()
    return _gap_scanner
