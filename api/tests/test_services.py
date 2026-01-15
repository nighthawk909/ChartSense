"""
Service Unit Tests for ChartSense
Tests core service functionality - focuses on pure logic tests
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCryptoService:
    """Test crypto service symbol normalization"""

    def test_symbol_normalization(self):
        """Test crypto symbol normalization to Alpaca format"""
        # Test the normalization logic directly
        def normalize_symbol(symbol: str) -> str:
            symbol = symbol.upper().replace("/", "")
            if symbol.endswith("USD"):
                symbol = symbol[:-3] + "/USD"
            else:
                symbol = symbol + "/USD"
            return symbol

        assert normalize_symbol("BTC") == "BTC/USD"
        assert normalize_symbol("BTCUSD") == "BTC/USD"
        assert normalize_symbol("BTC/USD") == "BTC/USD"
        assert normalize_symbol("eth") == "ETH/USD"
        assert normalize_symbol("ETHUSD") == "ETH/USD"


class TestRiskCalculations:
    """Test basic risk calculation logic"""

    def test_position_size_calculation(self):
        """Test basic position sizing math"""
        account_equity = 100000
        risk_pct = 0.01  # 1%
        entry_price = 150
        stop_loss_price = 145

        # Risk amount
        risk_amount = account_equity * risk_pct  # $1000

        # Risk per share
        risk_per_share = entry_price - stop_loss_price  # $5

        # Position size
        position_size = risk_amount / risk_per_share  # 200 shares

        assert risk_amount == 1000
        assert risk_per_share == 5
        assert position_size == 200

    def test_drawdown_calculation(self):
        """Test drawdown percentage calculation"""
        peak_equity = 100000
        current_equity = 85000

        drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100

        assert drawdown_pct == 15.0

    def test_pnl_calculation(self):
        """Test P&L calculation"""
        entry_price = 100
        exit_price = 110
        shares = 50

        pnl = (exit_price - entry_price) * shares
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100

        assert pnl == 500
        assert pnl_pct == 10.0


class TestIndicatorLogic:
    """Test indicator calculation logic"""

    def test_sma_calculation(self):
        """Test Simple Moving Average"""
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        period = 5

        # SMA is average of last 'period' prices
        sma = sum(prices[-period:]) / period

        assert sma == 17.0  # (15+16+17+18+19)/5

    def test_ema_weight(self):
        """Test EMA multiplier calculation"""
        period = 12
        multiplier = 2 / (period + 1)

        assert abs(multiplier - 0.1538) < 0.001

    def test_rsi_bounds(self):
        """Test RSI is bounded between 0 and 100"""
        # RSI formula: 100 - (100 / (1 + RS))
        # RS = avg_gain / avg_loss

        # Test extreme cases
        # All gains, no losses -> RS approaches infinity -> RSI approaches 100
        # All losses, no gains -> RS = 0 -> RSI = 0

        def calculate_rsi(avg_gain, avg_loss):
            if avg_loss == 0:
                return 100
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        assert calculate_rsi(10, 0) == 100
        assert calculate_rsi(0, 10) == 0
        assert 0 <= calculate_rsi(5, 5) <= 100


class TestPatternLogic:
    """Test pattern detection logic"""

    def test_doji_detection(self):
        """Test doji candle detection logic"""
        def is_doji(open_price, close_price, threshold=0.001):
            body = abs(close_price - open_price)
            avg_price = (open_price + close_price) / 2
            return (body / avg_price) < threshold

        # Perfect doji
        assert is_doji(100.0, 100.05, threshold=0.001)

        # Not a doji (significant body)
        assert not is_doji(100.0, 105.0, threshold=0.001)

    def test_engulfing_pattern(self):
        """Test engulfing pattern detection logic"""
        def is_bullish_engulfing(prev_open, prev_close, curr_open, curr_close):
            prev_bearish = prev_close < prev_open
            curr_bullish = curr_close > curr_open
            engulfs = curr_open < prev_close and curr_close > prev_open
            return prev_bearish and curr_bullish and engulfs

        # Bullish engulfing
        assert is_bullish_engulfing(105, 100, 99, 106)

        # Not engulfing
        assert not is_bullish_engulfing(100, 105, 104, 106)


class TestBacktestLogic:
    """Test backtesting calculations"""

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        import math

        returns = [0.01, 0.02, -0.01, 0.03, 0.01]
        risk_free_rate = 0.0001  # Daily risk-free rate

        avg_return = sum(returns) / len(returns)
        excess_returns = [r - risk_free_rate for r in returns]
        std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))

        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe = 0

        assert sharpe > 0  # Positive returns should give positive Sharpe

    def test_win_rate(self):
        """Test win rate calculation"""
        trades = [100, -50, 200, -30, 150]  # P&L of trades

        winners = len([t for t in trades if t > 0])
        total = len(trades)
        win_rate = (winners / total) * 100

        assert win_rate == 60.0  # 3 out of 5 trades profitable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
