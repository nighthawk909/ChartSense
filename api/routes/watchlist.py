"""
Watchlist management routes
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage (replace with database in production)
user_watchlist: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]


class WatchlistItemInput(BaseModel):
    symbol: str
    asset_class: Optional[str] = "stock"


class WatchlistItemDetail(BaseModel):
    symbol: str
    name: Optional[str] = None
    current_price: float = 0
    change: float = 0
    change_pct: float = 0
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    bot_discovered: bool = False
    discovered_at: Optional[str] = None
    discovery_reason: Optional[str] = None


class WatchlistResponse(BaseModel):
    symbols: List[str]
    count: int


class WatchlistDetailResponse(BaseModel):
    items: List[WatchlistItemDetail]
    count: int


@router.get("/")
async def get_watchlist():
    """Get all symbols in the watchlist with enriched data"""
    import asyncio
    from services.alpaca_service import get_alpaca_service

    alpaca = get_alpaca_service()

    async def fetch_stock_data(symbol: str) -> WatchlistItemDetail:
        """Fetch data for a single stock symbol"""
        try:
            # Check if it's a crypto symbol (skip Alpaca for crypto)
            if '/' in symbol or symbol.endswith('USD') or symbol.endswith('USDT'):
                return WatchlistItemDetail(
                    symbol=symbol,
                    name=get_company_name(symbol),
                )

            # Get latest bar data for stocks (includes OHLCV)
            bar = await alpaca.get_latest_bar(symbol)

            # Get 2-day bars to calculate change
            bars = await alpaca.get_bars(symbol, timeframe="1Day", limit=2)
            prev_close = bars[-2]["close"] if len(bars) >= 2 else bar["close"]
            change = bar["close"] - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return WatchlistItemDetail(
                symbol=symbol,
                name=get_company_name(symbol),
                current_price=bar.get('close', 0) if bar else 0,
                change=change,
                change_pct=change_pct,
                volume=bar.get('volume') if bar else None,
            )
        except Exception as e:
            logger.warning(f"Failed to get data for {symbol}: {e}")
            return WatchlistItemDetail(
                symbol=symbol,
                name=get_company_name(symbol),
            )

    # Fetch all stock data in parallel
    items = await asyncio.gather(*[fetch_stock_data(s) for s in user_watchlist])

    return {"items": list(items), "count": len(items)}


def get_company_name(symbol: str) -> str:
    """Get company name from symbol"""
    names = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corp.",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "NVDA": "NVIDIA Corp.",
        "META": "Meta Platforms Inc.",
        "TSLA": "Tesla Inc.",
        "BTC/USD": "Bitcoin",
        "ETH/USD": "Ethereum",
        "SOL/USD": "Solana",
    }
    return names.get(symbol, symbol)


@router.post("/add")
async def add_to_watchlist(item: WatchlistItemInput):
    """Add a symbol to the watchlist"""
    symbol = item.symbol.upper()
    if symbol in user_watchlist:
        raise HTTPException(status_code=400, detail=f"{symbol} already in watchlist")
    user_watchlist.append(symbol)
    return {"success": True, "symbol": symbol, "count": len(user_watchlist)}


@router.delete("/remove/{symbol}", response_model=WatchlistResponse)
async def remove_from_watchlist(symbol: str):
    """Remove a symbol from the watchlist"""
    symbol = symbol.upper()
    if symbol not in user_watchlist:
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    user_watchlist.remove(symbol)
    return WatchlistResponse(symbols=user_watchlist, count=len(user_watchlist))


@router.get("/check/{symbol}")
async def check_in_watchlist(symbol: str):
    """Check if a symbol is in the watchlist"""
    return {"symbol": symbol.upper(), "in_watchlist": symbol.upper() in user_watchlist}
