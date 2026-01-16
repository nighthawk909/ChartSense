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
    try:
        alpaca = get_alpaca_service()

        # Get latest bar from Alpaca (includes OHLCV)
        bar = await alpaca.get_latest_bar(symbol.upper())

        if not bar:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        # Get previous close to calculate change
        try:
            bars = await alpaca.get_bars(symbol.upper(), timeframe="1Day", limit=2)
            if len(bars) >= 2:
                prev_close = bars[-2]["close"]
                current_price = bar["close"]
                change = current_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0
            else:
                change = 0
                change_percent = 0
        except:
            change = 0
            change_percent = 0

        return StockQuote(
            symbol=symbol.upper(),
            price=bar["close"],
            open=bar["open"],
            high=bar["high"],
            low=bar["low"],
            volume=bar["volume"],
            change=change,
            change_percent=change_percent,
            timestamp=bar["timestamp"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alpaca quote failed for {symbol}: {e}")
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
    try:
        alpaca = get_alpaca_service()

        # Map interval to Alpaca timeframe
        timeframe_map = {
            TimeInterval.ONE_MIN: "1min",
            TimeInterval.FIVE_MIN: "5min",
            TimeInterval.FIFTEEN_MIN: "15min",
            TimeInterval.THIRTY_MIN: "15min",  # Alpaca doesn't have 30min, use 15
            TimeInterval.SIXTY_MIN: "1hour",
            TimeInterval.DAILY: "1day",
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

        bars = await alpaca.get_bars(
            symbol.upper(),
            timeframe=timeframe,
            limit=limit,
            start=start
        )

        if not bars:
            raise HTTPException(status_code=404, detail=f"No history found for {symbol}")

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
        logger.error(f"Alpaca history failed for {symbol}: {e}")
        # Fallback to Alpha Vantage
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
    alpaca_status = "unknown"
    alpaca_connected = False

    try:
        alpaca = get_alpaca_service()
        # Test connection
        await alpaca.get_latest_bar("AAPL")
        alpaca_status = "connected"
        alpaca_connected = True
    except Exception as e:
        alpaca_status = f"error: {str(e)}"

    return {
        "primary_source": "alpaca",
        "fallback_source": "alpha_vantage",
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
