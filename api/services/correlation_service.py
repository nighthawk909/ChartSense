"""
Correlation Service
Calculates and monitors correlations between positions to prevent over-concentration

This service provides:
1. Real-time correlation calculation
2. Portfolio correlation analysis
3. Position correlation checks before entry
4. Dynamic correlation-based position limits
"""
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CorrelationPair:
    """Correlation between two symbols"""
    symbol_a: str
    symbol_b: str
    correlation: float  # -1 to 1
    correlation_type: str  # "positive", "negative", "neutral"
    calculated_at: datetime
    lookback_days: int


@dataclass
class PortfolioCorrelationResult:
    """Portfolio-wide correlation analysis"""
    average_correlation: float
    max_correlation: float
    highly_correlated_pairs: List[CorrelationPair]
    diversification_score: float  # 0-100
    concentration_risk: str  # "low", "medium", "high"
    recommendations: List[str]


class CorrelationService:
    """
    Service for calculating and monitoring correlations.

    Helps prevent over-concentration in correlated assets
    by analyzing price movements and sector relationships.
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize correlation service.

        Args:
            alpaca_service: AlpacaService for price data
        """
        self.alpaca = alpaca_service

        # Configuration
        self.high_correlation_threshold = 0.7   # Above this = highly correlated
        self.negative_correlation_threshold = -0.5  # Below this = negatively correlated
        self.lookback_days = 30  # Days of data for correlation

        # Max correlated positions
        self.max_correlated_positions = 3

        # Cache
        self._correlation_cache: Dict[str, CorrelationPair] = {}
        self._cache_ttl_hours = 24

        # Known sector/group correlations (fallback)
        self._sector_correlations = {
            # Tech stocks tend to move together
            ("AAPL", "MSFT"): 0.75,
            ("AAPL", "GOOGL"): 0.70,
            ("MSFT", "GOOGL"): 0.72,
            ("NVDA", "AMD"): 0.80,
            ("NVDA", "INTC"): 0.65,

            # Banks
            ("JPM", "BAC"): 0.85,
            ("JPM", "WFC"): 0.82,
            ("BAC", "WFC"): 0.88,

            # Energy
            ("XOM", "CVX"): 0.90,
            ("XOM", "COP"): 0.85,

            # Crypto
            ("BTC/USD", "ETH/USD"): 0.85,
            ("BTCUSD", "ETHUSD"): 0.85,
        }

        # Sector mappings for quick lookup
        self._symbol_sectors = {
            "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
            "AMZN": "Technology", "META": "Technology", "NVDA": "Semiconductors",
            "AMD": "Semiconductors", "INTC": "Semiconductors",
            "JPM": "Financials", "BAC": "Financials", "WFC": "Financials",
            "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
            "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
            "BTC/USD": "Crypto", "ETH/USD": "Crypto", "BTCUSD": "Crypto", "ETHUSD": "Crypto",
        }

    def set_alpaca_service(self, alpaca_service):
        """Set the Alpaca service"""
        self.alpaca = alpaca_service

    # ==================== CORRELATION CALCULATION ====================

    async def calculate_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        days: int = None,
    ) -> Optional[CorrelationPair]:
        """
        Calculate correlation between two symbols.

        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            days: Lookback period (default: self.lookback_days)

        Returns:
            CorrelationPair object
        """
        days = days or self.lookback_days

        # Check cache first
        cache_key = self._make_cache_key(symbol_a, symbol_b)
        cached = self._get_cached_correlation(cache_key)
        if cached:
            return cached

        # Check known correlations
        known = self._get_known_correlation(symbol_a, symbol_b)
        if known is not None:
            pair = CorrelationPair(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                correlation=known,
                correlation_type=self._classify_correlation(known),
                calculated_at=datetime.now(),
                lookback_days=0,  # Using static data
            )
            return pair

        # Calculate from price data
        if self.alpaca:
            try:
                returns_a = await self._get_returns(symbol_a, days)
                returns_b = await self._get_returns(symbol_b, days)

                if returns_a is None or returns_b is None:
                    return None

                # Need same length
                min_len = min(len(returns_a), len(returns_b))
                if min_len < 10:  # Need at least 10 data points
                    return None

                returns_a = returns_a[-min_len:]
                returns_b = returns_b[-min_len:]

                # Calculate Pearson correlation
                correlation = np.corrcoef(returns_a, returns_b)[0, 1]

                pair = CorrelationPair(
                    symbol_a=symbol_a,
                    symbol_b=symbol_b,
                    correlation=float(correlation),
                    correlation_type=self._classify_correlation(correlation),
                    calculated_at=datetime.now(),
                    lookback_days=days,
                )

                # Cache result
                self._cache_correlation(cache_key, pair)

                return pair

            except Exception as e:
                logger.error(f"Error calculating correlation {symbol_a}/{symbol_b}: {e}")

        # Fallback: use sector-based estimate
        sector_corr = self._estimate_sector_correlation(symbol_a, symbol_b)
        return CorrelationPair(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            correlation=sector_corr,
            correlation_type=self._classify_correlation(sector_corr),
            calculated_at=datetime.now(),
            lookback_days=0,
        )

    async def _get_returns(self, symbol: str, days: int) -> Optional[List[float]]:
        """Get daily returns for a symbol"""
        try:
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1day",
                limit=days + 5,  # Extra buffer
            )

            if not bars or len(bars) < 2:
                return None

            # Calculate daily returns
            returns = []
            for i in range(1, len(bars)):
                prev_close = bars[i - 1]["close"]
                curr_close = bars[i]["close"]
                if prev_close > 0:
                    ret = (curr_close - prev_close) / prev_close
                    returns.append(ret)

            return returns

        except Exception as e:
            logger.debug(f"Could not get returns for {symbol}: {e}")
            return None

    def _classify_correlation(self, correlation: float) -> str:
        """Classify correlation strength"""
        if correlation >= self.high_correlation_threshold:
            return "positive"
        elif correlation <= self.negative_correlation_threshold:
            return "negative"
        return "neutral"

    def _get_known_correlation(self, symbol_a: str, symbol_b: str) -> Optional[float]:
        """Get known/static correlation"""
        # Check both orderings
        key1 = (symbol_a.upper(), symbol_b.upper())
        key2 = (symbol_b.upper(), symbol_a.upper())

        if key1 in self._sector_correlations:
            return self._sector_correlations[key1]
        if key2 in self._sector_correlations:
            return self._sector_correlations[key2]

        return None

    def _estimate_sector_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Estimate correlation based on sectors"""
        sector_a = self._symbol_sectors.get(symbol_a.upper(), "Unknown")
        sector_b = self._symbol_sectors.get(symbol_b.upper(), "Unknown")

        # Same sector = higher correlation
        if sector_a == sector_b and sector_a != "Unknown":
            return 0.6

        # Different sectors = lower correlation
        return 0.2

    # ==================== PORTFOLIO ANALYSIS ====================

    async def analyze_portfolio_correlation(
        self,
        positions: List[Dict[str, Any]],
    ) -> PortfolioCorrelationResult:
        """
        Analyze correlation across entire portfolio.

        Args:
            positions: List of position dictionaries with 'symbol' key

        Returns:
            PortfolioCorrelationResult
        """
        if not positions or len(positions) < 2:
            return PortfolioCorrelationResult(
                average_correlation=0,
                max_correlation=0,
                highly_correlated_pairs=[],
                diversification_score=100,
                concentration_risk="low",
                recommendations=["Portfolio has few positions - diversification not assessed"],
            )

        symbols = [p.get("symbol") for p in positions if p.get("symbol")]

        # Calculate all pairwise correlations
        correlations = []
        highly_correlated = []

        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                pair = await self.calculate_correlation(symbols[i], symbols[j])
                if pair:
                    correlations.append(pair.correlation)
                    if pair.correlation >= self.high_correlation_threshold:
                        highly_correlated.append(pair)

        if not correlations:
            return PortfolioCorrelationResult(
                average_correlation=0,
                max_correlation=0,
                highly_correlated_pairs=[],
                diversification_score=50,
                concentration_risk="unknown",
                recommendations=["Unable to calculate correlations"],
            )

        avg_corr = sum(correlations) / len(correlations)
        max_corr = max(correlations)

        # Calculate diversification score
        # Lower average correlation = better diversification
        div_score = max(0, min(100, 100 - (avg_corr * 100)))

        # Determine concentration risk
        if len(highly_correlated) >= 3 or avg_corr > 0.6:
            risk = "high"
        elif len(highly_correlated) >= 1 or avg_corr > 0.4:
            risk = "medium"
        else:
            risk = "low"

        # Generate recommendations
        recommendations = []
        if len(highly_correlated) > 0:
            for pair in highly_correlated[:3]:
                recommendations.append(
                    f"High correlation ({pair.correlation:.2f}) between {pair.symbol_a} and {pair.symbol_b}"
                )

        if avg_corr > 0.5:
            recommendations.append("Consider adding uncorrelated assets for diversification")

        if div_score < 50:
            recommendations.append("Portfolio is highly concentrated - reduce correlated positions")

        return PortfolioCorrelationResult(
            average_correlation=avg_corr,
            max_correlation=max_corr,
            highly_correlated_pairs=highly_correlated,
            diversification_score=div_score,
            concentration_risk=risk,
            recommendations=recommendations,
        )

    # ==================== ENTRY CHECKS ====================

    async def can_add_position(
        self,
        symbol: str,
        current_positions: List[Dict[str, Any]],
    ) -> Tuple[bool, str, List[str]]:
        """
        Check if adding a position would create too much correlation risk.

        Args:
            symbol: Symbol to add
            current_positions: Current portfolio positions

        Returns:
            (allowed, reason, correlated_symbols)
        """
        if not current_positions:
            return True, "No existing positions", []

        existing_symbols = [p.get("symbol") for p in current_positions if p.get("symbol")]
        correlated_with = []

        for existing_symbol in existing_symbols:
            pair = await self.calculate_correlation(symbol, existing_symbol)

            if pair and pair.correlation >= self.high_correlation_threshold:
                correlated_with.append(existing_symbol)

        if len(correlated_with) >= self.max_correlated_positions:
            return (
                False,
                f"Would exceed max correlated positions ({len(correlated_with)} highly correlated)",
                correlated_with,
            )

        if correlated_with:
            return (
                True,
                f"Allowed but correlated with {len(correlated_with)} position(s)",
                correlated_with,
            )

        return True, "No correlation concerns", []

    async def get_least_correlated(
        self,
        candidates: List[str],
        current_positions: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Get least correlated candidates from a list.

        Useful for selecting which opportunity to take when multiple are available.

        Args:
            candidates: List of candidate symbols
            current_positions: Current portfolio
            top_n: Number of results

        Returns:
            List of (symbol, avg_correlation) tuples, sorted by lowest correlation
        """
        if not current_positions:
            return [(c, 0) for c in candidates[:top_n]]

        existing_symbols = [p.get("symbol") for p in current_positions if p.get("symbol")]
        candidate_correlations = []

        for candidate in candidates:
            total_corr = 0
            count = 0

            for existing in existing_symbols:
                pair = await self.calculate_correlation(candidate, existing)
                if pair:
                    total_corr += abs(pair.correlation)
                    count += 1

            avg_corr = total_corr / count if count > 0 else 0
            candidate_correlations.append((candidate, avg_corr))

        # Sort by lowest correlation
        candidate_correlations.sort(key=lambda x: x[1])

        return candidate_correlations[:top_n]

    # ==================== CACHING ====================

    def _make_cache_key(self, symbol_a: str, symbol_b: str) -> str:
        """Make consistent cache key regardless of order"""
        symbols = sorted([symbol_a.upper(), symbol_b.upper()])
        return f"{symbols[0]}_{symbols[1]}"

    def _get_cached_correlation(self, cache_key: str) -> Optional[CorrelationPair]:
        """Get cached correlation if still valid"""
        if cache_key not in self._correlation_cache:
            return None

        pair = self._correlation_cache[cache_key]
        age = (datetime.now() - pair.calculated_at).total_seconds() / 3600

        if age > self._cache_ttl_hours:
            del self._correlation_cache[cache_key]
            return None

        return pair

    def _cache_correlation(self, cache_key: str, pair: CorrelationPair):
        """Cache a correlation result"""
        self._correlation_cache[cache_key] = pair

        # Limit cache size
        if len(self._correlation_cache) > 500:
            # Remove oldest entries
            sorted_items = sorted(
                self._correlation_cache.items(),
                key=lambda x: x[1].calculated_at
            )
            for key, _ in sorted_items[:250]:
                del self._correlation_cache[key]

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "enabled": self.alpaca is not None,
            "cache_size": len(self._correlation_cache),
            "cache_ttl_hours": self._cache_ttl_hours,
            "config": {
                "high_correlation_threshold": self.high_correlation_threshold,
                "negative_correlation_threshold": self.negative_correlation_threshold,
                "lookback_days": self.lookback_days,
                "max_correlated_positions": self.max_correlated_positions,
            },
        }


# Singleton instance
_correlation_service: Optional[CorrelationService] = None


def get_correlation_service() -> CorrelationService:
    """Get the global correlation service"""
    global _correlation_service
    if _correlation_service is None:
        _correlation_service = CorrelationService()
    return _correlation_service
