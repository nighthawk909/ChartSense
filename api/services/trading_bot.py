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

        # Bot state
        self.state = BotState.STOPPED
        self.start_time: Optional[datetime] = None
        self.last_trade_time: Optional[datetime] = None
        self.current_cycle: str = "idle"
        self.current_session: str = "unknown"  # pre_market, regular, after_hours, overnight, weekend
        self.error_message: Optional[str] = None

        # Configuration
        self.enabled_symbols: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        self.user_symbols: List[str] = []  # User's personal stock picks
        self.paper_trading = paper_trading
        self.trading_hours_only = False  # Changed: trade during extended hours too!
        self.allow_extended_hours = True  # Trade pre-market and after-hours
        self.cycle_interval_seconds = 60  # How often to run analysis
        self.use_ai_discovery = True  # Use AI to discover stocks
        self.last_discovery_time: Optional[datetime] = None

        # Exit Strategy Settings
        self.trailing_stop_enabled = False
        self.trailing_stop_pct = 0.03
        self.trailing_stop_activation_pct = 0.05
        self.partial_profit_enabled = False
        self.partial_profit_pct = 0.50  # Portion to sell
        self.partial_profit_at = 0.05  # Profit level to trigger

        # Profit Reinvestment
        self.reinvest_profits = True
        self.compounding_enabled = True

        # Intraday Settings
        self.intraday_enabled = False
        self.intraday_timeframe = "5min"
        self.max_trades_per_day = 10
        self.trades_today = 0

        # Auto Trade Mode
        self.auto_trade_mode = False
        self.ai_risk_tolerance = "moderate"

        # Crypto Trading Settings
        self.crypto_trading_enabled = False
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
        self.crypto_max_positions = 2
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

        # Track partial sells
        self._partial_sold: Dict[str, bool] = {}  # Symbol -> has taken partial profit

        # Stock repository
        self._stock_scores: Dict[str, float] = {}  # Symbol -> last score
        self._ready_stocks: List[str] = []  # Stocks ready for entry

        # AI Decision Tracking
        self._ai_decisions: List[Dict[str, Any]] = []  # History of AI decisions
        self._last_ai_decision: Optional[Dict[str, Any]] = None  # Most recent AI decision

        # Tracking
        self._positions_cache: Dict[str, Dict] = {}
        self._running_task: Optional[asyncio.Task] = None

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
            self.enabled_symbols = config["enabled_symbols"]
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

    async def _load_db_config(self):
        """Load configuration from database including user watchlist and stock repository"""
        try:
            db = SessionLocal()

            # Load bot configuration
            config = db.query(BotConfiguration).filter(BotConfiguration.is_active == True).first()

            if config:
                self.enabled_symbols = config.enabled_symbols or self.enabled_symbols
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

                # Exit Strategies
                self.trailing_stop_enabled = getattr(config, 'trailing_stop_enabled', False)
                self.trailing_stop_pct = getattr(config, 'trailing_stop_pct', 0.03)
                self.trailing_stop_activation_pct = getattr(config, 'trailing_stop_activation_pct', 0.05)
                self.partial_profit_enabled = getattr(config, 'partial_profit_enabled', False)
                self.partial_profit_pct = getattr(config, 'partial_profit_pct', 0.50)
                self.partial_profit_at = getattr(config, 'partial_profit_at', 0.05)

                # Profit Reinvestment
                self.reinvest_profits = getattr(config, 'reinvest_profits', True)
                self.compounding_enabled = getattr(config, 'compounding_enabled', True)

                # Intraday
                self.intraday_enabled = getattr(config, 'intraday_enabled', False)
                self.intraday_timeframe = getattr(config, 'intraday_timeframe', "5min")
                self.max_trades_per_day = getattr(config, 'max_trades_per_day', 10)

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
            self.user_symbols = [s.symbol for s in user_stocks]
            if self.user_symbols:
                logger.info(f"Loaded {len(self.user_symbols)} user stocks: {self.user_symbols}")

            # Load active stocks from repository
            repo_stocks = db.query(StockRepository).filter(
                StockRepository.is_active == True
            ).order_by(StockRepository.priority.desc()).limit(20).all()

            repo_symbols = [s.symbol for s in repo_stocks]

            # Merge all symbols: user picks first (highest priority), then enabled, then repository
            all_symbols = []
            seen = set()
            for symbol in self.user_symbols + self.enabled_symbols + repo_symbols:
                if symbol not in seen:
                    all_symbols.append(symbol)
                    seen.add(symbol)

            self.enabled_symbols = all_symbols[:20]  # Cap at 20 for API limits
            logger.info(f"Trading {len(self.enabled_symbols)} symbols: {self.enabled_symbols}")

            db.close()
        except Exception as e:
            logger.warning(f"Could not load config from database: {e}")

    async def _main_loop(self):
        """
        Main trading loop - always active, adapts to market session.

        Sessions:
        - regular: Normal trading with market orders
        - pre_market: Extended hours with limit orders (4:00 AM - 9:30 AM ET)
        - after_hours: Extended hours with limit orders (4:00 PM - 8:00 PM ET)
        - overnight/weekend: Analysis, discovery, preparation (no trading)
        """
        logger.info("Main trading loop started - Bot will stay active 24/7")

        while self.state in [BotState.RUNNING, BotState.PAUSED]:
            try:
                if self.state == BotState.PAUSED:
                    self.current_cycle = "paused"
                    await asyncio.sleep(5)
                    continue

                # Get detailed market session info
                market_info = await self.alpaca.get_market_hours_info()
                self.current_session = market_info.get("session", "unknown")
                can_trade = market_info.get("can_trade", False)
                is_extended = market_info.get("can_trade_extended", False)

                logger.debug(f"Session: {self.current_session}, Can trade: {can_trade}, Extended: {is_extended}")

                # Check daily loss limit
                account = await self.alpaca.get_account()
                if self.risk_manager.is_daily_loss_limit_hit(account["equity"]):
                    self.current_cycle = "daily_loss_limit_paused"
                    logger.warning("Daily loss limit reached, pausing trading")
                    await asyncio.sleep(300)
                    continue

                # Determine what to do based on session
                if self.current_session in ["overnight", "weekend"]:
                    # Can't trade stocks, but stay active - do analysis and discovery
                    self.current_cycle = "off_hours_analysis"
                    await self._run_off_hours_cycle()

                    # Crypto trades 24/7 - run crypto cycle even during stock market off hours!
                    if self.crypto_trading_enabled:
                        self.current_cycle = "crypto_trading"
                        await self._run_crypto_cycle()

                    await asyncio.sleep(300)  # Check every 5 minutes during off hours

                elif self.current_session == "regular":
                    # Normal trading hours - full trading cycle
                    await self._run_trading_cycle(extended_hours=False)

                    # Also run crypto if enabled (crypto is 24/7)
                    if self.crypto_trading_enabled:
                        self.current_cycle = "crypto_trading"
                        await self._run_crypto_cycle()

                    await asyncio.sleep(self.cycle_interval_seconds)

                elif self.current_session in ["pre_market", "after_hours"]:
                    # Extended hours - trade with limit orders only
                    if self.allow_extended_hours:
                        await self._run_trading_cycle(extended_hours=True)
                    else:
                        self.current_cycle = "extended_hours_waiting"
                        await self._run_off_hours_cycle()

                    # Crypto trades 24/7
                    if self.crypto_trading_enabled:
                        self.current_cycle = "crypto_trading"
                        await self._run_crypto_cycle()

                    await asyncio.sleep(self.cycle_interval_seconds * 2)  # Slower during extended

                else:
                    # Unknown session - be cautious, but still do crypto if enabled
                    self.current_cycle = "unknown_session"
                    if self.crypto_trading_enabled:
                        await self._run_crypto_cycle()
                    await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.error_message = str(e)
                self.current_cycle = "error_recovery"
                await asyncio.sleep(30)

        logger.info("Main trading loop ended")

    async def _run_off_hours_cycle(self):
        """Run analysis during off-hours (overnight/weekend) - no trading"""
        logger.debug("Running off-hours analysis cycle...")

        try:
            # AI discovery runs during off hours too
            if self.use_ai_discovery and self.ai_advisor.enabled:
                await self._ai_discover_stocks()

            # Analyze all stocks and update their scores for when market opens
            self.current_cycle = "pre_analyzing"
            for symbol in self.enabled_symbols[:10]:  # Limit to avoid rate limits
                try:
                    signal = await self._analyze_symbol(symbol)
                    if signal:
                        self._stock_scores[symbol] = signal.score
                        # Track stocks that are ready for entry
                        if signal.signal_type == SignalType.BUY and signal.score >= self.strategy.entry_threshold:
                            if symbol not in self._ready_stocks:
                                self._ready_stocks.append(symbol)
                                logger.info(f"Stock {symbol} is ready for entry (score: {signal.score:.1f})")
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol} during off-hours: {e}")

            # Update repository with scores
            await self._update_repository_scores()

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

    async def _run_trading_cycle(self, extended_hours: bool = False):
        """
        Run one trading cycle - analyze, decide, execute.

        Args:
            extended_hours: If True, use limit orders for extended hours trading
        """
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

            # Analyze symbols for entry signals
            self.current_cycle = "scanning_entries"
            for symbol in self.enabled_symbols:
                # Skip if already have position
                if symbol in self._positions_cache:
                    continue

                # Analyze symbol
                signal = await self._analyze_symbol(symbol)

                if signal and signal.signal_type == SignalType.BUY:
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
                            # === TRUE AI CONTROL FOR STOCKS ===
                            # When auto_trade_mode is enabled, AI makes the final decision
                            ai_decision = None
                            if self.auto_trade_mode:
                                logger.info(f"AI Auto Trade Mode: Evaluating {symbol} stock trade...")

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

                                # Log AI decision
                                self._log_ai_decision(symbol, ai_decision, signal_data)

                                # If AI rejects or says wait, skip this stock
                                if ai_decision.get("decision") != "APPROVE":
                                    logger.info(
                                        f"AI {ai_decision.get('decision', 'REJECTED')} trade for {symbol}: "
                                        f"{ai_decision.get('reasoning', 'No reason provided')}"
                                    )
                                    continue

                                logger.info(
                                    f"AI APPROVED trade for {symbol}: {ai_decision.get('reasoning', '')}"
                                )

                            await self._execute_entry(symbol, signal, position_size.shares, extended_hours)
                            # Update positions list
                            positions = await self.alpaca.get_positions()
                        else:
                            logger.debug(f"Skipping {symbol}: {risk_check.reason}")

            self.current_cycle = "cycle_complete"

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            raise

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
                # Extract symbols from discovered stocks
                new_symbols = [s["symbol"] for s in discovered if "symbol" in s]

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
        try:
            # Get historical bars
            bars = await self.alpaca.get_bars(symbol, timeframe="1day", limit=200)

            if len(bars) < 50:
                logger.debug(f"Insufficient data for {symbol}: {len(bars)} bars")
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
        try:
            order_type = "limit (extended)" if extended_hours else "market"
            logger.info(
                f"ENTRY: {symbol} - {shares} shares @ ~${signal.current_price:.2f} "
                f"(score={signal.score:.1f}, type={signal.trade_type.value}, order={order_type})"
            )

            # Submit order based on session
            if extended_hours:
                # Extended hours require limit orders
                # Use current price with small buffer for limit
                limit_price = round(signal.current_price * 1.001, 2)  # 0.1% above current
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
                )
                db.add(position)
                db.commit()
            finally:
                db.close()

            self.last_trade_time = datetime.now()
            logger.info(f"Entry executed: {symbol} {shares} shares @ ${filled_price:.2f}")

            # Submit stop-loss order
            await self.alpaca.submit_stop_loss_order(
                symbol=symbol,
                quantity=shares,
                stop_price=signal.suggested_stop_loss,
            )

        except Exception as e:
            logger.error(f"Failed to execute entry for {symbol}: {e}")
            raise

    async def _execute_partial_exit(self, symbol: str, quantity: int, reason: str):
        """Execute partial exit trade (for partial profit taking)"""
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

    async def _execute_exit(self, symbol: str, quantity: float, reason: str):
        """Execute exit trade"""
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
            # AI Decision Tracking
            "last_ai_decision": self._last_ai_decision,
            "ai_decisions_history": self._ai_decisions[-10:],  # Last 10 decisions for UI
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

            # If we have room for more positions, look for entry opportunities
            if num_crypto_positions < self.crypto_max_positions:
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
                                "threshold": self.strategy.entry_threshold,
                                "reason": "No analysis data available",
                                "timestamp": datetime.now().isoformat(),
                            }
                            continue

                        # Map crypto service response to our format
                        recommendation = analysis.get("recommendation", "HOLD")
                        score = analysis.get("score", 50)

                        # Convert recommendation to simple signal
                        if recommendation in ["BUY", "STRONG_BUY"]:
                            signal = "BUY"
                        elif recommendation in ["SELL", "STRONG_SELL"]:
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
                                "threshold": self.strategy.entry_threshold,
                                "meets_threshold": confidence >= self.strategy.entry_threshold,
                            }

                        # Track analysis result
                        self._crypto_analysis_results[symbol] = {
                            "signal": signal,
                            "confidence": confidence,
                            "threshold": self.strategy.entry_threshold,
                            "meets_threshold": signal == "BUY" and confidence >= self.strategy.entry_threshold,
                            "reason": self._get_analysis_reason(signal, confidence, self.strategy.entry_threshold),
                            "timestamp": datetime.now().isoformat(),
                            "indicators": analysis.get("indicators", {}),
                            "signals": analysis.get("signals", []),
                        }
                        self._last_crypto_analysis_time = datetime.now()

                        logger.info(f"Crypto analysis for {symbol}: signal={signal}, confidence={confidence:.1f}, threshold={self.strategy.entry_threshold}")

                        # Use same entry threshold as stocks
                        if signal == "BUY" and confidence >= self.strategy.entry_threshold:
                            signals_above_threshold += 1
                            self._crypto_scan_progress["signals_found"] = signals_above_threshold

                            # Calculate position size using same risk params as stocks
                            quote = await crypto_service.get_crypto_quote(symbol)
                            if not quote or quote.get("price", 0) <= 0:
                                continue

                            price = quote["price"]

                            # === TRUE AI CONTROL ===
                            # When auto_trade_mode is enabled, AI makes the final decision
                            ai_decision = None
                            if self.auto_trade_mode:
                                logger.info(f"AI Auto Trade Mode: Evaluating {symbol} trade...")
                                self._crypto_scan_progress["scan_summary"] = f"AI evaluating {symbol}..."

                                # Get existing crypto positions for portfolio context
                                existing_crypto_symbols = list(current_crypto_positions.keys())

                                # Ask AI to evaluate the trade
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

                                # Log AI decision
                                self._log_ai_decision(symbol, ai_decision, analysis)

                                # Update analysis result with AI decision
                                self._crypto_analysis_results[symbol]["ai_decision"] = ai_decision

                                # If AI rejects or says wait, skip this crypto
                                if ai_decision.get("decision") != "APPROVE":
                                    logger.info(
                                        f"AI {ai_decision.get('decision', 'REJECTED')} trade for {symbol}: "
                                        f"{ai_decision.get('reasoning', 'No reason provided')}"
                                    )
                                    if ai_decision.get("decision") == "WAIT":
                                        self._crypto_scan_progress["scan_summary"] = (
                                            f"AI says WAIT on {symbol}: {ai_decision.get('wait_for', 'better entry')}"
                                        )
                                    continue

                                logger.info(
                                    f"AI APPROVED trade for {symbol}: {ai_decision.get('reasoning', '')}"
                                )

                            # Position size based on risk per trade (or AI-suggested if available)
                            position_size_pct = self.risk_manager.risk_per_trade_pct
                            if ai_decision and ai_decision.get("suggested_position_size_pct"):
                                position_size_pct = ai_decision["suggested_position_size_pct"]
                                logger.info(f"Using AI-suggested position size: {position_size_pct*100:.1f}%")

                            position_value = buying_power * position_size_pct
                            position_value = min(position_value, buying_power * self.risk_manager.max_position_size_pct)

                            if position_value < 10:  # Minimum $10 for crypto
                                logger.debug(f"Insufficient buying power for {symbol}")
                                continue

                            qty = position_value / price

                            logger.info(f"Crypto BUY signal for {symbol}: confidence={confidence:.1f}, price=${price:.2f}, qty={qty:.6f}")

                            order = await crypto_service.place_crypto_order(
                                symbol=symbol,
                                qty=qty,
                                side="buy"
                            )

                            if order:
                                ai_note = " (AI Approved)" if self.auto_trade_mode and ai_decision else ""
                                logger.info(f"Crypto order placed for {symbol}: ${position_value:.2f}{ai_note}")
                                num_crypto_positions += 1

                                # Update scan status to found
                                self._crypto_scan_progress["scan_status"] = "found_opportunity"
                                self._crypto_scan_progress["scan_summary"] = (
                                    f"Entered position: {symbol} at {confidence:.0f}% confidence{ai_note}"
                                )

                                if num_crypto_positions >= self.crypto_max_positions:
                                    break

                    except Exception as e:
                        logger.error(f"Error analyzing crypto {symbol}: {e}")

            # Finalize scan tracking
            self._crypto_scan_progress["scanned"] = len(symbols_to_scan)
            self._crypto_scan_progress["current_symbol"] = None
            self._crypto_scan_progress["best_opportunity"] = best_buy_signal
            self._crypto_scan_progress["last_scan_completed"] = datetime.now().isoformat()

            # Set final scan status and summary
            if self._crypto_scan_progress["scan_status"] != "found_opportunity":
                if signals_above_threshold > 0:
                    self._crypto_scan_progress["scan_status"] = "found_opportunity"
                    self._crypto_scan_progress["scan_summary"] = f"Found {signals_above_threshold} signal(s) above threshold"
                elif best_buy_signal:
                    self._crypto_scan_progress["scan_status"] = "exhausted"
                    gap = best_buy_signal["threshold"] - best_buy_signal["confidence"]
                    self._crypto_scan_progress["scan_summary"] = (
                        f"Scanned {len(symbols_to_scan)} cryptos - no signals above {self.strategy.entry_threshold:.0f}% threshold. "
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
