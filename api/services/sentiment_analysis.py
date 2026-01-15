"""
Sentiment Analysis Service
Analyzes news and social media sentiment for stocks
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)


class SentimentAnalysisService:
    """
    Service for analyzing market sentiment from news and social media.
    Uses multiple data sources and AI for sentiment scoring.
    """

    def __init__(self):
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None

    async def get_news_sentiment(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get news sentiment for a stock using Alpha Vantage News API.

        Args:
            symbol: Stock symbol
            limit: Number of news articles to analyze
        """
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol.upper(),
            "limit": limit,
            "apikey": self.alpha_vantage_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)
                data = response.json()

            if "feed" not in data:
                return {"error": "No news data available"}

            articles = []
            total_sentiment = 0
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0

            for item in data["feed"][:limit]:
                # Find sentiment for our specific ticker
                ticker_sentiment = None
                for ts in item.get("ticker_sentiment", []):
                    if ts.get("ticker") == symbol.upper():
                        ticker_sentiment = ts
                        break

                if ticker_sentiment:
                    score = float(ticker_sentiment.get("ticker_sentiment_score", 0))
                    label = ticker_sentiment.get("ticker_sentiment_label", "Neutral")

                    total_sentiment += score

                    if score > 0.15:
                        bullish_count += 1
                    elif score < -0.15:
                        bearish_count += 1
                    else:
                        neutral_count += 1

                    articles.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", ""),
                        "published": item.get("time_published", ""),
                        "sentiment_score": score,
                        "sentiment_label": label,
                        "relevance": float(ticker_sentiment.get("relevance_score", 0)),
                    })

            avg_sentiment = total_sentiment / len(articles) if articles else 0

            # Determine overall sentiment
            if avg_sentiment > 0.15:
                overall = "BULLISH"
            elif avg_sentiment < -0.15:
                overall = "BEARISH"
            else:
                overall = "NEUTRAL"

            return {
                "symbol": symbol.upper(),
                "overall_sentiment": overall,
                "average_score": avg_sentiment,
                "bullish_articles": bullish_count,
                "bearish_articles": bearish_count,
                "neutral_articles": neutral_count,
                "total_articles": len(articles),
                "articles": articles,
            }

        except Exception as e:
            logger.error(f"Error fetching news sentiment: {e}")
            return {"error": str(e)}

    async def analyze_with_ai(self, symbol: str, news_data: Dict) -> Dict[str, Any]:
        """
        Use OpenAI to provide deeper sentiment analysis.
        """
        if not self.openai_client:
            return {"error": "OpenAI not configured"}

        articles = news_data.get("articles", [])
        if not articles:
            return {"error": "No articles to analyze"}

        # Prepare news summary for AI
        news_summary = "\n".join([
            f"- {a['title']} (Sentiment: {a['sentiment_label']}, Score: {a['sentiment_score']:.2f})"
            for a in articles[:5]
        ])

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a financial sentiment analyst. Analyze the news sentiment
                        for stocks and provide actionable insights. Be concise and focus on trading implications."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze the following news for {symbol}:

{news_summary}

Provide:
1. Overall sentiment (Bullish/Bearish/Neutral)
2. Key themes in the news
3. Potential price impact (High/Medium/Low)
4. Trading recommendation
5. Risk factors to consider

Format as JSON with keys: sentiment, themes, impact, recommendation, risks"""
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )

            import json
            content = response.choices[0].message.content

            # Try to parse as JSON
            try:
                # Clean up the response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                ai_analysis = json.loads(content)
            except:
                ai_analysis = {"raw_analysis": content}

            return {
                "symbol": symbol,
                "ai_analysis": ai_analysis,
                "model": "gpt-4o-mini",
            }

        except Exception as e:
            logger.error(f"AI sentiment analysis error: {e}")
            return {"error": str(e)}

    async def get_market_fear_greed(self) -> Dict[str, Any]:
        """
        Get overall market fear/greed sentiment.
        Uses multiple indicators to calculate market mood.
        """
        # This would ideally use multiple data sources
        # For now, we'll use a simplified approach

        indicators = {
            "vix_level": "unknown",  # VIX index
            "put_call_ratio": "unknown",
            "market_momentum": "unknown",
            "safe_haven_demand": "unknown",
        }

        # In a full implementation, we'd fetch:
        # 1. VIX (fear index)
        # 2. Put/Call ratio
        # 3. Market breadth (advancing vs declining stocks)
        # 4. Junk bond demand
        # 5. Safe haven demand (gold, treasuries)

        return {
            "index": 50,  # Placeholder
            "classification": "NEUTRAL",
            "indicators": indicators,
            "last_updated": datetime.now().isoformat(),
            "note": "Full fear/greed calculation requires additional data sources"
        }

    async def get_social_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Placeholder for social media sentiment analysis.
        Would integrate with Twitter/X, Reddit, StockTwits, etc.
        """
        # This would require API access to social platforms
        # For now, return placeholder data

        return {
            "symbol": symbol,
            "source": "social_media",
            "status": "not_implemented",
            "note": "Social media sentiment requires Twitter/Reddit API access",
            "placeholder_data": {
                "twitter_mentions": 0,
                "reddit_mentions": 0,
                "stocktwits_sentiment": "neutral",
            }
        }

    async def get_full_sentiment_report(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive sentiment report combining all sources.
        """
        news_sentiment = await self.get_news_sentiment(symbol)

        report = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "news_sentiment": news_sentiment,
        }

        # Add AI analysis if available
        if self.openai_client and "error" not in news_sentiment:
            ai_analysis = await self.analyze_with_ai(symbol, news_sentiment)
            report["ai_analysis"] = ai_analysis

        # Calculate composite score
        if "average_score" in news_sentiment:
            news_score = news_sentiment["average_score"]

            # Convert to 0-100 scale
            composite_score = (news_score + 1) * 50  # -1 to 1 -> 0 to 100

            if composite_score >= 65:
                recommendation = "BULLISH"
            elif composite_score <= 35:
                recommendation = "BEARISH"
            else:
                recommendation = "NEUTRAL"

            report["composite_score"] = composite_score
            report["recommendation"] = recommendation

        return report


# Singleton instance
_sentiment_service = None

def get_sentiment_service() -> SentimentAnalysisService:
    """Get singleton sentiment service instance"""
    global _sentiment_service
    if _sentiment_service is None:
        _sentiment_service = SentimentAnalysisService()
    return _sentiment_service
