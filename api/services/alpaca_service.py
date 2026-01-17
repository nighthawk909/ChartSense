"""
Alpaca Trading API Integration Service
Handles all communication with Alpaca brokerage for live/paper trading
"""
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AlpacaService:
    """
    Service for interacting with Alpaca Trading API.
    Supports both paper trading and live trading.
    """

    def __init__(self, paper_trading: bool = True):
        """
        Initialize Alpaca client.

        Args:
            paper_trading: If True, use paper trading API (default for safety)
        """
        self.api_key = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.paper_trading = paper_trading

        # Select base URL based on trading mode
        if paper_trading:
            self.base_url = os.getenv(
                "ALPACA_PAPER_URL",
                "https://paper-api.alpaca.markets"
            )
        else:
            self.base_url = os.getenv(
                "ALPACA_LIVE_URL",
                "https://api.alpaca.markets"
            )

        self.data_url = "https://data.alpaca.markets"
        self._api = None
        self._initialized = False

    def _get_api(self):
        """Lazy initialization of Alpaca API client"""
        if self._api is None:
            self._initialize_clients()
        return self._api

    def _get_data_client(self):
        """Get data client, initializing if needed"""
        if not hasattr(self, '_data_client') or self._data_client is None:
            self._initialize_clients()
        return self._data_client

    def _initialize_clients(self):
        """Initialize both trading and data clients"""
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient

            self._api = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper_trading
            )
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            self._initialized = True
            logger.info(f"Alpaca client initialized (paper={self.paper_trading})")
        except ImportError:
            logger.error("alpaca-py package not installed. Run: pip install alpaca-py")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            raise

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized"""
        return self._initialized

    # ============== Account Methods ==============

    async def get_account(self) -> Dict[str, Any]:
        """
        Get account information including equity, cash, buying power.

        Returns:
            dict with account details
        """
        try:
            api = self._get_api()
            account = api.get_account()

            return {
                "id": account.id,
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "currency": account.currency,
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
                "daytrade_count": account.daytrade_count,
                "last_equity": float(account.last_equity) if account.last_equity else None,
            }
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            raise

    async def get_buying_power(self) -> float:
        """Get available buying power"""
        account = await self.get_account()
        return account["buying_power"]

    # ============== Position Methods ==============

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all current open positions.

        Returns:
            List of position dictionaries
        """
        try:
            api = self._get_api()
            positions = api.get_all_positions()

            return [
                {
                    "symbol": pos.symbol,
                    "quantity": float(pos.qty),
                    "entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pnl": float(pos.unrealized_pl),
                    "unrealized_pnl_pct": float(pos.unrealized_plpc) * 100,
                    "side": pos.side.value,
                    "asset_class": pos.asset_class.value,
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific position by symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Position dict or None if no position
        """
        try:
            api = self._get_api()
            pos = api.get_open_position(symbol.upper())

            return {
                "symbol": pos.symbol,
                "quantity": float(pos.qty),
                "entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "unrealized_pnl": float(pos.unrealized_pl),
                "unrealized_pnl_pct": float(pos.unrealized_plpc) * 100,
                "side": pos.side.value,
            }
        except Exception as e:
            if "position does not exist" in str(e).lower():
                return None
            logger.error(f"Failed to get position {symbol}: {e}")
            raise

    # ============== Order Methods ==============

    async def submit_market_order(
        self,
        symbol: str,
        quantity: float,
        side: str,  # "buy" or "sell"
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Submit a market order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: "buy" or "sell"
            time_in_force: "day", "gtc", "ioc", "fok"

        Returns:
            Order details
        """
        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            api = self._get_api()

            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = getattr(TimeInForce, time_in_force.upper(), TimeInForce.DAY)

            order_data = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=quantity,
                side=order_side,
                time_in_force=tif
            )

            order = api.submit_order(order_data)

            logger.info(f"Submitted market order: {side} {quantity} {symbol}")

            return {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "quantity": float(order.qty) if order.qty else quantity,
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
        except Exception as e:
            logger.error(f"Failed to submit market order: {e}")
            raise

    async def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Submit a limit order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: "buy" or "sell"
            limit_price: Limit price
            time_in_force: "day", "gtc", "ioc", "fok"

        Returns:
            Order details
        """
        try:
            from alpaca.trading.requests import LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            api = self._get_api()

            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = getattr(TimeInForce, time_in_force.upper(), TimeInForce.DAY)

            order_data = LimitOrderRequest(
                symbol=symbol.upper(),
                qty=quantity,
                side=order_side,
                limit_price=limit_price,
                time_in_force=tif
            )

            order = api.submit_order(order_data)

            logger.info(f"Submitted limit order: {side} {quantity} {symbol} @ {limit_price}")

            return {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "quantity": float(order.qty) if order.qty else quantity,
                "side": order.side.value,
                "type": order.type.value,
                "limit_price": limit_price,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            }
        except Exception as e:
            logger.error(f"Failed to submit limit order: {e}")
            raise

    async def submit_stop_loss_order(
        self,
        symbol: str,
        quantity: float,
        stop_price: float,
        time_in_force: str = "gtc"
    ) -> Dict[str, Any]:
        """
        Submit a stop-loss order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            stop_price: Stop trigger price
            time_in_force: "day", "gtc"

        Returns:
            Order details
        """
        try:
            from alpaca.trading.requests import StopOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            api = self._get_api()

            order_data = StopOrderRequest(
                symbol=symbol.upper(),
                qty=quantity,
                side=OrderSide.SELL,
                stop_price=stop_price,
                time_in_force=getattr(TimeInForce, time_in_force.upper(), TimeInForce.GTC)
            )

            order = api.submit_order(order_data)

            logger.info(f"Submitted stop-loss order: {symbol} @ {stop_price}")

            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "quantity": float(order.qty) if order.qty else quantity,
                "stop_price": stop_price,
                "status": order.status.value,
            }
        except Exception as e:
            logger.error(f"Failed to submit stop-loss order: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            api = self._get_api()
            api.cancel_order_by_id(order_id)
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        try:
            api = self._get_api()
            order = api.get_order_by_id(order_id)

            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "quantity": float(order.qty) if order.qty else 0,
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            }
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None

    async def get_orders(
        self,
        status: str = "all",
        limit: int = 100,
        after: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get order history.

        Args:
            status: "open", "closed", "all"
            limit: Max number of orders
            after: Only orders after this time

        Returns:
            List of orders
        """
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            api = self._get_api()

            status_map = {
                "open": QueryOrderStatus.OPEN,
                "closed": QueryOrderStatus.CLOSED,
                "all": QueryOrderStatus.ALL,
            }

            request = GetOrdersRequest(
                status=status_map.get(status, QueryOrderStatus.ALL),
                limit=limit,
                after=after
            )

            orders = api.get_orders(request)

            return [
                {
                    "id": str(order.id),
                    "symbol": order.symbol,
                    "quantity": float(order.qty) if order.qty else 0,
                    "side": order.side.value,
                    "type": order.type.value,
                    "status": order.status.value,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                    "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise

    async def close_position(self, symbol: str, quantity: Optional[float] = None) -> Dict[str, Any]:
        """
        Close a position (sell all shares).

        Args:
            symbol: Stock symbol
            quantity: Shares to sell (None = all)

        Returns:
            Order details
        """
        try:
            api = self._get_api()

            if quantity:
                # Partial close via market order
                return await self.submit_market_order(symbol, quantity, "sell")
            else:
                # Close entire position
                order = api.close_position(symbol.upper())

                return {
                    "id": str(order.id),
                    "symbol": order.symbol,
                    "quantity": float(order.qty) if order.qty else 0,
                    "side": order.side.value,
                    "status": order.status.value,
                }
        except Exception as e:
            logger.error(f"Failed to close position {symbol}: {e}")
            raise

    async def close_all_positions(self) -> List[Dict[str, Any]]:
        """Close all open positions"""
        try:
            api = self._get_api()
            orders = api.close_all_positions(cancel_orders=True)

            logger.warning("Closed all positions!")

            return [
                {
                    "id": str(order.id) if hasattr(order, 'id') else None,
                    "symbol": order.symbol if hasattr(order, 'symbol') else None,
                    "status": order.status.value if hasattr(order, 'status') else "unknown",
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            raise

    # ============== Market Data Methods ==============

    async def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Quote with bid/ask/last price
        """
        try:
            from alpaca.data.requests import StockLatestQuoteRequest

            data_client = self._get_data_client()
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol.upper())
            quotes = data_client.get_stock_latest_quote(request)

            quote = quotes[symbol.upper()]

            return {
                "symbol": symbol.upper(),
                "bid_price": float(quote.bid_price),
                "ask_price": float(quote.ask_price),
                "bid_size": quote.bid_size,
                "ask_size": quote.ask_size,
                "timestamp": quote.timestamp.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise

    async def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bar (OHLCV) for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Latest bar data
        """
        try:
            from alpaca.data.requests import StockLatestBarRequest

            data_client = self._get_data_client()
            request = StockLatestBarRequest(symbol_or_symbols=symbol.upper())
            bars = data_client.get_stock_latest_bar(request)

            bar = bars[symbol.upper()]

            return {
                "symbol": symbol.upper(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": bar.volume,
                "timestamp": bar.timestamp.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get bar for {symbol}: {e}")
            raise

    async def get_latest_trade(self, symbol: str) -> Dict[str, Any]:
        """
        Get the most recent trade for a symbol.
        This provides the most current price available.

        Args:
            symbol: Stock symbol

        Returns:
            Latest trade data with price and timestamp
        """
        try:
            from alpaca.data.requests import StockLatestTradeRequest

            data_client = self._get_data_client()
            request = StockLatestTradeRequest(symbol_or_symbols=symbol.upper())
            trades = data_client.get_stock_latest_trade(request)

            trade = trades[symbol.upper()]

            return {
                "symbol": symbol.upper(),
                "price": float(trade.price),
                "size": trade.size,
                "timestamp": trade.timestamp.isoformat(),
                "exchange": trade.exchange,
            }
        except Exception as e:
            logger.error(f"Failed to get latest trade for {symbol}: {e}")
            raise

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars for a symbol.

        Args:
            symbol: Stock symbol
            timeframe: "1Min", "5Min", "15Min", "1Hour", "1Day"
            limit: Number of bars
            start: Start datetime
            end: End datetime

        Returns:
            List of bars
        """
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

            timeframe_map = {
                "1min": TimeFrame.Minute,
                "5min": TimeFrame(5, TimeFrameUnit.Minute),
                "15min": TimeFrame(15, TimeFrameUnit.Minute),
                "1hour": TimeFrame.Hour,
                "1day": TimeFrame.Day,
            }

            tf = timeframe_map.get(timeframe.lower(), TimeFrame.Day)

            # Calculate start date based on timeframe
            # For daily bars, go back 'limit' days (plus buffer for weekends/holidays)
            # For intraday, go back 7 days
            is_daily = timeframe.lower() == "1day"
            if not start:
                if is_daily:
                    # Add 50% buffer for weekends and holidays
                    days_back = int(limit * 1.5)
                    start = datetime.now() - timedelta(days=days_back)
                    logger.info(f"[STOCK BARS] Daily bars: going back {days_back} days for {limit} bars")
                else:
                    start = datetime.now() - timedelta(days=7)

            data_client = self._get_data_client()

            # IMPORTANT: When start is provided, do NOT pass limit to Alpaca
            # Alpaca returns FIRST N bars from start date, not the MOST RECENT N
            # We'll fetch all bars from start to now, then take the last N on our side
            request = StockBarsRequest(
                symbol_or_symbols=symbol.upper(),
                timeframe=tf,
                start=start,
                end=end,
                # Don't pass limit - we'll slice the results ourselves
            )

            logger.info(f"[STOCK BARS] Fetching for {symbol}: tf={tf}, start={start}, end={end}")
            bars = data_client.get_stock_bars(request)

            # BarSet is dict-like but access via .data attribute or directly with symbol key
            sym = symbol.upper()

            # Try to access data - BarSet may return data differently
            bar_data = None
            try:
                # Method 1: Direct dict-like access
                if sym in bars:
                    bar_data = bars[sym]
                # Method 2: Try .data attribute if it exists
                elif hasattr(bars, 'data') and sym in bars.data:
                    bar_data = bars.data[sym]
                # Method 3: The BarSet might have the data directly
                elif hasattr(bars, sym):
                    bar_data = getattr(bars, sym)
            except Exception as access_err:
                logger.warning(f"[STOCK BARS] Error accessing bar data for {sym}: {access_err}")

            if bar_data is None:
                logger.warning(f"[STOCK BARS] No data found for {symbol}")
                return []

            result = [
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": bar.volume,
                }
                for bar in bar_data
            ]

            # Take only the LAST N bars if limit was specified
            # This ensures we get the MOST RECENT data, not the oldest
            total_bars = len(result)
            if limit and total_bars > limit:
                result = result[-limit:]
                logger.info(f"[STOCK BARS] Got {total_bars} bars, returning last {limit} for {symbol}")
            else:
                logger.info(f"[STOCK BARS] Got {len(result)} bars for {symbol}")

            return result
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            raise

    # ============== Market Status ==============

    async def is_market_open(self) -> bool:
        """Check if the market is currently open"""
        try:
            api = self._get_api()
            clock = api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return False

    async def get_market_clock(self) -> Dict[str, Any]:
        """Get market clock info"""
        try:
            api = self._get_api()
            clock = api.get_clock()

            return {
                "is_open": clock.is_open,
                "next_open": clock.next_open.isoformat() if clock.next_open else None,
                "next_close": clock.next_close.isoformat() if clock.next_close else None,
                "timestamp": clock.timestamp.isoformat() if clock.timestamp else None,
            }
        except Exception as e:
            logger.error(f"Failed to get market clock: {e}")
            raise

    async def get_market_hours_info(self) -> Dict[str, Any]:
        """
        Get detailed market hours information including extended hours.

        Market Hours (Eastern Time):
        - Pre-market: 4:00 AM - 9:30 AM
        - Regular: 9:30 AM - 4:00 PM
        - After-hours: 4:00 PM - 8:00 PM

        Returns:
            Dict with current session info and tradability
        """
        try:
            from datetime import timezone
            import pytz

            api = self._get_api()
            clock = api.get_clock()

            # Get current time in Eastern
            eastern = pytz.timezone('US/Eastern')
            now_eastern = datetime.now(eastern)
            current_hour = now_eastern.hour
            current_minute = now_eastern.minute
            current_time_minutes = current_hour * 60 + current_minute

            # Define market sessions in minutes from midnight
            PRE_MARKET_START = 4 * 60      # 4:00 AM
            REGULAR_START = 9 * 60 + 30    # 9:30 AM
            REGULAR_END = 16 * 60          # 4:00 PM
            AFTER_HOURS_END = 20 * 60      # 8:00 PM

            # Determine current session
            is_weekday = now_eastern.weekday() < 5

            if not is_weekday:
                session = "weekend"
                can_trade = False
            elif current_time_minutes < PRE_MARKET_START:
                session = "overnight"
                can_trade = False
            elif current_time_minutes < REGULAR_START:
                session = "pre_market"
                can_trade = True  # Can trade with extended hours orders
            elif current_time_minutes < REGULAR_END:
                session = "regular"
                can_trade = True
            elif current_time_minutes < AFTER_HOURS_END:
                session = "after_hours"
                can_trade = True  # Can trade with extended hours orders
            else:
                session = "overnight"
                can_trade = False

            return {
                "is_open": clock.is_open,
                "session": session,
                "can_trade": can_trade,
                "can_trade_extended": session in ["pre_market", "after_hours"],
                "current_time_eastern": now_eastern.strftime("%H:%M:%S"),
                "next_open": clock.next_open.isoformat() if clock.next_open else None,
                "next_close": clock.next_close.isoformat() if clock.next_close else None,
                "market_hours": {
                    "pre_market": "4:00 AM - 9:30 AM ET",
                    "regular": "9:30 AM - 4:00 PM ET",
                    "after_hours": "4:00 PM - 8:00 PM ET",
                },
            }
        except Exception as e:
            logger.error(f"Failed to get market hours: {e}")
            # Fallback to basic check
            return {
                "is_open": await self.is_market_open(),
                "session": "unknown",
                "can_trade": await self.is_market_open(),
                "can_trade_extended": False,
            }

    async def submit_extended_hours_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        limit_price: float,
    ) -> Dict[str, Any]:
        """
        Submit an order that can execute during extended hours.
        Extended hours orders MUST be limit orders.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: "buy" or "sell"
            limit_price: Limit price (required for extended hours)

        Returns:
            Order details
        """
        try:
            from alpaca.trading.requests import LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            api = self._get_api()

            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            order_data = LimitOrderRequest(
                symbol=symbol.upper(),
                qty=quantity,
                side=order_side,
                limit_price=limit_price,
                time_in_force=TimeInForce.DAY,
                extended_hours=True  # Enable extended hours trading
            )

            order = api.submit_order(order_data)

            logger.info(f"Submitted extended hours order: {side} {quantity} {symbol} @ {limit_price}")

            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "quantity": float(order.qty) if order.qty else quantity,
                "side": order.side.value,
                "type": "limit",
                "limit_price": limit_price,
                "extended_hours": True,
                "status": order.status.value,
            }
        except Exception as e:
            logger.error(f"Failed to submit extended hours order: {e}")
            raise

    async def search_assets(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Search for tradable assets by symbol or name.
        Uses Alpaca's asset API which has NO rate limit!

        Args:
            query: Search query (symbol or partial name)
            limit: Maximum results to return

        Returns:
            List of matching assets with symbol, name, and type
        """
        try:
            from alpaca.trading.enums import AssetClass, AssetStatus
            from alpaca.trading.requests import GetAssetsRequest

            api = self._get_api()
            query_upper = query.upper()

            # Get all active tradable assets
            request = GetAssetsRequest(status=AssetStatus.ACTIVE)
            assets = api.get_all_assets(request)

            results = []
            for asset in assets:
                # Skip non-tradable assets
                if not asset.tradable:
                    continue

                # Match by symbol (exact or starts with) or name (contains)
                symbol_match = asset.symbol.upper().startswith(query_upper) or query_upper == asset.symbol.upper()
                name_match = asset.name and query_upper in asset.name.upper()

                if symbol_match or name_match:
                    asset_type = "stock" if asset.asset_class == AssetClass.US_EQUITY else "crypto"
                    # Convert exchange enum to string properly
                    exchange_str = str(asset.exchange.value) if hasattr(asset.exchange, 'value') else str(asset.exchange)
                    region = "United States" if exchange_str in ["NYSE", "NASDAQ", "AMEX"] else exchange_str
                    results.append({
                        "symbol": asset.symbol,
                        "name": asset.name or asset.symbol,
                        "type": asset_type,
                        "region": region,
                    })

                if len(results) >= limit:
                    break

            # Sort: exact matches first, then starts-with, then contains
            def sort_key(item):
                sym = item["symbol"].upper()
                if sym == query_upper:
                    return (0, sym)
                elif sym.startswith(query_upper):
                    return (1, sym)
                else:
                    return (2, sym)

            results.sort(key=sort_key)

            logger.info(f"Alpaca search for '{query}' found {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"Alpaca asset search failed: {e}")
            return []


# Singleton instances for paper and live trading
_alpaca_paper_service: Optional[AlpacaService] = None
_alpaca_live_service: Optional[AlpacaService] = None
_current_trading_mode: bool = True  # True = paper, False = live


def get_alpaca_service(paper_trading: bool = None) -> AlpacaService:
    """
    Get Alpaca service for the specified trading mode.

    If paper_trading is None, uses the current global trading mode.
    Paper and live services are maintained separately as singletons.
    """
    global _alpaca_paper_service, _alpaca_live_service, _current_trading_mode

    # Use current mode if not specified
    if paper_trading is None:
        paper_trading = _current_trading_mode

    if paper_trading:
        if _alpaca_paper_service is None:
            _alpaca_paper_service = AlpacaService(paper_trading=True)
            logger.info("Created Alpaca PAPER trading service")
        return _alpaca_paper_service
    else:
        if _alpaca_live_service is None:
            _alpaca_live_service = AlpacaService(paper_trading=False)
            logger.info("Created Alpaca LIVE trading service")
        return _alpaca_live_service


def set_trading_mode(paper_trading: bool) -> None:
    """Set the global trading mode (paper or live)"""
    global _current_trading_mode
    old_mode = "paper" if _current_trading_mode else "live"
    new_mode = "paper" if paper_trading else "live"
    _current_trading_mode = paper_trading
    logger.info(f"Trading mode changed from {old_mode} to {new_mode}")


def get_trading_mode() -> bool:
    """Get current trading mode. Returns True for paper, False for live."""
    return _current_trading_mode
