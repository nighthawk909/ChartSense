"""
Mock Alpha Vantage Service
==========================
Provides mock implementations of Alpha Vantage API for testing.

This module provides:
- MockAlphaVantageService: Full mock of AlphaVantageService class
- Factory functions for creating mock API responses
- Configurable responses for different test scenarios

Usage:
    from tests.mocks.alpha_vantage_mock import MockAlphaVantageService

    service = MockAlphaVantageService()
    quote = await service.get_quote("AAPL")
    history = await service.get_history("AAPL", interval=TimeInterval.DAILY)
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add parent to path for model imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from models.stock import StockQuote, StockHistory, PriceData, TimeInterval
except ImportError:
    # Fallback definitions if models aren't available
    from enum import Enum

    class TimeInterval(str, Enum):
        MINUTE_1 = "1min"
        MINUTE_5 = "5min"
        MINUTE_15 = "15min"
        MINUTE_30 = "30min"
        MINUTE_60 = "60min"
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"


def create_mock_quote_response(
    symbol: str,
    price: float = 150.0,
    change: float = 2.50,
    change_percent: float = 1.69,
    volume: int = 50000000,
    previous_close: float = 147.50,
    open_price: float = 148.00,
    high_price: float = 151.00,
    low_price: float = 147.00,
) -> Dict[str, Any]:
    """
    Create a mock Alpha Vantage Global Quote response.

    Args:
        symbol: Stock symbol
        price: Current price
        change: Price change
        change_percent: Percentage change
        volume: Trading volume
        previous_close: Previous close price
        open_price: Open price
        high_price: High price
        low_price: Low price

    Returns:
        Dictionary matching Alpha Vantage Global Quote format
    """
    return {
        "Global Quote": {
            "01. symbol": symbol.upper(),
            "02. open": str(open_price),
            "03. high": str(high_price),
            "04. low": str(low_price),
            "05. price": str(price),
            "06. volume": str(volume),
            "07. latest trading day": datetime.now().strftime("%Y-%m-%d"),
            "08. previous close": str(previous_close),
            "09. change": str(change),
            "10. change percent": f"{change_percent}%",
        }
    }


def create_mock_history_response(
    symbol: str,
    interval: str = "daily",
    days: int = 100,
    start_price: float = 100.0,
    trend: float = 0.001,
    volatility: float = 0.02,
) -> Dict[str, Any]:
    """
    Create a mock Alpha Vantage time series response.

    Args:
        symbol: Stock symbol
        interval: Time interval (daily, weekly, monthly, 1min, 5min, etc.)
        days: Number of data points
        start_price: Starting price
        trend: Daily trend (positive = uptrend, negative = downtrend)
        volatility: Price volatility

    Returns:
        Dictionary matching Alpha Vantage time series format
    """
    import random

    # Determine the time series key based on interval
    if interval == "daily":
        time_key = "Time Series (Daily)"
        function = "TIME_SERIES_DAILY"
    elif interval == "weekly":
        time_key = "Weekly Time Series"
        function = "TIME_SERIES_WEEKLY"
    elif interval == "monthly":
        time_key = "Monthly Time Series"
        function = "TIME_SERIES_MONTHLY"
    else:
        time_key = f"Time Series ({interval})"
        function = "TIME_SERIES_INTRADAY"

    # Generate price data
    time_series = {}
    price = start_price

    for i in range(days):
        if interval in ["daily", "weekly", "monthly"]:
            date = (datetime.now() - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        else:
            # For intraday, use datetime format
            date = (datetime.now() - timedelta(minutes=(days - i - 1) * 5)).strftime("%Y-%m-%d %H:%M:%S")

        # Generate OHLC
        daily_return = trend + random.gauss(0, volatility)
        open_price = price
        close_price = price * (1 + daily_return)

        # Generate high/low
        range_mult = abs(random.gauss(0, volatility))
        if close_price > open_price:
            high_price = close_price * (1 + range_mult)
            low_price = open_price * (1 - range_mult * 0.5)
        else:
            high_price = open_price * (1 + range_mult * 0.5)
            low_price = close_price * (1 - range_mult)

        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        volume = int(random.gauss(10000000, 3000000))
        volume = max(volume, 1000000)

        time_series[date] = {
            "1. open": str(round(open_price, 4)),
            "2. high": str(round(high_price, 4)),
            "3. low": str(round(low_price, 4)),
            "4. close": str(round(close_price, 4)),
            "5. volume": str(volume),
        }

        price = close_price

    return {
        "Meta Data": {
            "1. Information": f"Mock {interval.title()} Prices",
            "2. Symbol": symbol.upper(),
            "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4. Output Size": "Compact",
            "5. Time Zone": "US/Eastern",
        },
        time_key: time_series,
    }


def create_mock_search_response(
    query: str,
    results: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Create a mock Alpha Vantage symbol search response.

    Args:
        query: Search query
        results: Optional list of result dictionaries

    Returns:
        Dictionary matching Alpha Vantage search format
    """
    if results is None:
        # Default mock results
        results = [
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "Equity", "region": "United States"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "Equity", "region": "United States"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "Equity", "region": "United States"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "Equity", "region": "United States"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Equity", "region": "United States"},
        ]

    # Filter by query
    query_upper = query.upper()
    filtered = [
        r for r in results
        if query_upper in r["symbol"] or query_upper in r["name"].upper()
    ]

    return {
        "bestMatches": [
            {
                "1. symbol": r["symbol"],
                "2. name": r["name"],
                "3. type": r.get("type", "Equity"),
                "4. region": r.get("region", "United States"),
                "5. marketOpen": "09:30",
                "6. marketClose": "16:00",
                "7. timezone": "UTC-04",
                "8. currency": "USD",
                "9. matchScore": "1.0000",
            }
            for r in filtered
        ]
    }


def create_mock_company_overview(
    symbol: str,
    name: str = "Test Company Inc.",
    sector: str = "Technology",
    industry: str = "Software",
    market_cap: str = "1000000000000",
    pe_ratio: str = "25.50",
    eps: str = "5.00",
    dividend_yield: str = "0.50",
    week_52_high: str = "180.00",
    week_52_low: str = "120.00",
    day_50_ma: str = "155.00",
    day_200_ma: str = "145.00",
    beta: str = "1.20",
    profit_margin: str = "0.25",
    revenue_growth: str = "0.15",
) -> Dict[str, Any]:
    """
    Create a mock Alpha Vantage company overview response.

    Args:
        symbol: Stock symbol
        name: Company name
        sector: Business sector
        industry: Industry
        market_cap: Market capitalization
        pe_ratio: P/E ratio
        eps: Earnings per share
        dividend_yield: Dividend yield
        week_52_high: 52-week high
        week_52_low: 52-week low
        day_50_ma: 50-day moving average
        day_200_ma: 200-day moving average
        beta: Stock beta
        profit_margin: Profit margin
        revenue_growth: Quarterly revenue growth YoY

    Returns:
        Dictionary matching Alpha Vantage company overview format
    """
    return {
        "Symbol": symbol.upper(),
        "Name": name,
        "Description": f"{name} is a mock company for testing purposes.",
        "Sector": sector,
        "Industry": industry,
        "MarketCapitalization": market_cap,
        "PERatio": pe_ratio,
        "EPS": eps,
        "DividendYield": dividend_yield,
        "52WeekHigh": week_52_high,
        "52WeekLow": week_52_low,
        "50DayMovingAverage": day_50_ma,
        "200DayMovingAverage": day_200_ma,
        "Beta": beta,
        "ProfitMargin": profit_margin,
        "QuarterlyRevenueGrowthYOY": revenue_growth,
        "Address": "123 Test Street",
        "Country": "USA",
        "Currency": "USD",
        "Exchange": "NASDAQ",
    }


def create_mock_indicator_response(
    symbol: str,
    indicator: str,
    values: Optional[List[float]] = None,
    days: int = 100,
) -> Dict[str, Any]:
    """
    Create a mock Alpha Vantage technical indicator response.

    Args:
        symbol: Stock symbol
        indicator: Indicator name (RSI, MACD, etc.)
        values: Optional list of indicator values
        days: Number of data points

    Returns:
        Dictionary matching Alpha Vantage indicator format
    """
    import random

    indicator_upper = indicator.upper()

    # Generate mock values if not provided
    if values is None:
        if indicator_upper == "RSI":
            values = [random.gauss(50, 15) for _ in range(days)]
            values = [max(0, min(100, v)) for v in values]
        elif indicator_upper == "MACD":
            values = [random.gauss(0, 2) for _ in range(days)]
        else:
            values = [random.gauss(0, 1) for _ in range(days)]

    # Build time series
    time_series = {}
    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        time_series[date] = {indicator_upper: str(round(values[i], 4))}

    return {
        "Meta Data": {
            "1: Symbol": symbol.upper(),
            "2: Indicator": indicator_upper,
            "3: Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
            "4: Interval": "daily",
            "5: Time Period": "14",
            "6: Series Type": "close",
            "7: Time Zone": "US/Eastern",
        },
        f"Technical Analysis: {indicator_upper}": time_series,
    }


class MockAlphaVantageService:
    """
    Mock implementation of AlphaVantageService for testing.

    Provides configurable responses for:
    - Stock quotes
    - Historical price data
    - Symbol search
    - Company overview
    - Technical indicators

    Example:
        service = MockAlphaVantageService()
        quote = await service.get_quote("AAPL")
        history = await service.get_history("AAPL")
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        """Initialize mock service"""
        self.api_key = "mock_api_key"
        self._cache: Dict[str, Any] = {}

        # Configurable mock data
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._histories: Dict[str, Dict[str, Any]] = {}
        self._overviews: Dict[str, Dict[str, Any]] = {}

        # Track method calls for assertions
        self.call_history: List[Dict[str, Any]] = []

        # Error simulation
        self._simulate_rate_limit = False
        self._simulate_error: Optional[str] = None

    # ============================================================
    # Configuration Methods
    # ============================================================

    def set_quote(self, symbol: str, **kwargs) -> None:
        """Set custom quote data for a symbol"""
        self._quotes[symbol.upper()] = create_mock_quote_response(symbol, **kwargs)

    def set_history(self, symbol: str, interval: str = "daily", **kwargs) -> None:
        """Set custom history data for a symbol"""
        key = f"{symbol.upper()}_{interval}"
        self._histories[key] = create_mock_history_response(symbol, interval, **kwargs)

    def set_overview(self, symbol: str, **kwargs) -> None:
        """Set custom company overview for a symbol"""
        self._overviews[symbol.upper()] = create_mock_company_overview(symbol, **kwargs)

    def simulate_rate_limit(self, enabled: bool = True) -> None:
        """Enable/disable rate limit simulation"""
        self._simulate_rate_limit = enabled

    def simulate_error(self, error_message: Optional[str]) -> None:
        """Set an error to be raised on next request"""
        self._simulate_error = error_message

    def _record_call(self, method: str, **kwargs) -> None:
        """Record method call for testing"""
        self.call_history.append({
            "method": method,
            "args": kwargs,
            "timestamp": datetime.now().isoformat(),
        })

    def _check_errors(self) -> None:
        """Check if errors should be raised"""
        if self._simulate_rate_limit:
            raise Exception("API rate limit reached. Please wait and try again.")
        if self._simulate_error:
            raise Exception(self._simulate_error)

    # ============================================================
    # API Methods
    # ============================================================

    async def _make_request(self, params: Dict[str, str]) -> Optional[Dict]:
        """Mock request method"""
        self._check_errors()
        # Return cached or generated data based on params
        return params  # Placeholder

    async def get_quote(self, symbol: str):
        """Get mock quote for a symbol"""
        self._record_call("get_quote", symbol=symbol)
        self._check_errors()

        symbol_upper = symbol.upper()

        # Use custom quote if set, otherwise generate
        if symbol_upper in self._quotes:
            data = self._quotes[symbol_upper]
        else:
            data = create_mock_quote_response(symbol)

        quote_data = data["Global Quote"]

        # Return a StockQuote-like object (or dict)
        try:
            from models.stock import StockQuote
            return StockQuote(
                symbol=quote_data["01. symbol"],
                price=float(quote_data["05. price"]),
                change=float(quote_data["09. change"]),
                change_percent=float(quote_data["10. change percent"].rstrip("%")),
                volume=int(quote_data["06. volume"]),
                latest_trading_day=quote_data["07. latest trading day"],
                previous_close=float(quote_data["08. previous close"]),
                open=float(quote_data["02. open"]),
                high=float(quote_data["03. high"]),
                low=float(quote_data["04. low"]),
            )
        except ImportError:
            # Return dict if model not available
            return {
                "symbol": quote_data["01. symbol"],
                "price": float(quote_data["05. price"]),
                "change": float(quote_data["09. change"]),
                "change_percent": float(quote_data["10. change percent"].rstrip("%")),
                "volume": int(quote_data["06. volume"]),
                "latest_trading_day": quote_data["07. latest trading day"],
                "previous_close": float(quote_data["08. previous close"]),
                "open": float(quote_data["02. open"]),
                "high": float(quote_data["03. high"]),
                "low": float(quote_data["04. low"]),
            }

    async def get_history(
        self,
        symbol: str,
        interval: str = "daily",
        outputsize: str = "compact",
    ):
        """Get mock historical data for a symbol"""
        self._record_call("get_history", symbol=symbol, interval=interval)
        self._check_errors()

        symbol_upper = symbol.upper()
        key = f"{symbol_upper}_{interval}"

        # Use custom history if set, otherwise generate
        if key in self._histories:
            data = self._histories[key]
        else:
            data = create_mock_history_response(symbol, interval)

        # Determine time series key
        if interval == "daily":
            time_key = "Time Series (Daily)"
        elif interval == "weekly":
            time_key = "Weekly Time Series"
        elif interval == "monthly":
            time_key = "Monthly Time Series"
        else:
            time_key = f"Time Series ({interval})"

        time_series = data.get(time_key, {})

        # Convert to model format
        try:
            from models.stock import StockHistory, PriceData

            price_data = []
            prices = []

            for date_str, values in sorted(time_series.items()):
                price_data.append(PriceData(
                    date=date_str,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(values["5. volume"]),
                ))
                prices.append(float(values["4. close"]))

            return StockHistory(
                symbol=symbol_upper,
                interval=interval,
                data=price_data,
                prices=prices,
            )
        except ImportError:
            # Return dict if model not available
            price_data = []
            prices = []

            for date_str, values in sorted(time_series.items()):
                price_data.append({
                    "date": date_str,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"]),
                })
                prices.append(float(values["4. close"]))

            return {
                "symbol": symbol_upper,
                "interval": interval,
                "data": price_data,
                "prices": prices,
            }

    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for stock symbols"""
        self._record_call("search_symbols", query=query)
        self._check_errors()

        data = create_mock_search_response(query)

        return [
            {
                "symbol": match["1. symbol"],
                "name": match["2. name"],
                "type": match["3. type"],
                "region": match["4. region"],
            }
            for match in data["bestMatches"]
        ]

    async def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company fundamentals"""
        self._record_call("get_company_overview", symbol=symbol)
        self._check_errors()

        symbol_upper = symbol.upper()

        if symbol_upper in self._overviews:
            data = self._overviews[symbol_upper]
        else:
            data = create_mock_company_overview(symbol)

        return {
            "symbol": data.get("Symbol"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_cap": data.get("MarketCapitalization"),
            "pe_ratio": data.get("PERatio"),
            "eps": data.get("EPS"),
            "dividend_yield": data.get("DividendYield"),
            "52_week_high": data.get("52WeekHigh"),
            "52_week_low": data.get("52WeekLow"),
            "50_day_ma": data.get("50DayMovingAverage"),
            "200_day_ma": data.get("200DayMovingAverage"),
            "beta": data.get("Beta"),
            "profit_margin": data.get("ProfitMargin"),
            "revenue_growth": data.get("QuarterlyRevenueGrowthYOY"),
        }

    async def get_indicator(
        self,
        symbol: str,
        indicator: str,
        interval: str = "daily",
        time_period: int = 14,
        series_type: str = "close",
    ) -> Optional[Dict[str, Any]]:
        """Get technical indicator from Alpha Vantage"""
        self._record_call(
            "get_indicator",
            symbol=symbol,
            indicator=indicator,
            interval=interval,
            time_period=time_period,
        )
        self._check_errors()

        return create_mock_indicator_response(symbol, indicator)
