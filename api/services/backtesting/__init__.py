"""
Backtesting module for ChartSense Trading Bot.

This module provides a complete backtesting engine to validate trading strategies
on historical data before live trading.

Components:
- BacktestEngine: Core backtesting loop
- DataLoader: Historical data fetching from Alpaca
- SimulatedPortfolio: Track positions, cash, equity
- PerformanceMetrics: Calculate win rate, Sharpe, drawdown, etc.
"""

from .engine import BacktestEngine
from .data_loader import DataLoader
from .portfolio import SimulatedPortfolio
from .metrics import PerformanceMetrics

__all__ = [
    "BacktestEngine",
    "DataLoader",
    "SimulatedPortfolio",
    "PerformanceMetrics",
]
