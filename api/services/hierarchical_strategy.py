"""
Hierarchical Trading Strategy Engine
=====================================

Implements an intelligent, cascading trading approach:
1. First look for SWING trades (multi-day, bigger moves)
2. If nothing: look for INTRADAY trades (same-day, medium moves)
3. If nothing: look for SCALP opportunities (quick 0.5-2% gains)

The goal: Make money EVERY trading day by adapting to market conditions.

Uses all available indicators including:
- Elliott Wave Theory
- Pattern Recognition (Bull Flags, Head & Shoulders, etc.)
- Multi-timeframe Confluence
- Adaptive Indicator Parameters
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class TradingHorizon(str, Enum):
    """Trading time horizon - from longest to shortest"""
    LONG = "LONG"             # 10+ days, target 15-30%
    SWING = "SWING"           # 2-10 days, target 5-15%
    INTRADAY = "INTRADAY"     # 1-8 hours, target 1-3%
    SCALP = "SCALP"           # 5-60 minutes, target 0.3-1%


class OpportunityQuality(str, Enum):
    """Quality rating of trading opportunity"""
    EXCELLENT = "EXCELLENT"   # 85+ score, multiple confirmations
    GOOD = "GOOD"             # 70-84 score, solid setup
    FAIR = "FAIR"             # 55-69 score, acceptable risk/reward
    POOR = "POOR"             # Below 55, not recommended


@dataclass
class TradingOpportunity:
    """A potential trading opportunity with full context"""
    symbol: str
    horizon: TradingHorizon
    quality: OpportunityQuality

    # Scores
    overall_score: float           # 0-100
    trend_score: float             # How strong is the trend?
    momentum_score: float          # Momentum indicators alignment
    pattern_score: float           # Chart pattern strength
    volume_score: float            # Volume confirmation
    multi_tf_score: float          # Multi-timeframe alignment

    # Signal details
    direction: str                 # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    target_1: float                # Conservative target
    target_2: float                # Aggressive target
    risk_reward_ratio: float

    # Context
    patterns_detected: List[str] = field(default_factory=list)
    elliott_wave: Optional[str] = None      # e.g., "Wave 3 impulse"
    key_levels: Dict[str, float] = field(default_factory=dict)  # support/resistance
    confluence_factors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Timeframes analyzed
    primary_timeframe: str = "1d"
    confirmation_timeframe: str = "1h"
    entry_timeframe: str = "5m"

    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None


@dataclass
class DailyTradingGoal:
    """Daily profit target tracking"""
    date: str
    target_profit_pct: float       # e.g., 0.5% daily goal
    achieved_profit_pct: float
    trades_taken: int
    wins: int
    losses: int
    best_trade_pct: float
    worst_trade_pct: float
    horizons_used: List[str] = field(default_factory=list)
    goal_achieved: bool = False


class HierarchicalStrategy:
    """
    Intelligent cascading strategy that adapts to find the best opportunities.

    Philosophy:
    - Always start looking for the BIGGEST opportunities (Swing)
    - If market isn't providing swing setups, scale down to Intraday
    - If no intraday setups, look for quick Scalp profits
    - Never force trades - but always be looking

    The bot thinks like a professional trader:
    "What's the best opportunity available RIGHT NOW?"
    """

    def __init__(self):
        # Score thresholds for each horizon
        # Scan intervals based on trade type (user requested):
        # - Scalp: 60 seconds (fast, short-term trades)
        # - Intraday: 2 minutes (120 seconds)
        # - Swing: 10 minutes (600 seconds)
        # - Long: 30 minutes (1800 seconds)
        self.thresholds = {
            TradingHorizon.LONG: {
                "min_score": 75,          # Highest bar for long-term holds
                "excellent_score": 90,
                "risk_reward_min": 3.0,   # Need 3:1 minimum for long
                "max_positions": 2,
                "scan_interval_seconds": 1800,  # 30 minutes
            },
            TradingHorizon.SWING: {
                "min_score": 70,          # Higher bar for multi-day holds
                "excellent_score": 85,
                "risk_reward_min": 2.0,   # Need 2:1 minimum for swing
                "max_positions": 3,
                "scan_interval_seconds": 600,  # 10 minutes
            },
            TradingHorizon.INTRADAY: {
                "min_score": 65,
                "excellent_score": 80,
                "risk_reward_min": 1.5,
                "max_positions": 5,
                "scan_interval_seconds": 120,  # 2 minutes
            },
            TradingHorizon.SCALP: {
                "min_score": 60,          # Lower bar for quick trades
                "excellent_score": 75,
                "risk_reward_min": 1.2,   # 1.2:1 okay for scalps
                "max_positions": 3,
                "scan_interval_seconds": 60,   # 1 minute (60 seconds)
            },
        }

        # Multi-timeframe configurations
        self.timeframe_configs = {
            TradingHorizon.LONG: {
                "trend": "1w",       # Weekly for trend
                "momentum": "1d",    # Daily for momentum
                "entry": "4h",       # 4-hour for entry
            },
            TradingHorizon.SWING: {
                "trend": "1d",       # Daily for trend
                "momentum": "4h",    # 4-hour for momentum
                "entry": "1h",       # Hourly for entry
            },
            TradingHorizon.INTRADAY: {
                "trend": "1h",       # Hourly for trend
                "momentum": "15m",   # 15-min for momentum
                "entry": "5m",       # 5-min for entry
            },
            TradingHorizon.SCALP: {
                "trend": "15m",      # 15-min for trend
                "momentum": "5m",    # 5-min for momentum
                "entry": "1m",       # 1-min for entry
            },
        }

        # Indicator parameters by horizon (from adaptive engine)
        self.indicator_params = {
            TradingHorizon.LONG: {
                "rsi_period": 28,
                "macd_fast": 26,
                "macd_slow": 52,
                "macd_signal": 9,
                "bb_period": 50,
                "bb_std": 3.0,
                "atr_period": 28,
                "atr_multiplier_stop": 3.0,
                "atr_multiplier_target": 6.0,
            },
            TradingHorizon.SWING: {
                "rsi_period": 21,
                "macd_fast": 19,
                "macd_slow": 39,
                "macd_signal": 9,
                "bb_period": 30,
                "bb_std": 2.5,
                "atr_period": 21,
                "atr_multiplier_stop": 2.5,
                "atr_multiplier_target": 4.0,
            },
            TradingHorizon.INTRADAY: {
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "bb_period": 20,
                "bb_std": 2.0,
                "atr_period": 14,
                "atr_multiplier_stop": 1.5,
                "atr_multiplier_target": 2.5,
            },
            TradingHorizon.SCALP: {
                "rsi_period": 7,
                "macd_fast": 6,
                "macd_slow": 13,
                "macd_signal": 5,
                "bb_period": 10,
                "bb_std": 2.0,
                "atr_period": 7,
                "atr_multiplier_stop": 0.75,
                "atr_multiplier_target": 1.5,
            },
        }

        # Daily tracking
        self.daily_goal = DailyTradingGoal(
            date=datetime.now().strftime("%Y-%m-%d"),
            target_profit_pct=0.5,  # 0.5% daily goal
            achieved_profit_pct=0.0,
            trades_taken=0,
            wins=0,
            losses=0,
            best_trade_pct=0.0,
            worst_trade_pct=0.0,
        )

        # State tracking
        self.current_horizon: TradingHorizon = TradingHorizon.SWING
        self.last_scan_time: Dict[TradingHorizon, datetime] = {}
        self.active_opportunities: Dict[str, TradingOpportunity] = {}
        self.horizon_exhausted: Dict[TradingHorizon, bool] = {
            TradingHorizon.LONG: False,
            TradingHorizon.SWING: False,
            TradingHorizon.INTRADAY: False,
            TradingHorizon.SCALP: False,
        }

        # Performance tracking
        self.trades_by_horizon: Dict[TradingHorizon, List[Dict]] = {
            TradingHorizon.LONG: [],
            TradingHorizon.SWING: [],
            TradingHorizon.INTRADAY: [],
            TradingHorizon.SCALP: [],
        }

    def get_current_horizon(self) -> TradingHorizon:
        """
        Determine which trading horizon to focus on right now.

        Logic:
        1. If we haven't found any long-term setups, try long first
        2. If long is "exhausted", try swing
        3. If swing is "exhausted" (scanned, nothing good), try intraday
        4. If intraday exhausted, try scalp
        5. Reset exhausted flags based on scan intervals:
           - Scalp: 60 seconds
           - Intraday: 2 minutes (120 seconds)
           - Swing: 10 minutes (600 seconds)
           - Long: 30 minutes (1800 seconds)
        """
        now = datetime.now()

        # Reset exhausted flags based on time (using scan_interval_seconds)
        for horizon, last_time in self.last_scan_time.items():
            interval_seconds = self.thresholds[horizon]["scan_interval_seconds"]
            if (now - last_time) > timedelta(seconds=interval_seconds):
                self.horizon_exhausted[horizon] = False

        # Cascade through horizons (Long -> Swing -> Intraday -> Scalp)
        if not self.horizon_exhausted[TradingHorizon.LONG]:
            return TradingHorizon.LONG
        elif not self.horizon_exhausted[TradingHorizon.SWING]:
            return TradingHorizon.SWING
        elif not self.horizon_exhausted[TradingHorizon.INTRADAY]:
            return TradingHorizon.INTRADAY
        elif not self.horizon_exhausted[TradingHorizon.SCALP]:
            return TradingHorizon.SCALP
        else:
            # All exhausted - reset and start fresh with long
            self.horizon_exhausted = {h: False for h in TradingHorizon}
            return TradingHorizon.LONG

    def mark_horizon_exhausted(self, horizon: TradingHorizon):
        """Mark a horizon as scanned with no good opportunities"""
        self.horizon_exhausted[horizon] = True
        self.last_scan_time[horizon] = datetime.now()
        logger.info(f"Horizon {horizon.value} exhausted - cascading to next")

    def get_scan_interval_seconds(self, horizon: TradingHorizon) -> int:
        """Get the scan interval in seconds for a given horizon.

        User-requested intervals:
        - Scalp: 60 seconds
        - Intraday: 120 seconds (2 min)
        - Swing: 600 seconds (10 min)
        - Long: 1800 seconds (30 min)
        """
        return self.thresholds[horizon]["scan_interval_seconds"]

    def get_next_scan_time(self, horizon: TradingHorizon) -> Optional[datetime]:
        """Get the next scheduled scan time for a horizon, or None if ready to scan now."""
        if horizon not in self.last_scan_time:
            return None  # Never scanned, scan now

        interval_seconds = self.get_scan_interval_seconds(horizon)
        next_scan = self.last_scan_time[horizon] + timedelta(seconds=interval_seconds)

        if datetime.now() >= next_scan:
            return None  # Ready to scan now
        return next_scan

    def seconds_until_next_scan(self, horizon: TradingHorizon) -> int:
        """Get seconds until next scan for a horizon (0 if ready now)."""
        next_scan = self.get_next_scan_time(horizon)
        if next_scan is None:
            return 0

        delta = (next_scan - datetime.now()).total_seconds()
        return max(0, int(delta))

    def evaluate_opportunity(
        self,
        symbol: str,
        horizon: TradingHorizon,
        indicators: Dict[str, Any],
        patterns: List[Dict],
        elliott_wave: Optional[Dict],
        multi_tf_analysis: Dict[str, Any],
        current_price: float,
    ) -> Optional[TradingOpportunity]:
        """
        Evaluate a symbol for the given trading horizon.

        Combines all available analysis:
        - Technical indicators (adapted for horizon)
        - Chart patterns (flags, H&S, etc.)
        - Elliott Wave position
        - Multi-timeframe confluence
        """
        # ===== INDICATOR VALIDATION =====
        # Define required and important indicators
        critical_indicators = ["current_price"]  # Absolutely required
        important_indicators = ["atr", "rsi_14", "macd_histogram"]  # Needed for reliable scoring

        # Check if indicators dict is None or empty
        if not indicators:
            logger.warning(
                f"[INCOMPLETE_DATA] {symbol}: indicators dict is None or empty - skipping opportunity"
            )
            return None

        # Check critical indicators
        missing_critical = []
        for ind in critical_indicators:
            if ind not in indicators or indicators[ind] is None:
                missing_critical.append(ind)

        if missing_critical:
            logger.warning(
                f"[INCOMPLETE_DATA] {symbol}: Missing critical indicators {missing_critical} - skipping opportunity"
            )
            return None

        # Validate current_price is a valid number
        if not isinstance(current_price, (int, float)) or current_price <= 0:
            logger.warning(
                f"[INCOMPLETE_DATA] {symbol}: Invalid current_price ({current_price}) - skipping opportunity"
            )
            return None

        # Check important indicators and log warnings (but don't skip)
        missing_important = []
        for ind in important_indicators:
            if ind not in indicators or indicators[ind] is None:
                missing_important.append(ind)

        if missing_important:
            logger.warning(
                f"[INCOMPLETE_DATA] {symbol}: Missing important indicators {missing_important} - using fallbacks"
            )

        # Apply sensible fallbacks for missing non-critical indicators
        # ATR fallback: 2% of current price (reasonable volatility estimate)
        if indicators.get("atr") is None:
            indicators["atr"] = current_price * 0.02
            logger.debug(f"{symbol}: Using ATR fallback (2% of price)")

        # RSI fallback: neutral value
        if indicators.get("rsi_14") is None:
            indicators["rsi_14"] = 50
            logger.debug(f"{symbol}: Using RSI fallback (neutral 50)")

        # MACD fallbacks: neutral values
        if indicators.get("macd_histogram") is None:
            indicators["macd_histogram"] = 0
        if indicators.get("macd_histogram_prev") is None:
            indicators["macd_histogram_prev"] = 0
        if indicators.get("macd_line") is None:
            indicators["macd_line"] = 0
        if indicators.get("macd_signal") is None:
            indicators["macd_signal"] = 0

        # SMA fallbacks: use current price
        if indicators.get("sma_20") is None:
            indicators["sma_20"] = current_price
        if indicators.get("sma_50") is None:
            indicators["sma_50"] = current_price
        if indicators.get("sma_200") is None:
            indicators["sma_200"] = current_price

        # Volume fallback: neutral ratio
        if indicators.get("volume_ratio") is None:
            indicators["volume_ratio"] = 1.0

        # Stochastic fallbacks: neutral values
        if indicators.get("stoch_k") is None:
            indicators["stoch_k"] = 50
        if indicators.get("stoch_d") is None:
            indicators["stoch_d"] = 50

        # ADX fallback: low trend strength
        if indicators.get("adx") is None:
            indicators["adx"] = 20

        # ROC fallback: neutral
        if indicators.get("roc") is None:
            indicators["roc"] = 0

        # VWAP fallback: current price
        if indicators.get("vwap") is None:
            indicators["vwap"] = current_price

        # Ensure current_price is in indicators for scoring methods
        indicators["current_price"] = current_price

        params = self.indicator_params[horizon]
        thresholds = self.thresholds[horizon]

        # ===== SCORE CALCULATION =====

        # 1. Trend Score (25% weight)
        trend_score = self._calculate_trend_score(indicators, horizon)

        # 2. Momentum Score (25% weight)
        momentum_score = self._calculate_momentum_score(indicators, params)

        # 3. Pattern Score (20% weight) - includes Elliott Wave
        pattern_score = self._calculate_pattern_score(patterns, elliott_wave, horizon)

        # 4. Volume Score (15% weight)
        volume_score = self._calculate_volume_score(indicators)

        # 5. Multi-Timeframe Score (15% weight)
        multi_tf_score = self._calculate_multi_tf_score(multi_tf_analysis, horizon)

        # Weighted overall score
        overall_score = (
            trend_score * 0.25 +
            momentum_score * 0.25 +
            pattern_score * 0.20 +
            volume_score * 0.15 +
            multi_tf_score * 0.15
        )

        # Quality classification
        if overall_score >= thresholds["excellent_score"]:
            quality = OpportunityQuality.EXCELLENT
        elif overall_score >= thresholds["min_score"]:
            quality = OpportunityQuality.GOOD
        elif overall_score >= thresholds["min_score"] - 10:
            quality = OpportunityQuality.FAIR
        else:
            quality = OpportunityQuality.POOR

        # Skip if below minimum
        if overall_score < thresholds["min_score"] - 15:
            return None

        # ===== DETERMINE DIRECTION =====
        direction = self._determine_direction(indicators, patterns, multi_tf_analysis)

        # ===== CALCULATE ENTRY/EXIT LEVELS =====
        atr = indicators["atr"]  # Already validated with fallback in validation section

        entry_price = current_price

        if direction == "LONG":
            stop_loss = current_price - (atr * params["atr_multiplier_stop"])
            target_1 = current_price + (atr * params["atr_multiplier_target"] * 0.6)
            target_2 = current_price + (atr * params["atr_multiplier_target"])
        else:
            stop_loss = current_price + (atr * params["atr_multiplier_stop"])
            target_1 = current_price - (atr * params["atr_multiplier_target"] * 0.6)
            target_2 = current_price - (atr * params["atr_multiplier_target"])

        # Risk/Reward calculation
        risk = abs(current_price - stop_loss)
        reward = abs(target_1 - current_price)
        risk_reward = reward / risk if risk > 0 else 0

        # Check minimum R:R
        if risk_reward < thresholds["risk_reward_min"]:
            # Adjust or reject
            if quality == OpportunityQuality.EXCELLENT:
                # Keep excellent opportunities even with lower R:R
                pass
            elif risk_reward < thresholds["risk_reward_min"] * 0.8:
                return None

        # ===== BUILD CONFLUENCE FACTORS =====
        confluence = []
        warnings = []

        if trend_score >= 70:
            confluence.append("Strong trend alignment")
        if momentum_score >= 70:
            confluence.append("Momentum confirming")
        if pattern_score >= 60:
            confluence.append(f"Pattern detected: {patterns[0]['name'] if patterns else 'confluence'}")
        if volume_score >= 65:
            confluence.append("Volume supporting move")
        if multi_tf_score >= 70:
            confluence.append("Multi-timeframe alignment")

        # Add Elliott Wave context
        if elliott_wave:
            wave_info = elliott_wave.get("current_wave", "")
            if wave_info:
                confluence.append(f"Elliott Wave: {wave_info}")

        # Warnings
        if volume_score < 40:
            warnings.append("Low volume - be cautious")
        if multi_tf_score < 50:
            warnings.append("Conflicting timeframe signals")
        if indicators.get("rsi_14", 50) > 75 and direction == "LONG":
            warnings.append("RSI overbought - consider waiting for pullback")
        if indicators.get("rsi_14", 50) < 25 and direction == "SHORT":
            warnings.append("RSI oversold - consider waiting for bounce")

        # Pattern names
        pattern_names = [p["name"] for p in patterns] if patterns else []

        # Key levels
        key_levels = {
            "support": indicators.get("support", stop_loss),
            "resistance": indicators.get("resistance", target_2),
            "vwap": indicators.get("vwap", current_price),
            "sma_20": indicators.get("sma_20", current_price),
            "sma_50": indicators.get("sma_50", current_price),
        }

        # Validity period based on horizon
        validity_hours = {
            TradingHorizon.SWING: 24,
            TradingHorizon.INTRADAY: 4,
            TradingHorizon.SCALP: 0.5,
        }
        valid_until = datetime.now() + timedelta(hours=validity_hours[horizon])

        return TradingOpportunity(
            symbol=symbol,
            horizon=horizon,
            quality=quality,
            overall_score=overall_score,
            trend_score=trend_score,
            momentum_score=momentum_score,
            pattern_score=pattern_score,
            volume_score=volume_score,
            multi_tf_score=multi_tf_score,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            risk_reward_ratio=risk_reward,
            patterns_detected=pattern_names,
            elliott_wave=elliott_wave.get("summary") if elliott_wave else None,
            key_levels=key_levels,
            confluence_factors=confluence,
            warnings=warnings,
            primary_timeframe=self.timeframe_configs[horizon]["trend"],
            confirmation_timeframe=self.timeframe_configs[horizon]["momentum"],
            entry_timeframe=self.timeframe_configs[horizon]["entry"],
            valid_until=valid_until,
        )

    def _calculate_trend_score(self, indicators: Dict, horizon: TradingHorizon) -> float:
        """Score the trend strength (0-100)"""
        score = 50  # Neutral baseline

        # SMA alignment (Golden Cross = bullish, Death Cross = bearish)
        if indicators.get("golden_cross"):
            score += 20
        elif indicators.get("death_cross"):
            score -= 15  # Bearish still tradeable for shorts

        # Price vs SMAs
        price = indicators.get("current_price", 0)
        sma_20 = indicators.get("sma_20", price)
        sma_50 = indicators.get("sma_50", price)
        sma_200 = indicators.get("sma_200", price)

        if price > sma_20 > sma_50:
            score += 15  # Strong uptrend
        elif price < sma_20 < sma_50:
            score += 10  # Strong downtrend (tradeable for shorts)

        # ADX trend strength
        adx = indicators.get("adx", 20)
        if adx > 25:
            score += 10  # Trending market
        if adx > 40:
            score += 5   # Strong trend

        # MACD trend
        macd_hist = indicators.get("macd_histogram", 0)
        macd_hist_prev = indicators.get("macd_histogram_prev", 0)
        if macd_hist > 0 and macd_hist > macd_hist_prev:
            score += 10  # Increasing bullish momentum
        elif macd_hist < 0 and macd_hist < macd_hist_prev:
            score += 5   # Bearish momentum (for shorts)

        return max(0, min(100, score))

    def _calculate_momentum_score(self, indicators: Dict, params: Dict) -> float:
        """Score momentum indicators (0-100)

        Updated based on backtest analysis (2026-01-28):
        - Momentum (ROC) is the best performer (Sharpe 0.33) - INCREASED weight
        - MACD is the worst performer (Sharpe -0.43) - REDUCED weight
        - RSI with tighter thresholds (25/75) performs better
        """
        score = 50

        # RSI - UPDATED with tighter thresholds (25/75 instead of 30/70)
        rsi = indicators.get("rsi_14", 50)
        if 25 < rsi < 40:
            score += 15  # Oversold bouncing = good long
        elif 50 < rsi < 65:
            score += 10  # Healthy bullish
        elif rsi < 25:
            score += 20  # Very oversold = reversal opportunity
        elif rsi > 75:
            score -= 5   # Very overbought caution

        # Stochastic
        stoch_k = indicators.get("stoch_k", 50)
        stoch_d = indicators.get("stoch_d", 50)
        if stoch_k < 20 and stoch_k > stoch_d:
            score += 15  # Oversold with bullish crossover
        elif stoch_k > 80 and stoch_k < stoch_d:
            score += 10  # Overbought with bearish (short opportunity)

        # MACD crossover - REDUCED weight (poor backtest results)
        macd_line = indicators.get("macd_line", 0)
        macd_signal = indicators.get("macd_signal", 0)
        if macd_line > macd_signal and indicators.get("macd_histogram", 0) > 0:
            score += 5  # Reduced from 15 - MACD had worst backtest performance

        # Rate of change (Momentum) - INCREASED weight (best backtest performer!)
        roc = indicators.get("roc", 0)
        if roc > 5:
            score += 20  # Strong positive momentum - key signal
        elif 2 < roc <= 5:
            score += 15  # Good momentum
        elif 0 < roc <= 2:
            score += 10  # Slight positive momentum
        elif roc < -5:
            score -= 10  # Strong negative momentum - avoid

        # Mean reversion component - check deviation from SMA
        sma_20 = indicators.get("sma_20", 0)
        current_price = indicators.get("current_price", 0)
        if sma_20 > 0 and current_price > 0:
            deviation = ((current_price - sma_20) / sma_20) * 100
            if deviation < -3:
                score += 15  # Price below SMA = mean reversion opportunity
            elif deviation > 5:
                score -= 5   # Price extended above SMA

        return max(0, min(100, score))

    def _calculate_pattern_score(
        self,
        patterns: List[Dict],
        elliott_wave: Optional[Dict],
        horizon: TradingHorizon
    ) -> float:
        """Score chart patterns and Elliott Wave (0-100)"""
        score = 40  # Baseline (no pattern is neutral)

        # High-reliability patterns
        high_reliability = ["bull_flag", "bear_flag", "cup_and_handle", "inverse_head_shoulders"]
        medium_reliability = ["ascending_triangle", "descending_triangle", "double_bottom", "double_top"]

        for pattern in patterns:
            name = pattern.get("name", "").lower().replace(" ", "_")
            confidence = pattern.get("confidence", 0.5)

            if name in high_reliability:
                score += 30 * confidence
            elif name in medium_reliability:
                score += 20 * confidence
            else:
                score += 10 * confidence

        # Elliott Wave bonus
        if elliott_wave:
            wave = elliott_wave.get("current_wave", "")
            wave_confidence = elliott_wave.get("confidence", 0.5)

            # Wave 3 is the strongest - highest potential
            if "wave 3" in wave.lower() or "wave 5" in wave.lower():
                score += 25 * wave_confidence
            elif "wave 1" in wave.lower():
                score += 15 * wave_confidence  # Early trend
            elif "wave 4" in wave.lower():
                score += 10 * wave_confidence  # Pullback opportunity

            # Corrective waves
            if "wave a" in wave.lower() or "wave c" in wave.lower():
                score += 10 * wave_confidence  # Counter-trend plays

        # Cap at 100
        return max(0, min(100, score))

    def _calculate_volume_score(self, indicators: Dict) -> float:
        """Score volume confirmation (0-100)"""
        score = 50

        # Volume vs average
        volume_ratio = indicators.get("volume_ratio", 1.0)

        if volume_ratio > 2.0:
            score += 25  # High volume = conviction
        elif volume_ratio > 1.5:
            score += 15
        elif volume_ratio > 1.0:
            score += 5
        elif volume_ratio < 0.5:
            score -= 15  # Low volume = less reliable

        # OBV trend
        obv_trend = indicators.get("obv_trend", "neutral")
        if obv_trend == "bullish":
            score += 15
        elif obv_trend == "bearish":
            score += 10  # For shorts

        # Price vs VWAP
        price = indicators.get("current_price", 0)
        vwap = indicators.get("vwap", price)
        if price and vwap:
            vwap_pct = (price - vwap) / vwap * 100
            if -1 < vwap_pct < 1:
                score += 10  # Near VWAP = good entry
            elif vwap_pct < -2:
                score += 5   # Below VWAP = value

        return max(0, min(100, score))

    def _calculate_multi_tf_score(self, multi_tf: Dict, horizon: TradingHorizon) -> float:
        """Score multi-timeframe alignment (0-100)"""
        score = 50

        if not multi_tf:
            return score

        # Count aligned timeframes
        aligned_bullish = 0
        aligned_bearish = 0
        total_tf = 0

        for tf, analysis in multi_tf.items():
            total_tf += 1
            trend = analysis.get("trend", "neutral")
            if trend == "bullish":
                aligned_bullish += 1
            elif trend == "bearish":
                aligned_bearish += 1

        if total_tf > 0:
            # All timeframes aligned = maximum score
            if aligned_bullish == total_tf:
                score = 90
            elif aligned_bearish == total_tf:
                score = 85  # Bearish alignment good for shorts
            elif aligned_bullish > total_tf * 0.6:
                score = 75
            elif aligned_bearish > total_tf * 0.6:
                score = 70
            elif aligned_bullish == 0 and aligned_bearish == 0:
                score = 40  # All neutral/conflicting

        # Higher timeframe weight
        higher_tf = multi_tf.get("1d") or multi_tf.get("4h") or multi_tf.get("1h", {})
        if higher_tf.get("trend") == "bullish":
            score += 10
        elif higher_tf.get("trend") == "bearish":
            score += 5

        return max(0, min(100, score))

    def _determine_direction(
        self,
        indicators: Dict,
        patterns: List[Dict],
        multi_tf: Dict
    ) -> str:
        """Determine trade direction (LONG or SHORT)"""
        long_signals = 0
        short_signals = 0

        # Indicator signals
        rsi = indicators.get("rsi_14", 50)
        if rsi < 40:
            long_signals += 2
        elif rsi > 60:
            short_signals += 1

        macd_hist = indicators.get("macd_histogram", 0)
        if macd_hist > 0:
            long_signals += 2
        elif macd_hist < 0:
            short_signals += 1

        if indicators.get("golden_cross"):
            long_signals += 3
        if indicators.get("death_cross"):
            short_signals += 2

        # Pattern signals
        bullish_patterns = ["bull_flag", "inverse_head_shoulders", "double_bottom", "ascending_triangle"]
        bearish_patterns = ["bear_flag", "head_shoulders", "double_top", "descending_triangle"]

        for p in patterns:
            name = p.get("name", "").lower().replace(" ", "_")
            if any(bp in name for bp in bullish_patterns):
                long_signals += 2
            if any(bp in name for bp in bearish_patterns):
                short_signals += 1

        # Multi-TF signals
        bullish_tfs = sum(1 for tf in multi_tf.values() if tf.get("trend") == "bullish")
        bearish_tfs = sum(1 for tf in multi_tf.values() if tf.get("trend") == "bearish")
        long_signals += bullish_tfs
        short_signals += bearish_tfs

        # Default to LONG (bullish bias typical for retail)
        return "LONG" if long_signals >= short_signals else "SHORT"

    def get_best_opportunity(
        self,
        opportunities: List[TradingOpportunity]
    ) -> Optional[TradingOpportunity]:
        """Get the single best opportunity from a list"""
        if not opportunities:
            return None

        # Sort by: quality (EXCELLENT first), then score, then R:R
        def sort_key(opp: TradingOpportunity):
            quality_order = {
                OpportunityQuality.EXCELLENT: 0,
                OpportunityQuality.GOOD: 1,
                OpportunityQuality.FAIR: 2,
                OpportunityQuality.POOR: 3,
            }
            return (quality_order[opp.quality], -opp.overall_score, -opp.risk_reward_ratio)

        sorted_opps = sorted(opportunities, key=sort_key)
        return sorted_opps[0] if sorted_opps else None

    def update_daily_goal(self, trade_pnl_pct: float, horizon: TradingHorizon):
        """Update daily goal tracking after a trade"""
        today = datetime.now().strftime("%Y-%m-%d")

        # Reset if new day
        if self.daily_goal.date != today:
            self.daily_goal = DailyTradingGoal(
                date=today,
                target_profit_pct=0.5,
                achieved_profit_pct=0.0,
                trades_taken=0,
                wins=0,
                losses=0,
                best_trade_pct=0.0,
                worst_trade_pct=0.0,
            )

        # Update stats
        self.daily_goal.achieved_profit_pct += trade_pnl_pct
        self.daily_goal.trades_taken += 1

        if trade_pnl_pct > 0:
            self.daily_goal.wins += 1
            if trade_pnl_pct > self.daily_goal.best_trade_pct:
                self.daily_goal.best_trade_pct = trade_pnl_pct
        else:
            self.daily_goal.losses += 1
            if trade_pnl_pct < self.daily_goal.worst_trade_pct:
                self.daily_goal.worst_trade_pct = trade_pnl_pct

        if horizon.value not in self.daily_goal.horizons_used:
            self.daily_goal.horizons_used.append(horizon.value)

        # Check goal
        self.daily_goal.goal_achieved = (
            self.daily_goal.achieved_profit_pct >= self.daily_goal.target_profit_pct
        )

        if self.daily_goal.goal_achieved:
            logger.info(f"🎯 Daily goal achieved! {self.daily_goal.achieved_profit_pct:.2f}%")

    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get current strategy state for UI display"""
        return {
            "current_horizon": self.current_horizon.value,
            "horizon_exhausted": {h.value: v for h, v in self.horizon_exhausted.items()},
            "active_opportunities": len(self.active_opportunities),
            "daily_goal": {
                "date": self.daily_goal.date,
                "target_pct": self.daily_goal.target_profit_pct,
                "achieved_pct": self.daily_goal.achieved_profit_pct,
                "trades": self.daily_goal.trades_taken,
                "win_rate": (
                    self.daily_goal.wins / self.daily_goal.trades_taken * 100
                    if self.daily_goal.trades_taken > 0 else 0
                ),
                "goal_achieved": self.daily_goal.goal_achieved,
                "horizons_used": self.daily_goal.horizons_used,
            },
            "thresholds": {
                h.value: {
                    "min_score": t["min_score"],
                    "risk_reward_min": t["risk_reward_min"],
                }
                for h, t in self.thresholds.items()
            },
        }


# Singleton instance
_hierarchical_strategy: Optional[HierarchicalStrategy] = None


def get_hierarchical_strategy() -> HierarchicalStrategy:
    """Get or create the singleton hierarchical strategy instance"""
    global _hierarchical_strategy
    if _hierarchical_strategy is None:
        _hierarchical_strategy = HierarchicalStrategy()
    return _hierarchical_strategy
