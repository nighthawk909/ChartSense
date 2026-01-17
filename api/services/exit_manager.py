"""
Exit Manager Service
Handles automated exit execution, monitoring, and order management

This service provides:
1. Auto stop-loss execution via bracket orders
2. Exit automation at target/stop levels
3. Order monitoring and partial fill handling
4. Trailing stop management
5. Break-even stop adjustment
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Reason for position exit"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_BASED = "time_based"
    CIRCUIT_BREAKER = "circuit_breaker"
    AI_RECOMMENDATION = "ai_recommendation"
    MANUAL = "manual"
    PARTIAL_PROFIT = "partial_profit"
    BREAK_EVEN_STOP = "break_even_stop"
    SIGNAL_REVERSAL = "signal_reversal"
    RISK_LIMIT = "risk_limit"


class OrderStatus(str, Enum):
    """Order status for tracking"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ManagedPosition:
    """A position being managed by the exit manager"""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    trade_type: str  # SWING, INTRADAY, SCALP

    # Exit levels
    stop_loss_price: float
    original_stop_loss: float  # Never changes, for tracking
    take_profit_price: Optional[float] = None
    target_2_price: Optional[float] = None
    trailing_stop_active: bool = False
    trailing_stop_pct: float = 0.03

    # Order tracking
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    trailing_stop_order_id: Optional[str] = None
    bracket_order_id: Optional[str] = None  # Parent bracket order

    # State
    break_even_activated: bool = False
    partial_exit_done: bool = False
    partial_exit_quantity: float = 0
    high_water_mark: float = 0  # Highest price since entry (for trailing)

    # Metadata
    entry_signal_score: float = 0
    entry_reason: str = ""
    horizon: str = ""  # Trading horizon

    def __post_init__(self):
        self.high_water_mark = self.entry_price
        self.original_stop_loss = self.stop_loss_price


@dataclass
class ExitEvent:
    """Record of an exit event"""
    symbol: str
    quantity: float
    entry_price: float
    exit_price: float
    exit_time: datetime
    exit_reason: ExitReason
    pnl_amount: float
    pnl_percent: float
    order_id: str
    hold_duration_minutes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExitManager:
    """
    Manages automated exits for all positions.

    Key responsibilities:
    1. Track all open positions with their exit orders
    2. Monitor for exit conditions (stop, target, trailing, time)
    3. Execute exits when conditions are met
    4. Handle partial fills and order updates
    5. Move stops to break-even when appropriate
    6. Manage trailing stops
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize exit manager.

        Args:
            alpaca_service: AlpacaService instance for order execution
        """
        self.alpaca = alpaca_service

        # Managed positions: symbol -> ManagedPosition
        self._positions: Dict[str, ManagedPosition] = {}

        # Exit history
        self._exit_history: List[ExitEvent] = []
        self._max_history_size = 500

        # Configuration
        self.use_bracket_orders = True  # Use OCO/bracket for auto stop/target
        self.use_trailing_stops = True
        self.break_even_activation_pct = 0.02  # Move to BE after 2% profit
        self.partial_exit_at_pct = 0.05  # Take partial at 5% profit
        self.partial_exit_portion = 0.5  # Exit 50% at first target

        # Time-based exit settings
        self.scalp_max_hold_minutes = 60
        self.intraday_max_hold_hours = 8
        self.swing_max_hold_days = 7

        # Monitoring state
        self._monitor_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval_seconds = 5

        # Callbacks for events
        self._on_exit_callbacks: List[callable] = []
        self._on_stop_adjusted_callbacks: List[callable] = []

    def set_alpaca_service(self, alpaca_service):
        """Set the Alpaca service (for dependency injection)"""
        self.alpaca = alpaca_service

    # ==================== POSITION MANAGEMENT ====================

    async def register_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: Optional[float] = None,
        target_2_price: Optional[float] = None,
        trade_type: str = "SWING",
        entry_signal_score: float = 0,
        entry_reason: str = "",
        horizon: str = "",
        use_bracket: bool = True,
    ) -> ManagedPosition:
        """
        Register a new position for exit management.

        If use_bracket=True and we have both stop_loss and take_profit,
        submits an OCO order to protect the position automatically.

        Args:
            symbol: Stock symbol
            quantity: Position size
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            take_profit_price: Take-profit price (optional)
            target_2_price: Secondary target price (optional)
            trade_type: SWING, INTRADAY, or SCALP
            entry_signal_score: Signal confidence score
            entry_reason: Why we entered
            horizon: Trading horizon
            use_bracket: Whether to place protective orders

        Returns:
            ManagedPosition object
        """
        position = ManagedPosition(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(),
            trade_type=trade_type,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            target_2_price=target_2_price,
            entry_signal_score=entry_signal_score,
            entry_reason=entry_reason,
            horizon=horizon,
        )

        # Place protective orders if requested
        if use_bracket and self.alpaca and self.use_bracket_orders:
            if take_profit_price:
                # Place OCO order (stop + target)
                try:
                    oco_result = await self.alpaca.submit_oco_order(
                        symbol=symbol,
                        quantity=quantity,
                        stop_loss_price=stop_loss_price,
                        take_profit_price=take_profit_price,
                    )
                    if oco_result:
                        position.stop_loss_order_id = oco_result.get("id")
                        position.bracket_order_id = oco_result.get("id")
                        logger.info(f"Placed OCO protection for {symbol}: SL=${stop_loss_price:.2f}, TP=${take_profit_price:.2f}")
                except Exception as e:
                    logger.error(f"Failed to place OCO order for {symbol}: {e}")
                    # Fall back to standalone stop-loss
                    await self._place_standalone_stop(position)
            else:
                # Just place stop-loss
                await self._place_standalone_stop(position)

        self._positions[symbol] = position
        logger.info(f"Registered position for exit management: {symbol} @ ${entry_price:.2f}")

        return position

    async def _place_standalone_stop(self, position: ManagedPosition):
        """Place a standalone stop-loss order"""
        if not self.alpaca:
            return

        try:
            stop_result = await self.alpaca.submit_stop_loss_order(
                symbol=position.symbol,
                quantity=position.quantity,
                stop_price=position.stop_loss_price,
            )
            if stop_result:
                position.stop_loss_order_id = stop_result.get("id")
                logger.info(f"Placed stop-loss for {position.symbol} @ ${position.stop_loss_price:.2f}")
        except Exception as e:
            logger.error(f"Failed to place stop-loss for {position.symbol}: {e}")

    def unregister_position(self, symbol: str) -> Optional[ManagedPosition]:
        """Remove a position from management"""
        return self._positions.pop(symbol, None)

    def get_position(self, symbol: str) -> Optional[ManagedPosition]:
        """Get a managed position by symbol"""
        return self._positions.get(symbol)

    def get_all_positions(self) -> List[ManagedPosition]:
        """Get all managed positions"""
        return list(self._positions.values())

    # ==================== MONITORING ====================

    async def start_monitoring(self):
        """Start the position monitoring loop"""
        if self._monitor_running:
            logger.warning("Exit monitor already running")
            return

        self._monitor_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Exit manager monitoring started")

    async def stop_monitoring(self):
        """Stop the position monitoring loop"""
        self._monitor_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Exit manager monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - checks positions every N seconds"""
        while self._monitor_running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(self._monitor_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in exit monitor loop: {e}")
                await asyncio.sleep(5)

    async def _check_all_positions(self):
        """Check all positions for exit conditions"""
        if not self._positions:
            return

        for symbol, position in list(self._positions.items()):
            try:
                await self._check_position(position)
            except Exception as e:
                logger.error(f"Error checking position {symbol}: {e}")

    async def _check_position(self, position: ManagedPosition):
        """Check a single position for exit conditions"""
        if not self.alpaca:
            return

        # Get current price
        try:
            quote = await self.alpaca.get_latest_quote(position.symbol)
            current_price = (quote["bid_price"] + quote["ask_price"]) / 2
        except Exception as e:
            logger.debug(f"Could not get quote for {position.symbol}: {e}")
            return

        # Update high water mark for trailing stop
        if current_price > position.high_water_mark:
            position.high_water_mark = current_price

        # Calculate current P&L
        pnl_pct = (current_price - position.entry_price) / position.entry_price

        # Check for break-even activation
        if not position.break_even_activated and pnl_pct >= self.break_even_activation_pct:
            await self._activate_break_even(position)

        # Check for trailing stop activation
        if self.use_trailing_stops and not position.trailing_stop_active:
            if pnl_pct >= self.break_even_activation_pct * 2:  # 2x the BE threshold
                await self._activate_trailing_stop(position, current_price)

        # Update trailing stop if active
        if position.trailing_stop_active:
            new_stop = position.high_water_mark * (1 - position.trailing_stop_pct)
            if new_stop > position.stop_loss_price:
                await self._update_stop_loss(position, new_stop, "trailing_stop_adjustment")

        # Check for partial profit taking
        if not position.partial_exit_done and position.take_profit_price:
            if pnl_pct >= self.partial_exit_at_pct:
                await self._execute_partial_exit(position, current_price)

        # Check time-based exit
        exit_due = await self._check_time_based_exit(position)
        if exit_due:
            logger.warning(f"Time-based exit triggered for {position.symbol}")
            await self._execute_exit(
                position=position,
                exit_price=current_price,
                exit_reason=ExitReason.TIME_BASED,
                quantity=position.quantity - position.partial_exit_quantity,
            )

        # Check if orders filled (for positions using bracket/OCO)
        await self._check_order_status(position)

    async def _activate_break_even(self, position: ManagedPosition):
        """Move stop-loss to break-even"""
        # Add small buffer above entry for break-even
        be_price = position.entry_price * 1.001  # 0.1% above entry

        logger.info(f"Activating break-even stop for {position.symbol}: ${position.stop_loss_price:.2f} -> ${be_price:.2f}")

        await self._update_stop_loss(position, be_price, "break_even_activation")
        position.break_even_activated = True

    async def _activate_trailing_stop(self, position: ManagedPosition, current_price: float):
        """Activate trailing stop for a position"""
        position.trailing_stop_active = True

        # Calculate initial trailing stop level
        trailing_stop = current_price * (1 - position.trailing_stop_pct)

        # Only update if it's higher than current stop
        if trailing_stop > position.stop_loss_price:
            await self._update_stop_loss(position, trailing_stop, "trailing_stop_activation")

        logger.info(f"Activated trailing stop for {position.symbol} at {position.trailing_stop_pct*100:.1f}%")

    async def _update_stop_loss(self, position: ManagedPosition, new_stop: float, reason: str):
        """Update the stop-loss price for a position"""
        old_stop = position.stop_loss_price
        position.stop_loss_price = new_stop

        # Update the order if we have one
        if position.stop_loss_order_id and self.alpaca:
            try:
                # Cancel old and place new (safer than replace for complex orders)
                await self.alpaca.cancel_order(position.stop_loss_order_id)

                # Place new stop
                result = await self.alpaca.submit_stop_loss_order(
                    symbol=position.symbol,
                    quantity=position.quantity - position.partial_exit_quantity,
                    stop_price=new_stop,
                )

                if result:
                    position.stop_loss_order_id = result.get("id")
                    logger.info(f"Updated stop-loss for {position.symbol}: ${old_stop:.2f} -> ${new_stop:.2f} ({reason})")
            except Exception as e:
                logger.error(f"Failed to update stop-loss order for {position.symbol}: {e}")

        # Notify callbacks
        for callback in self._on_stop_adjusted_callbacks:
            try:
                callback(position.symbol, old_stop, new_stop, reason)
            except Exception as e:
                logger.error(f"Error in stop adjusted callback: {e}")

    async def _execute_partial_exit(self, position: ManagedPosition, current_price: float):
        """Execute a partial exit to lock in profits"""
        if not self.alpaca:
            return

        exit_quantity = int(position.quantity * self.partial_exit_portion)
        if exit_quantity < 1:
            return

        try:
            result = await self.alpaca.submit_market_order(
                symbol=position.symbol,
                quantity=exit_quantity,
                side="sell",
            )

            if result:
                position.partial_exit_done = True
                position.partial_exit_quantity = exit_quantity

                # Record the partial exit
                pnl_amount = (current_price - position.entry_price) * exit_quantity
                pnl_pct = (current_price - position.entry_price) / position.entry_price * 100

                exit_event = ExitEvent(
                    symbol=position.symbol,
                    quantity=exit_quantity,
                    entry_price=position.entry_price,
                    exit_price=current_price,
                    exit_time=datetime.now(),
                    exit_reason=ExitReason.PARTIAL_PROFIT,
                    pnl_amount=pnl_amount,
                    pnl_percent=pnl_pct,
                    order_id=result.get("id", ""),
                    hold_duration_minutes=int((datetime.now() - position.entry_time).total_seconds() / 60),
                    metadata={"partial": True, "portion": self.partial_exit_portion},
                )
                self._record_exit(exit_event)

                logger.info(
                    f"Partial exit for {position.symbol}: {exit_quantity} shares @ ${current_price:.2f} "
                    f"(P&L: ${pnl_amount:.2f} / {pnl_pct:.2f}%)"
                )

                # Move stop to break-even after partial exit
                if not position.break_even_activated:
                    await self._activate_break_even(position)

        except Exception as e:
            logger.error(f"Failed to execute partial exit for {position.symbol}: {e}")

    async def _check_time_based_exit(self, position: ManagedPosition) -> bool:
        """Check if position should be exited based on hold time"""
        hold_time = datetime.now() - position.entry_time

        if position.trade_type == "SCALP":
            max_hold = timedelta(minutes=self.scalp_max_hold_minutes)
        elif position.trade_type == "INTRADAY":
            max_hold = timedelta(hours=self.intraday_max_hold_hours)
        else:  # SWING
            max_hold = timedelta(days=self.swing_max_hold_days)

        return hold_time > max_hold

    async def _check_order_status(self, position: ManagedPosition):
        """Check if any exit orders have filled"""
        if not self.alpaca or not position.stop_loss_order_id:
            return

        try:
            order = await self.alpaca.get_order(position.stop_loss_order_id)
            if not order:
                return

            status = order.get("status", "")

            if status == "filled":
                # Exit order filled
                filled_price = order.get("filled_avg_price") or position.stop_loss_price
                filled_qty = order.get("filled_qty", position.quantity)

                # Determine exit reason based on fill price
                if position.take_profit_price and abs(filled_price - position.take_profit_price) < 0.01:
                    exit_reason = ExitReason.TAKE_PROFIT
                else:
                    exit_reason = ExitReason.STOP_LOSS

                await self._handle_order_filled(position, filled_price, filled_qty, exit_reason)

            elif status == "partially_filled":
                filled_qty = order.get("filled_qty", 0)
                logger.info(f"Partial fill for {position.symbol}: {filled_qty} shares")

        except Exception as e:
            logger.debug(f"Could not check order status for {position.symbol}: {e}")

    async def _handle_order_filled(
        self,
        position: ManagedPosition,
        exit_price: float,
        quantity: float,
        exit_reason: ExitReason,
    ):
        """Handle a filled exit order"""
        pnl_amount = (exit_price - position.entry_price) * quantity
        pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100

        exit_event = ExitEvent(
            symbol=position.symbol,
            quantity=quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            exit_time=datetime.now(),
            exit_reason=exit_reason,
            pnl_amount=pnl_amount,
            pnl_percent=pnl_pct,
            order_id=position.stop_loss_order_id or "",
            hold_duration_minutes=int((datetime.now() - position.entry_time).total_seconds() / 60),
            metadata={
                "trade_type": position.trade_type,
                "horizon": position.horizon,
                "entry_score": position.entry_signal_score,
                "original_stop": position.original_stop_loss,
                "final_stop": position.stop_loss_price,
                "trailing_active": position.trailing_stop_active,
                "break_even_active": position.break_even_activated,
            },
        )

        self._record_exit(exit_event)

        logger.info(
            f"Position closed: {position.symbol} @ ${exit_price:.2f} ({exit_reason.value}) "
            f"P&L: ${pnl_amount:.2f} ({pnl_pct:.2f}%)"
        )

        # Remove from managed positions
        self.unregister_position(position.symbol)

        # Notify callbacks
        for callback in self._on_exit_callbacks:
            try:
                callback(exit_event)
            except Exception as e:
                logger.error(f"Error in exit callback: {e}")

    # ==================== MANUAL EXITS ====================

    async def _execute_exit(
        self,
        position: ManagedPosition,
        exit_price: float,
        exit_reason: ExitReason,
        quantity: Optional[float] = None,
    ):
        """Execute an exit for a position"""
        if not self.alpaca:
            logger.error("No Alpaca service available for exit execution")
            return

        exit_qty = quantity or (position.quantity - position.partial_exit_quantity)
        if exit_qty <= 0:
            return

        try:
            # Cancel any existing exit orders
            if position.stop_loss_order_id:
                await self.alpaca.cancel_order(position.stop_loss_order_id)
            if position.take_profit_order_id:
                await self.alpaca.cancel_order(position.take_profit_order_id)

            # Submit market sell
            result = await self.alpaca.submit_market_order(
                symbol=position.symbol,
                quantity=exit_qty,
                side="sell",
            )

            if result:
                filled_price = result.get("filled_avg_price", exit_price)
                await self._handle_order_filled(position, filled_price, exit_qty, exit_reason)

        except Exception as e:
            logger.error(f"Failed to execute exit for {position.symbol}: {e}")

    async def exit_position(
        self,
        symbol: str,
        exit_reason: ExitReason = ExitReason.MANUAL,
        quantity: Optional[float] = None,
    ) -> bool:
        """
        Manually exit a position.

        Args:
            symbol: Stock symbol
            exit_reason: Reason for exit
            quantity: Shares to exit (None = all)

        Returns:
            True if exit was successful
        """
        position = self.get_position(symbol)
        if not position:
            logger.warning(f"No managed position found for {symbol}")
            return False

        try:
            quote = await self.alpaca.get_latest_quote(symbol)
            current_price = (quote["bid_price"] + quote["ask_price"]) / 2
        except:
            current_price = position.entry_price  # Fallback

        await self._execute_exit(position, current_price, exit_reason, quantity)
        return True

    async def exit_all_positions(self, exit_reason: ExitReason = ExitReason.CIRCUIT_BREAKER):
        """Exit all managed positions (emergency liquidation)"""
        logger.warning(f"Exiting all positions: {exit_reason.value}")

        for symbol in list(self._positions.keys()):
            await self.exit_position(symbol, exit_reason)

    # ==================== EXIT HISTORY ====================

    def _record_exit(self, exit_event: ExitEvent):
        """Record an exit event to history"""
        self._exit_history.append(exit_event)

        # Trim history if too large
        if len(self._exit_history) > self._max_history_size:
            self._exit_history = self._exit_history[-self._max_history_size:]

    def get_exit_history(
        self,
        limit: int = 50,
        symbol: Optional[str] = None,
        exit_reason: Optional[ExitReason] = None,
    ) -> List[ExitEvent]:
        """Get exit history with optional filters"""
        history = self._exit_history

        if symbol:
            history = [e for e in history if e.symbol == symbol]

        if exit_reason:
            history = [e for e in history if e.exit_reason == exit_reason]

        return history[-limit:]

    def get_exit_statistics(self) -> Dict[str, Any]:
        """Get statistics about exits"""
        if not self._exit_history:
            return {
                "total_exits": 0,
                "win_rate": 0,
                "avg_pnl_pct": 0,
                "total_pnl": 0,
                "best_exit": None,
                "worst_exit": None,
                "by_reason": {},
            }

        wins = [e for e in self._exit_history if e.pnl_amount > 0]
        losses = [e for e in self._exit_history if e.pnl_amount <= 0]

        by_reason = {}
        for reason in ExitReason:
            reason_exits = [e for e in self._exit_history if e.exit_reason == reason]
            if reason_exits:
                by_reason[reason.value] = {
                    "count": len(reason_exits),
                    "avg_pnl_pct": sum(e.pnl_percent for e in reason_exits) / len(reason_exits),
                    "total_pnl": sum(e.pnl_amount for e in reason_exits),
                }

        sorted_by_pnl = sorted(self._exit_history, key=lambda e: e.pnl_percent)

        return {
            "total_exits": len(self._exit_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(self._exit_history) * 100 if self._exit_history else 0,
            "avg_pnl_pct": sum(e.pnl_percent for e in self._exit_history) / len(self._exit_history),
            "total_pnl": sum(e.pnl_amount for e in self._exit_history),
            "avg_hold_minutes": sum(e.hold_duration_minutes for e in self._exit_history) / len(self._exit_history),
            "best_exit": {
                "symbol": sorted_by_pnl[-1].symbol,
                "pnl_pct": sorted_by_pnl[-1].pnl_percent,
            } if sorted_by_pnl else None,
            "worst_exit": {
                "symbol": sorted_by_pnl[0].symbol,
                "pnl_pct": sorted_by_pnl[0].pnl_percent,
            } if sorted_by_pnl else None,
            "by_reason": by_reason,
        }

    # ==================== CALLBACKS ====================

    def on_exit(self, callback: callable):
        """Register a callback for exit events"""
        self._on_exit_callbacks.append(callback)

    def on_stop_adjusted(self, callback: callable):
        """Register a callback for stop adjustments"""
        self._on_stop_adjusted_callbacks.append(callback)

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get exit manager status"""
        return {
            "monitoring": self._monitor_running,
            "managed_positions": len(self._positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity - p.partial_exit_quantity,
                    "entry_price": p.entry_price,
                    "stop_loss": p.stop_loss_price,
                    "take_profit": p.take_profit_price,
                    "trailing_active": p.trailing_stop_active,
                    "break_even_active": p.break_even_activated,
                    "partial_exit_done": p.partial_exit_done,
                    "high_water_mark": p.high_water_mark,
                    "trade_type": p.trade_type,
                    "hold_minutes": int((datetime.now() - p.entry_time).total_seconds() / 60),
                }
                for p in self._positions.values()
            ],
            "total_exits": len(self._exit_history),
            "exit_stats": self.get_exit_statistics(),
            "settings": {
                "use_bracket_orders": self.use_bracket_orders,
                "use_trailing_stops": self.use_trailing_stops,
                "break_even_activation_pct": self.break_even_activation_pct,
                "partial_exit_at_pct": self.partial_exit_at_pct,
                "partial_exit_portion": self.partial_exit_portion,
            },
        }


# Singleton instance
_exit_manager: Optional[ExitManager] = None


def get_exit_manager() -> ExitManager:
    """Get the global exit manager instance"""
    global _exit_manager
    if _exit_manager is None:
        _exit_manager = ExitManager()
    return _exit_manager
