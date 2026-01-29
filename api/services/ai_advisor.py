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

    async def evaluate_stock_trade(
        self,
        symbol: str,
        signal_data: Dict[str, Any],
        current_price: float,
        account_info: Dict[str, Any],
        existing_positions: List[str] = [],
    ) -> Dict[str, Any]:
        """
        AI evaluates whether to execute a stock trade.
        This is the TRUE AI control for stocks - the AI makes the final decision.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            signal_data: Trading signal with score, indicators, etc.
            current_price: Current stock price
            account_info: Account equity, buying power, etc.
            existing_positions: List of stocks already held

        Returns:
            Dict with AI decision, reasoning, and trade parameters
        """
        if not self.enabled:
            return self._fallback_stock_decision(symbol, signal_data, error_reason="API key not configured")

        client = self._get_client()
        if not client:
            return self._fallback_stock_decision(symbol, signal_data, error_reason="Failed to initialize OpenAI client")

        try:
            # Build comprehensive prompt for AI evaluation
            prompt = f"""You are a stock trading AI making a real trading decision. Evaluate this opportunity carefully.

STOCK: {symbol}
CURRENT PRICE: ${current_price:,.2f}

TRADING SIGNAL:
- Signal Type: {signal_data.get('signal_type', 'N/A')}
- Score: {signal_data.get('score', 'N/A')}/100
- Trade Type: {signal_data.get('trade_type', 'N/A')}
- Suggested Stop Loss: ${signal_data.get('suggested_stop_loss', 'N/A')}
- Suggested Target: ${signal_data.get('suggested_profit_target', 'N/A')}

TECHNICAL INDICATORS:
- RSI: {signal_data.get('indicators', {}).get('rsi_14', 'N/A')}
- MACD: {signal_data.get('indicators', {}).get('macd_histogram', 'N/A')}
- Trend (SMA): {signal_data.get('indicators', {}).get('trend', 'N/A')}
- Volume Ratio: {signal_data.get('indicators', {}).get('volume_ratio', 'N/A')}x
- ATR: {signal_data.get('indicators', {}).get('atr', 'N/A')}

ACCOUNT STATUS:
- Equity: ${account_info.get('equity', 0):,.2f}
- Buying Power: ${account_info.get('buying_power', 0):,.2f}
- Current Positions: {len(existing_positions)} ({', '.join(existing_positions[:5]) if existing_positions else 'None'})

DECISION REQUIRED:
Should we BUY {symbol} right now? Consider:
1. Is the technical setup strong enough?
2. Is this a good entry point or should we wait?
3. Are there any red flags in the indicators?
4. Portfolio diversification and sector exposure
5. Market conditions and timing

Respond with JSON:
{{
    "decision": "APPROVE" or "REJECT" or "WAIT",
    "confidence": 0-100,
    "reasoning": "2-3 sentence explanation of your decision",
    "concerns": ["list", "of", "concerns"] or [],
    "suggested_position_size_pct": 0.01-0.05 (if APPROVE),
    "suggested_stop_loss_pct": 0.02-0.10 (if APPROVE),
    "suggested_take_profit_pct": 0.05-0.20 (if APPROVE),
    "wait_for": "condition to wait for" (if WAIT)
}}"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert stock trading AI. You have final authority on trade decisions.
                        Be conservative - only approve trades with strong setups. It's better to miss an opportunity
                        than to enter a bad trade. Consider market conditions, technical signals, and portfolio risk.
                        Always respond in valid JSON format."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temp for consistent decisions
                max_tokens=500,
            )

            result = response.choices[0].message.content

            # Parse JSON response
            try:
                decision = json.loads(result)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    return self._fallback_stock_decision(symbol, signal_data)

            decision["ai_generated"] = True
            decision["model"] = self.model
            decision["timestamp"] = datetime.now().isoformat()
            decision["symbol"] = symbol

            logger.info(f"AI stock decision for {symbol}: {decision['decision']} ({decision['confidence']}%) - {decision['reasoning'][:100]}")
            return decision

        except Exception as e:
            error_msg = str(e)
            # Check for specific error types and give clear messages
            error_reason = self._parse_openai_error(error_msg)
            logger.error(f"AI stock evaluation failed for {symbol}: {error_msg}")
            return self._fallback_stock_decision(symbol, signal_data, error_reason=error_reason)

    def _parse_openai_error(self, error_msg: str) -> str:
        """Parse OpenAI error messages into user-friendly reasons"""
        error_lower = error_msg.lower()
        if "insufficient_quota" in error_lower or "exceeded your current quota" in error_lower:
            return "QUOTA EXCEEDED - Add billing at platform.openai.com/account/billing"
        elif "rate_limit" in error_lower or "429" in error_msg:
            return "Rate limited - too many requests, will retry"
        elif "invalid_api_key" in error_lower or "401" in error_msg:
            return "Invalid API key - check OPENAI_API_KEY in .env"
        elif "connection" in error_lower or "timeout" in error_lower:
            return "Network error - check internet connection"
        elif "model" in error_lower and "not found" in error_lower:
            return "Model not available - check OpenAI subscription"
        else:
            return error_msg[:80]

    def _fallback_stock_decision(self, symbol: str, signal_data: Dict[str, Any], error_reason: str = None) -> Dict[str, Any]:
        """Fallback decision when AI is unavailable for stocks - uses signal data only"""
        score = signal_data.get('score', 50)
        signal_type = signal_data.get('signal_type', 'HOLD')

        # Determine why AI is unavailable
        if not self.enabled:
            ai_status = "API key not configured"
        elif error_reason:
            ai_status = error_reason
        else:
            ai_status = "Unknown error"

        logger.warning(f"Using fallback for {symbol}: {ai_status}")

        # Without AI, we're more conservative
        # Only APPROVE if score is very high (75+) since we don't have AI confirmation
        if signal_type == 'BUY' and score >= 75:
            decision = "APPROVE"
            confidence = min(score, 70)  # Cap confidence without AI
            reasoning = f"Technical score {score}% exceeds high-confidence threshold. AI status: {ai_status}"
            concerns = [f"AI unavailable ({ai_status}) - approved based on strong technicals only"]
        elif signal_type == 'BUY' and score >= 65:
            decision = "WAIT"
            confidence = 50
            reasoning = f"Score {score}% meets threshold but AI unavailable ({ai_status}). Waiting for stronger signal."
            concerns = [f"AI status: {ai_status}", "Waiting for AI availability or stronger signal"]
        else:
            # Low score - this is NOT an AI rejection, it's a technical skip
            decision = "WAIT"  # Changed from REJECT - can't reject without AI evaluation
            confidence = score
            reasoning = f"Technical score {score}% below threshold (65%). Waiting for better setup."
            concerns = ["Score below threshold - needs stronger technical signal", "AI unavailable for deeper analysis"]

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "concerns": concerns,
            "suggested_position_size_pct": 0.02,
            "suggested_stop_loss_pct": 0.05,
            "suggested_take_profit_pct": 0.10,
            "ai_generated": False,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
        }

    async def evaluate_crypto_trade(
        self,
        symbol: str,
        technical_analysis: Dict[str, Any],
        current_price: float,
        account_info: Dict[str, Any],
        existing_positions: List[str] = [],
    ) -> Dict[str, Any]:
        """
        AI evaluates whether to execute a crypto trade.
        This is the TRUE AI control - the AI makes the final decision.

        Args:
            symbol: Crypto symbol (e.g., "BTC/USD")
            technical_analysis: Technical indicators and signals
            current_price: Current price
            account_info: Account equity, buying power, etc.
            existing_positions: List of cryptos already held

        Returns:
            Dict with AI decision, reasoning, and trade parameters
        """
        if not self.enabled:
            return self._fallback_crypto_decision(symbol, technical_analysis, error_reason="API key not configured")

        client = self._get_client()
        if not client:
            return self._fallback_crypto_decision(symbol, technical_analysis, error_reason="Failed to initialize OpenAI client")

        try:
            # Build comprehensive prompt for AI evaluation
            prompt = f"""You are a crypto trading AI making a real trading decision. Evaluate this opportunity carefully.

CRYPTO: {symbol}
CURRENT PRICE: ${current_price:,.2f}

TECHNICAL ANALYSIS:
- Signal: {technical_analysis.get('recommendation', 'N/A')}
- Score: {technical_analysis.get('score', 'N/A')}/100
- RSI: {technical_analysis.get('indicators', {}).get('rsi', 'N/A')}
- MACD Signal: {technical_analysis.get('indicators', {}).get('macd_signal', 'N/A')}
- Trend: {technical_analysis.get('indicators', {}).get('trend', 'N/A')}
- Technical Signals: {', '.join(technical_analysis.get('signals', []))}

ACCOUNT STATUS:
- Equity: ${account_info.get('equity', 0):,.2f}
- Buying Power: ${account_info.get('buying_power', 0):,.2f}
- Existing Crypto Positions: {', '.join(existing_positions) if existing_positions else 'None'}

DECISION REQUIRED:
Should we BUY {symbol} right now? Consider:
1. Is the technical setup strong enough?
2. Is this a good entry point or should we wait?
3. Are there any red flags in the indicators?
4. Portfolio diversification (already holding: {', '.join(existing_positions) if existing_positions else 'nothing'})

Respond with JSON:
{{
    "decision": "APPROVE" or "REJECT" or "WAIT",
    "confidence": 0-100,
    "reasoning": "2-3 sentence explanation of your decision",
    "concerns": ["list", "of", "concerns"] or [],
    "suggested_position_size_pct": 0.01-0.05 (if APPROVE),
    "suggested_stop_loss_pct": 0.02-0.10 (if APPROVE),
    "suggested_take_profit_pct": 0.05-0.20 (if APPROVE),
    "wait_for": "condition to wait for" (if WAIT)
}}"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert crypto trading AI. You have final authority on trade decisions.
                        Be conservative - only approve trades with strong setups. It's better to miss an opportunity
                        than to enter a bad trade. Consider market conditions, technical signals, and portfolio risk.
                        Always respond in valid JSON format."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temp for consistent decisions
                max_tokens=500,
            )

            result = response.choices[0].message.content

            # Parse JSON response
            try:
                decision = json.loads(result)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    return self._fallback_crypto_decision(symbol, technical_analysis, error_reason="Failed to parse AI JSON response")

            decision["ai_generated"] = True
            decision["model"] = self.model
            decision["timestamp"] = datetime.now().isoformat()
            decision["symbol"] = symbol

            logger.info(f"AI crypto decision for {symbol}: {decision['decision']} ({decision['confidence']}%) - {decision['reasoning'][:100]}")
            return decision

        except Exception as e:
            error_msg = str(e)
            error_reason = self._parse_openai_error(error_msg)
            logger.error(f"AI crypto evaluation failed for {symbol}: {error_msg}")
            return self._fallback_crypto_decision(symbol, technical_analysis, error_reason=error_reason)

    async def get_crypto_market_analysis(self) -> Dict[str, Any]:
        """
        Get AI analysis of overall crypto market conditions.

        Returns:
            Dict with market sentiment, recommendations, and cryptos to watch
        """
        if not self.enabled:
            return {
                "sentiment": "neutral",
                "confidence": 50,
                "recommendation": "Proceed with caution",
                "cryptos_to_watch": ["BTC/USD", "ETH/USD"],
                "cryptos_to_avoid": [],
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
                        "content": "You are a crypto market analyst. Provide brief market analysis. Respond in JSON."
                    },
                    {
                        "role": "user",
                        "content": """Analyze current crypto market conditions. Consider:
                        - Bitcoin dominance and trend
                        - Altcoin season indicators
                        - Market fear/greed
                        - Recent news and events

                        Respond with JSON containing:
                        - sentiment: "bullish", "bearish", or "neutral"
                        - confidence: 0-100
                        - bitcoin_outlook: brief BTC analysis
                        - altcoin_outlook: brief altcoin analysis
                        - recommendation: trading advice (1-2 sentences)
                        - cryptos_to_watch: array of promising cryptos
                        - cryptos_to_avoid: array of risky cryptos
                        - risk_level: "LOW", "MEDIUM", or "HIGH"
                        - best_strategy: "accumulate", "trade_swings", or "stay_cash" """
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = response.choices[0].message.content
            analysis = json.loads(result)
            analysis["ai_generated"] = True
            analysis["timestamp"] = datetime.now().isoformat()

            logger.info(f"AI crypto market analysis: {analysis['sentiment']} ({analysis['confidence']}%)")
            return analysis

        except Exception as e:
            logger.error(f"Crypto market analysis failed: {e}")
            return {"sentiment": "neutral", "confidence": 50, "ai_generated": False}

    def _fallback_crypto_decision(self, symbol: str, technical_analysis: Dict[str, Any], error_reason: str = None) -> Dict[str, Any]:
        """Fallback decision when AI is unavailable - uses technical analysis only"""
        score = technical_analysis.get('score', 50)
        recommendation = technical_analysis.get('recommendation', 'HOLD')

        # Determine why AI is unavailable
        if not self.enabled:
            ai_status = "API key not configured"
        elif error_reason:
            ai_status = error_reason
        else:
            ai_status = "Unknown error"

        logger.warning(f"Using crypto fallback for {symbol}: {ai_status}")

        # Without AI, we're more conservative
        if recommendation in ['BUY', 'STRONG_BUY'] and score >= 75:
            decision = "APPROVE"
            confidence = min(score, 70)  # Cap confidence without AI
            reasoning = f"Technical signals strong (Score: {score}%, Signal: {recommendation}). AI status: {ai_status}"
            concerns = [f"AI status: {ai_status}", "Approved based on strong technicals only"]
        elif recommendation in ['BUY', 'STRONG_BUY'] and score >= 65:
            decision = "WAIT"
            confidence = 50
            reasoning = f"Technical signals positive but AI unavailable ({ai_status}). Score: {score}%, Signal: {recommendation}."
            concerns = [f"AI status: {ai_status}", "Score below 75% threshold for auto-approval", "Waiting for better setup"]
        else:
            # Changed from REJECT to WAIT - we can't reject without AI evaluation
            decision = "WAIT"
            confidence = 40
            reasoning = f"Technical score {score}% below threshold (75%). AI status: {ai_status}. Waiting for better setup."
            concerns = ["Score below entry threshold", f"AI status: {ai_status}", "Will re-evaluate when conditions improve"]

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "concerns": concerns,
            "suggested_position_size_pct": 0.02,
            "suggested_stop_loss_pct": 0.05,
            "suggested_take_profit_pct": 0.10,
            "ai_generated": False,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
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
