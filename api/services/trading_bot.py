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
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session

from .alpaca_service import AlpacaService, get_alpaca_service
from .strategy_engine import StrategyEngine, SignalType, TradeType
from .risk_manager import RiskManager
from .indicators import IndicatorService
from .ai_advisor import get_ai_advisor
from ..database.models import Trade, Position, BotConfiguration, StockRepository, UserWatchlist
from ..database.connection import SessionLocal

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
        paper_trading: bool = False,
    ):
        """
        Initialize trading bot.

        Args:
            alpaca_service: Alpaca service instance
            paper_trading: Use paper trading (safer for testing)
        """
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

        # Stock repository
        self._stock_scores: Dict[str, float] = {}  # Symbol -> last score
        self._ready_stocks: List[str] = []  # Stocks ready for entry

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

                logger.info(f"Loaded config '{config.name}' from database")

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
                    # Can't trade, but stay active - do analysis and discovery
                    self.current_cycle = "off_hours_analysis"
                    await self._run_off_hours_cycle()
                    await asyncio.sleep(300)  # Check every 5 minutes during off hours

                elif self.current_session == "regular":
                    # Normal trading hours - full trading cycle
                    await self._run_trading_cycle(extended_hours=False)
                    await asyncio.sleep(self.cycle_interval_seconds)

                elif self.current_session in ["pre_market", "after_hours"]:
                    # Extended hours - trade with limit orders only
                    if self.allow_extended_hours:
                        await self._run_trading_cycle(extended_hours=True)
                    else:
                        self.current_cycle = "extended_hours_waiting"
                        await self._run_off_hours_cycle()
                    await asyncio.sleep(self.cycle_interval_seconds * 2)  # Slower during extended

                else:
                    # Unknown session - be cautious
                    self.current_cycle = "unknown_session"
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
        """Check existing positions for exit signals"""
        for pos in positions:
            symbol = pos["symbol"]

            try:
                # Get our tracked position data from database
                db = SessionLocal()
                db_position = db.query(Position).filter(Position.symbol == symbol).first()
                db.close()

                if not db_position:
                    logger.warning(f"Position {symbol} not in database, skipping exit check")
                    continue

                # Get recent bars
                bars = await self.alpaca.get_bars(symbol, timeframe="1day", limit=100)

                if len(bars) < 20:
                    continue

                prices = [b["close"] for b in bars]
                highs = [b["high"] for b in bars]
                lows = [b["low"] for b in bars]
                volumes = [b["volume"] for b in bars]

                # Calculate days held
                entry_time = db_position.entry_time
                days_held = (datetime.now() - entry_time).days

                # Check exit conditions
                should_exit, exit_reason = self.strategy.should_exit(
                    symbol=symbol,
                    entry_price=db_position.entry_price,
                    current_price=pos["current_price"],
                    stop_loss=db_position.stop_loss_price or db_position.entry_price * 0.95,
                    profit_target=db_position.profit_target_price or db_position.entry_price * 1.10,
                    trade_type=TradeType(db_position.trade_type) if db_position.trade_type else TradeType.SWING,
                    entry_time_days=days_held,
                    prices=prices,
                    highs=highs,
                    lows=lows,
                    volumes=volumes,
                )

                if should_exit:
                    await self._execute_exit(symbol, pos["quantity"], exit_reason)

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
        }


# Global bot instance
_trading_bot: Optional[TradingBot] = None


def get_trading_bot(paper_trading: bool = False) -> TradingBot:
    """Get or create trading bot singleton"""
    global _trading_bot
    if _trading_bot is None:
        _trading_bot = TradingBot(paper_trading=paper_trading)
    return _trading_bot
