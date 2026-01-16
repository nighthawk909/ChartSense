"""
ChartSense Diagnostic Script
=============================
Checks all API connections, validates chart data timestamps, and reports system health.

Usage:
    python -m scripts.diagnostic
    python -m scripts.diagnostic --verbose
    python -m scripts.diagnostic --json

This script will:
1. Check Alpaca API connection (both trading and data endpoints)
2. Check Alpha Vantage API connection
3. Validate chart data timestamps (should match current time for 1m charts)
4. Test crypto trading endpoint
5. Report any configuration issues
"""
import asyncio
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class DiagnosticResult:
    """Represents a diagnostic check result"""
    def __init__(self, name: str, passed: bool, message: str, details: Dict[str, Any] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"[{status}] {self.name}: {self.message}"


class ChartSenseDiagnostic:
    """
    Comprehensive diagnostic checks for ChartSense trading system.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[DiagnosticResult] = []

        # API Keys from environment
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.trading_mode = os.getenv("ALPACA_TRADING_MODE", "paper")

    def log(self, message: str):
        """Log verbose messages"""
        if self.verbose:
            print(f"  [DEBUG] {message}")

    async def run_all_checks(self) -> List[DiagnosticResult]:
        """Run all diagnostic checks"""
        print("\n" + "=" * 60)
        print("ChartSense Diagnostic Report")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")

        # Configuration checks
        print("1. Configuration Checks")
        print("-" * 40)
        await self._check_environment_variables()

        # Alpaca API checks
        print("\n2. Alpaca API Checks")
        print("-" * 40)
        await self._check_alpaca_connection()
        await self._check_alpaca_account()
        await self._check_alpaca_data_api()

        # Chart timestamp validation
        print("\n3. Chart Data Timestamp Validation")
        print("-" * 40)
        await self._check_chart_timestamps()

        # Crypto API checks
        print("\n4. Crypto Trading Checks")
        print("-" * 40)
        await self._check_crypto_api()

        # Alpha Vantage checks
        print("\n5. Alpha Vantage API Checks")
        print("-" * 40)
        await self._check_alpha_vantage()

        # System time check
        print("\n6. System Time Check")
        print("-" * 40)
        await self._check_system_time()

        # Summary
        self._print_summary()

        return self.results

    async def _check_environment_variables(self):
        """Check required environment variables are set"""
        checks = [
            ("ALPACA_API_KEY", self.alpaca_api_key, True),
            ("ALPACA_SECRET_KEY", self.alpaca_secret_key, True),
            ("ALPHA_VANTAGE_API_KEY", self.alpha_vantage_key, False),
            ("ALPACA_TRADING_MODE", self.trading_mode, False),
        ]

        for var_name, value, required in checks:
            if value:
                # Mask the key for security
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                result = DiagnosticResult(
                    f"ENV: {var_name}",
                    True,
                    f"Set ({masked})",
                    {"masked_value": masked}
                )
            else:
                result = DiagnosticResult(
                    f"ENV: {var_name}",
                    not required,
                    "Not set" + (" (optional)" if not required else " (REQUIRED)"),
                    {"required": required}
                )

            self.results.append(result)
            print(result)

    async def _check_alpaca_connection(self):
        """Check basic Alpaca API connectivity"""
        import httpx

        base_url = "https://paper-api.alpaca.markets" if self.trading_mode == "paper" else "https://api.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/v2/clock", headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    is_open = data.get("is_open", False)
                    result = DiagnosticResult(
                        "Alpaca API Connection",
                        True,
                        f"Connected to {self.trading_mode} API. Market {'OPEN' if is_open else 'CLOSED'}",
                        {"mode": self.trading_mode, "is_open": is_open, "response": data}
                    )
                else:
                    result = DiagnosticResult(
                        "Alpaca API Connection",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        {"status_code": response.status_code}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "Alpaca API Connection",
                False,
                f"Connection failed: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    async def _check_alpaca_account(self):
        """Check Alpaca account status and permissions"""
        import httpx

        base_url = "https://paper-api.alpaca.markets" if self.trading_mode == "paper" else "https://api.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/v2/account", headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    equity = float(data.get("equity", 0))
                    buying_power = float(data.get("buying_power", 0))
                    trading_blocked = data.get("trading_blocked", False)
                    crypto_status = data.get("crypto_status", "UNKNOWN")

                    result = DiagnosticResult(
                        "Alpaca Account",
                        not trading_blocked,
                        f"Equity: ${equity:,.2f}, Buying Power: ${buying_power:,.2f}, Crypto: {crypto_status}",
                        {
                            "equity": equity,
                            "buying_power": buying_power,
                            "trading_blocked": trading_blocked,
                            "crypto_status": crypto_status,
                        }
                    )
                else:
                    result = DiagnosticResult(
                        "Alpaca Account",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        {"status_code": response.status_code}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "Alpaca Account",
                False,
                f"Failed: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    async def _check_alpaca_data_api(self):
        """Check Alpaca data API connectivity"""
        import httpx

        data_url = "https://data.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                # Test stock data endpoint
                response = await client.get(
                    f"{data_url}/v2/stocks/AAPL/quotes/latest",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    quote = data.get("quote", {})
                    result = DiagnosticResult(
                        "Alpaca Data API (Stocks)",
                        True,
                        f"AAPL quote retrieved: ${float(quote.get('ap', 0)):.2f}",
                        {"quote": quote}
                    )
                else:
                    result = DiagnosticResult(
                        "Alpaca Data API (Stocks)",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        {"status_code": response.status_code}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "Alpaca Data API (Stocks)",
                False,
                f"Failed: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    async def _check_chart_timestamps(self):
        """
        CRITICAL CHECK: Validate that chart data timestamps are current.
        This detects the "stale chart" bug where TradingView shows old data.
        """
        import httpx

        data_url = "https://data.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }

        # Test both stocks and crypto
        test_cases = [
            ("AAPL", "/v2/stocks/AAPL/bars", "1Min", "Stock 1m Chart"),
            ("BTC/USD", "/v1beta3/crypto/us/bars", "1Min", "Crypto 1m Chart"),
        ]

        now_utc = datetime.now(timezone.utc)

        for symbol, endpoint, timeframe, label in test_cases:
            try:
                async with httpx.AsyncClient() as client:
                    params = {"timeframe": timeframe, "limit": 1}
                    if "crypto" in endpoint:
                        params["symbols"] = symbol

                    response = await client.get(
                        f"{data_url}{endpoint}",
                        headers=headers,
                        params=params,
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()

                        # Extract the most recent bar timestamp
                        bars = data.get("bars", [])
                        if "crypto" in endpoint and isinstance(bars, dict):
                            bars = bars.get(symbol, [])

                        if bars:
                            bar = bars[-1] if isinstance(bars, list) else bars
                            timestamp_str = bar.get("t", "")

                            # Parse timestamp
                            if timestamp_str:
                                bar_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                age_seconds = (now_utc - bar_time).total_seconds()
                                age_minutes = age_seconds / 60

                                # For 1-minute charts, data should be < 5 minutes old
                                is_fresh = age_minutes < 5

                                result = DiagnosticResult(
                                    f"{label} Timestamp",
                                    is_fresh,
                                    f"Last bar: {bar_time.strftime('%H:%M:%S UTC')} ({age_minutes:.1f} min ago)",
                                    {
                                        "bar_timestamp": timestamp_str,
                                        "system_time": now_utc.isoformat(),
                                        "age_seconds": age_seconds,
                                        "age_minutes": age_minutes,
                                        "is_fresh": is_fresh,
                                    }
                                )
                            else:
                                result = DiagnosticResult(
                                    f"{label} Timestamp",
                                    False,
                                    "No timestamp in bar data",
                                    {"data": data}
                                )
                        else:
                            result = DiagnosticResult(
                                f"{label} Timestamp",
                                False,
                                "No bars returned",
                                {"data": data}
                            )
                    else:
                        result = DiagnosticResult(
                            f"{label} Timestamp",
                            False,
                            f"HTTP {response.status_code}",
                            {"status_code": response.status_code}
                        )
            except Exception as e:
                result = DiagnosticResult(
                    f"{label} Timestamp",
                    False,
                    f"Error: {str(e)}",
                    {"error": str(e)}
                )

            self.results.append(result)
            print(result)

    async def _check_crypto_api(self):
        """Check crypto trading API"""
        import httpx

        data_url = "https://data.alpaca.markets"
        headers = {
            "APCA-API-KEY-ID": self.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                # Test crypto quote endpoint
                response = await client.get(
                    f"{data_url}/v1beta3/crypto/us/latest/quotes",
                    headers=headers,
                    params={"symbols": "BTC/USD"},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    quotes = data.get("quotes", {})
                    btc_quote = quotes.get("BTC/USD", {})
                    bid = float(btc_quote.get("bp", 0))
                    ask = float(btc_quote.get("ap", 0))
                    mid = (bid + ask) / 2 if bid and ask else 0

                    result = DiagnosticResult(
                        "Crypto API (BTC/USD)",
                        mid > 0,
                        f"BTC Price: ${mid:,.2f} (Bid: ${bid:,.2f}, Ask: ${ask:,.2f})",
                        {"bid": bid, "ask": ask, "mid": mid}
                    )
                else:
                    result = DiagnosticResult(
                        "Crypto API (BTC/USD)",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        {"status_code": response.status_code}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "Crypto API (BTC/USD)",
                False,
                f"Failed: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    async def _check_alpha_vantage(self):
        """Check Alpha Vantage API (optional)"""
        if not self.alpha_vantage_key:
            result = DiagnosticResult(
                "Alpha Vantage API",
                True,  # Pass since it's optional
                "Not configured (optional)",
                {"configured": False}
            )
            self.results.append(result)
            print(result)
            return

        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": "AAPL",
                        "apikey": self.alpha_vantage_key,
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if "Global Quote" in data:
                        price = data["Global Quote"].get("05. price", "N/A")
                        result = DiagnosticResult(
                            "Alpha Vantage API",
                            True,
                            f"AAPL price: ${price}",
                            {"price": price}
                        )
                    elif "Note" in data:
                        # Rate limited
                        result = DiagnosticResult(
                            "Alpha Vantage API",
                            False,
                            "Rate limited - too many requests",
                            {"note": data["Note"]}
                        )
                    else:
                        result = DiagnosticResult(
                            "Alpha Vantage API",
                            False,
                            f"Unexpected response: {str(data)[:100]}",
                            {"data": data}
                        )
                else:
                    result = DiagnosticResult(
                        "Alpha Vantage API",
                        False,
                        f"HTTP {response.status_code}",
                        {"status_code": response.status_code}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "Alpha Vantage API",
                False,
                f"Failed: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    async def _check_system_time(self):
        """Check system time is accurate (important for trading)"""
        import httpx

        try:
            # Get time from a reliable source (Alpaca)
            base_url = "https://paper-api.alpaca.markets" if self.trading_mode == "paper" else "https://api.alpaca.markets"
            headers = {
                "APCA-API-KEY-ID": self.alpaca_api_key,
                "APCA-API-SECRET-KEY": self.alpaca_secret_key,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/v2/clock", headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    server_time_str = data.get("timestamp", "")
                    server_time = datetime.fromisoformat(server_time_str.replace("Z", "+00:00"))
                    local_time = datetime.now(timezone.utc)
                    drift_seconds = abs((local_time - server_time).total_seconds())

                    # Time drift should be < 5 seconds
                    is_synced = drift_seconds < 5

                    result = DiagnosticResult(
                        "System Time Sync",
                        is_synced,
                        f"Drift: {drift_seconds:.2f}s (Local: {local_time.strftime('%H:%M:%S')}, Server: {server_time.strftime('%H:%M:%S')})",
                        {
                            "local_time": local_time.isoformat(),
                            "server_time": server_time_str,
                            "drift_seconds": drift_seconds,
                        }
                    )
                else:
                    result = DiagnosticResult(
                        "System Time Sync",
                        False,
                        "Could not verify time sync",
                        {}
                    )
        except Exception as e:
            result = DiagnosticResult(
                "System Time Sync",
                False,
                f"Error: {str(e)}",
                {"error": str(e)}
            )

        self.results.append(result)
        print(result)

    def _print_summary(self):
        """Print summary of all checks"""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"\nTotal checks: {total}")
        print(f"  ✓ Passed: {passed}")
        print(f"  ✗ Failed: {failed}")

        if failed > 0:
            print("\nFailed checks:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")

        # Critical issues
        critical_checks = [
            "Alpaca API Connection",
            "Alpaca Account",
            "Stock 1m Chart Timestamp",
            "Crypto 1m Chart Timestamp",
        ]

        critical_failures = [r for r in self.results if r.name in critical_checks and not r.passed]
        if critical_failures:
            print("\n⚠️  CRITICAL ISSUES DETECTED:")
            for r in critical_failures:
                print(f"  - {r.name}: {r.message}")

        print("\n" + "=" * 60)

    def get_json_report(self) -> str:
        """Get JSON report of all results"""
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
            "results": [r.to_dict() for r in self.results],
        }, indent=2)


async def main():
    parser = argparse.ArgumentParser(description="ChartSense Diagnostic Tool")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    diagnostic = ChartSenseDiagnostic(verbose=args.verbose)
    await diagnostic.run_all_checks()

    if args.json:
        print("\n" + diagnostic.get_json_report())


if __name__ == "__main__":
    asyncio.run(main())
