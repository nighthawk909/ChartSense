"""
Bot Control API Routes
Endpoints for starting, stopping, and monitoring the trading bot
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from fastapi import Query
from datetime import datetime, timedelta

from models.bot import (
    BotStatusResponse,
    BotStartRequest,
    BotActionResponse,
    BotState,
    CryptoAnalysisResult,
    CryptoScanProgress,
    CryptoBestOpportunity,
    StockScanProgress,
    StockBestOpportunity,
    StockAnalysisResult,
    ExecutionLogEntry,
    AIDecisionResult,
)
from services.trading_bot import get_trading_bot
from services.performance_tracker import PerformanceTracker
from services.alpaca_service import get_alpaca_service

router = APIRouter()


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status():
    """
    Get current trading bot status.

    Returns bot state, uptime, last trade time, and current activity.
    """
    bot = get_trading_bot()
    status = bot.get_status()

    # Convert crypto analysis results to Pydantic models
    crypto_results = {}
    for symbol, result in status.get("crypto_analysis_results", {}).items():
        crypto_results[symbol] = CryptoAnalysisResult(
            signal=result.get("signal", "NEUTRAL"),
            confidence=result.get("confidence", 0),
            threshold=result.get("threshold", 70),
            meets_threshold=result.get("meets_threshold", False),
            reason=result.get("reason", ""),
            timestamp=result.get("timestamp", ""),
            indicators=result.get("indicators", {}),
            signals=result.get("signals", []),
        )

    # Build crypto scan progress if available
    scan_progress = None
    raw_progress = status.get("crypto_scan_progress")
    if raw_progress:
        best_opp = None
        if raw_progress.get("best_opportunity"):
            best_opp = CryptoBestOpportunity(**raw_progress["best_opportunity"])
        scan_progress = CryptoScanProgress(
            total=raw_progress.get("total", 0),
            scanned=raw_progress.get("scanned", 0),
            current_symbol=raw_progress.get("current_symbol"),
            signals_found=raw_progress.get("signals_found", 0),
            best_opportunity=best_opp,
            scan_status=raw_progress.get("scan_status", "idle"),
            scan_summary=raw_progress.get("scan_summary", ""),
            last_scan_completed=raw_progress.get("last_scan_completed"),
            next_scan_in_seconds=raw_progress.get("next_scan_in_seconds", 0),
        )

    # Build stock scan progress if available
    stock_scan_progress = None
    raw_stock_progress = status.get("stock_scan_progress")
    if raw_stock_progress:
        stock_best_opp = None
        if raw_stock_progress.get("best_opportunity"):
            stock_best_opp = StockBestOpportunity(**raw_stock_progress["best_opportunity"])
        stock_scan_progress = StockScanProgress(
            total=raw_stock_progress.get("total", 0),
            scanned=raw_stock_progress.get("scanned", 0),
            current_symbol=raw_stock_progress.get("current_symbol"),
            signals_found=raw_stock_progress.get("signals_found", 0),
            best_opportunity=stock_best_opp,
            scan_status=raw_stock_progress.get("scan_status", "idle"),
            scan_summary=raw_stock_progress.get("scan_summary", ""),
            last_scan_completed=raw_stock_progress.get("last_scan_completed"),
            next_scan_in_seconds=raw_stock_progress.get("next_scan_in_seconds", 0),
            market_status=raw_stock_progress.get("market_status", "unknown"),
        )

    # Convert stock analysis results to Pydantic models (similar to crypto)
    stock_results = {}
    for symbol, result in status.get("stock_analysis_results", {}).items():
        stock_results[symbol] = StockAnalysisResult(
            signal=result.get("signal", "NEUTRAL"),
            confidence=result.get("confidence", 0),
            threshold=result.get("threshold", 70),
            meets_threshold=result.get("meets_threshold", False),
            reason=result.get("reason", ""),
            timestamp=result.get("timestamp", ""),
            indicators=result.get("indicators", {}),
            current_price=result.get("current_price"),
            trade_type=result.get("trade_type"),
        )

    # Convert execution log entries to Pydantic models
    execution_log_entries = []
    for entry in status.get("execution_log", []):
        execution_log_entries.append(ExecutionLogEntry(
            timestamp=entry.get("timestamp", ""),
            symbol=entry.get("symbol", ""),
            event_type=entry.get("event_type", "UNKNOWN"),
            executed=entry.get("executed", False),
            reason=entry.get("reason", ""),
            details=entry.get("details", {}),
        ))

    # Convert AI decisions to Pydantic models
    ai_decisions = []
    for decision in status.get("ai_decisions_history", []):
        ai_decisions.append(AIDecisionResult(
            decision=decision.get("decision", "WAIT"),
            confidence=decision.get("confidence", 0),
            reasoning=decision.get("reasoning", ""),
            concerns=decision.get("concerns", []),
            timestamp=decision.get("timestamp", ""),
            symbol=decision.get("symbol", ""),
            ai_generated=decision.get("ai_generated", True),
            model=decision.get("model", "gpt-4"),
            technical_score=decision.get("technical_score", 0),
            technical_signal=decision.get("technical_signal", ""),
        ))

    return BotStatusResponse(
        state=BotState(status["state"]),
        uptime_seconds=status["uptime_seconds"],
        last_trade_time=status["last_trade_time"],
        current_cycle=status["current_cycle"],
        current_session=status.get("current_session"),
        error_message=status["error_message"],
        paper_trading=status["paper_trading"],
        active_symbols=status["active_symbols"],
        asset_class_mode=status.get("asset_class_mode", "both"),
        # Auto Trade Mode
        auto_trade_mode=status.get("auto_trade_mode", False),
        ai_risk_tolerance=status.get("ai_risk_tolerance", "moderate"),
        # Entry threshold
        entry_threshold=status.get("entry_threshold", 65.0),
        crypto_trading_enabled=status.get("crypto_trading_enabled", False),
        crypto_symbols=status.get("crypto_symbols", []),
        crypto_max_positions=status.get("crypto_max_positions", 5),
        crypto_positions=status.get("crypto_positions", 0),
        crypto_analysis_results=crypto_results,
        last_crypto_analysis_time=status.get("last_crypto_analysis_time"),
        crypto_scan_progress=scan_progress,
        stock_scan_progress=stock_scan_progress,
        stock_analysis_results=stock_results,
        last_stock_analysis_time=status.get("last_stock_analysis_time"),
        # Tactical Controls
        new_entries_paused=status.get("new_entries_paused", False),
        strategy_override=status.get("strategy_override"),
        # Execution tracking
        execution_log=execution_log_entries,
        ai_decisions_history=ai_decisions,
        total_scans_today=status.get("total_scans_today", 0),
    )


@router.post("/start", response_model=BotActionResponse)
async def start_bot(
    background_tasks: BackgroundTasks,
    request: Optional[BotStartRequest] = None
):
    """
    Start the trading bot.

    Optionally override paper trading mode and enabled symbols.
    The bot runs in the background and can be monitored via /status.
    """
    bot = get_trading_bot()

    if bot.state.value == "RUNNING":
        return BotActionResponse(
            success=False,
            message="Bot is already running",
            state=BotState.RUNNING,
        )

    # Prepare config
    config = {}
    if request:
        if request.paper_trading is not None:
            config["paper_trading"] = request.paper_trading
        if request.symbols:
            config["enabled_symbols"] = request.symbols

    # Start in background
    background_tasks.add_task(bot.start, config if config else None)

    return BotActionResponse(
        success=True,
        message="Bot starting...",
        state=BotState.RUNNING,
    )


@router.post("/stop", response_model=BotActionResponse)
async def stop_bot(background_tasks: BackgroundTasks):
    """
    Stop the trading bot.

    Stops the trading loop but keeps existing positions open.
    Use /positions/close-all to close all positions.
    """
    bot = get_trading_bot()

    if bot.state.value == "STOPPED":
        return BotActionResponse(
            success=False,
            message="Bot is already stopped",
            state=BotState.STOPPED,
        )

    background_tasks.add_task(bot.stop)

    return BotActionResponse(
        success=True,
        message="Bot stopping...",
        state=BotState.STOPPED,
    )


@router.post("/pause", response_model=BotActionResponse)
async def pause_bot(background_tasks: BackgroundTasks):
    """
    Pause the trading bot.

    Pauses trading (no new positions) but continues monitoring existing positions.
    """
    bot = get_trading_bot()

    if bot.state.value != "RUNNING":
        return BotActionResponse(
            success=False,
            message="Bot is not running",
            state=BotState(bot.state.value),
        )

    background_tasks.add_task(bot.pause)

    return BotActionResponse(
        success=True,
        message="Bot pausing...",
        state=BotState.PAUSED,
    )


@router.post("/resume", response_model=BotActionResponse)
async def resume_bot(background_tasks: BackgroundTasks):
    """
    Resume the trading bot from paused state.
    """
    bot = get_trading_bot()

    if bot.state.value != "PAUSED":
        return BotActionResponse(
            success=False,
            message="Bot is not paused",
            state=BotState(bot.state.value),
        )

    background_tasks.add_task(bot.resume)

    return BotActionResponse(
        success=True,
        message="Bot resuming...",
        state=BotState.RUNNING,
    )


@router.get("/health")
async def bot_health():
    """
    Check bot health and connectivity.
    """
    bot = get_trading_bot()

    try:
        # Try to get account info
        account = await bot.alpaca.get_account()
        market_open = await bot.alpaca.is_market_open()

        return {
            "status": "healthy",
            "bot_state": bot.state.value,
            "alpaca_connected": True,
            "market_open": market_open,
            "account_equity": account["equity"],
            "buying_power": account["buying_power"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "bot_state": bot.state.value,
            "alpaca_connected": False,
            "error": str(e),
        }


@router.get("/execution-log")
async def get_execution_log(symbol: str = None, limit: int = 20):
    """
    Get execution log for debugging paper trade failures.

    Shows why trades were or weren't executed.
    """
    bot = get_trading_bot()
    return {
        "log": bot.get_execution_log(symbol=symbol, limit=limit),
        "total_entries": len(bot._execution_log),
    }


@router.get("/strong-buy-trace")
async def get_strong_buy_trace(limit: int = 5):
    """
    Get trace of last N 'Strong Buy' signals to diagnose execution failures.

    Paper Trading Troubleshooting:
    1. Balance & Allocation: Check if paper account has enough buying power
    2. Order Type Mismatch: Check if AI is sending market orders when limit required
    3. Spread Filter: Check if spread threshold is too tight
    4. Signal Expiry: Check if signals are stale by execution time
    5. API Permissions: Ensure paper trading API keys have trade permission
    """
    bot = get_trading_bot()
    return {
        "trace": bot.get_strong_buy_trace(limit=limit),
        "troubleshooting_tips": [
            "Check buying power vs minimum position size",
            "Verify order type matches asset class requirements",
            "Check if bid/ask spread is within threshold",
            "Ensure signal isn't expired before execution",
            "Confirm API keys have trading permissions enabled",
        ]
    }


@router.post("/pause-entries")
async def toggle_pause_entries():
    """
    Toggle pause on new position entries.

    When paused, bot continues monitoring existing positions but won't open new ones.
    """
    bot = get_trading_bot()
    bot.new_entries_paused = not bot.new_entries_paused

    return {
        "success": True,
        "new_entries_paused": bot.new_entries_paused,
        "message": "New entries paused" if bot.new_entries_paused else "New entries resumed",
    }


@router.post("/strategy-override")
async def set_strategy_override(strategy: str = None):
    """
    Override the trading strategy.

    Args:
        strategy: 'conservative', 'moderate', 'aggressive', or None to reset
    """
    bot = get_trading_bot()

    valid_strategies = ['conservative', 'moderate', 'aggressive', None, 'none']
    if strategy not in valid_strategies:
        raise HTTPException(status_code=400, detail=f"Invalid strategy. Use: {valid_strategies}")

    if strategy == 'none':
        strategy = None

    bot.strategy_override = strategy

    # Apply the strategy preset if not None
    if strategy:
        bot._apply_ai_risk_preset(strategy)

    return {
        "success": True,
        "strategy_override": bot.strategy_override,
        "message": f"Strategy set to {strategy}" if strategy else "Strategy reset to default",
    }


@router.post("/auto-trade")
async def toggle_auto_trade(enabled: bool = None):
    """
    Enable or disable automatic trade execution.

    When enabled, the bot will automatically execute trades when signals meet thresholds.
    When disabled, the bot will only detect signals and report them (manual trade approval required).

    Args:
        enabled: True to enable auto-trading, False to disable. If None, toggles current state.
    """
    from database.connection import SessionLocal
    from database.models import BotConfiguration
    from datetime import datetime

    bot = get_trading_bot()

    if enabled is None:
        # Toggle mode
        bot.auto_trade_mode = not bot.auto_trade_mode
    else:
        bot.auto_trade_mode = enabled

    # Persist to database so it survives bot restarts
    try:
        db = SessionLocal()
        config = db.query(BotConfiguration).filter(BotConfiguration.is_active == True).first()
        if config:
            config.auto_trade_mode = bot.auto_trade_mode
            config.updated_at = datetime.now()
            db.commit()
        db.close()
    except Exception as e:
        # Log but don't fail - the in-memory setting is still active
        import logging
        logging.getLogger(__name__).warning(f"Failed to persist auto_trade_mode to database: {e}")

    return {
        "success": True,
        "auto_trade_mode": bot.auto_trade_mode,
        "message": f"Auto-trade mode {'enabled' if bot.auto_trade_mode else 'disabled'}. " +
                   ("Bot will now automatically execute trades when signals meet thresholds." if bot.auto_trade_mode
                    else "Bot will only detect signals. Manual trade approval required."),
    }


@router.get("/auto-trade")
async def get_auto_trade_status():
    """
    Get current auto-trade mode status.
    """
    bot = get_trading_bot()

    return {
        "auto_trade_mode": bot.auto_trade_mode,
        "ai_risk_tolerance": getattr(bot, 'ai_risk_tolerance', 'moderate'),
        "message": "Auto-trade is " + ("enabled" if bot.auto_trade_mode else "disabled"),
    }


@router.post("/emergency-close-all")
async def emergency_close_all():
    """
    Emergency close all positions immediately.

    WARNING: This will close ALL open positions at market price.
    """
    bot = get_trading_bot()

    try:
        positions = await bot.alpaca.get_positions()
        closed_count = 0

        for pos in positions:
            symbol = pos.get("symbol")
            try:
                await bot.alpaca.close_position(symbol)
                closed_count += 1
                bot._log_execution_event(
                    symbol=symbol,
                    event_type="EMERGENCY_CLOSE",
                    executed=True,
                    reason="Emergency close all triggered by user",
                    details={"quantity": pos.get("qty"), "price": pos.get("current_price")}
                )
            except Exception as e:
                bot._log_execution_event(
                    symbol=symbol,
                    event_type="EMERGENCY_CLOSE_FAILED",
                    executed=False,
                    reason=str(e),
                )

        return {
            "success": True,
            "positions_closed": closed_count,
            "message": f"Closed {closed_count} positions",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/priority-tiers")
async def get_priority_tiers():
    """
    Get current priority tier distribution for symbols.

    Shows which symbols are in HIGH/STANDARD/LOW priority tiers.
    """
    bot = get_trading_bot()
    return {
        "summary": bot.priority_scanner.get_tier_summary(),
        "symbols": bot.priority_scanner.get_all_priorities(),
    }


@router.post("/asset-class-mode")
async def set_asset_class_mode(mode: str):
    """
    Set the asset class mode for hybrid scanning.

    Args:
        mode: 'crypto' for crypto only, 'stocks' for stocks only, 'both' for hybrid

    When set to 'both' (hybrid mode):
    - Stocks are scanned during regular market hours
    - Crypto is scanned 24/7
    - Both asset classes are monitored when market is open
    """
    bot = get_trading_bot()

    valid_modes = ['crypto', 'stocks', 'both']
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Use: {valid_modes}")

    old_mode = bot.asset_class_mode
    bot.asset_class_mode = mode

    # Enable/disable crypto based on mode
    if mode == 'crypto':
        bot.crypto_trading_enabled = True
    elif mode == 'stocks':
        bot.crypto_trading_enabled = False
    else:  # both
        bot.crypto_trading_enabled = True

    return {
        "success": True,
        "previous_mode": old_mode,
        "asset_class_mode": bot.asset_class_mode,
        "crypto_trading_enabled": bot.crypto_trading_enabled,
        "message": f"Asset class mode set to '{mode}'",
    }


@router.get("/scan-progress")
async def get_scan_progress():
    """
    Get current scan progress for both stocks and crypto.

    Returns real-time scan status, current symbol being analyzed,
    best opportunities found, and market status.
    """
    bot = get_trading_bot()

    return {
        "asset_class_mode": bot.asset_class_mode,
        "stock_scan_progress": bot._stock_scan_progress,
        "crypto_scan_progress": bot._crypto_scan_progress,
        "current_session": bot.current_session,
        "current_cycle": bot.current_cycle,
        "total_scans_today": bot._total_scans_today,
    }


@router.get("/activity")
async def get_bot_activity():
    """
    Get recent bot activity log.

    Returns recent actions, decisions, and events from the trading bot.
    """
    bot = get_trading_bot()

    # Get activity log if available
    activity_log = getattr(bot, 'activity_log', [])

    # Build activity from available data
    activities = []

    # Add current cycle as activity
    status = bot.get_status()
    if status["current_cycle"]:
        activities.append({
            "timestamp": status["last_trade_time"] or None,
            "type": "cycle",
            "message": f"Current: {status['current_cycle'].replace('_', ' ').title()}",
            "level": "info"
        })

    # Add state info
    activities.append({
        "timestamp": None,
        "type": "state",
        "message": f"Bot is {status['state']}",
        "level": "info" if status["state"] in ["RUNNING", "PAUSED"] else "warning" if status["state"] == "STOPPED" else "error"
    })

    # Add market hours check
    try:
        market_open = await bot.alpaca.is_market_open()
        activities.append({
            "timestamp": None,
            "type": "market",
            "message": f"Stock market is {'OPEN' if market_open else 'CLOSED'}",
            "level": "info" if market_open else "warning"
        })
    except:
        pass

    # Add watching symbols
    if status["active_symbols"]:
        activities.append({
            "timestamp": None,
            "type": "symbols",
            "message": f"Watching: {', '.join(status['active_symbols'][:5])}{'...' if len(status['active_symbols']) > 5 else ''}",
            "level": "info"
        })

    # Add error if present
    if status["error_message"]:
        activities.append({
            "timestamp": None,
            "type": "error",
            "message": status["error_message"],
            "level": "error"
        })

    # Add uptime info
    if status["uptime_seconds"] > 0:
        hours = int(status["uptime_seconds"] // 3600)
        minutes = int((status["uptime_seconds"] % 3600) // 60)
        activities.append({
            "timestamp": None,
            "type": "uptime",
            "message": f"Running for {hours}h {minutes}m",
            "level": "info"
        })

    return {
        "activities": activities,
        "total_count": len(activities),
    }


@router.get("/diagnostic")
async def run_diagnostic():
    """
    Run comprehensive system diagnostic.

    Checks:
    - API connections (Alpaca, Alpha Vantage)
    - Chart data freshness (1m timestamps)
    - System time sync
    - Account status and permissions

    Returns detailed diagnostic report with pass/fail status for each check.
    """
    from scripts.diagnostic import ChartSenseDiagnostic

    diagnostic = ChartSenseDiagnostic(verbose=False)
    await diagnostic.run_all_checks()

    # Convert results to response format
    results = []
    for r in diagnostic.results:
        results.append({
            "name": r.name,
            "passed": r.passed,
            "message": r.message,
            "details": r.details,
            "timestamp": r.timestamp,
        })

    passed = sum(1 for r in diagnostic.results if r.passed)
    failed = sum(1 for r in diagnostic.results if not r.passed)

    return {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "health": "healthy" if failed == 0 else "degraded" if failed < 3 else "unhealthy",
        },
        "results": results,
        "critical_failures": [
            {"name": r.name, "message": r.message}
            for r in diagnostic.results
            if not r.passed and r.name in [
                "Alpaca API Connection",
                "Alpaca Account",
                "Stock 1m Chart Timestamp",
                "Crypto 1m Chart Timestamp",
            ]
        ],
    }


@router.get("/execution-errors")
async def get_execution_errors():
    """
    Get detailed execution error summary from the ExecutionLogger.

    Returns error codes, frequency, and recent failures to help
    diagnose why trades aren't executing.
    """
    bot = get_trading_bot()

    error_summary = bot.execution_logger.get_error_summary()
    recent_failures = bot.execution_logger.get_recent_attempts(success_only=False, limit=20)
    diagnosis = bot.execution_logger.diagnose_failures()

    return {
        "error_summary": error_summary,
        "recent_failures": [
            {
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "symbol": a.symbol,
                "side": a.side,
                "quantity": a.quantity,
                "price": a.price,
                "success": a.success,
                "error_code": a.error_code.value if a.error_code else None,
                "error_message": a.error_message,
            }
            for a in recent_failures
        ],
        "diagnosis": diagnosis,
    }


# ============== Performance Endpoints (under /api/bot/performance/) ==============

@router.get("/performance/metrics")
async def get_performance_metrics(period: str = Query("1M")):
    """
    Get detailed trading performance metrics.

    Endpoint: /api/bot/performance/metrics

    Args:
        period: Time period - '1D', '1W', '1M', '3M', 'ALL'

    Returns comprehensive metrics including:
    - Win rate, profit factor, Sharpe ratio
    - Max drawdown, expectancy
    - Today's P&L and performance
    """
    # Convert period to days
    period_map = {
        '1D': 1,
        '1W': 7,
        '1M': 30,
        '3M': 90,
        'ALL': 365,
    }
    period_days = period_map.get(period, 30)

    tracker = PerformanceTracker()
    metrics = tracker.calculate_metrics(period_days)

    # Calculate today's metrics separately
    today_tracker = PerformanceTracker()
    today_metrics = today_tracker.calculate_metrics(1)

    return {
        "period": period,
        "period_days": period_days,
        "total_trades": metrics.total_trades,
        "winning_trades": metrics.winning_trades,
        "losing_trades": metrics.losing_trades,
        "win_rate": metrics.win_rate * 100,  # Convert to percentage
        "total_pnl": metrics.total_pnl,
        "total_pnl_pct": metrics.total_pnl_pct,
        "profit_factor": metrics.profit_factor if metrics.profit_factor != float('inf') else 999.99,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "avg_win": metrics.avg_win,
        "avg_loss": metrics.avg_loss,
        "avg_trade_duration_hours": metrics.avg_trade_duration_hours,
        "best_trade": metrics.best_trade,
        "worst_trade": metrics.worst_trade,
        "expectancy": (metrics.avg_win * metrics.win_rate - abs(metrics.avg_loss) * (1 - metrics.win_rate)) if metrics.total_trades > 0 else 0,
        # Today's performance
        "today_pnl": today_metrics.total_pnl,
        "today_trades": today_metrics.total_trades,
        "today_win_rate": today_metrics.win_rate * 100 if today_metrics.total_trades > 0 else 0,
        # By trade type
        "swing_trades": metrics.swing_trades,
        "swing_win_rate": metrics.swing_win_rate * 100,
        "longterm_trades": metrics.longterm_trades,
        "longterm_win_rate": metrics.longterm_win_rate * 100,
    }


@router.get("/performance/equity-curve")
async def get_equity_curve(period: str = Query("1M")):
    """
    Get equity curve data for charting.

    Endpoint: /api/bot/performance/equity-curve

    Args:
        period: Time period - '1D', '1W', '1M', '3M', 'ALL'

    Returns list of equity points for drawing the portfolio equity curve.
    """
    # Convert period to days
    period_map = {
        '1D': 1,
        '1W': 7,
        '1M': 30,
        '3M': 90,
        'ALL': 365,
    }
    period_days = period_map.get(period, 30)

    tracker = PerformanceTracker()
    curve_data = tracker.get_equity_curve(period_days)

    # Get current equity from Alpaca
    alpaca = get_alpaca_service()
    try:
        account = await alpaca.get_account()
        current_equity = float(account.get("equity", 0))
    except Exception:
        current_equity = 10000  # Default for paper trading

    # Calculate starting equity
    total_pnl = sum(p["pnl"] for p in curve_data) if curve_data else 0
    starting_equity = current_equity - total_pnl

    # Format data for frontend
    data = []
    for point in curve_data:
        equity_value = starting_equity + point["cumulative_pnl"]
        data.append({
            "date": point["date"],
            "equity": equity_value,
            "pnl": point["pnl"],
            "cumulativePnl": point["cumulative_pnl"],
        })

    return {
        "data": data,
        "starting_equity": starting_equity,
        "current_equity": current_equity,
        "total_return_pct": (total_pnl / starting_equity * 100) if starting_equity > 0 else 0,
    }


@router.get("/performance/summary")
async def get_performance_summary():
    """
    Get quick performance summary for the bot header.

    Endpoint: /api/bot/performance/summary
    """
    tracker = PerformanceTracker()
    metrics = tracker.calculate_metrics(30)

    return {
        "win_rate": round(metrics.win_rate * 100, 1),
        "total_trades": metrics.total_trades,
        "total_pnl": round(metrics.total_pnl, 2),
        "profit_factor": round(metrics.profit_factor, 2) if metrics.profit_factor != float('inf') else "∞",
    }


# ===== HIERARCHICAL TRADING STRATEGY ENDPOINTS =====

@router.get("/hierarchical/status")
async def get_hierarchical_status():
    """
    Get the current status of the hierarchical trading strategy.

    Returns:
    - Current trading horizon (SWING, INTRADAY, SCALP)
    - Daily goal progress
    - Scan statistics
    - Best current opportunity

    Endpoint: /api/bot/hierarchical/status
    """
    bot = get_trading_bot()

    return {
        "enabled": bot.hierarchical_mode_enabled,
        "current_horizon": bot.current_trading_horizon.value if bot.current_trading_horizon else None,
        "daily_profit_target_pct": bot.daily_profit_target_pct,
        "scan_results": bot._hierarchical_scan_results,
        "smart_scanner_summary": bot.smart_scanner.get_scan_summary() if bot.smart_scanner else None,
    }


@router.post("/hierarchical/toggle")
async def toggle_hierarchical_mode(enabled: bool = Query(..., description="Enable or disable hierarchical mode")):
    """
    Enable or disable the hierarchical trading mode.

    When enabled:
    - Bot uses intelligent cascading: SWING -> INTRADAY -> SCALP
    - Adapts to market conditions automatically
    - Aims to find profitable opportunities every trading day

    When disabled:
    - Bot uses traditional single-mode scanning

    Endpoint: /api/bot/hierarchical/toggle?enabled=true
    """
    bot = get_trading_bot()
    bot.hierarchical_mode_enabled = enabled

    return {
        "success": True,
        "message": f"Hierarchical mode {'enabled' if enabled else 'disabled'}",
        "hierarchical_mode_enabled": bot.hierarchical_mode_enabled,
    }


@router.post("/hierarchical/set-daily-target")
async def set_daily_target(target_pct: float = Query(..., ge=0.1, le=5.0, description="Daily profit target percentage")):
    """
    Set the daily profit target for the hierarchical strategy.

    The bot will track progress toward this daily goal and adapt its
    trading horizon based on how close it is to achieving it.

    Args:
        target_pct: Daily profit target percentage (0.1% to 5.0%)

    Endpoint: /api/bot/hierarchical/set-daily-target?target_pct=0.5
    """
    bot = get_trading_bot()
    bot.daily_profit_target_pct = target_pct

    # Also update the smart scanner's strategy
    if bot.smart_scanner:
        bot.smart_scanner.strategy.daily_goal.target_profit_pct = target_pct

    return {
        "success": True,
        "message": f"Daily target set to {target_pct}%",
        "daily_profit_target_pct": target_pct,
    }


@router.get("/hierarchical/opportunities")
async def get_hierarchical_opportunities():
    """
    Get all current trading opportunities from the hierarchical scanner.

    Returns opportunities organized by horizon (SWING, INTRADAY, SCALP)
    with full analysis details including:
    - Pattern detection (Bull Flags, H&S, etc.)
    - Elliott Wave position
    - Multi-timeframe confluence
    - Entry/exit levels

    Endpoint: /api/bot/hierarchical/opportunities
    """
    bot = get_trading_bot()

    if not bot.smart_scanner:
        return {
            "error": "Smart scanner not initialized",
            "opportunities": [],
        }

    # Get all valid opportunities (not expired)
    all_opps = [
        {
            "symbol": opp.symbol,
            "horizon": opp.horizon.value,
            "quality": opp.quality.value,
            "overall_score": opp.overall_score,
            "trend_score": opp.trend_score,
            "momentum_score": opp.momentum_score,
            "pattern_score": opp.pattern_score,
            "volume_score": opp.volume_score,
            "multi_tf_score": opp.multi_tf_score,
            "direction": opp.direction,
            "entry_price": opp.entry_price,
            "stop_loss": opp.stop_loss,
            "target_1": opp.target_1,
            "target_2": opp.target_2,
            "risk_reward_ratio": opp.risk_reward_ratio,
            "patterns_detected": opp.patterns_detected,
            "elliott_wave": opp.elliott_wave,
            "confluence_factors": opp.confluence_factors,
            "warnings": opp.warnings,
            "valid_until": opp.valid_until.isoformat() if opp.valid_until else None,
        }
        for opp in bot.smart_scanner.all_opportunities
        if opp.valid_until and opp.valid_until > datetime.now()
    ]

    # Group by horizon
    by_horizon = {
        "SWING": [o for o in all_opps if o["horizon"] == "SWING"],
        "INTRADAY": [o for o in all_opps if o["horizon"] == "INTRADAY"],
        "SCALP": [o for o in all_opps if o["horizon"] == "SCALP"],
    }

    return {
        "total_opportunities": len(all_opps),
        "by_horizon": by_horizon,
        "best_opportunity": bot._hierarchical_scan_results.get("best_opportunity"),
    }


@router.post("/hierarchical/force-horizon")
async def force_trading_horizon(
    horizon: str = Query(..., description="Force a specific horizon: SWING, INTRADAY, or SCALP")
):
    """
    Force the bot to focus on a specific trading horizon.

    This overrides the automatic cascading logic and forces the bot to
    only look for opportunities in the specified horizon.

    Useful when you have strong conviction about market conditions.

    Args:
        horizon: SWING, INTRADAY, or SCALP

    Endpoint: /api/bot/hierarchical/force-horizon?horizon=SCALP
    """
    from services.hierarchical_strategy import TradingHorizon

    bot = get_trading_bot()

    horizon_upper = horizon.upper()
    if horizon_upper not in ["SWING", "INTRADAY", "SCALP"]:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {horizon}. Must be SWING, INTRADAY, or SCALP")

    # Map string to enum
    horizon_map = {
        "SWING": TradingHorizon.SWING,
        "INTRADAY": TradingHorizon.INTRADAY,
        "SCALP": TradingHorizon.SCALP,
    }

    bot.current_trading_horizon = horizon_map[horizon_upper]

    # Reset exhausted flags except for the forced horizon
    if bot.smart_scanner:
        for h in TradingHorizon:
            bot.smart_scanner.strategy.horizon_exhausted[h] = h != horizon_map[horizon_upper]

    return {
        "success": True,
        "message": f"Forced trading horizon to {horizon_upper}",
        "current_horizon": horizon_upper,
    }


@router.get("/hierarchical/daily-goal")
async def get_daily_goal_progress():
    """
    Get detailed progress toward the daily profit goal.

    Returns:
    - Target percentage
    - Achieved percentage
    - Trades taken today
    - Win/loss count
    - Best and worst trade
    - Horizons used today

    Endpoint: /api/bot/hierarchical/daily-goal
    """
    bot = get_trading_bot()

    if not bot.smart_scanner:
        return {
            "error": "Smart scanner not initialized",
            "daily_goal": None,
        }

    goal = bot.smart_scanner.strategy.daily_goal

    return {
        "date": goal.date,
        "target_pct": goal.target_profit_pct,
        "achieved_pct": goal.achieved_profit_pct,
        "progress_pct": (goal.achieved_profit_pct / goal.target_profit_pct * 100)
            if goal.target_profit_pct > 0 else 0,
        "goal_achieved": goal.goal_achieved,
        "trades_taken": goal.trades_taken,
        "wins": goal.wins,
        "losses": goal.losses,
        "win_rate": (goal.wins / goal.trades_taken * 100) if goal.trades_taken > 0 else 0,
        "best_trade_pct": goal.best_trade_pct,
        "worst_trade_pct": goal.worst_trade_pct,
        "horizons_used": goal.horizons_used,
    }
