"""
Bot Control API Routes
Endpoints for starting, stopping, and monitoring the trading bot
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from ..models.bot import (
    BotStatusResponse,
    BotStartRequest,
    BotActionResponse,
    BotState,
)
from ..services.trading_bot import get_trading_bot

router = APIRouter()


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status():
    """
    Get current trading bot status.

    Returns bot state, uptime, last trade time, and current activity.
    """
    bot = get_trading_bot()
    status = bot.get_status()

    return BotStatusResponse(
        state=BotState(status["state"]),
        uptime_seconds=status["uptime_seconds"],
        last_trade_time=status["last_trade_time"],
        current_cycle=status["current_cycle"],
        error_message=status["error_message"],
        paper_trading=status["paper_trading"],
        active_symbols=status["active_symbols"],
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
