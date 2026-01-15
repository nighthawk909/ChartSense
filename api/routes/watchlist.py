"""
Watchlist management routes
"""
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter()

# In-memory storage (replace with database in production)
user_watchlist: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]


class WatchlistItem(BaseModel):
    symbol: str


class WatchlistResponse(BaseModel):
    symbols: List[str]
    count: int


@router.get("/", response_model=WatchlistResponse)
async def get_watchlist():
    """Get all symbols in the watchlist"""
    return WatchlistResponse(symbols=user_watchlist, count=len(user_watchlist))


@router.post("/add", response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistItem):
    """Add a symbol to the watchlist"""
    symbol = item.symbol.upper()
    if symbol in user_watchlist:
        raise HTTPException(status_code=400, detail=f"{symbol} already in watchlist")
    user_watchlist.append(symbol)
    return WatchlistResponse(symbols=user_watchlist, count=len(user_watchlist))


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
