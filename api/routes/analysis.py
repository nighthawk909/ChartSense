"""
Technical analysis routes - indicator calculations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from services.indicators import IndicatorService
from services.alpha_vantage import AlphaVantageService
from services.alpaca_service import get_alpaca_service
from models.indicators import (
    RSIResponse,
    MACDResponse,
    BollingerBandsResponse,
    MovingAverageResponse,
    TechnicalSummary,
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

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


@router.get("/ai-insight/{symbol}")
async def get_ai_insight(symbol: str):
    """
    Get comprehensive AI-generated insight for a stock.
    Uses multiple technical indicators to generate actionable recommendations.
    """
    try:
        alpaca = get_alpaca_service()

        # Get price data from Alpaca (unlimited)
        start = datetime.now() - timedelta(days=200)
        bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=200, start=start)

        if not bars or len(bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        # Extract price data
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]

        current_price = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current_price
        daily_change = ((current_price - prev_close) / prev_close) * 100

        # Calculate all indicators
        rsi_14 = indicator_service.calculate_rsi(closes, 14)
        rsi_value = rsi_14[-1] if rsi_14 else 50

        macd_line, signal_line, histogram = indicator_service.calculate_macd(closes, 12, 26, 9)
        macd_value = macd_line[-1] if macd_line else 0
        macd_signal = signal_line[-1] if signal_line else 0
        macd_hist = histogram[-1] if histogram else 0

        sma_20 = indicator_service.calculate_sma(closes, 20)
        sma_50 = indicator_service.calculate_sma(closes, 50)
        sma_200 = indicator_service.calculate_sma(closes, 200)

        ema_12 = indicator_service.calculate_ema(closes, 12)
        ema_26 = indicator_service.calculate_ema(closes, 26)

        upper_bb, middle_bb, lower_bb = indicator_service.calculate_bollinger_bands(closes, 20, 2)

        atr = indicator_service.calculate_atr(highs, lows, closes, 14)
        atr_value = atr[-1] if atr else 0

        # Calculate score and signals
        score = 50  # Start neutral
        signals = []
        concerns = []

        # RSI Analysis
        if rsi_value < 30:
            signals.append(f"RSI oversold at {rsi_value:.1f} - potential bounce")
            score += 15
        elif rsi_value > 70:
            concerns.append(f"RSI overbought at {rsi_value:.1f} - pullback risk")
            score -= 15
        elif rsi_value < 40:
            signals.append(f"RSI approaching oversold ({rsi_value:.1f})")
            score += 5
        elif rsi_value > 60:
            concerns.append(f"RSI getting elevated ({rsi_value:.1f})")
            score -= 5

        # MACD Analysis
        if macd_value > macd_signal:
            if macd_hist > 0 and len(histogram) > 1 and histogram[-2] <= 0:
                signals.append("MACD bullish crossover - momentum building")
                score += 15
            else:
                signals.append("MACD bullish - positive momentum")
                score += 8
        else:
            if macd_hist < 0 and len(histogram) > 1 and histogram[-2] >= 0:
                concerns.append("MACD bearish crossover - momentum fading")
                score -= 15
            else:
                concerns.append("MACD bearish - negative momentum")
                score -= 8

        # Moving Average Analysis
        sma_20_val = sma_20[-1] if sma_20 else current_price
        sma_50_val = sma_50[-1] if sma_50 else current_price
        sma_200_val = sma_200[-1] if sma_200 else current_price

        # Price vs MAs
        above_20 = current_price > sma_20_val
        above_50 = current_price > sma_50_val
        above_200 = current_price > sma_200_val

        if above_20 and above_50 and above_200:
            signals.append("Trading above all major moving averages - strong uptrend")
            score += 12
        elif not above_20 and not above_50 and not above_200:
            concerns.append("Trading below all major moving averages - weak trend")
            score -= 12
        elif above_200:
            signals.append("Above 200 SMA - long-term trend intact")
            score += 5
        else:
            concerns.append("Below 200 SMA - long-term trend broken")
            score -= 8

        # Golden/Death Cross
        if sma_50 and sma_200 and len(sma_50) > 1 and len(sma_200) > 1:
            if sma_50_val > sma_200_val and sma_50[-2] <= sma_200[-2]:
                signals.append("Golden Cross forming (50 SMA crossing above 200 SMA)")
                score += 10
            elif sma_50_val < sma_200_val and sma_50[-2] >= sma_200[-2]:
                concerns.append("Death Cross forming (50 SMA crossing below 200 SMA)")
                score -= 10

        # Bollinger Bands
        if upper_bb and lower_bb:
            bb_upper = upper_bb[-1]
            bb_lower = lower_bb[-1]
            bb_width = (bb_upper - bb_lower) / middle_bb[-1] * 100 if middle_bb else 0

            if current_price <= bb_lower:
                signals.append(f"At lower Bollinger Band - oversold condition")
                score += 8
            elif current_price >= bb_upper:
                concerns.append(f"At upper Bollinger Band - extended")
                score -= 5

            if bb_width < 5:
                signals.append("Bollinger Bands squeezing - breakout imminent")

        # Volume Analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        if volume_ratio > 1.5 and daily_change > 0:
            signals.append(f"High volume ({volume_ratio:.1f}x avg) on up day - conviction")
            score += 5
        elif volume_ratio > 1.5 and daily_change < 0:
            concerns.append(f"High volume ({volume_ratio:.1f}x avg) on down day - selling pressure")
            score -= 5

        # Price momentum (short-term)
        week_change = ((current_price - closes[-5]) / closes[-5]) * 100 if len(closes) >= 5 else 0
        month_change = ((current_price - closes[-20]) / closes[-20]) * 100 if len(closes) >= 20 else 0

        if week_change > 5:
            signals.append(f"Strong weekly momentum: +{week_change:.1f}%")
            score += 5
        elif week_change < -5:
            concerns.append(f"Weak weekly momentum: {week_change:.1f}%")
            score -= 5

        # Determine overall recommendation
        if score >= 70:
            recommendation = "STRONG BUY"
            recommendation_color = "green"
            action = f"Consider entering a long position in {symbol}. Multiple bullish signals align."
        elif score >= 60:
            recommendation = "BUY"
            recommendation_color = "green"
            action = f"Favorable setup for {symbol}. Consider adding to watchlist or small position."
        elif score <= 30:
            recommendation = "STRONG SELL"
            recommendation_color = "red"
            action = f"Consider reducing or exiting {symbol} position. Multiple bearish signals present."
        elif score <= 40:
            recommendation = "SELL"
            recommendation_color = "red"
            action = f"Caution warranted for {symbol}. Consider taking profits or setting stops."
        else:
            recommendation = "HOLD"
            recommendation_color = "yellow"
            action = f"Wait for clearer signals on {symbol}. Monitor for breakout direction."

        # Generate detailed insight text
        if score >= 60:
            sentiment = "bullish"
            outlook = "positive"
        elif score <= 40:
            sentiment = "bearish"
            outlook = "concerning"
        else:
            sentiment = "neutral"
            outlook = "mixed"

        insight_text = (
            f"{symbol} shows a {sentiment} setup with a technical score of {score}/100. "
            f"The stock is trading at ${current_price:.2f} ({'+' if daily_change >= 0 else ''}{daily_change:.2f}% today). "
        )

        if signals:
            insight_text += f"Key bullish signals: {signals[0]}. "
        if concerns:
            insight_text += f"Watch out for: {concerns[0]}. "

        insight_text += action

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "daily_change_pct": round(daily_change, 2),
            "score": score,
            "recommendation": recommendation,
            "recommendation_color": recommendation_color,
            "action": action,
            "insight": insight_text,
            "signals": signals,
            "concerns": concerns,
            "indicators": {
                "rsi_14": round(rsi_value, 2),
                "macd": round(macd_value, 4),
                "macd_signal": round(macd_signal, 4),
                "macd_histogram": round(macd_hist, 4),
                "sma_20": round(sma_20_val, 2),
                "sma_50": round(sma_50_val, 2),
                "sma_200": round(sma_200_val, 2),
                "atr_14": round(atr_value, 2),
                "volume_ratio": round(volume_ratio, 2),
            },
            "price_vs_ma": {
                "above_sma_20": above_20,
                "above_sma_50": above_50,
                "above_sma_200": above_200,
            },
            "momentum": {
                "week_change_pct": round(week_change, 2),
                "month_change_pct": round(month_change, 2),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI insight error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_stock_recommendations(
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get stock recommendations for watchlist/trading.
    Scans popular stocks and returns ranked opportunities.
    """
    # Popular stocks to scan
    scan_symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "INTC",
        "SPY", "QQQ", "DIA", "IWM", "XLF", "XLE", "XLK", "XLV", "XLI", "XLP",
        "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "PYPL",
        "UNH", "JNJ", "PFE", "ABBV", "MRK", "LLY",
        "HD", "WMT", "COST", "TGT", "NKE", "SBUX",
        "DIS", "CMCSA", "T", "VZ",
        "BA", "CAT", "GE", "HON", "UPS",
        "CRM", "ADBE", "NOW", "SNOW", "PLTR",
    ]

    alpaca = get_alpaca_service()
    recommendations = []

    for symbol in scan_symbols[:30]:  # Limit scan for performance
        try:
            # Get historical data
            start = datetime.now() - timedelta(days=100)
            bars = await alpaca.get_bars(symbol, timeframe="1day", limit=100, start=start)

            if not bars or len(bars) < 30:
                continue

            closes = [b["close"] for b in bars]
            highs = [b["high"] for b in bars]
            lows = [b["low"] for b in bars]

            current_price = closes[-1]

            # Quick technical analysis
            rsi = indicator_service.calculate_rsi(closes, 14)
            rsi_value = rsi[-1] if rsi else 50

            macd_line, signal_line, histogram = indicator_service.calculate_macd(closes, 12, 26, 9)
            macd_bullish = macd_line[-1] > signal_line[-1] if macd_line and signal_line else False

            sma_20 = indicator_service.calculate_sma(closes, 20)
            sma_50 = indicator_service.calculate_sma(closes, 50)

            above_sma_20 = current_price > sma_20[-1] if sma_20 else True
            above_sma_50 = current_price > sma_50[-1] if sma_50 else True

            # Calculate score
            score = 50
            signals = []

            if rsi_value < 35:
                score += 15
                signals.append("Oversold")
            elif rsi_value > 65:
                score -= 10

            if macd_bullish:
                score += 10
                signals.append("MACD Bullish")
            else:
                score -= 5

            if above_sma_20 and above_sma_50:
                score += 10
                signals.append("Above MAs")
            elif not above_sma_20 and not above_sma_50:
                score -= 10

            # Weekly momentum
            week_change = ((current_price - closes[-5]) / closes[-5]) * 100 if len(closes) >= 5 else 0
            if week_change > 3:
                score += 5
                signals.append(f"+{week_change:.1f}% week")
            elif week_change < -5:
                score -= 5

            # Determine signal
            if score >= 65:
                signal = "BUY"
                signal_color = "green"
            elif score <= 35:
                signal = "SELL"
                signal_color = "red"
            else:
                signal = "HOLD"
                signal_color = "yellow"

            recommendations.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "score": score,
                "signal": signal,
                "signal_color": signal_color,
                "rsi": round(rsi_value, 1),
                "macd_bullish": macd_bullish,
                "above_sma_20": above_sma_20,
                "above_sma_50": above_sma_50,
                "week_change_pct": round(week_change, 2),
                "signals": signals,
            })

        except Exception as e:
            logger.debug(f"Error scanning {symbol}: {e}")
            continue

    # Sort by score descending
    recommendations.sort(key=lambda x: x["score"], reverse=True)

    # Separate into categories
    buy_signals = [r for r in recommendations if r["signal"] == "BUY"][:limit]
    sell_signals = [r for r in recommendations if r["signal"] == "SELL"][:5]

    return {
        "timestamp": datetime.now().isoformat(),
        "total_scanned": len(recommendations),
        "buy_opportunities": buy_signals,
        "sell_candidates": sell_signals,
        "top_picks": recommendations[:5],
    }
