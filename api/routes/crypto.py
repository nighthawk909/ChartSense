"""
Crypto Trading API Routes
24/7 cryptocurrency trading endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from services.crypto_service import get_crypto_service, SUPPORTED_CRYPTOS, DEFAULT_CRYPTO_WATCHLIST

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
async def analyze_crypto(symbol: str):
    """
    Get technical analysis for a cryptocurrency.

    Returns signals, indicators, and trading recommendation.
    """
    crypto_service = get_crypto_service()
    analysis = await crypto_service.analyze_crypto(symbol)

    if "error" in analysis:
        raise HTTPException(status_code=400, detail=analysis["error"])

    return analysis


@router.get("/market-status")
async def get_crypto_market_status():
    """Check crypto market status (always open 24/7)"""
    crypto_service = get_crypto_service()
    return {
        "market_open": crypto_service.is_crypto_market_open(),
        "note": "Crypto markets are open 24/7/365"
    }
