"""
Auto-Optimizer Service
Automatically optimizes strategy weights based on recent market performance.

Runs periodically (default: weekly) and uses walk-forward backtesting to:
1. Test current strategy on recent data
2. Find optimal weights for current market regime
3. Update live strategy weights automatically

This ensures the bot adapts to changing market conditions without manual intervention.
"""
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .walk_forward_backtester import get_walk_forward_backtester, WalkForwardResult
from .strategy_engine import StrategyEngine, DEFAULT_WEIGHTS
from .alpaca_service import get_alpaca_service

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Detected market regime"""
    BULL_TRENDING = "bull_trending"      # Strong uptrend
    BEAR_TRENDING = "bear_trending"      # Strong downtrend
    HIGH_VOLATILITY = "high_volatility"  # Choppy, high VIX
    LOW_VOLATILITY = "low_volatility"    # Quiet, range-bound
    UNKNOWN = "unknown"


@dataclass
class OptimizationResult:
    """Results from an optimization run"""
    timestamp: datetime
    regime: MarketRegime
    old_weights: Dict[str, float]
    new_weights: Dict[str, float]
    backtest_sharpe: float
    backtest_win_rate: float
    backtest_profit_factor: float
    robustness_score: float
    symbols_tested: List[str]
    data_period_days: int
    weights_updated: bool
    reason: str


# Weight presets for different market regimes
REGIME_WEIGHT_ADJUSTMENTS = {
    MarketRegime.BULL_TRENDING: {
        "momentum": 0.35,       # Momentum shines in trends
        "mean_reversion": 0.10, # Less useful in trends
        "rsi": 0.15,
        "sma_crossover": 0.20,  # Trend following works
        "bollinger": 0.10,
        "volume": 0.05,
        "macd": 0.05,
    },
    MarketRegime.BEAR_TRENDING: {
        "momentum": 0.20,       # Still useful for shorts
        "mean_reversion": 0.25, # Oversold bounces
        "rsi": 0.25,            # RSI oversold more reliable
        "sma_crossover": 0.10,
        "bollinger": 0.10,
        "volume": 0.05,
        "macd": 0.05,
    },
    MarketRegime.HIGH_VOLATILITY: {
        "momentum": 0.15,       # Too many whipsaws
        "mean_reversion": 0.30, # Mean reversion works best
        "rsi": 0.20,
        "sma_crossover": 0.05,  # False signals
        "bollinger": 0.20,      # Bollinger bands useful
        "volume": 0.05,
        "macd": 0.05,
    },
    MarketRegime.LOW_VOLATILITY: {
        "momentum": 0.20,
        "mean_reversion": 0.25,
        "rsi": 0.20,
        "sma_crossover": 0.15,
        "bollinger": 0.10,
        "volume": 0.05,
        "macd": 0.05,
    },
}


class AutoOptimizer:
    """
    Automatic strategy optimizer.

    Periodically runs backtests and updates strategy weights based on:
    1. Walk-forward optimization results
    2. Detected market regime
    3. Recent performance metrics
    """

    def __init__(self):
        self.backtester = get_walk_forward_backtester()
        self.alpaca = get_alpaca_service()

        # Optimization settings
        self.optimization_interval_hours = 168  # Weekly by default (7 * 24)
        self.min_interval_hours = 24  # Don't optimize more than once per day
        self.lookback_days = 180  # 6 months of data for backtesting
        self.min_robustness_score = 50  # Don't update if robustness too low

        # State tracking
        self.last_optimization: Optional[datetime] = None
        self.optimization_history: List[OptimizationResult] = []
        self.current_regime: MarketRegime = MarketRegime.UNKNOWN
        self.enabled = True

        # Reference to strategy engine (set externally)
        self._strategy_engine: Optional[StrategyEngine] = None

        # Symbols to use for optimization
        self.optimization_symbols = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

        # Background task
        self._optimization_task: Optional[asyncio.Task] = None

    def set_strategy_engine(self, engine: StrategyEngine):
        """Set the strategy engine to update"""
        self._strategy_engine = engine

    async def start_background_optimization(self):
        """Start the background optimization loop"""
        if self._optimization_task is not None:
            return

        self._optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info("Auto-optimizer background task started")

    async def stop_background_optimization(self):
        """Stop the background optimization loop"""
        if self._optimization_task is not None:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            self._optimization_task = None
            logger.info("Auto-optimizer background task stopped")

    async def _optimization_loop(self):
        """Background loop that runs optimization periodically"""
        while True:
            try:
                # Check if optimization is needed
                if self._should_optimize():
                    logger.info("Starting scheduled optimization...")
                    result = await self.run_optimization()
                    if result:
                        logger.info(f"Optimization complete: {result.reason}")
                        if result.weights_updated:
                            logger.info(f"Weights updated for {result.regime.value} regime")

                # Sleep until next check (check every hour)
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retrying

    def _should_optimize(self) -> bool:
        """Check if optimization should run"""
        if not self.enabled:
            return False

        if self.last_optimization is None:
            return True

        hours_since_last = (datetime.now(timezone.utc) - self.last_optimization).total_seconds() / 3600
        return hours_since_last >= self.optimization_interval_hours

    async def run_optimization(self, force: bool = False) -> Optional[OptimizationResult]:
        """
        Run a full optimization cycle.

        Steps:
        1. Fetch historical data for test symbols
        2. Detect current market regime
        3. Run walk-forward backtest
        4. Compare results to current strategy
        5. Update weights if improvement found
        """
        if not force and not self._should_optimize():
            logger.info("Optimization not needed yet")
            return None

        # Check minimum interval
        if self.last_optimization:
            hours_since = (datetime.now(timezone.utc) - self.last_optimization).total_seconds() / 3600
            if hours_since < self.min_interval_hours and not force:
                logger.info(f"Too soon since last optimization ({hours_since:.1f}h < {self.min_interval_hours}h)")
                return None

        logger.info("Starting auto-optimization...")

        try:
            # 1. Fetch historical data
            historical_data = await self._fetch_historical_data()
            if not historical_data:
                logger.warning("Failed to fetch historical data for optimization")
                return None

            # 2. Detect market regime
            regime = await self._detect_market_regime(historical_data)
            self.current_regime = regime
            logger.info(f"Detected market regime: {regime.value}")

            # 3. Get current weights
            old_weights = self._get_current_weights()

            # 4. Run walk-forward backtest with different weight configurations
            best_weights, backtest_result = await self._find_optimal_weights(historical_data, regime)

            if backtest_result is None:
                logger.warning("Backtest failed - keeping current weights")
                return OptimizationResult(
                    timestamp=datetime.now(timezone.utc),
                    regime=regime,
                    old_weights=old_weights,
                    new_weights=old_weights,
                    backtest_sharpe=0,
                    backtest_win_rate=0,
                    backtest_profit_factor=0,
                    robustness_score=0,
                    symbols_tested=self.optimization_symbols,
                    data_period_days=self.lookback_days,
                    weights_updated=False,
                    reason="Backtest failed"
                )

            # 5. Check if new weights are better
            should_update = self._should_update_weights(backtest_result, best_weights, old_weights)

            if should_update:
                # Update the strategy engine weights
                self._apply_new_weights(best_weights)
                reason = f"Weights optimized for {regime.value} (Sharpe: {backtest_result.out_of_sample_sharpe:.2f})"
            else:
                best_weights = old_weights
                reason = f"Kept existing weights (robustness: {backtest_result.robustness_score:.0f}%)"

            self.last_optimization = datetime.now(timezone.utc)

            result = OptimizationResult(
                timestamp=self.last_optimization,
                regime=regime,
                old_weights=old_weights,
                new_weights=best_weights,
                backtest_sharpe=backtest_result.out_of_sample_sharpe,
                backtest_win_rate=backtest_result.win_rate,
                backtest_profit_factor=backtest_result.profit_factor,
                robustness_score=backtest_result.robustness_score,
                symbols_tested=self.optimization_symbols,
                data_period_days=self.lookback_days,
                weights_updated=should_update,
                reason=reason
            )

            self.optimization_history.append(result)

            # Keep only last 50 optimization results
            if len(self.optimization_history) > 50:
                self.optimization_history = self.optimization_history[-50:]

            return result

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            return None

    async def _fetch_historical_data(self) -> Dict[str, Dict[str, List]]:
        """Fetch historical data for optimization symbols"""
        data = {}
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.lookback_days)

        for symbol in self.optimization_symbols:
            try:
                bars = await asyncio.to_thread(
                    self.alpaca.get_stock_bars,
                    symbol,
                    "1Day",
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    limit=None
                )

                if bars and len(bars) >= 50:
                    data[symbol] = {
                        "opens": [b["open"] for b in bars],
                        "highs": [b["high"] for b in bars],
                        "lows": [b["low"] for b in bars],
                        "closes": [b["close"] for b in bars],
                        "volumes": [b["volume"] for b in bars],
                        "dates": [b.get("timestamp", b.get("t", "")) for b in bars],
                    }
                    logger.debug(f"Fetched {len(bars)} bars for {symbol}")
                else:
                    logger.warning(f"Insufficient data for {symbol}: {len(bars) if bars else 0} bars")

            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {e}")

        return data

    async def _detect_market_regime(self, historical_data: Dict) -> MarketRegime:
        """
        Detect current market regime based on SPY behavior.

        Looks at:
        1. 50-day trend direction
        2. Volatility (ATR as % of price)
        3. Recent momentum
        """
        if "SPY" not in historical_data:
            return MarketRegime.UNKNOWN

        spy_data = historical_data["SPY"]
        closes = spy_data["closes"]
        highs = spy_data["highs"]
        lows = spy_data["lows"]

        if len(closes) < 60:
            return MarketRegime.UNKNOWN

        # Calculate 50-day SMA trend
        sma_50 = sum(closes[-50:]) / 50
        sma_20 = sum(closes[-20:]) / 20
        current_price = closes[-1]

        # Calculate ATR for volatility
        atr_sum = 0
        for i in range(-20, 0):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            atr_sum += tr
        atr = atr_sum / 20
        atr_pct = (atr / current_price) * 100

        # Calculate momentum (20-day return)
        momentum = (closes[-1] - closes[-20]) / closes[-20] * 100

        # Determine regime
        is_trending_up = current_price > sma_50 and sma_20 > sma_50
        is_trending_down = current_price < sma_50 and sma_20 < sma_50
        is_high_vol = atr_pct > 2.0  # ATR > 2% of price

        if is_high_vol:
            return MarketRegime.HIGH_VOLATILITY
        elif is_trending_up and momentum > 3:
            return MarketRegime.BULL_TRENDING
        elif is_trending_down and momentum < -3:
            return MarketRegime.BEAR_TRENDING
        else:
            return MarketRegime.LOW_VOLATILITY

    def _get_current_weights(self) -> Dict[str, float]:
        """Get current strategy weights"""
        if self._strategy_engine:
            return self._strategy_engine.weights.copy()
        return DEFAULT_WEIGHTS.copy()

    async def _find_optimal_weights(
        self,
        historical_data: Dict,
        regime: MarketRegime
    ) -> tuple[Dict[str, float], Optional[WalkForwardResult]]:
        """
        Find optimal weights using walk-forward backtesting.

        Tests:
        1. Current weights
        2. Regime-specific preset weights
        3. Variations of both
        """
        # Get weight configurations to test
        weight_configs = [
            ("current", self._get_current_weights()),
            ("regime_preset", REGIME_WEIGHT_ADJUSTMENTS.get(regime, DEFAULT_WEIGHTS)),
            ("default", DEFAULT_WEIGHTS),
        ]

        best_result = None
        best_weights = self._get_current_weights()
        best_score = -float('inf')

        # Test each weight configuration
        for config_name, weights in weight_configs:
            try:
                result = await self._run_backtest_with_weights(historical_data, weights)
                if result is None:
                    continue

                # Score based on out-of-sample Sharpe and robustness
                score = (result.out_of_sample_sharpe * 0.6) + (result.robustness_score / 100 * 0.4)

                logger.info(
                    f"Config '{config_name}': Sharpe={result.out_of_sample_sharpe:.2f}, "
                    f"WinRate={result.win_rate:.1f}%, Robustness={result.robustness_score:.0f}%, "
                    f"Score={score:.3f}"
                )

                if score > best_score:
                    best_score = score
                    best_result = result
                    best_weights = weights

            except Exception as e:
                logger.warning(f"Backtest failed for {config_name}: {e}")

        return best_weights, best_result

    async def _run_backtest_with_weights(
        self,
        historical_data: Dict,
        weights: Dict[str, float]
    ) -> Optional[WalkForwardResult]:
        """Run a walk-forward backtest with specific weights"""
        # Use SPY as the primary test symbol
        if "SPY" not in historical_data:
            return None

        data = historical_data["SPY"]

        # Create a simple strategy function based on weights
        def weighted_strategy(i, opens, highs, lows, closes, volumes, params):
            """Strategy using weighted indicator scoring"""
            if i < 50:
                return False, ""

            # Calculate individual indicator signals
            signals = {}

            # RSI
            rsi = self._calculate_rsi(closes, i, params.get("rsi_period", 14))
            if rsi < params.get("rsi_oversold", 30):
                signals["rsi"] = 1  # Bullish
            elif rsi > params.get("rsi_overbought", 70):
                signals["rsi"] = -1  # Bearish
            else:
                signals["rsi"] = 0

            # SMA Crossover
            sma_short = sum(closes[i-20:i]) / 20
            sma_long = sum(closes[i-50:i]) / 50
            signals["sma_crossover"] = 1 if sma_short > sma_long else -1

            # Momentum (20-day return)
            momentum = (closes[i] - closes[i-20]) / closes[i-20]
            signals["momentum"] = 1 if momentum > 0.02 else (-1 if momentum < -0.02 else 0)

            # Bollinger Bands
            bb_period = params.get("bb_period", 20)
            bb_std = params.get("bb_std", 2.0)
            sma = sum(closes[i-bb_period:i]) / bb_period
            std = (sum((c - sma)**2 for c in closes[i-bb_period:i]) / bb_period) ** 0.5
            upper = sma + bb_std * std
            lower = sma - bb_std * std
            if closes[i] < lower:
                signals["bollinger"] = 1
                signals["mean_reversion"] = 1
            elif closes[i] > upper:
                signals["bollinger"] = -1
                signals["mean_reversion"] = -1
            else:
                signals["bollinger"] = 0
                signals["mean_reversion"] = 0

            # MACD
            fast_ema = self._calculate_ema(closes, i, params.get("macd_fast", 12))
            slow_ema = self._calculate_ema(closes, i, params.get("macd_slow", 26))
            macd = fast_ema - slow_ema
            signals["macd"] = 1 if macd > 0 else -1

            # Volume (above average = confirmation)
            avg_vol = sum(volumes[i-20:i]) / 20
            signals["volume"] = 1 if volumes[i] > avg_vol * 1.2 else 0

            # Calculate weighted score
            score = 0
            for indicator, signal in signals.items():
                weight = weights.get(indicator, 0)
                score += signal * weight

            # Generate signal based on score
            if score > 0.3:
                return True, "long"
            elif score < -0.3:
                return True, "short"
            return False, ""

        # Run walk-forward backtest
        result = self.backtester.run_walk_forward(
            opens=data["opens"],
            highs=data["highs"],
            lows=data["lows"],
            closes=data["closes"],
            volumes=data["volumes"],
            dates=data["dates"],
            strategy_func=weighted_strategy,
            num_windows=4,
            initial_capital=100000,
        )

        result.symbol = "SPY"
        return result

    def _calculate_rsi(self, closes: List[float], i: int, period: int) -> float:
        """Calculate RSI at index i"""
        if i < period:
            return 50

        gains = []
        losses = []
        for j in range(i - period, i):
            change = closes[j + 1] - closes[j]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_ema(self, closes: List[float], i: int, period: int) -> float:
        """Calculate EMA at index i"""
        if i < period:
            return closes[i]
        mult = 2 / (period + 1)
        value = sum(closes[i-period:i-period+period]) / period
        for j in range(i - period + 1, i + 1):
            value = (closes[j] - value) * mult + value
        return value

    def _should_update_weights(
        self,
        result: WalkForwardResult,
        new_weights: Dict[str, float],
        old_weights: Dict[str, float]
    ) -> bool:
        """Determine if weights should be updated"""
        # Don't update if robustness is too low
        if result.robustness_score < self.min_robustness_score:
            logger.info(f"Robustness too low ({result.robustness_score:.0f}% < {self.min_robustness_score}%)")
            return False

        # Don't update if Sharpe is negative
        if result.out_of_sample_sharpe < 0:
            logger.info(f"Negative Sharpe ratio ({result.out_of_sample_sharpe:.2f})")
            return False

        # Don't update if win rate is too low
        if result.win_rate < 40:
            logger.info(f"Win rate too low ({result.win_rate:.1f}% < 40%)")
            return False

        # Update if weights are different enough
        weight_change = sum(abs(new_weights.get(k, 0) - old_weights.get(k, 0)) for k in set(new_weights) | set(old_weights))
        if weight_change < 0.1:
            logger.info(f"Weights too similar (change: {weight_change:.3f})")
            return False

        return True

    def _apply_new_weights(self, weights: Dict[str, float]):
        """Apply new weights to the strategy engine"""
        if self._strategy_engine:
            self._strategy_engine.update_parameters(weights=weights)
            logger.info(f"Applied new weights: {weights}")
        else:
            logger.warning("No strategy engine set - weights not applied")

    def get_status(self) -> Dict[str, Any]:
        """Get optimizer status"""
        return {
            "enabled": self.enabled,
            "current_regime": self.current_regime.value,
            "last_optimization": self.last_optimization.isoformat() if self.last_optimization else None,
            "optimization_interval_hours": self.optimization_interval_hours,
            "next_optimization_in_hours": self._hours_until_next_optimization(),
            "optimization_symbols": self.optimization_symbols,
            "lookback_days": self.lookback_days,
            "current_weights": self._get_current_weights(),
            "recent_optimizations": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "regime": r.regime.value,
                    "sharpe": r.backtest_sharpe,
                    "win_rate": r.backtest_win_rate,
                    "updated": r.weights_updated,
                    "reason": r.reason,
                }
                for r in self.optimization_history[-5:]
            ],
        }

    def _hours_until_next_optimization(self) -> float:
        """Calculate hours until next scheduled optimization"""
        if self.last_optimization is None:
            return 0
        elapsed = (datetime.now(timezone.utc) - self.last_optimization).total_seconds() / 3600
        remaining = self.optimization_interval_hours - elapsed
        return max(0, remaining)


# Singleton instance
_auto_optimizer: Optional[AutoOptimizer] = None


def get_auto_optimizer() -> AutoOptimizer:
    """Get the global auto-optimizer instance"""
    global _auto_optimizer
    if _auto_optimizer is None:
        _auto_optimizer = AutoOptimizer()
    return _auto_optimizer
