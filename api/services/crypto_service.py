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

# Supported cryptocurrencies on Alpaca (verified to work)
# Updated 2025: Alpaca now supports major coins including SOL, DOGE, etc.
SUPPORTED_CRYPTOS = [
    "BTC/USD",   # Bitcoin
    "ETH/USD",   # Ethereum
    "SOL/USD",   # Solana
    "DOGE/USD",  # Dogecoin
    "AVAX/USD",  # Avalanche
    "LINK/USD",  # Chainlink
    "MATIC/USD", # Polygon
    "UNI/USD",   # Uniswap
    "LTC/USD",   # Litecoin
    "AAVE/USD",  # Aave
    "SHIB/USD",  # Shiba Inu
    # Note: XRP and ADA not available on Alpaca
]

# Default crypto watchlist
DEFAULT_CRYPTO_WATCHLIST = ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD"]


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
        json_data: Dict = None,
        return_error: bool = False
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
                error_msg = f"Crypto API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                if return_error:
                    return {"error": True, "status_code": response.status_code, "message": response.text}
                return None

    async def get_crypto_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote for a cryptocurrency with 24h stats.

        Args:
            symbol: Crypto symbol like "BTC/USD" or "BTCUSD"
        """
        # Normalize symbol to format: BTC/USD (Alpaca requires slash format)
        original_symbol = symbol
        symbol = symbol.upper().replace("/", "")
        if symbol.endswith("USD"):
            symbol = symbol[:-3] + "/USD"
        else:
            symbol = symbol + "/USD"

        # Get current quote
        endpoint = "/v1beta3/crypto/us/latest/quotes"
        params = {"symbols": symbol}
        data = await self._make_request("GET", endpoint, base_url=self.data_url, params=params)

        if not data or "quotes" not in data or symbol not in data["quotes"]:
            return None

        quote = data["quotes"][symbol]
        bid_price = float(quote.get("bp", 0))
        ask_price = float(quote.get("ap", 0))
        current_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0

        # Get 24h bars to calculate change
        bars = await self.get_crypto_bars(symbol, timeframe="1Hour", limit=24)

        change_24h = 0.0
        change_percent_24h = 0.0
        high_24h = current_price
        low_24h = current_price
        volume_24h = 0.0

        if bars and len(bars) > 0:
            # Get price from 24 hours ago (or oldest available)
            price_24h_ago = bars[0]["open"] if bars else current_price
            change_24h = current_price - price_24h_ago
            change_percent_24h = (change_24h / price_24h_ago * 100) if price_24h_ago else 0

            # Calculate 24h high/low/volume
            high_24h = max(bar["high"] for bar in bars)
            low_24h = min(bar["low"] for bar in bars)
            volume_24h = sum(bar["volume"] for bar in bars)

        return {
            "symbol": symbol,
            "price": current_price,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_size": float(quote.get("bs", 0)),
            "ask_size": float(quote.get("as", 0)),
            "timestamp": quote.get("t"),
            "mid_price": current_price,
            # 24h stats for frontend
            "change_24h": change_24h,
            "change_percent_24h": change_percent_24h,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volume_24h": volume_24h,
        }

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
        from datetime import datetime, timedelta

        # Normalize symbol to format: BTC/USD (Alpaca requires slash format)
        symbol = symbol.upper().replace("/", "")
        if symbol.endswith("USD"):
            symbol = symbol[:-3] + "/USD"
        else:
            symbol = symbol + "/USD"

        # Calculate start date to get enough historical data
        # For hourly bars, go back enough days to get the requested limit
        if timeframe == "1Hour":
            days_back = max(7, (limit // 24) + 2)  # At least 7 days for indicators
        elif timeframe == "1Day":
            days_back = limit + 10
        else:
            days_back = 3  # For minute bars, 3 days should be enough

        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")

        endpoint = f"/v1beta3/crypto/us/bars"
        params = {
            "symbols": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "start": start_date,
        }

        logger.debug(f"Fetching crypto bars: {symbol}, {timeframe}, limit={limit}, start={start_date}")
        data = await self._make_request("GET", endpoint, base_url=self.data_url, params=params)

        if data and "bars" in data and symbol in data["bars"]:
            bars = data["bars"][symbol]
            logger.debug(f"Received {len(bars)} bars for {symbol}")
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

        Symbol Format Notes:
            - Alpaca crypto API expects symbols WITHOUT slash: BTCUSD, ETHUSD
            - Common mistake: BTC/USD won't work, must be BTCUSD
            - This function handles the conversion automatically
        """
        # === SYMBOL NORMALIZATION ===
        # Convert BTC/USD -> BTCUSD, btc/usd -> BTCUSD, etc.
        original_symbol = symbol
        symbol = symbol.replace("/", "").upper()
        if not symbol.endswith("USD"):
            symbol += "USD"

        logger.debug(f"Symbol normalization: {original_symbol} -> {symbol}")

        # === MINIMUM ORDER VALIDATION ===
        # Alpaca has minimum notional value of $1 for crypto
        # Also validate that qty is reasonable
        if qty <= 0:
            logger.error(f"Invalid quantity: {qty}")
            return {
                "error": True,
                "error_message": "ORDER_SIZE_TOO_SMALL: Quantity must be greater than 0",
                "status_code": 400,
                "symbol": symbol,
                "qty": qty,
                "side": side,
            }

        # Round qty to reasonable precision (Alpaca accepts up to 9 decimal places for crypto)
        qty = round(qty, 9)

        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side.lower(),
            "type": order_type,
            "time_in_force": time_in_force,
        }

        if order_type == "limit" and limit_price:
            order_data["limit_price"] = str(round(limit_price, 2))

        logger.info(f"Placing crypto order: {side} {qty} {symbol} (type={order_type})")
        logger.info(f"Order data: {order_data}")
        data = await self._make_request("POST", "/v2/orders", json_data=order_data, return_error=True)

        if data and data.get("error"):
            error_msg = data.get('message', 'Unknown error')
            status_code = data.get('status_code', 'N/A')
            logger.error(f"Order FAILED for {symbol}: {error_msg} (status: {status_code})")
            logger.error(f"Order details: qty={qty}, side={side}, type={order_type}")
            # Return error info for execution log
            return {
                "error": True,
                "error_message": error_msg,
                "status_code": status_code,
                "symbol": symbol,
                "qty": qty,
                "side": side,
            }

        if data:
            logger.info(f"Crypto order SUCCESS: {side} {qty} {symbol} - status: {data.get('status')}")
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

        logger.error(f"Order returned None for {symbol}")
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
        Uses nuanced scoring to differentiate between cryptos even in normal conditions.
        """
        # Try to get more bars - request 200 to ensure we have enough for indicators
        bars = await self.get_crypto_bars(symbol, "1Hour", 200)

        # Require at least 10 bars for basic analysis (reduced from 20)
        if not bars or len(bars) < 10:
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

        # Generate signals with nuanced scoring
        signals = []
        score = 50  # Neutral starting score

        # === RSI Analysis (more nuanced) ===
        if rsi and len(rsi) > 0:
            current_rsi = rsi[-1]
            # Extreme levels
            if current_rsi < 30:
                signals.append(f"RSI oversold ({current_rsi:.1f}) - strong bullish")
                score += 18
            elif current_rsi < 40:
                signals.append(f"RSI approaching oversold ({current_rsi:.1f}) - bullish")
                score += 10
            elif current_rsi > 70:
                signals.append(f"RSI overbought ({current_rsi:.1f}) - strong bearish")
                score -= 18
            elif current_rsi > 60:
                signals.append(f"RSI elevated ({current_rsi:.1f}) - caution")
                score -= 8
            elif 45 <= current_rsi <= 55:
                signals.append(f"RSI neutral ({current_rsi:.1f})")
                # Neutral RSI - look at RSI trend
                if len(rsi) >= 3 and rsi[-1] > rsi[-3]:
                    signals.append("RSI trending up")
                    score += 5
                elif len(rsi) >= 3 and rsi[-1] < rsi[-3]:
                    signals.append("RSI trending down")
                    score -= 5

        # === MACD Analysis (more nuanced) ===
        if macd_line and signal_line and len(macd_line) >= 2:
            macd_current = macd_line[-1]
            signal_current = signal_line[-1]
            macd_prev = macd_line[-2]
            signal_prev = signal_line[-2]

            # Crossover signals
            if macd_current > signal_current and macd_prev <= signal_prev:
                signals.append("MACD bullish crossover - buy signal")
                score += 20
            elif macd_current < signal_current and macd_prev >= signal_prev:
                signals.append("MACD bearish crossover - sell signal")
                score -= 20
            else:
                # No crossover - check positioning and momentum
                macd_diff = macd_current - signal_current
                if macd_diff > 0:
                    signals.append(f"MACD above signal (+{abs(macd_diff):.4f}) - bullish")
                    score += min(12, abs(macd_diff) * 100)  # Scale by strength
                else:
                    signals.append(f"MACD below signal ({macd_diff:.4f}) - bearish")
                    score -= min(12, abs(macd_diff) * 100)

                # MACD momentum (is MACD accelerating?)
                if len(histogram) >= 3:
                    if histogram[-1] > histogram[-2] > histogram[-3]:
                        signals.append("MACD momentum accelerating up")
                        score += 6
                    elif histogram[-1] < histogram[-2] < histogram[-3]:
                        signals.append("MACD momentum accelerating down")
                        score -= 6

        # === Moving Average Analysis (more nuanced) ===
        if sma_20 and sma_50 and len(sma_20) > 0 and len(sma_50) > 0:
            sma20_val = sma_20[-1]
            sma50_val = sma_50[-1]

            # Price vs MAs
            price_vs_sma20_pct = ((current_price - sma20_val) / sma20_val) * 100
            price_vs_sma50_pct = ((current_price - sma50_val) / sma50_val) * 100

            # Bullish: price above both MAs, MAs aligned
            if current_price > sma20_val > sma50_val:
                signals.append(f"Strong uptrend: price > SMA20 > SMA50")
                score += 12
            elif current_price > sma20_val and current_price > sma50_val:
                signals.append(f"Price above both MAs - bullish")
                score += 8
            elif current_price < sma20_val < sma50_val:
                signals.append(f"Strong downtrend: price < SMA20 < SMA50")
                score -= 12
            elif current_price < sma20_val and current_price < sma50_val:
                signals.append(f"Price below both MAs - bearish")
                score -= 8
            else:
                # Mixed signals - price between MAs
                if current_price > sma20_val:
                    signals.append(f"Price above SMA20, below SMA50 - recovering")
                    score += 4
                else:
                    signals.append(f"Price below SMA20, above SMA50 - weakening")
                    score -= 4

            # Golden/Death cross proximity
            sma_gap_pct = ((sma20_val - sma50_val) / sma50_val) * 100
            if -1 < sma_gap_pct < 1:
                signals.append("MAs converging - potential crossover")
                score += 3 if sma_gap_pct > 0 else -3

        # === Bollinger Band Analysis (more nuanced) ===
        if upper_bb and lower_bb and middle_bb:
            bb_width = upper_bb[-1] - lower_bb[-1]
            bb_position = (current_price - lower_bb[-1]) / bb_width if bb_width > 0 else 0.5

            if bb_position <= 0.1:
                signals.append("At lower BB - strong bounce potential")
                score += 12
            elif bb_position <= 0.25:
                signals.append("Near lower BB - bullish opportunity")
                score += 7
            elif bb_position >= 0.9:
                signals.append("At upper BB - pullback likely")
                score -= 12
            elif bb_position >= 0.75:
                signals.append("Near upper BB - caution")
                score -= 7
            elif 0.4 <= bb_position <= 0.6:
                signals.append("Middle of BB range - neutral")

            # BB squeeze detection (volatility)
            if len(upper_bb) >= 20:
                avg_width = sum(upper_bb[i] - lower_bb[i] for i in range(-20, 0)) / 20
                if bb_width < avg_width * 0.7:
                    signals.append("BB squeeze - breakout expected")
                    score += 5  # Volatility incoming

        # === Price Momentum (short-term) ===
        if len(closes) >= 6:
            # 6-hour momentum
            momentum_6h = ((closes[-1] - closes[-6]) / closes[-6]) * 100
            if momentum_6h > 2:
                signals.append(f"Strong 6h momentum: +{momentum_6h:.1f}%")
                score += 8
            elif momentum_6h > 0.5:
                signals.append(f"Positive 6h momentum: +{momentum_6h:.1f}%")
                score += 4
            elif momentum_6h < -2:
                signals.append(f"Weak 6h momentum: {momentum_6h:.1f}%")
                score -= 8
            elif momentum_6h < -0.5:
                signals.append(f"Negative 6h momentum: {momentum_6h:.1f}%")
                score -= 4

        # === 24-hour trend ===
        if len(closes) >= 24:
            change_24h = ((closes[-1] - closes[-24]) / closes[-24]) * 100
            if change_24h > 5:
                signals.append(f"Strong 24h gain: +{change_24h:.1f}%")
                score += 6
            elif change_24h > 2:
                signals.append(f"24h up: +{change_24h:.1f}%")
                score += 3
            elif change_24h < -5:
                signals.append(f"Sharp 24h decline: {change_24h:.1f}%")
                score -= 6
            elif change_24h < -2:
                signals.append(f"24h down: {change_24h:.1f}%")
                score -= 3

        # === Volume Analysis ===
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1

        if volume_ratio > 2.0:
            signals.append(f"Very high volume ({volume_ratio:.1f}x) - strong interest")
            score += 5
        elif volume_ratio > 1.5:
            signals.append(f"Elevated volume ({volume_ratio:.1f}x)")
            score += 3
        elif volume_ratio < 0.5:
            signals.append(f"Low volume ({volume_ratio:.1f}x) - weak conviction")
            score -= 3

        # === Support/Resistance proximity ===
        if atr and len(atr) > 0:
            current_atr = atr[-1]
            # Check if near recent highs/lows (potential S/R)
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])

            dist_to_high = (recent_high - current_price) / current_atr if current_atr > 0 else 999
            dist_to_low = (current_price - recent_low) / current_atr if current_atr > 0 else 999

            if dist_to_high < 0.5:
                signals.append("Near resistance - may face selling")
                score -= 4
            if dist_to_low < 0.5:
                signals.append("Near support - buyers may step in")
                score += 4

        # Clamp score to 0-100
        score = max(0, min(100, score))

        # Determine recommendation based on score
        if score >= 75:
            recommendation = "STRONG_BUY"
        elif score >= 65:
            recommendation = "BUY"
        elif score >= 55:
            recommendation = "LEAN_BUY"
        elif score <= 25:
            recommendation = "STRONG_SELL"
        elif score <= 35:
            recommendation = "SELL"
        elif score <= 45:
            recommendation = "LEAN_SELL"
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
                "macd_histogram": histogram[-1] if histogram else None,
                "sma_20": sma_20[-1] if sma_20 else None,
                "sma_50": sma_50[-1] if sma_50 else None,
                "atr": atr[-1] if atr else None,
                "volume_ratio": volume_ratio,
                "bb_position": bb_position if upper_bb and lower_bb else None,
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
