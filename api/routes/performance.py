"""
Performance API Routes
Endpoints for viewing trading performance and history
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from models.bot import (
    PerformanceSummary,
    PerformanceMetrics,
    EquityCurvePoint,
    EquityCurveResponse,
    TradeResponse,
    TradeHistoryResponse,
    OrderSide,
    ExitReason,
    TradeType,
    OptimizationLogEntry,
    OptimizationHistoryResponse,
)
from services.performance_tracker import PerformanceTracker, SelfOptimizer
from services.alpaca_service import get_alpaca_service
from database.connection import SessionLocal
from database.models import Trade, OptimizationLog

router = APIRouter()


@router.get("/summary", response_model=PerformanceSummary)
async def get_performance_summary(period_days: int = Query(30, ge=1, le=365)):
    """
    Get quick performance summary.

    Args:
        period_days: Number of days to analyze (default 30)
    """
    tracker = PerformanceTracker()
    metrics = tracker.calculate_metrics(period_days)

    return PerformanceSummary(
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        win_rate=metrics.win_rate,
        total_pnl=metrics.total_pnl,
        total_pnl_pct=metrics.total_pnl_pct,
    )


@router.get("/metrics", response_model=PerformanceMetrics)
async def get_detailed_metrics(period_days: int = Query(30, ge=1, le=365)):
    """
    Get detailed performance metrics.

    Includes win rate, profit factor, Sharpe ratio, max drawdown, and more.

    Args:
        period_days: Number of days to analyze (default 30)
    """
    tracker = PerformanceTracker()
    metrics = tracker.calculate_metrics(period_days)

    return PerformanceMetrics(
        period_days=metrics.period_days,
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        win_rate=metrics.win_rate,
        total_pnl=metrics.total_pnl,
        total_pnl_pct=metrics.total_pnl_pct,
        profit_factor=metrics.profit_factor,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown=metrics.max_drawdown,
        max_drawdown_pct=metrics.max_drawdown_pct,
        avg_win=metrics.avg_win,
        avg_loss=metrics.avg_loss,
        avg_trade_duration_hours=metrics.avg_trade_duration_hours,
        best_trade=metrics.best_trade,
        worst_trade=metrics.worst_trade,
        swing_trades=metrics.swing_trades,
        swing_win_rate=metrics.swing_win_rate,
        longterm_trades=metrics.longterm_trades,
        longterm_win_rate=metrics.longterm_win_rate,
    )


@router.get("/equity-curve", response_model=EquityCurveResponse)
async def get_equity_curve(period_days: int = Query(30, ge=1, le=365)):
    """
    Get equity curve data for charting.

    Returns chronological list of equity values and P&L.

    Args:
        period_days: Number of days to include (default 30)
    """
    tracker = PerformanceTracker()
    curve_data = tracker.get_equity_curve(period_days)

    # Get starting equity from Alpaca
    alpaca = get_alpaca_service()
    try:
        account = await alpaca.get_account()
        current_equity = account["equity"]
    except:
        current_equity = 0

    # Calculate starting equity and total return
    total_pnl = sum(p["pnl"] for p in curve_data)
    starting_equity = current_equity - total_pnl
    total_return_pct = (total_pnl / starting_equity * 100) if starting_equity > 0 else 0

    data = [
        EquityCurvePoint(
            date=datetime.fromisoformat(p["date"]) if p["date"] else datetime.now(),
            equity=starting_equity + p["cumulative_pnl"],
            pnl=p["pnl"],
            cumulative_pnl=p["cumulative_pnl"],
        )
        for p in curve_data
    ]

    return EquityCurveResponse(
        data=data,
        starting_equity=starting_equity,
        current_equity=current_equity,
        total_return_pct=total_return_pct,
    )


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Get paginated trade history.

    Args:
        page: Page number (default 1)
        page_size: Number of trades per page (default 20)
    """
    tracker = PerformanceTracker()
    offset = (page - 1) * page_size

    trades, total_count = tracker.get_trade_history(limit=page_size, offset=offset)

    trade_responses = [
        TradeResponse(
            id=t.id,
            symbol=t.symbol,
            side=OrderSide(t.side),
            quantity=t.quantity,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            entry_time=t.entry_time,
            exit_time=t.exit_time,
            profit_loss=t.profit_loss,
            profit_loss_pct=t.profit_loss_pct,
            exit_reason=ExitReason(t.exit_reason) if t.exit_reason else None,
            trade_type=TradeType(t.trade_type) if t.trade_type else None,
            entry_score=t.entry_score,
        )
        for t in trades
    ]

    return TradeHistoryResponse(
        trades=trade_responses,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/trades/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int):
    """
    Get a specific trade by ID.
    """
    db = SessionLocal()
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    db.close()

    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    return TradeResponse(
        id=trade.id,
        symbol=trade.symbol,
        side=OrderSide(trade.side),
        quantity=trade.quantity,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        entry_time=trade.entry_time,
        exit_time=trade.exit_time,
        profit_loss=trade.profit_loss,
        profit_loss_pct=trade.profit_loss_pct,
        exit_reason=ExitReason(trade.exit_reason) if trade.exit_reason else None,
        trade_type=TradeType(trade.trade_type) if trade.trade_type else None,
        entry_score=trade.entry_score,
    )


@router.get("/optimization-history", response_model=OptimizationHistoryResponse)
async def get_optimization_history(limit: int = Query(20, ge=1, le=100)):
    """
    Get history of self-optimization changes.
    """
    db = SessionLocal()
    logs = db.query(OptimizationLog).order_by(
        OptimizationLog.timestamp.desc()
    ).limit(limit).all()
    db.close()

    entries = [
        OptimizationLogEntry(
            timestamp=log.timestamp,
            parameter=log.parameter_name,
            old_value=log.old_value,
            new_value=log.new_value,
            reason=log.reason,
            applied=log.applied,
        )
        for log in logs
    ]

    return OptimizationHistoryResponse(
        entries=entries,
        total_adjustments=len(entries),
    )


@router.post("/optimize")
async def trigger_optimization():
    """
    Manually trigger self-optimization cycle.

    Analyzes recent performance and applies parameter adjustments.
    """
    optimizer = SelfOptimizer()
    result = optimizer.run_optimization_cycle()

    return result
