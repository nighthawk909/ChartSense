"""
Trading Configuration
Centralized configuration for all trading bot parameters.

All values can be overridden via environment variables with the TRADING_ prefix.
Example: TRADING_DAILY_PROFIT_TARGET_PCT=0.75 overrides daily_profit_target_pct
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable with fallback to default."""
    env_key = f"TRADING_{key.upper()}"
    value = os.getenv(env_key)
    if value is not None:
        try:
            result = float(value)
            logger.info(f"Config override: {key} = {result} (from {env_key})")
            return result
        except ValueError:
            logger.warning(f"Invalid float for {env_key}: {value}, using default {default}")
    return default


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable with fallback to default."""
    env_key = f"TRADING_{key.upper()}"
    value = os.getenv(env_key)
    if value is not None:
        try:
            result = int(value)
            logger.info(f"Config override: {key} = {result} (from {env_key})")
            return result
        except ValueError:
            logger.warning(f"Invalid int for {env_key}: {value}, using default {default}")
    return default


def _get_env_bool(key: str, default: bool) -> bool:
    """Get boolean from environment variable with fallback to default."""
    env_key = f"TRADING_{key.upper()}"
    value = os.getenv(env_key)
    if value is not None:
        result = value.lower() in ('true', '1', 'yes', 'on')
        logger.info(f"Config override: {key} = {result} (from {env_key})")
        return result
    return default


@dataclass
class TradingConfig:
    """
    Centralized trading configuration.

    All magic numbers from trading_bot.py are collected here for easy tuning.
    Values can be overridden via environment variables with TRADING_ prefix.
    """

    # ===== Profit Taking Settings =====
    # Portion of position to sell when taking partial profit
    partial_profit_pct: float = field(default_factory=lambda: _get_env_float('partial_profit_pct', 0.50))

    # Profit level (%) to trigger partial profit taking
    partial_profit_trigger_pct: float = field(default_factory=lambda: _get_env_float('partial_profit_trigger_pct', 0.05))

    # Daily profit target (%) - used by hierarchical strategy
    daily_profit_target_pct: float = field(default_factory=lambda: _get_env_float('daily_profit_target_pct', 0.5))

    # ===== Position Limits =====
    # Maximum number of symbols to track (API rate limit consideration)
    max_enabled_symbols: int = field(default_factory=lambda: _get_env_int('max_enabled_symbols', 20))

    # Maximum crypto positions
    crypto_max_positions: int = field(default_factory=lambda: _get_env_int('crypto_max_positions', 2))

    # Minimum buying power required to open new positions
    min_buying_power_for_position: float = field(default_factory=lambda: _get_env_float('min_buying_power_for_position', 500.0))

    # Minimum position value for stocks
    min_position_value_stocks: float = field(default_factory=lambda: _get_env_float('min_position_value_stocks', 100.0))

    # Minimum position value for crypto
    min_position_value_crypto: float = field(default_factory=lambda: _get_env_float('min_position_value_crypto', 10.0))

    # ===== Order Settings =====
    # Offset percentage for limit orders (e.g., 0.001 = 0.1% above current price for buys)
    limit_order_offset_pct: float = field(default_factory=lambda: _get_env_float('limit_order_offset_pct', 0.001))

    # ===== Scanning Settings =====
    # Number of symbols to scan in each batch
    scan_batch_size: int = field(default_factory=lambda: _get_env_int('scan_batch_size', 10))

    # Interval between trading cycles (seconds)
    cycle_interval_seconds: int = field(default_factory=lambda: _get_env_int('cycle_interval_seconds', 60))

    # ===== Trailing Stop Settings =====
    # Default trailing stop percentage
    trailing_stop_pct: float = field(default_factory=lambda: _get_env_float('trailing_stop_pct', 0.03))

    # Profit level required to activate trailing stop
    trailing_stop_activation_pct: float = field(default_factory=lambda: _get_env_float('trailing_stop_activation_pct', 0.05))

    # ===== Crypto Settings =====
    # Entry threshold for crypto (lower than stocks due to higher volatility)
    crypto_entry_threshold: float = field(default_factory=lambda: _get_env_float('crypto_entry_threshold', 55.0))

    # ===== Intraday Settings =====
    # Maximum trades per day
    max_trades_per_day: int = field(default_factory=lambda: _get_env_int('max_trades_per_day', 10))

    # ===== Timeout Settings =====
    # HTTP request timeout in seconds
    http_timeout_seconds: int = field(default_factory=lambda: _get_env_int('http_timeout_seconds', 30))

    # Order fill wait timeout in seconds
    order_fill_timeout_seconds: int = field(default_factory=lambda: _get_env_int('order_fill_timeout_seconds', 60))

    # ===== Default Stop Loss =====
    # Default stop loss percentage if not specified
    default_stop_loss_pct: float = field(default_factory=lambda: _get_env_float('default_stop_loss_pct', 0.05))

    def __post_init__(self):
        """Validate configuration values."""
        self._validate()

    def _validate(self):
        """Validate that all values are within reasonable ranges."""
        errors = []

        if not 0 < self.partial_profit_pct <= 1:
            errors.append(f"partial_profit_pct must be between 0 and 1, got {self.partial_profit_pct}")

        if not 0 < self.daily_profit_target_pct <= 10:
            errors.append(f"daily_profit_target_pct must be between 0 and 10, got {self.daily_profit_target_pct}")

        if self.max_enabled_symbols < 1:
            errors.append(f"max_enabled_symbols must be at least 1, got {self.max_enabled_symbols}")

        if self.min_buying_power_for_position < 0:
            errors.append(f"min_buying_power_for_position cannot be negative, got {self.min_buying_power_for_position}")

        if not 0 < self.limit_order_offset_pct < 0.1:
            errors.append(f"limit_order_offset_pct should be between 0 and 0.1, got {self.limit_order_offset_pct}")

        if errors:
            for error in errors:
                logger.error(f"Config validation error: {error}")
            raise ValueError(f"Invalid trading configuration: {'; '.join(errors)}")

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'partial_profit_pct': self.partial_profit_pct,
            'partial_profit_trigger_pct': self.partial_profit_trigger_pct,
            'daily_profit_target_pct': self.daily_profit_target_pct,
            'max_enabled_symbols': self.max_enabled_symbols,
            'crypto_max_positions': self.crypto_max_positions,
            'min_buying_power_for_position': self.min_buying_power_for_position,
            'min_position_value_stocks': self.min_position_value_stocks,
            'min_position_value_crypto': self.min_position_value_crypto,
            'limit_order_offset_pct': self.limit_order_offset_pct,
            'scan_batch_size': self.scan_batch_size,
            'cycle_interval_seconds': self.cycle_interval_seconds,
            'trailing_stop_pct': self.trailing_stop_pct,
            'trailing_stop_activation_pct': self.trailing_stop_activation_pct,
            'crypto_entry_threshold': self.crypto_entry_threshold,
            'max_trades_per_day': self.max_trades_per_day,
            'http_timeout_seconds': self.http_timeout_seconds,
            'order_fill_timeout_seconds': self.order_fill_timeout_seconds,
            'default_stop_loss_pct': self.default_stop_loss_pct,
        }


# Singleton instance
_config_instance: Optional[TradingConfig] = None


def get_trading_config() -> TradingConfig:
    """Get the singleton TradingConfig instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = TradingConfig()
        logger.info(f"Initialized TradingConfig: {_config_instance.to_dict()}")
    return _config_instance


def reset_trading_config():
    """Reset config instance (useful for testing)."""
    global _config_instance
    _config_instance = None
