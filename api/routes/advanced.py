"""
Advanced Analysis API Routes
Multi-timeframe, patterns, sentiment, calendar, backtesting
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from services.multi_timeframe import get_multi_timeframe_service
from services.pattern_recognition import get_pattern_service
from services.sentiment_analysis import get_sentiment_service
from services.calendar_service import get_calendar_service
from services.backtester import get_backtest_engine, StrategyType
from services.alpha_vantage import AlphaVantageService
from services.alpaca_service import get_alpaca_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Multi-Timeframe Analysis ====================

@router.get("/mtf/{symbol}")
async def multi_timeframe_analysis(symbol: str):
    """
    Perform multi-timeframe analysis on a stock.

    Analyzes daily and weekly timeframes to find confluence.
    Higher confluence = stronger signal.
    """
    mtf_service = get_multi_timeframe_service()
    result = await mtf_service.analyze_symbol(symbol)
    return result


# ==================== Pattern Recognition ====================

@router.get("/patterns/{symbol}")
async def detect_patterns(
    symbol: str,
    interval: str = Query("daily", description="Timeframe: 5min, 15min, 1hour, daily")
):
    """
    Detect chart patterns for a stock.

    Identifies patterns like:
    - Head & Shoulders
    - Double Top/Bottom
    - Triangles
    - Candlestick patterns (Doji, Hammer, Engulfing, etc.)
    """
    alpaca = get_alpaca_service()
    pattern_service = get_pattern_service()

    # Map frontend interval to Alpaca timeframe
    interval_map = {
        "5min": "5Min",
        "15min": "15Min",
        "1hour": "1Hour",
        "1h": "1Hour",
        "daily": "1Day",
        "1d": "1Day",
        "1D": "1Day",
    }
    timeframe = interval_map.get(interval, "1Day")

    # Adjust limit based on timeframe (more bars for intraday)
    limit_map = {
        "5Min": 500,   # ~2 days of 5min data
        "15Min": 400,  # ~5 days of 15min data
        "1Hour": 300,  # ~2 weeks of hourly data
        "1Day": 200,   # ~200 trading days
    }
    limit = limit_map.get(timeframe, 200)

    try:
        # Get historical data from Alpaca
        bars = await alpaca.get_bars(symbol.upper(), timeframe=timeframe, limit=limit)

        if not bars or len(bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol} ({len(bars) if bars else 0} bars)")

        # Extract OHLC data
        opens = [b["open"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]

        # Analyze patterns with timeframe-appropriate weighting
        result = pattern_service.analyze(opens, highs, lows, closes, timeframe=interval)
        result["symbol"] = symbol.upper()
        result["interval"] = interval
        result["timeframe"] = timeframe
        result["bars_analyzed"] = len(bars)
        result["current_price"] = closes[-1] if closes else None

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting patterns for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elliott-wave/{symbol}")
async def get_elliott_wave(symbol: str, interval: str = "1day"):
    """
    Get Elliott Wave analysis for a stock.

    Elliott Wave Theory identifies 5-wave impulse patterns and 3-wave corrective patterns.
    Returns current wave position, confidence, and Fibonacci-based price targets.

    Args:
        symbol: Stock symbol
        interval: Timeframe for analysis (5min, 15min, 1hour, 1day, 1week)
    """
    alpaca = get_alpaca_service()
    pattern_service = get_pattern_service()

    # Map interval to Alpaca timeframe format
    INTERVAL_MAP = {
        "1m": "1min",
        "1min": "1min",
        "5m": "5min",
        "5min": "5min",
        "15m": "15min",
        "15min": "15min",
        "1h": "1hour",
        "1hour": "1hour",
        "4h": "4hour",
        "4hour": "4hour",
        "1d": "1day",
        "1day": "1day",
        "daily": "1day",
        "1w": "1week",
        "1week": "1week",
        "weekly": "1week",
    }
    timeframe = INTERVAL_MAP.get(interval.lower(), "1day")

    try:
        # Get historical data from Alpaca (no rate limit issues)
        bars = await alpaca.get_bars(symbol.upper(), timeframe=timeframe, limit=200)

        if not bars or len(bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol} ({len(bars) if bars else 0} bars)")

        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]

        # Pass timeframe to Elliott Wave detection for adaptive pivot sizing
        elliott = pattern_service.detect_elliott_wave(highs, lows, closes, timeframe=timeframe)

        # Map timeframe to display name
        TIMEFRAME_DISPLAY = {
            "1min": "1 Minute",
            "5min": "5 Minute",
            "15min": "15 Minute",
            "1hour": "1 Hour",
            "4hour": "4 Hour",
            "1day": "Daily",
            "1week": "Weekly",
        }
        timeframe_display = TIMEFRAME_DISPLAY.get(timeframe, timeframe)

        if not elliott:
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "timeframe": timeframe,
                "timeframe_display": timeframe_display,
                "elliott_wave": None,
                "message": f"No clear Elliott Wave pattern detected on {timeframe_display} timeframe"
            }

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "timeframe": timeframe,
            "timeframe_display": timeframe_display,
            "elliott_wave": {
                "wave_count": elliott.wave_count,
                "wave_type": elliott.wave_type,
                "wave_degree": elliott.wave_degree,
                "direction": elliott.direction,
                "current_position": elliott.current_position,
                "confidence": elliott.confidence,
                "next_target": elliott.next_target,
                "description": elliott.description,
                "wave_points": elliott.wave_points,
                "timeframe": timeframe,
                "timeframe_display": timeframe_display,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting Elliott Wave for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/support-resistance/{symbol}")
async def get_support_resistance(symbol: str):
    """
    Get support and resistance levels for a stock.

    Identifies key price levels based on historical pivot points and price clustering.
    Returns levels sorted by strength.
    """
    alpaca = get_alpaca_service()
    pattern_service = get_pattern_service()

    try:
        # Get historical data from Alpaca (no rate limit issues)
        bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=200)

        if not bars or len(bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol} ({len(bars) if bars else 0} bars)")

        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]

        levels = pattern_service.detect_support_resistance(highs, lows, closes)
        current_price = closes[-1] if closes else 0

        # Separate support and resistance
        support_levels = [l for l in levels if l.level_type == "support"]
        resistance_levels = [l for l in levels if l.level_type == "resistance"]

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "support_levels": [
                {
                    "price": l.price,
                    "strength": l.strength,
                    "touches": l.touches,
                    "distance_pct": round(((current_price - l.price) / current_price) * 100, 2) if current_price else 0
                }
                for l in support_levels
            ],
            "resistance_levels": [
                {
                    "price": l.price,
                    "strength": l.strength,
                    "touches": l.touches,
                    "distance_pct": round(((l.price - current_price) / current_price) * 100, 2) if current_price else 0
                }
                for l in resistance_levels
            ],
            "nearest_support": support_levels[0].price if support_levels else None,
            "nearest_resistance": resistance_levels[0].price if resistance_levels else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting support/resistance for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend-lines/{symbol}")
async def get_trend_lines(symbol: str):
    """
    Get trend lines for a stock.

    Calculates support and resistance trend lines using linear regression on pivot points.
    """
    alpaca = get_alpaca_service()
    pattern_service = get_pattern_service()

    try:
        # Get historical data from Alpaca (no rate limit issues)
        bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=200)

        if not bars or len(bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol} ({len(bars) if bars else 0} bars)")

        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]
        dates = [b["timestamp"] for b in bars]

        trend_lines = pattern_service.detect_trend_lines(highs, lows, closes)

        return {
            "symbol": symbol.upper(),
            "current_price": closes[-1] if closes else 0,
            "trend_lines": [
                {
                    "type": tl.line_type,
                    "direction": tl.direction,
                    "slope": tl.slope,
                    "intercept": tl.intercept,
                    "strength": tl.strength,
                    "touches": tl.touches,
                    "start_date": dates[tl.start_index] if tl.start_index < len(dates) else None,
                    "end_date": dates[tl.end_index] if tl.end_index < len(dates) else None,
                    # Project current value based on latest index
                    "current_value": round(tl.slope * (len(closes) - 1) + tl.intercept, 2),
                }
                for tl in trend_lines
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting trend lines for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Sentiment Analysis ====================

@router.get("/sentiment/{symbol}")
async def get_sentiment(symbol: str):
    """
    Get sentiment analysis for a stock.

    Analyzes news articles and provides bullish/bearish sentiment score.
    """
    sentiment_service = get_sentiment_service()
    result = await sentiment_service.get_full_sentiment_report(symbol)
    return result


@router.get("/sentiment/news/{symbol}")
async def get_news_sentiment(symbol: str, limit: int = Query(10, ge=1, le=50)):
    """Get news sentiment breakdown for a stock"""
    sentiment_service = get_sentiment_service()
    return await sentiment_service.get_news_sentiment(symbol, limit)


@router.get("/market/fear-greed")
async def get_market_fear_greed():
    """Get overall market fear/greed index"""
    sentiment_service = get_sentiment_service()
    return await sentiment_service.get_market_fear_greed()


# ==================== Calendar & Events ====================

@router.get("/calendar/earnings")
async def get_earnings_calendar(
    symbol: Optional[str] = None,
    horizon: str = Query("3month", description="3month, 6month, or 12month")
):
    """Get upcoming earnings dates"""
    calendar_service = get_calendar_service()
    return await calendar_service.get_earnings_calendar(symbol, horizon)


@router.get("/calendar/earnings-risk/{symbol}")
async def check_earnings_risk(symbol: str):
    """
    Check if a stock has upcoming earnings.

    Returns risk level and recommendation for trading around earnings.
    """
    calendar_service = get_calendar_service()
    return await calendar_service.check_earnings_risk(symbol)


@router.get("/calendar/economic")
async def get_economic_calendar():
    """Get important economic events"""
    calendar_service = get_calendar_service()
    return await calendar_service.get_economic_calendar()


@router.get("/calendar/market-hours")
async def get_market_hours():
    """Get current market hours status for stocks and crypto"""
    calendar_service = get_calendar_service()
    return await calendar_service.get_market_hours_status()


# ==================== Backtesting ====================

class BacktestRequest(BaseModel):
    """Request for running a backtest"""
    symbol: str
    strategy: str
    initial_capital: float = 10000
    position_size_pct: float = 0.1
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10


@router.get("/backtest/strategies")
async def get_available_strategies():
    """Get list of available backtest strategies"""
    return {
        "strategies": [
            {
                "id": "rsi_oversold",
                "name": "RSI Oversold/Overbought",
                "description": "Buy when RSI < 30, sell when RSI > 70"
            },
            {
                "id": "macd_crossover",
                "name": "MACD Crossover",
                "description": "Buy on bullish MACD crossover, sell on bearish"
            },
            {
                "id": "golden_cross",
                "name": "Golden Cross",
                "description": "Buy when 50 SMA crosses above 200 SMA"
            },
            {
                "id": "bollinger_bounce",
                "name": "Bollinger Band Bounce",
                "description": "Buy at lower band, sell at upper band"
            },
            {
                "id": "momentum",
                "name": "Momentum",
                "description": "Buy when price momentum exceeds threshold"
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion",
                "description": "Buy when price deviates from 20 SMA"
            },
        ]
    }


@router.post("/backtest/run")
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest on historical data.

    Returns performance metrics including:
    - Total return
    - Win rate
    - Profit factor
    - Max drawdown
    - Sharpe ratio
    """
    av_service = AlphaVantageService()
    backtest_engine = get_backtest_engine()

    # Map strategy string to enum
    strategy_map = {
        "rsi_oversold": StrategyType.RSI_OVERSOLD,
        "macd_crossover": StrategyType.MACD_CROSSOVER,
        "golden_cross": StrategyType.GOLDEN_CROSS,
        "bollinger_bounce": StrategyType.BOLLINGER_BOUNCE,
        "momentum": StrategyType.MOMENTUM,
        "mean_reversion": StrategyType.MEAN_REVERSION,
    }

    strategy = strategy_map.get(request.strategy.lower())
    if not strategy:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")

    # Get historical data
    history = await av_service.get_history(request.symbol.upper(), "daily", "full")

    if not history or not history.data:
        raise HTTPException(status_code=404, detail=f"No data found for {request.symbol}")

    # Need at least 200 bars for proper backtesting
    if len(history.data) < 200:
        raise HTTPException(status_code=400, detail="Insufficient historical data (need 200+ bars)")

    # Extract OHLCV data
    opens = [d.open for d in history.data]
    highs = [d.high for d in history.data]
    lows = [d.low for d in history.data]
    closes = [d.close for d in history.data]
    volumes = [d.volume for d in history.data]
    dates = [d.date for d in history.data]

    # Run backtest
    result = backtest_engine.run_backtest(
        symbol=request.symbol.upper(),
        strategy=strategy,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
        volumes=volumes,
        dates=dates,
        initial_capital=request.initial_capital,
        position_size_pct=request.position_size_pct,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
    )

    # Convert to dict (excluding trades list for brevity)
    return {
        "strategy": result.strategy,
        "symbol": result.symbol,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_return": result.total_return,
        "total_return_pct": result.total_return_pct,
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown,
        "max_drawdown_pct": result.max_drawdown_pct,
        "sharpe_ratio": result.sharpe_ratio,
        "avg_trade_pnl": result.avg_trade_pnl,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "largest_win": result.largest_win,
        "largest_loss": result.largest_loss,
    }


# ==================== Risk Analysis ====================

@router.get("/risk/portfolio")
async def get_portfolio_risk_analysis():
    """
    Get comprehensive portfolio risk analysis.

    Includes sector exposure, correlation risk, and diversification score.
    """
    from services.alpaca_service import get_alpaca_service
    from services.risk_manager import SectorExposureManager, CorrelationRiskManager

    alpaca = get_alpaca_service()
    sector_manager = SectorExposureManager()
    correlation_manager = CorrelationRiskManager()

    try:
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()

        sector_exposure = sector_manager.calculate_sector_exposure(positions, account["equity"])
        correlation_report = correlation_manager.get_portfolio_correlation_report(positions)

        return {
            "account_equity": account["equity"],
            "total_positions": len(positions),
            "sector_exposure": sector_exposure,
            "correlation_analysis": correlation_report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
