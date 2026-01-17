"""
Crypto Trading API Routes
24/7 cryptocurrency trading endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from services.crypto_service import get_crypto_service, SUPPORTED_CRYPTOS, DEFAULT_CRYPTO_WATCHLIST
from services.pattern_recognition import get_pattern_service

router = APIRouter()


class CryptoOrderRequest(BaseModel):
    """Request to place a crypto order"""
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    order_type: str = "market"
    limit_price: Optional[float] = None


class CryptoOrderResponse(BaseModel):
    """Response from crypto order"""
    order_id: str
    symbol: str
    qty: float
    side: str
    status: str


@router.get("/supported")
async def get_supported_cryptos():
    """Get list of supported cryptocurrencies"""
    return {
        "supported": SUPPORTED_CRYPTOS,
        "default_watchlist": DEFAULT_CRYPTO_WATCHLIST,
    }


@router.get("/quote/{symbol}")
async def get_crypto_quote(symbol: str):
    """
    Get real-time quote for a cryptocurrency.

    Args:
        symbol: Crypto symbol like "BTC/USD" or "BTCUSD"
    """
    crypto_service = get_crypto_service()
    quote = await crypto_service.get_crypto_quote(symbol)

    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")

    return quote


@router.get("/quotes")
async def get_all_crypto_quotes():
    """Get quotes for all default watchlist cryptos"""
    crypto_service = get_crypto_service()
    return await crypto_service.get_all_crypto_quotes()


@router.get("/bars/{symbol}")
async def get_crypto_bars(
    symbol: str,
    timeframe: str = Query("1Hour", description="1Min, 5Min, 15Min, 1Hour, 1Day"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get historical bars for a cryptocurrency"""
    crypto_service = get_crypto_service()
    bars = await crypto_service.get_crypto_bars(symbol, timeframe, limit)

    if not bars:
        raise HTTPException(status_code=404, detail=f"Bars not found for {symbol}")

    return {"symbol": symbol, "timeframe": timeframe, "bars": bars}


@router.get("/positions")
async def get_crypto_positions():
    """Get all current crypto positions"""
    crypto_service = get_crypto_service()
    return await crypto_service.get_crypto_positions()


@router.post("/order")
async def place_crypto_order(order: CryptoOrderRequest):
    """
    Place a cryptocurrency order.

    Note: This places real orders on your Alpaca account (paper or live).
    """
    crypto_service = get_crypto_service()

    result = await crypto_service.place_crypto_order(
        symbol=order.symbol,
        qty=order.qty,
        side=order.side,
        order_type=order.order_type,
        limit_price=order.limit_price,
    )

    if not result:
        raise HTTPException(status_code=400, detail="Failed to place order")

    return result


@router.delete("/position/{symbol}")
async def close_crypto_position(symbol: str):
    """Close a crypto position"""
    crypto_service = get_crypto_service()
    result = await crypto_service.close_crypto_position(symbol)

    if not result:
        raise HTTPException(status_code=400, detail=f"Failed to close position for {symbol}")

    return {"success": True, "symbol": symbol, "message": "Position closed"}


@router.get("/analyze/{symbol}")
async def analyze_crypto(
    symbol: str,
    interval: str = Query("1hour", description="Analysis timeframe: 5min, 15min, 1hour, daily")
):
    """
    Get technical analysis for a cryptocurrency.

    Args:
        symbol: Crypto symbol (e.g., BTC/USD)
        interval: Timeframe for analysis (5min, 15min, 1hour, daily)

    Returns signals, indicators, and trading recommendation with timeframe context.
    """
    crypto_service = get_crypto_service()

    # Map frontend interval names to API format
    interval_map = {
        "5min": "5Min",
        "15min": "15Min",
        "1hour": "1Hour",
        "1h": "1Hour",
        "daily": "1Day",
        "1d": "1Day",
    }
    timeframe = interval_map.get(interval.lower(), "1Hour")

    analysis = await crypto_service.analyze_crypto(symbol, timeframe)

    if "error" in analysis:
        raise HTTPException(status_code=400, detail=analysis["error"])

    return analysis


@router.get("/patterns/{symbol}")
async def get_crypto_patterns(
    symbol: str,
    interval: str = Query("1hour", description="Timeframe: 5min, 15min, 1hour, daily")
):
    """
    Get pattern analysis for a cryptocurrency.

    Same pattern recognition as stocks: H&S, Double Top/Bottom, Flags, etc.
    Includes timeframe-appropriate weighting and entry zones.
    """
    crypto_service = get_crypto_service()
    pattern_service = get_pattern_service()

    # Map frontend interval to Alpaca timeframe
    interval_map = {
        "5min": "5Min",
        "15min": "15Min",
        "1hour": "1Hour",
        "1h": "1Hour",
        "daily": "1Day",
        "1d": "1Day",
        "1D": "1Day",
    }
    timeframe = interval_map.get(interval, "1Hour")

    # Adjust limit based on timeframe
    limit_map = {
        "5Min": 500,
        "15Min": 400,
        "1Hour": 300,
        "1Day": 200,
    }
    limit = limit_map.get(timeframe, 300)

    try:
        bars = await crypto_service.get_crypto_bars(symbol, timeframe, limit)

        if not bars or len(bars) < 50:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data for {symbol} ({len(bars) if bars else 0} bars)"
            )

        # Extract OHLC data
        opens = [b["open"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]

        # Analyze patterns with timeframe weighting
        result = pattern_service.analyze(opens, highs, lows, closes, timeframe=interval)
        result["symbol"] = symbol.upper()
        result["interval"] = interval
        result["timeframe"] = timeframe
        result["bars_analyzed"] = len(bars)
        result["current_price"] = closes[-1] if closes else None
        result["asset_type"] = "crypto"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-status")
async def get_crypto_market_status():
    """Check crypto market status (always open 24/7)"""
    crypto_service = get_crypto_service()
    return {
        "market_open": crypto_service.is_crypto_market_open(),
        "message": "Crypto markets are open 24/7/365"
    }


@router.get("/debug")
async def debug_crypto_connection():
    """Debug endpoint to test Alpaca crypto API connection"""
    import os
    crypto_service = get_crypto_service()

    result = {
        "api_key_set": bool(os.getenv("ALPACA_API_KEY")),
        "secret_key_set": bool(os.getenv("ALPACA_SECRET_KEY")),
        "trading_mode": os.getenv("ALPACA_TRADING_MODE", "paper"),
        "data_url": crypto_service.data_url,
        "base_url": crypto_service.base_url,
    }

    # Test BTC quote
    try:
        quote = await crypto_service.get_crypto_quote("BTC/USD")
        result["btc_quote_success"] = quote is not None
        if quote:
            result["btc_price"] = quote.get("price")
    except Exception as e:
        result["btc_quote_error"] = str(e)

    return result
