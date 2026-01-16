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
        if timeframe == "1day":
            start = datetime.now() - timedelta(days=limit)
        elif timeframe == "1hour":
            start = datetime.now() - timedelta(days=30)
        else:
            start = datetime.now() - timedelta(days=7)

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
        history = [
            {
                "date": bar["timestamp"].split("T")[0] if "T" in bar["timestamp"] else bar["timestamp"],
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
    """Search for stock symbols by keyword"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Searching for: {query}")
        results = await av_service.search_symbols(query)
        logger.info(f"Search results: {len(results)} matches")
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
