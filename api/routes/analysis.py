"""
Technical analysis routes - indicator calculations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from services.indicators import IndicatorService, AdaptiveIndicatorEngine, TradingMode
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
adaptive_engine = AdaptiveIndicatorEngine()
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
    """Get a summary of all technical indicators for a symbol.

    Uses Alpaca for price data (unlimited API calls).
    """
    try:
        # Use Alpaca for price data (unlimited) instead of Alpha Vantage (25/day)
        alpaca = get_alpaca_service()
        start = datetime.now() - timedelta(days=250)  # Enough for 200 SMA
        bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=250, start=start)

        if not bars or len(bars) < 20:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        prices = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]

        # Calculate all indicators
        rsi = indicator_service.calculate_rsi(prices, 14)
        sma_20 = indicator_service.calculate_sma(prices, 20)
        sma_50 = indicator_service.calculate_sma(prices, 50)
        sma_200 = indicator_service.calculate_sma(prices, 200)
        macd, signal, histogram = indicator_service.calculate_macd(prices, 12, 26, 9)
        upper_bb, middle_bb, lower_bb = indicator_service.calculate_bollinger_bands(prices, 20, 2)
        ema_12 = indicator_service.calculate_ema(prices, 12)
        ema_26 = indicator_service.calculate_ema(prices, 26)
        atr = indicator_service.calculate_atr(highs, lows, prices, 14)

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
                "signal": "Above SMA20" if current_price > sma_20[-1] else "Below SMA20"
            }

        if sma_50 and current_price:
            indicators["sma_50"] = {
                "value": round(sma_50[-1], 2),
                "signal": "Above SMA50" if current_price > sma_50[-1] else "Below SMA50"
            }

        if sma_200 and current_price:
            indicators["sma_200"] = {
                "value": round(sma_200[-1], 2),
                "signal": "Above SMA200" if current_price > sma_200[-1] else "Below SMA200"
            }

        if macd and signal:
            indicators["macd"] = {
                "value": round(macd[-1], 4),
                "signal": "Bullish" if macd[-1] > signal[-1] else "Bearish",
                "signal_line": round(signal[-1], 4),
                "histogram": round(histogram[-1], 4) if histogram else 0
            }

        if upper_bb and lower_bb and middle_bb and current_price:
            bb_upper = upper_bb[-1]
            bb_lower = lower_bb[-1]
            bb_middle = middle_bb[-1]

            # Determine position within bands
            if current_price >= bb_upper:
                position = "Upper Band"
                bb_signal = "Overbought"
            elif current_price <= bb_lower:
                position = "Lower Band"
                bb_signal = "Oversold"
            elif current_price > bb_middle:
                position = "Upper Half"
                bb_signal = "Above Middle"
            else:
                position = "Lower Half"
                bb_signal = "Below Middle"

            indicators["bollinger"] = {
                "position": position,
                "signal": bb_signal,
                "upper": round(bb_upper, 2),
                "middle": round(bb_middle, 2),
                "lower": round(bb_lower, 2)
            }

        if ema_12 and ema_26 and current_price:
            ema_12_val = ema_12[-1]
            ema_26_val = ema_26[-1]
            indicators["ema_cross"] = {
                "ema_12": round(ema_12_val, 2),
                "ema_26": round(ema_26_val, 2),
                "signal": "Bullish (EMA12 > EMA26)" if ema_12_val > ema_26_val else "Bearish (EMA12 < EMA26)"
            }

        if atr:
            atr_val = atr[-1]
            atr_pct = (atr_val / current_price) * 100 if current_price else 0
            indicators["atr_14"] = {
                "value": round(atr_val, 2),
                "percent": round(atr_pct, 2),
                "signal": "High Volatility" if atr_pct > 3 else "Low Volatility" if atr_pct < 1 else "Normal"
            }

        # Overall sentiment
        bullish_count = sum(
            1 for ind in indicators.values()
            if any(s in str(ind.get("signal", "")).lower() for s in ["bullish", "above", "oversold"])
        )
        bearish_count = sum(
            1 for ind in indicators.values()
            if any(s in str(ind.get("signal", "")).lower() for s in ["bearish", "below", "overbought"])
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
        logger.error(f"Summary error for {symbol}: {e}")
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


@router.get("/ai-insight-multi/{symbol}")
async def get_multi_timeframe_ai_insight(symbol: str):
    """
    Get AI insights for multiple trading timeframes.

    Returns analysis for:
    - Scalp (1-15 min): Quick trades, RSI extremes, MACD momentum
    - Intraday (1h-4h): Day trading, trend following
    - Swing (1D-1W): Multi-day holds, trend direction
    - Long-term (Weekly+): Position trading, 200 SMA trend

    A stock can be BUY for scalping but HOLD for long-term.
    """
    try:
        alpaca = get_alpaca_service()

        # Get multiple timeframes of data
        start_long = datetime.now() - timedelta(days=365)
        start_medium = datetime.now() - timedelta(days=60)
        start_short = datetime.now() - timedelta(days=5)

        # Fetch different timeframe data
        daily_bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=250, start=start_long)
        hourly_bars = await alpaca.get_bars(symbol.upper(), timeframe="1hour", limit=100, start=start_medium)
        min_15_bars = await alpaca.get_bars(symbol.upper(), timeframe="15min", limit=100, start=start_short)

        if not daily_bars or len(daily_bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        # Extract daily data
        daily_closes = [b["close"] for b in daily_bars]
        daily_highs = [b["high"] for b in daily_bars]
        daily_lows = [b["low"] for b in daily_bars]
        daily_volumes = [b["volume"] for b in daily_bars]

        current_price = daily_closes[-1]

        # Calculate daily indicators
        rsi_14 = indicator_service.calculate_rsi(daily_closes, 14)
        rsi_value = rsi_14[-1] if rsi_14 else 50

        macd_line, signal_line, histogram = indicator_service.calculate_macd(daily_closes, 12, 26, 9)
        macd_value = macd_line[-1] if macd_line else 0
        macd_signal = signal_line[-1] if signal_line else 0
        macd_hist = histogram[-1] if histogram else 0

        sma_20 = indicator_service.calculate_sma(daily_closes, 20)
        sma_50 = indicator_service.calculate_sma(daily_closes, 50)
        sma_200 = indicator_service.calculate_sma(daily_closes, 200)

        ema_9 = indicator_service.calculate_ema(daily_closes, 9)
        ema_21 = indicator_service.calculate_ema(daily_closes, 21)

        upper_bb, middle_bb, lower_bb = indicator_service.calculate_bollinger_bands(daily_closes, 20, 2)
        atr = indicator_service.calculate_atr(daily_highs, daily_lows, daily_closes, 14)
        atr_value = atr[-1] if atr else 0
        atr_pct = (atr_value / current_price) * 100 if current_price else 0

        # Calculate volume ratio
        avg_volume = sum(daily_volumes[-20:]) / 20 if len(daily_volumes) >= 20 else sum(daily_volumes) / max(len(daily_volumes), 1)
        volume_ratio = daily_volumes[-1] / avg_volume if avg_volume > 0 else 1

        # MA values
        sma_20_val = sma_20[-1] if sma_20 else current_price
        sma_50_val = sma_50[-1] if sma_50 else current_price
        sma_200_val = sma_200[-1] if sma_200 else current_price
        ema_9_val = ema_9[-1] if ema_9 else current_price
        ema_21_val = ema_21[-1] if ema_21 else current_price

        # BB values
        bb_upper = upper_bb[-1] if upper_bb else current_price * 1.02
        bb_lower = lower_bb[-1] if lower_bb else current_price * 0.98
        bb_middle = middle_bb[-1] if middle_bb else current_price

        # Calculate momentum over different periods
        day_change = ((current_price - daily_closes[-2]) / daily_closes[-2]) * 100 if len(daily_closes) > 1 else 0
        week_change = ((current_price - daily_closes[-5]) / daily_closes[-5]) * 100 if len(daily_closes) >= 5 else 0
        month_change = ((current_price - daily_closes[-20]) / daily_closes[-20]) * 100 if len(daily_closes) >= 20 else 0
        quarter_change = ((current_price - daily_closes[-60]) / daily_closes[-60]) * 100 if len(daily_closes) >= 60 else 0

        # Calculate hourly indicators for intraday
        hourly_rsi = None
        hourly_macd_bullish = False
        if hourly_bars and len(hourly_bars) > 20:
            hourly_closes = [b["close"] for b in hourly_bars]
            h_rsi = indicator_service.calculate_rsi(hourly_closes, 14)
            hourly_rsi = h_rsi[-1] if h_rsi else 50
            h_macd, h_signal, _ = indicator_service.calculate_macd(hourly_closes, 12, 26, 9)
            hourly_macd_bullish = h_macd[-1] > h_signal[-1] if h_macd and h_signal else False

        # Calculate 15min indicators for scalping
        min15_rsi = None
        min15_macd_bullish = False
        if min_15_bars and len(min_15_bars) > 20:
            min15_closes = [b["close"] for b in min_15_bars]
            m_rsi = indicator_service.calculate_rsi(min15_closes, 14)
            min15_rsi = m_rsi[-1] if m_rsi else 50
            m_macd, m_signal, _ = indicator_service.calculate_macd(min15_closes, 12, 26, 9)
            min15_macd_bullish = m_macd[-1] > m_signal[-1] if m_macd and m_signal else False

        # ============= SCALP ANALYSIS (1-15 min) =============
        scalp_score = 50
        scalp_signals = []
        scalp_concerns = []

        # RSI for scalping (extremes are opportunities)
        if min15_rsi:
            if min15_rsi < 25:
                scalp_signals.append(f"15m RSI oversold ({min15_rsi:.1f}) - bounce setup")
                scalp_score += 20
            elif min15_rsi > 75:
                scalp_concerns.append(f"15m RSI overbought ({min15_rsi:.1f}) - short setup")
                scalp_score -= 15
            elif min15_rsi < 40:
                scalp_signals.append(f"15m RSI low ({min15_rsi:.1f}) - watch for reversal")
                scalp_score += 8
            elif min15_rsi > 60:
                scalp_concerns.append(f"15m RSI elevated ({min15_rsi:.1f})")
                scalp_score -= 5

        # MACD for scalp momentum
        if min15_macd_bullish:
            scalp_signals.append("15m MACD bullish - momentum up")
            scalp_score += 10
        else:
            scalp_concerns.append("15m MACD bearish - momentum down")
            scalp_score -= 8

        # Price vs BB for mean reversion scalps
        if current_price <= bb_lower:
            scalp_signals.append("At lower Bollinger Band - mean reversion buy")
            scalp_score += 12
        elif current_price >= bb_upper:
            scalp_concerns.append("At upper Bollinger Band - extended")
            scalp_score -= 10

        # ATR for scalp viability
        if atr_pct > 1.5:
            scalp_signals.append(f"Good volatility for scalping ({atr_pct:.1f}% ATR)")
            scalp_score += 5
        elif atr_pct < 0.5:
            scalp_concerns.append(f"Low volatility ({atr_pct:.1f}% ATR) - tight ranges")
            scalp_score -= 5

        scalp_rec = _get_recommendation(scalp_score)

        # ============= INTRADAY ANALYSIS (1h-4h) =============
        intraday_score = 50
        intraday_signals = []
        intraday_concerns = []

        # Hourly RSI
        if hourly_rsi:
            if hourly_rsi < 30:
                intraday_signals.append(f"Hourly RSI oversold ({hourly_rsi:.1f})")
                intraday_score += 15
            elif hourly_rsi > 70:
                intraday_concerns.append(f"Hourly RSI overbought ({hourly_rsi:.1f})")
                intraday_score -= 12

        # EMA cross for intraday trend
        if ema_9_val > ema_21_val:
            intraday_signals.append("EMA 9 > EMA 21 - short-term uptrend")
            intraday_score += 12
        else:
            intraday_concerns.append("EMA 9 < EMA 21 - short-term downtrend")
            intraday_score -= 10

        # Hourly MACD
        if hourly_macd_bullish:
            intraday_signals.append("Hourly MACD bullish")
            intraday_score += 8
        else:
            intraday_concerns.append("Hourly MACD bearish")
            intraday_score -= 8

        # Price vs SMA 20 for intraday trend
        if current_price > sma_20_val:
            intraday_signals.append("Above 20 SMA - intraday trend up")
            intraday_score += 8
        else:
            intraday_concerns.append("Below 20 SMA - intraday trend down")
            intraday_score -= 8

        # Volume for conviction
        if volume_ratio > 1.5:
            intraday_signals.append(f"High volume ({volume_ratio:.1f}x) - strong conviction")
            intraday_score += 5

        intraday_rec = _get_recommendation(intraday_score)

        # ============= SWING ANALYSIS (1D-1W) =============
        swing_score = 50
        swing_signals = []
        swing_concerns = []

        # Daily RSI
        if rsi_value < 35:
            swing_signals.append(f"Daily RSI oversold ({rsi_value:.1f}) - bounce setup")
            swing_score += 15
        elif rsi_value > 65:
            swing_concerns.append(f"Daily RSI overbought ({rsi_value:.1f})")
            swing_score -= 10

        # Daily MACD
        if macd_value > macd_signal:
            swing_signals.append("Daily MACD bullish - trend confirmed")
            swing_score += 12
        else:
            swing_concerns.append("Daily MACD bearish - trend weak")
            swing_score -= 12

        # Price vs SMA 50 for swing trend
        if current_price > sma_50_val:
            swing_signals.append("Above 50 SMA - intermediate uptrend")
            swing_score += 10
        else:
            swing_concerns.append("Below 50 SMA - intermediate downtrend")
            swing_score -= 10

        # Week momentum
        if week_change > 3:
            swing_signals.append(f"Strong weekly momentum (+{week_change:.1f}%)")
            swing_score += 8
        elif week_change < -3:
            swing_concerns.append(f"Weak weekly momentum ({week_change:.1f}%)")
            swing_score -= 8

        # Golden/Death cross
        if sma_50_val > sma_200_val:
            swing_signals.append("Golden cross active (50 > 200 SMA)")
            swing_score += 8
        else:
            swing_concerns.append("Death cross active (50 < 200 SMA)")
            swing_score -= 8

        swing_rec = _get_recommendation(swing_score)

        # ============= LONG-TERM ANALYSIS (Weekly+) =============
        longterm_score = 50
        longterm_signals = []
        longterm_concerns = []

        # Price vs 200 SMA - the key long-term indicator
        if current_price > sma_200_val:
            longterm_signals.append("Above 200 SMA - long-term uptrend intact")
            longterm_score += 15
        else:
            longterm_concerns.append("Below 200 SMA - long-term trend broken")
            longterm_score -= 15

        # 50 vs 200 SMA relationship
        if sma_50_val > sma_200_val:
            pct_above = ((sma_50_val - sma_200_val) / sma_200_val) * 100
            if pct_above > 5:
                longterm_signals.append(f"Strong trend: 50 SMA {pct_above:.1f}% above 200 SMA")
                longterm_score += 10
            else:
                longterm_signals.append("Uptrend: 50 SMA above 200 SMA")
                longterm_score += 5
        else:
            pct_below = ((sma_200_val - sma_50_val) / sma_200_val) * 100
            if pct_below > 5:
                longterm_concerns.append(f"Strong downtrend: 50 SMA {pct_below:.1f}% below 200 SMA")
                longterm_score -= 10
            else:
                longterm_concerns.append("Downtrend: 50 SMA below 200 SMA")
                longterm_score -= 5

        # Quarterly momentum
        if quarter_change > 10:
            longterm_signals.append(f"Strong 3-month gain (+{quarter_change:.1f}%)")
            longterm_score += 10
        elif quarter_change < -10:
            longterm_concerns.append(f"Significant 3-month loss ({quarter_change:.1f}%)")
            longterm_score -= 10

        # Monthly trend
        if month_change > 5:
            longterm_signals.append(f"Positive monthly trend (+{month_change:.1f}%)")
            longterm_score += 5
        elif month_change < -5:
            longterm_concerns.append(f"Negative monthly trend ({month_change:.1f}%)")
            longterm_score -= 5

        longterm_rec = _get_recommendation(longterm_score)

        # ============= ELLIOTT WAVE ESTIMATE =============
        elliott_wave = _estimate_elliott_wave(daily_closes, daily_highs, daily_lows)

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "daily_change_pct": round(day_change, 2),

            # Multi-timeframe analysis
            "timeframes": {
                "scalp": {
                    "timeframe": "1-15 min",
                    "score": max(0, min(100, scalp_score)),
                    "recommendation": scalp_rec["recommendation"],
                    "color": scalp_rec["color"],
                    "signals": scalp_signals[:3],
                    "concerns": scalp_concerns[:3],
                    "best_for": "Quick trades, momentum plays, mean reversion"
                },
                "intraday": {
                    "timeframe": "1h-4h",
                    "score": max(0, min(100, intraday_score)),
                    "recommendation": intraday_rec["recommendation"],
                    "color": intraday_rec["color"],
                    "signals": intraday_signals[:3],
                    "concerns": intraday_concerns[:3],
                    "best_for": "Day trades, trend following within the day"
                },
                "swing": {
                    "timeframe": "1D-1W",
                    "score": max(0, min(100, swing_score)),
                    "recommendation": swing_rec["recommendation"],
                    "color": swing_rec["color"],
                    "signals": swing_signals[:3],
                    "concerns": swing_concerns[:3],
                    "best_for": "Multi-day holds, trend trades"
                },
                "longterm": {
                    "timeframe": "Weekly+",
                    "score": max(0, min(100, longterm_score)),
                    "recommendation": longterm_rec["recommendation"],
                    "color": longterm_rec["color"],
                    "signals": longterm_signals[:3],
                    "concerns": longterm_concerns[:3],
                    "best_for": "Position trading, investment"
                }
            },

            # Elliott Wave analysis
            "elliott_wave": elliott_wave,

            # Key indicators
            "indicators": {
                "rsi_14": round(rsi_value, 2),
                "rsi_15m": round(min15_rsi, 2) if min15_rsi else None,
                "rsi_1h": round(hourly_rsi, 2) if hourly_rsi else None,
                "macd_histogram": round(macd_hist, 4),
                "sma_20": round(sma_20_val, 2),
                "sma_50": round(sma_50_val, 2),
                "sma_200": round(sma_200_val, 2),
                "ema_9": round(ema_9_val, 2),
                "ema_21": round(ema_21_val, 2),
                "atr_14": round(atr_value, 2),
                "atr_pct": round(atr_pct, 2),
                "volume_ratio": round(volume_ratio, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
            },

            # Momentum across timeframes
            "momentum": {
                "day": round(day_change, 2),
                "week": round(week_change, 2),
                "month": round(month_change, 2),
                "quarter": round(quarter_change, 2),
            },

            # Price vs key levels
            "price_vs_ma": {
                "above_sma_20": current_price > sma_20_val,
                "above_sma_50": current_price > sma_50_val,
                "above_sma_200": current_price > sma_200_val,
                "above_ema_9": current_price > ema_9_val,
                "above_ema_21": current_price > ema_21_val,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-timeframe insight error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_recommendation(score: int) -> dict:
    """Convert score to recommendation and color."""
    if score >= 70:
        return {"recommendation": "STRONG BUY", "color": "green"}
    elif score >= 60:
        return {"recommendation": "BUY", "color": "green"}
    elif score <= 30:
        return {"recommendation": "STRONG SELL", "color": "red"}
    elif score <= 40:
        return {"recommendation": "SELL", "color": "red"}
    else:
        return {"recommendation": "HOLD", "color": "yellow"}


@router.get("/triple-screen/{symbol}")
async def get_triple_screen_analysis(symbol: str):
    """
    Alexander Elder's Triple Screen Trading System Analysis.

    This methodology uses three "screens" across different timeframes:
    - Screen 1 (Daily): Determine the "tide" - overall market direction
    - Screen 2 (1-Hour): Identify the "wave" - pullbacks or consolidations
    - Screen 3 (5-Minute): Pinpoint the "ripple" - precise entry timing

    The system aligns long-term trends with short-term entries for higher probability trades.
    Ideal for SMR and similar stocks with multi-timeframe dynamics.
    """
    try:
        alpaca = get_alpaca_service()

        # Fetch data for all three screens
        start_daily = datetime.now() - timedelta(days=270)  # 9 months for Screen 1
        start_hourly = datetime.now() - timedelta(days=14)   # 2 weeks for Screen 2
        start_5min = datetime.now() - timedelta(days=3)      # 3 days for Screen 3

        daily_bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=180, start=start_daily)
        hourly_bars = await alpaca.get_bars(symbol.upper(), timeframe="1hour", limit=150, start=start_hourly)
        min5_bars = await alpaca.get_bars(symbol.upper(), timeframe="5min", limit=200, start=start_5min)

        if not daily_bars or len(daily_bars) < 50:
            raise HTTPException(status_code=404, detail=f"Insufficient daily data for {symbol}")

        # Extract data
        daily_closes = [b["close"] for b in daily_bars]
        daily_highs = [b["high"] for b in daily_bars]
        daily_lows = [b["low"] for b in daily_bars]
        daily_volumes = [b["volume"] for b in daily_bars]

        current_price = daily_closes[-1]

        # ============= SCREEN 1: THE TIDE (Daily - Long-term trend) =============
        # Uses MACD Histogram slope and 50/200 SMA for trend direction

        # Calculate daily indicators
        macd_line, signal_line, histogram = indicator_service.calculate_macd(daily_closes, 12, 26, 9)
        sma_50 = indicator_service.calculate_sma(daily_closes, 50)
        sma_200 = indicator_service.calculate_sma(daily_closes, 200)
        ema_13 = indicator_service.calculate_ema(daily_closes, 13)
        rsi_daily = indicator_service.calculate_rsi(daily_closes, 14)

        # ADX for trend strength
        adx, plus_di, minus_di = indicator_service.calculate_adx(daily_highs, daily_lows, daily_closes, 14)

        # Weekly momentum (last 5 days)
        week_momentum = ((daily_closes[-1] - daily_closes[-5]) / daily_closes[-5]) * 100 if len(daily_closes) >= 5 else 0

        # Determine tide direction
        histogram_slope = (histogram[-1] - histogram[-3]) if len(histogram) >= 3 else 0
        sma_50_val = sma_50[-1] if sma_50 else current_price
        sma_200_val = sma_200[-1] if sma_200 else current_price
        ema_13_val = ema_13[-1] if ema_13 else current_price
        rsi_daily_val = rsi_daily[-1] if rsi_daily else 50
        adx_val = adx[-1] if adx else 20
        plus_di_val = plus_di[-1] if plus_di else 25
        minus_di_val = minus_di[-1] if minus_di else 25

        # Tide is bullish if:
        # - MACD histogram rising OR
        # - Price above 50 SMA AND 50 SMA above 200 SMA (Golden Cross)
        # - ADX > 25 with +DI > -DI
        tide_bullish_signals = []
        tide_bearish_signals = []

        if histogram_slope > 0:
            tide_bullish_signals.append(f"MACD histogram rising (+{histogram_slope:.3f})")
        else:
            tide_bearish_signals.append(f"MACD histogram falling ({histogram_slope:.3f})")

        if current_price > sma_50_val:
            tide_bullish_signals.append("Price above 50 SMA")
        else:
            tide_bearish_signals.append("Price below 50 SMA")

        if sma_50_val > sma_200_val:
            tide_bullish_signals.append("Golden Cross (50 SMA > 200 SMA)")
        else:
            tide_bearish_signals.append("Death Cross (50 SMA < 200 SMA)")

        if adx_val > 25:
            if plus_di_val > minus_di_val:
                tide_bullish_signals.append(f"Strong trend with +DI leadership (ADX: {adx_val:.1f})")
            else:
                tide_bearish_signals.append(f"Strong trend with -DI leadership (ADX: {adx_val:.1f})")
        else:
            tide_bearish_signals.append(f"Weak/no trend (ADX: {adx_val:.1f})")

        tide_direction = "BULLISH" if len(tide_bullish_signals) >= 3 else ("BEARISH" if len(tide_bearish_signals) >= 3 else "NEUTRAL")
        tide_strength = min(100, (len(tide_bullish_signals) - len(tide_bearish_signals) + 4) * 12.5)

        # ============= SCREEN 2: THE WAVE (Hourly - Intermediate oscillator) =============
        # Uses RSI to find pullbacks in direction of tide

        if hourly_bars and len(hourly_bars) > 20:
            hourly_closes = [b["close"] for b in hourly_bars]
            hourly_highs = [b["high"] for b in hourly_bars]
            hourly_lows = [b["low"] for b in hourly_bars]

            rsi_hourly = indicator_service.calculate_rsi(hourly_closes, 14)
            stoch_k, stoch_d = indicator_service.calculate_stochastic(hourly_highs, hourly_lows, hourly_closes, 14, 3)
            ema_9h = indicator_service.calculate_ema(hourly_closes, 9)
            ema_21h = indicator_service.calculate_ema(hourly_closes, 21)

            rsi_hourly_val = rsi_hourly[-1] if rsi_hourly else 50
            stoch_k_val = stoch_k[-1] if stoch_k else 50
            stoch_d_val = stoch_d[-1] if stoch_d else 50
            ema_9h_val = ema_9h[-1] if ema_9h else current_price
            ema_21h_val = ema_21h[-1] if ema_21h else current_price

            # Wave analysis: Look for pullbacks
            wave_signals = []
            wave_concerns = []

            # In bullish tide, look for oversold conditions (buy the dip)
            if tide_direction == "BULLISH":
                if rsi_hourly_val < 40:
                    wave_signals.append(f"Hourly RSI pullback ({rsi_hourly_val:.1f}) - Wave buy zone")
                elif rsi_hourly_val < 50:
                    wave_signals.append(f"Hourly RSI consolidating ({rsi_hourly_val:.1f})")
                else:
                    wave_concerns.append(f"Hourly RSI elevated ({rsi_hourly_val:.1f}) - Wait for pullback")

                if stoch_k_val < 30:
                    wave_signals.append(f"Stochastic oversold ({stoch_k_val:.0f}) - Entry setup forming")
                elif stoch_k_val < stoch_d_val:
                    wave_concerns.append("Stochastic momentum fading")

            # In bearish tide, look for overbought conditions (short the rally)
            elif tide_direction == "BEARISH":
                if rsi_hourly_val > 60:
                    wave_signals.append(f"Hourly RSI rally ({rsi_hourly_val:.1f}) - Wave short zone")
                elif rsi_hourly_val > 50:
                    wave_signals.append(f"Hourly RSI holding ({rsi_hourly_val:.1f})")
                else:
                    wave_concerns.append(f"Hourly RSI low ({rsi_hourly_val:.1f}) - Wait for bounce")

            # EMA cross
            if ema_9h_val > ema_21h_val:
                wave_signals.append("EMA 9 > 21 - Short-term momentum up")
            else:
                wave_concerns.append("EMA 9 < 21 - Short-term momentum down")

            wave_entry_ready = (
                (tide_direction == "BULLISH" and rsi_hourly_val < 45) or
                (tide_direction == "BEARISH" and rsi_hourly_val > 55) or
                (tide_direction == "NEUTRAL")
            )
        else:
            rsi_hourly_val = 50
            stoch_k_val = 50
            stoch_d_val = 50
            wave_signals = ["Insufficient hourly data"]
            wave_concerns = []
            wave_entry_ready = False

        # ============= SCREEN 3: THE RIPPLE (5-Min - Entry timing) =============
        # Uses intraday patterns for precise entry

        if min5_bars and len(min5_bars) > 30:
            min5_closes = [b["close"] for b in min5_bars]
            min5_highs = [b["high"] for b in min5_bars]
            min5_lows = [b["low"] for b in min5_bars]
            min5_volumes = [b["volume"] for b in min5_bars]

            rsi_5min = indicator_service.calculate_rsi(min5_closes, 7)
            macd_5m, signal_5m, hist_5m = indicator_service.calculate_macd(min5_closes, 6, 13, 5)
            vwap = indicator_service.calculate_vwap(min5_highs, min5_lows, min5_closes, min5_volumes)
            upper_bb, middle_bb, lower_bb = indicator_service.calculate_bollinger_bands(min5_closes, 20, 2)

            rsi_5min_val = rsi_5min[-1] if rsi_5min else 50
            macd_5m_hist = hist_5m[-1] if hist_5m else 0
            vwap_val = vwap[-1] if vwap else current_price
            bb_upper = upper_bb[-1] if upper_bb else current_price * 1.02
            bb_lower = lower_bb[-1] if lower_bb else current_price * 0.98

            ripple_signals = []
            ripple_concerns = []
            entry_trigger = False

            # Bullish ripple signals
            if tide_direction == "BULLISH" and wave_entry_ready:
                if rsi_5min_val < 35:
                    ripple_signals.append(f"5m RSI oversold ({rsi_5min_val:.1f}) - BUY trigger")
                    entry_trigger = True
                elif rsi_5min_val < 45:
                    ripple_signals.append(f"5m RSI low ({rsi_5min_val:.1f}) - Near entry")

                if macd_5m_hist > 0 and (len(hist_5m) < 2 or hist_5m[-2] < 0):
                    ripple_signals.append("5m MACD bullish cross - Momentum confirming")
                    entry_trigger = True

                if current_price < vwap_val:
                    ripple_signals.append(f"Below VWAP (${vwap_val:.2f}) - Value entry")
                else:
                    ripple_concerns.append(f"Above VWAP (${vwap_val:.2f})")

                if current_price <= bb_lower * 1.01:
                    ripple_signals.append("At lower Bollinger Band - Mean reversion buy")
                    entry_trigger = True

            # Bearish ripple signals
            elif tide_direction == "BEARISH" and wave_entry_ready:
                if rsi_5min_val > 65:
                    ripple_signals.append(f"5m RSI overbought ({rsi_5min_val:.1f}) - SHORT trigger")
                    entry_trigger = True
                elif rsi_5min_val > 55:
                    ripple_signals.append(f"5m RSI high ({rsi_5min_val:.1f}) - Near short entry")

                if macd_5m_hist < 0 and (len(hist_5m) < 2 or hist_5m[-2] > 0):
                    ripple_signals.append("5m MACD bearish cross - Momentum confirming")
                    entry_trigger = True

                if current_price > vwap_val:
                    ripple_signals.append(f"Above VWAP (${vwap_val:.2f}) - Overextended short")
                else:
                    ripple_concerns.append(f"Below VWAP (${vwap_val:.2f})")

            else:
                ripple_concerns.append("Awaiting wave alignment before entry")
        else:
            rsi_5min_val = 50
            vwap_val = current_price
            ripple_signals = ["Insufficient 5-minute data"]
            ripple_concerns = []
            entry_trigger = False

        # ============= OVERALL TRIPLE SCREEN VERDICT =============
        # All three screens must align for a high-confidence trade

        alignment_score = 0
        if tide_direction == "BULLISH":
            alignment_score += 40
        elif tide_direction == "BEARISH":
            alignment_score += 30

        if wave_entry_ready:
            alignment_score += 30

        if entry_trigger:
            alignment_score += 30

        # Final trade recommendation
        if alignment_score >= 80:
            if tide_direction == "BULLISH":
                trade_action = "STRONG BUY"
                trade_rationale = "All three screens aligned bullish. Tide up, wave pullback complete, ripple entry triggered."
            else:
                trade_action = "STRONG SHORT"
                trade_rationale = "All three screens aligned bearish. Tide down, wave bounce complete, ripple short triggered."
        elif alignment_score >= 60:
            if tide_direction == "BULLISH":
                trade_action = "BUY"
                trade_rationale = "Tide and wave aligned. Monitor 5-minute for entry confirmation."
            else:
                trade_action = "SHORT"
                trade_rationale = "Tide and wave aligned bearish. Monitor 5-minute for short entry."
        elif alignment_score >= 40:
            trade_action = "WAIT"
            trade_rationale = "Partial alignment only. Wait for wave to complete pullback."
        else:
            trade_action = "NO TRADE"
            trade_rationale = "Screens not aligned. Tide unclear or conflicting signals."

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "timestamp": datetime.now().isoformat(),
            "trade_action": trade_action,
            "alignment_score": alignment_score,
            "trade_rationale": trade_rationale,
            "screens": {
                "screen_1_tide": {
                    "timeframe": "Daily (9-month view)",
                    "direction": tide_direction,
                    "strength": tide_strength,
                    "signals": tide_bullish_signals,
                    "concerns": tide_bearish_signals,
                    "indicators": {
                        "macd_histogram": round(histogram[-1], 4) if histogram else 0,
                        "histogram_slope": round(histogram_slope, 4),
                        "sma_50": round(sma_50_val, 2),
                        "sma_200": round(sma_200_val, 2),
                        "adx": round(adx_val, 1),
                        "plus_di": round(plus_di_val, 1),
                        "minus_di": round(minus_di_val, 1),
                        "rsi_daily": round(rsi_daily_val, 1),
                        "week_momentum_pct": round(week_momentum, 2),
                    }
                },
                "screen_2_wave": {
                    "timeframe": "Hourly (2-week view)",
                    "entry_ready": wave_entry_ready,
                    "signals": wave_signals,
                    "concerns": wave_concerns,
                    "indicators": {
                        "rsi_hourly": round(rsi_hourly_val, 1),
                        "stochastic_k": round(stoch_k_val, 1),
                        "stochastic_d": round(stoch_d_val, 1),
                    }
                },
                "screen_3_ripple": {
                    "timeframe": "5-Minute (3-day view)",
                    "entry_triggered": entry_trigger,
                    "signals": ripple_signals,
                    "concerns": ripple_concerns,
                    "indicators": {
                        "rsi_5min": round(rsi_5min_val, 1),
                        "vwap": round(vwap_val, 2),
                        "price_vs_vwap_pct": round((current_price - vwap_val) / vwap_val * 100, 2),
                    }
                }
            },
            "methodology": {
                "name": "Alexander Elder Triple Screen",
                "description": "Three-tier analysis: Daily tide determines direction, Hourly wave finds pullbacks, 5-Min ripple times entries.",
                "best_for": ["Swing trades", "Position entries", "Multi-day holds"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Triple screen analysis error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-indicators/{symbol}")
async def get_adaptive_indicators(
    symbol: str,
    interval: str = Query(default="5min", description="Chart interval: 1min, 5min, 15min, 1hour, 1day"),
):
    """
    Get timeframe-adaptive indicators based on the active chart interval.

    Short-Term/Intraday (1m, 5m, 15m):
    - Focus: Momentum & Breakouts
    - Indicators: VWAP, ADX/DI, RSI (fast), Support/Resistance

    Long-Term/Swing (1h, 1d, 1w):
    - Focus: Trend & Structure
    - Indicators: 50/200 SMA, RSI, MACD, Volume Profile
    """
    try:
        alpaca = get_alpaca_service()

        # Determine timeframe category
        intraday_intervals = ["1min", "5min", "15min"]
        swing_intervals = ["1hour", "1day", "1week"]

        is_intraday = interval.lower() in intraday_intervals

        # Fetch data based on interval
        if is_intraday:
            # Get 3 days of data for intraday
            start = datetime.now() - timedelta(days=3)
            bars = await alpaca.get_bars(symbol.upper(), timeframe=interval.lower().replace("min", "Min").replace("hour", "Hour"), limit=400, start=start)
        else:
            # Get 6 months of daily data for swing
            start = datetime.now() - timedelta(days=180)
            bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=180, start=start)

        if not bars or len(bars) < 30:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]

        current_price = closes[-1]
        indicators = {}
        patterns = []

        if is_intraday:
            # ============= INTRADAY INDICATORS =============
            # VWAP
            vwap = indicator_service.calculate_vwap(highs, lows, closes, volumes)
            vwap_val = vwap[-1] if vwap else current_price
            indicators["vwap"] = round(vwap_val, 2)
            indicators["price_vs_vwap"] = round((current_price - vwap_val) / vwap_val * 100, 2)

            # ADX/DI with crossover detection
            adx, plus_di, minus_di = indicator_service.calculate_adx(highs, lows, closes, 14)
            if adx and plus_di and minus_di:
                indicators["adx"] = round(adx[-1], 1)
                indicators["plus_di"] = round(plus_di[-1], 1)
                indicators["minus_di"] = round(minus_di[-1], 1)
                indicators["di_bullish"] = plus_di[-1] > minus_di[-1]
                indicators["trend_strength"] = "Strong" if adx[-1] > 25 else ("Moderate" if adx[-1] > 20 else "Weak")

                # DI crossover detection
                if len(plus_di) >= 2 and len(minus_di) >= 2:
                    if plus_di[-1] > minus_di[-1] and plus_di[-2] <= minus_di[-2]:
                        patterns.append({"type": "DI_BULLISH_CROSS", "signal": "BUY", "strength": "strong"})
                    elif minus_di[-1] > plus_di[-1] and minus_di[-2] <= plus_di[-2]:
                        patterns.append({"type": "DI_BEARISH_CROSS", "signal": "SELL", "strength": "strong"})

            # Fast RSI for scalping
            rsi = indicator_service.calculate_rsi(closes, 7)
            rsi_val = rsi[-1] if rsi else 50
            indicators["rsi_7"] = round(rsi_val, 1)
            indicators["rsi_zone"] = "overbought" if rsi_val > 70 else ("oversold" if rsi_val < 30 else "neutral")

            # Bollinger Bands for breakouts
            upper_bb, middle_bb, lower_bb = indicator_service.calculate_bollinger_bands(closes, 20, 2)
            if upper_bb and lower_bb:
                indicators["bb_upper"] = round(upper_bb[-1], 2)
                indicators["bb_lower"] = round(lower_bb[-1], 2)
                indicators["bb_middle"] = round(middle_bb[-1], 2)
                bb_width = (upper_bb[-1] - lower_bb[-1]) / middle_bb[-1] * 100
                indicators["bb_width_pct"] = round(bb_width, 2)
                indicators["bb_squeeze"] = bb_width < 4  # Tight bands = breakout coming

                if current_price >= upper_bb[-1]:
                    patterns.append({"type": "BB_UPPER_BREAKOUT", "signal": "WATCH", "strength": "moderate"})
                elif current_price <= lower_bb[-1]:
                    patterns.append({"type": "BB_LOWER_TOUCH", "signal": "BOUNCE_POSSIBLE", "strength": "moderate"})

            # Support/Resistance from recent swings
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            indicators["resistance_near"] = round(recent_high, 2)
            indicators["support_near"] = round(recent_low, 2)

            # ATR for volatility
            atr = indicator_service.calculate_atr(highs, lows, closes, 14)
            atr_val = atr[-1] if atr else 0
            indicators["atr"] = round(atr_val, 2)
            indicators["atr_pct"] = round((atr_val / current_price) * 100, 2)

            # Bull/Bear flag detection (simplified)
            if len(closes) >= 30:
                # Check for consolidation after move
                range_20 = max(highs[-20:]) - min(lows[-20:])
                range_5 = max(highs[-5:]) - min(lows[-5:])
                if range_5 < range_20 * 0.3:  # Tight recent range
                    # Determine flag direction by prior move
                    prior_move = closes[-20] - closes[-30] if len(closes) >= 30 else 0
                    if prior_move > 0:
                        patterns.append({"type": "BULL_FLAG", "signal": "BUY", "strength": "moderate"})
                    elif prior_move < 0:
                        patterns.append({"type": "BEAR_FLAG", "signal": "SELL", "strength": "moderate"})

        else:
            # ============= SWING/LONG-TERM INDICATORS =============
            # SMAs
            sma_20 = indicator_service.calculate_sma(closes, 20)
            sma_50 = indicator_service.calculate_sma(closes, 50)
            sma_200 = indicator_service.calculate_sma(closes, 200) if len(closes) >= 200 else []

            indicators["sma_20"] = round(sma_20[-1], 2) if sma_20 else None
            indicators["sma_50"] = round(sma_50[-1], 2) if sma_50 else None
            indicators["sma_200"] = round(sma_200[-1], 2) if sma_200 else None

            # Golden/Death cross
            if sma_50 and sma_200:
                if sma_50[-1] > sma_200[-1]:
                    indicators["ma_cross"] = "GOLDEN_CROSS"
                    if len(sma_50) >= 2 and len(sma_200) >= 2:
                        if sma_50[-2] <= sma_200[-2]:
                            patterns.append({"type": "GOLDEN_CROSS", "signal": "BUY", "strength": "strong"})
                else:
                    indicators["ma_cross"] = "DEATH_CROSS"
                    if len(sma_50) >= 2 and len(sma_200) >= 2:
                        if sma_50[-2] >= sma_200[-2]:
                            patterns.append({"type": "DEATH_CROSS", "signal": "SELL", "strength": "strong"})

            # RSI for swing
            rsi = indicator_service.calculate_rsi(closes, 14)
            rsi_val = rsi[-1] if rsi else 50
            indicators["rsi_14"] = round(rsi_val, 1)
            indicators["rsi_zone"] = "overbought" if rsi_val > 70 else ("oversold" if rsi_val < 30 else "neutral")

            # MACD
            macd_line, signal_line, histogram = indicator_service.calculate_macd(closes, 12, 26, 9)
            if macd_line and signal_line:
                indicators["macd"] = round(macd_line[-1], 4)
                indicators["macd_signal"] = round(signal_line[-1], 4)
                indicators["macd_histogram"] = round(histogram[-1], 4)
                indicators["macd_bullish"] = macd_line[-1] > signal_line[-1]

                # MACD crossover
                if len(macd_line) >= 2 and len(signal_line) >= 2:
                    if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                        patterns.append({"type": "MACD_BULLISH_CROSS", "signal": "BUY", "strength": "moderate"})
                    elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                        patterns.append({"type": "MACD_BEARISH_CROSS", "signal": "SELL", "strength": "moderate"})

            # Volume analysis
            avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            indicators["volume_ratio"] = round(volumes[-1] / avg_volume, 2) if avg_volume > 0 else 1
            indicators["volume_trend"] = "HIGH" if indicators["volume_ratio"] > 1.5 else ("LOW" if indicators["volume_ratio"] < 0.5 else "NORMAL")

            # ADX for trend confirmation
            adx, plus_di, minus_di = indicator_service.calculate_adx(highs, lows, closes, 14)
            if adx:
                indicators["adx"] = round(adx[-1], 1)
                indicators["trend_strength"] = "Strong" if adx[-1] > 25 else ("Moderate" if adx[-1] > 20 else "Weak/Ranging")

        # Determine overall signal
        buy_signals = sum(1 for p in patterns if p["signal"] == "BUY")
        sell_signals = sum(1 for p in patterns if p["signal"] == "SELL")

        if buy_signals > sell_signals:
            overall_signal = "BULLISH"
        elif sell_signals > buy_signals:
            overall_signal = "BEARISH"
        else:
            overall_signal = "NEUTRAL"

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "timeframe_category": "INTRADAY" if is_intraday else "SWING",
            "current_price": current_price,
            "timestamp": datetime.now().isoformat(),
            "overall_signal": overall_signal,
            "indicators": indicators,
            "patterns": patterns,
            "recommended_actions": {
                "intraday_focus" if is_intraday else "swing_focus": [
                    "Monitor VWAP for entry/exit" if is_intraday else "Follow 50/200 SMA trend",
                    "Watch ADX > 25 for breakout confirmation" if is_intraday else "Wait for RSI extremes",
                    "Use tight stops (0.5-1% ATR)" if is_intraday else "Use wider stops (1.5-2% ATR)",
                ]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adaptive indicators error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _estimate_elliott_wave(closes: list, highs: list, lows: list) -> dict:
    """
    Estimate Elliott Wave position based on price action.
    This is a simplified estimation - real Elliott Wave analysis is complex.
    """
    if len(closes) < 50:
        return {
            "wave_count": 0,
            "wave_type": "unknown",
            "direction": "neutral",
            "current_position": "Insufficient data",
            "confidence": 0,
            "next_target": None,
            "description": "Need more price history for Elliott Wave analysis"
        }

    # Find significant swing points
    lookback = min(100, len(closes))
    recent_closes = closes[-lookback:]
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    # Calculate trend
    sma_50 = sum(closes[-50:]) / 50
    current = closes[-1]

    # Find local highs and lows for wave counting
    swing_highs = []
    swing_lows = []

    for i in range(5, lookback - 5):
        if recent_highs[i] == max(recent_highs[i-5:i+6]):
            swing_highs.append((i, recent_highs[i]))
        if recent_lows[i] == min(recent_lows[i-5:i+6]):
            swing_lows.append((i, recent_lows[i]))

    # Determine overall direction
    if current > sma_50:
        direction = "bullish"
        wave_type = "impulse"
    else:
        direction = "bearish"
        wave_type = "corrective"

    # Estimate wave count based on recent swings
    total_swings = len(swing_highs) + len(swing_lows)

    if total_swings < 3:
        wave_count = 1
        current_position = "Wave 1 developing"
        confidence = 30
    elif total_swings < 5:
        wave_count = 2
        current_position = "Wave 2-3 territory"
        confidence = 45
    elif total_swings < 8:
        wave_count = 3
        current_position = "Possible Wave 3 (strongest)"
        confidence = 55
    elif total_swings < 12:
        wave_count = 4
        current_position = "Wave 4-5 territory"
        confidence = 50
    else:
        wave_count = 5
        current_position = "Wave 5 or correction starting"
        confidence = 40

    # Estimate next target
    recent_high = max(recent_highs[-20:])
    recent_low = min(recent_lows[-20:])
    range_size = recent_high - recent_low

    if direction == "bullish":
        next_target = round(current + (range_size * 0.618), 2)  # Fibonacci extension
        description = f"Bullish {wave_type} wave in progress. Price above 50 SMA suggests continuation. Watch for resistance near ${next_target}."
    else:
        next_target = round(current - (range_size * 0.382), 2)  # Fibonacci retracement
        description = f"Bearish {wave_type} wave in progress. Price below 50 SMA suggests weakness. Support expected near ${next_target}."

    return {
        "wave_count": wave_count,
        "wave_type": wave_type,
        "direction": direction,
        "current_position": current_position,
        "confidence": confidence,
        "next_target": next_target,
        "description": description,
        "swings_detected": total_swings,
    }


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


@router.get("/adaptive/{symbol}")
async def get_adaptive_indicators(
    symbol: str,
    mode: str = Query(default="intraday", description="Trading mode: scalp, intraday, or swing"),
    auto_mode: bool = Query(default=True, description="Auto-detect optimal mode based on volatility"),
):
    """
    Get adaptive technical indicators with mode-specific parameters.

    The adaptive engine automatically adjusts indicator periods and thresholds
    based on the selected trading mode (scalp, intraday, swing) or can auto-detect
    the optimal mode based on current market volatility.
    """
    try:
        alpaca = get_alpaca_service()

        # Get historical data
        start = datetime.now() - timedelta(days=100)
        bars = await alpaca.get_bars(symbol.upper(), timeframe="1day", limit=100, start=start)

        if not bars or len(bars) < 30:
            raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

        # Extract OHLCV data
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]

        # Set mode if not auto
        if not auto_mode:
            try:
                trading_mode = TradingMode(mode.lower())
                adaptive_engine.set_mode(trading_mode, auto=False)
            except ValueError:
                trading_mode = TradingMode.INTRADAY
                adaptive_engine.set_mode(trading_mode, auto=False)
        else:
            adaptive_engine.set_mode(TradingMode.INTRADAY, auto=True)

        # Calculate adaptive indicators
        indicators = adaptive_engine.calculate_adaptive_indicators(
            highs, lows, closes, volumes
        )

        # Get mode recommendation
        recommendation = adaptive_engine.get_mode_recommendation(
            highs, lows, closes, volumes
        )

        return {
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
            "current_price": closes[-1],
            "indicators": indicators,
            "recommendation": recommendation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adaptive indicators error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adaptive/mode")
async def set_adaptive_mode(
    mode: str = Query(..., description="Trading mode: scalp, intraday, or swing"),
    auto: bool = Query(default=False, description="Enable auto-mode switching"),
):
    """
    Set the trading mode for the adaptive indicator engine.

    Modes:
    - scalp: Short timeframes, tight stops, quick trades (high volatility)
    - intraday: Same-day positions, moderate risk (moderate volatility)
    - swing: Multi-day holds, wider stops (low volatility)
    """
    try:
        if auto:
            adaptive_engine.set_mode(TradingMode.INTRADAY, auto=True)
            return {
                "success": True,
                "mode": "auto",
                "message": "Auto-mode enabled. Mode will adjust based on market volatility.",
            }

        try:
            trading_mode = TradingMode(mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be 'scalp', 'intraday', or 'swing'"
            )

        adaptive_engine.set_mode(trading_mode, auto=False)
        config = adaptive_engine.get_config()

        return {
            "success": True,
            "mode": trading_mode.value,
            "auto_mode": False,
            "config": config,
            "message": f"Mode set to {trading_mode.value}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set adaptive mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive/config")
async def get_adaptive_config():
    """
    Get the current adaptive indicator engine configuration.
    """
    return {
        "current_mode": adaptive_engine.current_mode.value,
        "auto_mode": adaptive_engine.auto_mode,
        "config": adaptive_engine.get_config(),
        "available_modes": {
            "scalp": {
                "description": "Quick trades, tight stops, high volatility environments",
                "typical_hold_time": "Minutes to 1 hour",
                "volatility_threshold": ">2.5% ATR",
            },
            "intraday": {
                "description": "Same-day positions, moderate risk",
                "typical_hold_time": "1-8 hours",
                "volatility_threshold": "0.8-2.5% ATR",
            },
            "swing": {
                "description": "Multi-day holds, wider stops, trending markets",
                "typical_hold_time": "1-7 days",
                "volatility_threshold": "<1.0% ATR",
            },
        },
    }
