"""
Smart Scanner - Intelligent Hierarchical Trading Scanner
=========================================================

This module orchestrates the hierarchical trading strategy, combining:
- Multi-timeframe analysis
- Pattern recognition (including Elliott Wave)
- Adaptive indicators
- Cascading horizon logic (Swing -> Intraday -> Scalp)

The scanner thinks like a professional day trader:
"What's the BEST opportunity available RIGHT NOW?"

Daily Goal: Make money every trading day by adapting to conditions.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .hierarchical_strategy import (
    HierarchicalStrategy,
    TradingHorizon,
    TradingOpportunity,
    OpportunityQuality,
    get_hierarchical_strategy,
)
from .pattern_recognition import PatternRecognitionService
from .multi_timeframe import MultiTimeframeService, Timeframe
from .indicators import IndicatorService, AdaptiveIndicatorEngine, TradingMode
from .alpaca_service import AlpacaService, get_alpaca_service

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a smart scan cycle"""
    horizon_scanned: TradingHorizon
    symbols_scanned: int
    opportunities_found: int
    best_opportunity: Optional[TradingOpportunity]
    scan_duration_ms: int
    next_horizon: TradingHorizon
    daily_progress: Dict[str, Any]
    scan_summary: str


class SmartScanner:
    """
    Intelligent scanner that cascades through trading horizons.

    Philosophy:
    1. Start with SWING (biggest opportunities, multi-day holds)
    2. If no swing setups found, cascade to INTRADAY
    3. If no intraday, look for SCALP opportunities
    4. Goal: Find profitable opportunities EVERY trading day

    Uses all available analysis:
    - Technical indicators adapted for each horizon
    - Chart patterns (Bull Flags, Head & Shoulders, etc.)
    - Elliott Wave Theory for trend positioning
    - Multi-timeframe confluence for confirmation
    """

    def __init__(
        self,
        alpaca_service: Optional[AlpacaService] = None,
    ):
        self.alpaca = alpaca_service or get_alpaca_service()
        self.strategy = get_hierarchical_strategy()
        self.pattern_service = PatternRecognitionService()
        self.multi_tf_service = MultiTimeframeService()
        self.indicator_service = IndicatorService()
        self.adaptive_engine = AdaptiveIndicatorEngine()

        # Scan state
        self.last_scan_results: Dict[TradingHorizon, ScanResult] = {}
        self.all_opportunities: List[TradingOpportunity] = []

        # Performance tracking
        self.scans_today = 0
        self.opportunities_found_today = 0
        self.last_reset_date = datetime.now().date()

    def _reset_daily_stats_if_needed(self):
        """Reset daily statistics at market open"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.scans_today = 0
            self.opportunities_found_today = 0
            self.last_reset_date = today
            # Also reset the hierarchical strategy's daily goal
            self.strategy.daily_goal.date = today.strftime("%Y-%m-%d")
            self.strategy.daily_goal.achieved_profit_pct = 0.0
            self.strategy.daily_goal.trades_taken = 0
            self.strategy.daily_goal.wins = 0
            self.strategy.daily_goal.losses = 0
            self.strategy.daily_goal.horizons_used = []

    async def scan(
        self,
        symbols: List[str],
        force_horizon: Optional[TradingHorizon] = None,
    ) -> ScanResult:
        """
        Perform an intelligent scan of symbols.

        Args:
            symbols: List of symbols to scan
            force_horizon: Force a specific horizon (skips cascading logic)

        Returns:
            ScanResult with best opportunity found
        """
        self._reset_daily_stats_if_needed()
        start_time = datetime.now()

        # Determine which horizon to scan
        if force_horizon:
            current_horizon = force_horizon
        else:
            current_horizon = self.strategy.get_current_horizon()

        logger.info(f"[SmartScanner] Starting {current_horizon.value} scan of {len(symbols)} symbols")

        opportunities = []
        scanned = 0

        # Scan each symbol
        for symbol in symbols:
            try:
                opportunity = await self._analyze_symbol_for_horizon(symbol, current_horizon)
                if opportunity:
                    opportunities.append(opportunity)
                    if opportunity.quality in [OpportunityQuality.EXCELLENT, OpportunityQuality.GOOD]:
                        logger.info(
                            f"[SmartScanner] Found {opportunity.quality.value} opportunity: "
                            f"{symbol} ({opportunity.horizon.value}) - Score: {opportunity.overall_score:.1f}"
                        )
                scanned += 1
            except Exception as e:
                logger.warning(f"[SmartScanner] Error analyzing {symbol}: {e}")

        # Store all opportunities for this horizon
        self.all_opportunities.extend(opportunities)

        # Get the best opportunity
        best = self.strategy.get_best_opportunity(opportunities)

        # Determine next action
        if not best or best.quality == OpportunityQuality.POOR:
            # No good opportunities found - mark horizon as exhausted
            self.strategy.mark_horizon_exhausted(current_horizon)
            next_horizon = self.strategy.get_current_horizon()
            scan_summary = f"No {current_horizon.value} opportunities. Cascading to {next_horizon.value}."
        else:
            next_horizon = current_horizon
            scan_summary = (
                f"Found {len(opportunities)} {current_horizon.value} opportunities. "
                f"Best: {best.symbol} ({best.quality.value}, {best.overall_score:.1f})"
            )

        # Calculate scan duration
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Update stats
        self.scans_today += 1
        self.opportunities_found_today += len([o for o in opportunities if o.quality != OpportunityQuality.POOR])

        result = ScanResult(
            horizon_scanned=current_horizon,
            symbols_scanned=scanned,
            opportunities_found=len(opportunities),
            best_opportunity=best,
            scan_duration_ms=duration_ms,
            next_horizon=next_horizon,
            daily_progress=self.strategy.get_strategy_summary()["daily_goal"],
            scan_summary=scan_summary,
        )

        self.last_scan_results[current_horizon] = result

        logger.info(f"[SmartScanner] Scan complete: {scan_summary}")
        return result

    async def _analyze_symbol_for_horizon(
        self,
        symbol: str,
        horizon: TradingHorizon,
    ) -> Optional[TradingOpportunity]:
        """
        Analyze a single symbol for the given trading horizon.

        Combines:
        1. Multi-timeframe data fetching
        2. Adaptive indicator calculation
        3. Pattern recognition
        4. Elliott Wave analysis
        5. Multi-TF confluence scoring
        """
        try:
            # Get timeframe configuration for this horizon
            tf_config = self.strategy.timeframe_configs[horizon]

            # Map horizon to primary timeframe for data fetching
            primary_tf_map = {
                TradingHorizon.SWING: "1day",
                TradingHorizon.INTRADAY: "1hour",
                TradingHorizon.SCALP: "5min",
            }
            primary_tf = primary_tf_map[horizon]

            # Fetch bars for primary timeframe
            limit = {
                TradingHorizon.SWING: 200,
                TradingHorizon.INTRADAY: 100,
                TradingHorizon.SCALP: 100,
            }[horizon]

            bars = await self.alpaca.get_bars(symbol, timeframe=primary_tf, limit=limit)

            if len(bars) < 30:
                logger.debug(f"[SmartScanner] Insufficient data for {symbol}: {len(bars)} bars")
                return None

            # Extract OHLCV
            opens = [b["open"] for b in bars]
            highs = [b["high"] for b in bars]
            lows = [b["low"] for b in bars]
            closes = [b["close"] for b in bars]
            volumes = [b["volume"] for b in bars]
            current_price = closes[-1]

            # Map horizon to TradingMode for adaptive engine
            mode_map = {
                TradingHorizon.SWING: TradingMode.SWING,
                TradingHorizon.INTRADAY: TradingMode.INTRADAY,
                TradingHorizon.SCALP: TradingMode.SCALP,
            }
            trading_mode = mode_map[horizon]

            # Calculate adaptive indicators
            indicators = self.adaptive_engine.calculate_adaptive_indicators(
                mode=trading_mode,
                prices=closes,
                highs=highs,
                lows=lows,
                volumes=volumes,
            )

            # Add current price to indicators
            indicators["current_price"] = current_price

            # Run pattern recognition
            pattern_analysis = self.pattern_service.analyze(opens, highs, lows, closes)
            patterns = []
            if pattern_analysis:
                # Convert pattern results to dicts
                for p in pattern_analysis.get("patterns", []):
                    if hasattr(p, "pattern_type"):
                        patterns.append({
                            "name": p.pattern_type.value if hasattr(p.pattern_type, "value") else str(p.pattern_type),
                            "confidence": p.confidence / 100 if p.confidence > 1 else p.confidence,
                            "direction": p.direction,
                        })

            # Get Elliott Wave analysis
            elliott_wave = pattern_analysis.get("elliott_wave") if pattern_analysis else None

            # Build multi-timeframe analysis
            # For now, use the primary timeframe analysis as a starting point
            # In production, you'd fetch multiple timeframes
            multi_tf = {
                tf_config["trend"]: {
                    "trend": "bullish" if indicators.get("macd_histogram", 0) > 0 and
                             indicators.get("rsi_14", 50) > 45 else
                             "bearish" if indicators.get("macd_histogram", 0) < 0 and
                             indicators.get("rsi_14", 50) < 55 else "neutral",
                    "strength": abs(indicators.get("macd_histogram", 0)) * 10,
                },
                tf_config["momentum"]: {
                    "trend": "bullish" if indicators.get("rsi_14", 50) < 40 else
                             "bearish" if indicators.get("rsi_14", 50) > 60 else "neutral",
                    "strength": abs(50 - indicators.get("rsi_14", 50)),
                },
                tf_config["entry"]: {
                    "trend": "bullish" if closes[-1] > closes[-2] else
                             "bearish" if closes[-1] < closes[-2] else "neutral",
                    "strength": abs(closes[-1] - closes[-2]) / closes[-2] * 100,
                },
            }

            # Evaluate using hierarchical strategy
            opportunity = self.strategy.evaluate_opportunity(
                symbol=symbol,
                horizon=horizon,
                indicators=indicators,
                patterns=patterns,
                elliott_wave=elliott_wave,
                multi_tf_analysis=multi_tf,
                current_price=current_price,
            )

            return opportunity

        except Exception as e:
            logger.error(f"[SmartScanner] Error analyzing {symbol} for {horizon.value}: {e}")
            return None

    async def full_cascade_scan(
        self,
        symbols: List[str],
        max_cascades: int = 3,
    ) -> Tuple[Optional[TradingOpportunity], List[ScanResult]]:
        """
        Perform a full cascading scan through all horizons until a good opportunity is found.

        This is the main entry point for the "make money every day" logic:
        1. Scan for SWING trades
        2. If nothing good, scan for INTRADAY
        3. If nothing good, scan for SCALP

        Returns:
            Tuple of (best_opportunity, all_scan_results)
        """
        results = []
        best_overall = None

        for cascade_num in range(max_cascades):
            # Determine current horizon (cascading logic)
            current_horizon = self.strategy.get_current_horizon()

            logger.info(f"[SmartScanner] Cascade {cascade_num + 1}/{max_cascades}: Scanning {current_horizon.value}")

            # Perform scan
            result = await self.scan(symbols)
            results.append(result)

            # Check if we found a good opportunity
            if result.best_opportunity:
                quality = result.best_opportunity.quality
                if quality in [OpportunityQuality.EXCELLENT, OpportunityQuality.GOOD]:
                    best_overall = result.best_opportunity
                    logger.info(
                        f"[SmartScanner] Found tradeable opportunity on cascade {cascade_num + 1}: "
                        f"{best_overall.symbol} ({quality.value})"
                    )
                    break

            # Check if all horizons are exhausted
            if all(self.strategy.horizon_exhausted.values()):
                logger.info("[SmartScanner] All horizons exhausted - no opportunities at this time")
                break

            # Small delay between cascades
            await asyncio.sleep(0.5)

        # If we didn't find anything good, return the best FAIR opportunity if any
        if not best_overall:
            fair_opportunities = [
                r.best_opportunity for r in results
                if r.best_opportunity and r.best_opportunity.quality == OpportunityQuality.FAIR
            ]
            if fair_opportunities:
                best_overall = max(fair_opportunities, key=lambda o: o.overall_score)
                logger.info(
                    f"[SmartScanner] Best available is FAIR: {best_overall.symbol} "
                    f"(score: {best_overall.overall_score:.1f})"
                )

        return best_overall, results

    def get_scan_summary(self) -> Dict[str, Any]:
        """Get summary of scanning activity for UI display"""
        return {
            "scans_today": self.scans_today,
            "opportunities_found_today": self.opportunities_found_today,
            "current_horizon": self.strategy.get_current_horizon().value,
            "horizon_status": {
                h.value: {
                    "exhausted": self.strategy.horizon_exhausted[h],
                    "last_scan": self.last_scan_results.get(h, {}).scan_summary
                    if self.last_scan_results.get(h) else "Not scanned yet"
                }
                for h in TradingHorizon
            },
            "daily_goal": self.strategy.get_strategy_summary()["daily_goal"],
            "active_opportunities": len([
                o for o in self.all_opportunities
                if o.valid_until and o.valid_until > datetime.now()
            ]),
        }

    def record_trade_result(self, pnl_pct: float, horizon: TradingHorizon):
        """Record a trade result for daily goal tracking"""
        self.strategy.update_daily_goal(pnl_pct, horizon)


# Singleton instance
_smart_scanner: Optional[SmartScanner] = None


def get_smart_scanner() -> SmartScanner:
    """Get or create the singleton smart scanner instance"""
    global _smart_scanner
    if _smart_scanner is None:
        _smart_scanner = SmartScanner()
    return _smart_scanner
