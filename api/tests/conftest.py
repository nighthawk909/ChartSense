"""
ChartSense API Test Configuration
=================================
Shared pytest fixtures and configuration for all tests.

This file is automatically loaded by pytest and provides:
- Mock service fixtures for Alpaca and Alpha Vantage
- Sample price data fixtures (uptrend, downtrend, sideways)
- Test client fixtures for FastAPI testing
- Async test support configuration
"""
import pytest
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

# Import mocks
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
from tests.mocks.fixtures import (
    generate_uptrend_data,
    generate_downtrend_data,
    generate_sideways_data,
    generate_volatile_data,
    generate_ohlcv_dataframe,
    PriceDataset,
)


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# ============================================================
# FastAPI Test Client Fixtures
# ============================================================

@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    Create a FastAPI test client for the entire test session.

    Returns:
        TestClient instance for making requests
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def client() -> TestClient:
    """
    Create a fresh FastAPI test client for each test function.

    Returns:
        TestClient instance for making requests
    """
    return TestClient(app)


# ============================================================
# Mock Service Fixtures
# ============================================================

@pytest.fixture
def mock_alpaca_service() -> MockAlpacaService:
    """
    Create a mock Alpaca service with default configuration.

    Returns:
        MockAlpacaService instance with default account/positions
    """
    service = MockAlpacaService()
    return service


@pytest.fixture
def mock_alpaca_service_with_positions() -> MockAlpacaService:
    """
    Create a mock Alpaca service with sample positions.

    Returns:
        MockAlpacaService instance with preset positions
    """
    service = MockAlpacaService()

    # Add sample positions
    service.add_position(create_mock_position(
        symbol="AAPL",
        quantity=100,
        entry_price=150.00,
        current_price=155.00,
    ))
    service.add_position(create_mock_position(
        symbol="MSFT",
        quantity=50,
        entry_price=380.00,
        current_price=375.00,
    ))
    service.add_position(create_mock_position(
        symbol="GOOGL",
        quantity=25,
        entry_price=140.00,
        current_price=145.00,
    ))

    return service


@pytest.fixture
def mock_alpha_vantage_service() -> MockAlphaVantageService:
    """
    Create a mock Alpha Vantage service.

    Returns:
        MockAlphaVantageService instance
    """
    return MockAlphaVantageService()


@pytest.fixture
def alpaca_service_patch(mock_alpaca_service: MockAlpacaService):
    """
    Patch the Alpaca service for tests that need it.

    Usage:
        def test_something(alpaca_service_patch):
            # AlpacaService is now mocked
            pass
    """
    with patch('services.alpaca_service.get_alpaca_service', return_value=mock_alpaca_service):
        yield mock_alpaca_service


@pytest.fixture
def alpha_vantage_service_patch(mock_alpha_vantage_service: MockAlphaVantageService):
    """
    Patch the Alpha Vantage service for tests that need it.

    Usage:
        def test_something(alpha_vantage_service_patch):
            # AlphaVantageService is now mocked
            pass
    """
    with patch('services.alpha_vantage.AlphaVantageService', return_value=mock_alpha_vantage_service):
        yield mock_alpha_vantage_service


# ============================================================
# Price Data Fixtures
# ============================================================

@pytest.fixture
def uptrend_prices() -> PriceDataset:
    """
    Generate price data showing a clear uptrend.

    Use for testing bullish signal detection.

    Returns:
        PriceDataset with 100 days of uptrend data
    """
    return generate_uptrend_data(
        start_price=100.0,
        days=100,
        daily_return=0.002,  # 0.2% daily gain
        volatility=0.01,
    )


@pytest.fixture
def downtrend_prices() -> PriceDataset:
    """
    Generate price data showing a clear downtrend.

    Use for testing bearish signal detection.

    Returns:
        PriceDataset with 100 days of downtrend data
    """
    return generate_downtrend_data(
        start_price=100.0,
        days=100,
        daily_return=-0.002,  # 0.2% daily loss
        volatility=0.01,
    )


@pytest.fixture
def sideways_prices() -> PriceDataset:
    """
    Generate price data showing sideways/ranging movement.

    Use for testing neutral signal detection.

    Returns:
        PriceDataset with 100 days of sideways data
    """
    return generate_sideways_data(
        center_price=100.0,
        days=100,
        range_pct=0.05,  # +/- 5% range
        volatility=0.01,
    )


@pytest.fixture
def volatile_prices() -> PriceDataset:
    """
    Generate highly volatile price data.

    Use for testing scalp mode detection.

    Returns:
        PriceDataset with 100 days of volatile data
    """
    return generate_volatile_data(
        start_price=100.0,
        days=100,
        volatility=0.03,  # 3% daily volatility
    )


@pytest.fixture
def ohlcv_data() -> Dict[str, List[float]]:
    """
    Generate a complete OHLCV dataset for indicator testing.

    Returns:
        Dictionary with 'opens', 'highs', 'lows', 'closes', 'volumes'
    """
    return generate_ohlcv_dataframe(
        start_price=100.0,
        days=100,
        trend='neutral',
        volatility=0.015,
    )


@pytest.fixture
def bullish_ohlcv_data() -> Dict[str, List[float]]:
    """
    Generate OHLCV data with bullish characteristics.

    Returns:
        Dictionary with bullish price action
    """
    return generate_ohlcv_dataframe(
        start_price=100.0,
        days=100,
        trend='up',
        volatility=0.01,
    )


@pytest.fixture
def bearish_ohlcv_data() -> Dict[str, List[float]]:
    """
    Generate OHLCV data with bearish characteristics.

    Returns:
        Dictionary with bearish price action
    """
    return generate_ohlcv_dataframe(
        start_price=100.0,
        days=100,
        trend='down',
        volatility=0.01,
    )


# ============================================================
# Account/Position Fixtures
# ============================================================

@pytest.fixture
def sample_account() -> Dict[str, Any]:
    """
    Create a sample account with typical paper trading values.

    Returns:
        Account dictionary
    """
    return create_mock_account(
        equity=100000.0,
        cash=50000.0,
        buying_power=100000.0,
    )


@pytest.fixture
def sample_positions() -> List[Dict[str, Any]]:
    """
    Create a list of sample positions.

    Returns:
        List of position dictionaries
    """
    return [
        create_mock_position("AAPL", 100, 150.00, 155.00),
        create_mock_position("MSFT", 50, 380.00, 375.00),
        create_mock_position("GOOGL", 25, 140.00, 145.00),
        create_mock_position("NVDA", 30, 450.00, 480.00),
    ]


@pytest.fixture
def sample_orders() -> List[Dict[str, Any]]:
    """
    Create a list of sample orders.

    Returns:
        List of order dictionaries
    """
    return [
        create_mock_order("AAPL", 10, "buy", "filled", filled_price=155.00),
        create_mock_order("MSFT", 5, "sell", "filled", filled_price=378.00),
        create_mock_order("TSLA", 20, "buy", "pending"),
        create_mock_order("AMD", 50, "buy", "canceled"),
    ]


# ============================================================
# Indicator Service Fixture
# ============================================================

@pytest.fixture
def indicator_service():
    """
    Create an indicator service instance for testing calculations.

    Returns:
        IndicatorService instance
    """
    from services.indicators import IndicatorService
    return IndicatorService()


@pytest.fixture
def adaptive_engine():
    """
    Create an adaptive indicator engine for testing.

    Returns:
        AdaptiveIndicatorEngine instance
    """
    from services.indicators import AdaptiveIndicatorEngine
    return AdaptiveIndicatorEngine()


# ============================================================
# Time/Date Fixtures
# ============================================================

@pytest.fixture
def market_hours_time() -> datetime:
    """
    Return a datetime during market hours (10:00 AM ET).

    Returns:
        datetime object during market hours
    """
    return datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)  # 10 AM ET


@pytest.fixture
def pre_market_time() -> datetime:
    """
    Return a datetime during pre-market hours (7:00 AM ET).

    Returns:
        datetime object during pre-market
    """
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)  # 7 AM ET


@pytest.fixture
def after_hours_time() -> datetime:
    """
    Return a datetime during after-hours (6:00 PM ET).

    Returns:
        datetime object during after-hours
    """
    return datetime(2024, 1, 15, 23, 0, 0, tzinfo=timezone.utc)  # 6 PM ET


# ============================================================
# Environment Variable Fixtures
# ============================================================

@pytest.fixture
def mock_env_vars():
    """
    Set up mock environment variables for testing.
    Cleans up after test completes.
    """
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ["ALPACA_API_KEY"] = "test_api_key"
    os.environ["ALPACA_SECRET_KEY"] = "test_secret_key"
    os.environ["ALPACA_PAPER"] = "true"
    os.environ["ALPHA_VANTAGE_API_KEY"] = "test_av_key"
    os.environ["OPENAI_API_KEY"] = "test_openai_key"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================
# Utility Fixtures
# ============================================================

@pytest.fixture
def async_mock():
    """
    Create an AsyncMock for mocking async functions.

    Returns:
        AsyncMock instance
    """
    return AsyncMock()


@pytest.fixture
def mock_logger():
    """
    Create a mock logger for testing logging behavior.

    Returns:
        MagicMock configured as a logger
    """
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


# ============================================================
# Integration Test Fixtures
# ============================================================

@pytest.fixture
def mock_crypto_service():
    """
    Create a mock crypto service for testing.

    Returns:
        MockCryptoService instance
    """
    from tests.mocks.crypto_mock import MockCryptoService
    return MockCryptoService()


@pytest.fixture
def mock_db_session():
    """
    Create a mock database session for testing.

    Returns:
        MagicMock configured as a database session
    """
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_session.commit = MagicMock()
    mock_session.close = MagicMock()
    return mock_session


@pytest.fixture
def trading_bot_fixture(mock_alpaca_service, mock_db_session):
    """
    Create a trading bot instance with mocked services for integration testing.

    Returns:
        TradingBot instance configured for testing
    """
    from unittest.mock import patch
    from services.trading_bot import TradingBot

    with patch('services.trading_bot.SessionLocal', return_value=mock_db_session):
        bot = TradingBot(alpaca_service=mock_alpaca_service, paper_trading=True)
        bot.use_ai_discovery = False
        bot.auto_trade_mode = False
        bot.enabled_symbols = ["AAPL", "MSFT", "GOOGL"]
        bot.crypto_symbols = ["BTC/USD", "ETH/USD"]
        bot.cycle_interval_seconds = 0.1  # Fast cycles for testing
        return bot
