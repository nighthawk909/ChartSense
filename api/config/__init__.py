"""
Configuration module for ChartSense trading bot.

Centralizes all configurable values with environment variable overrides.
"""

from .trading_config import TradingConfig, get_trading_config

__all__ = ['TradingConfig', 'get_trading_config']
