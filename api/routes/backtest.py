"""
API routes for backtesting.

Provides endpoints to run backtests and view results.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from models.backtest import (
    BacktestRequest,
    BacktestResult,
    StrategyInfo,
)
from services.backtesting.engine import run_backtest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResult)
async def run_backtest_endpoint(request: BacktestRequest):
    """
    Run a backtest with the specified configuration.

    Example request:
    ```json
    {
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "initial_capital": 100000,
        "strategy": "simple_rsi",
        "strategy_params": {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70
        },
        "position_size_pct": 10.0
    }
    ```
    """
    try:
        logger.info(f"Starting backtest: {request.strategy} on {len(request.symbols)} symbols")
        result = await run_backtest(request)
        logger.info(f"Backtest complete: {result.metrics.total_return_pct:.1f}% return")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/strategies", response_model=List[StrategyInfo])
async def list_strategies():
    """
    List all available backtestable strategies.

    Returns information about each strategy including default parameters.
    """
    return [
        StrategyInfo(
            id="simple_rsi",
            name="Simple RSI",
            description="Mean-reversion strategy. Buy when RSI < oversold, sell when RSI > overbought.",
            default_params={
                "rsi_period": 14,
                "oversold": 30,
                "overbought": 70,
            }
        ),
        StrategyInfo(
            id="macd_crossover",
            name="MACD Crossover",
            description="Trend-following strategy. Buy on bullish MACD crossover, sell on bearish crossover.",
            default_params={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
            }
        ),
    ]


@router.get("/health")
async def backtest_health():
    """Health check for backtest service."""
    return {"status": "healthy", "service": "backtest"}
