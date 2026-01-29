"""
Position Management API Routes
Endpoints for viewing and managing trading positions
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from models.bot import (
    PositionResponse,
    PositionsListResponse,
    ClosePositionRequest,
    ClosePositionResponse,
    AccountSummary,
    TradeType,
)
from services.trading_bot import get_trading_bot
from services.alpaca_service import get_alpaca_service
from database.connection import SessionLocal
from database.models import Position as DBPosition

router = APIRouter()


@router.get("/account", response_model=AccountSummary)
async def get_account_summary():
    """
    Get account summary with equity, cash, and P&L.
    """
    alpaca = get_alpaca_service()

    try:
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()

        # Calculate unrealized P&L
        unrealized_pnl = sum(p["unrealized_pnl"] for p in positions)
        portfolio_value = sum(p["market_value"] for p in positions)

        # Calculate day P&L (equity change from previous close)
        day_pnl = account["equity"] - (account.get("last_equity") or account["equity"])
        day_pnl_pct = (day_pnl / account.get("last_equity", account["equity"]) * 100) if account.get("last_equity") else 0

        unrealized_pnl_pct = (unrealized_pnl / portfolio_value * 100) if portfolio_value > 0 else 0

        return AccountSummary(
            equity=account["equity"],
            cash=account["cash"],
            buying_power=account["buying_power"],
            portfolio_value=portfolio_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            day_pnl=day_pnl,
            day_pnl_pct=day_pnl_pct,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get account: {str(e)}")


@router.get("/current", response_model=PositionsListResponse)
async def get_current_positions():
    """
    Get all current open positions (stocks AND crypto).

    Returns positions from Alpaca with our strategy metadata.
    """
    alpaca = get_alpaca_service()

    try:
        alpaca_positions = await alpaca.get_positions()

        # Get our tracked data from database (use context manager for proper cleanup)
        db_positions = {}
        try:
            db = SessionLocal()
            db_positions = {p.symbol: p for p in db.query(DBPosition).all()}
        finally:
            db.close()

        positions = []
        total_value = 0
        total_unrealized_pnl = 0

        for pos in alpaca_positions:
            symbol = pos["symbol"]
            db_pos = db_positions.get(symbol)

            # Determine if crypto based on symbol format or asset class
            asset_class = pos.get("asset_class", "us_equity")
            is_crypto = asset_class == "crypto" or symbol.endswith("USD") or "/" in symbol

            position = PositionResponse(
                symbol=symbol,
                quantity=pos["quantity"],
                entry_price=db_pos.entry_price if db_pos else pos["entry_price"],
                current_price=pos["current_price"],
                market_value=pos["market_value"],
                unrealized_pnl=pos["unrealized_pnl"],
                unrealized_pnl_pct=pos["unrealized_pnl_pct"],
                stop_loss=db_pos.stop_loss_price if db_pos else None,
                profit_target=db_pos.profit_target_price if db_pos else None,
                trade_type=TradeType(db_pos.trade_type) if db_pos and db_pos.trade_type else None,
                entry_time=db_pos.entry_time if db_pos else None,
                entry_score=db_pos.entry_score if db_pos else None,
                asset_class="crypto" if is_crypto else "stock",
                # Entry insight fields
                entry_reason=getattr(db_pos, 'entry_reason', None) if db_pos else None,
                indicators_snapshot=getattr(db_pos, 'indicators_snapshot', None) if db_pos else None,
                confluence_factors=getattr(db_pos, 'confluence_factors', None) if db_pos else None,
            )
            positions.append(position)

            total_value += pos["market_value"]
            total_unrealized_pnl += pos["unrealized_pnl"]

        return PositionsListResponse(
            positions=positions,
            total_value=total_value,
            total_unrealized_pnl=total_unrealized_pnl,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str):
    """
    Get a specific position by symbol.
    """
    alpaca = get_alpaca_service()

    try:
        pos = await alpaca.get_position(symbol.upper())

        if not pos:
            raise HTTPException(status_code=404, detail=f"No position for {symbol}")

        # Get our tracked data
        db = SessionLocal()
        db_pos = db.query(DBPosition).filter(DBPosition.symbol == symbol.upper()).first()
        db.close()

        return PositionResponse(
            symbol=pos["symbol"],
            quantity=pos["quantity"],
            entry_price=db_pos.entry_price if db_pos else pos["entry_price"],
            current_price=pos["current_price"],
            market_value=pos["market_value"],
            unrealized_pnl=pos["unrealized_pnl"],
            unrealized_pnl_pct=pos["unrealized_pnl_pct"],
            stop_loss=db_pos.stop_loss_price if db_pos else None,
            profit_target=db_pos.profit_target_price if db_pos else None,
            trade_type=TradeType(db_pos.trade_type) if db_pos and db_pos.trade_type else None,
            entry_time=db_pos.entry_time if db_pos else None,
            entry_score=db_pos.entry_score if db_pos else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {str(e)}")


@router.post("/close/{symbol}", response_model=ClosePositionResponse)
async def close_position(symbol: str, quantity: Optional[float] = None):
    """
    Close a position (sell shares).

    If quantity is not specified, closes the entire position.
    """
    alpaca = get_alpaca_service()

    try:
        # Check if position exists
        pos = await alpaca.get_position(symbol.upper())
        if not pos:
            raise HTTPException(status_code=404, detail=f"No position for {symbol}")

        # Close position
        order = await alpaca.close_position(symbol.upper(), quantity)

        # Update database
        db = SessionLocal()
        db_pos = db.query(DBPosition).filter(DBPosition.symbol == symbol.upper()).first()
        if db_pos and not quantity:
            db.delete(db_pos)
            db.commit()
        db.close()

        return ClosePositionResponse(
            success=True,
            message=f"Position closed for {symbol}",
            symbol=symbol.upper(),
            quantity_closed=quantity or pos["quantity"],
            exit_price=None,  # Will be filled after order execution
            realized_pnl=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")


@router.post("/close-all")
async def close_all_positions():
    """
    Close all open positions.

    WARNING: This will sell all shares in all positions.
    """
    alpaca = get_alpaca_service()

    try:
        orders = await alpaca.close_all_positions()

        # Clear database positions
        db = SessionLocal()
        db.query(DBPosition).delete()
        db.commit()
        db.close()

        return {
            "success": True,
            "message": "All positions closed",
            "orders": orders,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close all positions: {str(e)}")
