"""
API Endpoint Tests for ChartSense
Tests critical endpoints before deployment
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "ChartSense API"
        assert "version" in data
        assert "features" in data

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestCryptoEndpoints:
    """Test cryptocurrency endpoints"""

    def test_crypto_supported(self):
        """Test supported cryptocurrencies list"""
        response = client.get("/api/crypto/supported")
        assert response.status_code == 200
        data = response.json()
        # Check for supported list
        assert "supported" in data
        assert len(data["supported"]) > 0
        # Check for major cryptos
        assert "BTC/USD" in data["supported"]
        assert "ETH/USD" in data["supported"]

    def test_crypto_market_status(self):
        """Test crypto market status (24/7)"""
        response = client.get("/api/crypto/market-status")
        assert response.status_code == 200
        data = response.json()
        # Crypto markets are always open
        assert data["market_open"] == True


class TestBotEndpoints:
    """Test trading bot endpoints"""

    def test_bot_status(self):
        """Test bot status endpoint"""
        response = client.get("/api/bot/status")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert data["state"] in ["STOPPED", "RUNNING", "PAUSED", "ERROR"]

    def test_bot_health(self):
        """Test bot health endpoint"""
        response = client.get("/api/bot/health")
        assert response.status_code == 200


class TestAdvancedEndpoints:
    """Test advanced analysis endpoints"""

    def test_backtest_strategies(self):
        """Test backtesting strategies list"""
        response = client.get("/api/advanced/backtest/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert len(data["strategies"]) >= 4  # Should have at least 4 strategies

        # Check strategy structure
        for strategy in data["strategies"]:
            assert "id" in strategy
            assert "name" in strategy
            assert "description" in strategy

    def test_market_hours(self):
        """Test market hours endpoint"""
        response = client.get("/api/advanced/calendar/market-hours")
        assert response.status_code == 200
        data = response.json()
        assert "stock_market" in data
        assert "crypto_market" in data
        # Crypto is always open
        assert data["crypto_market"]["status"] == "OPEN"


class TestStockEndpoints:
    """Test stock data endpoints"""

    def test_stock_search(self):
        """Test stock symbol search"""
        response = client.get("/api/stocks/search?query=AAPL")
        assert response.status_code == 200
        data = response.json()
        # API returns {results: [...]}
        assert "results" in data
        results = data["results"]
        assert isinstance(results, list)
        # Should find Apple
        if len(results) > 0:
            symbols = [s.get("symbol", "") for s in results]
            assert any("AAPL" in s for s in symbols)


class TestSettingsEndpoints:
    """Test settings endpoints"""

    def test_get_settings(self):
        """Test getting bot settings"""
        response = client.get("/api/settings/")
        assert response.status_code == 200
        data = response.json()
        # Settings are nested under 'settings' key
        assert "settings" in data or "config_name" in data

    def test_get_presets(self):
        """Test getting strategy presets"""
        response = client.get("/api/settings/presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


# Integration test - requires API keys
class TestIntegration:
    """Integration tests (may require valid API keys)"""

    @pytest.mark.skipif(
        not os.getenv("ALPACA_API_KEY"),
        reason="Alpaca API key not configured"
    )
    def test_account_endpoint(self):
        """Test account endpoint with real API"""
        response = client.get("/api/positions/account")
        # Should work with valid API key
        if response.status_code == 200:
            data = response.json()
            assert "equity" in data
            assert "buying_power" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
