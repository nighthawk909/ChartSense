"""
SQLAlchemy ORM models for ChartSense Trading Bot
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum

from .connection import Base


class TradeType(str, enum.Enum):
    """Type of trade based on holding period"""
    SWING = "SWING"  # Hold days to 2 weeks
    LONG_TERM = "LONG_TERM"  # Hold weeks to months


class OrderSide(str, enum.Enum):
    """Buy or sell"""
    BUY = "BUY"
    SELL = "SELL"


class ExitReason(str, enum.Enum):
    """Reason for exiting a position"""
    PROFIT_TARGET = "PROFIT_TARGET"
    STOP_LOSS = "STOP_LOSS"
    SIGNAL = "SIGNAL"  # Technical signal reversal
    MANUAL = "MANUAL"  # User manually closed
    TIME_STOP = "TIME_STOP"  # Held too long with minimal gain


class BotState(str, enum.Enum):
    """Trading bot operational state"""
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class Trade(Base):
    """
    Completed trades table.
    Records all trades executed by the bot for performance tracking.
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)

    # Entry details
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    entry_order_id = Column(String(50))

    # Exit details (nullable until position is closed)
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    exit_order_id = Column(String(50))
    exit_reason = Column(String(20))  # PROFIT_TARGET, STOP_LOSS, SIGNAL, MANUAL, TIME_STOP

    # Results
    profit_loss = Column(Float)  # Dollar P&L
    profit_loss_pct = Column(Float)  # Percentage P&L

    # Strategy metadata
    strategy_name = Column(String(50), default="default")
    trade_type = Column(String(20))  # SWING, LONG_TERM
    entry_score = Column(Float)  # Confidence score at entry (0-100)

    # Snapshot of indicators at entry for analysis
    indicators_snapshot = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Trade {self.id}: {self.symbol} {self.side} {self.quantity}@{self.entry_price}>"


class Position(Base):
    """
    Currently open positions tracked by the bot.
    Synced with Alpaca but includes our strategy metadata.
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False)

    # Price targets
    stop_loss_price = Column(Float)
    profit_target_price = Column(Float)
    trailing_stop_pct = Column(Float)  # Trailing stop percentage (if activated)

    # Strategy info
    trade_type = Column(String(20))  # SWING, LONG_TERM
    strategy_name = Column(String(50), default="default")
    entry_score = Column(Float)  # Confidence score at entry

    # Current status (updated periodically)
    current_price = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_pct = Column(Float)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Position {self.symbol}: {self.quantity}@{self.entry_price}>"


class PerformanceMetric(Base):
    """
    Daily/periodic performance snapshots.
    Used for equity curve, performance tracking, and self-optimization.
    """
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)

    # Account metrics
    account_equity = Column(Float)
    account_cash = Column(Float)
    buying_power = Column(Float)

    # Trade counts
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float)  # winning_trades / total_trades

    # P&L metrics
    daily_pnl = Column(Float)  # Today's P&L
    cumulative_pnl = Column(Float)  # Total P&L since inception

    # Risk metrics
    max_drawdown = Column(Float)  # Maximum drawdown percentage
    sharpe_ratio = Column(Float)  # Risk-adjusted return
    profit_factor = Column(Float)  # Gross profit / gross loss

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<PerformanceMetric {self.date}: equity={self.account_equity}, win_rate={self.win_rate}>"


class BotConfiguration(Base):
    """
    Trading bot configuration and settings.
    Allows multiple configurations (presets) with one active at a time.
    """
    __tablename__ = "bot_configuration"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), default="default", unique=True)

    # Symbols to trade
    enabled_symbols = Column(JSON, default=list)  # ["AAPL", "MSFT", "GOOGL", ...]

    # Position limits
    max_positions = Column(Integer, default=5)
    max_position_size_pct = Column(Float, default=0.20)  # 20% max per position

    # Risk management
    risk_per_trade_pct = Column(Float, default=0.02)  # 2% risk per trade
    max_daily_loss_pct = Column(Float, default=0.03)  # 3% daily loss limit
    default_stop_loss_pct = Column(Float, default=0.05)  # 5% default stop

    # Strategy parameters
    entry_score_threshold = Column(Float, default=70.0)  # Min score to enter
    swing_profit_target_pct = Column(Float, default=0.08)  # 8% profit target for swing
    longterm_profit_target_pct = Column(Float, default=0.15)  # 15% for long-term

    # Indicator weights for scoring (JSON dict)
    indicator_weights = Column(JSON, default=dict)

    # Bot behavior
    trading_hours_only = Column(Boolean, default=True)  # Only trade during market hours
    paper_trading = Column(Boolean, default=False)  # Paper trading mode

    # Self-optimization settings
    auto_optimize = Column(Boolean, default=True)  # Enable self-optimization
    optimization_lookback_days = Column(Integer, default=30)  # Days to analyze

    # Active flag
    is_active = Column(Boolean, default=True)  # Currently active configuration

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<BotConfiguration {self.name}: active={self.is_active}>"


class OptimizationLog(Base):
    """
    Log of self-optimization parameter adjustments.
    Tracks what the AI changed and why for analysis.
    """
    __tablename__ = "optimization_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)

    # What changed
    parameter_name = Column(String(50), nullable=False)
    old_value = Column(Float)
    new_value = Column(Float)

    # Why it changed
    reason = Column(String(500))

    # Performance data that triggered the change
    performance_context = Column(JSON)  # Metrics at time of change

    # Was this change applied?
    applied = Column(Boolean, default=True)

    def __repr__(self):
        return f"<OptimizationLog {self.parameter_name}: {self.old_value} -> {self.new_value}>"


class StockSource(str, enum.Enum):
    """Source of a stock in the repository"""
    USER = "USER"  # User-added stock
    AI_DISCOVERED = "AI_DISCOVERED"  # AI found this stock
    PERFORMANCE = "PERFORMANCE"  # Added based on good performance


class StockRepository(Base):
    """
    Repository of stocks that the bot can trade.
    Combines user picks, AI discoveries, and proven performers.
    The bot maintains this list and prioritizes based on readiness.
    """
    __tablename__ = "stock_repository"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    name = Column(String(100))  # Company name

    # Source and priority
    source = Column(String(20), default="USER")  # USER, AI_DISCOVERED, PERFORMANCE
    priority = Column(Integer, default=5)  # 1-10, higher = more priority

    # Trading characteristics
    trade_type = Column(String(20))  # SWING, LONG_TERM, BOTH
    sector = Column(String(50))
    risk_level = Column(String(10), default="MEDIUM")  # LOW, MEDIUM, HIGH

    # AI analysis data
    ai_reason = Column(String(500))  # Why AI picked this stock
    last_analysis_score = Column(Float)  # Last entry signal score
    last_analysis_time = Column(DateTime)

    # Performance metrics for this stock
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    avg_return_pct = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)  # Currently in rotation
    is_tradeable = Column(Boolean, default=True)  # Meets entry criteria
    last_traded = Column(DateTime)
    notes = Column(String(500))  # User notes

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<StockRepository {self.symbol}: source={self.source}, priority={self.priority}>"


class UserWatchlist(Base):
    """
    User's personal watchlist - stocks they want the bot to always consider.
    These have highest priority for the bot.
    """
    __tablename__ = "user_watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    name = Column(String(100))

    # User preferences
    notes = Column(String(500))
    target_buy_price = Column(Float)  # User's desired entry price
    target_sell_price = Column(Float)  # User's desired exit price

    # Bot behavior for this stock
    auto_trade = Column(Boolean, default=True)  # Let bot trade this automatically
    max_position_pct = Column(Float, default=0.20)  # Max % of portfolio for this stock

    # Timestamps
    added_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<UserWatchlist {self.symbol}: auto_trade={self.auto_trade}>"
