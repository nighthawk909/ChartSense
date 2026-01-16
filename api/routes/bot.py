"""
Bot Control API Routes
Endpoints for starting, stopping, and monitoring the trading bot
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from models.bot import (
    BotStatusResponse,
    BotStartRequest,
    BotActionResponse,
    BotState,
    CryptoAnalysisResult,
    CryptoScanProgress,
    CryptoBestOpportunity,
)
from services.trading_bot import get_trading_bot

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

    return BotStatusResponse(
        state=BotState(status["state"]),
        uptime_seconds=status["uptime_seconds"],
        last_trade_time=status["last_trade_time"],
        current_cycle=status["current_cycle"],
        current_session=status.get("current_session"),
        error_message=status["error_message"],
        paper_trading=status["paper_trading"],
        active_symbols=status["active_symbols"],
        crypto_trading_enabled=status.get("crypto_trading_enabled", False),
        crypto_symbols=status.get("crypto_symbols", []),
        crypto_positions=status.get("crypto_positions", 0),
        crypto_analysis_results=crypto_results,
        last_crypto_analysis_time=status.get("last_crypto_analysis_time"),
        crypto_scan_progress=scan_progress,
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
