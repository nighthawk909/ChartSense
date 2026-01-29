"""
Mock Alpaca Service
===================
Provides mock implementations of Alpaca trading API for testing.

This module provides:
- MockAlpacaService: Full mock of AlpacaService class
- Factory functions for creating mock data objects
- Configurable responses for different test scenarios

Usage:
    from tests.mocks.alpaca_mock import MockAlpacaService, create_mock_account

    service = MockAlpacaService()
    service.set_account(equity=100000, buying_power=50000)
    account = await service.get_account()
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock


def create_mock_account(
    equity: float = 100000.0,
    cash: float = 50000.0,
    buying_power: float = 100000.0,
    portfolio_value: float = 100000.0,
    currency: str = "USD",
    pattern_day_trader: bool = False,
    trading_blocked: bool = False,
    account_blocked: bool = False,
    daytrade_count: int = 0,
    last_equity: float = 99500.0,
) -> Dict[str, Any]:
    """
    Create a mock Alpaca account response.

    Args:
        equity: Total account equity
        cash: Available cash
        buying_power: Available buying power
        portfolio_value: Total portfolio value
        currency: Account currency (default USD)
        pattern_day_trader: PDT flag
        trading_blocked: Whether trading is blocked
        account_blocked: Whether account is blocked
        daytrade_count: Number of day trades in period
        last_equity: Previous day's equity

    Returns:
        Dictionary matching Alpaca account format
    """
    return {
        "id": str(uuid.uuid4()),
        "equity": equity,
        "cash": cash,
        "buying_power": buying_power,
        "portfolio_value": portfolio_value,
        "currency": currency,
        "pattern_day_trader": pattern_day_trader,
        "trading_blocked": trading_blocked,
        "account_blocked": account_blocked,
        "daytrade_count": daytrade_count,
        "last_equity": last_equity,
    }


def create_mock_position(
    symbol: str,
    quantity: float,
    entry_price: float,
    current_price: float,
    side: str = "long",
    asset_class: str = "us_equity",
) -> Dict[str, Any]:
    """
    Create a mock Alpaca position response.

    Args:
        symbol: Stock symbol
        quantity: Number of shares
        entry_price: Average entry price
        current_price: Current market price
        side: Position side ("long" or "short")
        asset_class: Asset class ("us_equity" or "crypto")

    Returns:
        Dictionary matching Alpaca position format
    """
    market_value = quantity * current_price
    cost_basis = quantity * entry_price
    unrealized_pnl = market_value - cost_basis
    unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100

    return {
        "symbol": symbol.upper(),
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": current_price,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "side": side,
        "asset_class": asset_class,
    }


def create_mock_order(
    symbol: str,
    quantity: float,
    side: str,
    status: str = "new",
    order_type: str = "market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    filled_price: Optional[float] = None,
    filled_qty: Optional[float] = None,
    time_in_force: str = "day",
) -> Dict[str, Any]:
    """
    Create a mock Alpaca order response.

    Args:
        symbol: Stock symbol
        quantity: Number of shares
        side: Order side ("buy" or "sell")
        status: Order status ("new", "pending", "filled", "canceled", "rejected")
        order_type: Order type ("market", "limit", "stop", "stop_limit")
        limit_price: Limit price for limit orders
        stop_price: Stop price for stop orders
        filled_price: Average fill price
        filled_qty: Filled quantity
        time_in_force: Time in force ("day", "gtc", "ioc", "fok")

    Returns:
        Dictionary matching Alpaca order format
    """
    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())

    order = {
        "id": order_id,
        "client_order_id": f"test_{order_id[:8]}",
        "symbol": symbol.upper(),
        "quantity": quantity,
        "side": side.lower(),
        "type": order_type,
        "status": status,
        "time_in_force": time_in_force,
        "submitted_at": now.isoformat(),
        "filled_at": None,
        "filled_qty": filled_qty or 0,
        "filled_avg_price": filled_price,
    }

    if limit_price:
        order["limit_price"] = limit_price
    if stop_price:
        order["stop_price"] = stop_price

    if status == "filled":
        order["filled_at"] = now.isoformat()
        order["filled_qty"] = quantity
        if filled_price is None and limit_price:
            order["filled_avg_price"] = limit_price

    return order


def create_mock_quote(
    symbol: str,
    bid_price: float,
    ask_price: float,
    bid_size: int = 100,
    ask_size: int = 100,
) -> Dict[str, Any]:
    """
    Create a mock Alpaca quote response.

    Args:
        symbol: Stock symbol
        bid_price: Current bid price
        ask_price: Current ask price
        bid_size: Bid size in shares
        ask_size: Ask size in shares

    Returns:
        Dictionary matching Alpaca quote format
    """
    return {
        "symbol": symbol.upper(),
        "bid_price": bid_price,
        "ask_price": ask_price,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def create_mock_bar(
    symbol: str,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Create a mock Alpaca bar (OHLCV) response.

    Args:
        symbol: Stock symbol
        open_price: Open price
        high_price: High price
        low_price: Low price
        close_price: Close price
        volume: Trading volume
        timestamp: Bar timestamp (default: now)

    Returns:
        Dictionary matching Alpaca bar format
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
    }


def create_mock_bars(
    symbol: str,
    days: int = 100,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.001,
) -> List[Dict[str, Any]]:
    """
    Create a list of mock bars for historical data testing.

    Args:
        symbol: Stock symbol
        days: Number of days of data
        start_price: Starting price
        volatility: Daily volatility (percentage as decimal)
        trend: Daily trend (positive for uptrend, negative for downtrend)

    Returns:
        List of bar dictionaries
    """
    import random

    bars = []
    price = start_price
    current_date = datetime.now(timezone.utc) - timedelta(days=days)

    for i in range(days):
        # Generate daily OHLC
        daily_return = trend + random.gauss(0, volatility)
        open_price = price
        close_price = price * (1 + daily_return)

        # High and low within the range
        range_mult = abs(random.gauss(0, volatility * 2))
        if close_price > open_price:
            high_price = close_price * (1 + range_mult)
            low_price = open_price * (1 - range_mult * 0.5)
        else:
            high_price = open_price * (1 + range_mult * 0.5)
            low_price = close_price * (1 - range_mult)

        # Ensure high >= open, close and low <= open, close
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        volume = int(random.gauss(1000000, 300000))
        volume = max(volume, 100000)

        bars.append(create_mock_bar(
            symbol=symbol,
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            close_price=round(close_price, 2),
            volume=volume,
            timestamp=current_date,
        ))

        price = close_price
        current_date += timedelta(days=1)

    return bars


class MockAlpacaService:
    """
    Mock implementation of AlpacaService for testing.

    Provides configurable responses and state tracking for:
    - Account information
    - Positions
    - Orders
    - Market data (quotes, bars)
    - Market status

    Example:
        service = MockAlpacaService()
        service.set_account(equity=100000)
        service.add_position(create_mock_position("AAPL", 100, 150.0, 155.0))

        account = await service.get_account()
        positions = await service.get_positions()
    """

    def __init__(self, paper_trading: bool = True):
        """
        Initialize mock service with default values.

        Args:
            paper_trading: Whether this is paper trading mode
        """
        self.paper_trading = paper_trading
        self._account = create_mock_account()
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._market_open = True
        self._initialized = True

        # Track method calls for assertions
        self.call_history: List[Dict[str, Any]] = []

        # Configurable error simulation
        self._simulate_error: Optional[str] = None
        self._error_method: Optional[str] = None

    # ============================================================
    # Configuration Methods
    # ============================================================

    def set_account(self, **kwargs) -> None:
        """Update account with specified values"""
        self._account.update(kwargs)

    def add_position(self, position: Dict[str, Any]) -> None:
        """Add a position to the mock service"""
        symbol = position["symbol"]
        self._positions[symbol] = position

    def remove_position(self, symbol: str) -> None:
        """Remove a position from the mock service"""
        if symbol in self._positions:
            del self._positions[symbol]

    def clear_positions(self) -> None:
        """Remove all positions"""
        self._positions.clear()

    def add_order(self, order: Dict[str, Any]) -> None:
        """Add an order to the mock service"""
        order_id = order["id"]
        self._orders[order_id] = order

    def clear_orders(self) -> None:
        """Remove all orders"""
        self._orders.clear()

    def set_market_open(self, is_open: bool) -> None:
        """Set whether market is open"""
        self._market_open = is_open

    def simulate_error(self, error_message: str, method: Optional[str] = None) -> None:
        """
        Configure the service to raise an error.

        Args:
            error_message: Error message to raise
            method: Specific method to fail (None = all methods)
        """
        self._simulate_error = error_message
        self._error_method = method

    def clear_error(self) -> None:
        """Clear error simulation"""
        self._simulate_error = None
        self._error_method = None

    def _check_error(self, method_name: str) -> None:
        """Check if an error should be raised for this method"""
        if self._simulate_error:
            if self._error_method is None or self._error_method == method_name:
                raise Exception(self._simulate_error)

    def _record_call(self, method: str, **kwargs) -> None:
        """Record a method call for test assertions"""
        self.call_history.append({
            "method": method,
            "args": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ============================================================
    # Account Methods
    # ============================================================

    async def get_account(self) -> Dict[str, Any]:
        """Get mock account information"""
        self._record_call("get_account")
        self._check_error("get_account")
        return self._account.copy()

    async def get_buying_power(self) -> float:
        """Get available buying power"""
        self._record_call("get_buying_power")
        self._check_error("get_buying_power")
        return self._account["buying_power"]

    # ============================================================
    # Position Methods
    # ============================================================

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions"""
        self._record_call("get_positions")
        self._check_error("get_positions")
        return list(self._positions.values())

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get a specific position"""
        self._record_call("get_position", symbol=symbol)
        self._check_error("get_position")
        return self._positions.get(symbol.upper())

    # ============================================================
    # Order Methods
    # ============================================================

    async def submit_market_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit a mock market order"""
        self._record_call("submit_market_order", symbol=symbol, quantity=quantity, side=side)
        self._check_error("submit_market_order")

        # Simulate immediate fill for market orders
        current_price = 100.0  # Default price
        if symbol.upper() in self._positions:
            current_price = self._positions[symbol.upper()]["current_price"]

        order = create_mock_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            status="filled",
            order_type="market",
            filled_price=current_price,
            time_in_force=time_in_force,
        )

        self._orders[order["id"]] = order
        return order

    async def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        limit_price: float,
        time_in_force: str = "day",
    ) -> Dict[str, Any]:
        """Submit a mock limit order"""
        self._record_call(
            "submit_limit_order",
            symbol=symbol,
            quantity=quantity,
            side=side,
            limit_price=limit_price,
        )
        self._check_error("submit_limit_order")

        order = create_mock_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            status="new",
            order_type="limit",
            limit_price=limit_price,
            time_in_force=time_in_force,
        )

        self._orders[order["id"]] = order
        return order

    async def submit_stop_loss_order(
        self,
        symbol: str,
        quantity: float,
        stop_price: float,
        time_in_force: str = "gtc",
    ) -> Dict[str, Any]:
        """Submit a mock stop-loss order"""
        self._record_call(
            "submit_stop_loss_order",
            symbol=symbol,
            quantity=quantity,
            stop_price=stop_price,
        )
        self._check_error("submit_stop_loss_order")

        order = create_mock_order(
            symbol=symbol,
            quantity=quantity,
            side="sell",
            status="new",
            order_type="stop",
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

        self._orders[order["id"]] = order
        return order

    async def submit_bracket_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        stop_loss_price: float,
        take_profit_price: float,
        limit_price: Optional[float] = None,
        time_in_force: str = "gtc",
    ) -> Dict[str, Any]:
        """Submit a mock bracket order"""
        self._record_call(
            "submit_bracket_order",
            symbol=symbol,
            quantity=quantity,
            side=side,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
        )
        self._check_error("submit_bracket_order")

        order = create_mock_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            status="new",
            order_type="limit" if limit_price else "market",
            limit_price=limit_price,
            time_in_force=time_in_force,
        )

        order["order_class"] = "bracket"
        order["stop_loss_price"] = stop_loss_price
        order["take_profit_price"] = take_profit_price
        order["legs"] = [
            {"id": str(uuid.uuid4()), "type": "take_profit", "status": "new"},
            {"id": str(uuid.uuid4()), "type": "stop_loss", "status": "new"},
        ]

        self._orders[order["id"]] = order
        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        self._record_call("cancel_order", order_id=order_id)
        self._check_error("cancel_order")

        if order_id in self._orders:
            self._orders[order_id]["status"] = "canceled"
            return True
        return False

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        self._record_call("get_order", order_id=order_id)
        self._check_error("get_order")
        return self._orders.get(order_id)

    async def get_orders(
        self,
        status: str = "all",
        limit: int = 100,
        after: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get order history"""
        self._record_call("get_orders", status=status, limit=limit)
        self._check_error("get_orders")

        orders = list(self._orders.values())

        if status != "all":
            orders = [o for o in orders if o["status"] == status]

        return orders[:limit]

    async def close_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Close a position"""
        self._record_call("close_position", symbol=symbol, quantity=quantity)
        self._check_error("close_position")

        position = self._positions.get(symbol.upper())
        if not position:
            raise Exception(f"Position does not exist for {symbol}")

        qty_to_close = quantity or position["quantity"]

        order = create_mock_order(
            symbol=symbol,
            quantity=qty_to_close,
            side="sell",
            status="filled",
            order_type="market",
            filled_price=position["current_price"],
        )

        if quantity is None or quantity >= position["quantity"]:
            self.remove_position(symbol)
        else:
            position["quantity"] -= quantity

        return order

    async def close_all_positions(self) -> List[Dict[str, Any]]:
        """Close all positions"""
        self._record_call("close_all_positions")
        self._check_error("close_all_positions")

        orders = []
        for symbol, position in list(self._positions.items()):
            order = create_mock_order(
                symbol=symbol,
                quantity=position["quantity"],
                side="sell",
                status="filled",
                filled_price=position["current_price"],
            )
            orders.append(order)

        self.clear_positions()
        return orders

    # ============================================================
    # Market Data Methods
    # ============================================================

    async def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Get latest quote for a symbol"""
        self._record_call("get_latest_quote", symbol=symbol)
        self._check_error("get_latest_quote")

        # Use position price if available, otherwise default
        current_price = 100.0
        if symbol.upper() in self._positions:
            current_price = self._positions[symbol.upper()]["current_price"]

        return create_mock_quote(
            symbol=symbol,
            bid_price=current_price - 0.01,
            ask_price=current_price + 0.01,
        )

    async def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """Get latest bar for a symbol"""
        self._record_call("get_latest_bar", symbol=symbol)
        self._check_error("get_latest_bar")

        current_price = 100.0
        if symbol.upper() in self._positions:
            current_price = self._positions[symbol.upper()]["current_price"]

        return create_mock_bar(
            symbol=symbol,
            open_price=current_price * 0.998,
            high_price=current_price * 1.002,
            low_price=current_price * 0.995,
            close_price=current_price,
            volume=1000000,
        )

    async def get_latest_trade(self, symbol: str) -> Dict[str, Any]:
        """Get the most recent trade for a symbol"""
        self._record_call("get_latest_trade", symbol=symbol)
        self._check_error("get_latest_trade")

        current_price = 100.0
        if symbol.upper() in self._positions:
            current_price = self._positions[symbol.upper()]["current_price"]

        return {
            "symbol": symbol.upper(),
            "price": current_price,
            "size": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exchange": "NYSE",
        }

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical bars"""
        self._record_call("get_bars", symbol=symbol, timeframe=timeframe, limit=limit)
        self._check_error("get_bars")

        current_price = 100.0
        if symbol.upper() in self._positions:
            current_price = self._positions[symbol.upper()]["current_price"]

        # Generate mock historical bars
        return create_mock_bars(
            symbol=symbol,
            days=limit,
            start_price=current_price * 0.9,  # Start 10% lower
            volatility=0.02,
            trend=0.001,
        )

    # ============================================================
    # Market Status Methods
    # ============================================================

    async def is_market_open(self) -> bool:
        """Check if market is open"""
        self._record_call("is_market_open")
        self._check_error("is_market_open")
        return self._market_open

    async def get_market_clock(self) -> Dict[str, Any]:
        """Get market clock info"""
        self._record_call("get_market_clock")
        self._check_error("get_market_clock")

        now = datetime.now(timezone.utc)
        return {
            "is_open": self._market_open,
            "next_open": (now + timedelta(hours=12)).isoformat(),
            "next_close": (now + timedelta(hours=6)).isoformat(),
            "timestamp": now.isoformat(),
        }

    async def get_market_hours_info(self) -> Dict[str, Any]:
        """Get detailed market hours information"""
        self._record_call("get_market_hours_info")
        self._check_error("get_market_hours_info")

        return {
            "is_open": self._market_open,
            "session": "regular" if self._market_open else "closed",
            "can_trade": self._market_open,
            "can_trade_extended": False,
            "current_time_eastern": "10:30:00",
            "market_hours": {
                "pre_market": "4:00 AM - 9:30 AM ET",
                "regular": "9:30 AM - 4:00 PM ET",
                "after_hours": "4:00 PM - 8:00 PM ET",
            },
        }

    async def search_assets(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """Search for tradable assets"""
        self._record_call("search_assets", query=query, limit=limit)
        self._check_error("search_assets")

        # Return mock search results
        mock_results = [
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock", "region": "United States"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "stock", "region": "United States"},
            {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "type": "stock", "region": "United States"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "stock", "region": "United States"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock", "region": "United States"},
        ]

        # Filter by query
        query_upper = query.upper()
        filtered = [r for r in mock_results if query_upper in r["symbol"] or query_upper in r["name"].upper()]

        return filtered[:limit]

    # ============================================================
    # Property
    # ============================================================

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self._initialized
