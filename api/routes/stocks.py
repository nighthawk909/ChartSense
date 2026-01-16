"""
Stock data routes - fetches data from Alpaca (primary) and Alpha Vantage (fallback)

Alpaca provides unlimited real-time quotes and historical data.
Alpha Vantage is used for company overview and symbol search (25 calls/day limit).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
import logging

from services.alpha_vantage import AlphaVantageService
from services.alpaca_service import get_alpaca_service
from models.stock import StockQuote, StockHistory, TimeInterval

router = APIRouter()
av_service = AlphaVantageService()
logger = logging.getLogger(__name__)


@router.get("/quote/{symbol}", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    """
    Get real-time quote for a stock symbol.
    Uses Alpaca (unlimited) as primary source.
    """
    symbol_upper = symbol.upper()
    logger.info(f"[QUOTE] Fetching quote for {symbol_upper}")

    try:
        alpaca = get_alpaca_service()
        logger.debug(f"[QUOTE] Alpaca service initialized, fetching latest bar for {symbol_upper}")

        # Get latest bar from Alpaca (includes OHLCV)
        bar = await alpaca.get_latest_bar(symbol_upper)
        logger.debug(f"[QUOTE] Got bar for {symbol_upper}: {bar}")

        if not bar:
            logger.warning(f"[QUOTE] No bar data returned for {symbol_upper}")
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        # Get previous close to calculate change
        prev_close = bar["close"]  # Default to current if we can't get previous
        latest_trading_day = bar["timestamp"].split("T")[0] if "T" in bar["timestamp"] else bar["timestamp"]

        try:
            logger.debug(f"[QUOTE] Fetching 2-day bars for {symbol_upper} to calculate change")
            bars = await alpaca.get_bars(symbol_upper, timeframe="1Day", limit=2)
            logger.debug(f"[QUOTE] Got {len(bars)} bars for {symbol_upper}")
            if len(bars) >= 2:
                prev_close = bars[-2]["close"]
                current_price = bar["close"]
                change = current_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0
                logger.debug(f"[QUOTE] {symbol_upper}: prev_close=${prev_close:.2f}, current=${current_price:.2f}, change={change_percent:.2f}%")
            else:
                change = 0
                change_percent = 0
                logger.debug(f"[QUOTE] {symbol_upper}: Not enough bars for change calculation")
        except Exception as bar_err:
            logger.warning(f"[QUOTE] Error fetching bars for {symbol_upper}: {bar_err}")
            change = 0
            change_percent = 0

        quote = StockQuote(
            symbol=symbol_upper,
            price=bar["close"],
            open=bar["open"],
            high=bar["high"],
            low=bar["low"],
            volume=bar["volume"],
            change=change,
            change_percent=change_percent,
            latest_trading_day=latest_trading_day,
            previous_close=prev_close,
        )
        logger.info(f"[QUOTE] Successfully returned quote for {symbol_upper}: ${bar['close']:.2f}")
        return quote

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUOTE] Alpaca quote failed for {symbol}: {e}", exc_info=True)
        # Fallback to Alpha Vantage
        try:
            quote = await av_service.get_quote(symbol.upper())
            if quote:
                return quote
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_stock_history(
    symbol: str,
    interval: TimeInterval = Query(default=TimeInterval.DAILY),
    outputsize: str = Query(default="compact", pattern="^(compact|full)$"),
):
    """
    Get historical price data for a stock.
    Uses Alpaca (unlimited) as primary source.
    """
    symbol_upper = symbol.upper()
    logger.info(f"[HISTORY] Fetching history for {symbol_upper}, interval={interval.value}, outputsize={outputsize}")

    try:
        alpaca = get_alpaca_service()

        # Map interval to Alpaca timeframe
        timeframe_map = {
            TimeInterval.MINUTE_1: "1min",
            TimeInterval.MINUTE_5: "5min",
            TimeInterval.MINUTE_15: "15min",
            TimeInterval.MINUTE_30: "15min",  # Alpaca doesn't have 30min, use 15
            TimeInterval.MINUTE_60: "1hour",
            TimeInterval.DAILY: "1day",
            TimeInterval.WEEKLY: "1day",  # Use daily for weekly (aggregate client-side)
            TimeInterval.MONTHLY: "1day",  # Use daily for monthly (aggregate client-side)
        }

        timeframe = timeframe_map.get(interval, "1day")
        limit = 500 if outputsize == "full" else 100

        # Calculate start date based on timeframe
        # Use UTC time for consistency with Alpaca API
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)

        if timeframe == "1day":
            start = now_utc - timedelta(days=limit)
        elif timeframe == "1hour":
            start = now_utc - timedelta(days=30)
        elif timeframe == "5min":
            # For 5-minute data, go back 3 days max to get fresh data
            start = now_utc - timedelta(days=3)
        elif timeframe == "1min":
            # For 1-minute data, go back 1 day to ensure fresh data
            start = now_utc - timedelta(days=1)
        else:
            start = now_utc - timedelta(days=7)

        logger.debug(f"[HISTORY] Fetching {limit} {timeframe} bars for {symbol_upper} from {start}")

        bars = await alpaca.get_bars(
            symbol_upper,
            timeframe=timeframe,
            limit=limit,
            start=start
        )

        if not bars:
            logger.warning(f"[HISTORY] No bars returned for {symbol_upper}")
            raise HTTPException(status_code=404, detail=f"No history found for {symbol}")

        logger.info(f"[HISTORY] Got {len(bars)} bars for {symbol_upper}")

        # Transform to format expected by frontend StockChart component
        # Frontend expects: { history: [{ date, open, high, low, close, volume }, ...] }
        # For intraday intervals, keep full timestamp; for daily+, use just date
        is_intraday = timeframe in ["1min", "5min", "15min", "1hour"]
        logger.info(f"[HISTORY] timeframe={timeframe}, is_intraday={is_intraday}")
        if bars:
            logger.info(f"[HISTORY] Sample timestamp from Alpaca: {bars[0].get('timestamp', 'N/A')}")

        history = [
            {
                # For intraday: keep full ISO timestamp for unique candles
                # For daily+: just date (YYYY-MM-DD)
                "date": bar["timestamp"] if is_intraday else (bar["timestamp"].split("T")[0] if "T" in bar["timestamp"] else bar["timestamp"]),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
            }
            for bar in bars
        ]

        return {
            "symbol": symbol.upper(),
            "interval": interval.value,
            "history": history,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HISTORY] Alpaca history failed for {symbol}: {e}", exc_info=True)
        # Fallback to Alpha Vantage
        logger.info(f"[HISTORY] Attempting Alpha Vantage fallback for {symbol}")
        try:
            history = await av_service.get_history(
                symbol.upper(),
                interval=interval,
                outputsize=outputsize
            )
            if history:
                return history
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_symbols(query: str = Query(min_length=1)):
    """
    Search for stock symbols by keyword.
    Uses Alpaca (unlimited) as primary, Alpha Vantage as fallback.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Searching for: {query}")

        # Primary: Use Alpaca (unlimited API calls)
        alpaca = get_alpaca_service()
        results = await alpaca.search_assets(query, limit=20)

        if results:
            logger.info(f"Alpaca search found {len(results)} results")
            return {"results": results}

        # Fallback: Alpha Vantage (limited to 25/day)
        logger.info("Alpaca returned no results, trying Alpha Vantage")
        results = await av_service.search_symbols(query)
        logger.info(f"Alpha Vantage search found {len(results)} results")
        return {"results": results}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview/{symbol}")
async def get_company_overview(symbol: str):
    """
    Get company fundamentals and overview.
    Uses Alpha Vantage (limited to 25 calls/day on free tier).
    """
    try:
        overview = await av_service.get_company_overview(symbol.upper())
        if not overview:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/{symbol}")
async def get_realtime_quote(symbol: str):
    """
    Get real-time (latest) quote with forced fresh data.
    Bypasses any caching and fetches directly from Alpaca.
    """
    symbol_upper = symbol.upper()
    logger.info(f"[REALTIME] Force-fetching fresh data for {symbol_upper}")

    try:
        alpaca = get_alpaca_service()

        # Get the absolute latest bar
        bar = await alpaca.get_latest_bar(symbol_upper)

        if not bar:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        # Also get latest trade for more precision
        try:
            latest_trade = await alpaca.get_latest_trade(symbol_upper)
        except:
            latest_trade = None

        # Get 2-day bars for change calculation
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        bars = await alpaca.get_bars(symbol_upper, timeframe="1Day", limit=2)

        prev_close = bars[-2]["close"] if len(bars) >= 2 else bar["close"]
        change = bar["close"] - prev_close
        change_percent = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol_upper,
            "price": latest_trade["price"] if latest_trade else bar["close"],
            "bar_close": bar["close"],
            "bar_timestamp": bar["timestamp"],
            "trade_timestamp": latest_trade["timestamp"] if latest_trade else None,
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "volume": bar["volume"],
            "change": change,
            "change_percent": change_percent,
            "server_time": now_utc.isoformat(),
            "data_age_seconds": (now_utc - datetime.fromisoformat(bar["timestamp"].replace("Z", "+00:00"))).total_seconds() if "T" in bar["timestamp"] else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REALTIME] Error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-source-status")
async def get_data_source_status():
    """
    Get status of data sources and their capabilities.
    Useful for debugging data freshness issues.
    """
    import os
    alpaca_status = "unknown"
    alpaca_connected = False
    test_symbols = {}

    try:
        alpaca = get_alpaca_service()
        # Test connection with multiple symbols
        for symbol in ["AAPL", "GOOGL", "SPY"]:
            try:
                bar = await alpaca.get_latest_bar(symbol)
                test_symbols[symbol] = {
                    "success": True,
                    "price": bar.get("close") if bar else None
                }
                if symbol == "AAPL":
                    alpaca_status = "connected"
                    alpaca_connected = True
            except Exception as e:
                test_symbols[symbol] = {"success": False, "error": str(e)}
    except Exception as e:
        alpaca_status = f"error: {str(e)}"

    return {
        "primary_source": "alpaca",
        "fallback_source": "alpha_vantage",
        "api_key_configured": bool(os.getenv("ALPACA_API_KEY")),
        "test_results": test_symbols,
        "alpaca": {
            "status": alpaca_status,
            "connected": alpaca_connected,
            "features": ["quotes", "historical_bars", "real_time"],
            "limits": "unlimited",
            "cost": "free (included with trading account)",
        },
        "alpha_vantage": {
            "status": "available",
            "features": ["company_overview", "symbol_search"],
            "limits": "25 calls/day (free tier)",
            "cost": "free tier or paid plans available",
            "note": "Only used for company fundamentals and symbol search",
        },
        "recommendation": "Using Alpaca for all price data (unlimited). Alpha Vantage rate limits won't affect charts."
    }


@router.post("/force-refresh/{symbol}")
async def force_refresh_chart_data(symbol: str, interval: str = "1min"):
    """
    Force refresh chart data for a symbol.

    This endpoint:
    1. Clears any server-side cache for the symbol
    2. Fetches fresh data directly from Alpaca
    3. Returns the latest 100 candles with timestamps

    Use this when:
    - Charts appear stale or frozen
    - Data timestamps don't match current time
    - You need to verify data freshness

    Args:
        symbol: Stock symbol (e.g., AAPL) or crypto (e.g., BTC/USD)
        interval: Candle interval (1min, 5min, 15min, 1hour, 1day)
    """
    from datetime import timezone
    symbol_upper = symbol.upper()
    logger.info(f"[FORCE-REFRESH] Clearing cache and fetching fresh data for {symbol_upper} ({interval})")

    try:
        alpaca = get_alpaca_service()
        now_utc = datetime.now(timezone.utc)

        # Map interval to Alpaca timeframe
        interval_map = {
            "1min": "1Min",
            "5min": "5Min",
            "15min": "15Min",
            "30min": "30Min",
            "1hour": "1Hour",
            "1day": "1Day",
        }
        timeframe = interval_map.get(interval.lower(), "1Min")

        # Fetch fresh bars (bypass any caching by requesting with timestamp)
        bars = await alpaca.get_bars(symbol_upper, timeframe=timeframe, limit=100)

        if not bars:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        # Calculate data freshness
        latest_bar = bars[-1] if bars else None
        data_age_seconds = None
        if latest_bar and "timestamp" in latest_bar:
            try:
                bar_time = datetime.fromisoformat(latest_bar["timestamp"].replace("Z", "+00:00"))
                data_age_seconds = (now_utc - bar_time).total_seconds()
            except:
                pass

        return {
            "symbol": symbol_upper,
            "interval": interval,
            "bars_count": len(bars),
            "first_bar_time": bars[0]["timestamp"] if bars else None,
            "last_bar_time": latest_bar["timestamp"] if latest_bar else None,
            "server_time": now_utc.isoformat(),
            "data_age_seconds": data_age_seconds,
            "is_fresh": data_age_seconds is not None and data_age_seconds < 120,  # < 2 min = fresh
            "bars": bars,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORCE-REFRESH] Error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
