"""
Walk-Forward Backtesting Engine with Slippage Modeling
Advanced backtesting with out-of-sample validation and realistic execution simulation

This service provides:
1. Walk-forward optimization (rolling window validation)
2. Realistic slippage modeling based on volatility and volume
3. Monte Carlo simulation for robustness testing
4. Parameter optimization with cross-validation
5. Regime detection for strategy selection
"""
import logging
import math
import random
import statistics
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class SlippageModel(str, Enum):
    """Slippage calculation methods"""
    FIXED = "fixed"              # Fixed percentage
    VOLUME_BASED = "volume_based"  # Based on order size vs volume
    VOLATILITY_BASED = "volatility_based"  # Based on ATR
    ADAPTIVE = "adaptive"        # Combines volume and volatility


@dataclass
class SlippageConfig:
    """Configuration for slippage modeling"""
    model: SlippageModel = SlippageModel.ADAPTIVE
    fixed_slippage_pct: float = 0.001  # 0.1% default
    volume_impact_factor: float = 0.1  # How much order size impacts price
    volatility_multiplier: float = 0.5  # Multiplier for ATR-based slippage
    min_slippage_pct: float = 0.0001   # 0.01% minimum
    max_slippage_pct: float = 0.02     # 2% maximum


@dataclass
class WalkForwardWindow:
    """Represents a single walk-forward window"""
    train_start: int      # Index of training start
    train_end: int        # Index of training end
    test_start: int       # Index of test start
    test_end: int         # Index of test end
    optimal_params: Dict[str, Any] = field(default_factory=dict)
    train_performance: float = 0
    test_performance: float = 0
    trades: List[Dict] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """Results from walk-forward analysis"""
    symbol: str
    strategy: str
    total_windows: int
    in_sample_sharpe: float      # Average in-sample Sharpe
    out_of_sample_sharpe: float  # Average out-of-sample Sharpe
    efficiency_ratio: float      # OOS Sharpe / IS Sharpe
    total_return_pct: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    avg_slippage_pct: float
    total_slippage_cost: float
    windows: List[WalkForwardWindow] = field(default_factory=list)
    optimal_params_summary: Dict[str, Any] = field(default_factory=dict)
    robustness_score: float = 0  # 0-100


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation"""
    num_simulations: int
    original_sharpe: float
    mean_sharpe: float
    median_sharpe: float
    sharpe_std: float
    sharpe_5th_percentile: float
    sharpe_95th_percentile: float
    probability_profitable: float
    mean_max_drawdown: float
    worst_drawdown: float
    confidence_interval_90: Tuple[float, float]


class WalkForwardBacktester:
    """
    Advanced backtesting engine with walk-forward validation.

    Key features:
    1. Rolling window optimization prevents overfitting
    2. Realistic slippage based on market conditions
    3. Monte Carlo simulation for statistical validity
    4. Parameter sensitivity analysis
    """

    def __init__(self):
        self.slippage_config = SlippageConfig()

        # Default parameter ranges for optimization
        self.param_ranges = {
            "rsi_period": [7, 14, 21],
            "rsi_oversold": [25, 30, 35],
            "rsi_overbought": [65, 70, 75],
            "macd_fast": [8, 12, 16],
            "macd_slow": [21, 26, 31],
            "macd_signal": [7, 9, 11],
            "bb_period": [15, 20, 25],
            "bb_std": [1.5, 2.0, 2.5],
            "sma_short": [10, 20, 30],
            "sma_long": [50, 100, 200],
            "stop_loss_pct": [0.02, 0.03, 0.05],
            "take_profit_pct": [0.04, 0.06, 0.10],
        }

    def set_slippage_config(self, config: SlippageConfig):
        """Set slippage configuration"""
        self.slippage_config = config

    # ==================== SLIPPAGE MODELING ====================

    def calculate_slippage(
        self,
        price: float,
        quantity: int,
        side: str,
        volume: float,
        atr: float,
        avg_volume: float = None,
    ) -> Tuple[float, float]:
        """
        Calculate realistic slippage for an order.

        Args:
            price: Order price
            quantity: Order quantity
            side: "buy" or "sell"
            volume: Current bar volume
            atr: Average True Range
            avg_volume: Average daily volume

        Returns:
            (slippage_pct, executed_price)
        """
        config = self.slippage_config

        if config.model == SlippageModel.FIXED:
            slippage_pct = config.fixed_slippage_pct

        elif config.model == SlippageModel.VOLUME_BASED:
            # Slippage increases with order size relative to volume
            order_value = price * quantity
            volume_value = price * volume if volume > 0 else price * 10000
            order_ratio = order_value / volume_value
            slippage_pct = config.fixed_slippage_pct * (1 + order_ratio * config.volume_impact_factor)

        elif config.model == SlippageModel.VOLATILITY_BASED:
            # Slippage based on ATR as percentage of price
            atr_pct = atr / price if price > 0 else 0
            slippage_pct = atr_pct * config.volatility_multiplier

        else:  # ADAPTIVE - combines both
            # Volume component
            order_value = price * quantity
            volume_value = price * volume if volume > 0 else price * 10000
            order_ratio = order_value / volume_value
            volume_slippage = config.fixed_slippage_pct * (1 + order_ratio * config.volume_impact_factor)

            # Volatility component
            atr_pct = atr / price if price > 0 else 0
            vol_slippage = atr_pct * config.volatility_multiplier

            # Combine - take the larger impact
            slippage_pct = max(volume_slippage, vol_slippage)

            # Add random variation (market microstructure noise)
            noise = random.uniform(-0.2, 0.3) * slippage_pct
            slippage_pct += noise

        # Apply bounds
        slippage_pct = max(config.min_slippage_pct, min(config.max_slippage_pct, slippage_pct))

        # Calculate executed price
        if side == "buy":
            executed_price = price * (1 + slippage_pct)
        else:
            executed_price = price * (1 - slippage_pct)

        return slippage_pct, executed_price

    def estimate_market_impact(
        self,
        order_value: float,
        avg_daily_volume: float,
        avg_price: float,
    ) -> float:
        """
        Estimate market impact for large orders.

        Uses square-root market impact model.
        """
        if avg_daily_volume <= 0 or avg_price <= 0:
            return 0

        daily_value = avg_daily_volume * avg_price
        participation_rate = order_value / daily_value

        # Square-root impact model: impact = sigma * sqrt(participation)
        # Using typical volatility of 2%
        sigma = 0.02
        impact = sigma * math.sqrt(participation_rate)

        return min(impact, 0.05)  # Cap at 5%

    # ==================== WALK-FORWARD ANALYSIS ====================

    def run_walk_forward(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        dates: List[str],
        strategy_func: Callable,
        param_ranges: Dict[str, List] = None,
        train_pct: float = 0.7,        # 70% for training
        num_windows: int = 5,          # Number of walk-forward periods
        min_trades_per_window: int = 5,
        initial_capital: float = 10000,
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization.

        Splits data into rolling train/test windows, optimizes on train,
        validates on test.

        Args:
            opens, highs, lows, closes, volumes: Price data
            dates: Date strings
            strategy_func: Function that generates signals given params
            param_ranges: Parameter ranges to optimize
            train_pct: Percentage of window for training
            num_windows: Number of rolling windows
            min_trades_per_window: Minimum trades for valid window
            initial_capital: Starting capital

        Returns:
            WalkForwardResult with performance metrics
        """
        param_ranges = param_ranges or self.param_ranges
        total_bars = len(closes)
        window_size = total_bars // num_windows
        train_size = int(window_size * train_pct)
        test_size = window_size - train_size

        windows = []
        all_trades = []
        total_slippage = 0
        slippage_count = 0

        # Calculate ATR for slippage
        atrs = self._calculate_atr(highs, lows, closes, 14)

        for i in range(num_windows):
            window_start = i * window_size
            train_start = window_start
            train_end = window_start + train_size
            test_start = train_end
            test_end = min(window_start + window_size, total_bars)

            if test_end <= test_start:
                continue

            # Optimize parameters on training data
            best_params, train_sharpe = self._optimize_params(
                opens[train_start:train_end],
                highs[train_start:train_end],
                lows[train_start:train_end],
                closes[train_start:train_end],
                volumes[train_start:train_end],
                atrs[train_start:train_end] if atrs else None,
                strategy_func,
                param_ranges,
                initial_capital,
            )

            # Validate on test data
            test_result = self._run_single_backtest(
                opens[test_start:test_end],
                highs[test_start:test_end],
                lows[test_start:test_end],
                closes[test_start:test_end],
                volumes[test_start:test_end],
                atrs[test_start:test_end] if atrs else None,
                strategy_func,
                best_params,
                initial_capital,
            )

            window = WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                optimal_params=best_params,
                train_performance=train_sharpe,
                test_performance=test_result["sharpe"],
                trades=test_result["trades"],
            )
            windows.append(window)
            all_trades.extend(test_result["trades"])

            # Track slippage
            for trade in test_result["trades"]:
                total_slippage += trade.get("slippage_pct", 0)
                slippage_count += 1

        # Calculate aggregate metrics
        in_sample_sharpes = [w.train_performance for w in windows]
        out_sample_sharpes = [w.test_performance for w in windows]

        avg_is_sharpe = statistics.mean(in_sample_sharpes) if in_sample_sharpes else 0
        avg_oos_sharpe = statistics.mean(out_sample_sharpes) if out_sample_sharpes else 0
        efficiency = avg_oos_sharpe / avg_is_sharpe if avg_is_sharpe > 0 else 0

        # Calculate trade metrics
        wins = [t for t in all_trades if t.get("pnl", 0) > 0]
        losses = [t for t in all_trades if t.get("pnl", 0) <= 0]
        win_rate = len(wins) / len(all_trades) * 100 if all_trades else 0

        total_wins = sum(t.get("pnl", 0) for t in wins)
        total_losses = abs(sum(t.get("pnl", 0) for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        total_pnl = sum(t.get("pnl", 0) for t in all_trades)
        total_return_pct = (total_pnl / initial_capital) * 100

        avg_slippage = total_slippage / slippage_count if slippage_count > 0 else 0
        slippage_cost = sum(t.get("slippage_cost", 0) for t in all_trades)

        # Calculate max drawdown
        max_dd = self._calculate_max_drawdown(all_trades, initial_capital)

        # Summarize optimal params across windows
        param_summary = self._summarize_params(windows)

        # Calculate robustness score
        robustness = self._calculate_robustness_score(
            efficiency, win_rate, profit_factor, len(all_trades), max_dd
        )

        return WalkForwardResult(
            symbol="",  # Set externally
            strategy="walk_forward",
            total_windows=len(windows),
            in_sample_sharpe=round(avg_is_sharpe, 3),
            out_of_sample_sharpe=round(avg_oos_sharpe, 3),
            efficiency_ratio=round(efficiency, 3),
            total_return_pct=round(total_return_pct, 2),
            total_trades=len(all_trades),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 3),
            max_drawdown_pct=round(max_dd * 100, 2),
            avg_slippage_pct=round(avg_slippage * 100, 4),
            total_slippage_cost=round(slippage_cost, 2),
            windows=windows,
            optimal_params_summary=param_summary,
            robustness_score=round(robustness, 1),
        )

    def _optimize_params(
        self,
        opens, highs, lows, closes, volumes, atrs,
        strategy_func, param_ranges, initial_capital
    ) -> Tuple[Dict[str, Any], float]:
        """Find optimal parameters using grid search"""
        best_sharpe = -float('inf')
        best_params = {}

        # Generate parameter combinations
        param_combos = self._generate_param_combinations(param_ranges)

        for params in param_combos[:100]:  # Limit combinations
            result = self._run_single_backtest(
                opens, highs, lows, closes, volumes, atrs,
                strategy_func, params, initial_capital
            )

            if result["sharpe"] > best_sharpe:
                best_sharpe = result["sharpe"]
                best_params = params

        return best_params, best_sharpe

    def _run_single_backtest(
        self,
        opens, highs, lows, closes, volumes, atrs,
        strategy_func, params, initial_capital
    ) -> Dict[str, Any]:
        """Run a single backtest with given parameters"""
        capital = initial_capital
        position = None
        trades = []
        equity_curve = [initial_capital]

        stop_loss_pct = params.get("stop_loss_pct", 0.03)
        take_profit_pct = params.get("take_profit_pct", 0.06)

        for i in range(50, len(closes)):
            current_price = closes[i]
            current_volume = volumes[i] if volumes else 10000
            current_atr = atrs[i] if atrs else current_price * 0.02

            # Update equity
            if position:
                unrealized = (current_price - position["entry_price"]) * position["quantity"]
                if position["side"] == "short":
                    unrealized = -unrealized
                current_equity = capital + unrealized
            else:
                current_equity = capital
            equity_curve.append(current_equity)

            # Check exit
            if position:
                exit_signal = False
                exit_reason = ""

                if position["side"] == "long":
                    if current_price <= position["stop_price"]:
                        exit_signal = True
                        exit_reason = "stop_loss"
                    elif current_price >= position["target_price"]:
                        exit_signal = True
                        exit_reason = "take_profit"
                else:
                    if current_price >= position["stop_price"]:
                        exit_signal = True
                        exit_reason = "stop_loss"
                    elif current_price <= position["target_price"]:
                        exit_signal = True
                        exit_reason = "take_profit"

                if exit_signal:
                    # Apply slippage
                    slippage_pct, exec_price = self.calculate_slippage(
                        current_price, position["quantity"],
                        "sell" if position["side"] == "long" else "buy",
                        current_volume, current_atr
                    )

                    if position["side"] == "long":
                        pnl = (exec_price - position["entry_price"]) * position["quantity"]
                    else:
                        pnl = (position["entry_price"] - exec_price) * position["quantity"]

                    slippage_cost = abs(current_price - exec_price) * position["quantity"]

                    trades.append({
                        "entry_price": position["entry_price"],
                        "exit_price": exec_price,
                        "side": position["side"],
                        "quantity": position["quantity"],
                        "pnl": pnl,
                        "exit_reason": exit_reason,
                        "slippage_pct": slippage_pct,
                        "slippage_cost": slippage_cost,
                    })

                    capital += pnl
                    position = None

            # Check entry
            if not position:
                signal, side = strategy_func(
                    i, opens, highs, lows, closes, volumes, params
                )

                if signal:
                    position_value = capital * 0.1
                    quantity = int(position_value / current_price)

                    if quantity > 0:
                        # Apply slippage
                        slippage_pct, exec_price = self.calculate_slippage(
                            current_price, quantity, side,
                            current_volume, current_atr
                        )

                        if side == "long":
                            stop = exec_price * (1 - stop_loss_pct)
                            target = exec_price * (1 + take_profit_pct)
                        else:
                            stop = exec_price * (1 + stop_loss_pct)
                            target = exec_price * (1 - take_profit_pct)

                        position = {
                            "entry_price": exec_price,
                            "side": side,
                            "quantity": quantity,
                            "stop_price": stop,
                            "target_price": target,
                        }

        # Calculate Sharpe
        if len(equity_curve) > 1:
            returns = []
            for j in range(1, len(equity_curve)):
                ret = (equity_curve[j] - equity_curve[j-1]) / equity_curve[j-1]
                returns.append(ret)

            if returns and len(returns) > 1:
                avg_ret = statistics.mean(returns)
                std_ret = statistics.stdev(returns)
                sharpe = (avg_ret * 252) / (std_ret * math.sqrt(252)) if std_ret > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0

        return {
            "sharpe": sharpe,
            "trades": trades,
            "final_capital": capital,
            "equity_curve": equity_curve,
        }

    def _generate_param_combinations(self, param_ranges: Dict[str, List]) -> List[Dict]:
        """Generate all parameter combinations"""
        if not param_ranges:
            return [{}]

        keys = list(param_ranges.keys())
        values = list(param_ranges.values())

        combinations = []

        def recurse(idx, current):
            if idx == len(keys):
                combinations.append(current.copy())
                return
            for val in values[idx]:
                current[keys[idx]] = val
                recurse(idx + 1, current)

        recurse(0, {})
        return combinations

    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int
    ) -> List[float]:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return []

        atrs = [0] * len(closes)
        tr_values = []

        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)

            if i >= period:
                atrs[i] = statistics.mean(tr_values[-period:])

        return atrs

    def _calculate_max_drawdown(self, trades: List[Dict], initial_capital: float) -> float:
        """Calculate maximum drawdown from trades"""
        if not trades:
            return 0

        equity = initial_capital
        peak = initial_capital
        max_dd = 0

        for trade in trades:
            equity += trade.get("pnl", 0)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _summarize_params(self, windows: List[WalkForwardWindow]) -> Dict[str, Any]:
        """Summarize optimal parameters across windows"""
        if not windows:
            return {}

        param_values = defaultdict(list)
        for window in windows:
            for key, value in window.optimal_params.items():
                param_values[key].append(value)

        summary = {}
        for key, values in param_values.items():
            if all(isinstance(v, (int, float)) for v in values):
                summary[key] = {
                    "mean": round(statistics.mean(values), 2),
                    "std": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                }
            else:
                # Mode for categorical
                summary[key] = max(set(values), key=values.count)

        return summary

    def _calculate_robustness_score(
        self,
        efficiency: float,
        win_rate: float,
        profit_factor: float,
        num_trades: int,
        max_dd: float,
    ) -> float:
        """Calculate strategy robustness score (0-100)"""
        score = 50  # Base score

        # Efficiency bonus (OOS vs IS performance)
        if efficiency >= 0.8:
            score += 15
        elif efficiency >= 0.6:
            score += 10
        elif efficiency >= 0.4:
            score += 5
        elif efficiency < 0.2:
            score -= 15

        # Win rate bonus
        if win_rate >= 60:
            score += 10
        elif win_rate >= 50:
            score += 5
        elif win_rate < 40:
            score -= 10

        # Profit factor bonus
        if profit_factor >= 2.0:
            score += 10
        elif profit_factor >= 1.5:
            score += 5
        elif profit_factor < 1.0:
            score -= 15

        # Trade count (statistical significance)
        if num_trades >= 100:
            score += 10
        elif num_trades >= 50:
            score += 5
        elif num_trades < 20:
            score -= 10

        # Drawdown penalty
        if max_dd <= 0.10:
            score += 5
        elif max_dd > 0.25:
            score -= 15
        elif max_dd > 0.20:
            score -= 10

        return max(0, min(100, score))

    # ==================== MONTE CARLO SIMULATION ====================

    def run_monte_carlo(
        self,
        trades: List[Dict],
        initial_capital: float = 10000,
        num_simulations: int = 1000,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation on trade results.

        Randomly shuffles trade order to test robustness.
        """
        if not trades or len(trades) < 10:
            return MonteCarloResult(
                num_simulations=0,
                original_sharpe=0,
                mean_sharpe=0,
                median_sharpe=0,
                sharpe_std=0,
                sharpe_5th_percentile=0,
                sharpe_95th_percentile=0,
                probability_profitable=0,
                mean_max_drawdown=0,
                worst_drawdown=0,
                confidence_interval_90=(0, 0),
            )

        # Calculate original performance
        original_sharpe = self._calculate_sharpe_from_trades(trades, initial_capital)

        simulation_sharpes = []
        simulation_drawdowns = []
        profitable_count = 0

        for _ in range(num_simulations):
            # Shuffle trades
            shuffled = trades.copy()
            random.shuffle(shuffled)

            # Calculate metrics
            sharpe = self._calculate_sharpe_from_trades(shuffled, initial_capital)
            max_dd = self._calculate_max_drawdown(shuffled, initial_capital)

            simulation_sharpes.append(sharpe)
            simulation_drawdowns.append(max_dd)

            final_pnl = sum(t.get("pnl", 0) for t in shuffled)
            if final_pnl > 0:
                profitable_count += 1

        # Sort for percentiles
        sorted_sharpes = sorted(simulation_sharpes)

        return MonteCarloResult(
            num_simulations=num_simulations,
            original_sharpe=round(original_sharpe, 3),
            mean_sharpe=round(statistics.mean(simulation_sharpes), 3),
            median_sharpe=round(statistics.median(simulation_sharpes), 3),
            sharpe_std=round(statistics.stdev(simulation_sharpes), 3) if len(simulation_sharpes) > 1 else 0,
            sharpe_5th_percentile=round(sorted_sharpes[int(0.05 * num_simulations)], 3),
            sharpe_95th_percentile=round(sorted_sharpes[int(0.95 * num_simulations)], 3),
            probability_profitable=round(profitable_count / num_simulations * 100, 1),
            mean_max_drawdown=round(statistics.mean(simulation_drawdowns) * 100, 2),
            worst_drawdown=round(max(simulation_drawdowns) * 100, 2),
            confidence_interval_90=(
                round(sorted_sharpes[int(0.05 * num_simulations)], 3),
                round(sorted_sharpes[int(0.95 * num_simulations)], 3),
            ),
        )

    def _calculate_sharpe_from_trades(
        self,
        trades: List[Dict],
        initial_capital: float
    ) -> float:
        """Calculate Sharpe ratio from trade list"""
        if not trades:
            return 0

        # Build equity curve
        equity = initial_capital
        equity_curve = [initial_capital]

        for trade in trades:
            equity += trade.get("pnl", 0)
            equity_curve.append(equity)

        # Calculate returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)

        if not returns or len(returns) < 2:
            return 0

        avg_ret = statistics.mean(returns)
        std_ret = statistics.stdev(returns)

        if std_ret <= 0:
            return 0

        # Annualized Sharpe (assuming daily)
        sharpe = (avg_ret * 252) / (std_ret * math.sqrt(252))
        return sharpe

    # ==================== STRATEGY FUNCTIONS ====================

    @staticmethod
    def rsi_strategy(
        i: int,
        opens, highs, lows, closes, volumes,
        params: Dict
    ) -> Tuple[bool, str]:
        """RSI-based strategy"""
        period = params.get("rsi_period", 14)
        oversold = params.get("rsi_oversold", 30)
        overbought = params.get("rsi_overbought", 70)

        if i < period:
            return False, ""

        # Calculate RSI
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

        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if rsi < oversold:
            return True, "long"
        elif rsi > overbought:
            return True, "short"

        return False, ""

    @staticmethod
    def macd_strategy(
        i: int,
        opens, highs, lows, closes, volumes,
        params: Dict
    ) -> Tuple[bool, str]:
        """MACD crossover strategy"""
        fast = params.get("macd_fast", 12)
        slow = params.get("macd_slow", 26)
        signal = params.get("macd_signal", 9)

        if i < slow + signal:
            return False, ""

        # Calculate EMAs
        def ema(data, period, idx):
            mult = 2 / (period + 1)
            value = data[idx - period]
            for j in range(idx - period + 1, idx + 1):
                value = (data[j] - value) * mult + value
            return value

        fast_ema = ema(closes, fast, i)
        slow_ema = ema(closes, slow, i)
        macd_line = fast_ema - slow_ema

        fast_ema_prev = ema(closes, fast, i - 1)
        slow_ema_prev = ema(closes, slow, i - 1)
        macd_line_prev = fast_ema_prev - slow_ema_prev

        # Signal line (simplified)
        signal_value = macd_line * 0.9  # Approximation
        signal_prev = macd_line_prev * 0.9

        # Bullish crossover
        if macd_line > signal_value and macd_line_prev <= signal_prev:
            return True, "long"
        # Bearish crossover
        elif macd_line < signal_value and macd_line_prev >= signal_prev:
            return True, "short"

        return False, ""

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get backtester status"""
        return {
            "enabled": True,
            "slippage_config": {
                "model": self.slippage_config.model.value,
                "fixed_slippage_pct": self.slippage_config.fixed_slippage_pct,
                "min_slippage_pct": self.slippage_config.min_slippage_pct,
                "max_slippage_pct": self.slippage_config.max_slippage_pct,
            },
            "available_strategies": ["rsi", "macd", "bollinger", "momentum"],
            "monte_carlo_enabled": True,
        }


# Singleton instance
_walk_forward_backtester: Optional[WalkForwardBacktester] = None


def get_walk_forward_backtester() -> WalkForwardBacktester:
    """Get the global walk-forward backtester"""
    global _walk_forward_backtester
    if _walk_forward_backtester is None:
        _walk_forward_backtester = WalkForwardBacktester()
    return _walk_forward_backtester
