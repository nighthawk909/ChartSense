"""
Circuit Breaker Service
Hard stops trading when drawdown exceeds thresholds

This service provides:
1. Real-time drawdown monitoring
2. Automatic trading halt on threshold breach
3. Progressive warning system
4. Position liquidation on critical drawdown
5. Cooldown period management
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class BreakerState(str, Enum):
    """Circuit breaker state"""
    NORMAL = "normal"           # Trading allowed
    WARNING = "warning"         # Approaching limit, trading allowed
    TRIGGERED = "triggered"     # Limit hit, trading halted
    COOLDOWN = "cooldown"       # In cooldown period
    MANUAL_HALT = "manual_halt" # Manually halted


class DrawdownType(str, Enum):
    """Type of drawdown that triggered breaker"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    TOTAL = "total"
    CONSECUTIVE_LOSSES = "consecutive_losses"


@dataclass
class BreakerStatus:
    """Current circuit breaker status"""
    state: BreakerState
    trigger_type: DrawdownType
    trigger_message: str
    trigger_time: Optional[datetime]
    cooldown_ends: Optional[datetime]

    # Drawdown levels
    daily_drawdown_pct: float
    weekly_drawdown_pct: float
    total_drawdown_pct: float

    # Peaks
    daily_peak: float
    weekly_peak: float
    all_time_peak: float

    # Current equity
    current_equity: float

    # Loss streak
    consecutive_losses: int


@dataclass
class BreakerConfig:
    """Circuit breaker configuration"""
    # Drawdown thresholds
    daily_max_drawdown_pct: float = 0.03      # 3% daily
    weekly_max_drawdown_pct: float = 0.07     # 7% weekly
    total_max_drawdown_pct: float = 0.15      # 15% total

    # Warning thresholds (percentage of max)
    warning_threshold_pct: float = 0.70       # Warn at 70% of max

    # Consecutive loss threshold
    max_consecutive_losses: int = 5

    # Cooldown settings
    daily_cooldown_hours: int = 4             # 4 hours after daily trigger
    weekly_cooldown_hours: int = 24           # 24 hours after weekly trigger
    total_cooldown_hours: int = 72            # 72 hours after total trigger

    # Actions
    liquidate_on_total_trigger: bool = True   # Liquidate all on total trigger
    reduce_size_on_warning: bool = True       # Reduce position sizes on warning
    warning_size_multiplier: float = 0.5      # Size multiplier during warning


class CircuitBreaker:
    """
    Circuit breaker that halts trading when drawdown exceeds thresholds.

    Key features:
    1. Tracks daily, weekly, and total drawdown
    2. Triggers at configurable thresholds
    3. Provides warning state before trigger
    4. Enforces cooldown periods
    5. Can automatically liquidate positions on critical drawdown
    """

    def __init__(
        self,
        alpaca_service=None,
        exit_manager=None,
        config: Optional[BreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            alpaca_service: AlpacaService for account queries
            exit_manager: ExitManager for position liquidation
            config: BreakerConfig with thresholds
        """
        self.alpaca = alpaca_service
        self.exit_manager = exit_manager
        self.config = config or BreakerConfig()

        # State
        self._state = BreakerState.NORMAL
        self._trigger_type = DrawdownType.NONE
        self._trigger_time: Optional[datetime] = None
        self._trigger_message = ""

        # Peak tracking
        self._daily_peak: float = 0
        self._weekly_peak: float = 0
        self._all_time_peak: float = 0
        self._current_equity: float = 0

        # Date tracking
        self._last_daily_reset: Optional[date] = None
        self._last_weekly_reset: Optional[date] = None
        self._week_start_equity: float = 0

        # Loss tracking
        self._consecutive_losses = 0
        self._last_trade_was_loss = False

        # Monitoring
        self._monitor_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 10  # seconds

        # Callbacks
        self._on_trigger_callbacks: List[Callable] = []
        self._on_warning_callbacks: List[Callable] = []
        self._on_reset_callbacks: List[Callable] = []

        # History
        self._trigger_history: List[Dict[str, Any]] = []

    def set_services(self, alpaca_service=None, exit_manager=None):
        """Set service dependencies"""
        if alpaca_service:
            self.alpaca = alpaca_service
        if exit_manager:
            self.exit_manager = exit_manager

    # ==================== MONITORING ====================

    async def start_monitoring(self):
        """Start continuous monitoring"""
        if self._monitor_running:
            return

        self._monitor_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Circuit breaker monitoring started")

    async def stop_monitoring(self):
        """Stop monitoring"""
        self._monitor_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Circuit breaker monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitor_running:
            try:
                await self._check_drawdown()
                await asyncio.sleep(self._monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in circuit breaker monitor: {e}")
                await asyncio.sleep(30)

    async def _check_drawdown(self):
        """Check current drawdown levels"""
        if not self.alpaca:
            return

        try:
            account = await self.alpaca.get_account()
            current_equity = account.get("equity", 0)

            await self.update(current_equity)

        except Exception as e:
            logger.debug(f"Could not get account for drawdown check: {e}")

    # ==================== CORE LOGIC ====================

    async def update(self, current_equity: float) -> BreakerStatus:
        """
        Update circuit breaker with current equity.

        This should be called regularly (every few seconds to minutes)
        with the current account equity.

        Args:
            current_equity: Current account equity

        Returns:
            BreakerStatus with current state
        """
        self._current_equity = current_equity
        today = date.today()

        # Daily reset
        if self._last_daily_reset != today:
            self._daily_peak = current_equity
            self._last_daily_reset = today
            logger.info(f"Daily peak reset to ${current_equity:.2f}")

            # Weekly reset (Monday)
            if today.weekday() == 0:
                self._weekly_peak = current_equity
                self._week_start_equity = current_equity
                self._last_weekly_reset = today
                logger.info(f"Weekly peak reset to ${current_equity:.2f}")

        # Update peaks (only up, never down)
        self._daily_peak = max(self._daily_peak, current_equity)
        self._weekly_peak = max(self._weekly_peak, current_equity)
        self._all_time_peak = max(self._all_time_peak, current_equity)

        # Calculate drawdowns
        daily_dd = self._calc_drawdown(self._daily_peak, current_equity)
        weekly_dd = self._calc_drawdown(self._weekly_peak, current_equity)
        total_dd = self._calc_drawdown(self._all_time_peak, current_equity)

        # Check cooldown expiration
        if self._state == BreakerState.COOLDOWN:
            await self._check_cooldown_expiration()

        # Don't evaluate if already triggered or in cooldown
        if self._state in [BreakerState.TRIGGERED, BreakerState.COOLDOWN, BreakerState.MANUAL_HALT]:
            return self._build_status(daily_dd, weekly_dd, total_dd)

        # Check for triggers
        triggered = await self._evaluate_triggers(daily_dd, weekly_dd, total_dd)

        if not triggered:
            # Check for warnings
            self._evaluate_warnings(daily_dd, weekly_dd, total_dd)

        return self._build_status(daily_dd, weekly_dd, total_dd)

    def _calc_drawdown(self, peak: float, current: float) -> float:
        """Calculate drawdown percentage"""
        if peak <= 0:
            return 0
        return (peak - current) / peak

    async def _evaluate_triggers(
        self,
        daily_dd: float,
        weekly_dd: float,
        total_dd: float,
    ) -> bool:
        """Evaluate if any trigger threshold is breached"""

        # Check daily drawdown
        if daily_dd >= self.config.daily_max_drawdown_pct:
            await self._trigger(
                DrawdownType.DAILY,
                f"Daily drawdown {daily_dd*100:.1f}% exceeded {self.config.daily_max_drawdown_pct*100:.1f}% limit",
                self.config.daily_cooldown_hours,
            )
            return True

        # Check weekly drawdown
        if weekly_dd >= self.config.weekly_max_drawdown_pct:
            await self._trigger(
                DrawdownType.WEEKLY,
                f"Weekly drawdown {weekly_dd*100:.1f}% exceeded {self.config.weekly_max_drawdown_pct*100:.1f}% limit",
                self.config.weekly_cooldown_hours,
            )
            return True

        # Check total drawdown
        if total_dd >= self.config.total_max_drawdown_pct:
            await self._trigger(
                DrawdownType.TOTAL,
                f"Total drawdown {total_dd*100:.1f}% exceeded {self.config.total_max_drawdown_pct*100:.1f}% limit",
                self.config.total_cooldown_hours,
                liquidate=self.config.liquidate_on_total_trigger,
            )
            return True

        # Check consecutive losses
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            await self._trigger(
                DrawdownType.CONSECUTIVE_LOSSES,
                f"Hit {self._consecutive_losses} consecutive losses",
                self.config.daily_cooldown_hours,
            )
            return True

        return False

    def _evaluate_warnings(
        self,
        daily_dd: float,
        weekly_dd: float,
        total_dd: float,
    ):
        """Evaluate warning thresholds"""
        warning_pct = self.config.warning_threshold_pct

        daily_warning = daily_dd >= self.config.daily_max_drawdown_pct * warning_pct
        weekly_warning = weekly_dd >= self.config.weekly_max_drawdown_pct * warning_pct
        total_warning = total_dd >= self.config.total_max_drawdown_pct * warning_pct

        if daily_warning or weekly_warning or total_warning:
            if self._state != BreakerState.WARNING:
                self._state = BreakerState.WARNING
                self._trigger_message = self._build_warning_message(
                    daily_dd, weekly_dd, total_dd, warning_pct
                )
                logger.warning(f"Circuit breaker WARNING: {self._trigger_message}")

                # Notify callbacks
                for callback in self._on_warning_callbacks:
                    try:
                        callback(self._trigger_message)
                    except Exception as e:
                        logger.error(f"Error in warning callback: {e}")
        else:
            if self._state == BreakerState.WARNING:
                self._state = BreakerState.NORMAL
                self._trigger_message = ""

    def _build_warning_message(
        self,
        daily_dd: float,
        weekly_dd: float,
        total_dd: float,
        warning_pct: float,
    ) -> str:
        """Build warning message"""
        warnings = []
        if daily_dd >= self.config.daily_max_drawdown_pct * warning_pct:
            warnings.append(f"Daily: {daily_dd*100:.1f}%/{self.config.daily_max_drawdown_pct*100:.0f}%")
        if weekly_dd >= self.config.weekly_max_drawdown_pct * warning_pct:
            warnings.append(f"Weekly: {weekly_dd*100:.1f}%/{self.config.weekly_max_drawdown_pct*100:.0f}%")
        if total_dd >= self.config.total_max_drawdown_pct * warning_pct:
            warnings.append(f"Total: {total_dd*100:.1f}%/{self.config.total_max_drawdown_pct*100:.0f}%")
        return f"Approaching limits: {', '.join(warnings)}"

    async def _trigger(
        self,
        trigger_type: DrawdownType,
        message: str,
        cooldown_hours: int,
        liquidate: bool = False,
    ):
        """Trigger the circuit breaker"""
        self._state = BreakerState.TRIGGERED
        self._trigger_type = trigger_type
        self._trigger_time = datetime.now()
        self._trigger_message = message

        logger.critical(f"🚨 CIRCUIT BREAKER TRIGGERED: {message}")

        # Record in history
        self._trigger_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": trigger_type.value,
            "message": message,
            "equity": self._current_equity,
            "daily_peak": self._daily_peak,
            "weekly_peak": self._weekly_peak,
            "all_time_peak": self._all_time_peak,
        })

        # Liquidate positions if requested
        if liquidate and self.exit_manager:
            logger.warning("Initiating emergency position liquidation")
            try:
                from .exit_manager import ExitReason
                await self.exit_manager.exit_all_positions(ExitReason.CIRCUIT_BREAKER)
            except Exception as e:
                logger.error(f"Failed to liquidate positions: {e}")

        # Start cooldown
        self._state = BreakerState.COOLDOWN

        # Notify callbacks
        for callback in self._on_trigger_callbacks:
            try:
                callback(trigger_type, message)
            except Exception as e:
                logger.error(f"Error in trigger callback: {e}")

    async def _check_cooldown_expiration(self):
        """Check if cooldown has expired"""
        if not self._trigger_time:
            return

        cooldown_hours = {
            DrawdownType.DAILY: self.config.daily_cooldown_hours,
            DrawdownType.WEEKLY: self.config.weekly_cooldown_hours,
            DrawdownType.TOTAL: self.config.total_cooldown_hours,
            DrawdownType.CONSECUTIVE_LOSSES: self.config.daily_cooldown_hours,
        }.get(self._trigger_type, 24)

        cooldown_end = self._trigger_time + timedelta(hours=cooldown_hours)

        if datetime.now() >= cooldown_end:
            await self._reset()

    async def _reset(self):
        """Reset the circuit breaker"""
        logger.info("Circuit breaker reset - trading resuming")

        self._state = BreakerState.NORMAL
        self._trigger_type = DrawdownType.NONE
        self._trigger_time = None
        self._trigger_message = ""
        self._consecutive_losses = 0

        # Notify callbacks
        for callback in self._on_reset_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in reset callback: {e}")

    # ==================== LOSS TRACKING ====================

    def record_trade_result(self, pnl: float):
        """
        Record a trade result for consecutive loss tracking.

        Args:
            pnl: Profit/loss from the trade
        """
        if pnl < 0:
            self._consecutive_losses += 1
            self._last_trade_was_loss = True
            logger.info(f"Loss recorded. Consecutive losses: {self._consecutive_losses}")
        else:
            self._consecutive_losses = 0
            self._last_trade_was_loss = False
            logger.info("Win recorded. Consecutive loss streak reset.")

    # ==================== MANUAL CONTROL ====================

    async def manual_halt(self, reason: str = "Manual halt requested"):
        """Manually halt trading"""
        self._state = BreakerState.MANUAL_HALT
        self._trigger_message = reason
        self._trigger_time = datetime.now()
        logger.warning(f"Manual trading halt: {reason}")

    async def manual_resume(self):
        """Manually resume trading"""
        if self._state == BreakerState.MANUAL_HALT:
            await self._reset()

    async def force_reset(self):
        """Force reset the circuit breaker (use with caution)"""
        await self._reset()

    # ==================== QUERIES ====================

    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed.

        Returns:
            (allowed, reason)
        """
        if self._state == BreakerState.NORMAL:
            return True, "Trading allowed"

        if self._state == BreakerState.WARNING:
            return True, f"Warning: {self._trigger_message}"

        if self._state == BreakerState.TRIGGERED:
            return False, f"Breaker triggered: {self._trigger_message}"

        if self._state == BreakerState.COOLDOWN:
            if self._trigger_time:
                cooldown_hours = {
                    DrawdownType.DAILY: self.config.daily_cooldown_hours,
                    DrawdownType.WEEKLY: self.config.weekly_cooldown_hours,
                    DrawdownType.TOTAL: self.config.total_cooldown_hours,
                }.get(self._trigger_type, 24)
                cooldown_end = self._trigger_time + timedelta(hours=cooldown_hours)
                remaining = cooldown_end - datetime.now()
                return False, f"In cooldown ({remaining.total_seconds()/3600:.1f}h remaining)"
            return False, "In cooldown"

        if self._state == BreakerState.MANUAL_HALT:
            return False, f"Manual halt: {self._trigger_message}"

        return False, "Unknown state"

    def get_position_size_multiplier(self) -> float:
        """
        Get position size multiplier based on current state.

        Returns:
            Multiplier (1.0 = full size, 0.5 = half, etc.)
        """
        if self._state == BreakerState.WARNING and self.config.reduce_size_on_warning:
            return self.config.warning_size_multiplier
        return 1.0

    def _build_status(
        self,
        daily_dd: float,
        weekly_dd: float,
        total_dd: float,
    ) -> BreakerStatus:
        """Build status object"""
        cooldown_ends = None
        if self._state == BreakerState.COOLDOWN and self._trigger_time:
            cooldown_hours = {
                DrawdownType.DAILY: self.config.daily_cooldown_hours,
                DrawdownType.WEEKLY: self.config.weekly_cooldown_hours,
                DrawdownType.TOTAL: self.config.total_cooldown_hours,
            }.get(self._trigger_type, 24)
            cooldown_ends = self._trigger_time + timedelta(hours=cooldown_hours)

        return BreakerStatus(
            state=self._state,
            trigger_type=self._trigger_type,
            trigger_message=self._trigger_message,
            trigger_time=self._trigger_time,
            cooldown_ends=cooldown_ends,
            daily_drawdown_pct=daily_dd * 100,
            weekly_drawdown_pct=weekly_dd * 100,
            total_drawdown_pct=total_dd * 100,
            daily_peak=self._daily_peak,
            weekly_peak=self._weekly_peak,
            all_time_peak=self._all_time_peak,
            current_equity=self._current_equity,
            consecutive_losses=self._consecutive_losses,
        )

    # ==================== CALLBACKS ====================

    def on_trigger(self, callback: Callable):
        """Register callback for trigger events"""
        self._on_trigger_callbacks.append(callback)

    def on_warning(self, callback: Callable):
        """Register callback for warning events"""
        self._on_warning_callbacks.append(callback)

    def on_reset(self, callback: Callable):
        """Register callback for reset events"""
        self._on_reset_callbacks.append(callback)

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        can_trade, reason = self.can_trade()

        return {
            "state": self._state.value,
            "can_trade": can_trade,
            "reason": reason,
            "trigger_type": self._trigger_type.value,
            "trigger_message": self._trigger_message,
            "trigger_time": self._trigger_time.isoformat() if self._trigger_time else None,
            "current_equity": self._current_equity,
            "drawdown": {
                "daily_pct": self._calc_drawdown(self._daily_peak, self._current_equity) * 100 if self._daily_peak else 0,
                "weekly_pct": self._calc_drawdown(self._weekly_peak, self._current_equity) * 100 if self._weekly_peak else 0,
                "total_pct": self._calc_drawdown(self._all_time_peak, self._current_equity) * 100 if self._all_time_peak else 0,
            },
            "peaks": {
                "daily": self._daily_peak,
                "weekly": self._weekly_peak,
                "all_time": self._all_time_peak,
            },
            "consecutive_losses": self._consecutive_losses,
            "position_size_multiplier": self.get_position_size_multiplier(),
            "config": {
                "daily_max_drawdown_pct": self.config.daily_max_drawdown_pct * 100,
                "weekly_max_drawdown_pct": self.config.weekly_max_drawdown_pct * 100,
                "total_max_drawdown_pct": self.config.total_max_drawdown_pct * 100,
                "max_consecutive_losses": self.config.max_consecutive_losses,
            },
            "trigger_history": self._trigger_history[-10:],  # Last 10 triggers
        }


# Singleton instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance"""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
