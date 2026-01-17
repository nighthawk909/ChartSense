"""
News and Sentiment Integration Service
Fetches news and analyzes sentiment to inform trading decisions

This service provides:
1. Real-time news fetching for symbols
2. Sentiment analysis using AI
3. News-based trade signals
4. Event detection (earnings, FDA approvals, etc.)
"""
import asyncio
import logging
import os
import aiohttp
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentLevel(str, Enum):
    """Sentiment classification"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


class NewsCategory(str, Enum):
    """News category classification"""
    EARNINGS = "earnings"
    FDA = "fda"
    MERGER = "merger"
    LEGAL = "legal"
    ANALYST = "analyst"
    PRODUCT = "product"
    EXECUTIVE = "executive"
    MARKET = "market"
    GENERAL = "general"


@dataclass
class NewsItem:
    """A single news item"""
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    symbols: List[str]
    sentiment: SentimentLevel = SentimentLevel.NEUTRAL
    sentiment_score: float = 0.0  # -1 to 1
    category: NewsCategory = NewsCategory.GENERAL
    relevance_score: float = 0.0  # 0 to 1
    keywords: List[str] = field(default_factory=list)


@dataclass
class SymbolSentiment:
    """Aggregated sentiment for a symbol"""
    symbol: str
    overall_sentiment: SentimentLevel
    sentiment_score: float  # -1 to 1
    news_count: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    key_events: List[str]
    latest_news: List[NewsItem]
    updated_at: datetime


class NewsSentimentService:
    """
    Service for fetching and analyzing news sentiment.

    Uses multiple sources:
    1. Alpaca News API
    2. Alpha Vantage News (if available)
    3. AI-based sentiment analysis
    """

    def __init__(self, ai_advisor=None):
        """
        Initialize news sentiment service.

        Args:
            ai_advisor: AIAdvisor for sentiment analysis
        """
        self.ai_advisor = ai_advisor

        # API keys
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")

        # Cache
        self._sentiment_cache: Dict[str, SymbolSentiment] = {}
        self._news_cache: Dict[str, List[NewsItem]] = {}
        self._cache_ttl_minutes = 15

        # Configuration
        self.max_news_per_symbol = 20
        self.sentiment_lookback_hours = 24

        # Keywords for event detection
        self._earnings_keywords = ["earnings", "revenue", "profit", "quarterly", "guidance", "eps"]
        self._fda_keywords = ["fda", "approval", "clinical", "trial", "drug"]
        self._merger_keywords = ["merger", "acquisition", "buyout", "takeover"]
        self._analyst_keywords = ["upgrade", "downgrade", "target", "rating", "analyst"]

    def set_ai_advisor(self, ai_advisor):
        """Set the AI advisor"""
        self.ai_advisor = ai_advisor

    # ==================== NEWS FETCHING ====================

    async def get_news(
        self,
        symbol: str,
        limit: int = 10,
        hours_back: int = 24,
    ) -> List[NewsItem]:
        """
        Get recent news for a symbol.

        Args:
            symbol: Stock symbol
            limit: Maximum news items
            hours_back: How far back to look

        Returns:
            List of NewsItem objects
        """
        # Check cache first
        cache_key = f"{symbol}_{limit}_{hours_back}"
        cached = self._get_cached_news(cache_key)
        if cached:
            return cached

        news_items = []

        # Try Alpaca News API first
        try:
            alpaca_news = await self._fetch_alpaca_news(symbol, limit)
            news_items.extend(alpaca_news)
        except Exception as e:
            logger.debug(f"Alpaca news fetch failed for {symbol}: {e}")

        # Analyze sentiment for each news item
        for item in news_items:
            await self._analyze_item_sentiment(item)

        # Cache results
        self._cache_news(cache_key, news_items)

        return news_items[:limit]

    async def _fetch_alpaca_news(self, symbol: str, limit: int) -> List[NewsItem]:
        """Fetch news from Alpaca"""
        if not self.alpaca_api_key:
            return []

        url = "https://data.alpaca.markets/v1beta1/news"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }
        params = {
            "symbols": symbol,
            "limit": limit,
            "sort": "desc",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    news_items = []

                    for item in data.get("news", []):
                        published = datetime.fromisoformat(
                            item.get("created_at", "").replace("Z", "+00:00")
                        )

                        news_item = NewsItem(
                            title=item.get("headline", ""),
                            summary=item.get("summary", ""),
                            source=item.get("source", ""),
                            url=item.get("url", ""),
                            published_at=published,
                            symbols=item.get("symbols", [symbol]),
                        )

                        # Detect category from content
                        news_item.category = self._detect_category(
                            news_item.title + " " + news_item.summary
                        )

                        news_items.append(news_item)

                    return news_items

        except Exception as e:
            logger.error(f"Error fetching Alpaca news: {e}")
            return []

    def _detect_category(self, text: str) -> NewsCategory:
        """Detect news category from text"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in self._earnings_keywords):
            return NewsCategory.EARNINGS
        if any(kw in text_lower for kw in self._fda_keywords):
            return NewsCategory.FDA
        if any(kw in text_lower for kw in self._merger_keywords):
            return NewsCategory.MERGER
        if any(kw in text_lower for kw in self._analyst_keywords):
            return NewsCategory.ANALYST

        return NewsCategory.GENERAL

    # ==================== SENTIMENT ANALYSIS ====================

    async def _analyze_item_sentiment(self, item: NewsItem):
        """Analyze sentiment of a news item"""
        # Simple rule-based sentiment if no AI
        text = (item.title + " " + item.summary).lower()

        # Bullish keywords
        bullish_words = [
            "surge", "soar", "jump", "rally", "gain", "rise", "upgrade",
            "beat", "exceed", "strong", "growth", "breakthrough", "approval"
        ]
        # Bearish keywords
        bearish_words = [
            "fall", "drop", "plunge", "decline", "loss", "miss", "downgrade",
            "cut", "weak", "fail", "recall", "lawsuit", "investigation"
        ]

        bullish_count = sum(1 for word in bullish_words if word in text)
        bearish_count = sum(1 for word in bearish_words if word in text)

        # Calculate score
        total = bullish_count + bearish_count
        if total > 0:
            score = (bullish_count - bearish_count) / total
        else:
            score = 0

        item.sentiment_score = score

        # Classify sentiment level
        if score >= 0.5:
            item.sentiment = SentimentLevel.VERY_BULLISH
        elif score >= 0.2:
            item.sentiment = SentimentLevel.BULLISH
        elif score <= -0.5:
            item.sentiment = SentimentLevel.VERY_BEARISH
        elif score <= -0.2:
            item.sentiment = SentimentLevel.BEARISH
        else:
            item.sentiment = SentimentLevel.NEUTRAL

        # If AI is available, use it for better analysis
        if self.ai_advisor and self.ai_advisor.enabled:
            try:
                ai_sentiment = await self._ai_sentiment_analysis(item.title, item.summary)
                if ai_sentiment:
                    item.sentiment_score = ai_sentiment.get("score", score)
                    item.sentiment = self._score_to_level(item.sentiment_score)
                    item.keywords = ai_sentiment.get("keywords", [])
            except Exception as e:
                logger.debug(f"AI sentiment analysis failed: {e}")

    async def _ai_sentiment_analysis(
        self,
        title: str,
        summary: str,
    ) -> Optional[Dict[str, Any]]:
        """Use AI for sentiment analysis"""
        if not self.ai_advisor:
            return None

        # This would call the AI advisor with a prompt for sentiment analysis
        # For now, return None to use rule-based
        return None

    def _score_to_level(self, score: float) -> SentimentLevel:
        """Convert sentiment score to level"""
        if score >= 0.5:
            return SentimentLevel.VERY_BULLISH
        elif score >= 0.2:
            return SentimentLevel.BULLISH
        elif score <= -0.5:
            return SentimentLevel.VERY_BEARISH
        elif score <= -0.2:
            return SentimentLevel.BEARISH
        return SentimentLevel.NEUTRAL

    # ==================== SYMBOL SENTIMENT ====================

    async def get_symbol_sentiment(self, symbol: str) -> SymbolSentiment:
        """
        Get aggregated sentiment for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            SymbolSentiment object
        """
        # Check cache
        cached = self._sentiment_cache.get(symbol)
        if cached and (datetime.now() - cached.updated_at).seconds < self._cache_ttl_minutes * 60:
            return cached

        # Get news
        news_items = await self.get_news(
            symbol=symbol,
            limit=self.max_news_per_symbol,
            hours_back=self.sentiment_lookback_hours,
        )

        if not news_items:
            return SymbolSentiment(
                symbol=symbol,
                overall_sentiment=SentimentLevel.NEUTRAL,
                sentiment_score=0,
                news_count=0,
                bullish_count=0,
                bearish_count=0,
                neutral_count=0,
                key_events=[],
                latest_news=[],
                updated_at=datetime.now(),
            )

        # Aggregate sentiment
        bullish = sum(1 for n in news_items if n.sentiment in [SentimentLevel.BULLISH, SentimentLevel.VERY_BULLISH])
        bearish = sum(1 for n in news_items if n.sentiment in [SentimentLevel.BEARISH, SentimentLevel.VERY_BEARISH])
        neutral = len(news_items) - bullish - bearish

        # Calculate weighted average score (more recent = higher weight)
        total_weight = 0
        weighted_score = 0
        for i, item in enumerate(news_items):
            weight = 1 / (i + 1)  # More recent items have higher weight
            weighted_score += item.sentiment_score * weight
            total_weight += weight

        avg_score = weighted_score / total_weight if total_weight > 0 else 0

        # Identify key events
        key_events = []
        for item in news_items:
            if item.category in [NewsCategory.EARNINGS, NewsCategory.FDA, NewsCategory.MERGER]:
                key_events.append(f"{item.category.value}: {item.title[:50]}")

        sentiment = SymbolSentiment(
            symbol=symbol,
            overall_sentiment=self._score_to_level(avg_score),
            sentiment_score=avg_score,
            news_count=len(news_items),
            bullish_count=bullish,
            bearish_count=bearish,
            neutral_count=neutral,
            key_events=key_events[:5],
            latest_news=news_items[:5],
            updated_at=datetime.now(),
        )

        # Cache result
        self._sentiment_cache[symbol] = sentiment

        return sentiment

    # ==================== TRADE SIGNALS ====================

    async def get_sentiment_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Get a trade signal based on news sentiment.

        Returns:
            Dict with signal type, confidence, and reasoning
        """
        sentiment = await self.get_symbol_sentiment(symbol)

        signal = {
            "symbol": symbol,
            "sentiment": sentiment.overall_sentiment.value,
            "sentiment_score": sentiment.sentiment_score,
            "signal": "NEUTRAL",
            "confidence": 50,
            "reasoning": [],
            "key_events": sentiment.key_events,
            "news_count": sentiment.news_count,
        }

        # Determine signal
        if sentiment.sentiment_score >= 0.4 and sentiment.news_count >= 3:
            signal["signal"] = "BULLISH"
            signal["confidence"] = min(90, 60 + sentiment.sentiment_score * 30)
            signal["reasoning"].append(f"Strong bullish sentiment ({sentiment.sentiment_score:.2f})")

        elif sentiment.sentiment_score <= -0.4 and sentiment.news_count >= 3:
            signal["signal"] = "BEARISH"
            signal["confidence"] = min(90, 60 + abs(sentiment.sentiment_score) * 30)
            signal["reasoning"].append(f"Strong bearish sentiment ({sentiment.sentiment_score:.2f})")

        elif sentiment.sentiment_score >= 0.2:
            signal["signal"] = "MILDLY_BULLISH"
            signal["confidence"] = 55 + sentiment.sentiment_score * 20
            signal["reasoning"].append("Slightly positive news flow")

        elif sentiment.sentiment_score <= -0.2:
            signal["signal"] = "MILDLY_BEARISH"
            signal["confidence"] = 55 + abs(sentiment.sentiment_score) * 20
            signal["reasoning"].append("Slightly negative news flow")

        # Add event-based reasoning
        for event in sentiment.key_events:
            if "earnings" in event.lower():
                signal["reasoning"].append("Earnings-related news detected")
            if "fda" in event.lower():
                signal["reasoning"].append("FDA-related news detected")

        return signal

    async def should_avoid_entry(self, symbol: str) -> tuple[bool, str]:
        """
        Check if we should avoid entering a position due to news.

        Args:
            symbol: Stock symbol

        Returns:
            (should_avoid, reason)
        """
        try:
            sentiment = await self.get_symbol_sentiment(symbol)

            # Avoid on very negative sentiment
            if sentiment.sentiment_score <= -0.5:
                return True, f"Very bearish sentiment ({sentiment.sentiment_score:.2f})"

            # Avoid around earnings
            for event in sentiment.key_events:
                if "earnings" in event.lower():
                    return True, "Earnings event detected - high volatility expected"

            # Avoid if major negative news
            for item in sentiment.latest_news[:3]:
                if item.category in [NewsCategory.LEGAL] and item.sentiment_score < -0.3:
                    return True, f"Negative legal news: {item.title[:50]}"

            return False, "News sentiment acceptable"

        except Exception as e:
            logger.debug(f"Could not check news for {symbol}: {e}")
            return False, "News check skipped"

    # ==================== CACHING ====================

    def _get_cached_news(self, cache_key: str) -> Optional[List[NewsItem]]:
        """Get cached news if still valid"""
        if cache_key not in self._news_cache:
            return None

        # Simple cache - would need timestamp tracking for TTL
        return None  # Disable for now

    def _cache_news(self, cache_key: str, news: List[NewsItem]):
        """Cache news items"""
        self._news_cache[cache_key] = news

        # Limit cache size
        if len(self._news_cache) > 100:
            keys = list(self._news_cache.keys())
            for key in keys[:50]:
                del self._news_cache[key]

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "enabled": bool(self.alpaca_api_key),
            "ai_enabled": bool(self.ai_advisor and self.ai_advisor.enabled),
            "cached_symbols": list(self._sentiment_cache.keys()),
            "cache_ttl_minutes": self._cache_ttl_minutes,
            "sentiment_lookback_hours": self.sentiment_lookback_hours,
        }


# Singleton instance
_news_sentiment: Optional[NewsSentimentService] = None


def get_news_sentiment() -> NewsSentimentService:
    """Get the global news sentiment service"""
    global _news_sentiment
    if _news_sentiment is None:
        _news_sentiment = NewsSentimentService()
    return _news_sentiment
