"""
Alpha Vantage API Service
Handles all interactions with the Alpha Vantage API
"""
import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
from models.stock import StockQuote, StockHistory, PriceData, TimeInterval

# Cache for API responses (simple in-memory cache)
_cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_DURATION = timedelta(minutes=5)


class AlphaVantageService:
    """Service for interacting with Alpha Vantage API"""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached response if still valid"""
        if key in _cache:
            data, timestamp = _cache[key]
            if datetime.now() - timestamp < CACHE_DURATION:
                return data
            del _cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        """Cache a response"""
        _cache[key] = (data, datetime.now())

    async def _make_request(self, params: Dict[str, str]) -> Optional[Dict]:
        """Make a request to Alpha Vantage API"""
        params["apikey"] = self.api_key

        # Check cache
        cache_key = str(sorted(params.items()))
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "Error Message" in data:
                raise Exception(data["Error Message"])
            if "Note" in data:
                # Rate limit warning
                raise Exception("API rate limit reached. Please wait and try again.")

            # Cache successful response
            self._set_cache(cache_key, data)
            return data

    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get real-time quote for a symbol"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }

        data = await self._make_request(params)
        if not data or "Global Quote" not in data:
            return None

        quote = data["Global Quote"]
        if not quote:
            return None

        return StockQuote(
            symbol=quote.get("01. symbol", symbol),
            price=float(quote.get("05. price", 0)),
            change=float(quote.get("09. change", 0)),
            change_percent=float(quote.get("10. change percent", "0%").rstrip("%")),
            volume=int(quote.get("06. volume", 0)),
            latest_trading_day=quote.get("07. latest trading day", ""),
            previous_close=float(quote.get("08. previous close", 0)),
            open=float(quote.get("02. open", 0)),
            high=float(quote.get("03. high", 0)),
            low=float(quote.get("04. low", 0)),
        )

    async def get_history(
        self,
        symbol: str,
        interval: TimeInterval = TimeInterval.DAILY,
        outputsize: str = "compact",
    ) -> Optional[StockHistory]:
        """Get historical price data"""
        if interval == TimeInterval.DAILY:
            function = "TIME_SERIES_DAILY"
            time_key = "Time Series (Daily)"
        elif interval == TimeInterval.WEEKLY:
            function = "TIME_SERIES_WEEKLY"
            time_key = "Weekly Time Series"
        elif interval == TimeInterval.MONTHLY:
            function = "TIME_SERIES_MONTHLY"
            time_key = "Monthly Time Series"
        else:
            # Intraday
            function = "TIME_SERIES_INTRADAY"
            time_key = f"Time Series ({interval.value})"

        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": outputsize,
        }

        if interval in [TimeInterval.MINUTE_1, TimeInterval.MINUTE_5,
                        TimeInterval.MINUTE_15, TimeInterval.MINUTE_30,
                        TimeInterval.MINUTE_60]:
            params["interval"] = interval.value

        data = await self._make_request(params)
        if not data or time_key not in data:
            return None

        time_series = data[time_key]
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
            symbol=symbol,
            interval=interval.value,
            data=price_data,
            prices=prices,  # Just close prices for indicator calculations
        )

    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for stock symbols"""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query,
        }

        data = await self._make_request(params)
        if not data or "bestMatches" not in data:
            return []

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
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
        }

        data = await self._make_request(params)
        if not data or "Symbol" not in data:
            return None

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
        """Get technical indicator directly from Alpha Vantage"""
        params = {
            "function": indicator.upper(),
            "symbol": symbol,
            "interval": interval,
            "time_period": str(time_period),
            "series_type": series_type,
        }

        data = await self._make_request(params)
        return data
