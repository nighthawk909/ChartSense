"""
Trading Bot Engine
Main bot orchestration - runs trading cycles, manages state, executes trades

The bot is designed to be always active:
- Regular hours: Normal trading with market orders
- Pre-market/After-hours: Extended hours trading with limit orders
- Overnight/Weekend: Analysis, discovery, preparation for next session
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session

from .alpaca_service import AlpacaService, get_alpaca_service
from .strategy_engine import StrategyEngine, SignalType, TradeType
from .risk_manager import RiskManager
from .indicators import IndicatorService
from .ai_advisor import get_ai_advisor
from .crypto_service import CryptoService
from .priority_scanner import PriorityScannerService, get_priority_scanner, PriorityTier
from .execution_logger import ExecutionLogger, ExecutionErrorCode, parse_api_error
from .smart_scanner import SmartScanner, get_smart_scanner
from .hierarchical_strategy import TradingHorizon, OpportunityQuality
from config import TradingConfig, get_trading_config
from database.models import Trade, Position, BotConfiguration, StockRepository, UserWatchlist
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


class BotState(str, Enum):
    """Trading bot operational state"""
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class TradingBot:
    """
    Main trading bot engine.
    Orchestrates market analysis, signal generation, and trade execution.
    """

    def __init__(
        self,
        alpaca_service: Optional[AlpacaService] = None,
        paper_trading: bool = None,
    ):
        """
        Initialize trading bot.

        Args:
            alpaca_service: Alpaca service instance
            paper_trading: Use paper trading (safer for testing). Reads from ALPACA_TRADING_MODE env var if not specified.
        """
        # Default to paper trading unless explicitly set to live
        if paper_trading is None:
            paper_trading = os.getenv("ALPACA_TRADING_MODE", "paper") == "paper"
        self.alpaca = alpaca_service or get_alpaca_service(paper_trading=paper_trading)
        self.strategy = StrategyEngine()
        self.risk_manager = RiskManager()
        self.indicator_service = IndicatorService()
        self.ai_advisor = get_ai_advisor()

        # Load centralized trading configuration
        self.trading_config = get_trading_config()

        # Bot state
        self.state = BotState.STOPPED
        self.start_time: Optional[datetime] = None
        self.last_trade_time: Optional[datetime] = None
        self.current_cycle: str = "idle"
        self.current_session: str = "unknown"  # pre_market, regular, after_hours, overnight, weekend
        self.previous_session: str = "unknown"  # Track previous session for transition detection
        self.error_message: Optional[str] = None

        # Queued trades for market open
        self._queued_trades: List[Dict[str, Any]] = []
        self.auto_queue_strong_signals = True  # Auto-queue STRONG BUY when market closed

        # Configuration (using TradingConfig for configurable values)
        self.enabled_symbols: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        self.user_symbols: List[str] = []  # User's personal stock picks
        self.paper_trading = paper_trading
        self.trading_hours_only = False  # Changed: trade during extended hours too!
        self.allow_extended_hours = True  # Trade pre-market and after-hours
        self.cycle_interval_seconds = self.trading_config.cycle_interval_seconds
        self.use_ai_discovery = True  # Use AI to discover stocks
        self.last_discovery_time: Optional[datetime] = None

        # Exit Strategy Settings (from TradingConfig)
        self.trailing_stop_enabled = False
        self.trailing_stop_pct = self.trading_config.trailing_stop_pct
        self.trailing_stop_activation_pct = self.trading_config.trailing_stop_activation_pct
        self.partial_profit_enabled = False
        self.partial_profit_pct = self.trading_config.partial_profit_pct
        self.partial_profit_at = self.trading_config.partial_profit_trigger_pct

        # Profit Reinvestment
        self.reinvest_profits = True
        self.compounding_enabled = True

        # Intraday Settings (from TradingConfig)
        self.intraday_enabled = False
        self.intraday_timeframe = "5min"
        self.max_trades_per_day = self.trading_config.max_trades_per_day
        self.trades_today = 0

        # Auto Trade Mode
        self.auto_trade_mode = False
        self.ai_risk_tolerance = "moderate"

        # Crypto Trading Settings - enabled by default for 24/7 trading
        self.crypto_trading_enabled = True
        # Expanded crypto list - popular trading pairs on Alpaca
        self.crypto_symbols: List[str] = [
            "BTC/USD",   # Bitcoin
            "ETH/USD",   # Ethereum
            "SOL/USD",   # Solana
            "DOGE/USD",  # Dogecoin
            "ADA/USD",   # Cardano
            "XRP/USD",   # Ripple
            "AVAX/USD",  # Avalanche
            "LINK/USD",  # Chainlink
            "DOT/USD",   # Polkadot
            "MATIC/USD", # Polygon
            "LTC/USD",   # Litecoin
            "UNI/USD",   # Uniswap
        ]
        self.crypto_max_positions = self.trading_config.crypto_max_positions
        self.crypto_entry_threshold = self.trading_config.crypto_entry_threshold
        self._crypto_positions: Dict[str, Dict] = {}  # Track crypto positions
        self._crypto_analysis_results: Dict[str, Dict] = {}  # Track latest analysis for each crypto
        self._last_crypto_analysis_time: Optional[datetime] = None

        # Crypto scan tracking
        self._crypto_scan_progress: Dict[str, Any] = {
            "total": 0,
            "scanned": 0,
            "current_symbol": None,
            "signals_found": 0,
            "best_opportunity": None,  # Best signal even if below threshold
            "scan_status": "idle",  # idle, scanning, exhausted, found_opportunity
            "scan_summary": "",
            "last_scan_completed": None,
            "next_scan_in_seconds": 0,
        }

        # 24/7 Auto Mode Settings
        self.auto_247_mode = True  # Automatically switch between stocks and crypto
        self.crypto_only_after_hours = True  # Focus on crypto when stock market closed
        self.aggressive_crypto_after_hours = True  # Increase crypto activity when stocks unavailable

        # Track partial sells
        self._partial_sold: Dict[str, bool] = {}  # Symbol -> has taken partial profit

        # Stock repository
        self._stock_scores: Dict[str, float] = {}  # Symbol -> last score
        self._ready_stocks: List[str] = []  # Stocks ready for entry

        # Stock analysis results (similar to crypto)
        self._stock_analysis_results: Dict[str, Dict] = {}  # Track latest analysis for each stock
        self._last_stock_analysis_time: Optional[datetime] = None

        # AI Decision Tracking
        self._ai_decisions: List[Dict[str, Any]] = []  # History of AI decisions
        self._last_ai_decision: Optional[Dict[str, Any]] = None  # Most recent AI decision

        # Tracking
        self._positions_cache: Dict[str, Dict] = {}
        self._running_task: Optional[asyncio.Task] = None

        # Priority Scanner for smart scanning
        self.priority_scanner = get_priority_scanner()

        # Enhanced Execution Logger with specific failure reasons
        self.execution_logger = ExecutionLogger()

        # Execution Log - tracks why trades were/weren't executed (legacy, kept for compatibility)
        self._execution_log: List[Dict[str, Any]] = []
        self._max_execution_log_size = 100

        # Tactical Controls
        self.new_entries_paused = False  # Pause new entries but monitor existing
        self.strategy_override: Optional[str] = None  # conservative, moderate, aggressive

        # Scan statistics
        self._total_scans_today = 0
        self._last_scan_reset_date: Optional[datetime] = None

        # Asset Class Mode for hybrid scanning
        # 'crypto' = crypto only, 'stocks' = stocks only, 'both' = hybrid
        self.asset_class_mode: str = 'both'

        # ===== HIERARCHICAL TRADING MODE =====
        # This is the "make money every day" intelligent strategy
        self.hierarchical_mode_enabled = True  # Use smart cascading scan
        self.smart_scanner = get_smart_scanner()  # Intelligent scanner
        self.daily_profit_target_pct = self.trading_config.daily_profit_target_pct
        self.current_trading_horizon: Optional[TradingHorizon] = None
        self._hierarchical_scan_results: Dict[str, Any] = {}

        # Stock scan tracking (similar to crypto scan tracking)
        self._stock_scan_progress: Dict[str, Any] = {
            "total": 0,
            "scanned": 0,
            "current_symbol": None,
            "signals_found": 0,
            "best_opportunity": None,
            "scan_status": "idle",
            "scan_summary": "",
            "last_scan_completed": None,
            "next_scan_in_seconds": 0,
            "market_status": "unknown",  # open, closed, pre_market, after_hours
        }

    async def start(self, config: Optional[Dict[str, Any]] = None):
        """
        Start the trading bot.

        Args:
            config: Optional configuration override
        """
        if self.state == BotState.RUNNING:
            logger.warning("Bot is already running")
            return

        logger.info("Starting trading bot...")

        # Load configuration
        if config:
            self._apply_config(config)

        # Load config from database
        await self._load_db_config()

        # Verify Alpaca connection
        try:
            account = await self.alpaca.get_account()
            logger.info(f"Connected to Alpaca. Equity: ${account['equity']:.2f}")
        except Exception as e:
            self.state = BotState.ERROR
            self.error_message = f"Failed to connect to Alpaca: {e}"
            logger.error(self.error_message)
            return

        self.state = BotState.RUNNING
        self.start_time = datetime.now()
        self.error_message = None

        # Start the main loop
        self._running_task = asyncio.create_task(self._main_loop())
        logger.info("Trading bot started successfully")

    async def stop(self):
        """Stop the trading bot"""
        if self.state == BotState.STOPPED:
            logger.warning("Bot is already stopped")
            return

        logger.info("Stopping trading bot...")
        self.state = BotState.STOPPED

        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None

        logger.info("Trading bot stopped")

    async def pause(self):
        """Pause the trading bot (keeps positions, stops new trades)"""
        if self.state != BotState.RUNNING:
            logger.warning("Bot is not running")
            return

        logger.info("Pausing trading bot...")
        self.state = BotState.PAUSED
        logger.info("Trading bot paused")

    async def resume(self):
        """Resume the trading bot from paused state"""
        if self.state != BotState.PAUSED:
            logger.warning("Bot is not paused")
            return

        logger.info("Resuming trading bot...")
        self.state = BotState.RUNNING
        logger.info("Trading bot resumed")

    def _apply_config(self, config: Dict[str, Any]):
        """Apply configuration dictionary"""
        if "enabled_symbols" in config:
            # Validate and filter symbols before applying
            validated_symbols = self._validate_and_filter_symbols(config["enabled_symbols"], allow_crypto=False)
            if validated_symbols:
                self.enabled_symbols = validated_symbols
                logger.info(f"[CONFIG] Applied {len(validated_symbols)} validated symbols")
            else:
                logger.warning("[CONFIG] No valid symbols in config, keeping existing symbols")
        if "paper_trading" in config:
            self.paper_trading = config["paper_trading"]
        if "trading_hours_only" in config:
            self.trading_hours_only = config["trading_hours_only"]
        if "cycle_interval_seconds" in config:
            self.cycle_interval_seconds = config["cycle_interval_seconds"]

        # Update sub-components
        if "entry_score_threshold" in config:
            self.strategy.entry_threshold = config["entry_score_threshold"]
        if "swing_profit_target_pct" in config:
            self.strategy.swing_profit_target_pct = config["swing_profit_target_pct"]
        if "longterm_profit_target_pct" in config:
            self.strategy.longterm_profit_target_pct = config["longterm_profit_target_pct"]

        if "max_positions" in config:
            self.risk_manager.max_positions = config["max_positions"]
        if "risk_per_trade_pct" in config:
            self.risk_manager.risk_per_trade_pct = config["risk_per_trade_pct"]
        if "max_daily_loss_pct" in config:
            self.risk_manager.max_daily_loss_pct = config["max_daily_loss_pct"]
        if "default_stop_loss_pct" in config:
            self.risk_manager.default_stop_loss_pct = config["default_stop_loss_pct"]

        # Exit Strategies
        if "trailing_stop_enabled" in config:
            self.trailing_stop_enabled = config["trailing_stop_enabled"]
        if "trailing_stop_pct" in config:
            self.trailing_stop_pct = config["trailing_stop_pct"]
        if "trailing_stop_activation_pct" in config:
            self.trailing_stop_activation_pct = config["trailing_stop_activation_pct"]
        if "partial_profit_enabled" in config:
            self.partial_profit_enabled = config["partial_profit_enabled"]
        if "partial_profit_pct" in config:
            self.partial_profit_pct = config["partial_profit_pct"]
        if "partial_profit_at" in config:
            self.partial_profit_at = config["partial_profit_at"]

        # Profit Reinvestment
        if "reinvest_profits" in config:
            self.reinvest_profits = config["reinvest_profits"]
        if "compounding_enabled" in config:
            self.compounding_enabled = config["compounding_enabled"]

        # Intraday
        if "intraday_enabled" in config:
            self.intraday_enabled = config["intraday_enabled"]
        if "intraday_timeframe" in config:
            self.intraday_timeframe = config["intraday_timeframe"]
        if "max_trades_per_day" in config:
            self.max_trades_per_day = config["max_trades_per_day"]

        # Auto Trade Mode
        if "auto_trade_mode" in config:
            self.auto_trade_mode = config["auto_trade_mode"]
        if "ai_risk_tolerance" in config:
            self.ai_risk_tolerance = config["ai_risk_tolerance"]
            # Apply AI risk tolerance presets
            if self.auto_trade_mode:
                self._apply_ai_risk_preset(config["ai_risk_tolerance"])

        # Crypto Trading
        if "crypto_trading_enabled" in config:
            self.crypto_trading_enabled = config["crypto_trading_enabled"]
        if "crypto_symbols" in config:
            self.crypto_symbols = config["crypto_symbols"]
        if "crypto_max_positions" in config:
            self.crypto_max_positions = config["crypto_max_positions"]

    def _apply_ai_risk_preset(self, risk_level: str):
        """Apply AI-controlled risk presets based on risk tolerance"""
        presets = {
            "conservative": {
                "risk_per_trade_pct": 0.01,
                "max_positions": 3,
                "entry_threshold": 80.0,
                "trailing_stop_pct": 0.02,
                "partial_profit_at": 0.03,
            },
            "moderate": {
                "risk_per_trade_pct": 0.02,
                "max_positions": 5,
                "entry_threshold": 70.0,
                "trailing_stop_pct": 0.03,
                "partial_profit_at": 0.05,
            },
            "aggressive": {
                "risk_per_trade_pct": 0.03,
                "max_positions": 8,
                "entry_threshold": 65.0,
                "trailing_stop_pct": 0.05,
                "partial_profit_at": 0.08,
            },
        }

        preset = presets.get(risk_level, presets["moderate"])
        self.risk_manager.risk_per_trade_pct = preset["risk_per_trade_pct"]
        self.risk_manager.max_positions = preset["max_positions"]
        self.strategy.entry_threshold = preset["entry_threshold"]
        self.trailing_stop_pct = preset["trailing_stop_pct"]
        self.partial_profit_at = preset["partial_profit_at"]

        logger.info(f"Applied AI risk preset: {risk_level}")

    def _normalize_and_validate_symbol(self, symbol: str, allow_crypto: bool = True) -> tuple[str, bool, str]:
        """
        Normalize and validate a trading symbol.

        Args:
            symbol: The symbol to validate (e.g., "AAPL", "btc/usd", " MSFT ")
            allow_crypto: Whether to allow crypto symbols

        Returns:
            Tuple of (normalized_symbol, is_valid, error_message)
            - normalized_symbol: Uppercase, stripped symbol (or empty string if invalid)
            - is_valid: Whether the symbol passed validation
            - error_message: Description of validation failure (empty if valid)
        """
        # Check for empty/None input
        if not symbol or not isinstance(symbol, str):
            logger.warning(f"[SYMBOL_VALIDATION] Invalid symbol: empty or not a string")
            return "", False, "Symbol must be a non-empty string"

        # Strip whitespace and convert to uppercase
        normalized = symbol.strip().upper()

        # Check if empty after stripping
        if not normalized:
            logger.warning(f"[SYMBOL_VALIDATION] Invalid symbol: '{symbol}' is empty after stripping whitespace")
            return "", False, "Symbol is empty after removing whitespace"

        # Check length (1-10 characters for standard symbols)
        if len(normalized) < 1 or len(normalized) > 10:
            logger.warning(f"[SYMBOL_VALIDATION] Invalid symbol length: '{normalized}' ({len(normalized)} chars, expected 1-10)")
            return normalized, False, f"Symbol length must be 1-10 characters, got {len(normalized)}"

        # Detect crypto vs stock
        is_crypto = (
            '/' in normalized or
            normalized.endswith('USD') or
            normalized.endswith('USDT') or
            normalized.endswith('USDC')
        )

        if is_crypto:
            if not allow_crypto:
                logger.warning(f"[SYMBOL_VALIDATION] Crypto symbol '{normalized}' not allowed in stock context")
                return normalized, False, "Crypto symbols not allowed in this context"

            # Normalize crypto symbols to standard format (e.g., BTC/USD)
            # Accept: BTC/USD, BTCUSD, BTC-USD -> normalize to BTC/USD
            crypto_normalized = normalized.replace("-", "/")

            # If no slash but ends with USD/USDT/USDC, add slash
            if '/' not in crypto_normalized:
                for suffix in ['USDT', 'USDC', 'USD']:
                    if crypto_normalized.endswith(suffix):
                        base = crypto_normalized[:-len(suffix)]
                        if base:  # Ensure base is not empty
                            crypto_normalized = f"{base}/{suffix}"
                            break

            # Validate crypto format: BASE/QUOTE
            if '/' in crypto_normalized:
                parts = crypto_normalized.split('/')
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    logger.warning(f"[SYMBOL_VALIDATION] Invalid crypto format: '{normalized}'")
                    return normalized, False, f"Invalid crypto symbol format: expected BASE/QUOTE"

                # Validate base and quote are alphanumeric
                base, quote = parts
                if not base.isalnum() or not quote.isalnum():
                    logger.warning(f"[SYMBOL_VALIDATION] Crypto symbol contains invalid characters: '{normalized}'")
                    return normalized, False, "Crypto symbol must contain only alphanumeric characters"

                logger.debug(f"[SYMBOL_VALIDATION] Validated crypto symbol: '{symbol}' -> '{crypto_normalized}'")
                return crypto_normalized, True, ""
            else:
                logger.warning(f"[SYMBOL_VALIDATION] Could not parse crypto symbol: '{normalized}'")
                return normalized, False, "Could not parse crypto symbol format"
        else:
            # Stock symbol validation
            # Stock symbols should be 1-5 uppercase letters (some exceptions like BRK.A, BRK.B)

            # Check for suspicious characters
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
            if not all(c in valid_chars for c in normalized):
                invalid_chars = [c for c in normalized if c not in valid_chars]
                logger.warning(f"[SYMBOL_VALIDATION] Stock symbol contains invalid characters: '{normalized}' (found: {invalid_chars})")
                return normalized, False, f"Stock symbol contains invalid characters: {invalid_chars}"

            # Warn about unusually long stock symbols (>5 chars without special chars)
            if len(normalized) > 5 and '.' not in normalized and '-' not in normalized:
                logger.warning(f"[SYMBOL_VALIDATION] Suspicious stock symbol (unusually long): '{normalized}'")
                # Still allow but log warning - could be valid (e.g., some OTC stocks)

            logger.debug(f"[SYMBOL_VALIDATION] Validated stock symbol: '{symbol}' -> '{normalized}'")
            return normalized, True, ""

    def _validate_and_filter_symbols(self, symbols: List[str], allow_crypto: bool = False) -> List[str]:
        """
        Validate and normalize a list of symbols, filtering out invalid ones.

        Args:
            symbols: List of symbols to validate
            allow_crypto: Whether to allow crypto symbols in the list

        Returns:
            List of valid, normalized symbols (invalid symbols are logged and removed)
        """
        if not symbols:
            return []

        valid_symbols = []
        seen = set()

        for symbol in symbols:
            normalized, is_valid, error_msg = self._normalize_and_validate_symbol(symbol, allow_crypto=allow_crypto)

            if is_valid:
                # Avoid duplicates
                if normalized not in seen:
                    valid_symbols.append(normalized)
                    seen.add(normalized)
            else:
                logger.warning(f"[SYMBOL_FILTER] Rejected invalid symbol '{symbol}': {error_msg}")

        if len(valid_symbols) < len(symbols):
            rejected_count = len(symbols) - len(valid_symbols)
            logger.info(f"[SYMBOL_FILTER] Filtered {rejected_count} invalid symbols, kept {len(valid_symbols)} valid")

        return valid_symbols

    async def _load_db_config(self):
        """Load configuration from database including user watchlist and stock repository"""
        try:
            db = SessionLocal()

            # Load bot configuration
            config = db.query(BotConfiguration).filter(BotConfiguration.is_active == True).first()

            if config:
                # Validate symbols from database config
                if config.enabled_symbols:
                    validated = self._validate_and_filter_symbols(config.enabled_symbols, allow_crypto=False)
                    self.enabled_symbols = validated if validated else self.enabled_symbols
                self.paper_trading = config.paper_trading
                self.trading_hours_only = config.trading_hours_only

                self.strategy.entry_threshold = config.entry_score_threshold
                self.strategy.swing_profit_target_pct = config.swing_profit_target_pct
                self.strategy.longterm_profit_target_pct = config.longterm_profit_target_pct

                self.risk_manager.max_positions = config.max_positions
                self.risk_manager.max_position_size_pct = config.max_position_size_pct
                self.risk_manager.risk_per_trade_pct = config.risk_per_trade_pct
                self.risk_manager.max_daily_loss_pct = config.max_daily_loss_pct
                self.risk_manager.default_stop_loss_pct = config.default_stop_loss_pct

                # Exit Strategies (using TradingConfig values as defaults)
                self.trailing_stop_enabled = getattr(config, 'trailing_stop_enabled', False)
                self.trailing_stop_pct = getattr(config, 'trailing_stop_pct', self.trading_config.trailing_stop_pct)
                self.trailing_stop_activation_pct = getattr(config, 'trailing_stop_activation_pct', self.trading_config.trailing_stop_activation_pct)
                self.partial_profit_enabled = getattr(config, 'partial_profit_enabled', False)
                self.partial_profit_pct = getattr(config, 'partial_profit_pct', self.trading_config.partial_profit_pct)
                self.partial_profit_at = getattr(config, 'partial_profit_at', self.trading_config.partial_profit_trigger_pct)

                # Profit Reinvestment
                self.reinvest_profits = getattr(config, 'reinvest_profits', True)
                self.compounding_enabled = getattr(config, 'compounding_enabled', True)

                # Intraday (using TradingConfig values as defaults)
                self.intraday_enabled = getattr(config, 'intraday_enabled', False)
                self.intraday_timeframe = getattr(config, 'intraday_timeframe', "5min")
                self.max_trades_per_day = getattr(config, 'max_trades_per_day', self.trading_config.max_trades_per_day)

                # Auto Trade Mode
                self.auto_trade_mode = getattr(config, 'auto_trade_mode', False)
                self.ai_risk_tolerance = getattr(config, 'ai_risk_tolerance', "moderate")

                if self.auto_trade_mode:
                    self._apply_ai_risk_preset(self.ai_risk_tolerance)

                # Crypto Trading
                self.crypto_trading_enabled = getattr(config, 'crypto_trading_enabled', False)
                db_crypto_symbols = getattr(config, 'crypto_symbols', None)
                # If database has old minimal list, use expanded default instead
                if db_crypto_symbols and len(db_crypto_symbols) <= 2:
                    logger.info(f"Database has minimal crypto list ({db_crypto_symbols}), using expanded default")
                    # Keep the expanded default from __init__
                elif db_crypto_symbols:
                    self.crypto_symbols = db_crypto_symbols
                self.crypto_max_positions = getattr(config, 'crypto_max_positions', 2)

                logger.info(f"Loaded config '{config.name}' from database")
                if self.crypto_trading_enabled:
                    logger.info(f"Crypto trading enabled for: {self.crypto_symbols}")

            # Load user watchlist (highest priority stocks)
            user_stocks = db.query(UserWatchlist).filter(UserWatchlist.auto_trade == True).all()
            raw_user_symbols = [s.symbol for s in user_stocks]
            # Validate user symbols
            self.user_symbols = self._validate_and_filter_symbols(raw_user_symbols, allow_crypto=False)
            if self.user_symbols:
                logger.info(f"Loaded {len(self.user_symbols)} user stocks: {self.user_symbols}")

            # Load active stocks from repository
            max_symbols = self.trading_config.max_enabled_symbols
            repo_stocks = db.query(StockRepository).filter(
                StockRepository.is_active == True
            ).order_by(StockRepository.priority.desc()).limit(max_symbols).all()

            raw_repo_symbols = [s.symbol for s in repo_stocks]
            # Validate repository symbols
            repo_symbols = self._validate_and_filter_symbols(raw_repo_symbols, allow_crypto=False)

            # Merge all symbols: user picks first (highest priority), then enabled, then repository
            # Note: enabled_symbols already validated, user_symbols and repo_symbols just validated above
            all_symbols = []
            seen = set()
            for symbol in self.user_symbols + self.enabled_symbols + repo_symbols:
                if symbol not in seen:
                    all_symbols.append(symbol)
                    seen.add(symbol)

            self.enabled_symbols = all_symbols[:max_symbols]  # Cap at configured max for API limits
            logger.info(f"Trading {len(self.enabled_symbols)} validated symbols: {self.enabled_symbols}")

            db.close()
        except Exception as e:
            logger.warning(f"Could not load config from database: {e}")

    async def _main_loop(self):
        """
        Main trading loop - always active, adapts to market session.

        IMPORTANT: Stock and Crypto scanning now run CONCURRENTLY using asyncio.gather()
        to maximize scanning efficiency. Neither scanner waits for the other.

        Sessions:
        - regular: Normal trading with market orders
        - pre_market: Extended hours with limit orders (4:00 AM - 9:30 AM ET)
        - after_hours: Extended hours with limit orders (4:00 PM - 8:00 PM ET)
        - overnight/weekend: Analysis, discovery, preparation (no trading)
        """
        logger.info("Main trading loop started - Bot will stay active 24/7 with CONCURRENT scanning")

        while self.state in [BotState.RUNNING, BotState.PAUSED]:
            try:
                if self.state == BotState.PAUSED:
                    self.current_cycle = "paused"
                    await asyncio.sleep(5)
                    continue

                # Get detailed market session info
                market_info = await self.alpaca.get_market_hours_info()
                new_session = market_info.get("session", "unknown")
                can_trade = market_info.get("can_trade", False)
                is_extended = market_info.get("can_trade_extended", False)

                # Detect session transition to regular market hours
                if new_session == "regular" and self.previous_session != "regular":
                    logger.info(f"🔔 Market session changed: {self.previous_session} → regular")
                    # Execute any queued trades from overnight/weekend
                    if self._queued_trades and self.auto_trade_mode:
                        await self._execute_queued_trades()

                self.previous_session = self.current_session
                self.current_session = new_session

                logger.debug(f"Session: {self.current_session}, Can trade: {can_trade}, Extended: {is_extended}")

                # Check daily loss limit
                account = await self.alpaca.get_account()
                if self.risk_manager.is_daily_loss_limit_hit(account["equity"]):
                    self.current_cycle = "daily_loss_limit_paused"
                    logger.warning("Daily loss limit reached, pausing trading")
                    await asyncio.sleep(300)
                    continue

                # Determine what to do based on session and asset class mode
                should_scan_stocks = self.asset_class_mode in ['stocks', 'both']
                should_scan_crypto = self.asset_class_mode in ['crypto', 'both'] and self.crypto_trading_enabled

                # Update stock scan progress with market status
                self._stock_scan_progress["market_status"] = self.current_session

                # ===== CONCURRENT SCANNING =====
                # Build list of tasks to run in parallel
                concurrent_tasks = []

                if self.current_session in ["overnight", "weekend"]:
                    # Can't trade stocks, but stay active - do analysis and discovery
                    self.current_cycle = "off_hours_concurrent"

                    # Update stock scan progress when market closed
                    if should_scan_stocks:
                        self._stock_scan_progress["scan_status"] = "market_closed"
                        self._stock_scan_progress["scan_summary"] = f"Stock market closed ({self.current_session}). Stocks will be scanned when market opens."

                    # Off-hours analysis runs for stocks
                    concurrent_tasks.append(self._run_off_hours_cycle())

                    # 24/7 Mode: Crypto trades around the clock!
                    if should_scan_crypto:
                        # Run crypto cycle more frequently when it's the only game in town
                        if self.aggressive_crypto_after_hours:
                            concurrent_tasks.append(self._run_aggressive_crypto_cycle())
                        else:
                            concurrent_tasks.append(self._run_crypto_cycle())

                    # Execute all tasks concurrently
                    if concurrent_tasks:
                        self.current_cycle = "scanning_concurrent"
                        await asyncio.gather(*concurrent_tasks, return_exceptions=True)

                    # Shorter sleep when actively trading crypto
                    sleep_time = 60 if should_scan_crypto and self.aggressive_crypto_after_hours else 300
                    await asyncio.sleep(sleep_time)

                elif self.current_session == "regular":
                    # Normal trading hours - run both stock and crypto cycles CONCURRENTLY
                    self.current_cycle = "regular_concurrent"

                    if should_scan_stocks:
                        concurrent_tasks.append(self._run_trading_cycle(extended_hours=False))
                    else:
                        self._stock_scan_progress["scan_status"] = "disabled"
                        self._stock_scan_progress["scan_summary"] = "Stock scanning disabled (crypto only mode)"

                    # Crypto is 24/7 - run in parallel with stocks
                    if should_scan_crypto:
                        concurrent_tasks.append(self._run_crypto_cycle())

                    # Execute both scanners CONCURRENTLY - neither waits for the other
                    if concurrent_tasks:
                        logger.info(f"Starting CONCURRENT scan: {len(concurrent_tasks)} scanner(s) running in parallel")
                        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

                        # Log any exceptions that occurred
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"Concurrent task {i} failed: {result}")

                    self.current_cycle = "cycle_complete"
                    await asyncio.sleep(self.cycle_interval_seconds)

                elif self.current_session in ["pre_market", "after_hours"]:
                    # Extended hours - both scanners run concurrently
                    self.current_cycle = "extended_concurrent"

                    if should_scan_stocks:
                        if self.allow_extended_hours:
                            concurrent_tasks.append(self._run_trading_cycle(extended_hours=True))
                        else:
                            self._stock_scan_progress["scan_status"] = "extended_hours_waiting"
                            self._stock_scan_progress["scan_summary"] = f"Stock market in {self.current_session.replace('_', ' ')}. Extended hours trading disabled."
                            concurrent_tasks.append(self._run_off_hours_cycle())

                    # Crypto trades 24/7
                    if should_scan_crypto:
                        concurrent_tasks.append(self._run_crypto_cycle())

                    # Execute both scanners CONCURRENTLY
                    if concurrent_tasks:
                        logger.info(f"Starting CONCURRENT extended hours scan: {len(concurrent_tasks)} scanner(s)")
                        await asyncio.gather(*concurrent_tasks, return_exceptions=True)

                    await asyncio.sleep(self.cycle_interval_seconds * 2)  # Slower during extended

                else:
                    # Unknown session - be cautious, but still do crypto if enabled
                    self.current_cycle = "unknown_session"
                    if should_scan_crypto:
                        await self._run_crypto_cycle()
                    await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.error_message = str(e)
                self.current_cycle = "error_recovery"
                # Log to execution logger
                self.execution_logger.log_failure(
                    symbol="SYSTEM",
                    asset_class="system",
                    side="N/A",
                    quantity=0,
                    price=0,
                    order_type="system",
                    error_code=ExecutionErrorCode.UNKNOWN_ERROR,
                    error_message=f"Main loop error: {str(e)}",
                )
                await asyncio.sleep(30)

        logger.info("Main trading loop ended")

    async def _run_aggressive_crypto_cycle(self):
        """
        Run aggressive crypto scanning when stock market is closed.
        Runs two crypto scans with a short pause in between.
        """
        logger.info("Running aggressive crypto cycle (market closed, crypto focus)")
        await self._run_crypto_cycle()
        await asyncio.sleep(30)  # Short pause between scans
        await self._run_crypto_cycle()

    async def _run_off_hours_cycle(self):
        """Run analysis during off-hours (overnight/weekend) - no trading but queue strong signals"""
        logger.debug("Running off-hours analysis cycle...")

        try:
            # AI discovery runs during off hours too
            if self.use_ai_discovery and self.ai_advisor.enabled:
                await self._ai_discover_stocks()

            # Analyze all stocks and update their scores for when market opens
            self.current_cycle = "pre_analyzing"
            scan_batch = self.trading_config.scan_batch_size
            for symbol in self.enabled_symbols[:scan_batch]:  # Limit to avoid rate limits
                try:
                    signal = await self._analyze_symbol(symbol)
                    if signal:
                        self._stock_scores[symbol] = signal.score
                        # Track stocks that are ready for entry
                        if signal.signal_type == SignalType.BUY and signal.score >= self.strategy.entry_threshold:
                            if symbol not in self._ready_stocks:
                                self._ready_stocks.append(symbol)
                                logger.info(f"Stock {symbol} is ready for entry (score: {signal.score:.1f})")

                            # AUTO-QUEUE strong signals for market open
                            if self.auto_queue_strong_signals and signal.score >= 75:
                                self.queue_trade(
                                    symbol=symbol,
                                    signal="BUY",
                                    confidence=signal.score,
                                    reason=f"Off-hours analysis: Strong BUY signal (score: {signal.score:.1f})"
                                )
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol} during off-hours: {e}")

            # Update repository with scores
            await self._update_repository_scores()

            # Log queue status
            if self._queued_trades:
                logger.info(f"📋 {len(self._queued_trades)} trade(s) queued for market open")

            self.current_cycle = "off_hours_idle"

        except Exception as e:
            logger.error(f"Error in off-hours cycle: {e}")

    async def _update_repository_scores(self):
        """Update stock repository with latest analysis scores"""
        if not self._stock_scores:
            return

        try:
            db = SessionLocal()
            for symbol, score in self._stock_scores.items():
                repo_stock = db.query(StockRepository).filter(StockRepository.symbol == symbol).first()
                if repo_stock:
                    repo_stock.last_analysis_score = score
                    repo_stock.last_analysis_time = datetime.now()
                    repo_stock.is_tradeable = score >= self.strategy.entry_threshold
            db.commit()
            db.close()
        except Exception as e:
            logger.debug(f"Could not update repository scores: {e}")

    async def _run_hierarchical_trading_cycle(self, extended_hours: bool = False):
        """
        Run intelligent hierarchical trading cycle - the "make money every day" logic.

        This method cascades through trading horizons:
        1. First check for SWING opportunities (multi-day, 5-15% targets)
        2. If nothing good, check INTRADAY (same-day, 1-3% targets)
        3. If nothing good, check SCALP (quick 0.3-1% gains)

        Goal: Find profitable opportunities EVERY trading day.
        """
        self.current_cycle = "hierarchical_scanning"
        logger.info("[Hierarchical] Starting intelligent cascading scan...")

        try:
            # Get account info
            account = await self.alpaca.get_account()
            equity = account["equity"]
            buying_power = account["buying_power"]

            # Get current positions
            positions = await self.alpaca.get_positions()
            self._positions_cache = {p["symbol"]: p for p in positions}

            # Check existing positions for exits first
            self.current_cycle = "checking_exits"
            await self._check_exit_signals(positions)

            # Refresh symbols from watchlist
            await self._refresh_symbols_from_watchlist()

            # Count stock positions (exclude crypto)
            stock_positions = {k: v for k, v in self._positions_cache.items()
                              if "/" not in k and not k.endswith("USD")}
            num_stock_positions = len(stock_positions)
            max_stock_positions = self.risk_manager.max_positions

            # Check if at max capacity - only monitor existing positions, don't scan for new ones
            # Capacity is reached if either:
            # 1. Position count is at max
            # 2. Buying power is too low (< $100 minimum to open meaningful position)
            MIN_BUYING_POWER_FOR_NEW_POSITION = self.trading_config.min_buying_power_for_position
            at_max_positions = num_stock_positions >= max_stock_positions
            insufficient_buying_power = float(buying_power) < MIN_BUYING_POWER_FOR_NEW_POSITION
            at_max_capacity = at_max_positions or insufficient_buying_power

            if at_max_capacity:
                # Determine the specific reason
                if at_max_positions and insufficient_buying_power:
                    capacity_reason = f"At max positions ({num_stock_positions}/{max_stock_positions}) and low buying power (${float(buying_power):.2f})"
                elif at_max_positions:
                    capacity_reason = f"At max positions ({num_stock_positions}/{max_stock_positions})"
                else:
                    capacity_reason = f"Insufficient buying power (${float(buying_power):.2f} < ${MIN_BUYING_POWER_FOR_NEW_POSITION} minimum)"

                # At max capacity - update status to show monitoring mode only
                self._stock_scan_progress = {
                    "total": 0,
                    "scanned": 0,
                    "current_symbol": None,
                    "signals_found": 0,
                    "best_opportunity": None,
                    "scan_status": "at_capacity",
                    "scan_summary": f"{capacity_reason}. Monitoring existing positions only.",
                    "last_scan_completed": datetime.now().isoformat(),
                    "next_scan_in_seconds": self.cycle_interval_seconds,
                    "market_status": "regular" if not extended_hours else "extended",
                    "monitoring_only": True,
                    "positions_held": list(stock_positions.keys()),
                    "buying_power": float(buying_power),
                }
                logger.info(f"[Hierarchical] Capacity reached: {capacity_reason} - monitoring only, no new position scans")
                return  # Exit early - no need to scan for new positions

            # Get symbols to scan (exclude those we already have positions in)
            symbols_to_scan = [s for s in self.enabled_symbols if s not in self._positions_cache]

            if not symbols_to_scan:
                logger.info("[Hierarchical] No symbols to scan (all in positions)")
                self._stock_scan_progress["scan_summary"] = "All symbols already in positions"
                return

            # Update scan progress
            self._stock_scan_progress = {
                "total": len(symbols_to_scan),
                "scanned": 0,
                "current_symbol": None,
                "signals_found": 0,
                "best_opportunity": None,
                "scan_status": "hierarchical_scanning",
                "scan_summary": f"Starting hierarchical cascade scan... ({num_stock_positions}/{max_stock_positions} positions)",
                "last_scan_completed": None,
                "next_scan_in_seconds": self.cycle_interval_seconds,
                "market_status": "regular" if not extended_hours else "extended",
                "current_positions": num_stock_positions,
                "max_positions": max_stock_positions,
            }

            # Run the full cascade scan (Swing -> Intraday -> Scalp)
            best_opportunity, scan_results = await self.smart_scanner.full_cascade_scan(
                symbols=symbols_to_scan,
                max_cascades=3,
            )

            # Store results for UI
            self._hierarchical_scan_results = {
                "best_opportunity": {
                    "symbol": best_opportunity.symbol,
                    "horizon": best_opportunity.horizon.value,
                    "quality": best_opportunity.quality.value,
                    "score": best_opportunity.overall_score,
                    "direction": best_opportunity.direction,
                    "entry_price": best_opportunity.entry_price,
                    "stop_loss": best_opportunity.stop_loss,
                    "target_1": best_opportunity.target_1,
                    "target_2": best_opportunity.target_2,
                    "risk_reward": best_opportunity.risk_reward_ratio,
                    "patterns": best_opportunity.patterns_detected,
                    "elliott_wave": best_opportunity.elliott_wave,
                    "confluence_factors": best_opportunity.confluence_factors,
                    "warnings": best_opportunity.warnings,
                } if best_opportunity else None,
                "scan_summary": self.smart_scanner.get_scan_summary(),
                "cascades_run": len(scan_results),
                "timestamp": datetime.now().isoformat(),
            }

            # Update stock scan progress
            self._stock_scan_progress["scanned"] = len(symbols_to_scan)
            self._stock_scan_progress["signals_found"] = sum(r.opportunities_found for r in scan_results)

            if best_opportunity:
                self.current_trading_horizon = best_opportunity.horizon
                self._stock_scan_progress["best_opportunity"] = {
                    "symbol": best_opportunity.symbol,
                    "horizon": best_opportunity.horizon.value,
                    "quality": best_opportunity.quality.value,
                    "score": best_opportunity.overall_score,
                }

                # Check if we should execute
                if best_opportunity.quality in [OpportunityQuality.EXCELLENT, OpportunityQuality.GOOD]:
                    logger.info(
                        f"[Hierarchical] Found {best_opportunity.quality.value} opportunity: "
                        f"{best_opportunity.symbol} ({best_opportunity.horizon.value}) "
                        f"Score: {best_opportunity.overall_score:.1f}"
                    )

                    # Check risk management
                    can_trade, reason = self.risk_manager.can_open_position(
                        equity=equity,
                        buying_power=buying_power,
                        current_positions=len(positions),
                    )

                    if can_trade and not self.new_entries_paused:
                        # Calculate position size
                        position_size = self.risk_manager.calculate_position_size(
                            equity=equity,
                            price=best_opportunity.entry_price,
                            stop_loss_pct=abs(
                                (best_opportunity.entry_price - best_opportunity.stop_loss) /
                                best_opportunity.entry_price
                            ),
                        )

                        if position_size > 0:
                            logger.info(
                                f"[Hierarchical] Executing {best_opportunity.direction} on "
                                f"{best_opportunity.symbol}: {position_size} shares @ ${best_opportunity.entry_price:.2f}"
                            )

                            # Execute the trade
                            await self._execute_hierarchical_entry(
                                opportunity=best_opportunity,
                                quantity=position_size,
                                extended_hours=extended_hours,
                            )
                        else:
                            logger.warning(f"[Hierarchical] Position size calculated as 0 - skipping")
                    else:
                        logger.info(f"[Hierarchical] Cannot trade: {reason}")
                        self._stock_scan_progress["scan_summary"] = f"Opportunity found but blocked: {reason}"
                else:
                    self._stock_scan_progress["scan_summary"] = (
                        f"Best opportunity is {best_opportunity.quality.value} - "
                        f"waiting for better setup"
                    )
            else:
                self._stock_scan_progress["scan_summary"] = "No opportunities found after full cascade"
                logger.info("[Hierarchical] No tradeable opportunities found after full cascade")

            self._stock_scan_progress["last_scan_completed"] = datetime.now().isoformat()
            self.current_cycle = "cycle_complete"

        except Exception as e:
            logger.error(f"[Hierarchical] Error in hierarchical trading cycle: {e}")
            self._stock_scan_progress["scan_status"] = "error"
            self._stock_scan_progress["scan_summary"] = f"Error: {str(e)}"

    async def _execute_hierarchical_entry(
        self,
        opportunity,  # TradingOpportunity
        quantity: int,
        extended_hours: bool = False,
    ):
        """Execute a trade based on hierarchical opportunity"""
        symbol = opportunity.symbol
        side = "buy" if opportunity.direction == "LONG" else "sell"

        try:
            # Use limit order for extended hours, market order otherwise
            if extended_hours:
                result = await self.alpaca.submit_extended_hours_order(
                    symbol=symbol,
                    quantity=quantity,
                    side=side,
                    limit_price=opportunity.entry_price,
                )
            else:
                result = await self.alpaca.submit_market_order(
                    symbol=symbol,
                    quantity=quantity,
                    side=side,
                    time_in_force="day",
                )

            if result and result.get("id"):
                logger.info(f"[Hierarchical] Order placed: {result['id']} for {symbol}")

                # Store position in database with hierarchical metadata
                db = SessionLocal()
                try:
                    # Map horizon to trade type
                    trade_type_map = {
                        TradingHorizon.LONG: "LONG_TERM",
                        TradingHorizon.SWING: "SWING",
                        TradingHorizon.INTRADAY: "INTRADAY",
                        TradingHorizon.SCALP: "SCALP",
                    }

                    # Build detailed entry reason with trade plan
                    entry_reason = self._build_entry_reason(opportunity)

                    # Build indicators snapshot
                    indicators_snapshot = {
                        "scores": {
                            "overall": opportunity.overall_score,
                            "trend": opportunity.trend_score,
                            "momentum": opportunity.momentum_score,
                            "pattern": opportunity.pattern_score,
                            "volume": opportunity.volume_score,
                            "multi_tf": opportunity.multi_tf_score,
                        },
                        "levels": opportunity.key_levels,
                        "risk_reward": opportunity.risk_reward_ratio,
                        "timeframes": {
                            "primary": opportunity.primary_timeframe,
                            "confirmation": opportunity.confirmation_timeframe,
                            "entry": opportunity.entry_timeframe,
                        },
                    }

                    # Build confluence factors
                    confluence_factors = {
                        "confirming": opportunity.confluence_factors,
                        "patterns": opportunity.patterns_detected,
                        "elliott_wave": opportunity.elliott_wave,
                        "warnings": opportunity.warnings,
                    }

                    new_position = Position(
                        symbol=symbol,
                        quantity=quantity,
                        entry_price=opportunity.entry_price,
                        stop_loss_price=opportunity.stop_loss,
                        profit_target_price=opportunity.target_1,
                        trade_type=trade_type_map.get(opportunity.horizon, "SWING"),
                        entry_reason=entry_reason,
                        entry_score=opportunity.overall_score,
                        indicators_snapshot=indicators_snapshot,
                        confluence_factors=confluence_factors,
                        entry_time=datetime.now(),
                    )
                    db.add(new_position)
                    db.commit()
                finally:
                    db.close()

                self.last_trade_time = datetime.now()
                self.trades_today += 1

                # Log success
                self.execution_logger.log_success(
                    symbol=symbol,
                    asset_class="stock",
                    side=side,
                    quantity=quantity,
                    price=opportunity.entry_price,
                    order_type="market",
                    order_id=result["id"],
                    filled_quantity=result.get("filled_qty", quantity),
                    filled_price=result.get("filled_avg_price", opportunity.entry_price),
                )

                return result

        except Exception as e:
            logger.error(f"[Hierarchical] Error executing entry for {symbol}: {e}")
            error_code, error_msg = parse_api_error(str(e))
            self.execution_logger.log_failure(
                symbol=symbol,
                asset_class="stock",
                side=side,
                quantity=quantity,
                price=opportunity.entry_price,
                order_type="market",
                error_code=error_code,
                error_message=error_msg,
            )
            return None

    async def _run_trading_cycle(self, extended_hours: bool = False):
        """
        Run one trading cycle - analyze, decide, execute.

        Args:
            extended_hours: If True, use limit orders for extended hours trading
        """
        # If hierarchical mode is enabled, use the smart scanner
        if self.hierarchical_mode_enabled:
            await self._run_hierarchical_trading_cycle(extended_hours)
            return

        self.current_cycle = "analyzing"
        logger.debug(f"Running trading cycle (extended_hours={extended_hours})...")

        try:
            # Get account info
            account = await self.alpaca.get_account()
            equity = account["equity"]
            buying_power = account["buying_power"]

            # Get current positions
            positions = await self.alpaca.get_positions()
            self._positions_cache = {p["symbol"]: p for p in positions}

            # Check existing positions for exits
            self.current_cycle = "checking_exits"
            await self._check_exit_signals(positions)

            # Periodically discover new stocks using AI (every 4 hours)
            if self.use_ai_discovery and self.ai_advisor.enabled:
                await self._ai_discover_stocks()

            # REFRESH STOCKS FROM WATCHLIST before each scan
            # This allows users to add stocks to watchlist and have them scanned immediately
            await self._refresh_symbols_from_watchlist()

            # Initialize stock scan tracking
            symbols_to_scan = [s for s in self.enabled_symbols if s not in self._positions_cache]
            self._stock_scan_progress = {
                "total": len(symbols_to_scan),
                "scanned": 0,
                "current_symbol": None,
                "signals_found": 0,
                "best_opportunity": None,
                "scan_status": "scanning",
                "scan_summary": f"Starting scan of {len(symbols_to_scan)} stocks...",
                "last_scan_completed": None,
                "next_scan_in_seconds": self.cycle_interval_seconds,
                "market_status": "regular" if not extended_hours else "extended",
            }

            # Track best opportunity even if below threshold
            best_buy_signal = None
            best_buy_confidence = 0.0
            signals_above_threshold = 0

            # Analyze symbols for entry signals
            self.current_cycle = "scanning_entries"
            for idx, symbol in enumerate(symbols_to_scan):
                # Update scan progress
                self._stock_scan_progress["current_symbol"] = symbol
                self._stock_scan_progress["scanned"] = idx + 1
                self._stock_scan_progress["scan_summary"] = f"Analyzing {symbol}... ({idx + 1}/{len(symbols_to_scan)})"

                # Skip if already have position
                if symbol in self._positions_cache:
                    continue

                # Analyze symbol
                signal = await self._analyze_symbol(symbol)

                # Store analysis results for UI display (like crypto) - store ALL results
                if signal:
                    signal_type = signal.signal_type.value if signal.signal_type else "NEUTRAL"
                    confidence = signal.score
                    meets_threshold = signal.signal_type == SignalType.BUY and signal.score >= self.strategy.entry_threshold

                    self._stock_analysis_results[symbol] = {
                        "signal": signal_type,
                        "confidence": confidence,
                        "threshold": self.strategy.entry_threshold,
                        "meets_threshold": meets_threshold,
                        "reason": self._get_analysis_reason(
                            signal_type,
                            confidence,
                            self.strategy.entry_threshold
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "indicators": signal.indicators if hasattr(signal, 'indicators') else {},
                        "current_price": signal.current_price,
                        "trade_type": signal.trade_type.value if signal.trade_type else None,
                    }
                    self._last_stock_analysis_time = datetime.now()

                    # Log stock analysis like crypto does
                    logger.info(f"Stock analysis for {symbol}: signal={signal_type}, confidence={confidence:.1f}, threshold={self.strategy.entry_threshold}")
                else:
                    # Store NO_DATA result for visibility
                    self._stock_analysis_results[symbol] = {
                        "signal": "NO_DATA",
                        "confidence": 0,
                        "threshold": self.strategy.entry_threshold,
                        "meets_threshold": False,
                        "reason": "Insufficient historical data (need 50+ days)",
                        "timestamp": datetime.now().isoformat(),
                        "indicators": {},
                        "current_price": None,
                        "trade_type": None,
                    }
                    self._last_stock_analysis_time = datetime.now()
                    # Debug log moved to _analyze_symbol for actual bar count

                # Track best opportunity
                if signal and signal.signal_type == SignalType.BUY:
                    if signal.score > best_buy_confidence:
                        best_buy_confidence = signal.score
                        best_buy_signal = {
                            "symbol": symbol,
                            "confidence": signal.score,
                            "threshold": self.strategy.entry_threshold,
                            "meets_threshold": signal.score >= self.strategy.entry_threshold,
                        }

                if signal and signal.signal_type == SignalType.BUY:
                    # Track that we found a signal above threshold
                    if signal.score >= self.strategy.entry_threshold:
                        signals_above_threshold += 1
                        self._stock_scan_progress["signals_found"] = signals_above_threshold

                    # Check if we can take the trade
                    position_size = self.risk_manager.calculate_position_size(
                        account_equity=equity,
                        entry_price=signal.current_price,
                        stop_loss_price=signal.suggested_stop_loss,
                        current_positions=len(positions),
                    )

                    if position_size.shares > 0:
                        risk_check = self.risk_manager.can_open_position(
                            account_equity=equity,
                            buying_power=buying_power,
                            current_positions=positions,
                            entry_price=signal.current_price,
                            position_value=position_size.position_value,
                        )

                        if risk_check.can_trade:
                            # === AI EVALUATION FOR ALL SIGNALS (for transparency) ===
                            # Always run AI evaluation so users can see why trades pass/fail
                            ai_decision = None
                            logger.info(f"AI Evaluating {symbol} stock trade (auto_trade_mode={self.auto_trade_mode})...")

                            # Get existing positions for portfolio context
                            existing_symbols = list(self._positions_cache.keys())

                            # Build signal data for AI
                            signal_data = {
                                "signal_type": signal.signal_type.value,
                                "score": signal.score,
                                "trade_type": signal.trade_type.value,
                                "suggested_stop_loss": signal.suggested_stop_loss,
                                "suggested_profit_target": signal.suggested_profit_target,
                                "indicators": signal.indicators,
                            }

                            # Ask AI to evaluate the trade
                            try:
                                ai_decision = await self.ai_advisor.evaluate_stock_trade(
                                    symbol=symbol,
                                    signal_data=signal_data,
                                    current_price=signal.current_price,
                                    account_info={
                                        "equity": equity,
                                        "buying_power": buying_power,
                                        "positions": len(positions),
                                        "max_positions": self.risk_manager.max_positions,
                                    },
                                    existing_positions=existing_symbols,
                                )
                            except Exception as e:
                                logger.warning(f"AI evaluation failed for {symbol}: {e}")
                                ai_decision = {
                                    "decision": "WAIT",
                                    "confidence": 0,
                                    "reasoning": f"AI evaluation unavailable: {str(e)[:50]}",
                                    "concerns": ["AI service error"],
                                }

                            # Log AI decision
                            self._log_ai_decision(symbol, ai_decision, signal_data)

                            # UPDATE STOCK ANALYSIS RESULTS WITH AI DECISION
                            # This fixes the disconnect between scanner confidence and AI decision
                            if symbol in self._stock_analysis_results:
                                self._stock_analysis_results[symbol]["ai_decision"] = {
                                    "decision": ai_decision.get("decision"),
                                    "confidence": ai_decision.get("confidence", 0),
                                    "reasoning": ai_decision.get("reasoning", ""),
                                    "concerns": ai_decision.get("concerns", []),
                                    "timestamp": datetime.now().isoformat(),
                                    "symbol": symbol,
                                    "ai_generated": True,
                                    "model": ai_decision.get("model", "gpt-4"),
                                    "technical_score": ai_decision.get("technical_score", signal.score),
                                    "technical_signal": signal.signal_type.value,
                                }
                                # If AI rejects, update the signal to reflect reality
                                if ai_decision.get("decision") != "APPROVE":
                                    self._stock_analysis_results[symbol]["signal"] = "HOLD"
                                    self._stock_analysis_results[symbol]["meets_threshold"] = False
                                    self._stock_analysis_results[symbol]["reason"] = f"AI {ai_decision.get('decision')}: {ai_decision.get('reasoning', '')[:50]}"

                            # If AI rejects or says wait, skip this stock
                            if ai_decision.get("decision") != "APPROVE":
                                logger.info(
                                    f"AI {ai_decision.get('decision', 'REJECTED')} trade for {symbol}: "
                                    f"{ai_decision.get('reasoning', 'No reason provided')}"
                                )
                                # Log to execution log for Activity tab visibility
                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type=f"AI_{ai_decision.get('decision', 'REJECTED')}",
                                    executed=False,
                                    reason=ai_decision.get('reasoning', 'No reason provided')[:100],
                                    details={
                                        "score": signal.score,
                                        "ai_decision": ai_decision.get("decision"),
                                        "confidence": ai_decision.get("confidence", 0),
                                        "concerns": ai_decision.get("concerns", [])[:3],
                                    }
                                )
                                continue

                            logger.info(
                                f"AI APPROVED trade for {symbol}: {ai_decision.get('reasoning', '')}"
                            )

                            # ONLY EXECUTE IF AUTO_TRADE_MODE IS ON
                            if not self.auto_trade_mode:
                                logger.info(f"Auto trade mode OFF - Signal approved for {symbol} but not executing")
                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type="ENTRY_SKIPPED",
                                    executed=False,
                                    reason="Auto trade mode is OFF - manual execution required",
                                    details={"score": signal.score, "ai_decision": ai_decision.get("decision")}
                                )
                                continue

                            await self._execute_entry(symbol, signal, position_size.shares, extended_hours)
                            # Update positions list
                            positions = await self.alpaca.get_positions()

                            # Update scan status to found
                            self._stock_scan_progress["scan_status"] = "found_opportunity"
                            self._stock_scan_progress["scan_summary"] = (
                                f"Entered position: {symbol} at {signal.score:.0f}% confidence"
                            )
                        else:
                            logger.debug(f"Skipping {symbol}: {risk_check.reason}")
                            # Log to execution log for debugging
                            self._log_execution_event(
                                symbol=symbol,
                                event_type="ENTRY_SKIPPED",
                                executed=False,
                                reason=risk_check.reason,
                                details={"score": signal.score, "signal": signal.signal_type.value}
                            )

            # Finalize stock scan tracking
            self._stock_scan_progress["scanned"] = len(symbols_to_scan)
            self._stock_scan_progress["current_symbol"] = None
            self._stock_scan_progress["best_opportunity"] = best_buy_signal
            self._stock_scan_progress["last_scan_completed"] = datetime.now().isoformat()
            self._total_scans_today += 1

            # Set final scan status and summary
            if self._stock_scan_progress["scan_status"] != "found_opportunity":
                if signals_above_threshold > 0:
                    self._stock_scan_progress["scan_status"] = "found_opportunity"
                    self._stock_scan_progress["scan_summary"] = f"Found {signals_above_threshold} signal(s) above threshold"
                elif best_buy_signal:
                    self._stock_scan_progress["scan_status"] = "exhausted"
                    gap = best_buy_signal["threshold"] - best_buy_signal["confidence"]
                    self._stock_scan_progress["scan_summary"] = (
                        f"Scanned {len(symbols_to_scan)} stocks - no signals above {self.strategy.entry_threshold:.0f}% threshold. "
                        f"Best: {best_buy_signal['symbol']} at {best_buy_signal['confidence']:.0f}% ({gap:.0f}% below threshold)"
                    )
                else:
                    self._stock_scan_progress["scan_status"] = "exhausted"
                    self._stock_scan_progress["scan_summary"] = (
                        f"Scanned {len(symbols_to_scan)} stocks - no buy signals found. Waiting for next cycle..."
                    )

            logger.info(f"Stock scan complete: {self._stock_scan_progress['scan_summary']}")
            self.current_cycle = "cycle_complete"

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            raise

    async def _refresh_symbols_from_watchlist(self):
        """
        Refresh stock symbols from the user's watchlist.
        This allows users to add/remove stocks from watchlist and have them
        automatically included in the next scan cycle.
        """
        try:
            db = SessionLocal()

            # Get ALL stocks from watchlist (not just auto_trade=True)
            # This makes the scanner follow the watchlist completely
            from database.models import UserWatchlist
            watchlist_stocks = db.query(UserWatchlist).all()
            raw_symbols = [s.symbol for s in watchlist_stocks if s.symbol]

            # Validate and filter watchlist symbols
            validated_symbols = self._validate_and_filter_symbols(raw_symbols, allow_crypto=False)

            if validated_symbols:
                # Use validated watchlist as the primary source
                self.enabled_symbols = validated_symbols
                logger.info(f"Refreshed stock symbols from watchlist: {len(self.enabled_symbols)} validated stocks")
            else:
                # Fallback to defaults if watchlist is empty or all invalid
                if not self.enabled_symbols:
                    self.enabled_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
                logger.info(f"Watchlist empty/invalid, using defaults: {self.enabled_symbols}")

            db.close()
        except Exception as e:
            logger.warning(f"Could not refresh from watchlist: {e}")
            # Keep existing symbols on error

    async def _ai_discover_stocks(self):
        """Use AI to discover promising stocks to trade"""
        # Only run discovery every 4 hours
        discovery_interval = timedelta(hours=4)
        if self.last_discovery_time and (datetime.now() - self.last_discovery_time) < discovery_interval:
            return

        logger.info("Running AI stock discovery...")
        self.current_cycle = "ai_discovery"

        try:
            # Get market sentiment first
            sentiment = await self.ai_advisor.get_market_sentiment()
            market_conditions = sentiment.get("sentiment", "neutral")

            # Discover stocks based on market conditions
            risk_tolerance = "moderate"  # Could be configurable
            discovered = await self.ai_advisor.discover_stocks(
                market_conditions=market_conditions,
                risk_tolerance=risk_tolerance,
            )

            if discovered:
                # Extract and validate symbols from discovered stocks
                new_symbols = []
                for s in discovered:
                    if "symbol" in s:
                        normalized, is_valid, error_msg = self._normalize_and_validate_symbol(s["symbol"], allow_crypto=False)
                        if is_valid:
                            new_symbols.append(normalized)
                        else:
                            logger.warning(f"[AI_DISCOVERY] Skipping invalid symbol '{s['symbol']}': {error_msg}")

                # Merge with existing symbols (keep unique)
                existing = set(self.enabled_symbols)
                for symbol in new_symbols:
                    if symbol not in existing:
                        self.enabled_symbols.append(symbol)
                        existing.add(symbol)

                # Limit to 15 symbols max to manage API calls
                if len(self.enabled_symbols) > 15:
                    self.enabled_symbols = self.enabled_symbols[:15]

                logger.info(f"AI discovered stocks. Now tracking: {self.enabled_symbols}")

                # Update database config
                await self._save_discovered_symbols()

            self.last_discovery_time = datetime.now()

        except Exception as e:
            logger.error(f"AI stock discovery failed: {e}")

    async def _save_discovered_symbols(self):
        """Save discovered symbols to database"""
        try:
            db = SessionLocal()
            config = db.query(BotConfiguration).filter(BotConfiguration.is_active == True).first()
            if config:
                config.enabled_symbols = self.enabled_symbols
                db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"Could not save discovered symbols: {e}")

    async def _analyze_symbol(self, symbol: str):
        """Analyze a symbol and generate trading signal"""
        # Validate and normalize symbol first
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol, allow_crypto=False)
        if not is_valid:
            logger.warning(f"[ANALYZE] Invalid symbol '{symbol}': {error_msg}")
            self.execution_logger.log_failure(
                symbol=symbol,
                asset_class="stock",
                side="buy",
                quantity=0,
                price=None,
                order_type="analysis",
                error_code=ExecutionErrorCode.INVALID_SYMBOL,
                error_message=error_msg,
            )
            return None
        symbol = normalized_symbol

        try:
            # Get historical bars
            logger.info(f"[ANALYZE] Fetching bars for {symbol}...")
            bars = await self.alpaca.get_bars(symbol, timeframe="1day", limit=200)
            logger.info(f"[ANALYZE] Got {len(bars)} bars for {symbol}")

            if len(bars) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(bars)} bars (need 50+)")
                return None

            # Extract OHLCV data
            prices = [b["close"] for b in bars]
            highs = [b["high"] for b in bars]
            lows = [b["low"] for b in bars]
            volumes = [b["volume"] for b in bars]

            # Generate signal
            signal = self.strategy.analyze(symbol, prices, highs, lows, volumes)

            logger.debug(
                f"{symbol}: score={signal.score:.1f}, signal={signal.signal_type.value}, "
                f"type={signal.trade_type.value}"
            )

            return signal

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

    async def _check_exit_signals(self, positions: List[Dict]):
        """Check existing positions for exit signals including trailing stops and partial profits"""
        for pos in positions:
            symbol = pos["symbol"]

            try:
                # Get our tracked position data from database
                db = SessionLocal()
                db_position = db.query(Position).filter(Position.symbol == symbol).first()

                if not db_position:
                    db.close()
                    logger.warning(f"Position {symbol} not in database, skipping exit check")
                    continue

                # Get recent bars
                bars = await self.alpaca.get_bars(symbol, timeframe="1day", limit=100)

                if len(bars) < 20:
                    db.close()
                    continue

                prices = [b["close"] for b in bars]
                highs = [b["high"] for b in bars]
                lows = [b["low"] for b in bars]
                volumes = [b["volume"] for b in bars]

                entry_price = db_position.entry_price
                current_price = pos["current_price"]
                current_pnl_pct = (current_price - entry_price) / entry_price

                # Check for partial profit taking first
                if (self.partial_profit_enabled and
                    current_pnl_pct >= self.partial_profit_at and
                    symbol not in self._partial_sold):

                    partial_qty = int(pos["quantity"] * self.partial_profit_pct)
                    if partial_qty > 0:
                        logger.info(f"Taking partial profit on {symbol}: {partial_qty} shares at {current_pnl_pct*100:.1f}% profit")
                        await self._execute_partial_exit(symbol, partial_qty, "PARTIAL_PROFIT")
                        self._partial_sold[symbol] = True
                        db.close()
                        continue

                # Check trailing stop logic
                current_stop = db_position.stop_loss_price or entry_price * 0.95

                if self.trailing_stop_enabled:
                    # Activate trailing stop when profit threshold is reached
                    if current_pnl_pct >= self.trailing_stop_activation_pct:
                        new_stop = self.risk_manager.calculate_trailing_stop(
                            entry_price=entry_price,
                            current_price=current_price,
                            current_stop=current_stop,
                            trailing_pct=self.trailing_stop_pct,
                        )

                        if new_stop > current_stop:
                            # Update stop loss in database
                            db_position.stop_loss_price = new_stop
                            db_position.trailing_stop_pct = self.trailing_stop_pct
                            db.commit()
                            current_stop = new_stop
                            logger.info(f"Trailing stop updated for {symbol}: ${new_stop:.2f}")

                # Check if trailing stop is hit
                if current_price <= current_stop:
                    db.close()
                    await self._execute_exit(symbol, pos["quantity"], "TRAILING_STOP")
                    # Clean up partial sold tracking
                    self._partial_sold.pop(symbol, None)
                    continue

                db.close()

                # Calculate days held
                entry_time = db_position.entry_time
                days_held = (datetime.now() - entry_time).days

                # Check standard exit conditions
                should_exit, exit_reason = self.strategy.should_exit(
                    symbol=symbol,
                    entry_price=entry_price,
                    current_price=current_price,
                    stop_loss=current_stop,
                    profit_target=db_position.profit_target_price or entry_price * 1.10,
                    trade_type=TradeType(db_position.trade_type) if db_position.trade_type else TradeType.SWING,
                    entry_time_days=days_held,
                    prices=prices,
                    highs=highs,
                    lows=lows,
                    volumes=volumes,
                )

                if should_exit:
                    await self._execute_exit(symbol, pos["quantity"], exit_reason)
                    # Clean up partial sold tracking
                    self._partial_sold.pop(symbol, None)

            except Exception as e:
                logger.error(f"Error checking exit for {symbol}: {e}")

    async def _execute_entry(self, symbol: str, signal, shares: int, extended_hours: bool = False):
        """
        Execute entry trade.

        Args:
            symbol: Stock symbol
            signal: Trading signal
            shares: Number of shares
            extended_hours: If True, use limit order for extended hours
        """
        # Validate and normalize symbol
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol, allow_crypto=False)
        if not is_valid:
            logger.warning(f"[ENTRY] Invalid symbol '{symbol}': {error_msg}")
            self.execution_logger.log_failure(
                symbol=symbol,
                asset_class="stock",
                side="buy",
                quantity=shares,
                price=getattr(signal, 'current_price', None),
                order_type="market" if not extended_hours else "limit",
                error_code=ExecutionErrorCode.INVALID_SYMBOL,
                error_message=error_msg,
            )
            raise ValueError(f"Invalid symbol: {error_msg}")
        symbol = normalized_symbol

        try:
            order_type = "limit (extended)" if extended_hours else "market"
            logger.info(
                f"ENTRY: {symbol} - {shares} shares @ ~${signal.current_price:.2f} "
                f"(score={signal.score:.1f}, type={signal.trade_type.value}, order={order_type})"
            )

            # Log entry attempt
            self._log_execution_event(
                symbol=symbol,
                event_type="STOCK_ENTRY_ATTEMPT",
                executed=False,
                reason=f"Attempting to buy {shares} shares @ ${signal.current_price:.2f}",
                details={
                    "shares": shares,
                    "price": signal.current_price,
                    "score": signal.score,
                    "trade_type": signal.trade_type.value,
                    "order_type": order_type,
                    "extended_hours": extended_hours,
                }
            )

            # Submit order based on session
            if extended_hours:
                # Extended hours require limit orders
                # Use current price with small buffer for limit
                limit_price = round(signal.current_price * (1 + self.trading_config.limit_order_offset_pct), 2)
                order = await self.alpaca.submit_extended_hours_order(
                    symbol=symbol,
                    quantity=shares,
                    side="buy",
                    limit_price=limit_price,
                )
            else:
                # Regular hours - use market order
                order = await self.alpaca.submit_market_order(
                    symbol=symbol,
                    quantity=shares,
                    side="buy",
                    time_in_force="day"
                )

            # Wait for fill (with timeout)
            filled_price = signal.current_price
            for _ in range(10):
                await asyncio.sleep(1)
                order_status = await self.alpaca.get_order(order["id"])
                if order_status and order_status["status"] == "filled":
                    filled_price = order_status["filled_avg_price"] or filled_price
                    break

            # Record in database
            db = SessionLocal()
            try:
                # Create trade record
                trade = Trade(
                    symbol=symbol,
                    side="BUY",
                    quantity=shares,
                    entry_price=filled_price,
                    entry_time=datetime.now(),
                    entry_order_id=order["id"],
                    strategy_name="default",
                    trade_type=signal.trade_type.value,
                    entry_score=signal.score,
                    indicators_snapshot=signal.indicators,
                )
                db.add(trade)

                # Build entry reason from signal
                entry_reason = self._build_signal_entry_reason(signal, filled_price)

                # Build indicators snapshot if available
                indicators_snapshot = None
                if signal.indicators:
                    indicators_snapshot = {
                        "raw": signal.indicators,
                        "score": signal.score,
                        "trade_type": signal.trade_type.value if signal.trade_type else "SWING",
                    }

                # Build confluence factors
                confluence_factors = None
                if signal.confluence_factors:
                    confluence_factors = {
                        "confirming": signal.confluence_factors,
                        "signal_type": signal.signal_type.value if signal.signal_type else "UNKNOWN",
                    }

                # Create position record
                position = Position(
                    symbol=symbol,
                    quantity=shares,
                    entry_price=filled_price,
                    entry_time=datetime.now(),
                    stop_loss_price=signal.suggested_stop_loss,
                    profit_target_price=signal.suggested_profit_target,
                    trade_type=signal.trade_type.value,
                    strategy_name="default",
                    entry_score=signal.score,
                    entry_reason=entry_reason,
                    indicators_snapshot=indicators_snapshot,
                    confluence_factors=confluence_factors,
                )
                db.add(position)
                db.commit()
            finally:
                db.close()

            self.last_trade_time = datetime.now()
            logger.info(f"Entry executed: {symbol} {shares} shares @ ${filled_price:.2f}")

            # Log successful execution
            self._log_execution_event(
                symbol=symbol,
                event_type="STOCK_ENTRY_SUCCESS",
                executed=True,
                reason=f"Bought {shares} shares @ ${filled_price:.2f}",
                details={
                    "order_id": order["id"],
                    "filled_price": filled_price,
                    "shares": shares,
                    "score": signal.score,
                }
            )

            # Submit stop-loss order
            await self.alpaca.submit_stop_loss_order(
                symbol=symbol,
                quantity=shares,
                stop_price=signal.suggested_stop_loss,
            )

        except Exception as e:
            logger.error(f"Failed to execute entry for {symbol}: {e}")
            # Log the failure
            self._log_execution_event(
                symbol=symbol,
                event_type="STOCK_ENTRY_FAILED",
                executed=False,
                reason=f"Order failed: {str(e)}",
                details={
                    "error": str(e),
                    "shares": shares,
                    "price": signal.current_price if signal else 0,
                }
            )
            raise

    async def _execute_partial_exit(self, symbol: str, quantity: int, reason: str):
        """Execute partial exit trade (for partial profit taking)"""
        # Validate and normalize symbol
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol, allow_crypto=False)
        if not is_valid:
            logger.warning(f"[PARTIAL_EXIT] Invalid symbol '{symbol}': {error_msg}")
            self.execution_logger.log_failure(
                symbol=symbol,
                asset_class="stock",
                side="sell",
                quantity=quantity,
                price=None,
                order_type="market",
                error_code=ExecutionErrorCode.INVALID_SYMBOL,
                error_message=error_msg,
            )
            raise ValueError(f"Invalid symbol: {error_msg}")
        symbol = normalized_symbol

        try:
            logger.info(f"PARTIAL EXIT: {symbol} - {quantity} shares (reason: {reason})")

            # Submit partial sell order
            order = await self.alpaca.submit_market_order(
                symbol=symbol,
                quantity=quantity,
                side="sell",
                time_in_force="day"
            )

            # Wait for fill
            exit_price = None
            for _ in range(10):
                await asyncio.sleep(1)
                order_status = await self.alpaca.get_order(order["id"])
                if order_status and order_status["status"] == "filled":
                    exit_price = order_status["filled_avg_price"]
                    break

            # Update database - reduce position quantity
            db = SessionLocal()
            try:
                position = db.query(Position).filter(Position.symbol == symbol).first()
                if position:
                    position.quantity -= quantity

                # Record partial trade
                trade = Trade(
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    entry_price=position.entry_price if position else 0,
                    entry_time=position.entry_time if position else datetime.now(),
                    exit_price=exit_price,
                    exit_time=datetime.now(),
                    exit_order_id=order["id"],
                    exit_reason=reason,
                    profit_loss=(exit_price - position.entry_price) * quantity if position and exit_price else 0,
                    profit_loss_pct=(exit_price - position.entry_price) / position.entry_price if position and exit_price else 0,
                    strategy_name="default",
                    trade_type="PARTIAL",
                )
                db.add(trade)
                db.commit()

                # Record P&L for risk manager
                if trade.profit_loss:
                    self.risk_manager.record_trade_pnl(trade.profit_loss)

            finally:
                db.close()

            self.last_trade_time = datetime.now()
            logger.info(f"Partial exit executed: {symbol} {quantity} shares @ ${exit_price:.2f if exit_price else 'N/A'} ({reason})")

        except Exception as e:
            logger.error(f"Failed to execute partial exit for {symbol}: {e}")
            raise

    async def _execute_queued_trades(self):
        """
        Execute trades that were queued while market was closed.
        Called when market session transitions to 'regular'.
        """
        if not self._queued_trades:
            return

        logger.info(f"🚀 Market opened! Executing {len(self._queued_trades)} queued trades...")

        executed = []
        failed = []

        for trade in self._queued_trades[:]:  # Copy list since we're modifying it
            symbol = trade["symbol"]
            signal = trade["signal"]
            confidence = trade["confidence"]

            try:
                # Get current price
                quote = await self.alpaca.get_quote(symbol)
                current_price = quote.get("price", 0)

                if current_price <= 0:
                    failed.append({"symbol": symbol, "error": "Could not get price"})
                    continue

                # Get account info for position sizing
                account = await self.alpaca.get_account()
                buying_power = float(account.get("buying_power", 0))

                # Use 5% of buying power per queued trade
                position_value = buying_power * 0.05
                quantity = int(position_value / current_price)

                if quantity < 1:
                    # Try fractional
                    quantity = round(position_value / current_price, 4)

                if quantity <= 0 or position_value < self.trading_config.min_position_value_crypto:
                    failed.append({"symbol": symbol, "error": "Position size too small"})
                    continue

                if signal.upper() == "BUY":
                    order = await self.alpaca.submit_market_order(
                        symbol=symbol,
                        quantity=quantity,
                        side="buy",
                        time_in_force="day",
                    )

                    executed.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "price": current_price,
                        "order_id": order.get("id"),
                    })

                    self._log_execution_event(
                        symbol=symbol,
                        event_type="QUEUED_TRADE_EXECUTED",
                        executed=True,
                        reason=f"Queued trade executed at market open (Confidence: {confidence}%)",
                        details={
                            "quantity": quantity,
                            "price": current_price,
                            "queued_reason": trade.get("reason", ""),
                        }
                    )

                    logger.info(f"✅ Executed queued trade: {symbol} {quantity} shares @ ${current_price:.2f}")

                # Mark as executed
                trade["status"] = "EXECUTED"

            except Exception as e:
                failed.append({"symbol": symbol, "error": str(e)})
                trade["status"] = "FAILED"
                trade["error"] = str(e)
                logger.error(f"❌ Failed to execute queued trade for {symbol}: {e}")

        # Remove executed/failed trades from queue
        self._queued_trades = [t for t in self._queued_trades if t.get("status") == "PENDING"]

        logger.info(f"Queued trades complete: {len(executed)} executed, {len(failed)} failed")
        return {"executed": executed, "failed": failed}

    def queue_trade(self, symbol: str, signal: str, confidence: float, reason: str = ""):
        """
        Add a trade to the queue for market open.

        Args:
            symbol: Stock symbol to trade
            signal: Trade signal (BUY/SELL)
            confidence: Signal confidence score
            reason: Reason for queueing
        """
        # Validate and normalize symbol
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol)
        if not is_valid:
            logger.warning(f"[QUEUE] Invalid symbol '{symbol}': {error_msg}")
            return False
        symbol = normalized_symbol

        # Check if already queued
        existing = [t for t in self._queued_trades if t["symbol"] == symbol]
        if existing:
            logger.debug(f"{symbol} already queued")
            return False

        trade = {
            "symbol": symbol,
            "signal": signal.upper(),
            "confidence": confidence,
            "reason": reason or f"Strong {signal} signal detected while market closed",
            "queued_at": datetime.now().isoformat(),
            "status": "PENDING",
        }
        self._queued_trades.append(trade)

        logger.info(f"📋 Queued {signal} trade for {symbol} at market open (Confidence: {confidence}%)")
        return True

    async def _execute_exit(self, symbol: str, quantity: float, reason: str):
        """Execute exit trade"""
        # Validate and normalize symbol
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol)
        if not is_valid:
            logger.warning(f"[EXIT] Invalid symbol '{symbol}': {error_msg}")
            self.execution_logger.log_failure(
                symbol=symbol,
                asset_class="stock",
                side="sell",
                quantity=quantity,
                price=None,
                order_type="market",
                error_code=ExecutionErrorCode.INVALID_SYMBOL,
                error_message=error_msg,
            )
            raise ValueError(f"Invalid symbol: {error_msg}")
        symbol = normalized_symbol

        try:
            logger.info(f"EXIT: {symbol} - {quantity} shares (reason: {reason})")

            # Close position
            order = await self.alpaca.close_position(symbol)

            # Wait for fill
            exit_price = None
            for _ in range(10):
                await asyncio.sleep(1)
                order_status = await self.alpaca.get_order(order["id"])
                if order_status and order_status["status"] == "filled":
                    exit_price = order_status["filled_avg_price"]
                    break

            # Update database
            db = SessionLocal()
            try:
                # Find the open trade
                trade = db.query(Trade).filter(
                    Trade.symbol == symbol,
                    Trade.exit_time == None
                ).first()

                if trade:
                    trade.exit_price = exit_price or trade.entry_price
                    trade.exit_time = datetime.now()
                    trade.exit_order_id = order["id"]
                    trade.exit_reason = reason
                    trade.profit_loss = (trade.exit_price - trade.entry_price) * trade.quantity
                    trade.profit_loss_pct = (trade.exit_price - trade.entry_price) / trade.entry_price

                    # Record P&L for risk manager
                    self.risk_manager.record_trade_pnl(trade.profit_loss)

                # Remove position record
                position = db.query(Position).filter(Position.symbol == symbol).first()
                if position:
                    db.delete(position)

                db.commit()
            finally:
                db.close()

            self.last_trade_time = datetime.now()
            logger.info(f"Exit executed: {symbol} @ ${exit_price:.2f if exit_price else 'N/A'} ({reason})")

        except Exception as e:
            logger.error(f"Failed to execute exit for {symbol}: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status with detailed information"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = int((datetime.now() - self.start_time).total_seconds())

        # Format uptime nicely
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        return {
            "state": self.state.value,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": uptime_str,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "current_cycle": self.current_cycle,
            "current_session": self.current_session,
            "error_message": self.error_message,
            "paper_trading": self.paper_trading,
            "allow_extended_hours": self.allow_extended_hours,
            "active_symbols": self.enabled_symbols,
            "user_symbols": self.user_symbols,
            "ready_stocks": self._ready_stocks,  # Stocks ready for entry
            "ai_enabled": self.ai_advisor.enabled,
            "last_discovery_time": self.last_discovery_time.isoformat() if self.last_discovery_time else None,
            # Exit strategy settings
            "trailing_stop_enabled": self.trailing_stop_enabled,
            "trailing_stop_pct": self.trailing_stop_pct,
            "partial_profit_enabled": self.partial_profit_enabled,
            "partial_profit_pct": self.partial_profit_pct,
            # Profit reinvestment
            "reinvest_profits": self.reinvest_profits,
            "compounding_enabled": self.compounding_enabled,
            # Intraday
            "intraday_enabled": self.intraday_enabled,
            "intraday_timeframe": self.intraday_timeframe,
            "trades_today": self.trades_today,
            "max_trades_per_day": self.max_trades_per_day,
            # Auto trade
            "auto_trade_mode": self.auto_trade_mode,
            "ai_risk_tolerance": self.ai_risk_tolerance,
            # Crypto trading
            "crypto_trading_enabled": self.crypto_trading_enabled,
            "crypto_symbols": self.crypto_symbols,
            "crypto_max_positions": self.crypto_max_positions,
            "crypto_positions": len(self._crypto_positions),
            "crypto_analysis_results": self._crypto_analysis_results,
            "last_crypto_analysis_time": self._last_crypto_analysis_time.isoformat() if self._last_crypto_analysis_time else None,
            # Crypto scan progress tracking
            "crypto_scan_progress": self._crypto_scan_progress,
            # Stock scan progress tracking
            "stock_scan_progress": self._stock_scan_progress,
            # Stock analysis results (similar to crypto)
            "stock_analysis_results": self._stock_analysis_results,
            "last_stock_analysis_time": self._last_stock_analysis_time.isoformat() if self._last_stock_analysis_time else None,
            # Entry threshold (important for understanding why signals aren't traded)
            "entry_threshold": self.strategy.entry_threshold,
            # Asset Class Mode
            "asset_class_mode": self.asset_class_mode,
            # 24/7 Mode
            "auto_247_mode": self.auto_247_mode,
            "crypto_only_after_hours": self.crypto_only_after_hours,
            "aggressive_crypto_after_hours": self.aggressive_crypto_after_hours,
            "is_247_crypto_active": (
                self.crypto_trading_enabled and
                self.current_session in ["overnight", "weekend", "after_hours"] and
                self.aggressive_crypto_after_hours
            ),
            # AI Decision Tracking
            "last_ai_decision": self._last_ai_decision,
            "ai_decisions_history": self._ai_decisions[-10:],  # Last 10 decisions for UI
            # Execution Log (legacy)
            "execution_log": self._execution_log[-20:],  # Last 20 execution events
            # Enhanced Execution Logger (new)
            "execution_error_summary": self.execution_logger.get_error_summary(),
            "execution_recent_failures": self.execution_logger.get_failed_attempts(limit=10),
            # Tactical Controls
            "new_entries_paused": self.new_entries_paused,
            "strategy_override": self.strategy_override,
            # Scan Statistics
            "total_scans_today": self._total_scans_today,
            # Priority Tier Summary
            "priority_tier_summary": self.priority_scanner.get_tier_summary(),
            # Queued trades for market open
            "queued_trades": self._queued_trades,
            "queued_trades_count": len(self._queued_trades),
            "auto_queue_strong_signals": self.auto_queue_strong_signals,
        }

    def _get_analysis_reason(self, signal: str, confidence: float, threshold: float) -> str:
        """Get a human-readable reason for the analysis result"""
        if signal == "BUY":
            if confidence >= threshold:
                return f"Strong buy signal ({confidence:.0f}% confidence)"
            else:
                return f"Weak buy signal ({confidence:.0f}% < {threshold:.0f}% threshold)"
        elif signal == "SELL":
            return f"Sell signal detected ({confidence:.0f}% confidence)"
        elif signal == "NEUTRAL":
            return f"No clear direction ({confidence:.0f}% confidence)"
        else:
            return f"Waiting for signal ({signal})"

    def _build_entry_reason(self, opportunity) -> str:
        """
        Build a detailed human-readable entry reason explaining:
        - Why we entered this position
        - What the trade plan is (targets, stop loss)
        - Key confluence factors

        Args:
            opportunity: TradingOpportunity object with all trade details

        Returns:
            A formatted string explaining the trade rationale
        """
        # Build horizon description
        horizon_desc = {
            "LONG": "Long-term hold (10+ days, targeting 15-30% gain)",
            "SWING": "Swing trade (2-10 days, targeting 5-15% gain)",
            "INTRADAY": "Intraday trade (1-8 hours, targeting 1-3% gain)",
            "SCALP": "Scalp trade (5-60 min, targeting 0.3-1% gain)",
        }
        horizon_text = horizon_desc.get(opportunity.horizon.value, opportunity.horizon.value)

        # Build signal strength description
        if opportunity.overall_score >= 85:
            strength = "EXCELLENT"
        elif opportunity.overall_score >= 70:
            strength = "STRONG"
        elif opportunity.overall_score >= 55:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        # Format confluence factors
        confluence_text = ", ".join(opportunity.confluence_factors[:4]) if opportunity.confluence_factors else "Multiple indicators aligned"

        # Format patterns detected
        patterns_text = ", ".join(opportunity.patterns_detected[:3]) if opportunity.patterns_detected else None

        # Build the entry reason
        parts = [
            f"[{strength} {opportunity.direction}] {horizon_text}",
            f"Score: {opportunity.overall_score:.0f}/100 | R:R {opportunity.risk_reward_ratio:.1f}:1",
            f"Entry: ${opportunity.entry_price:.2f} | Stop: ${opportunity.stop_loss:.2f} | Target: ${opportunity.target_1:.2f}",
            f"Confluence: {confluence_text}",
        ]

        # Add patterns if detected
        if patterns_text:
            parts.append(f"Patterns: {patterns_text}")

        # Add Elliott Wave if present
        if opportunity.elliott_wave:
            parts.append(f"Elliott: {opportunity.elliott_wave}")

        # Add warnings if present
        if opportunity.warnings:
            parts.append(f"Caution: {', '.join(opportunity.warnings[:2])}")

        return " | ".join(parts[:5])  # Limit to 500 chars (field limit)

    def _build_signal_entry_reason(self, signal, filled_price: float) -> str:
        """
        Build entry reason from a trading signal (used for non-hierarchical trades).

        Args:
            signal: TradingSignal object
            filled_price: The actual fill price

        Returns:
            A formatted string explaining the trade rationale
        """
        # Build signal strength description
        if signal.score >= 85:
            strength = "EXCELLENT"
        elif signal.score >= 70:
            strength = "STRONG"
        elif signal.score >= 55:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        # Trade type description
        trade_type = signal.trade_type.value if signal.trade_type else "SWING"

        # Build parts
        parts = [
            f"[{strength} {signal.signal_type.value if signal.signal_type else 'BUY'}] {trade_type}",
            f"Score: {signal.score:.0f}/100",
            f"Entry: ${filled_price:.2f}",
        ]

        # Add targets if available
        if signal.suggested_stop_loss:
            parts.append(f"Stop: ${signal.suggested_stop_loss:.2f}")
        if signal.suggested_profit_target:
            parts.append(f"Target: ${signal.suggested_profit_target:.2f}")

        # Add confluence if available
        if hasattr(signal, 'confluence_factors') and signal.confluence_factors:
            parts.append(f"Confluence: {', '.join(signal.confluence_factors[:3])}")

        return " | ".join(parts[:5])  # Limit to 500 chars

    def _log_execution_event(
        self,
        symbol: str,
        event_type: str,
        executed: bool,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an execution event for debugging paper trade failures.

        Args:
            symbol: The symbol involved
            event_type: Type of event (ENTRY_SIGNAL, ENTRY_ATTEMPT, ENTRY_SKIPPED, EXIT_SIGNAL, etc.)
            executed: Whether the trade was actually executed
            reason: Human-readable reason for the outcome
            details: Additional details (prices, scores, etc.)
        """
        # Normalize symbol for consistent logging (but don't fail on invalid)
        normalized_symbol, _, _ = self._normalize_and_validate_symbol(symbol)
        if normalized_symbol:
            symbol = normalized_symbol

        event = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "event_type": event_type,
            "executed": executed,
            "reason": reason,
            "details": details or {},
        }

        self._execution_log.append(event)

        # Keep log size bounded
        if len(self._execution_log) > self._max_execution_log_size:
            self._execution_log = self._execution_log[-self._max_execution_log_size:]

        # Log to standard logger as well
        log_msg = f"EXECUTION LOG [{event_type}] {symbol}: {reason}"
        if executed:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

    def get_execution_log(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent execution log entries, optionally filtered by symbol.

        Args:
            symbol: Filter to specific symbol (optional)
            limit: Maximum entries to return
        """
        log = self._execution_log
        if symbol:
            # Normalize the filter symbol for consistent matching
            normalized_symbol, _, _ = self._normalize_and_validate_symbol(symbol)
            if normalized_symbol:
                symbol = normalized_symbol
            log = [e for e in log if e["symbol"] == symbol]
        return log[-limit:]

    def get_strong_buy_trace(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get trace of last N 'Strong Buy' signals to diagnose execution failures.
        """
        strong_buys = [
            e for e in self._execution_log
            if e["event_type"] in ["ENTRY_SIGNAL", "ENTRY_ATTEMPT", "ENTRY_SKIPPED"]
            and e.get("details", {}).get("signal_strength") in ["STRONG_BUY", "BUY"]
        ]
        return strong_buys[-limit:]

    def _log_ai_decision(
        self,
        symbol: str,
        ai_decision: Dict[str, Any],
        technical_analysis: Dict[str, Any],
    ):
        """
        Log AI trading decision for tracking and display.

        Args:
            symbol: The symbol being evaluated
            ai_decision: The AI's decision response
            technical_analysis: The technical analysis that was evaluated
        """
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "decision": ai_decision.get("decision", "UNKNOWN"),
            "confidence": ai_decision.get("confidence", 0),
            "reasoning": ai_decision.get("reasoning", ""),
            "concerns": ai_decision.get("concerns", []),
            "ai_generated": ai_decision.get("ai_generated", False),
            "model": ai_decision.get("model", "unknown"),
            "technical_score": technical_analysis.get("score", 0),
            "technical_signal": technical_analysis.get("recommendation", ""),
            # Trade parameters if approved
            "suggested_position_size_pct": ai_decision.get("suggested_position_size_pct"),
            "suggested_stop_loss_pct": ai_decision.get("suggested_stop_loss_pct"),
            "suggested_take_profit_pct": ai_decision.get("suggested_take_profit_pct"),
            # Wait condition if applicable
            "wait_for": ai_decision.get("wait_for"),
        }

        # Update last decision
        self._last_ai_decision = decision_record

        # Add to history (keep last 50 decisions)
        self._ai_decisions.append(decision_record)
        if len(self._ai_decisions) > 50:
            self._ai_decisions = self._ai_decisions[-50:]

        logger.info(
            f"AI Decision logged: {symbol} - {decision_record['decision']} "
            f"({decision_record['confidence']}% confidence) - "
            f"AI: {decision_record['ai_generated']}"
        )

    async def _run_crypto_cycle(self):
        """
        Run crypto trading cycle.
        Crypto markets are 24/7, so this runs regardless of stock market hours.
        Uses the same risk parameters as stocks (as requested by user).
        Now includes comprehensive scan tracking and progress reporting.
        """
        from .crypto_service import get_crypto_service
        logger.info("Running crypto trading cycle (24/7)...")

        try:
            # Get singleton crypto service
            crypto_service = get_crypto_service()

            # Get current account to check buying power
            account = await self.alpaca.get_account()
            buying_power = float(account.get("buying_power", 0))

            # Get current crypto positions from Alpaca
            positions = await self.alpaca.get_positions()
            current_crypto_positions = {}
            for pos in positions:
                symbol = pos.get("symbol", "")
                # Crypto symbols in Alpaca contain "/" like "BTC/USD"
                if "/" in symbol or symbol.endswith("USD") and len(symbol) <= 7:
                    current_crypto_positions[symbol] = pos

            self._crypto_positions = current_crypto_positions
            num_crypto_positions = len(current_crypto_positions)

            logger.debug(f"Current crypto positions: {num_crypto_positions}/{self.crypto_max_positions}")

            # Check existing crypto positions for exit signals
            for symbol, position in list(current_crypto_positions.items()):
                try:
                    await self._check_crypto_exit(crypto_service, symbol, position)
                except Exception as e:
                    logger.error(f"Error checking crypto exit for {symbol}: {e}")

            # Initialize scan tracking
            symbols_to_scan = [s for s in self.crypto_symbols if s not in current_crypto_positions]
            self._crypto_scan_progress = {
                "total": len(symbols_to_scan),
                "scanned": 0,
                "current_symbol": None,
                "signals_found": 0,
                "best_opportunity": None,
                "scan_status": "scanning",
                "scan_summary": f"Starting scan of {len(symbols_to_scan)} cryptos...",
                "last_scan_completed": None,
                "next_scan_in_seconds": self.cycle_interval_seconds,
            }

            # Track best opportunity even if below threshold
            best_buy_signal = None
            best_buy_confidence = 0
            signals_above_threshold = 0

            # Check if at max capacity - only monitor existing positions, don't scan for new ones
            # Capacity is reached if either:
            # 1. Position count is at max
            # 2. Buying power is too low (< $100 minimum to open meaningful position)
            MIN_BUYING_POWER_FOR_NEW_POSITION = self.trading_config.min_buying_power_for_position
            at_max_positions = num_crypto_positions >= self.crypto_max_positions
            insufficient_buying_power = buying_power < MIN_BUYING_POWER_FOR_NEW_POSITION
            at_max_capacity = at_max_positions or insufficient_buying_power

            if at_max_capacity:
                # Determine the specific reason
                if at_max_positions and insufficient_buying_power:
                    capacity_reason = f"At max positions ({num_crypto_positions}/{self.crypto_max_positions}) and low buying power (${buying_power:.2f})"
                elif at_max_positions:
                    capacity_reason = f"At max positions ({num_crypto_positions}/{self.crypto_max_positions})"
                else:
                    capacity_reason = f"Insufficient buying power (${buying_power:.2f} < ${MIN_BUYING_POWER_FOR_NEW_POSITION} minimum)"

                # At max capacity - update status to show monitoring mode only
                self._crypto_scan_progress = {
                    "total": 0,
                    "scanned": 0,
                    "current_symbol": None,
                    "signals_found": 0,
                    "best_opportunity": None,
                    "scan_status": "at_capacity",
                    "scan_summary": f"{capacity_reason}. Monitoring existing positions only.",
                    "last_scan_completed": datetime.now().isoformat(),
                    "next_scan_in_seconds": self.cycle_interval_seconds,
                    "monitoring_only": True,
                    "positions_held": list(current_crypto_positions.keys()),
                    "buying_power": buying_power,
                }
                logger.info(f"Crypto capacity reached: {capacity_reason} - monitoring only, no new position scans")
                return  # Exit early - no need to scan for new positions

            # If we have room for more positions, look for entry opportunities
            for idx, symbol in enumerate(symbols_to_scan):
                # Update scan progress
                self._crypto_scan_progress["current_symbol"] = symbol
                self._crypto_scan_progress["scanned"] = idx + 1
                self._crypto_scan_progress["scan_summary"] = f"Analyzing {symbol}... ({idx + 1}/{len(symbols_to_scan)})"

                try:
                    # Analyze crypto for entry
                    analysis = await crypto_service.analyze_crypto(symbol)
                    if not analysis:
                        logger.debug(f"No analysis returned for {symbol}")
                        # Track that we analyzed but got no data
                        self._crypto_analysis_results[symbol] = {
                            "signal": "NO_DATA",
                            "confidence": 0,
                            "threshold": self.crypto_entry_threshold,
                            "reason": "No analysis data available",
                            "timestamp": datetime.now().isoformat(),
                        }
                        continue

                    # Map crypto service response to our format
                    recommendation = analysis.get("recommendation", "HOLD")
                    score = analysis.get("score", 50)

                    # Convert recommendation to simple signal
                    if recommendation in ["BUY", "STRONG_BUY", "LEAN_BUY"]:
                        signal = "BUY"
                    elif recommendation in ["SELL", "STRONG_SELL", "LEAN_SELL"]:
                        signal = "SELL"
                    else:
                        signal = "NEUTRAL"

                    confidence = score

                    # Track best buy opportunity (even if below threshold)
                    if signal == "BUY" and confidence > best_buy_confidence:
                        best_buy_confidence = confidence
                        best_buy_signal = {
                            "symbol": symbol,
                            "confidence": confidence,
                            "threshold": self.crypto_entry_threshold,
                            "meets_threshold": confidence >= self.crypto_entry_threshold,
                        }

                    # Track analysis result - use lower crypto threshold
                    self._crypto_analysis_results[symbol] = {
                        "signal": signal,
                        "confidence": confidence,
                        "threshold": self.crypto_entry_threshold,
                        "meets_threshold": signal == "BUY" and confidence >= self.crypto_entry_threshold,
                        "reason": self._get_analysis_reason(signal, confidence, self.crypto_entry_threshold),
                        "timestamp": datetime.now().isoformat(),
                        "indicators": analysis.get("indicators", {}),
                        "signals": analysis.get("signals", []),
                    }
                    self._last_crypto_analysis_time = datetime.now()

                    logger.info(f"Crypto analysis for {symbol}: signal={signal}, confidence={confidence:.1f}, threshold={self.crypto_entry_threshold}")

                    # Use CRYPTO-SPECIFIC threshold (lower than stocks)
                    if signal == "BUY" and confidence >= self.crypto_entry_threshold:
                        signals_above_threshold += 1
                        self._crypto_scan_progress["signals_found"] = signals_above_threshold

                        # Calculate position size using same risk params as stocks
                        quote = await crypto_service.get_crypto_quote(symbol)
                        if not quote or quote.get("price", 0) <= 0:
                            continue

                        price = quote["price"]

                        # === AI EVALUATION FOR ALL SIGNALS (for transparency) ===
                        # Always run AI evaluation so users can see why trades pass/fail
                        ai_decision = None
                        logger.info(f"AI Evaluating {symbol} crypto trade (auto_trade_mode={self.auto_trade_mode})...")
                        self._crypto_scan_progress["scan_summary"] = f"AI evaluating {symbol}..."

                        # Get existing crypto positions for portfolio context
                        existing_crypto_symbols = list(current_crypto_positions.keys())

                        # Ask AI to evaluate the trade
                        try:
                            ai_decision = await self.ai_advisor.evaluate_crypto_trade(
                                symbol=symbol,
                                technical_analysis=analysis,
                                current_price=price,
                                account_info={
                                    "equity": float(account.get("equity", 0)),
                                    "buying_power": buying_power,
                                    "crypto_positions": num_crypto_positions,
                                    "max_crypto_positions": self.crypto_max_positions,
                                },
                                existing_positions=existing_crypto_symbols,
                            )
                        except Exception as e:
                            logger.warning(f"AI evaluation failed for {symbol}: {e}")
                            ai_decision = {
                                "decision": "WAIT",
                                "confidence": 0,
                                "reasoning": f"AI evaluation unavailable: {str(e)[:50]}",
                                "concerns": ["AI service error"],
                            }

                            # Log AI decision
                            self._log_ai_decision(symbol, ai_decision, analysis)

                            # Update analysis result with AI decision
                            self._crypto_analysis_results[symbol]["ai_decision"] = ai_decision

                            # If AI rejects, update the signal to reflect reality
                            if ai_decision.get("decision") != "APPROVE":
                                self._crypto_analysis_results[symbol]["signal"] = "HOLD"
                                self._crypto_analysis_results[symbol]["meets_threshold"] = False
                                self._crypto_analysis_results[symbol]["reason"] = f"AI {ai_decision.get('decision')}: {ai_decision.get('reasoning', '')[:50]}"

                            # If AI rejects or says wait, skip this crypto
                            if ai_decision.get("decision") != "APPROVE":
                                logger.info(
                                    f"AI {ai_decision.get('decision', 'REJECTED')} trade for {symbol}: "
                                    f"{ai_decision.get('reasoning', 'No reason provided')}"
                                )
                                # Log to execution log for Activity tab visibility
                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type=f"AI_{ai_decision.get('decision', 'REJECTED')}",
                                    executed=False,
                                    reason=ai_decision.get('reasoning', 'No reason provided')[:100],
                                    details={
                                        "score": confidence,
                                        "ai_decision": ai_decision.get("decision"),
                                        "confidence": ai_decision.get("confidence", 0),
                                        "concerns": ai_decision.get("concerns", [])[:3],
                                    }
                                )
                                if ai_decision.get("decision") == "WAIT":
                                    self._crypto_scan_progress["scan_summary"] = (
                                        f"AI says WAIT on {symbol}: {ai_decision.get('wait_for', 'better entry')}"
                                    )
                                continue

                            logger.info(
                                f"AI APPROVED trade for {symbol}: {ai_decision.get('reasoning', '')}"
                            )

                            # ONLY EXECUTE IF AUTO_TRADE_MODE IS ON
                            if not self.auto_trade_mode:
                                logger.info(f"Auto trade mode OFF - Signal approved for {symbol} but not executing")
                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type="CRYPTO_ENTRY_SKIPPED",
                                    executed=False,
                                    reason="Auto trade mode is OFF - manual execution required",
                                    details={"confidence": confidence, "ai_decision": ai_decision.get("decision")}
                                )
                                continue

                            # Position size based on risk per trade (or AI-suggested if available)
                            position_size_pct = self.risk_manager.risk_per_trade_pct
                            if ai_decision and ai_decision.get("suggested_position_size_pct"):
                                position_size_pct = ai_decision["suggested_position_size_pct"]
                                logger.info(f"Using AI-suggested position size: {position_size_pct*100:.1f}%")

                            position_value = buying_power * position_size_pct
                            position_value = min(position_value, buying_power * self.risk_manager.max_position_size_pct)

                            if position_value < self.trading_config.min_position_value_crypto:
                                logger.debug(f"Insufficient buying power for {symbol}")
                                continue

                            qty = position_value / price

                            logger.info(f"Crypto BUY signal for {symbol}: confidence={confidence:.1f}, price=${price:.2f}, qty={qty:.6f}")

                            # Log the entry attempt
                            self._log_execution_event(
                                symbol=symbol,
                                event_type="CRYPTO_ENTRY_ATTEMPT",
                                executed=False,  # Will be updated if successful
                                reason=f"Attempting to buy ${position_value:.2f} worth ({qty:.6f} units) at ${price:.2f}",
                                details={
                                    "signal_strength": signal,
                                    "confidence": confidence,
                                    "price": price,
                                    "qty": qty,
                                    "position_value": position_value,
                                    "buying_power": buying_power,
                                }
                            )

                            order = await crypto_service.place_crypto_order(
                                symbol=symbol,
                                qty=qty,
                                side="buy"
                            )

                            if order:
                                # Check if order contains an error
                                if order.get("error"):
                                    error_msg = order.get("error_message", "Unknown error")
                                    status_code = order.get("status_code")

                                    # Parse error to get specific error code
                                    error_code, parsed_msg = parse_api_error(
                                        Exception(error_msg),
                                        {"status_code": status_code, "message": error_msg}
                                    )

                                    # Log to enhanced ExecutionLogger
                                    self.execution_logger.log_failure(
                                        symbol=symbol,
                                        asset_class="crypto",
                                        side="BUY",
                                        quantity=qty,
                                        price=price,
                                        order_type="market",
                                        error_code=error_code,
                                        error_message=parsed_msg,
                                    )

                                    # Also log to legacy event log
                                    self._log_execution_event(
                                        symbol=symbol,
                                        event_type="CRYPTO_ORDER_FAILED",
                                        executed=False,
                                        reason=f"[{error_code.value}] {parsed_msg}",
                                        details={
                                            "error_code": error_code.value,
                                            "error_message": error_msg,
                                            "status_code": status_code,
                                            "qty": qty,
                                            "price": price,
                                        }
                                    )
                                    continue  # Don't count this as a position

                                ai_note = " (AI Approved)" if self.auto_trade_mode and ai_decision else ""
                                logger.info(f"Crypto order placed for {symbol}: ${position_value:.2f}{ai_note}")

                                # Log to enhanced ExecutionLogger
                                filled_price = order.get("filled_avg_price") or price
                                self.execution_logger.log_success(
                                    symbol=symbol,
                                    asset_class="crypto",
                                    side="BUY",
                                    quantity=order.get("qty", qty),
                                    price=filled_price,
                                    order_type="market",
                                    order_id=order.get("order_id"),
                                    filled_quantity=order.get("filled_qty", qty),
                                    filled_price=filled_price,
                                )

                                # Log successful execution (legacy)
                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type="CRYPTO_ENTRY_SUCCESS",
                                    executed=True,
                                    reason=f"Bought ${position_value:.2f} worth at ${price:.2f}",
                                    details={
                                        "order_id": order.get("order_id"),
                                        "status": order.get("status"),
                                        "qty": order.get("qty"),
                                        "filled_qty": order.get("filled_qty"),
                                        "filled_avg_price": order.get("filled_avg_price"),
                                    }
                                )

                                num_crypto_positions += 1

                                # Update scan status to found
                                self._crypto_scan_progress["scan_status"] = "found_opportunity"
                                self._crypto_scan_progress["scan_summary"] = (
                                    f"Entered position: {symbol} at {confidence:.0f}% confidence{ai_note}"
                                )

                                if num_crypto_positions >= self.crypto_max_positions:
                                    break
                            else:
                                # Order returned None - log this failure
                                self.execution_logger.log_failure(
                                    symbol=symbol,
                                    asset_class="crypto",
                                    side="BUY",
                                    quantity=qty,
                                    price=price,
                                    order_type="market",
                                    error_code=ExecutionErrorCode.NETWORK_ERROR,
                                    error_message="Order returned None - API call failed or returned no data",
                                )

                                self._log_execution_event(
                                    symbol=symbol,
                                    event_type="CRYPTO_ORDER_FAILED",
                                    executed=False,
                                    reason="[NETWORK_ERROR] Order returned None - API call failed or returned no data",
                                    details={
                                        "error_code": "NETWORK_ERROR",
                                        "qty": qty,
                                        "price": price,
                                        "position_value": position_value,
                                    }
                                )

                except Exception as e:
                    logger.error(f"Error analyzing crypto {symbol}: {e}")

            # Finalize scan tracking
            self._crypto_scan_progress["scanned"] = len(symbols_to_scan)
            self._crypto_scan_progress["current_symbol"] = None
            self._crypto_scan_progress["best_opportunity"] = best_buy_signal
            self._crypto_scan_progress["last_scan_completed"] = datetime.now().isoformat()
            self._total_scans_today += 1  # Count crypto scans too

            # Set final scan status and summary
            if self._crypto_scan_progress["scan_status"] != "found_opportunity":
                if signals_above_threshold > 0:
                    self._crypto_scan_progress["scan_status"] = "found_opportunity"
                    self._crypto_scan_progress["scan_summary"] = f"Found {signals_above_threshold} signal(s) above threshold"
                elif best_buy_signal:
                    self._crypto_scan_progress["scan_status"] = "exhausted"
                    gap = best_buy_signal["threshold"] - best_buy_signal["confidence"]
                    self._crypto_scan_progress["scan_summary"] = (
                        f"Scanned {len(symbols_to_scan)} cryptos - no signals above {self.crypto_entry_threshold:.0f}% threshold. "
                        f"Best: {best_buy_signal['symbol']} at {best_buy_signal['confidence']:.0f}% ({gap:.0f}% below threshold)"
                    )
                else:
                    self._crypto_scan_progress["scan_status"] = "exhausted"
                    self._crypto_scan_progress["scan_summary"] = (
                        f"Scanned {len(symbols_to_scan)} cryptos - no buy signals found. Waiting for next cycle..."
                    )

            logger.info(f"Crypto scan complete: {self._crypto_scan_progress['scan_summary']}")

        except Exception as e:
            logger.error(f"Error in crypto trading cycle: {e}")

    async def _check_crypto_exit(self, crypto_service: CryptoService, symbol: str, position: Dict):
        """Check if a crypto position should be exited"""
        # Validate and normalize crypto symbol
        normalized_symbol, is_valid, error_msg = self._normalize_and_validate_symbol(symbol, allow_crypto=True)
        if not is_valid:
            logger.warning(f"[CRYPTO_EXIT] Invalid symbol '{symbol}': {error_msg}")
            return
        symbol = normalized_symbol

        try:
            qty = float(position.get("qty", 0))
            entry_price = float(position.get("avg_entry_price", 0))
            current_price = float(position.get("current_price", 0))
            unrealized_pnl_pct = float(position.get("unrealized_plpc", 0)) * 100

            if entry_price <= 0 or qty <= 0:
                return

            # Get fresh quote
            quote = await crypto_service.get_crypto_quote(symbol)
            if quote:
                current_price = quote.get("price", current_price)
                unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # Check exit conditions using same parameters as stocks
            should_exit = False
            exit_reason = ""

            # Stop loss check
            if unrealized_pnl_pct <= -self.risk_manager.default_stop_loss_pct * 100:
                should_exit = True
                exit_reason = "stop_loss"

            # Take profit check
            if unrealized_pnl_pct >= self.strategy.swing_profit_target_pct * 100:
                should_exit = True
                exit_reason = "profit_target"

            # Trailing stop check (if enabled and in profit)
            if self.trailing_stop_enabled and unrealized_pnl_pct > self.trailing_stop_activation_pct * 100:
                # Simple trailing stop - check if price dropped from high
                # In production, you'd track the high watermark
                if unrealized_pnl_pct < (self.trailing_stop_activation_pct - self.trailing_stop_pct) * 100:
                    should_exit = True
                    exit_reason = "trailing_stop"

            if should_exit:
                logger.info(f"Crypto EXIT signal for {symbol}: reason={exit_reason}, P&L={unrealized_pnl_pct:.2f}%")

                # Place sell order
                order = await crypto_service.place_crypto_order(
                    symbol=symbol,
                    qty=qty,
                    side="sell"
                )

                if order:
                    logger.info(f"Crypto sell order placed for {symbol}: {qty} units")
                    if symbol in self._crypto_positions:
                        del self._crypto_positions[symbol]

        except Exception as e:
            logger.error(f"Error checking crypto exit for {symbol}: {e}")


# Global bot instance
_trading_bot: Optional[TradingBot] = None


def get_trading_bot(paper_trading: bool = None) -> TradingBot:
    """Get or create trading bot singleton"""
    global _trading_bot
    if _trading_bot is None:
        # Default to paper trading from env, or True for safety
        if paper_trading is None:
            paper_trading = os.getenv("ALPACA_TRADING_MODE", "paper") == "paper"
        _trading_bot = TradingBot(paper_trading=paper_trading)
    return _trading_bot
