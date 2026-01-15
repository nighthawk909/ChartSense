"""
AI Advisor API Routes
Endpoints for AI-powered stock analysis and recommendations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from services.ai_advisor import get_ai_advisor
from services.alpha_vantage import AlphaVantageService
from services.indicators import IndicatorService

router = APIRouter()


class StockAnalysisRequest(BaseModel):
    """Request for stock analysis"""
    symbol: str
    include_fundamentals: bool = True


class StockRecommendation(BaseModel):
    """Stock recommendation from AI"""
    symbol: str
    name: str
    reason: str
    trade_type: str
    risk_level: str
    sector: str


@router.get("/analyze/{symbol}")
async def analyze_stock(symbol: str, include_fundamentals: bool = True):
    """
    Get AI-powered analysis for a stock.

    Uses OpenAI GPT to analyze technical indicators and provide
    trading recommendations with confidence scores.
    """
    advisor = get_ai_advisor()
    av_service = AlphaVantageService()
    indicator_service = IndicatorService()

    try:
        # Get historical data
        history = await av_service.get_history(symbol.upper(), "daily")
        if not history or not history.prices:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        prices = history.prices
        data = history.data

        # Calculate technical indicators
        highs = [d.high for d in data]
        lows = [d.low for d in data]
        volumes = [d.volume for d in data]

        rsi = indicator_service.calculate_rsi(prices, 14)
        macd_line, signal_line, histogram = indicator_service.calculate_macd(prices)
        sma_20 = indicator_service.calculate_sma(prices, 20)
        sma_50 = indicator_service.calculate_sma(prices, 50)
        sma_200 = indicator_service.calculate_sma(prices, 200) if len(prices) >= 200 else []
        upper, middle, lower = indicator_service.calculate_bollinger_bands(prices)
        atr = indicator_service.calculate_atr(highs, lows, prices, 14)

        technical_data = {
            "current_price": prices[-1] if prices else 0,
            "rsi_14": rsi[-1] if rsi else 50,
            "macd_line": macd_line[-1] if macd_line else 0,
            "macd_signal": signal_line[-1] if signal_line else 0,
            "macd_histogram": histogram[-1] if histogram else 0,
            "sma_20": sma_20[-1] if sma_20 else 0,
            "sma_50": sma_50[-1] if sma_50 else 0,
            "sma_200": sma_200[-1] if sma_200 else 0,
            "bb_upper": upper[-1] if upper else 0,
            "bb_lower": lower[-1] if lower else 0,
            "atr": atr[-1] if atr else 0,
            "volume_ratio": volumes[-1] / (sum(volumes[-20:]) / 20) if len(volumes) >= 20 else 1,
        }

        # Get fundamentals if requested
        fundamental_data = None
        if include_fundamentals:
            try:
                overview = await av_service.get_company_overview(symbol.upper())
                if overview:
                    fundamental_data = {
                        "pe_ratio": overview.pe_ratio,
                        "eps": overview.eps,
                        "market_cap": overview.market_cap,
                        "week_52_high": overview.week_52_high,
                        "week_52_low": overview.week_52_low,
                    }
            except:
                pass  # Fundamentals are optional

        # Get AI analysis
        analysis = await advisor.analyze_stock(symbol.upper(), technical_data, fundamental_data)
        analysis["symbol"] = symbol.upper()
        analysis["technical_data"] = technical_data

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/discover", response_model=List[StockRecommendation])
async def discover_stocks(
    risk_tolerance: str = Query("moderate", enum=["conservative", "moderate", "aggressive"]),
    sector: Optional[str] = None,
):
    """
    Discover promising stocks to trade using AI.

    Returns a list of stock recommendations based on current market
    conditions and the specified risk tolerance.
    """
    advisor = get_ai_advisor()

    try:
        stocks = await advisor.discover_stocks(
            risk_tolerance=risk_tolerance,
            sector_preference=sector,
        )

        return [
            StockRecommendation(
                symbol=s.get("symbol", ""),
                name=s.get("name", ""),
                reason=s.get("reason", ""),
                trade_type=s.get("trade_type", "SWING"),
                risk_level=s.get("risk_level", "MEDIUM"),
                sector=s.get("sector", ""),
            )
            for s in stocks
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/sentiment")
async def get_market_sentiment():
    """
    Get AI analysis of overall market sentiment.

    Returns bullish/bearish/neutral sentiment with confidence
    and sector recommendations.
    """
    advisor = get_ai_advisor()

    try:
        sentiment = await advisor.get_market_sentiment()
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.get("/status")
async def get_ai_status():
    """
    Check if AI advisor is enabled and working.
    """
    advisor = get_ai_advisor()

    return {
        "enabled": advisor.enabled,
        "model": advisor.model if advisor.enabled else None,
        "message": "AI advisor is active" if advisor.enabled else "OpenAI API key not configured",
    }
