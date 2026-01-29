"""
Pydantic models for Trading Bot API
Request/Response models for bot endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============== Enums ==============

class BotState(str, Enum):
    """Trading bot operational state"""
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class TradeType(str, Enum):
    """Type of trade based on holding period"""
    SCALP = "SCALP"        # < 5 minutes
    INTRADAY = "INTRADAY"  # Same day, < 1 hour
    SWING = "SWING"        # 1-5 days
    LONG_TERM = "LONG_TERM"  # > 5 days


class OrderSide(str, Enum):
    """Buy or sell"""
    BUY = "BUY"
    SELL = "SELL"


class ExitReason(str, Enum):
    """Reason for exiting a position"""
    PROFIT_TARGET = "PROFIT_TARGET"
    STOP_LOSS = "STOP_LOSS"
    SIGNAL = "SIGNAL"
    MANUAL = "MANUAL"
    TIME_STOP = "TIME_STOP"


# ============== Bot Status ==============

class CryptoAnalysisResult(BaseModel):
    """Result of crypto analysis for a single symbol"""
    signal: str  # BUY, SELL, NEUTRAL, NO_DATA
    confidence: float
    threshold: float
    meets_threshold: bool = False
    reason: str
    timestamp: str
    indicators: Dict[str, Any] = {}
    signals: List[str] = []  # Technical signals detected


class AIDecisionResult(BaseModel):
    """AI decision result for a trade"""
    decision: str  # APPROVE, REJECT, WAIT
    confidence: float = 0
    reasoning: str = ""
    concerns: List[str] = []
    timestamp: str = ""
    symbol: str = ""
    ai_generated: bool = True
    model: str = "gpt-4"
    technical_score: float = 0
    technical_signal: str = ""


class StockAnalysisResult(BaseModel):
    """Result of stock analysis for a single symbol"""
    signal: str  # BUY, SELL, NEUTRAL
    confidence: float
    threshold: float
    meets_threshold: bool = False
    reason: str
    timestamp: str
    indicators: Dict[str, Any] = {}
    current_price: Optional[float] = None
    trade_type: Optional[str] = None
    ai_decision: Optional[AIDecisionResult] = None  # AI's decision on this trade


class CryptoBestOpportunity(BaseModel):
    """Best crypto opportunity found during scan"""
    symbol: str
    confidence: float
    threshold: float
    meets_threshold: bool


class CryptoScanProgress(BaseModel):
    """Progress tracking for crypto scanning cycle"""
    total: int = 0
    scanned: int = 0
    current_symbol: Optional[str] = None
    signals_found: int = 0
    best_opportunity: Optional[CryptoBestOpportunity] = None
    scan_status: str = "idle"  # idle, scanning, exhausted, found_opportunity
    scan_summary: str = ""
    last_scan_completed: Optional[str] = None
    next_scan_in_seconds: int = 0


class StockBestOpportunity(BaseModel):
    """Best stock opportunity found during scan"""
    symbol: str
    confidence: float
    threshold: float
    meets_threshold: bool


class StockScanProgress(BaseModel):
    """Progress tracking for stock scanning cycle"""
    total: int = 0
    scanned: int = 0
    current_symbol: Optional[str] = None
    signals_found: int = 0
    best_opportunity: Optional[StockBestOpportunity] = None
    scan_status: str = "idle"  # idle, scanning, exhausted, found_opportunity, market_closed, disabled
    scan_summary: str = ""
    last_scan_completed: Optional[str] = None
    next_scan_in_seconds: int = 0
    market_status: str = "unknown"  # regular, extended, pre_market, after_hours, overnight, weekend


class ExecutionLogEntry(BaseModel):
    """Entry in the execution log"""
    timestamp: str
    symbol: str
    event_type: str  # ENTRY_EXECUTED, EXIT_EXECUTED, ENTRY_SKIPPED, AI_REJECTED, etc.
    executed: bool
    reason: str
    details: Dict[str, Any] = {}


class BotStatusResponse(BaseModel):
    """Current bot status"""
    state: BotState
    uptime_seconds: int = 0
    last_trade_time: Optional[datetime] = None
    current_cycle: str = "idle"  # What the bot is currently doing
    current_session: Optional[str] = None  # pre_market, regular, after_hours, overnight, weekend
    error_message: Optional[str] = None
    paper_trading: bool = True
    active_symbols: List[str] = []
    # Asset Class Mode
    asset_class_mode: str = "both"  # crypto, stocks, both
    # Auto Trade Mode
    auto_trade_mode: Optional[bool] = False
    ai_risk_tolerance: Optional[str] = "moderate"
    # Entry threshold (important for understanding why signals aren't traded)
    entry_threshold: Optional[float] = 65.0
    # Crypto trading status
    crypto_trading_enabled: bool = False
    crypto_symbols: List[str] = []
    crypto_max_positions: int = 5
    crypto_positions: int = 0
    crypto_analysis_results: Dict[str, CryptoAnalysisResult] = {}
    last_crypto_analysis_time: Optional[str] = None
    # Crypto scan progress tracking
    crypto_scan_progress: Optional[CryptoScanProgress] = None
    # Stock scan progress tracking
    stock_scan_progress: Optional[StockScanProgress] = None
    # Stock analysis results (similar to crypto)
    stock_analysis_results: Dict[str, StockAnalysisResult] = {}
    last_stock_analysis_time: Optional[str] = None
    # Tactical Controls
    new_entries_paused: Optional[bool] = False
    strategy_override: Optional[str] = None
    # Execution tracking
    execution_log: List[ExecutionLogEntry] = []
    ai_decisions_history: List[AIDecisionResult] = []
    total_scans_today: int = 0


class BotStartRequest(BaseModel):
    """Request to start the bot"""
    paper_trading: Optional[bool] = None  # Override config
    symbols: Optional[List[str]] = None  # Override enabled symbols


class BotActionResponse(BaseModel):
    """Response for bot control actions"""
    success: bool
    message: str
    state: BotState


# ============== Account ==============

class AccountSummary(BaseModel):
    """Alpaca account summary"""
    equity: float = Field(..., description="Total account equity")
    cash: float = Field(..., description="Available cash")
    buying_power: float = Field(..., description="Available buying power")
    portfolio_value: float = Field(..., description="Value of all positions")
    unrealized_pnl: float = Field(0, description="Unrealized profit/loss")
    unrealized_pnl_pct: float = Field(0, description="Unrealized P&L percentage")
    day_pnl: float = Field(0, description="Today's profit/loss")
    day_pnl_pct: float = Field(0, description="Today's P&L percentage")


# ============== Positions ==============

class PositionResponse(BaseModel):
    """Current open position"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    profit_target: Optional[float] = None
    trade_type: Optional[TradeType] = None
    entry_time: Optional[datetime] = None  # Optional for positions not tracked in DB
    entry_score: Optional[float] = None
    asset_class: Optional[str] = None  # 'stock' or 'crypto'
    # NEW: Entry insight fields for position details modal
    entry_reason: Optional[str] = None  # Human-readable reason why we entered
    indicators_snapshot: Optional[Dict[str, Any]] = None  # Technical indicators at entry
    confluence_factors: Optional[List[str]] = None  # List of confirming technical factors


class PositionsListResponse(BaseModel):
    """List of current positions"""
    positions: List[PositionResponse]
    total_value: float
    total_unrealized_pnl: float


class ClosePositionRequest(BaseModel):
    """Request to close a position"""
    symbol: str
    quantity: Optional[float] = None  # None = close entire position


class ClosePositionResponse(BaseModel):
    """Response after closing a position"""
    success: bool
    message: str
    symbol: str
    quantity_closed: float
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None


# ============== Trades / History ==============

class TradeResponse(BaseModel):
    """Completed trade record"""
    id: int
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    trade_type: Optional[TradeType] = None
    entry_score: Optional[float] = None


class TradeHistoryResponse(BaseModel):
    """Paginated trade history"""
    trades: List[TradeResponse]
    total_count: int
    page: int
    page_size: int


# ============== Performance ==============

class PerformanceSummary(BaseModel):
    """Quick performance summary"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0


class PerformanceMetrics(BaseModel):
    """Detailed performance metrics"""
    period_days: int
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    profit_factor: float = 0.0  # Gross profit / gross loss
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    expectancy: float = 0.0
    avg_trade_duration_hours: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    # Consecutive tracking
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    # By trade type
    swing_trades: int = 0
    swing_win_rate: float = 0.0
    longterm_trades: int = 0
    longterm_win_rate: float = 0.0


class EquityCurvePoint(BaseModel):
    """Single point on equity curve"""
    date: datetime
    equity: float
    pnl: float
    cumulative_pnl: float


class EquityCurveResponse(BaseModel):
    """Equity curve data for charting"""
    data: List[EquityCurvePoint]
    starting_equity: float
    current_equity: float
    total_return_pct: float


# ============== Settings ==============

class BotSettings(BaseModel):
    """Bot configuration settings"""
    # Symbols
    enabled_symbols: List[str] = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        description="Symbols the bot will trade"
    )

    # Position limits
    max_positions: int = Field(5, ge=1, le=20, description="Maximum concurrent positions")
    max_position_size_pct: float = Field(
        0.20, ge=0.05, le=0.50,
        description="Maximum position size as percentage of equity"
    )

    # Risk management
    risk_per_trade_pct: float = Field(
        0.02, ge=0.01, le=0.10,
        description="Risk per trade as percentage of equity"
    )
    max_daily_loss_pct: float = Field(
        0.03, ge=0.01, le=0.10,
        description="Maximum daily loss before bot pauses"
    )
    default_stop_loss_pct: float = Field(
        0.05, ge=0.01, le=0.20,
        description="Default stop loss percentage"
    )
    default_take_profit_pct: float = Field(
        0.10, ge=0.02, le=0.50,
        description="Default take profit percentage"
    )

    # Exit Strategies
    trailing_stop_enabled: bool = Field(
        False, description="Enable trailing stop loss"
    )
    trailing_stop_pct: float = Field(
        0.03, ge=0.01, le=0.10,
        description="Trailing stop percentage from peak"
    )
    trailing_stop_activation_pct: float = Field(
        0.05, ge=0.02, le=0.20,
        description="Profit percentage to activate trailing stop"
    )
    partial_profit_enabled: bool = Field(
        False, description="Enable partial profit taking"
    )
    partial_profit_pct: float = Field(
        0.50, ge=0.25, le=0.75,
        description="Portion of position to sell at partial target"
    )
    partial_profit_at: float = Field(
        0.05, ge=0.02, le=0.25,
        description="Profit percentage to trigger partial sell"
    )

    # Strategy parameters
    entry_score_threshold: float = Field(
        70.0, ge=50.0, le=95.0,
        description="Minimum score to enter a trade (0-100)"
    )
    swing_profit_target_pct: float = Field(
        0.08, ge=0.03, le=0.25,
        description="Profit target for swing trades"
    )
    longterm_profit_target_pct: float = Field(
        0.15, ge=0.05, le=0.50,
        description="Profit target for long-term trades"
    )

    # Behavior
    paper_trading: bool = Field(False, description="Use paper trading (simulated)")
    trading_hours_only: bool = Field(True, description="Only trade during market hours")
    auto_optimize: bool = Field(True, description="Enable self-optimization")

    # Profit Reinvestment
    reinvest_profits: bool = Field(
        True, description="Reinvest profits back into trading"
    )
    compounding_enabled: bool = Field(
        True, description="Enable compound growth (increase position sizes with equity growth)"
    )

    # Intraday Trading
    intraday_enabled: bool = Field(
        False, description="Enable intraday (day trading) mode"
    )
    intraday_timeframe: str = Field(
        "5min", description="Timeframe for intraday analysis (1min, 5min, 15min, 30min, 1hour)"
    )
    max_trades_per_day: int = Field(
        10, ge=1, le=50, description="Maximum trades per day in intraday mode"
    )

    # Auto Trade Mode (AI controlled)
    auto_trade_mode: bool = Field(
        False, description="Let AI control trading parameters"
    )
    ai_risk_tolerance: str = Field(
        "moderate", description="AI risk tolerance (conservative, moderate, aggressive)"
    )

    # Broker
    broker: str = Field(
        "alpaca", description="Active broker (alpaca, robinhood, fidelity)"
    )

    # Crypto Trading
    crypto_trading_enabled: bool = Field(
        False, description="Enable cryptocurrency trading (24/7)"
    )
    crypto_symbols: List[str] = Field(
        default=["BTC/USD", "ETH/USD"],
        description="Crypto pairs to trade"
    )
    crypto_max_positions: int = Field(
        2, ge=1, le=10, description="Maximum concurrent crypto positions"
    )


class BotSettingsResponse(BaseModel):
    """Settings response with metadata"""
    settings: BotSettings
    config_name: str = "default"
    last_updated: Optional[datetime] = None


class UpdateSettingsRequest(BaseModel):
    """Request to update settings"""
    settings: BotSettings


# ============== Optimization ==============

class OptimizationSuggestion(BaseModel):
    """AI-suggested parameter adjustment"""
    parameter: str
    current_value: float
    suggested_value: float
    reason: str
    expected_impact: str


class OptimizationLogEntry(BaseModel):
    """Log entry for an optimization change"""
    timestamp: datetime
    parameter: str
    old_value: float
    new_value: float
    reason: str
    applied: bool


class OptimizationHistoryResponse(BaseModel):
    """History of optimization changes"""
    entries: List[OptimizationLogEntry]
    total_adjustments: int


# ============== Trading Signals (internal) ==============

class TradingSignal(BaseModel):
    """Generated trading signal"""
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    score: float  # 0-100 confidence
    trade_type: TradeType
    suggested_entry: float
    suggested_stop_loss: float
    suggested_profit_target: float
    indicators: Dict[str, Any]
    reason: str
