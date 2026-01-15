"""
Calendar Service
Earnings calendar and economic events integration
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Service for tracking earnings reports and economic events.
    Helps avoid trading around high-volatility events.
    """

    def __init__(self):
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    async def get_earnings_calendar(
        self,
        symbol: str = None,
        horizon: str = "3month"
    ) -> Dict[str, Any]:
        """
        Get upcoming earnings dates.

        Args:
            symbol: Optional - filter by specific stock
            horizon: Time horizon - 3month, 6month, 12month
        """
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "EARNINGS_CALENDAR",
            "horizon": horizon,
            "apikey": self.alpha_vantage_key,
        }

        if symbol:
            params["symbol"] = symbol.upper()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30.0)

                # This endpoint returns CSV data
                if response.status_code == 200:
                    content = response.text
                    lines = content.strip().split('\n')

                    if len(lines) < 2:
                        return {"earnings": [], "count": 0}

                    headers = lines[0].split(',')
                    earnings = []

                    for line in lines[1:]:
                        values = line.split(',')
                        if len(values) >= len(headers):
                            entry = dict(zip(headers, values))

                            # Filter by symbol if specified
                            if symbol and entry.get('symbol', '').upper() != symbol.upper():
                                continue

                            earnings.append({
                                "symbol": entry.get("symbol", ""),
                                "name": entry.get("name", ""),
                                "report_date": entry.get("reportDate", ""),
                                "fiscal_date_ending": entry.get("fiscalDateEnding", ""),
                                "estimate": entry.get("estimate", ""),
                                "currency": entry.get("currency", "USD"),
                            })

                    # Sort by report date
                    earnings.sort(key=lambda x: x.get("report_date", ""))

                    return {
                        "earnings": earnings[:50],  # Limit results
                        "count": len(earnings),
                        "horizon": horizon,
                    }

        except Exception as e:
            logger.error(f"Error fetching earnings calendar: {e}")
            return {"error": str(e)}

        return {"earnings": [], "count": 0}

    async def get_economic_calendar(self) -> Dict[str, Any]:
        """
        Get upcoming economic events.
        Note: Alpha Vantage doesn't have this - using placeholder data.

        Key events to track:
        - FOMC meetings/rate decisions
        - CPI (inflation data)
        - Jobs reports (NFP)
        - GDP releases
        - Retail sales
        """
        # In production, you would integrate with:
        # - Trading Economics API
        # - Forex Factory calendar
        # - Investing.com calendar

        # Key recurring events (approximate schedule)
        events = [
            {
                "event": "FOMC Rate Decision",
                "importance": "HIGH",
                "frequency": "8x per year",
                "typical_impact": "Major market moves, affects all sectors",
                "note": "Check Fed calendar for exact dates"
            },
            {
                "event": "CPI (Consumer Price Index)",
                "importance": "HIGH",
                "frequency": "Monthly",
                "typical_day": "~10th-15th of month",
                "typical_impact": "Inflation data affects Fed policy expectations"
            },
            {
                "event": "Non-Farm Payrolls (NFP)",
                "importance": "HIGH",
                "frequency": "Monthly",
                "typical_day": "First Friday of month",
                "typical_impact": "Employment data, major market volatility"
            },
            {
                "event": "GDP Release",
                "importance": "MEDIUM",
                "frequency": "Quarterly",
                "typical_impact": "Economic growth indicator"
            },
            {
                "event": "Retail Sales",
                "importance": "MEDIUM",
                "frequency": "Monthly",
                "typical_impact": "Consumer spending indicator"
            },
            {
                "event": "Initial Jobless Claims",
                "importance": "MEDIUM",
                "frequency": "Weekly (Thursday)",
                "typical_impact": "Labor market health indicator"
            },
        ]

        return {
            "events": events,
            "note": "For real-time economic calendar, integrate with Trading Economics or similar service",
            "recommendation": "Avoid opening new positions 24h before HIGH importance events"
        }

    async def check_earnings_risk(self, symbol: str) -> Dict[str, Any]:
        """
        Check if a stock has upcoming earnings that could cause volatility.

        Returns risk assessment for trading decisions.
        """
        earnings_data = await self.get_earnings_calendar(symbol)

        if "error" in earnings_data:
            return {"error": earnings_data["error"]}

        earnings = earnings_data.get("earnings", [])

        if not earnings:
            return {
                "symbol": symbol,
                "earnings_soon": False,
                "risk_level": "LOW",
                "recommendation": "No upcoming earnings found - safe to trade",
            }

        # Check if earnings are within 7 days
        today = datetime.now().date()
        upcoming = []

        for e in earnings:
            try:
                report_date = datetime.strptime(e["report_date"], "%Y-%m-%d").date()
                days_until = (report_date - today).days

                if 0 <= days_until <= 14:
                    upcoming.append({
                        **e,
                        "days_until": days_until
                    })
            except:
                continue

        if not upcoming:
            return {
                "symbol": symbol,
                "earnings_soon": False,
                "risk_level": "LOW",
                "recommendation": "No earnings in next 2 weeks - safe to trade",
            }

        nearest = upcoming[0]
        days_until = nearest["days_until"]

        if days_until <= 2:
            risk_level = "CRITICAL"
            recommendation = "AVOID - Earnings imminent, high volatility expected"
        elif days_until <= 5:
            risk_level = "HIGH"
            recommendation = "CAUTION - Consider reducing position size or waiting"
        elif days_until <= 10:
            risk_level = "MEDIUM"
            recommendation = "Monitor - Be prepared for pre-earnings moves"
        else:
            risk_level = "LOW"
            recommendation = "Safe to trade with normal position sizing"

        return {
            "symbol": symbol,
            "earnings_soon": True,
            "next_earnings": nearest["report_date"],
            "days_until": days_until,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "upcoming_earnings": upcoming,
        }

    async def get_market_hours_status(self) -> Dict[str, Any]:
        """
        Get current market hours status for stocks and crypto.
        """
        now = datetime.now()
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday

        # US Stock Market hours (9:30 AM - 4:00 PM ET)
        # Pre-market: 4:00 AM - 9:30 AM ET
        # After-hours: 4:00 PM - 8:00 PM ET

        # Simplified - assumes ET timezone
        hour = now.hour
        minute = now.minute
        current_time = hour + minute / 60

        stock_market = {
            "name": "US Stock Market",
            "timezone": "ET",
        }

        if day_of_week >= 5:  # Weekend
            stock_market["status"] = "CLOSED"
            stock_market["session"] = "weekend"
            stock_market["next_open"] = "Monday 9:30 AM ET"
        elif 4 <= current_time < 9.5:
            stock_market["status"] = "PRE_MARKET"
            stock_market["session"] = "pre_market"
            stock_market["note"] = "Limited liquidity, use limit orders"
        elif 9.5 <= current_time < 16:
            stock_market["status"] = "OPEN"
            stock_market["session"] = "regular"
        elif 16 <= current_time < 20:
            stock_market["status"] = "AFTER_HOURS"
            stock_market["session"] = "after_hours"
            stock_market["note"] = "Limited liquidity, use limit orders"
        else:
            stock_market["status"] = "CLOSED"
            stock_market["session"] = "overnight"
            stock_market["next_open"] = "4:00 AM ET (pre-market)"

        crypto_market = {
            "name": "Crypto Market",
            "status": "OPEN",
            "session": "24/7",
            "note": "Crypto markets never close"
        }

        return {
            "timestamp": now.isoformat(),
            "stock_market": stock_market,
            "crypto_market": crypto_market,
        }


# Singleton instance
_calendar_service = None

def get_calendar_service() -> CalendarService:
    """Get singleton calendar service instance"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService()
    return _calendar_service
