"""
Performance Tracker and Self-Optimizer
Tracks trading performance, calculates metrics, and optimizes strategy parameters
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database.models import Trade, PerformanceMetric, BotConfiguration, OptimizationLog
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics"""
    period_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    profit_factor: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown_pct: float
    avg_win: float
    avg_loss: float
    avg_trade: float
    expectancy: float
    avg_trade_duration_hours: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    swing_trades: int
    swing_win_rate: float
    longterm_trades: int
    longterm_win_rate: float


@dataclass
class OptimizationSuggestion:
    """AI-suggested parameter adjustment"""
    parameter: str
    current_value: float
    suggested_value: float
    reason: str
    expected_impact: str


class PerformanceTracker:
    """
    Tracks and calculates trading performance metrics.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize performance tracker.

        Args:
            db: Database session (creates new if not provided)
        """
        self._db = db

    def _get_db(self) -> Session:
        """Get or create database session"""
        if self._db:
            return self._db
        return SessionLocal()

    def calculate_metrics(self, period_days: int = 30) -> PerformanceMetrics:
        """
        Calculate performance metrics for the specified period.

        Args:
            period_days: Number of days to analyze

        Returns:
            PerformanceMetrics with all calculated values
        """
        db = self._get_db()
        try:
            start_date = datetime.now() - timedelta(days=period_days)

            # Get completed trades in period
            trades = db.query(Trade).filter(
                and_(
                    Trade.exit_time != None,
                    Trade.exit_time >= start_date
                )
            ).all()

            if not trades:
                return self._empty_metrics(period_days)

            # Basic counts
            total_trades = len(trades)
            winning_trades = len([t for t in trades if (t.profit_loss or 0) > 0])
            losing_trades = len([t for t in trades if (t.profit_loss or 0) < 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            # P&L calculations
            pnls = [t.profit_loss or 0 for t in trades]
            total_pnl = sum(pnls)

            # Calculate total P&L percentage (weighted by trade size)
            total_invested = sum(t.entry_price * t.quantity for t in trades)
            total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

            # Profit factor
            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

            # Average win/loss
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            avg_win = statistics.mean(wins) if wins else 0
            avg_loss = statistics.mean(losses) if losses else 0

            # Best/worst trades
            best_trade = max(pnls) if pnls else 0
            worst_trade = min(pnls) if pnls else 0

            # Trade duration
            durations = []
            for t in trades:
                if t.entry_time and t.exit_time:
                    duration = (t.exit_time - t.entry_time).total_seconds() / 3600
                    durations.append(duration)
            avg_duration = statistics.mean(durations) if durations else 0

            # Sharpe ratio (simplified - daily returns)
            sharpe_ratio = self._calculate_sharpe_ratio(trades, period_days)

            # Max drawdown
            max_drawdown, max_drawdown_pct = self._calculate_max_drawdown(trades)

            # By trade type
            swing_trades_list = [t for t in trades if t.trade_type == "SWING"]
            swing_wins = len([t for t in swing_trades_list if (t.profit_loss or 0) > 0])
            swing_win_rate = swing_wins / len(swing_trades_list) if swing_trades_list else 0

            longterm_trades_list = [t for t in trades if t.trade_type == "LONG_TERM"]
            longterm_wins = len([t for t in longterm_trades_list if (t.profit_loss or 0) > 0])
            longterm_win_rate = longterm_wins / len(longterm_trades_list) if longterm_trades_list else 0

            # Calculate additional risk metrics
            sortino_ratio = self._calculate_sortino_ratio(trades, period_days)
            calmar_ratio = self._calculate_calmar_ratio(total_pnl_pct, max_drawdown_pct)
            current_drawdown_pct = self._calculate_current_drawdown(trades)

            # Average trade and expectancy
            avg_trade = statistics.mean(pnls) if pnls else 0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if total_trades > 0 else 0

            # Consecutive tracking
            cons_wins, cons_losses, max_cons_wins, max_cons_losses = self._calculate_consecutive_stats(trades)

            return PerformanceMetrics(
                period_days=period_days,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                max_drawdown_pct=max_drawdown_pct,
                current_drawdown_pct=current_drawdown_pct,
                avg_win=avg_win,
                avg_loss=avg_loss,
                avg_trade=avg_trade,
                expectancy=expectancy,
                avg_trade_duration_hours=avg_duration,
                best_trade=best_trade,
                worst_trade=worst_trade,
                consecutive_wins=cons_wins,
                consecutive_losses=cons_losses,
                max_consecutive_wins=max_cons_wins,
                max_consecutive_losses=max_cons_losses,
                swing_trades=len(swing_trades_list),
                swing_win_rate=swing_win_rate,
                longterm_trades=len(longterm_trades_list),
                longterm_win_rate=longterm_win_rate,
            )
        finally:
            if not self._db:
                db.close()

    def _empty_metrics(self, period_days: int) -> PerformanceMetrics:
        """Return empty metrics when no trades exist"""
        return PerformanceMetrics(
            period_days=period_days,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_pnl=0,
            total_pnl_pct=0,
            profit_factor=0,
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            max_drawdown=0,
            max_drawdown_pct=0,
            current_drawdown_pct=0,
            avg_win=0,
            avg_loss=0,
            avg_trade=0,
            expectancy=0,
            avg_trade_duration_hours=0,
            best_trade=0,
            worst_trade=0,
            consecutive_wins=0,
            consecutive_losses=0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            swing_trades=0,
            swing_win_rate=0,
            longterm_trades=0,
            longterm_win_rate=0,
        )

    def _calculate_sharpe_ratio(
        self,
        trades: List[Trade],
        period_days: int,
        risk_free_rate: float = 0.05
    ) -> Optional[float]:
        """
        Calculate Sharpe ratio from trades.

        Args:
            trades: List of completed trades
            period_days: Period in days
            risk_free_rate: Annual risk-free rate (default 5%)

        Returns:
            Sharpe ratio or None if insufficient data
        """
        if len(trades) < 5:
            return None

        # Group trades by date and calculate daily returns
        daily_pnl: Dict[str, float] = {}
        for trade in trades:
            if trade.exit_time:
                date_key = trade.exit_time.strftime("%Y-%m-%d")
                daily_pnl[date_key] = daily_pnl.get(date_key, 0) + (trade.profit_loss or 0)

        if len(daily_pnl) < 5:
            return None

        returns = list(daily_pnl.values())
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0

        if std_return == 0:
            return None

        # Annualize (assuming 252 trading days)
        daily_rf_rate = risk_free_rate / 252
        sharpe = (avg_return - daily_rf_rate) / std_return * (252 ** 0.5)

        return round(sharpe, 2)

    def _calculate_max_drawdown(self, trades: List[Trade]) -> Tuple[float, float]:
        """
        Calculate maximum drawdown from trade history.

        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_pct)
        """
        if not trades:
            return 0, 0

        # Sort by exit time
        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        # Build equity curve
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0

        for trade in sorted_trades:
            cumulative_pnl += trade.profit_loss or 0
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)

        max_drawdown_pct = (max_drawdown / peak * 100) if peak > 0 else 0

        return max_drawdown, max_drawdown_pct

    def _calculate_sortino_ratio(
        self,
        trades: List[Trade],
        period_days: int,
        risk_free_rate: float = 0.05
    ) -> Optional[float]:
        """
        Calculate Sortino ratio (downside deviation only).

        Args:
            trades: List of completed trades
            period_days: Period in days
            risk_free_rate: Annual risk-free rate (default 5%)

        Returns:
            Sortino ratio or None if insufficient data
        """
        if len(trades) < 5:
            return None

        # Group trades by date and calculate daily returns
        daily_pnl: Dict[str, float] = {}
        for trade in trades:
            if trade.exit_time:
                date_key = trade.exit_time.strftime("%Y-%m-%d")
                daily_pnl[date_key] = daily_pnl.get(date_key, 0) + (trade.profit_loss or 0)

        if len(daily_pnl) < 5:
            return None

        returns = list(daily_pnl.values())
        avg_return = statistics.mean(returns)

        # Calculate downside deviation (only negative returns)
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return None  # No downside = infinite Sortino

        import math
        downside_dev = math.sqrt(statistics.mean([r**2 for r in negative_returns]))

        if downside_dev == 0:
            return None

        daily_rf_rate = risk_free_rate / 252
        sortino = (avg_return - daily_rf_rate) / downside_dev * (252 ** 0.5)

        return round(sortino, 2)

    def _calculate_calmar_ratio(
        self,
        total_return_pct: float,
        max_drawdown_pct: float
    ) -> Optional[float]:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            total_return_pct: Total return percentage
            max_drawdown_pct: Maximum drawdown percentage

        Returns:
            Calmar ratio or None
        """
        if max_drawdown_pct <= 0:
            return None

        return round(total_return_pct / max_drawdown_pct, 2)

    def _calculate_current_drawdown(self, trades: List[Trade]) -> float:
        """Calculate current drawdown percentage from peak"""
        if not trades:
            return 0

        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        if not sorted_trades:
            return 0

        cumulative_pnl = 0
        peak = 0

        for trade in sorted_trades:
            cumulative_pnl += trade.profit_loss or 0
            peak = max(peak, cumulative_pnl)

        if peak <= 0:
            return 0

        current_dd = (peak - cumulative_pnl) / peak * 100
        return round(current_dd, 2)

    def _calculate_consecutive_stats(
        self,
        trades: List[Trade]
    ) -> Tuple[int, int, int, int]:
        """
        Calculate consecutive win/loss statistics.

        Returns:
            (current_wins, current_losses, max_wins, max_losses)
        """
        if not trades:
            return 0, 0, 0, 0

        sorted_trades = sorted(
            [t for t in trades if t.exit_time],
            key=lambda t: t.exit_time
        )

        current_wins = 0
        current_losses = 0
        max_wins = 0
        max_losses = 0
        streak = 0
        last_winner = None

        for trade in sorted_trades:
            is_winner = (trade.profit_loss or 0) > 0

            if last_winner is None:
                streak = 1
            elif is_winner == last_winner:
                streak += 1
            else:
                streak = 1

            if is_winner:
                max_wins = max(max_wins, streak)
                current_wins = streak
                current_losses = 0
            else:
                max_losses = max(max_losses, streak)
                current_losses = streak
                current_wins = 0

            last_winner = is_winner

        return current_wins, current_losses, max_wins, max_losses

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get complete dashboard data for the frontend.

        Returns:
            Dict with all performance data needed for dashboard display
        """
        metrics_7d = self.calculate_metrics(period_days=7)
        metrics_30d = self.calculate_metrics(period_days=30)
        metrics_90d = self.calculate_metrics(period_days=90)
        equity_curve = self.get_equity_curve(period_days=90)

        return {
            "summary": {
                "total_trades": metrics_30d.total_trades,
                "win_rate": round(metrics_30d.win_rate * 100, 1),
                "total_pnl": round(metrics_30d.total_pnl, 2),
                "total_pnl_pct": round(metrics_30d.total_pnl_pct, 2),
                "sharpe_ratio": metrics_30d.sharpe_ratio,
                "sortino_ratio": metrics_30d.sortino_ratio,
                "calmar_ratio": metrics_30d.calmar_ratio,
                "profit_factor": round(metrics_30d.profit_factor, 2),
                "max_drawdown_pct": round(metrics_30d.max_drawdown_pct, 2),
                "current_drawdown_pct": metrics_30d.current_drawdown_pct,
                "expectancy": round(metrics_30d.expectancy, 2),
            },
            "periods": {
                "7d": {
                    "trades": metrics_7d.total_trades,
                    "win_rate": round(metrics_7d.win_rate * 100, 1),
                    "pnl": round(metrics_7d.total_pnl, 2),
                    "pnl_pct": round(metrics_7d.total_pnl_pct, 2),
                },
                "30d": {
                    "trades": metrics_30d.total_trades,
                    "win_rate": round(metrics_30d.win_rate * 100, 1),
                    "pnl": round(metrics_30d.total_pnl, 2),
                    "pnl_pct": round(metrics_30d.total_pnl_pct, 2),
                },
                "90d": {
                    "trades": metrics_90d.total_trades,
                    "win_rate": round(metrics_90d.win_rate * 100, 1),
                    "pnl": round(metrics_90d.total_pnl, 2),
                    "pnl_pct": round(metrics_90d.total_pnl_pct, 2),
                },
            },
            "trade_stats": {
                "avg_win": round(metrics_30d.avg_win, 2),
                "avg_loss": round(metrics_30d.avg_loss, 2),
                "avg_trade": round(metrics_30d.avg_trade, 2),
                "best_trade": round(metrics_30d.best_trade, 2),
                "worst_trade": round(metrics_30d.worst_trade, 2),
                "avg_duration_hours": round(metrics_30d.avg_trade_duration_hours, 1),
                "consecutive_wins": metrics_30d.consecutive_wins,
                "consecutive_losses": metrics_30d.consecutive_losses,
                "max_consecutive_wins": metrics_30d.max_consecutive_wins,
                "max_consecutive_losses": metrics_30d.max_consecutive_losses,
            },
            "by_type": {
                "swing": {
                    "trades": metrics_30d.swing_trades,
                    "win_rate": round(metrics_30d.swing_win_rate * 100, 1),
                },
                "longterm": {
                    "trades": metrics_30d.longterm_trades,
                    "win_rate": round(metrics_30d.longterm_win_rate * 100, 1),
                },
            },
            "equity_curve": equity_curve,
        }

    def get_equity_curve(self, period_days: int = 30) -> List[Dict[str, Any]]:
        """
        Get equity curve data for charting.

        Args:
            period_days: Number of days

        Returns:
            List of {date, equity, pnl, cumulative_pnl}
        """
        db = self._get_db()
        try:
            start_date = datetime.now() - timedelta(days=period_days)

            trades = db.query(Trade).filter(
                and_(
                    Trade.exit_time != None,
                    Trade.exit_time >= start_date
                )
            ).order_by(Trade.exit_time).all()

            curve = []
            cumulative_pnl = 0

            for trade in trades:
                cumulative_pnl += trade.profit_loss or 0
                curve.append({
                    "date": trade.exit_time.isoformat() if trade.exit_time else None,
                    "pnl": trade.profit_loss or 0,
                    "cumulative_pnl": cumulative_pnl,
                })

            return curve
        finally:
            if not self._db:
                db.close()

    def get_trade_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Trade], int]:
        """
        Get paginated trade history.

        Args:
            limit: Number of trades to return
            offset: Offset for pagination

        Returns:
            Tuple of (trades, total_count)
        """
        db = self._get_db()
        try:
            total = db.query(Trade).filter(Trade.exit_time != None).count()

            trades = db.query(Trade).filter(
                Trade.exit_time != None
            ).order_by(Trade.exit_time.desc()).offset(offset).limit(limit).all()

            return trades, total
        finally:
            if not self._db:
                db.close()

    def record_daily_metrics(self, account_equity: float):
        """
        Record daily performance snapshot.

        Args:
            account_equity: Current account equity
        """
        db = self._get_db()
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Check if we already have a record for today
            existing = db.query(PerformanceMetric).filter(
                PerformanceMetric.date >= today
            ).first()

            if existing:
                # Update existing record
                metrics = self.calculate_metrics(period_days=1)
                existing.account_equity = account_equity
                existing.total_trades = metrics.total_trades
                existing.winning_trades = metrics.winning_trades
                existing.losing_trades = metrics.losing_trades
                existing.win_rate = metrics.win_rate
                existing.daily_pnl = metrics.total_pnl
            else:
                # Create new record
                metrics = self.calculate_metrics(period_days=30)
                record = PerformanceMetric(
                    date=today,
                    account_equity=account_equity,
                    total_trades=metrics.total_trades,
                    winning_trades=metrics.winning_trades,
                    losing_trades=metrics.losing_trades,
                    win_rate=metrics.win_rate,
                    daily_pnl=metrics.total_pnl,
                    cumulative_pnl=metrics.total_pnl,
                    max_drawdown=metrics.max_drawdown_pct,
                    sharpe_ratio=metrics.sharpe_ratio,
                    profit_factor=metrics.profit_factor,
                )
                db.add(record)

            db.commit()
        finally:
            if not self._db:
                db.close()


class SelfOptimizer:
    """
    AI-powered self-optimization of trading parameters.
    Analyzes performance and suggests/applies parameter adjustments.
    """

    def __init__(
        self,
        tracker: Optional[PerformanceTracker] = None,
        lookback_days: int = 30,
    ):
        """
        Initialize self-optimizer.

        Args:
            tracker: PerformanceTracker instance
            lookback_days: Days to analyze for optimization
        """
        self.tracker = tracker or PerformanceTracker()
        self.lookback_days = lookback_days

    def analyze_and_suggest(self) -> List[OptimizationSuggestion]:
        """
        Analyze recent performance and generate optimization suggestions.

        Returns:
            List of suggested parameter adjustments
        """
        suggestions = []
        metrics = self.tracker.calculate_metrics(self.lookback_days)

        # Need minimum trades for meaningful analysis
        if metrics.total_trades < 10:
            logger.info(f"Only {metrics.total_trades} trades, need 10+ for optimization")
            return suggestions

        # Get current config
        db = SessionLocal()
        try:
            config = db.query(BotConfiguration).filter(
                BotConfiguration.is_active == True
            ).first()

            if not config:
                return suggestions

            # Analyze win rate
            suggestions.extend(self._analyze_win_rate(metrics, config))

            # Analyze profit targets
            suggestions.extend(self._analyze_profit_targets(metrics, config))

            # Analyze stop losses
            suggestions.extend(self._analyze_stop_losses(metrics, config))

            # Analyze trade types
            suggestions.extend(self._analyze_trade_types(metrics, config))

        finally:
            db.close()

        return suggestions

    def _analyze_win_rate(
        self,
        metrics: PerformanceMetrics,
        config: BotConfiguration
    ) -> List[OptimizationSuggestion]:
        """Analyze and suggest entry threshold adjustments based on win rate"""
        suggestions = []

        if metrics.win_rate < 0.40:
            # Too many losing trades - be more selective
            new_threshold = min(config.entry_score_threshold + 5, 90)
            if new_threshold != config.entry_score_threshold:
                suggestions.append(OptimizationSuggestion(
                    parameter="entry_score_threshold",
                    current_value=config.entry_score_threshold,
                    suggested_value=new_threshold,
                    reason=f"Win rate ({metrics.win_rate:.1%}) below 40% target",
                    expected_impact="Fewer trades but higher quality entries",
                ))

        elif metrics.win_rate > 0.65 and metrics.total_trades >= 20:
            # Very high win rate - might be too conservative
            new_threshold = max(config.entry_score_threshold - 3, 60)
            if new_threshold != config.entry_score_threshold:
                suggestions.append(OptimizationSuggestion(
                    parameter="entry_score_threshold",
                    current_value=config.entry_score_threshold,
                    suggested_value=new_threshold,
                    reason=f"Win rate ({metrics.win_rate:.1%}) above 65%, potentially missing opportunities",
                    expected_impact="More trades while maintaining good win rate",
                ))

        return suggestions

    def _analyze_profit_targets(
        self,
        metrics: PerformanceMetrics,
        config: BotConfiguration
    ) -> List[OptimizationSuggestion]:
        """Analyze profit target effectiveness"""
        suggestions = []

        # If average win is much larger than expected target, we might be leaving money on table
        if metrics.avg_win > 0:
            expected_swing_win = config.swing_profit_target_pct * 100  # Convert to dollars (rough)
            if metrics.avg_win > expected_swing_win * 1.5:
                new_target = min(config.swing_profit_target_pct * 1.15, 0.20)
                suggestions.append(OptimizationSuggestion(
                    parameter="swing_profit_target_pct",
                    current_value=config.swing_profit_target_pct,
                    suggested_value=new_target,
                    reason="Average winning trade exceeds target by 50%+",
                    expected_impact="Capture more profit per winning trade",
                ))

        # If profit factor is very high, targets might be too tight
        if metrics.profit_factor > 2.5 and metrics.win_rate > 0.55:
            new_target = min(config.swing_profit_target_pct * 1.10, 0.15)
            if new_target != config.swing_profit_target_pct:
                suggestions.append(OptimizationSuggestion(
                    parameter="swing_profit_target_pct",
                    current_value=config.swing_profit_target_pct,
                    suggested_value=new_target,
                    reason=f"High profit factor ({metrics.profit_factor:.2f}) suggests room for larger targets",
                    expected_impact="Higher average profit per trade",
                ))

        return suggestions

    def _analyze_stop_losses(
        self,
        metrics: PerformanceMetrics,
        config: BotConfiguration
    ) -> List[OptimizationSuggestion]:
        """Analyze stop-loss effectiveness"""
        suggestions = []

        # If many trades are losses and avg loss is close to stop-loss level,
        # stops might be too tight
        if metrics.losing_trades > 0:
            loss_ratio = metrics.losing_trades / metrics.total_trades

            if loss_ratio > 0.50 and abs(metrics.avg_loss) < 50:  # High stop-out rate
                new_stop = min(config.default_stop_loss_pct * 1.20, 0.08)
                suggestions.append(OptimizationSuggestion(
                    parameter="default_stop_loss_pct",
                    current_value=config.default_stop_loss_pct,
                    suggested_value=new_stop,
                    reason=f"High loss rate ({loss_ratio:.1%}) suggests stops may be too tight",
                    expected_impact="Fewer premature stop-outs",
                ))

            elif loss_ratio < 0.25 and abs(metrics.avg_loss) > metrics.avg_win * 1.5:
                # Few losses but they're large - tighten stops
                new_stop = max(config.default_stop_loss_pct * 0.85, 0.03)
                suggestions.append(OptimizationSuggestion(
                    parameter="default_stop_loss_pct",
                    current_value=config.default_stop_loss_pct,
                    suggested_value=new_stop,
                    reason="Average loss significantly exceeds average win",
                    expected_impact="Smaller losses, better risk/reward",
                ))

        return suggestions

    def _analyze_trade_types(
        self,
        metrics: PerformanceMetrics,
        config: BotConfiguration
    ) -> List[OptimizationSuggestion]:
        """Analyze performance by trade type"""
        suggestions = []

        # Compare swing vs long-term performance
        if metrics.swing_trades >= 5 and metrics.longterm_trades >= 5:
            swing_better = metrics.swing_win_rate > metrics.longterm_win_rate + 0.15

            if swing_better:
                suggestions.append(OptimizationSuggestion(
                    parameter="trading_preference",
                    current_value=0,
                    suggested_value=1,
                    reason=f"Swing trades ({metrics.swing_win_rate:.1%}) significantly outperforming long-term ({metrics.longterm_win_rate:.1%})",
                    expected_impact="Focus more on swing trading patterns",
                ))

        return suggestions

    def apply_suggestions(
        self,
        suggestions: List[OptimizationSuggestion],
        auto_apply: bool = True
    ) -> List[OptimizationSuggestion]:
        """
        Apply optimization suggestions to the configuration.

        Args:
            suggestions: List of suggestions to apply
            auto_apply: If True, automatically apply to database

        Returns:
            List of applied suggestions
        """
        if not suggestions:
            return []

        if not auto_apply:
            return suggestions

        db = SessionLocal()
        applied = []

        try:
            config = db.query(BotConfiguration).filter(
                BotConfiguration.is_active == True
            ).first()

            if not config:
                return []

            for suggestion in suggestions:
                # Apply the change
                if suggestion.parameter == "entry_score_threshold":
                    config.entry_score_threshold = suggestion.suggested_value
                elif suggestion.parameter == "swing_profit_target_pct":
                    config.swing_profit_target_pct = suggestion.suggested_value
                elif suggestion.parameter == "longterm_profit_target_pct":
                    config.longterm_profit_target_pct = suggestion.suggested_value
                elif suggestion.parameter == "default_stop_loss_pct":
                    config.default_stop_loss_pct = suggestion.suggested_value
                else:
                    continue  # Skip non-config parameters

                # Log the change
                log = OptimizationLog(
                    parameter_name=suggestion.parameter,
                    old_value=suggestion.current_value,
                    new_value=suggestion.suggested_value,
                    reason=suggestion.reason,
                    applied=True,
                )
                db.add(log)
                applied.append(suggestion)

                logger.info(
                    f"Applied optimization: {suggestion.parameter} "
                    f"{suggestion.current_value} -> {suggestion.suggested_value}"
                )

            db.commit()

        finally:
            db.close()

        return applied

    def run_optimization_cycle(self) -> Dict[str, Any]:
        """
        Run a full optimization cycle.

        Returns:
            Dict with optimization results
        """
        logger.info("Running optimization cycle...")

        # Analyze and generate suggestions
        suggestions = self.analyze_and_suggest()

        if not suggestions:
            logger.info("No optimization suggestions at this time")
            return {
                "suggestions": [],
                "applied": [],
                "message": "No optimization needed",
            }

        # Apply suggestions
        applied = self.apply_suggestions(suggestions)

        return {
            "suggestions": [
                {
                    "parameter": s.parameter,
                    "current": s.current_value,
                    "suggested": s.suggested_value,
                    "reason": s.reason,
                }
                for s in suggestions
            ],
            "applied": [s.parameter for s in applied],
            "message": f"Applied {len(applied)} of {len(suggestions)} suggestions",
        }
