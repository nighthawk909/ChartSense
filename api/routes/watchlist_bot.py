"""
User Watchlist and Stock Repository Routes
Manage user's personal stock picks and the bot's stock repository
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.connection import SessionLocal
from database.models import UserWatchlist, StockRepository

logger = logging.getLogger(__name__)

# Promotion settings (could be moved to settings/config)
PROMOTION_SETTINGS = {
    "min_confidence": 75.0,  # Minimum AI confidence to auto-promote
    "min_consecutive_signals": 2,  # Consecutive bullish signals needed
    "max_auto_promotions_per_day": 5,  # Limit daily auto-promotions
    "cool_down_hours": 24,  # Hours before re-evaluating a rejected ticker
    "auto_promote_enabled": True,  # Global toggle
}

# In-memory tracking for promotions (replace with database in production)
promotion_history: List[Dict[str, Any]] = []
promotion_candidates: Dict[str, Dict[str, Any]] = {}

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


# ============== Watchlist Promotion Routes ==============

class PromotionCandidate(BaseModel):
    """Bot-discovered ticker candidate for promotion"""
    symbol: str
    name: Optional[str] = None
    confidence: float
    signal: str  # BUY, STRONG_BUY, etc.
    reasoning: List[str]
    indicators: Dict[str, Any]
    discovered_at: Optional[datetime] = None


class PromotionDecision(BaseModel):
    """User decision on a promotion candidate"""
    symbol: str
    approved: bool
    add_to_watchlist: bool = False
    notes: Optional[str] = None


class PromotionSettings(BaseModel):
    """Settings for auto-promotion behavior"""
    min_confidence: float = 75.0
    min_consecutive_signals: int = 2
    max_auto_promotions_per_day: int = 5
    cool_down_hours: int = 24
    auto_promote_enabled: bool = True


@router.post("/promotion/candidate")
async def add_promotion_candidate(candidate: PromotionCandidate):
    """
    Bot submits a ticker as a promotion candidate.
    Called by the trading bot when it discovers a high-confidence opportunity.
    """
    global promotion_candidates

    symbol = candidate.symbol.upper()

    # Check if already in watchlist or repository
    db = SessionLocal()
    try:
        in_watchlist = db.query(UserWatchlist).filter(
            UserWatchlist.symbol == symbol
        ).first() is not None

        in_repository = db.query(StockRepository).filter(
            StockRepository.symbol == symbol
        ).first() is not None

        if in_watchlist:
            return {
                "status": "already_watched",
                "symbol": symbol,
                "message": f"{symbol} is already in watchlist"
            }

        # Track or update candidate
        if symbol in promotion_candidates:
            # Update existing candidate
            existing = promotion_candidates[symbol]
            existing["consecutive_signals"] = existing.get("consecutive_signals", 0) + 1
            existing["latest_confidence"] = candidate.confidence
            existing["latest_signal"] = candidate.signal
            existing["latest_reasoning"] = candidate.reasoning
            existing["updated_at"] = datetime.now().isoformat()
        else:
            # New candidate
            promotion_candidates[symbol] = {
                "symbol": symbol,
                "name": candidate.name,
                "confidence": candidate.confidence,
                "signal": candidate.signal,
                "reasoning": candidate.reasoning,
                "indicators": candidate.indicators,
                "discovered_at": (candidate.discovered_at or datetime.now()).isoformat(),
                "consecutive_signals": 1,
                "latest_confidence": candidate.confidence,
                "latest_signal": candidate.signal,
                "latest_reasoning": candidate.reasoning,
                "in_repository": in_repository,
                "updated_at": datetime.now().isoformat(),
            }

        # Check if should auto-promote
        should_promote = await _check_auto_promotion(symbol)

        return {
            "status": "candidate_added" if not should_promote else "auto_promoted",
            "symbol": symbol,
            "consecutive_signals": promotion_candidates[symbol]["consecutive_signals"],
            "meets_threshold": candidate.confidence >= PROMOTION_SETTINGS["min_confidence"],
            "auto_promoted": should_promote,
        }

    finally:
        db.close()


async def _check_auto_promotion(symbol: str) -> bool:
    """Check if a candidate should be auto-promoted to watchlist"""
    global promotion_history

    if not PROMOTION_SETTINGS["auto_promote_enabled"]:
        return False

    candidate = promotion_candidates.get(symbol)
    if not candidate:
        return False

    # Check confidence threshold
    if candidate["latest_confidence"] < PROMOTION_SETTINGS["min_confidence"]:
        return False

    # Check consecutive signals
    if candidate["consecutive_signals"] < PROMOTION_SETTINGS["min_consecutive_signals"]:
        return False

    # Check daily limit
    today = datetime.now().date()
    today_promotions = [
        p for p in promotion_history
        if datetime.fromisoformat(p["promoted_at"]).date() == today
        and p["auto_promoted"]
    ]
    if len(today_promotions) >= PROMOTION_SETTINGS["max_auto_promotions_per_day"]:
        logger.info(f"Daily auto-promotion limit reached, skipping {symbol}")
        return False

    # Auto-promote to watchlist
    db = SessionLocal()
    try:
        new_stock = UserWatchlist(
            symbol=symbol,
            name=candidate.get("name"),
            notes=f"Auto-promoted by bot. Confidence: {candidate['latest_confidence']:.0f}%. Reason: {candidate['latest_reasoning'][0] if candidate['latest_reasoning'] else 'High confidence signal'}",
            auto_trade=True,
            max_position_pct=0.15,  # More conservative for auto-promoted
        )
        db.add(new_stock)
        db.commit()

        # Record promotion
        promotion_history.append({
            "symbol": symbol,
            "confidence": candidate["latest_confidence"],
            "signal": candidate["latest_signal"],
            "reasoning": candidate["latest_reasoning"],
            "promoted_at": datetime.now().isoformat(),
            "auto_promoted": True,
            "consecutive_signals": candidate["consecutive_signals"],
        })

        # Remove from candidates
        del promotion_candidates[symbol]

        logger.info(f"Auto-promoted {symbol} to watchlist with {candidate['latest_confidence']:.0f}% confidence")
        return True

    except Exception as e:
        logger.error(f"Failed to auto-promote {symbol}: {e}")
        return False
    finally:
        db.close()


@router.get("/promotion/candidates")
async def get_promotion_candidates():
    """Get all pending promotion candidates for user review"""
    return {
        "candidates": list(promotion_candidates.values()),
        "count": len(promotion_candidates),
        "settings": PROMOTION_SETTINGS,
    }


@router.post("/promotion/decide")
async def decide_promotion(decision: PromotionDecision):
    """
    User makes a decision on a promotion candidate.
    Can approve/reject and optionally add to watchlist.
    """
    global promotion_candidates, promotion_history

    symbol = decision.symbol.upper()
    candidate = promotion_candidates.get(symbol)

    if not candidate:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in promotion candidates")

    if decision.approved and decision.add_to_watchlist:
        # Add to watchlist
        db = SessionLocal()
        try:
            existing = db.query(UserWatchlist).filter(
                UserWatchlist.symbol == symbol
            ).first()

            if existing:
                raise HTTPException(status_code=400, detail=f"{symbol} already in watchlist")

            new_stock = UserWatchlist(
                symbol=symbol,
                name=candidate.get("name"),
                notes=decision.notes or f"Promoted from bot discovery. Confidence: {candidate['latest_confidence']:.0f}%",
                auto_trade=True,
                max_position_pct=0.20,
            )
            db.add(new_stock)
            db.commit()

        finally:
            db.close()

    # Record decision
    promotion_history.append({
        "symbol": symbol,
        "confidence": candidate["latest_confidence"],
        "signal": candidate["latest_signal"],
        "reasoning": candidate["latest_reasoning"],
        "promoted_at": datetime.now().isoformat(),
        "auto_promoted": False,
        "approved": decision.approved,
        "added_to_watchlist": decision.add_to_watchlist,
        "user_notes": decision.notes,
    })

    # Remove from candidates
    del promotion_candidates[symbol]

    return {
        "symbol": symbol,
        "approved": decision.approved,
        "added_to_watchlist": decision.add_to_watchlist,
        "message": f"{symbol} {'promoted to watchlist' if decision.add_to_watchlist else 'decision recorded'}",
    }


@router.get("/promotion/history")
async def get_promotion_history(
    limit: int = Query(default=50, ge=1, le=200),
    auto_only: bool = False,
):
    """Get promotion history"""
    history = promotion_history

    if auto_only:
        history = [p for p in history if p.get("auto_promoted")]

    # Sort by most recent first
    history = sorted(history, key=lambda x: x["promoted_at"], reverse=True)

    return {
        "history": history[:limit],
        "total": len(promotion_history),
    }


@router.get("/promotion/settings")
async def get_promotion_settings():
    """Get current promotion settings"""
    return PROMOTION_SETTINGS


@router.post("/promotion/settings")
async def update_promotion_settings(settings: PromotionSettings):
    """Update promotion settings"""
    global PROMOTION_SETTINGS

    PROMOTION_SETTINGS["min_confidence"] = settings.min_confidence
    PROMOTION_SETTINGS["min_consecutive_signals"] = settings.min_consecutive_signals
    PROMOTION_SETTINGS["max_auto_promotions_per_day"] = settings.max_auto_promotions_per_day
    PROMOTION_SETTINGS["cool_down_hours"] = settings.cool_down_hours
    PROMOTION_SETTINGS["auto_promote_enabled"] = settings.auto_promote_enabled

    return {
        "message": "Promotion settings updated",
        "settings": PROMOTION_SETTINGS,
    }


@router.delete("/promotion/candidate/{symbol}")
async def dismiss_candidate(symbol: str):
    """Dismiss a promotion candidate without adding to watchlist"""
    global promotion_candidates

    symbol = symbol.upper()

    if symbol not in promotion_candidates:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in promotion candidates")

    # Record dismissal
    candidate = promotion_candidates[symbol]
    promotion_history.append({
        "symbol": symbol,
        "confidence": candidate["latest_confidence"],
        "signal": candidate["latest_signal"],
        "promoted_at": datetime.now().isoformat(),
        "auto_promoted": False,
        "approved": False,
        "dismissed": True,
    })

    del promotion_candidates[symbol]

    return {
        "symbol": symbol,
        "message": f"{symbol} dismissed from promotion candidates",
    }


@router.post("/promotion/bulk-approve")
async def bulk_approve_candidates(
    min_confidence: float = Query(default=80.0, description="Minimum confidence to approve"),
):
    """Bulk approve all candidates meeting confidence threshold"""
    global promotion_candidates

    approved = []
    db = SessionLocal()

    try:
        for symbol, candidate in list(promotion_candidates.items()):
            if candidate["latest_confidence"] >= min_confidence:
                # Check not already in watchlist
                existing = db.query(UserWatchlist).filter(
                    UserWatchlist.symbol == symbol
                ).first()

                if not existing:
                    new_stock = UserWatchlist(
                        symbol=symbol,
                        name=candidate.get("name"),
                        notes=f"Bulk approved. Confidence: {candidate['latest_confidence']:.0f}%",
                        auto_trade=True,
                        max_position_pct=0.15,
                    )
                    db.add(new_stock)

                    # Record
                    promotion_history.append({
                        "symbol": symbol,
                        "confidence": candidate["latest_confidence"],
                        "signal": candidate["latest_signal"],
                        "promoted_at": datetime.now().isoformat(),
                        "auto_promoted": False,
                        "bulk_approved": True,
                    })

                    approved.append(symbol)
                    del promotion_candidates[symbol]

        db.commit()

    finally:
        db.close()

    return {
        "approved": approved,
        "count": len(approved),
        "message": f"Bulk approved {len(approved)} candidates with confidence >= {min_confidence}%",
    }
