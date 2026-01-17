"""
Order Monitor Service
Tracks order fills, handles partial fills, and monitors order status

This service provides:
1. Real-time order status tracking
2. Partial fill detection and handling
3. Order fill notifications
4. Order history and analytics
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class OrderState(str, Enum):
    """Order state enumeration"""
    NEW = "new"
    PENDING_NEW = "pending_new"
    ACCEPTED = "accepted"
    PENDING_CANCEL = "pending_cancel"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REPLACED = "replaced"
    DONE_FOR_DAY = "done_for_day"
    PENDING_REPLACE = "pending_replace"


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


@dataclass
class TrackedOrder:
    """An order being tracked by the monitor"""
    order_id: str
    symbol: str
    side: str  # buy, sell
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # Status tracking
    status: OrderState = OrderState.NEW
    filled_quantity: float = 0
    filled_avg_price: Optional[float] = None
    remaining_quantity: float = 0

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None

    # Metadata
    order_class: str = "simple"  # simple, bracket, oco
    parent_order_id: Optional[str] = None  # For bracket legs
    child_order_ids: List[str] = field(default_factory=list)
    is_entry: bool = True  # Entry or exit order
    trade_type: str = "SWING"  # SWING, INTRADAY, SCALP

    # Fill history for partial fills
    fills: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity


@dataclass
class FillEvent:
    """Represents a fill event"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    is_partial: bool
    total_filled: float
    remaining: float


class OrderMonitor:
    """
    Monitors and tracks all orders.

    Key responsibilities:
    1. Track order status in real-time
    2. Detect and handle partial fills
    3. Notify on order state changes
    4. Maintain order history
    """

    def __init__(self, alpaca_service=None):
        """
        Initialize order monitor.

        Args:
            alpaca_service: AlpacaService instance for order queries
        """
        self.alpaca = alpaca_service

        # Active orders: order_id -> TrackedOrder
        self._orders: Dict[str, TrackedOrder] = {}

        # Order history (completed/cancelled)
        self._order_history: List[TrackedOrder] = []
        self._max_history = 1000

        # Fill events
        self._fill_events: List[FillEvent] = []

        # Callbacks
        self._on_fill_callbacks: List[Callable] = []
        self._on_partial_fill_callbacks: List[Callable] = []
        self._on_cancelled_callbacks: List[Callable] = []
        self._on_rejected_callbacks: List[Callable] = []

        # Monitoring state
        self._monitor_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 2  # seconds

        # Statistics
        self._stats = {
            "total_orders": 0,
            "filled_orders": 0,
            "cancelled_orders": 0,
            "rejected_orders": 0,
            "partial_fills": 0,
            "total_fills": 0,
        }

    def set_alpaca_service(self, alpaca_service):
        """Set the Alpaca service"""
        self.alpaca = alpaca_service

    # ==================== ORDER TRACKING ====================

    def track_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        order_type: OrderType,
        quantity: float,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        order_class: str = "simple",
        parent_order_id: Optional[str] = None,
        is_entry: bool = True,
        trade_type: str = "SWING",
    ) -> TrackedOrder:
        """
        Start tracking a new order.

        Args:
            order_id: Alpaca order ID
            symbol: Stock symbol
            side: buy or sell
            order_type: Order type
            quantity: Order quantity
            limit_price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            order_class: simple, bracket, or oco
            parent_order_id: Parent order ID for bracket legs
            is_entry: Whether this is an entry order
            trade_type: SWING, INTRADAY, or SCALP

        Returns:
            TrackedOrder object
        """
        order = TrackedOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            order_class=order_class,
            parent_order_id=parent_order_id,
            is_entry=is_entry,
            trade_type=trade_type,
            submitted_at=datetime.now(),
        )

        self._orders[order_id] = order
        self._stats["total_orders"] += 1

        logger.info(f"Tracking order {order_id}: {side} {quantity} {symbol} ({order_type.value})")

        return order

    def untrack_order(self, order_id: str) -> Optional[TrackedOrder]:
        """Stop tracking an order and move to history"""
        order = self._orders.pop(order_id, None)
        if order:
            self._order_history.append(order)
            # Trim history
            if len(self._order_history) > self._max_history:
                self._order_history = self._order_history[-self._max_history:]
        return order

    def get_order(self, order_id: str) -> Optional[TrackedOrder]:
        """Get a tracked order by ID"""
        return self._orders.get(order_id)

    def get_orders_by_symbol(self, symbol: str) -> List[TrackedOrder]:
        """Get all active orders for a symbol"""
        return [o for o in self._orders.values() if o.symbol == symbol]

    def get_all_active_orders(self) -> List[TrackedOrder]:
        """Get all active orders"""
        return list(self._orders.values())

    # ==================== MONITORING ====================

    async def start_monitoring(self):
        """Start the order monitoring loop"""
        if self._monitor_running:
            return

        self._monitor_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Order monitor started")

    async def stop_monitoring(self):
        """Stop the order monitoring loop"""
        self._monitor_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Order monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitor_running:
            try:
                await self._check_all_orders()
                await asyncio.sleep(self._monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in order monitor loop: {e}")
                await asyncio.sleep(5)

    async def _check_all_orders(self):
        """Check status of all tracked orders"""
        if not self._orders or not self.alpaca:
            return

        for order_id, order in list(self._orders.items()):
            try:
                await self._check_order(order)
            except Exception as e:
                logger.debug(f"Error checking order {order_id}: {e}")

    async def _check_order(self, order: TrackedOrder):
        """Check and update status of a single order"""
        if not self.alpaca:
            return

        try:
            api_order = await self.alpaca.get_order(order.order_id)
            if not api_order:
                return

            order.last_checked = datetime.now()

            # Get new status
            new_status_str = api_order.get("status", "").lower()

            # Map status string to enum
            status_map = {
                "new": OrderState.NEW,
                "pending_new": OrderState.PENDING_NEW,
                "accepted": OrderState.ACCEPTED,
                "pending_cancel": OrderState.PENDING_CANCEL,
                "canceled": OrderState.CANCELLED,
                "cancelled": OrderState.CANCELLED,
                "partially_filled": OrderState.PARTIALLY_FILLED,
                "filled": OrderState.FILLED,
                "rejected": OrderState.REJECTED,
                "expired": OrderState.EXPIRED,
                "replaced": OrderState.REPLACED,
                "done_for_day": OrderState.DONE_FOR_DAY,
                "pending_replace": OrderState.PENDING_REPLACE,
            }

            new_status = status_map.get(new_status_str, order.status)
            old_status = order.status

            # Update fill info
            new_filled_qty = float(api_order.get("filled_qty", 0))
            new_filled_price = api_order.get("filled_avg_price")
            if new_filled_price:
                new_filled_price = float(new_filled_price)

            # Detect new fills
            if new_filled_qty > order.filled_quantity:
                fill_qty = new_filled_qty - order.filled_quantity
                await self._handle_fill(order, fill_qty, new_filled_price, new_status)

            # Update order
            order.status = new_status
            order.filled_quantity = new_filled_qty
            order.filled_avg_price = new_filled_price
            order.remaining_quantity = order.quantity - new_filled_qty

            if api_order.get("filled_at"):
                order.filled_at = datetime.fromisoformat(api_order["filled_at"].replace("Z", "+00:00"))

            # Handle terminal states
            if new_status in [OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED]:
                await self._handle_terminal_state(order, new_status, old_status)

        except Exception as e:
            logger.debug(f"Error checking order {order.order_id}: {e}")

    async def _handle_fill(
        self,
        order: TrackedOrder,
        fill_quantity: float,
        fill_price: Optional[float],
        new_status: OrderState,
    ):
        """Handle a fill (full or partial)"""
        is_partial = new_status == OrderState.PARTIALLY_FILLED

        fill_event = FillEvent(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price or 0,
            timestamp=datetime.now(),
            is_partial=is_partial,
            total_filled=order.filled_quantity + fill_quantity,
            remaining=order.quantity - (order.filled_quantity + fill_quantity),
        )

        self._fill_events.append(fill_event)
        self._stats["total_fills"] += 1

        # Add to order's fill history
        order.fills.append({
            "quantity": fill_quantity,
            "price": fill_price,
            "timestamp": datetime.now().isoformat(),
            "is_partial": is_partial,
        })

        logger.info(
            f"Fill: {order.symbol} {order.side} {fill_quantity} @ ${fill_price:.2f if fill_price else 0} "
            f"({'PARTIAL' if is_partial else 'COMPLETE'})"
        )

        # Notify callbacks
        if is_partial:
            self._stats["partial_fills"] += 1
            for callback in self._on_partial_fill_callbacks:
                try:
                    callback(fill_event)
                except Exception as e:
                    logger.error(f"Error in partial fill callback: {e}")
        else:
            for callback in self._on_fill_callbacks:
                try:
                    callback(fill_event)
                except Exception as e:
                    logger.error(f"Error in fill callback: {e}")

    async def _handle_terminal_state(
        self,
        order: TrackedOrder,
        new_status: OrderState,
        old_status: OrderState,
    ):
        """Handle order reaching a terminal state"""

        if new_status == OrderState.FILLED:
            self._stats["filled_orders"] += 1
            logger.info(f"Order {order.order_id} FILLED: {order.symbol} {order.side} {order.filled_quantity} @ ${order.filled_avg_price:.2f if order.filled_avg_price else 0}")

        elif new_status == OrderState.CANCELLED:
            self._stats["cancelled_orders"] += 1
            logger.info(f"Order {order.order_id} CANCELLED: {order.symbol}")
            for callback in self._on_cancelled_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"Error in cancelled callback: {e}")

        elif new_status == OrderState.REJECTED:
            self._stats["rejected_orders"] += 1
            logger.warning(f"Order {order.order_id} REJECTED: {order.symbol}")
            for callback in self._on_rejected_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"Error in rejected callback: {e}")

        elif new_status == OrderState.EXPIRED:
            logger.info(f"Order {order.order_id} EXPIRED: {order.symbol}")

        # Move to history
        self.untrack_order(order.order_id)

    # ==================== PARTIAL FILL HANDLING ====================

    async def handle_partial_fill_completion(
        self,
        order: TrackedOrder,
        action: str = "wait"
    ) -> Optional[Dict[str, Any]]:
        """
        Handle a partially filled order.

        Args:
            order: The partially filled order
            action: 'wait' (do nothing), 'cancel' (cancel remaining), 'market' (fill at market)

        Returns:
            Result of the action
        """
        if order.status != OrderState.PARTIALLY_FILLED:
            return None

        if action == "cancel":
            # Cancel the remaining portion
            if self.alpaca:
                try:
                    await self.alpaca.cancel_order(order.order_id)
                    logger.info(f"Cancelled remaining {order.remaining_quantity} of order {order.order_id}")
                    return {"action": "cancelled", "cancelled_qty": order.remaining_quantity}
                except Exception as e:
                    logger.error(f"Failed to cancel partial order: {e}")

        elif action == "market":
            # Fill remaining at market
            if self.alpaca:
                try:
                    # Cancel original order
                    await self.alpaca.cancel_order(order.order_id)

                    # Submit market order for remaining
                    result = await self.alpaca.submit_market_order(
                        symbol=order.symbol,
                        quantity=order.remaining_quantity,
                        side=order.side,
                    )

                    if result:
                        # Track the new order
                        self.track_order(
                            order_id=result["id"],
                            symbol=order.symbol,
                            side=order.side,
                            order_type=OrderType.MARKET,
                            quantity=order.remaining_quantity,
                            is_entry=order.is_entry,
                            trade_type=order.trade_type,
                        )

                        logger.info(f"Submitted market order for remaining {order.remaining_quantity}")
                        return {"action": "market_filled", "new_order_id": result["id"]}

                except Exception as e:
                    logger.error(f"Failed to complete partial order at market: {e}")

        return {"action": "wait"}

    # ==================== CALLBACKS ====================

    def on_fill(self, callback: Callable):
        """Register callback for fill events"""
        self._on_fill_callbacks.append(callback)

    def on_partial_fill(self, callback: Callable):
        """Register callback for partial fill events"""
        self._on_partial_fill_callbacks.append(callback)

    def on_cancelled(self, callback: Callable):
        """Register callback for cancelled orders"""
        self._on_cancelled_callbacks.append(callback)

    def on_rejected(self, callback: Callable):
        """Register callback for rejected orders"""
        self._on_rejected_callbacks.append(callback)

    # ==================== ANALYTICS ====================

    def get_fill_rate(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get fill rate statistics for a time window"""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        recent_orders = [
            o for o in self._order_history
            if o.submitted_at and o.submitted_at > cutoff
        ]

        if not recent_orders:
            return {
                "total_orders": 0,
                "filled": 0,
                "fill_rate": 0,
                "avg_fill_time_seconds": 0,
            }

        filled = [o for o in recent_orders if o.status == OrderState.FILLED]
        partial = [o for o in recent_orders if o.status == OrderState.PARTIALLY_FILLED]

        # Calculate average fill time
        fill_times = []
        for o in filled:
            if o.submitted_at and o.filled_at:
                fill_time = (o.filled_at - o.submitted_at).total_seconds()
                fill_times.append(fill_time)

        avg_fill_time = sum(fill_times) / len(fill_times) if fill_times else 0

        return {
            "total_orders": len(recent_orders),
            "filled": len(filled),
            "partial": len(partial),
            "fill_rate": len(filled) / len(recent_orders) * 100 if recent_orders else 0,
            "avg_fill_time_seconds": avg_fill_time,
            "time_window_hours": time_window_hours,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall monitoring statistics"""
        return {
            **self._stats,
            "active_orders": len(self._orders),
            "order_history_size": len(self._order_history),
            "fill_rate_24h": self.get_fill_rate(24),
        }

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get order monitor status"""
        return {
            "monitoring": self._monitor_running,
            "active_orders": len(self._orders),
            "orders": [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "side": o.side,
                    "type": o.order_type.value,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "remaining": o.remaining_quantity,
                    "status": o.status.value,
                    "avg_price": o.filled_avg_price,
                    "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
                }
                for o in self._orders.values()
            ],
            "statistics": self.get_statistics(),
        }


# Singleton instance
_order_monitor: Optional[OrderMonitor] = None


def get_order_monitor() -> OrderMonitor:
    """Get the global order monitor instance"""
    global _order_monitor
    if _order_monitor is None:
        _order_monitor = OrderMonitor()
    return _order_monitor
