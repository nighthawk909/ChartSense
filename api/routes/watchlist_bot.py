"""
User Watchlist and Stock Repository Routes
Manage user's personal stock picks and the bot's stock repository
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database.connection import SessionLocal
from database.models import UserWatchlist, StockRepository

router = APIRouter()


# ============== Pydantic Models ==============

class AddWatchlistStock(BaseModel):
    """Request to add a stock to user watchlist"""
    symbol: str
    name: Optional[str] = None
    notes: Optional[str] = None
    target_buy_price: Optional[float] = None
    target_sell_price: Optional[float] = None
    auto_trade: bool = True
    max_position_pct: float = 0.20


class WatchlistStockResponse(BaseModel):
    """User watchlist stock response"""
    id: int
    symbol: str
    name: Optional[str]
    notes: Optional[str]
    target_buy_price: Optional[float]
    target_sell_price: Optional[float]
    auto_trade: bool
    max_position_pct: float
    added_at: datetime


class AddRepositoryStock(BaseModel):
    """Request to add a stock to repository"""
    symbol: str
    name: Optional[str] = None
    source: str = "USER"  # USER, AI_DISCOVERED, PERFORMANCE
    priority: int = 5
    trade_type: Optional[str] = None  # SWING, LONG_TERM, BOTH
    sector: Optional[str] = None
    risk_level: str = "MEDIUM"
    notes: Optional[str] = None


class RepositoryStockResponse(BaseModel):
    """Stock repository response"""
    id: int
    symbol: str
    name: Optional[str]
    source: str
    priority: int
    trade_type: Optional[str]
    sector: Optional[str]
    risk_level: str
    ai_reason: Optional[str]
    last_analysis_score: Optional[float]
    total_trades: int
    winning_trades: int
    total_pnl: float
    is_active: bool
    is_tradeable: bool


# ============== User Watchlist Routes ==============

@router.get("/watchlist", response_model=List[WatchlistStockResponse])
async def get_user_watchlist():
    """Get all stocks in user's personal watchlist"""
    db = SessionLocal()
    try:
        stocks = db.query(UserWatchlist).all()
        return [
            WatchlistStockResponse(
                id=s.id,
                symbol=s.symbol,
                name=s.name,
                notes=s.notes,
                target_buy_price=s.target_buy_price,
                target_sell_price=s.target_sell_price,
                auto_trade=s.auto_trade,
                max_position_pct=s.max_position_pct,
                added_at=s.added_at or datetime.now(),
            )
            for s in stocks
        ]
    finally:
        db.close()


@router.post("/watchlist", response_model=WatchlistStockResponse)
async def add_to_watchlist(stock: AddWatchlistStock):
    """Add a stock to user's watchlist - bot will prioritize these"""
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(UserWatchlist).filter(
            UserWatchlist.symbol == stock.symbol.upper()
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail=f"{stock.symbol} already in watchlist")

        new_stock = UserWatchlist(
            symbol=stock.symbol.upper(),
            name=stock.name,
            notes=stock.notes,
            target_buy_price=stock.target_buy_price,
            target_sell_price=stock.target_sell_price,
            auto_trade=stock.auto_trade,
            max_position_pct=stock.max_position_pct,
        )
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)

        return WatchlistStockResponse(
            id=new_stock.id,
            symbol=new_stock.symbol,
            name=new_stock.name,
            notes=new_stock.notes,
            target_buy_price=new_stock.target_buy_price,
            target_sell_price=new_stock.target_sell_price,
            auto_trade=new_stock.auto_trade,
            max_position_pct=new_stock.max_position_pct,
            added_at=new_stock.added_at or datetime.now(),
        )
    finally:
        db.close()


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a stock from user's watchlist"""
    db = SessionLocal()
    try:
        stock = db.query(UserWatchlist).filter(
            UserWatchlist.symbol == symbol.upper()
        ).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")

        db.delete(stock)
        db.commit()
        return {"message": f"{symbol} removed from watchlist"}
    finally:
        db.close()


@router.patch("/watchlist/{symbol}/toggle-auto-trade")
async def toggle_auto_trade(symbol: str):
    """Toggle auto-trade setting for a watchlist stock"""
    db = SessionLocal()
    try:
        stock = db.query(UserWatchlist).filter(
            UserWatchlist.symbol == symbol.upper()
        ).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")

        stock.auto_trade = not stock.auto_trade
        db.commit()

        return {
            "symbol": stock.symbol,
            "auto_trade": stock.auto_trade,
            "message": f"Auto-trade {'enabled' if stock.auto_trade else 'disabled'} for {symbol}"
        }
    finally:
        db.close()


# ============== Stock Repository Routes ==============

@router.get("/repository", response_model=List[RepositoryStockResponse])
async def get_stock_repository(
    active_only: bool = False,
    tradeable_only: bool = False,
    source: Optional[str] = None,
):
    """
    Get stocks from the bot's repository.

    Args:
        active_only: Only return active stocks
        tradeable_only: Only return stocks meeting entry criteria
        source: Filter by source (USER, AI_DISCOVERED, PERFORMANCE)
    """
    db = SessionLocal()
    try:
        query = db.query(StockRepository)

        if active_only:
            query = query.filter(StockRepository.is_active == True)
        if tradeable_only:
            query = query.filter(StockRepository.is_tradeable == True)
        if source:
            query = query.filter(StockRepository.source == source.upper())

        stocks = query.order_by(StockRepository.priority.desc()).all()

        return [
            RepositoryStockResponse(
                id=s.id,
                symbol=s.symbol,
                name=s.name,
                source=s.source or "USER",
                priority=s.priority or 5,
                trade_type=s.trade_type,
                sector=s.sector,
                risk_level=s.risk_level or "MEDIUM",
                ai_reason=s.ai_reason,
                last_analysis_score=s.last_analysis_score,
                total_trades=s.total_trades or 0,
                winning_trades=s.winning_trades or 0,
                total_pnl=s.total_pnl or 0.0,
                is_active=s.is_active if s.is_active is not None else True,
                is_tradeable=s.is_tradeable if s.is_tradeable is not None else True,
            )
            for s in stocks
        ]
    finally:
        db.close()


@router.post("/repository", response_model=RepositoryStockResponse)
async def add_to_repository(stock: AddRepositoryStock):
    """Add a stock to the bot's repository"""
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(StockRepository).filter(
            StockRepository.symbol == stock.symbol.upper()
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail=f"{stock.symbol} already in repository")

        new_stock = StockRepository(
            symbol=stock.symbol.upper(),
            name=stock.name,
            source=stock.source.upper(),
            priority=stock.priority,
            trade_type=stock.trade_type,
            sector=stock.sector,
            risk_level=stock.risk_level,
            notes=stock.notes,
            is_active=True,
            is_tradeable=True,
        )
        db.add(new_stock)
        db.commit()
        db.refresh(new_stock)

        return RepositoryStockResponse(
            id=new_stock.id,
            symbol=new_stock.symbol,
            name=new_stock.name,
            source=new_stock.source or "USER",
            priority=new_stock.priority or 5,
            trade_type=new_stock.trade_type,
            sector=new_stock.sector,
            risk_level=new_stock.risk_level or "MEDIUM",
            ai_reason=new_stock.ai_reason,
            last_analysis_score=new_stock.last_analysis_score,
            total_trades=new_stock.total_trades or 0,
            winning_trades=new_stock.winning_trades or 0,
            total_pnl=new_stock.total_pnl or 0.0,
            is_active=True,
            is_tradeable=True,
        )
    finally:
        db.close()


@router.delete("/repository/{symbol}")
async def remove_from_repository(symbol: str):
    """Remove a stock from the repository"""
    db = SessionLocal()
    try:
        stock = db.query(StockRepository).filter(
            StockRepository.symbol == symbol.upper()
        ).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"{symbol} not found in repository")

        db.delete(stock)
        db.commit()
        return {"message": f"{symbol} removed from repository"}
    finally:
        db.close()


@router.patch("/repository/{symbol}/priority")
async def update_priority(symbol: str, priority: int):
    """Update a stock's priority (1-10, higher = more priority)"""
    if priority < 1 or priority > 10:
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 10")

    db = SessionLocal()
    try:
        stock = db.query(StockRepository).filter(
            StockRepository.symbol == symbol.upper()
        ).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"{symbol} not found in repository")

        stock.priority = priority
        db.commit()

        return {"symbol": stock.symbol, "priority": priority}
    finally:
        db.close()


@router.patch("/repository/{symbol}/toggle-active")
async def toggle_repository_active(symbol: str):
    """Toggle active status for a repository stock"""
    db = SessionLocal()
    try:
        stock = db.query(StockRepository).filter(
            StockRepository.symbol == symbol.upper()
        ).first()

        if not stock:
            raise HTTPException(status_code=404, detail=f"{symbol} not found in repository")

        stock.is_active = not stock.is_active
        db.commit()

        return {
            "symbol": stock.symbol,
            "is_active": stock.is_active,
            "message": f"{symbol} {'activated' if stock.is_active else 'deactivated'}"
        }
    finally:
        db.close()


@router.get("/repository/stats")
async def get_repository_stats():
    """Get statistics about the stock repository"""
    db = SessionLocal()
    try:
        total = db.query(StockRepository).count()
        active = db.query(StockRepository).filter(StockRepository.is_active == True).count()
        tradeable = db.query(StockRepository).filter(StockRepository.is_tradeable == True).count()

        user_added = db.query(StockRepository).filter(StockRepository.source == "USER").count()
        ai_discovered = db.query(StockRepository).filter(StockRepository.source == "AI_DISCOVERED").count()
        performance = db.query(StockRepository).filter(StockRepository.source == "PERFORMANCE").count()

        return {
            "total_stocks": total,
            "active_stocks": active,
            "tradeable_stocks": tradeable,
            "by_source": {
                "user_added": user_added,
                "ai_discovered": ai_discovered,
                "performance_based": performance,
            }
        }
    finally:
        db.close()
