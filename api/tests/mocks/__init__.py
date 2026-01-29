"""
ChartSense Test Mocks Package
=============================
Mock implementations for external services used in testing.

This package provides:
- MockAlpacaService: Mock implementation of Alpaca trading API
- MockAlphaVantageService: Mock implementation of Alpha Vantage API
- MockCryptoService: Mock implementation of Alpaca crypto trading API
- Price data fixtures: Sample datasets for indicator testing

Usage:
    from tests.mocks import MockAlpacaService, MockAlphaVantageService, MockCryptoService
    from tests.mocks.fixtures import generate_uptrend_data
"""

from tests.mocks.alpaca_mock import (
    MockAlpacaService,
    create_mock_account,
    create_mock_position,
    create_mock_order,
    create_mock_quote,
    create_mock_bar,
)

from tests.mocks.alpha_vantage_mock import (
    MockAlphaVantageService,
    create_mock_quote_response,
    create_mock_history_response,
)

from tests.mocks.crypto_mock import (
    MockCryptoService,
    create_mock_crypto_quote,
    create_mock_crypto_bar,
    create_mock_crypto_bars,
    create_mock_crypto_order,
    create_mock_crypto_position,
)

from tests.mocks.fixtures import (
    PriceDataset,
    generate_uptrend_data,
    generate_downtrend_data,
    generate_sideways_data,
    generate_volatile_data,
    generate_ohlcv_dataframe,
)

__all__ = [
    # Alpaca mocks
    "MockAlpacaService",
    "create_mock_account",
    "create_mock_position",
    "create_mock_order",
    "create_mock_quote",
    "create_mock_bar",
    # Alpha Vantage mocks
    "MockAlphaVantageService",
    "create_mock_quote_response",
    "create_mock_history_response",
    # Crypto mocks
    "MockCryptoService",
    "create_mock_crypto_quote",
    "create_mock_crypto_bar",
    "create_mock_crypto_bars",
    "create_mock_crypto_order",
    "create_mock_crypto_position",
    # Fixtures
    "PriceDataset",
    "generate_uptrend_data",
    "generate_downtrend_data",
    "generate_sideways_data",
    "generate_volatile_data",
    "generate_ohlcv_dataframe",
]
