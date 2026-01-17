"""
Watchlist management routes
Includes both stocks and crypto from scanning
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage (replace with database in production)
user_watchlist: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

# Crypto watchlist - synced from bot's crypto scanning
crypto_watchlist: List[str] = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD"]


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
    """Get all symbols in the watchlist with enriched data (stocks + crypto)"""
    import asyncio
    from services.alpaca_service import get_alpaca_service
    from services.crypto_service import get_crypto_service

    alpaca = get_alpaca_service()
    crypto_service = get_crypto_service()

    async def fetch_stock_data(symbol: str) -> WatchlistItemDetail:
        """Fetch data for a single stock symbol"""
        try:
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

    async def fetch_crypto_data(symbol: str) -> WatchlistItemDetail:
        """Fetch data for a crypto symbol"""
        try:
            quote = await crypto_service.get_crypto_quote(symbol)
            if quote:
                return WatchlistItemDetail(
                    symbol=symbol,
                    name=get_company_name(symbol),
                    current_price=quote.get('price', 0),
                    change=quote.get('change_24h', 0),
                    change_pct=quote.get('change_percent_24h', 0),
                    volume=int(quote.get('volume_24h', 0)) if quote.get('volume_24h') else None,
                    bot_discovered=True,  # Crypto is always from bot scanning
                )
            return WatchlistItemDetail(
                symbol=symbol,
                name=get_company_name(symbol),
                bot_discovered=True,
            )
        except Exception as e:
            logger.warning(f"Failed to get crypto data for {symbol}: {e}")
            return WatchlistItemDetail(
                symbol=symbol,
                name=get_company_name(symbol),
                bot_discovered=True,
            )

    # Fetch stock data and crypto data in parallel
    stock_items = await asyncio.gather(*[fetch_stock_data(s) for s in user_watchlist])
    crypto_items = await asyncio.gather(*[fetch_crypto_data(s) for s in crypto_watchlist])

    # Combine stocks and crypto
    all_items = list(stock_items) + list(crypto_items)

    return {"items": all_items, "count": len(all_items)}


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
    """Add a symbol to the watchlist (stocks or crypto)"""
    symbol = item.symbol.upper()
    is_crypto = '/' in symbol or symbol.endswith('USD') or symbol.endswith('USDT') or item.asset_class == 'crypto'

    if is_crypto:
        # Ensure proper format for crypto (e.g., BTC/USD)
        if not '/' in symbol and symbol.endswith('USD'):
            # Convert BTCUSD -> BTC/USD
            base = symbol[:-3]
            symbol = f"{base}/USD"

        if symbol in crypto_watchlist:
            raise HTTPException(status_code=400, detail=f"{symbol} already in crypto watchlist")
        crypto_watchlist.append(symbol)
        return {"success": True, "symbol": symbol, "asset_class": "crypto", "count": len(crypto_watchlist)}
    else:
        if symbol in user_watchlist:
            raise HTTPException(status_code=400, detail=f"{symbol} already in watchlist")
        user_watchlist.append(symbol)
        return {"success": True, "symbol": symbol, "asset_class": "stock", "count": len(user_watchlist)}


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
