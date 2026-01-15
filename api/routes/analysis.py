"""
Technical analysis routes - indicator calculations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.indicators import IndicatorService
from services.alpha_vantage import AlphaVantageService
from models.indicators import (
    RSIResponse,
    MACDResponse,
    BollingerBandsResponse,
    MovingAverageResponse,
    TechnicalSummary,
)

router = APIRouter()
indicator_service = IndicatorService()
av_service = AlphaVantageService()


@router.get("/rsi/{symbol}", response_model=RSIResponse)
async def get_rsi(
    symbol: str,
    period: int = Query(default=14, ge=2, le=100),
    interval: str = Query(default="daily"),
):
    """Calculate RSI (Relative Strength Index) for a symbol"""
    try:
        # Get historical data
        history = await av_service.get_history(symbol.upper(), interval=interval)
        if not history:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        # Calculate RSI
        rsi_values = indicator_service.calculate_rsi(history.prices, period)
        current_rsi = rsi_values[-1] if rsi_values else None

        # Determine signal
        if current_rsi is None:
            signal = "Unknown"
        elif current_rsi > 70:
            signal = "Overbought"
        elif current_rsi < 30:
            signal = "Oversold"
        else:
            signal = "Neutral"

        return RSIResponse(
            symbol=symbol.upper(),
            period=period,
            current_value=current_rsi,
            signal=signal,
            values=rsi_values[-30:],  # Last 30 values
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macd/{symbol}", response_model=MACDResponse)
async def get_macd(
    symbol: str,
    fast_period: int = Query(default=12, ge=2, le=50),
    slow_period: int = Query(default=26, ge=2, le=100),
    signal_period: int = Query(default=9, ge=2, le=50),
):
    """Calculate MACD for a symbol"""
    try:
        history = await av_service.get_history(symbol.upper())
        if not history:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        macd_line, signal_line, histogram = indicator_service.calculate_macd(
            history.prices, fast_period, slow_period, signal_period
        )

        current_macd = macd_line[-1] if macd_line else None
        current_signal = signal_line[-1] if signal_line else None
        current_histogram = histogram[-1] if histogram else None

        # Determine signal
        if current_macd is not None and current_signal is not None:
            if current_macd > current_signal:
                signal = "Bullish"
            elif current_macd < current_signal:
                signal = "Bearish"
            else:
                signal = "Neutral"
        else:
            signal = "Unknown"

        return MACDResponse(
            symbol=symbol.upper(),
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            macd_line=current_macd,
            signal_line=current_signal,
            histogram=current_histogram,
            signal=signal,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sma/{symbol}", response_model=MovingAverageResponse)
async def get_sma(
    symbol: str,
    period: int = Query(default=20, ge=2, le=200),
):
    """Calculate Simple Moving Average"""
    try:
        history = await av_service.get_history(symbol.upper())
        if not history:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        sma_values = indicator_service.calculate_sma(history.prices, period)
        current_sma = sma_values[-1] if sma_values else None
        current_price = history.prices[-1] if history.prices else None

        if current_sma and current_price:
            signal = "Above" if current_price > current_sma else "Below"
        else:
            signal = "Unknown"

        return MovingAverageResponse(
            symbol=symbol.upper(),
            period=period,
            type="SMA",
            current_value=current_sma,
            current_price=current_price,
            signal=signal,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}", response_model=TechnicalSummary)
async def get_technical_summary(symbol: str):
    """Get a summary of all technical indicators for a symbol"""
    try:
        history = await av_service.get_history(symbol.upper())
        if not history:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        prices = history.prices

        # Calculate all indicators
        rsi = indicator_service.calculate_rsi(prices, 14)
        sma_20 = indicator_service.calculate_sma(prices, 20)
        sma_50 = indicator_service.calculate_sma(prices, 50)
        sma_200 = indicator_service.calculate_sma(prices, 200)
        macd, signal, _ = indicator_service.calculate_macd(prices, 12, 26, 9)

        current_price = prices[-1] if prices else None

        # Build summary
        indicators = {}

        if rsi:
            rsi_val = rsi[-1]
            indicators["rsi_14"] = {
                "value": round(rsi_val, 2),
                "signal": "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
            }

        if sma_20 and current_price:
            indicators["sma_20"] = {
                "value": round(sma_20[-1], 2),
                "signal": "Above" if current_price > sma_20[-1] else "Below"
            }

        if sma_50 and current_price:
            indicators["sma_50"] = {
                "value": round(sma_50[-1], 2),
                "signal": "Above" if current_price > sma_50[-1] else "Below"
            }

        if sma_200 and current_price:
            indicators["sma_200"] = {
                "value": round(sma_200[-1], 2),
                "signal": "Above" if current_price > sma_200[-1] else "Below"
            }

        if macd and signal:
            indicators["macd"] = {
                "value": round(macd[-1], 2),
                "signal": "Bullish" if macd[-1] > signal[-1] else "Bearish"
            }

        # Overall sentiment
        bullish_count = sum(
            1 for ind in indicators.values()
            if ind["signal"] in ["Bullish", "Above", "Oversold"]
        )
        bearish_count = sum(
            1 for ind in indicators.values()
            if ind["signal"] in ["Bearish", "Below", "Overbought"]
        )

        if bullish_count > bearish_count:
            overall = "Bullish"
        elif bearish_count > bullish_count:
            overall = "Bearish"
        else:
            overall = "Neutral"

        return TechnicalSummary(
            symbol=symbol.upper(),
            current_price=current_price,
            indicators=indicators,
            overall_signal=overall,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
