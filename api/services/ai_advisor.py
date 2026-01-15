"""
AI Advisor Service - OpenAI Integration
Uses GPT to provide intelligent stock analysis and recommendations
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AIAdvisor:
    """
    AI-powered trading advisor using OpenAI GPT.
    Provides intelligent analysis, stock recommendations, and trade suggestions.
    """

    def __init__(self):
        """Initialize the AI advisor with OpenAI client"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self._client = None
        self.model = "gpt-4o"  # Use GPT-4o for best results
        self.enabled = bool(self.api_key and self.api_key.startswith("sk-"))

        if not self.enabled:
            logger.warning("OpenAI API key not configured - AI advisor disabled")

    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None and self.enabled:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("openai package not installed")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.enabled = False
        return self._client

    async def analyze_stock(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        fundamental_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get AI analysis of a stock based on technical and fundamental data.

        Args:
            symbol: Stock symbol
            technical_data: Dict with indicators (RSI, MACD, etc.)
            fundamental_data: Optional dict with P/E, EPS, etc.

        Returns:
            Dict with AI analysis, recommendation, and confidence
        """
        if not self.enabled:
            return self._fallback_analysis(symbol, technical_data)

        client = self._get_client()
        if not client:
            return self._fallback_analysis(symbol, technical_data)

        try:
            prompt = self._build_analysis_prompt(symbol, technical_data, fundamental_data)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert stock trading analyst. Analyze the provided
                        technical indicators and provide a clear recommendation. Be concise and actionable.
                        Always respond in valid JSON format with these fields:
                        - recommendation: "BUY", "SELL", or "HOLD"
                        - confidence: number 0-100
                        - analysis: brief explanation (2-3 sentences)
                        - key_factors: array of main factors influencing decision
                        - risk_level: "LOW", "MEDIUM", or "HIGH"
                        - suggested_entry: price to enter (if BUY)
                        - suggested_stop_loss: stop loss price
                        - suggested_target: profit target price
                        - trade_type: "SWING" or "LONG_TERM"
                        """
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = response.choices[0].message.content

            # Parse JSON response
            try:
                analysis = json.loads(result)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    return self._fallback_analysis(symbol, technical_data)

            analysis["ai_generated"] = True
            analysis["model"] = self.model
            analysis["timestamp"] = datetime.now().isoformat()

            logger.info(f"AI analysis for {symbol}: {analysis['recommendation']} ({analysis['confidence']}%)")
            return analysis

        except Exception as e:
            logger.error(f"AI analysis failed for {symbol}: {e}")
            return self._fallback_analysis(symbol, technical_data)

    async def discover_stocks(
        self,
        market_conditions: Optional[str] = None,
        sector_preference: Optional[str] = None,
        risk_tolerance: str = "moderate",
    ) -> List[Dict[str, Any]]:
        """
        Use AI to discover promising stocks to trade.

        Args:
            market_conditions: Current market state description
            sector_preference: Preferred sector (tech, healthcare, etc.)
            risk_tolerance: "conservative", "moderate", or "aggressive"

        Returns:
            List of stock recommendations with reasoning
        """
        if not self.enabled:
            return self._get_default_watchlist()

        client = self._get_client()
        if not client:
            return self._get_default_watchlist()

        try:
            prompt = f"""Based on current market conditions, suggest 10 stocks that would be good
            candidates for swing trading and long-term positions.

            Risk tolerance: {risk_tolerance}
            {"Sector preference: " + sector_preference if sector_preference else "No sector preference"}
            {"Market conditions: " + market_conditions if market_conditions else ""}

            For each stock, provide:
            - symbol: ticker symbol
            - name: company name
            - reason: why this stock (1-2 sentences)
            - trade_type: SWING or LONG_TERM
            - risk_level: LOW, MEDIUM, or HIGH
            - sector: industry sector

            Focus on liquid, well-known stocks with good trading volume.
            Include a mix of tech, healthcare, finance, and consumer sectors.

            Respond in JSON format as an array of objects."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert stock screener. Provide actionable stock picks based on current market dynamics. Always respond in valid JSON array format."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000,
            )

            result = response.choices[0].message.content

            # Parse JSON response
            try:
                stocks = json.loads(result)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    stocks = json.loads(json_match.group())
                else:
                    return self._get_default_watchlist()

            logger.info(f"AI discovered {len(stocks)} stock candidates")
            return stocks

        except Exception as e:
            logger.error(f"AI stock discovery failed: {e}")
            return self._get_default_watchlist()

    async def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Get AI analysis of overall market sentiment.

        Returns:
            Dict with market sentiment and recommendations
        """
        if not self.enabled:
            return {
                "sentiment": "neutral",
                "confidence": 50,
                "recommendation": "Proceed with normal trading",
                "ai_generated": False,
            }

        client = self._get_client()
        if not client:
            return {"sentiment": "neutral", "confidence": 50, "ai_generated": False}

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a market analyst. Provide brief market sentiment analysis. Respond in JSON."
                    },
                    {
                        "role": "user",
                        "content": """Analyze current market sentiment for US stocks. Consider:
                        - Recent market trends
                        - Economic indicators
                        - Sector rotations

                        Respond with JSON containing:
                        - sentiment: "bullish", "bearish", or "neutral"
                        - confidence: 0-100
                        - key_factors: array of factors
                        - recommendation: trading advice (1 sentence)
                        - sectors_to_watch: array of promising sectors
                        - sectors_to_avoid: array of risky sectors"""
                    }
                ],
                temperature=0.3,
                max_tokens=400,
            )

            result = response.choices[0].message.content
            sentiment = json.loads(result)
            sentiment["ai_generated"] = True
            sentiment["timestamp"] = datetime.now().isoformat()

            return sentiment

        except Exception as e:
            logger.error(f"Market sentiment analysis failed: {e}")
            return {"sentiment": "neutral", "confidence": 50, "ai_generated": False}

    async def optimize_trade_parameters(
        self,
        symbol: str,
        entry_price: float,
        technical_data: Dict[str, Any],
        account_equity: float,
    ) -> Dict[str, Any]:
        """
        Get AI-optimized trade parameters.

        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            technical_data: Technical indicators
            account_equity: Available capital

        Returns:
            Optimized stop-loss, target, and position size
        """
        if not self.enabled:
            # Return defaults
            return {
                "stop_loss_pct": 0.05,
                "profit_target_pct": 0.10,
                "position_size_pct": 0.15,
                "ai_generated": False,
            }

        client = self._get_client()
        if not client:
            return {"stop_loss_pct": 0.05, "profit_target_pct": 0.10, "ai_generated": False}

        try:
            prompt = f"""Optimize trade parameters for {symbol}:
            - Entry price: ${entry_price:.2f}
            - Account equity: ${account_equity:.2f}
            - RSI: {technical_data.get('rsi_14', 'N/A')}
            - ATR: {technical_data.get('atr', 'N/A')}
            - Volatility: {technical_data.get('atr_pct', 'N/A')}%

            Provide optimal parameters as JSON:
            - stop_loss_pct: percentage below entry (0.01-0.10)
            - profit_target_pct: percentage above entry (0.05-0.25)
            - position_size_pct: percentage of equity to risk (0.05-0.20)
            - reasoning: brief explanation"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a risk management expert. Optimize trade parameters."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300,
            )

            result = response.choices[0].message.content
            params = json.loads(result)
            params["ai_generated"] = True

            return params

        except Exception as e:
            logger.error(f"Trade parameter optimization failed: {e}")
            return {"stop_loss_pct": 0.05, "profit_target_pct": 0.10, "ai_generated": False}

    def _build_analysis_prompt(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        fundamental_data: Optional[Dict[str, Any]],
    ) -> str:
        """Build the analysis prompt for GPT"""
        prompt = f"""Analyze {symbol} for trading opportunity:

TECHNICAL INDICATORS:
- Current Price: ${technical_data.get('current_price', 'N/A')}
- RSI (14): {technical_data.get('rsi_14', 'N/A')}
- MACD Line: {technical_data.get('macd_line', 'N/A')}
- MACD Signal: {technical_data.get('macd_signal', 'N/A')}
- MACD Histogram: {technical_data.get('macd_histogram', 'N/A')}
- SMA 20: ${technical_data.get('sma_20', 'N/A')}
- SMA 50: ${technical_data.get('sma_50', 'N/A')}
- SMA 200: ${technical_data.get('sma_200', 'N/A')}
- Bollinger Upper: ${technical_data.get('bb_upper', 'N/A')}
- Bollinger Lower: ${technical_data.get('bb_lower', 'N/A')}
- ATR: ${technical_data.get('atr', 'N/A')}
- Volume vs Avg: {technical_data.get('volume_ratio', 'N/A')}x
"""
        if fundamental_data:
            prompt += f"""
FUNDAMENTALS:
- P/E Ratio: {fundamental_data.get('pe_ratio', 'N/A')}
- EPS: ${fundamental_data.get('eps', 'N/A')}
- Market Cap: ${fundamental_data.get('market_cap', 'N/A')}
- 52-Week High: ${fundamental_data.get('week_52_high', 'N/A')}
- 52-Week Low: ${fundamental_data.get('week_52_low', 'N/A')}
"""
        return prompt

    def _fallback_analysis(self, symbol: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI is unavailable"""
        rsi = technical_data.get('rsi_14', 50)
        macd_hist = technical_data.get('macd_histogram', 0)

        if rsi < 30 and macd_hist > 0:
            recommendation = "BUY"
            confidence = 70
        elif rsi > 70 and macd_hist < 0:
            recommendation = "SELL"
            confidence = 70
        else:
            recommendation = "HOLD"
            confidence = 50

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "analysis": "Based on technical indicators only (AI unavailable)",
            "key_factors": ["RSI", "MACD"],
            "risk_level": "MEDIUM",
            "ai_generated": False,
        }

    def _get_default_watchlist(self) -> List[Dict[str, Any]]:
        """Return default watchlist when AI is unavailable"""
        return [
            {"symbol": "AAPL", "name": "Apple Inc.", "reason": "Tech leader with strong fundamentals", "trade_type": "LONG_TERM", "risk_level": "LOW", "sector": "Technology"},
            {"symbol": "MSFT", "name": "Microsoft Corp", "reason": "Cloud computing growth", "trade_type": "LONG_TERM", "risk_level": "LOW", "sector": "Technology"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "reason": "AI and advertising dominance", "trade_type": "LONG_TERM", "risk_level": "MEDIUM", "sector": "Technology"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "reason": "E-commerce and AWS leader", "trade_type": "LONG_TERM", "risk_level": "MEDIUM", "sector": "Consumer"},
            {"symbol": "NVDA", "name": "NVIDIA Corp", "reason": "AI chip leader with strong momentum", "trade_type": "SWING", "risk_level": "MEDIUM", "sector": "Technology"},
            {"symbol": "META", "name": "Meta Platforms", "reason": "Social media and VR potential", "trade_type": "SWING", "risk_level": "MEDIUM", "sector": "Technology"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "reason": "EV market leader, high volatility", "trade_type": "SWING", "risk_level": "HIGH", "sector": "Automotive"},
            {"symbol": "JPM", "name": "JPMorgan Chase", "reason": "Banking sector strength", "trade_type": "LONG_TERM", "risk_level": "LOW", "sector": "Finance"},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "reason": "Healthcare stability", "trade_type": "LONG_TERM", "risk_level": "LOW", "sector": "Healthcare"},
            {"symbol": "V", "name": "Visa Inc.", "reason": "Payment processing growth", "trade_type": "LONG_TERM", "risk_level": "LOW", "sector": "Finance"},
        ]


# Singleton instance
_ai_advisor: Optional[AIAdvisor] = None


def get_ai_advisor() -> AIAdvisor:
    """Get or create AI advisor singleton"""
    global _ai_advisor
    if _ai_advisor is None:
        _ai_advisor = AIAdvisor()
    return _ai_advisor
