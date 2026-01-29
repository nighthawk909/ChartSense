"""
Mock Crypto Service
===================
Provides mock implementation of CryptoService for testing.

This module provides:
- MockCryptoService: Full mock of CryptoService class for Alpaca crypto trading
- Factory functions for creating mock crypto data objects

Usage:
    from tests.mocks.crypto_mock import MockCryptoService, create_mock_crypto_quote

    service = MockCryptoService()
    quote = await service.get_crypto_quote("BTC/USD")
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock


def create_mock_crypto_quote(
    symbol: str,
    bid_price: float,
    ask_price: float,
    bid_size: float = 1.0,
    ask_size: float = 1.0,
    price_change_24h: Optional[float] = None,
    price_change_pct_24h: Optional[float] = None,
    volume_24h: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create a mock crypto quote response.

    Args:
        symbol: Crypto symbol like "BTC/USD"
        bid_price: Current bid price
        ask_price: Current ask price
        bid_size: Bid size
        ask_size: Ask size
        price_change_24h: 24h price change (optional, calculated if not provided)
        price_change_pct_24h: 24h price change percentage (optional)
        volume_24h: 24h volume (optional)

    Returns:
        Dictionary matching crypto quote format
    """
    mid_price = (bid_price + ask_price) / 2

    if price_change_24h is None:
        price_change_24h = mid_price * 0.02  # Default 2% gain

    if price_change_pct_24h is None:
        prev_price = mid_price - price_change_24h
        price_change_pct_24h = (price_change_24h / prev_price) * 100 if prev_price > 0 else 0

    if volume_24h is None:
        volume_24h = 1000000.0  # Default volume

    return {
        "symbol": symbol.upper(),
        "bid_price": bid_price,
        "ask_price": ask_price,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "price": mid_price,
        "price_change_24h": price_change_24h,
        "price_change_pct_24h": price_change_pct_24h,
        "volume_24h": volume_24h,
        "high_24h": mid_price * 1.03,
        "low_24h": mid_price * 0.97,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def create_mock_crypto_bar(
    symbol: str,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Create a mock crypto bar (OHLCV) response.

    Args:
        symbol: Crypto symbol
        open_price: Open price
        high_price: High price
        low_price: Low price
        close_price: Close price
        volume: Trading volume
        timestamp: Bar timestamp (default: now)

    Returns:
        Dictionary matching crypto bar format
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    return {
        "symbol": symbol.upper(),
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "timestamp": timestamp.isoformat(),
        "trade_count": int(volume / 0.1),
        "vwap": (high_price + low_price + close_price) / 3,
    }


def create_mock_crypto_bars(
    symbol: str,
    periods: int = 100,
    start_price: float = 50000.0,
    volatility: float = 0.02,
    trend: float = 0.001,
) -> List[Dict[str, Any]]:
    """
    Create a list of mock crypto bars for historical data testing.

    Args:
        symbol: Crypto symbol
        periods: Number of periods
        start_price: Starting price
        volatility: Price volatility
        trend: Daily trend (positive for uptrend)

    Returns:
        List of bar dictionaries
    """
    import random

    bars = []
    price = start_price
    current_time = datetime.now(timezone.utc) - timedelta(hours=periods)

    for i in range(periods):
        daily_return = trend + random.gauss(0, volatility)
        open_price = price
        close_price = price * (1 + daily_return)

        range_mult = abs(random.gauss(0, volatility * 2))
        if close_price > open_price:
            high_price = close_price * (1 + range_mult)
            low_price = open_price * (1 - range_mult * 0.5)
        else:
            high_price = open_price * (1 + range_mult * 0.5)
            low_price = close_price * (1 - range_mult)

        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        volume = random.gauss(100, 30)
        volume = max(volume, 10)

        bars.append(create_mock_crypto_bar(
            symbol=symbol,
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            close_price=round(close_price, 2),
            volume=round(volume, 4),
            timestamp=current_time,
        ))

        price = close_price
        current_time += timedelta(hours=1)

    return bars


def create_mock_crypto_order(
    symbol: str,
    quantity: float,
    side: str,
    status: str = "new",
    order_type: str = "market",
    limit_price: Optional[float] = None,
    filled_price: Optional[float] = None,
    filled_qty: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create a mock crypto order response.

    Args:
        symbol: Crypto symbol
        quantity: Order quantity
        side: Order side ("buy" or "sell")
        status: Order status
        order_type: Order type ("market", "limit")
        limit_price: Limit price for limit orders
        filled_price: Average fill price
        filled_qty: Filled quantity

    Returns:
        Dictionary matching crypto order format
    """
    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())

    order = {
        "id": order_id,
        "client_order_id": f"crypto_test_{order_id[:8]}",
        "symbol": symbol.upper(),
        "qty": quantity,
        "side": side.lower(),
        "type": order_type,
        "status": status,
        "submitted_at": now.isoformat(),
        "filled_at": None,
        "filled_qty": filled_qty or 0,
        "filled_avg_price": filled_price,
        "asset_class": "crypto",
    }

    if limit_price:
        order["limit_price"] = limit_price

    if status == "filled":
        order["filled_at"] = now.isoformat()
        order["filled_qty"] = quantity
        if filled_price is None and limit_price:
            order["filled_avg_price"] = limit_price

    return order


def create_mock_crypto_position(
    symbol: str,
    quantity: float,
    entry_price: float,
    current_price: float,
) -> Dict[str, Any]:
    """
    Create a mock crypto position response.

    Args:
        symbol: Crypto symbol
        quantity: Position size
        entry_price: Average entry price
        current_price: Current market price

    Returns:
        Dictionary matching crypto position format
    """
    market_value = quantity * current_price
    cost_basis = quantity * entry_price
    unrealized_pnl = market_value - cost_basis
    unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100

    return {
        "symbol": symbol.upper(),
        "qty": quantity,
        "avg_entry_price": entry_price,
        "current_price": current_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pl": unrealized_pnl,
        "unrealized_plpc": unrealized_pnl_pct / 100,
        "asset_class": "crypto",
        "side": "long" if quantity > 0 else "short",
    }


class MockCryptoService:
    """
    Mock implementation of CryptoService for testing.

    Provides configurable responses and state tracking for:
    - Crypto quotes
    - Crypto orders
    - Crypto positions
    - Historical bars

    Example:
        service = MockCryptoService()
        service.set_quote("BTC/USD", 50000.0)
        quote = await service.get_crypto_quote("BTC/USD")
    """

    def __init__(self):
        """Initialize mock crypto service with default values."""
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._bars: Dict[str, List[Dict[str, Any]]] = {}

        # Track method calls for assertions
        self.call_history: List[Dict[str, Any]] = []

        # Configurable error simulation
        self._simulate_error: Optional[str] = None
        self._error_method: Optional[str] = None
        self._rate_limited: bool = False

        # Default quotes for common cryptos
        self._default_quotes = {
            "BTC/USD": 50000.0,
            "ETH/USD": 3000.0,
            "SOL/USD": 100.0,
            "DOGE/USD": 0.10,
            "AVAX/USD": 35.0,
            "LINK/USD": 15.0,
            "MATIC/USD": 0.80,
        }

    # ============================================================
    # Configuration Methods
    # ============================================================

    def set_quote(self, symbol: str, price: float, spread: float = 0.001) -> None:
        """Set quote for a symbol"""
        bid = price * (1 - spread / 2)
        ask = price * (1 + spread / 2)
        self._quotes[symbol.upper()] = create_mock_crypto_quote(symbol, bid, ask)

    def add_position(self, position: Dict[str, Any]) -> None:
        """Add a position"""
        symbol = position["symbol"]
        self._positions[symbol.upper()] = position

    def remove_position(self, symbol: str) -> None:
        """Remove a position"""
        if symbol.upper() in self._positions:
            del self._positions[symbol.upper()]

    def clear_positions(self) -> None:
        """Remove all positions"""
        self._positions.clear()

    def add_order(self, order: Dict[str, Any]) -> None:
        """Add an order"""
        self._orders[order["id"]] = order

    def clear_orders(self) -> None:
        """Remove all orders"""
        self._orders.clear()

    def set_bars(self, symbol: str, bars: List[Dict[str, Any]]) -> None:
        """Set historical bars for a symbol"""
        self._bars[symbol.upper()] = bars

    def simulate_error(self, error_message: str, method: Optional[str] = None) -> None:
        """Configure error simulation"""
        self._simulate_error = error_message
        self._error_method = method

    def simulate_rate_limit(self, limited: bool = True) -> None:
        """Configure rate limit simulation"""
        self._rate_limited = limited

    def clear_error(self) -> None:
        """Clear error simulation"""
        self._simulate_error = None
        self._error_method = None
        self._rate_limited = False

    def _check_error(self, method_name: str) -> None:
        """Check if an error should be raised"""
        if self._rate_limited:
            raise Exception("Rate limit exceeded - too many requests")
        if self._simulate_error:
            if self._error_method is None or self._error_method == method_name:
                raise Exception(self._simulate_error)

    def _record_call(self, method: str, **kwargs) -> None:
        """Record a method call"""
        self.call_history.append({
            "method": method,
            "args": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ============================================================
    # Quote Methods
    # ============================================================

    async def get_crypto_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get crypto quote"""
        self._record_call("get_crypto_quote", symbol=symbol)
        self._check_error("get_crypto_quote")

        symbol = symbol.upper()
        if symbol in self._quotes:
            return self._quotes[symbol]

        # Generate default quote if not set
        base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USD", "")
        default_price = self._default_quotes.get(f"{base}/USD", 100.0)

        bid = default_price * 0.999
        ask = default_price * 1.001
        return create_mock_crypto_quote(symbol, bid, ask)

    async def get_crypto_bars(
        self,
        symbol: str,
        timeframe: str = "1Hour",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get historical crypto bars"""
        self._record_call("get_crypto_bars", symbol=symbol, timeframe=timeframe, limit=limit)
        self._check_error("get_crypto_bars")

        symbol = symbol.upper()
        if symbol in self._bars:
            return self._bars[symbol][-limit:]

        # Generate default bars
        default_price = self._default_quotes.get(symbol, 100.0)
        return create_mock_crypto_bars(symbol, limit, default_price)

    # ============================================================
    # Order Methods
    # ============================================================

    async def submit_crypto_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Submit a crypto order"""
        self._record_call(
            "submit_crypto_order",
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type=order_type,
            limit_price=limit_price,
        )
        self._check_error("submit_crypto_order")

        # Get current price for fill simulation
        quote = await self.get_crypto_quote(symbol)
        fill_price = quote["ask_price"] if side == "buy" else quote["bid_price"]

        # Create filled order for market orders
        status = "filled" if order_type == "market" else "new"
        order = create_mock_crypto_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            status=status,
            order_type=order_type,
            limit_price=limit_price,
            filled_price=fill_price if status == "filled" else None,
        )

        self._orders[order["id"]] = order
        return order

    async def cancel_crypto_order(self, order_id: str) -> bool:
        """Cancel a crypto order"""
        self._record_call("cancel_crypto_order", order_id=order_id)
        self._check_error("cancel_crypto_order")

        if order_id in self._orders:
            self._orders[order_id]["status"] = "canceled"
            return True
        return False

    async def get_crypto_orders(
        self,
        status: str = "all",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get crypto orders"""
        self._record_call("get_crypto_orders", status=status, limit=limit)
        self._check_error("get_crypto_orders")

        orders = list(self._orders.values())
        if status != "all":
            orders = [o for o in orders if o["status"] == status]
        return orders[:limit]

    # ============================================================
    # Position Methods
    # ============================================================

    async def get_crypto_positions(self) -> List[Dict[str, Any]]:
        """Get all crypto positions"""
        self._record_call("get_crypto_positions")
        self._check_error("get_crypto_positions")
        return list(self._positions.values())

    async def get_crypto_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get a specific crypto position"""
        self._record_call("get_crypto_position", symbol=symbol)
        self._check_error("get_crypto_position")
        return self._positions.get(symbol.upper())

    async def close_crypto_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Close a crypto position"""
        self._record_call("close_crypto_position", symbol=symbol, quantity=quantity)
        self._check_error("close_crypto_position")

        position = self._positions.get(symbol.upper())
        if not position:
            raise Exception(f"No crypto position found for {symbol}")

        qty_to_close = quantity or position["qty"]
        order = create_mock_crypto_order(
            symbol=symbol,
            quantity=qty_to_close,
            side="sell",
            status="filled",
            filled_price=position["current_price"],
        )

        if quantity is None or quantity >= position["qty"]:
            self.remove_position(symbol)
        else:
            position["qty"] -= quantity

        return order

    # ============================================================
    # Analysis Methods (used by trading bot)
    # ============================================================

    async def analyze_crypto(self, symbol: str) -> Dict[str, Any]:
        """Analyze a crypto for trading signals (simplified mock)"""
        self._record_call("analyze_crypto", symbol=symbol)
        self._check_error("analyze_crypto")

        quote = await self.get_crypto_quote(symbol)
        price = quote["price"]

        # Return mock analysis
        return {
            "symbol": symbol.upper(),
            "price": price,
            "signal": "HOLD",
            "confidence": 50.0,
            "rsi": 50.0,
            "macd_signal": "neutral",
            "trend": "neutral",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }
