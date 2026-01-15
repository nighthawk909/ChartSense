"""
Crypto Trading Service
24/7 cryptocurrency trading via Alpaca API
Supports BTC, ETH, and other major cryptocurrencies
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

logger = logging.getLogger(__name__)

# Supported cryptocurrencies on Alpaca
SUPPORTED_CRYPTOS = [
    "BTC/USD",   # Bitcoin
    "ETH/USD",   # Ethereum
    "SOL/USD",   # Solana
    "AVAX/USD",  # Avalanche
    "LINK/USD",  # Chainlink
    "DOT/USD",   # Polkadot
    "MATIC/USD", # Polygon
    "UNI/USD",   # Uniswap
    "AAVE/USD",  # Aave
    "LTC/USD",   # Litecoin
    "DOGE/USD",  # Dogecoin
    "SHIB/USD",  # Shiba Inu
    "XRP/USD",   # Ripple (if available)
]

# Default crypto watchlist
DEFAULT_CRYPTO_WATCHLIST = ["BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "LINK/USD"]


class CryptoService:
    """
    Service for 24/7 cryptocurrency trading.
    Uses Alpaca's crypto trading API.
    """

    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.paper_trading = os.getenv("ALPACA_TRADING_MODE", "paper") == "paper"

        if self.paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"

        self.data_url = "https://data.alpaca.markets"
        self._headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        base_url: str = None,
        params: Dict = None,
        json_data: Dict = None
    ) -> Optional[Dict]:
        """Make authenticated request to Alpaca API"""
        url = f"{base_url or self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json_data,
                timeout=30.0
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return {"success": True}
            else:
                logger.error(f"Crypto API error: {response.status_code} - {response.text}")
                return None

    async def get_crypto_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote for a cryptocurrency.

        Args:
            symbol: Crypto symbol like "BTC/USD" or "BTCUSD"
        """
        # Normalize symbol to format: BTC/USD (Alpaca requires slash format)
        symbol = symbol.upper().replace("/", "")
        if symbol.endswith("USD"):
            symbol = symbol[:-3] + "/USD"
        else:
            symbol = symbol + "/USD"

        endpoint = f"/v1beta3/crypto/us/latest/quotes"
        params = {"symbols": symbol}

        data = await self._make_request("GET", endpoint, base_url=self.data_url, params=params)

        if data and "quotes" in data and symbol in data["quotes"]:
            quote = data["quotes"][symbol]
            return {
                "symbol": symbol,
                "bid_price": float(quote.get("bp", 0)),
                "ask_price": float(quote.get("ap", 0)),
                "bid_size": float(quote.get("bs", 0)),
                "ask_size": float(quote.get("as", 0)),
                "timestamp": quote.get("t"),
                "mid_price": (float(quote.get("bp", 0)) + float(quote.get("ap", 0))) / 2,
            }
        return None

    async def get_crypto_bars(
        self,
        symbol: str,
        timeframe: str = "1Hour",
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical bars for a cryptocurrency.

        Args:
            symbol: Crypto symbol like "BTC/USD"
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            limit: Number of bars to fetch
        """
        # Normalize symbol to format: BTC/USD (Alpaca requires slash format)
        symbol = symbol.upper().replace("/", "")
        if symbol.endswith("USD"):
            symbol = symbol[:-3] + "/USD"
        else:
            symbol = symbol + "/USD"

        endpoint = f"/v1beta3/crypto/us/bars"
        params = {
            "symbols": symbol,
            "timeframe": timeframe,
            "limit": limit,
        }

        data = await self._make_request("GET", endpoint, base_url=self.data_url, params=params)

        if data and "bars" in data and symbol in data["bars"]:
            bars = data["bars"][symbol]
            return [
                {
                    "timestamp": bar.get("t"),
                    "open": float(bar.get("o", 0)),
                    "high": float(bar.get("h", 0)),
                    "low": float(bar.get("l", 0)),
                    "close": float(bar.get("c", 0)),
                    "volume": float(bar.get("v", 0)),
                    "vwap": float(bar.get("vw", 0)),
                    "trade_count": bar.get("n", 0),
                }
                for bar in bars
            ]
        return None

    async def get_all_crypto_quotes(self) -> Dict[str, Dict]:
        """Get quotes for all supported cryptocurrencies"""
        quotes = {}

        for symbol in DEFAULT_CRYPTO_WATCHLIST:
            try:
                quote = await self.get_crypto_quote(symbol)
                if quote:
                    quotes[symbol] = quote
            except Exception as e:
                logger.error(f"Error fetching {symbol} quote: {e}")

        return quotes

    async def place_crypto_order(
        self,
        symbol: str,
        qty: float,
        side: str,  # "buy" or "sell"
        order_type: str = "market",
        time_in_force: str = "gtc",
        limit_price: float = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Place a cryptocurrency order.

        Args:
            symbol: Crypto symbol like "BTC/USD"
            qty: Quantity to trade (can be fractional)
            side: "buy" or "sell"
            order_type: "market" or "limit"
            time_in_force: "gtc" (good til cancelled) or "ioc" (immediate or cancel)
            limit_price: Required for limit orders
        """
        symbol = symbol.replace("/", "").upper()
        if not symbol.endswith("USD"):
            symbol += "USD"

        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side.lower(),
            "type": order_type,
            "time_in_force": time_in_force,
        }

        if order_type == "limit" and limit_price:
            order_data["limit_price"] = str(limit_price)

        data = await self._make_request("POST", "/v2/orders", json_data=order_data)

        if data:
            logger.info(f"Crypto order placed: {side} {qty} {symbol}")
            return {
                "order_id": data.get("id"),
                "symbol": data.get("symbol"),
                "qty": float(data.get("qty", 0)),
                "side": data.get("side"),
                "type": data.get("type"),
                "status": data.get("status"),
                "filled_qty": float(data.get("filled_qty", 0)),
                "filled_avg_price": float(data.get("filled_avg_price") or 0),
            }
        return None

    async def get_crypto_positions(self) -> List[Dict[str, Any]]:
        """Get all current crypto positions"""
        data = await self._make_request("GET", "/v2/positions")

        if not data:
            return []

        crypto_positions = []
        for pos in data:
            symbol = pos.get("symbol", "")
            # Crypto symbols end with USD
            if symbol.endswith("USD") and not symbol.startswith("T"):  # Exclude TSLA etc
                crypto_positions.append({
                    "symbol": symbol,
                    "qty": float(pos.get("qty", 0)),
                    "avg_entry_price": float(pos.get("avg_entry_price", 0)),
                    "current_price": float(pos.get("current_price", 0)),
                    "market_value": float(pos.get("market_value", 0)),
                    "unrealized_pnl": float(pos.get("unrealized_pl", 0)),
                    "unrealized_pnl_pct": float(pos.get("unrealized_plpc", 0)) * 100,
                })

        return crypto_positions

    async def close_crypto_position(self, symbol: str) -> Optional[Dict]:
        """Close a crypto position"""
        symbol = symbol.replace("/", "").upper()
        if not symbol.endswith("USD"):
            symbol += "USD"

        return await self._make_request("DELETE", f"/v2/positions/{symbol}")

    def is_crypto_market_open(self) -> bool:
        """Crypto markets are always open 24/7"""
        return True

    async def analyze_crypto(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a cryptocurrency for trading signals.

        Returns technical analysis with buy/sell signals.
        """
        bars = await self.get_crypto_bars(symbol, "1Hour", 100)

        if not bars or len(bars) < 20:
            return {"error": "Insufficient data"}

        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]

        # Calculate indicators
        from services.indicators import IndicatorService
        indicator_svc = IndicatorService()

        rsi = indicator_svc.calculate_rsi(closes, 14)
        macd_line, signal_line, histogram = indicator_svc.calculate_macd(closes)
        sma_20 = indicator_svc.calculate_sma(closes, 20)
        sma_50 = indicator_svc.calculate_sma(closes, 50)
        upper_bb, middle_bb, lower_bb = indicator_svc.calculate_bollinger_bands(closes)
        atr = indicator_svc.calculate_atr(highs, lows, closes, 14)

        current_price = closes[-1]

        # Generate signals
        signals = []
        score = 50  # Neutral starting score

        # RSI signals
        if rsi and rsi[-1] < 30:
            signals.append("RSI oversold - bullish")
            score += 15
        elif rsi and rsi[-1] > 70:
            signals.append("RSI overbought - bearish")
            score -= 15

        # MACD signals
        if macd_line and signal_line:
            if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                signals.append("MACD bullish crossover")
                score += 20
            elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                signals.append("MACD bearish crossover")
                score -= 20

        # Moving average signals
        if sma_20 and sma_50:
            if current_price > sma_20[-1] > sma_50[-1]:
                signals.append("Price above rising MAs - bullish trend")
                score += 10
            elif current_price < sma_20[-1] < sma_50[-1]:
                signals.append("Price below falling MAs - bearish trend")
                score -= 10

        # Bollinger Band signals
        if upper_bb and lower_bb:
            if current_price <= lower_bb[-1]:
                signals.append("Price at lower Bollinger Band - potential bounce")
                score += 10
            elif current_price >= upper_bb[-1]:
                signals.append("Price at upper Bollinger Band - potential pullback")
                score -= 10

        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1

        if volume_ratio > 1.5:
            signals.append(f"High volume ({volume_ratio:.1f}x average)")

        # Determine recommendation
        if score >= 70:
            recommendation = "STRONG_BUY"
        elif score >= 60:
            recommendation = "BUY"
        elif score <= 30:
            recommendation = "STRONG_SELL"
        elif score <= 40:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "score": score,
            "recommendation": recommendation,
            "signals": signals,
            "indicators": {
                "rsi": rsi[-1] if rsi else None,
                "macd": macd_line[-1] if macd_line else None,
                "macd_signal": signal_line[-1] if signal_line else None,
                "sma_20": sma_20[-1] if sma_20 else None,
                "sma_50": sma_50[-1] if sma_50 else None,
                "atr": atr[-1] if atr else None,
                "volume_ratio": volume_ratio,
            },
            "support": lower_bb[-1] if lower_bb else None,
            "resistance": upper_bb[-1] if upper_bb else None,
        }


# Singleton instance
_crypto_service = None

def get_crypto_service() -> CryptoService:
    """Get singleton crypto service instance"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service
