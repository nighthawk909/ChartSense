"""
Volume Profile Analysis Service
Analyzes volume distribution at price levels for trading decisions

This service provides:
1. Volume Profile calculation (VP)
2. Point of Control (POC) identification
3. Value Area High/Low (VAH/VAL)
4. Volume nodes (HVN/LVN) detection
5. Trading signals based on volume profile
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class VolumeNode:
    """A significant volume node"""
    price_level: float
    volume: int
    volume_pct: float  # Percentage of total volume
    is_high_volume: bool  # HVN = True, LVN = False


@dataclass
class VolumeProfile:
    """Volume Profile analysis result"""
    symbol: str
    timeframe: str  # e.g., "session", "weekly", "monthly"

    # Key levels
    poc: float           # Point of Control - highest volume price
    vah: float           # Value Area High
    val: float           # Value Area Low
    value_area_pct: float  # Percentage of volume in value area (typically 70%)

    # Price range
    profile_high: float
    profile_low: float

    # Volume distribution
    total_volume: int
    bins: List[Dict[str, Any]]  # Price bins with volume

    # Important nodes
    high_volume_nodes: List[VolumeNode]
    low_volume_nodes: List[VolumeNode]

    # Context
    current_price: float
    price_vs_poc: str  # "above", "below", "at"
    price_vs_value_area: str  # "above", "below", "inside"

    # Trading signals
    support_levels: List[float]
    resistance_levels: List[float]

    # Metadata
    calculated_at: datetime = None
    bars_used: int = 0

    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.now()


class VolumeProfileAnalyzer:
    """
    Analyzes volume distribution across price levels.

    Volume Profile shows where trading activity occurred,
    helping identify:
    - Support/resistance based on high volume
    - Potential breakout zones at low volume
    - Fair value areas
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize volume profile analyzer.

        Args:
            alpaca_service: AlpacaService for market data
        """
        self.alpaca = alpaca_service

        # Configuration
        self.value_area_pct = 70  # Standard 70% value area
        self.num_bins = 50        # Number of price bins
        self.hvn_threshold = 2.0  # Stddev above mean for HVN
        self.lvn_threshold = 0.5  # Stddev below mean for LVN

        # Cache
        self._profile_cache: Dict[str, VolumeProfile] = {}
        self._cache_ttl_minutes = 30

    def set_alpaca_service(self, alpaca_service):
        """Set the Alpaca service"""
        self.alpaca = alpaca_service

    # ==================== PROFILE CALCULATION ====================

    async def calculate_session_profile(
        self,
        symbol: str,
        days_back: int = 1,
    ) -> Optional[VolumeProfile]:
        """
        Calculate volume profile for recent session(s).

        Args:
            symbol: Stock symbol
            days_back: Number of trading days

        Returns:
            VolumeProfile object
        """
        if not self.alpaca:
            return None

        try:
            # Get intraday bars for detailed volume distribution
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="5min",
                limit=days_back * 78,  # ~78 5-min bars per day
            )

            if not bars or len(bars) < 10:
                return None

            return self._build_profile(symbol, bars, "session")

        except Exception as e:
            logger.error(f"Error calculating session profile for {symbol}: {e}")
            return None

    async def calculate_weekly_profile(self, symbol: str) -> Optional[VolumeProfile]:
        """Calculate volume profile for the past week"""
        return await self.calculate_session_profile(symbol, days_back=5)

    async def calculate_monthly_profile(self, symbol: str) -> Optional[VolumeProfile]:
        """Calculate volume profile for the past month"""
        if not self.alpaca:
            return None

        try:
            # Use daily bars for monthly profile
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1day",
                limit=22,  # ~22 trading days per month
            )

            if not bars or len(bars) < 5:
                return None

            return self._build_profile(symbol, bars, "monthly")

        except Exception as e:
            logger.error(f"Error calculating monthly profile for {symbol}: {e}")
            return None

    def _build_profile(
        self,
        symbol: str,
        bars: List[Dict],
        timeframe: str,
    ) -> VolumeProfile:
        """Build volume profile from bars"""

        # Get current price from last bar
        current_price = bars[-1]["close"]

        # Find price range
        all_highs = [b["high"] for b in bars]
        all_lows = [b["low"] for b in bars]
        profile_high = max(all_highs)
        profile_low = min(all_lows)
        price_range = profile_high - profile_low

        if price_range <= 0:
            return None

        # Create price bins
        bin_size = price_range / self.num_bins
        volume_by_bin = defaultdict(int)

        # Distribute volume across price levels
        for bar in bars:
            bar_volume = bar["volume"]
            bar_high = bar["high"]
            bar_low = bar["low"]
            bar_range = bar_high - bar_low

            if bar_range <= 0:
                # All volume at close price
                bin_idx = int((bar["close"] - profile_low) / bin_size)
                bin_idx = max(0, min(self.num_bins - 1, bin_idx))
                volume_by_bin[bin_idx] += bar_volume
            else:
                # Distribute volume across the bar's range
                # Using Volume Price Trend (simplified TPO-style)
                for price_level in [bar_low, (bar_low + bar_high) / 2, bar_high]:
                    bin_idx = int((price_level - profile_low) / bin_size)
                    bin_idx = max(0, min(self.num_bins - 1, bin_idx))
                    volume_by_bin[bin_idx] += bar_volume // 3

        total_volume = sum(volume_by_bin.values())

        # Create bins list
        bins = []
        for i in range(self.num_bins):
            bin_low = profile_low + i * bin_size
            bin_high = bin_low + bin_size
            bin_mid = (bin_low + bin_high) / 2
            volume = volume_by_bin.get(i, 0)
            volume_pct = (volume / total_volume * 100) if total_volume > 0 else 0

            bins.append({
                "price_low": round(bin_low, 2),
                "price_high": round(bin_high, 2),
                "price_mid": round(bin_mid, 2),
                "volume": volume,
                "volume_pct": round(volume_pct, 2),
            })

        # Find POC (Point of Control) - bin with highest volume
        poc_bin = max(bins, key=lambda b: b["volume"])
        poc = poc_bin["price_mid"]

        # Calculate Value Area (70% of volume around POC)
        vah, val = self._calculate_value_area(bins, poc, total_volume)

        # Identify HVN and LVN
        hvn, lvn = self._identify_volume_nodes(bins, total_volume)

        # Determine price position
        price_vs_poc = "at" if abs(current_price - poc) / poc < 0.005 else (
            "above" if current_price > poc else "below"
        )

        price_vs_value_area = "inside" if val <= current_price <= vah else (
            "above" if current_price > vah else "below"
        )

        # Identify support and resistance levels
        support_levels = [n.price_level for n in hvn if n.price_level < current_price][:3]
        resistance_levels = [n.price_level for n in hvn if n.price_level > current_price][:3]

        return VolumeProfile(
            symbol=symbol,
            timeframe=timeframe,
            poc=poc,
            vah=vah,
            val=val,
            value_area_pct=self.value_area_pct,
            profile_high=profile_high,
            profile_low=profile_low,
            total_volume=total_volume,
            bins=bins,
            high_volume_nodes=hvn,
            low_volume_nodes=lvn,
            current_price=current_price,
            price_vs_poc=price_vs_poc,
            price_vs_value_area=price_vs_value_area,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            bars_used=len(bars),
        )

    def _calculate_value_area(
        self,
        bins: List[Dict],
        poc: float,
        total_volume: int,
    ) -> Tuple[float, float]:
        """Calculate Value Area High and Low"""
        target_volume = total_volume * (self.value_area_pct / 100)
        accumulated_volume = 0

        # Sort bins by volume descending
        sorted_bins = sorted(bins, key=lambda b: b["volume"], reverse=True)

        value_area_bins = []
        for bin_data in sorted_bins:
            value_area_bins.append(bin_data)
            accumulated_volume += bin_data["volume"]
            if accumulated_volume >= target_volume:
                break

        if not value_area_bins:
            # Fallback to middle bins
            mid_idx = len(bins) // 2
            return bins[mid_idx + 5]["price_high"], bins[mid_idx - 5]["price_low"]

        # Find VAH and VAL from value area bins
        vah = max(b["price_high"] for b in value_area_bins)
        val = min(b["price_low"] for b in value_area_bins)

        return round(vah, 2), round(val, 2)

    def _identify_volume_nodes(
        self,
        bins: List[Dict],
        total_volume: int,
    ) -> Tuple[List[VolumeNode], List[VolumeNode]]:
        """Identify High Volume Nodes and Low Volume Nodes"""
        volumes = [b["volume"] for b in bins if b["volume"] > 0]

        if not volumes:
            return [], []

        mean_vol = statistics.mean(volumes)
        std_vol = statistics.stdev(volumes) if len(volumes) > 1 else 0

        hvn = []
        lvn = []

        for bin_data in bins:
            volume = bin_data["volume"]
            volume_pct = (volume / total_volume * 100) if total_volume > 0 else 0

            if std_vol > 0:
                z_score = (volume - mean_vol) / std_vol

                if z_score >= self.hvn_threshold:
                    hvn.append(VolumeNode(
                        price_level=bin_data["price_mid"],
                        volume=volume,
                        volume_pct=volume_pct,
                        is_high_volume=True,
                    ))
                elif z_score <= -self.lvn_threshold:
                    lvn.append(VolumeNode(
                        price_level=bin_data["price_mid"],
                        volume=volume,
                        volume_pct=volume_pct,
                        is_high_volume=False,
                    ))

        # Sort HVN by volume (highest first), LVN by price
        hvn.sort(key=lambda n: n.volume, reverse=True)
        lvn.sort(key=lambda n: n.price_level)

        return hvn[:5], lvn[:5]  # Return top 5 of each

    # ==================== TRADING SIGNALS ====================

    async def get_trading_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Get trading signal based on volume profile.

        Returns:
            Dict with signal type, levels, and reasoning
        """
        # Try cache first
        cache_key = symbol
        profile = self._profile_cache.get(cache_key)

        if not profile or (datetime.now() - profile.calculated_at).seconds > self._cache_ttl_minutes * 60:
            profile = await self.calculate_session_profile(symbol)
            if profile:
                self._profile_cache[cache_key] = profile

        if not profile:
            return {
                "symbol": symbol,
                "signal": "NO_DATA",
                "confidence": 0,
                "levels": {},
                "reasoning": ["Unable to calculate volume profile"],
            }

        signal = {
            "symbol": symbol,
            "signal": "NEUTRAL",
            "confidence": 50,
            "levels": {
                "poc": profile.poc,
                "vah": profile.vah,
                "val": profile.val,
                "support": profile.support_levels,
                "resistance": profile.resistance_levels,
            },
            "reasoning": [],
            "action_zones": [],
        }

        # Price at POC = equilibrium
        if profile.price_vs_poc == "at":
            signal["signal"] = "NEUTRAL"
            signal["reasoning"].append("Price at POC - fair value zone")

        # Price below value area = potential long
        elif profile.price_vs_value_area == "below":
            signal["signal"] = "BULLISH"
            signal["confidence"] = 65
            signal["reasoning"].append("Price below value area - potential value buy")
            signal["action_zones"].append({
                "type": "entry_zone",
                "direction": "long",
                "price_range": [profile.val * 0.99, profile.val],
                "target": profile.poc,
            })

        # Price above value area = potential short or trend
        elif profile.price_vs_value_area == "above":
            # Could be bullish trend or short opportunity
            signal["signal"] = "CAUTIOUS"
            signal["confidence"] = 55
            signal["reasoning"].append("Price above value area - extended or trending")

        # Check for HVN support/resistance
        for hvn in profile.high_volume_nodes:
            if abs(profile.current_price - hvn.price_level) / profile.current_price < 0.02:
                signal["reasoning"].append(f"Near HVN at ${hvn.price_level:.2f}")
                if hvn.price_level < profile.current_price:
                    signal["confidence"] += 10
                    signal["reasoning"].append("HVN support nearby")

        # Check for LVN (potential fast moves through these)
        for lvn in profile.low_volume_nodes:
            if profile.val < lvn.price_level < profile.vah:
                signal["reasoning"].append(f"LVN at ${lvn.price_level:.2f} - potential fast move zone")

        return signal

    # ==================== ANALYSIS ====================

    def analyze_breakout_potential(self, profile: VolumeProfile) -> Dict[str, Any]:
        """Analyze breakout potential based on volume profile"""
        analysis = {
            "upside_breakout_potential": "low",
            "downside_breakout_potential": "low",
            "key_levels_to_watch": [],
            "notes": [],
        }

        # Check for LVN above current price (easy upside)
        for lvn in profile.low_volume_nodes:
            if lvn.price_level > profile.current_price:
                analysis["upside_breakout_potential"] = "high"
                analysis["key_levels_to_watch"].append(lvn.price_level)
                analysis["notes"].append(f"LVN above at ${lvn.price_level:.2f} - low resistance")

        # Check for LVN below current price (easy downside)
        for lvn in profile.low_volume_nodes:
            if lvn.price_level < profile.current_price:
                analysis["downside_breakout_potential"] = "high"
                analysis["key_levels_to_watch"].append(lvn.price_level)
                analysis["notes"].append(f"LVN below at ${lvn.price_level:.2f} - low support")

        # Value area width indicates potential
        va_width = (profile.vah - profile.val) / profile.poc
        if va_width < 0.02:  # Tight value area
            analysis["notes"].append("Tight value area - breakout likely")

        return analysis

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get analyzer status"""
        return {
            "enabled": self.alpaca is not None,
            "cached_profiles": len(self._profile_cache),
            "cache_ttl_minutes": self._cache_ttl_minutes,
            "config": {
                "value_area_pct": self.value_area_pct,
                "num_bins": self.num_bins,
                "hvn_threshold": self.hvn_threshold,
                "lvn_threshold": self.lvn_threshold,
            },
        }


# Singleton instance
_volume_analyzer: Optional[VolumeProfileAnalyzer] = None


def get_volume_analyzer() -> VolumeProfileAnalyzer:
    """Get the global volume profile analyzer"""
    global _volume_analyzer
    if _volume_analyzer is None:
        _volume_analyzer = VolumeProfileAnalyzer()
    return _volume_analyzer
