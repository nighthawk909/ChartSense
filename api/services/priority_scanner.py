"""
Priority Tier Scanner Service
Implements smart scanning with dynamic priority based on volatility and volume
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class PriorityTier(str, Enum):
    """Priority tiers for symbol scanning"""
    HIGH = "HIGH"       # Tier 1: Every 3 seconds - High volatility or news spike
    STANDARD = "STANDARD"  # Tier 2: Every 30 seconds - Normal watchlist
    LOW = "LOW"         # Tier 3: Every 3 minutes - Low activity, consolidating


@dataclass
class SymbolPriority:
    """Priority data for a single symbol"""
    symbol: str
    tier: PriorityTier = PriorityTier.STANDARD
    last_scan_time: Optional[datetime] = None
    scan_count: int = 0

    # Volatility metrics
    volume_ratio: float = 1.0  # Current volume / average volume
    volatility_ratio: float = 1.0  # Current ATR / average ATR
    price_change_pct: float = 0.0

    # Sentiment/news indicators
    has_news_spike: bool = False
    sentiment_score: float = 0.5  # 0-1, 0.5 is neutral

    # Historical accuracy at this symbol
    historical_win_rate: float = 0.5
    signals_generated: int = 0

    # Timing
    time_in_current_tier: int = 0  # seconds
    tier_change_reason: str = ""

    def should_scan(self) -> bool:
        """Check if this symbol should be scanned based on its tier"""
        if self.last_scan_time is None:
            return True

        elapsed = (datetime.now() - self.last_scan_time).total_seconds()

        if self.tier == PriorityTier.HIGH:
            return elapsed >= 3  # 3 seconds
        elif self.tier == PriorityTier.STANDARD:
            return elapsed >= 30  # 30 seconds
        else:  # LOW
            return elapsed >= 180  # 3 minutes

    def get_scan_interval(self) -> int:
        """Get scan interval in seconds for this tier"""
        if self.tier == PriorityTier.HIGH:
            return 3
        elif self.tier == PriorityTier.STANDARD:
            return 30
        else:
            return 180


class PriorityScannerService:
    """
    Smart scanning service with dynamic priority tiers.

    Tier 1 (HIGH Priority) - 3 second scans:
        - Volume > 200% of average
        - News/sentiment spike detected
        - Price moved > 2% in last hour
        - Strong signal detected recently

    Tier 2 (STANDARD Priority) - 30 second scans:
        - Normal watchlist symbols
        - Price within normal Bollinger Bands
        - Moderate activity

    Tier 3 (LOW Priority) - 3 minute scans:
        - Low volume (< 50% of average)
        - Price consolidating in tight range
        - No recent signals
    """

    def __init__(self):
        self._symbol_priorities: Dict[str, SymbolPriority] = {}
        self._total_scans: int = 0
        self._scans_by_tier: Dict[PriorityTier, int] = {
            PriorityTier.HIGH: 0,
            PriorityTier.STANDARD: 0,
            PriorityTier.LOW: 0,
        }
        self._last_priority_update: Optional[datetime] = None

        # Thresholds for tier promotion/demotion
        self.HIGH_VOLUME_THRESHOLD = 2.0  # 200% of average
        self.HIGH_VOLATILITY_THRESHOLD = 1.5  # 150% of average ATR
        self.HIGH_PRICE_CHANGE_THRESHOLD = 2.0  # 2% price change

        self.LOW_VOLUME_THRESHOLD = 0.5  # 50% of average
        self.LOW_VOLATILITY_THRESHOLD = 0.7  # 70% of average ATR

    def register_symbol(self, symbol: str, initial_tier: PriorityTier = PriorityTier.STANDARD) -> SymbolPriority:
        """Register a symbol for priority tracking"""
        if symbol not in self._symbol_priorities:
            self._symbol_priorities[symbol] = SymbolPriority(
                symbol=symbol,
                tier=initial_tier
            )
            logger.debug(f"Registered {symbol} in {initial_tier.value} tier")
        return self._symbol_priorities[symbol]

    def register_symbols(self, symbols: List[str]) -> None:
        """Register multiple symbols"""
        for symbol in symbols:
            self.register_symbol(symbol)

    def update_symbol_metrics(
        self,
        symbol: str,
        volume_ratio: float = 1.0,
        volatility_ratio: float = 1.0,
        price_change_pct: float = 0.0,
        has_news_spike: bool = False,
        sentiment_score: float = 0.5,
    ) -> PriorityTier:
        """
        Update metrics for a symbol and recalculate its priority tier.

        Returns the new tier.
        """
        priority = self._symbol_priorities.get(symbol)
        if not priority:
            priority = self.register_symbol(symbol)

        # Update metrics
        priority.volume_ratio = volume_ratio
        priority.volatility_ratio = volatility_ratio
        priority.price_change_pct = price_change_pct
        priority.has_news_spike = has_news_spike
        priority.sentiment_score = sentiment_score

        # Calculate new tier
        old_tier = priority.tier
        new_tier = self._calculate_tier(priority)

        if new_tier != old_tier:
            priority.tier = new_tier
            priority.time_in_current_tier = 0
            priority.tier_change_reason = self._get_tier_change_reason(priority)
            logger.info(f"{symbol} tier changed: {old_tier.value} -> {new_tier.value} ({priority.tier_change_reason})")

        return new_tier

    def _calculate_tier(self, priority: SymbolPriority) -> PriorityTier:
        """Calculate the appropriate tier for a symbol based on its metrics"""

        # Check for HIGH tier conditions
        if (
            priority.volume_ratio >= self.HIGH_VOLUME_THRESHOLD or
            priority.volatility_ratio >= self.HIGH_VOLATILITY_THRESHOLD or
            abs(priority.price_change_pct) >= self.HIGH_PRICE_CHANGE_THRESHOLD or
            priority.has_news_spike
        ):
            return PriorityTier.HIGH

        # Check for LOW tier conditions
        if (
            priority.volume_ratio <= self.LOW_VOLUME_THRESHOLD and
            priority.volatility_ratio <= self.LOW_VOLATILITY_THRESHOLD and
            abs(priority.price_change_pct) < 0.5  # Less than 0.5% movement
        ):
            return PriorityTier.LOW

        # Default to STANDARD
        return PriorityTier.STANDARD

    def _get_tier_change_reason(self, priority: SymbolPriority) -> str:
        """Get human-readable reason for tier placement"""
        reasons = []

        if priority.tier == PriorityTier.HIGH:
            if priority.volume_ratio >= self.HIGH_VOLUME_THRESHOLD:
                reasons.append(f"High volume ({priority.volume_ratio:.1f}x)")
            if priority.volatility_ratio >= self.HIGH_VOLATILITY_THRESHOLD:
                reasons.append(f"High volatility ({priority.volatility_ratio:.1f}x)")
            if abs(priority.price_change_pct) >= self.HIGH_PRICE_CHANGE_THRESHOLD:
                reasons.append(f"Large price move ({priority.price_change_pct:+.1f}%)")
            if priority.has_news_spike:
                reasons.append("News spike")
        elif priority.tier == PriorityTier.LOW:
            reasons.append("Low activity, consolidating")
        else:
            reasons.append("Normal activity")

        return "; ".join(reasons) if reasons else "Standard monitoring"

    def get_symbols_to_scan(self) -> List[str]:
        """Get list of symbols that should be scanned now, ordered by priority"""
        to_scan = []

        # Sort by tier (HIGH first) then by time since last scan
        sorted_priorities = sorted(
            self._symbol_priorities.values(),
            key=lambda p: (
                0 if p.tier == PriorityTier.HIGH else 1 if p.tier == PriorityTier.STANDARD else 2,
                p.last_scan_time or datetime.min
            )
        )

        for priority in sorted_priorities:
            if priority.should_scan():
                to_scan.append(priority.symbol)

        return to_scan

    def get_next_symbol_to_scan(self) -> Optional[str]:
        """Get the single highest priority symbol to scan next"""
        symbols = self.get_symbols_to_scan()
        return symbols[0] if symbols else None

    def record_scan(self, symbol: str) -> None:
        """Record that a symbol was just scanned"""
        priority = self._symbol_priorities.get(symbol)
        if priority:
            priority.last_scan_time = datetime.now()
            priority.scan_count += 1
            self._total_scans += 1
            self._scans_by_tier[priority.tier] += 1

    def record_signal(self, symbol: str, signal_type: str, confidence: float) -> None:
        """Record that a signal was generated for a symbol"""
        priority = self._symbol_priorities.get(symbol)
        if priority:
            priority.signals_generated += 1

            # If strong signal, promote to HIGH tier temporarily
            if confidence >= 70 and signal_type in ["BUY", "STRONG_BUY"]:
                priority.tier = PriorityTier.HIGH
                priority.tier_change_reason = f"Strong {signal_type} signal at {confidence:.0f}%"
                logger.info(f"{symbol} promoted to HIGH tier: {priority.tier_change_reason}")

    def get_tier_summary(self) -> Dict[str, Any]:
        """Get summary of current tier distribution"""
        tier_counts = {tier: 0 for tier in PriorityTier}
        for priority in self._symbol_priorities.values():
            tier_counts[priority.tier] += 1

        return {
            "total_symbols": len(self._symbol_priorities),
            "tier_distribution": {
                "high": tier_counts[PriorityTier.HIGH],
                "standard": tier_counts[PriorityTier.STANDARD],
                "low": tier_counts[PriorityTier.LOW],
            },
            "total_scans": self._total_scans,
            "scans_by_tier": {
                "high": self._scans_by_tier[PriorityTier.HIGH],
                "standard": self._scans_by_tier[PriorityTier.STANDARD],
                "low": self._scans_by_tier[PriorityTier.LOW],
            },
        }

    def get_symbol_priority(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get priority info for a specific symbol"""
        priority = self._symbol_priorities.get(symbol)
        if not priority:
            return None

        return {
            "symbol": priority.symbol,
            "tier": priority.tier.value,
            "scan_interval_seconds": priority.get_scan_interval(),
            "last_scan_time": priority.last_scan_time.isoformat() if priority.last_scan_time else None,
            "scan_count": priority.scan_count,
            "volume_ratio": priority.volume_ratio,
            "volatility_ratio": priority.volatility_ratio,
            "price_change_pct": priority.price_change_pct,
            "has_news_spike": priority.has_news_spike,
            "tier_change_reason": priority.tier_change_reason,
            "should_scan_now": priority.should_scan(),
        }

    def get_all_priorities(self) -> List[Dict[str, Any]]:
        """Get priority info for all registered symbols"""
        return [
            self.get_symbol_priority(symbol)
            for symbol in self._symbol_priorities.keys()
        ]

    def demote_inactive_symbols(self, inactivity_threshold_minutes: int = 30) -> int:
        """
        Demote symbols that have been in HIGH tier without signals for too long.
        Returns count of demoted symbols.
        """
        demoted = 0
        threshold = timedelta(minutes=inactivity_threshold_minutes)

        for priority in self._symbol_priorities.values():
            if priority.tier == PriorityTier.HIGH:
                if priority.last_scan_time:
                    priority.time_in_current_tier = int(
                        (datetime.now() - priority.last_scan_time).total_seconds()
                    )

                # If HIGH for too long without new signals, demote to STANDARD
                if priority.time_in_current_tier > threshold.total_seconds():
                    if priority.signals_generated == 0:
                        priority.tier = PriorityTier.STANDARD
                        priority.tier_change_reason = "Demoted: No signals in HIGH tier"
                        priority.time_in_current_tier = 0
                        demoted += 1
                        logger.info(f"{priority.symbol} demoted to STANDARD: inactivity")

        return demoted


# Singleton instance
_priority_scanner: Optional[PriorityScannerService] = None


def get_priority_scanner() -> PriorityScannerService:
    """Get singleton priority scanner instance"""
    global _priority_scanner
    if _priority_scanner is None:
        _priority_scanner = PriorityScannerService()
    return _priority_scanner
