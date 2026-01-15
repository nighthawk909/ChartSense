"""
Stock data models
"""
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class TimeInterval(str, Enum):
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    MINUTE_60 = "60min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class StockQuote(BaseModel):
    """Real-time stock quote"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    latest_trading_day: str
    previous_close: float
    open: float
    high: float
    low: float


class PriceData(BaseModel):
    """Single price data point"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockHistory(BaseModel):
    """Historical price data"""
    symbol: str
    interval: str
    data: List[PriceData]
    prices: List[float]  # Close prices for calculations


class SearchResult(BaseModel):
    """Stock search result"""
    symbol: str
    name: str
    type: str
    region: str


class CompanyOverview(BaseModel):
    """Company fundamental data"""
    symbol: str
    name: str
    description: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[str]
    pe_ratio: Optional[str]
    eps: Optional[str]
    dividend_yield: Optional[str]
    week_52_high: Optional[str]
    week_52_low: Optional[str]
    day_50_ma: Optional[str]
    day_200_ma: Optional[str]
    beta: Optional[str]
