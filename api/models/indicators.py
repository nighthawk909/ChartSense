"""
Technical indicator response models
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class RSIResponse(BaseModel):
    """RSI indicator response"""
    symbol: str
    period: int
    current_value: Optional[float]
    signal: str  # Overbought, Oversold, Neutral
    values: List[float]


class MACDResponse(BaseModel):
    """MACD indicator response"""
    symbol: str
    fast_period: int
    slow_period: int
    signal_period: int
    macd_line: Optional[float]
    signal_line: Optional[float]
    histogram: Optional[float]
    signal: str  # Bullish, Bearish, Neutral


class BollingerBandsResponse(BaseModel):
    """Bollinger Bands response"""
    symbol: str
    period: int
    std_dev: float
    upper_band: Optional[float]
    middle_band: Optional[float]
    lower_band: Optional[float]
    current_price: Optional[float]
    position: str  # Above, Below, Middle


class MovingAverageResponse(BaseModel):
    """Moving average response"""
    symbol: str
    period: int
    type: str  # SMA, EMA
    current_value: Optional[float]
    current_price: Optional[float]
    signal: str  # Above, Below


class StochasticResponse(BaseModel):
    """Stochastic oscillator response"""
    symbol: str
    k_period: int
    d_period: int
    k_value: Optional[float]
    d_value: Optional[float]
    signal: str  # Overbought, Oversold, Neutral


class IndicatorSummary(BaseModel):
    """Single indicator summary"""
    value: float
    signal: str


class TechnicalSummary(BaseModel):
    """Summary of all technical indicators"""
    symbol: str
    current_price: Optional[float]
    indicators: Dict[str, IndicatorSummary]
    overall_signal: str  # Bullish, Bearish, Neutral
    bullish_count: int
    bearish_count: int
