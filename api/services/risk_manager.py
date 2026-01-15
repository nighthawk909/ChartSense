"""
Risk Manager for Trading Bot
Handles position sizing, stop-losses, and risk limits
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, date

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    shares: int
    position_value: float
    risk_amount: float
    risk_per_share: float
    limited_by: str  # What limited the position size


@dataclass
class RiskCheckResult:
    """Result of risk check"""
    can_trade: bool
    reason: str
    available_capital: float
    current_exposure: float


class RiskManager:
    """
    Manages risk for the trading bot.
    Controls position sizing, enforces limits, and tracks daily losses.
    """

    def __init__(
        self,
        max_positions: int = 5,
        max_position_size_pct: float = 0.20,
        risk_per_trade_pct: float = 0.02,
        max_daily_loss_pct: float = 0.03,
        default_stop_loss_pct: float = 0.05,
    ):
        """
        Initialize risk manager.

        Args:
            max_positions: Maximum number of concurrent positions
            max_position_size_pct: Maximum size of single position (% of equity)
            risk_per_trade_pct: Risk per trade (% of equity)
            max_daily_loss_pct: Maximum daily loss before stopping (% of equity)
            default_stop_loss_pct: Default stop-loss percentage
        """
        self.max_positions = max_positions
        self.max_position_size_pct = max_position_size_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.default_stop_loss_pct = default_stop_loss_pct

        # Daily tracking
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._last_reset_date: Optional[date] = None
        self._starting_equity: float = 0.0

    def calculate_position_size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss_price: float,
        current_positions: int = 0,
    ) -> PositionSizeResult:
        """
        Calculate position size using fixed fractional risk model.

        The position size is determined by:
        1. Risk amount = equity * risk_per_trade_pct
        2. Risk per share = entry_price - stop_loss_price
        3. Shares = risk_amount / risk_per_share
        4. Limited by max_position_size_pct

        Args:
            account_equity: Total account equity
            entry_price: Intended entry price
            stop_loss_price: Stop-loss price
            current_positions: Number of current open positions

        Returns:
            PositionSizeResult with calculated shares and details
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return PositionSizeResult(
                shares=0,
                position_value=0,
                risk_amount=0,
                risk_per_share=0,
                limited_by="invalid_prices"
            )

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            # Default to percentage-based stop if no valid stop provided
            risk_per_share = entry_price * self.default_stop_loss_pct

        # Calculate max risk amount for this trade
        max_risk_amount = account_equity * self.risk_per_trade_pct

        # Shares based on risk
        shares_by_risk = int(max_risk_amount / risk_per_share)

        # Calculate max position value
        max_position_value = account_equity * self.max_position_size_pct

        # Shares based on max position size
        shares_by_position = int(max_position_value / entry_price)

        # Check remaining capital allocation
        # If we have many positions, reduce allocation for new ones
        remaining_allocation_pct = 1.0 - (current_positions * self.max_position_size_pct)
        remaining_allocation_pct = max(0.1, remaining_allocation_pct)  # At least 10%
        shares_by_allocation = int((account_equity * remaining_allocation_pct) / entry_price)

        # Take the minimum to respect all limits
        final_shares = min(shares_by_risk, shares_by_position, shares_by_allocation)

        # Ensure at least 1 share if we can afford it
        if final_shares == 0 and account_equity >= entry_price:
            final_shares = 1

        # Determine what limited us
        if final_shares == shares_by_risk:
            limited_by = "risk_per_trade"
        elif final_shares == shares_by_position:
            limited_by = "max_position_size"
        elif final_shares == shares_by_allocation:
            limited_by = "remaining_allocation"
        else:
            limited_by = "insufficient_funds"

        position_value = final_shares * entry_price
        actual_risk = final_shares * risk_per_share

        logger.info(
            f"Position size calculated: {final_shares} shares @ ${entry_price:.2f} "
            f"(value: ${position_value:.2f}, risk: ${actual_risk:.2f}, limited_by: {limited_by})"
        )

        return PositionSizeResult(
            shares=final_shares,
            position_value=position_value,
            risk_amount=actual_risk,
            risk_per_share=risk_per_share,
            limited_by=limited_by,
        )

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: Optional[float] = None,
        is_swing_trade: bool = True,
    ) -> float:
        """
        Calculate stop-loss price.

        Args:
            entry_price: Entry price
            atr: Average True Range (for ATR-based stops)
            is_swing_trade: If True, use tighter stops for swing trades

        Returns:
            Stop-loss price
        """
        if atr and atr > 0:
            # ATR-based stop (2x ATR for swing, 2.5x for long-term)
            multiplier = 2.0 if is_swing_trade else 2.5
            stop_loss = entry_price - (atr * multiplier)

            # Ensure stop is at least minimum percentage away
            min_stop = entry_price * (1 - self.default_stop_loss_pct)
            stop_loss = max(stop_loss, min_stop)

            # Cap stop loss at reasonable level (not more than 10% away)
            max_stop = entry_price * 0.90
            stop_loss = max(stop_loss, max_stop)
        else:
            # Percentage-based stop
            stop_pct = 0.04 if is_swing_trade else self.default_stop_loss_pct
            stop_loss = entry_price * (1 - stop_pct)

        return round(stop_loss, 2)

    def can_open_position(
        self,
        account_equity: float,
        buying_power: float,
        current_positions: List[Dict[str, Any]],
        entry_price: float,
        position_value: float,
    ) -> RiskCheckResult:
        """
        Check if we can open a new position based on risk limits.

        Args:
            account_equity: Total account equity
            buying_power: Available buying power
            current_positions: List of current positions
            entry_price: Intended entry price
            position_value: Intended position value

        Returns:
            RiskCheckResult with approval and reasoning
        """
        num_positions = len(current_positions)

        # Check position count limit
        if num_positions >= self.max_positions:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Maximum positions reached ({self.max_positions})",
                available_capital=buying_power,
                current_exposure=self._calculate_exposure(current_positions),
            )

        # Check buying power
        if position_value > buying_power:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Insufficient buying power (need ${position_value:.2f}, have ${buying_power:.2f})",
                available_capital=buying_power,
                current_exposure=self._calculate_exposure(current_positions),
            )

        # Check daily loss limit
        self._reset_daily_if_needed(account_equity)
        if self._daily_pnl < -(account_equity * self.max_daily_loss_pct):
            return RiskCheckResult(
                can_trade=False,
                reason=f"Daily loss limit reached (${self._daily_pnl:.2f})",
                available_capital=buying_power,
                current_exposure=self._calculate_exposure(current_positions),
            )

        # Check total exposure
        current_exposure = self._calculate_exposure(current_positions)
        new_exposure = current_exposure + position_value
        max_exposure = account_equity * 0.80  # Max 80% exposure

        if new_exposure > max_exposure:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Would exceed max exposure (${new_exposure:.2f} > ${max_exposure:.2f})",
                available_capital=buying_power,
                current_exposure=current_exposure,
            )

        # Check position size limit
        if position_value > account_equity * self.max_position_size_pct:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Position too large (${position_value:.2f} > {self.max_position_size_pct*100:.0f}% of equity)",
                available_capital=buying_power,
                current_exposure=current_exposure,
            )

        return RiskCheckResult(
            can_trade=True,
            reason="All risk checks passed",
            available_capital=buying_power,
            current_exposure=current_exposure,
        )

    def _calculate_exposure(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate total exposure from positions"""
        return sum(pos.get("market_value", 0) for pos in positions)

    def _reset_daily_if_needed(self, account_equity: float):
        """Reset daily tracking if it's a new day"""
        today = date.today()
        if self._last_reset_date != today:
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._last_reset_date = today
            self._starting_equity = account_equity
            logger.info(f"Daily risk counters reset. Starting equity: ${account_equity:.2f}")

    def record_trade_pnl(self, pnl: float):
        """Record a trade's P&L for daily tracking"""
        self._daily_pnl += pnl
        self._daily_trades += 1
        logger.info(f"Trade recorded: P&L ${pnl:.2f}, Daily total: ${self._daily_pnl:.2f}")

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get current daily statistics"""
        return {
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trades,
            "starting_equity": self._starting_equity,
            "last_reset": self._last_reset_date.isoformat() if self._last_reset_date else None,
        }

    def is_daily_loss_limit_hit(self, account_equity: float) -> bool:
        """Check if daily loss limit has been hit"""
        self._reset_daily_if_needed(account_equity)
        max_loss = account_equity * self.max_daily_loss_pct
        return self._daily_pnl < -max_loss

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        current_stop: float,
        trailing_pct: float = 0.03,
    ) -> float:
        """
        Calculate trailing stop price.

        The trailing stop moves up as price increases but never moves down.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            current_stop: Current stop-loss price
            trailing_pct: Trailing percentage (default 3%)

        Returns:
            New stop-loss price (may be same as current if price hasn't moved up)
        """
        # Calculate new potential stop based on current price
        new_stop = current_price * (1 - trailing_pct)

        # Only move stop up, never down
        if new_stop > current_stop:
            logger.info(f"Trailing stop updated: ${current_stop:.2f} -> ${new_stop:.2f}")
            return round(new_stop, 2)

        return current_stop

    def should_activate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        profit_threshold_pct: float = 0.05,
    ) -> bool:
        """
        Determine if we should activate trailing stop.

        Trailing stops are typically activated after reaching a certain profit level.

        Args:
            entry_price: Original entry price
            current_price: Current market price
            profit_threshold_pct: Profit level to activate trailing stop

        Returns:
            True if trailing stop should be activated
        """
        pnl_pct = (current_price - entry_price) / entry_price
        return pnl_pct >= profit_threshold_pct

    def update_parameters(
        self,
        max_positions: Optional[int] = None,
        max_position_size_pct: Optional[float] = None,
        risk_per_trade_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
        default_stop_loss_pct: Optional[float] = None,
    ):
        """Update risk parameters (used by optimizer)"""
        if max_positions is not None:
            self.max_positions = max_positions
        if max_position_size_pct is not None:
            self.max_position_size_pct = max_position_size_pct
        if risk_per_trade_pct is not None:
            self.risk_per_trade_pct = risk_per_trade_pct
        if max_daily_loss_pct is not None:
            self.max_daily_loss_pct = max_daily_loss_pct
        if default_stop_loss_pct is not None:
            self.default_stop_loss_pct = default_stop_loss_pct

        logger.info(
            f"Risk parameters updated: max_positions={self.max_positions}, "
            f"max_position_size={self.max_position_size_pct}, risk_per_trade={self.risk_per_trade_pct}"
        )

    # ==================== ENHANCED RISK MANAGEMENT ====================

    def calculate_atr_position_size(
        self,
        account_equity: float,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.0,
        risk_pct: float = None,
    ) -> PositionSizeResult:
        """
        Calculate position size using ATR-based volatility adjustment.

        Uses ATR to set dynamic stop-loss distance, which determines position size.
        More volatile stocks get smaller positions.

        Args:
            account_equity: Total account equity
            entry_price: Intended entry price
            atr: Average True Range value
            atr_multiplier: How many ATRs to use for stop (default 2.0)
            risk_pct: Risk percentage (defaults to self.risk_per_trade_pct)
        """
        if atr <= 0 or entry_price <= 0:
            return PositionSizeResult(
                shares=0,
                position_value=0,
                risk_amount=0,
                risk_per_share=0,
                limited_by="invalid_atr_or_price"
            )

        risk_pct = risk_pct or self.risk_per_trade_pct

        # Calculate stop distance based on ATR
        stop_distance = atr * atr_multiplier
        stop_loss_price = entry_price - stop_distance

        # Risk per share is the ATR-based stop distance
        risk_per_share = stop_distance

        # Calculate risk amount
        risk_amount = account_equity * risk_pct

        # Shares based on ATR risk
        shares = int(risk_amount / risk_per_share)

        # Apply position size cap
        max_position_value = account_equity * self.max_position_size_pct
        max_shares_by_cap = int(max_position_value / entry_price)
        shares = min(shares, max_shares_by_cap)

        # Ensure at least 1 share
        if shares == 0 and account_equity >= entry_price:
            shares = 1

        position_value = shares * entry_price
        actual_risk = shares * risk_per_share

        limited_by = "atr_risk" if shares == int(risk_amount / risk_per_share) else "position_cap"

        logger.info(
            f"ATR Position Size: {shares} shares, ATR=${atr:.2f}, "
            f"Stop Distance=${stop_distance:.2f}, Risk=${actual_risk:.2f}"
        )

        return PositionSizeResult(
            shares=shares,
            position_value=position_value,
            risk_amount=actual_risk,
            risk_per_share=risk_per_share,
            limited_by=limited_by,
        )


class DrawdownCircuitBreaker:
    """
    Circuit breaker that halts trading when drawdown exceeds thresholds.
    Protects capital during losing streaks.
    """

    def __init__(
        self,
        daily_max_drawdown_pct: float = 0.03,      # 3% daily max drawdown
        weekly_max_drawdown_pct: float = 0.07,     # 7% weekly max drawdown
        total_max_drawdown_pct: float = 0.15,      # 15% total max drawdown
        cooldown_hours: int = 24,                   # Hours to wait after trigger
    ):
        self.daily_max_drawdown_pct = daily_max_drawdown_pct
        self.weekly_max_drawdown_pct = weekly_max_drawdown_pct
        self.total_max_drawdown_pct = total_max_drawdown_pct
        self.cooldown_hours = cooldown_hours

        self._is_triggered = False
        self._trigger_time: Optional[datetime] = None
        self._trigger_reason: str = ""

        # Peak tracking
        self._daily_peak: float = 0
        self._weekly_peak: float = 0
        self._all_time_peak: float = 0

        self._last_daily_reset: Optional[date] = None
        self._week_start_equity: float = 0

    def update(self, current_equity: float) -> Dict[str, Any]:
        """
        Update circuit breaker with current equity.

        Args:
            current_equity: Current account equity

        Returns:
            Status dict with breaker state and metrics
        """
        today = date.today()

        # Daily reset
        if self._last_daily_reset != today:
            self._daily_peak = current_equity
            self._last_daily_reset = today

            # Weekly reset (Monday)
            if today.weekday() == 0:
                self._week_start_equity = current_equity
                self._weekly_peak = current_equity

        # Update peaks
        self._daily_peak = max(self._daily_peak, current_equity)
        self._weekly_peak = max(self._weekly_peak, current_equity)
        self._all_time_peak = max(self._all_time_peak, current_equity)

        # Calculate drawdowns
        daily_drawdown = (self._daily_peak - current_equity) / self._daily_peak if self._daily_peak > 0 else 0
        weekly_drawdown = (self._weekly_peak - current_equity) / self._weekly_peak if self._weekly_peak > 0 else 0
        total_drawdown = (self._all_time_peak - current_equity) / self._all_time_peak if self._all_time_peak > 0 else 0

        # Check for triggers
        if daily_drawdown >= self.daily_max_drawdown_pct:
            self._trigger("daily_drawdown", f"Daily drawdown {daily_drawdown*100:.1f}% exceeded {self.daily_max_drawdown_pct*100:.1f}%")
        elif weekly_drawdown >= self.weekly_max_drawdown_pct:
            self._trigger("weekly_drawdown", f"Weekly drawdown {weekly_drawdown*100:.1f}% exceeded {self.weekly_max_drawdown_pct*100:.1f}%")
        elif total_drawdown >= self.total_max_drawdown_pct:
            self._trigger("total_drawdown", f"Total drawdown {total_drawdown*100:.1f}% exceeded {self.total_max_drawdown_pct*100:.1f}%")

        # Check cooldown
        if self._is_triggered and self._trigger_time:
            hours_since_trigger = (datetime.now() - self._trigger_time).total_seconds() / 3600
            if hours_since_trigger >= self.cooldown_hours:
                self._reset()

        return {
            "is_triggered": self._is_triggered,
            "trigger_reason": self._trigger_reason,
            "trigger_time": self._trigger_time.isoformat() if self._trigger_time else None,
            "daily_drawdown_pct": daily_drawdown * 100,
            "weekly_drawdown_pct": weekly_drawdown * 100,
            "total_drawdown_pct": total_drawdown * 100,
            "daily_peak": self._daily_peak,
            "weekly_peak": self._weekly_peak,
            "all_time_peak": self._all_time_peak,
        }

    def _trigger(self, reason_type: str, message: str):
        """Trigger the circuit breaker"""
        if not self._is_triggered:
            self._is_triggered = True
            self._trigger_time = datetime.now()
            self._trigger_reason = message
            logger.warning(f"CIRCUIT BREAKER TRIGGERED: {message}")

    def _reset(self):
        """Reset the circuit breaker after cooldown"""
        self._is_triggered = False
        self._trigger_time = None
        self._trigger_reason = ""
        logger.info("Circuit breaker reset after cooldown period")

    def can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed"""
        if self._is_triggered:
            return False, self._trigger_reason
        return True, "Circuit breaker not triggered"


class SectorExposureManager:
    """
    Manages sector exposure limits to ensure diversification.
    Prevents over-concentration in any single sector.
    """

    # Stock to sector mapping (simplified - would use API in production)
    SECTOR_MAP = {
        # Technology
        "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
        "AMZN": "Technology", "META": "Technology", "NVDA": "Technology",
        "AMD": "Technology", "INTC": "Technology", "CRM": "Technology",
        "ORCL": "Technology", "ADBE": "Technology", "CSCO": "Technology",

        # Healthcare
        "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
        "ABBV": "Healthcare", "MRK": "Healthcare", "LLY": "Healthcare",

        # Financials
        "JPM": "Financials", "BAC": "Financials", "WFC": "Financials",
        "GS": "Financials", "MS": "Financials", "V": "Financials",
        "MA": "Financials", "AXP": "Financials",

        # Consumer
        "WMT": "Consumer", "KO": "Consumer", "PEP": "Consumer",
        "COST": "Consumer", "HD": "Consumer", "MCD": "Consumer",
        "NKE": "Consumer", "SBUX": "Consumer",

        # Energy
        "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
        "SLB": "Energy", "OXY": "Energy",

        # Industrials
        "CAT": "Industrials", "BA": "Industrials", "UPS": "Industrials",
        "HON": "Industrials", "GE": "Industrials",

        # Crypto (special sector)
        "BTCUSD": "Crypto", "ETHUSD": "Crypto", "SOLUSD": "Crypto",
        "BTC/USD": "Crypto", "ETH/USD": "Crypto", "SOL/USD": "Crypto",
    }

    def __init__(self, max_sector_exposure_pct: float = 0.35):
        """
        Args:
            max_sector_exposure_pct: Maximum portfolio allocation to any single sector
        """
        self.max_sector_exposure_pct = max_sector_exposure_pct

    def get_sector(self, symbol: str) -> str:
        """Get sector for a symbol"""
        return self.SECTOR_MAP.get(symbol.upper(), "Unknown")

    def calculate_sector_exposure(
        self,
        positions: List[Dict[str, Any]],
        total_equity: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate current exposure by sector.

        Returns dict with sector exposures and percentages.
        """
        sector_exposure = {}

        for pos in positions:
            symbol = pos.get("symbol", "")
            market_value = pos.get("market_value", 0)
            sector = self.get_sector(symbol)

            if sector not in sector_exposure:
                sector_exposure[sector] = {
                    "value": 0,
                    "symbols": [],
                    "count": 0,
                }

            sector_exposure[sector]["value"] += market_value
            sector_exposure[sector]["symbols"].append(symbol)
            sector_exposure[sector]["count"] += 1

        # Calculate percentages
        for sector in sector_exposure:
            sector_exposure[sector]["percentage"] = (
                sector_exposure[sector]["value"] / total_equity * 100
                if total_equity > 0 else 0
            )
            sector_exposure[sector]["at_limit"] = (
                sector_exposure[sector]["percentage"] >= self.max_sector_exposure_pct * 100
            )

        return sector_exposure

    def can_add_to_sector(
        self,
        symbol: str,
        position_value: float,
        positions: List[Dict[str, Any]],
        total_equity: float
    ) -> tuple[bool, str]:
        """
        Check if adding a position would exceed sector limits.

        Returns:
            (allowed, reason)
        """
        sector = self.get_sector(symbol)
        current_exposure = self.calculate_sector_exposure(positions, total_equity)

        current_sector_value = current_exposure.get(sector, {}).get("value", 0)
        new_sector_value = current_sector_value + position_value
        new_sector_pct = new_sector_value / total_equity if total_equity > 0 else 0

        if new_sector_pct > self.max_sector_exposure_pct:
            return False, f"Would exceed {sector} sector limit ({new_sector_pct*100:.1f}% > {self.max_sector_exposure_pct*100:.0f}%)"

        return True, f"Sector exposure OK ({new_sector_pct*100:.1f}%)"


class CorrelationRiskManager:
    """
    Manages correlation risk between positions.
    Prevents over-concentration in correlated assets.
    """

    # Simplified correlation groups (assets that tend to move together)
    CORRELATION_GROUPS = {
        "big_tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        "semiconductors": ["NVDA", "AMD", "INTC", "AVGO", "QCOM"],
        "banks": ["JPM", "BAC", "WFC", "C", "GS"],
        "energy": ["XOM", "CVX", "COP", "SLB", "OXY"],
        "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
        "crypto": ["BTCUSD", "ETHUSD", "SOLUSD", "BTC/USD", "ETH/USD", "SOL/USD"],
        "consumer_staples": ["WMT", "KO", "PEP", "PG", "COST"],
    }

    def __init__(self, max_correlated_positions: int = 3):
        """
        Args:
            max_correlated_positions: Max positions from the same correlation group
        """
        self.max_correlated_positions = max_correlated_positions

        # Build reverse lookup
        self._symbol_to_group = {}
        for group, symbols in self.CORRELATION_GROUPS.items():
            for symbol in symbols:
                self._symbol_to_group[symbol.upper()] = group

    def get_correlation_group(self, symbol: str) -> Optional[str]:
        """Get correlation group for a symbol"""
        return self._symbol_to_group.get(symbol.upper())

    def check_correlation_risk(
        self,
        symbol: str,
        positions: List[Dict[str, Any]]
    ) -> tuple[bool, str, List[str]]:
        """
        Check if adding a position would create too much correlation risk.

        Returns:
            (allowed, reason, correlated_symbols)
        """
        group = self.get_correlation_group(symbol)

        if not group:
            return True, "No known correlation group", []

        # Find existing positions in same correlation group
        correlated = []
        for pos in positions:
            pos_symbol = pos.get("symbol", "").upper()
            if self.get_correlation_group(pos_symbol) == group:
                correlated.append(pos_symbol)

        if len(correlated) >= self.max_correlated_positions:
            return False, f"Already have {len(correlated)} positions in {group} group", correlated

        return True, f"Correlation OK ({len(correlated)} existing in {group})", correlated

    def get_portfolio_correlation_report(
        self,
        positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate correlation risk report for current portfolio.
        """
        group_counts = {}

        for pos in positions:
            symbol = pos.get("symbol", "").upper()
            group = self.get_correlation_group(symbol)

            if group:
                if group not in group_counts:
                    group_counts[group] = {"count": 0, "symbols": [], "value": 0}
                group_counts[group]["count"] += 1
                group_counts[group]["symbols"].append(symbol)
                group_counts[group]["value"] += pos.get("market_value", 0)

        # Identify high-risk concentrations
        high_risk_groups = [
            group for group, data in group_counts.items()
            if data["count"] >= self.max_correlated_positions
        ]

        return {
            "group_breakdown": group_counts,
            "high_risk_groups": high_risk_groups,
            "diversification_score": self._calculate_diversification_score(group_counts),
        }

    def _calculate_diversification_score(self, group_counts: Dict) -> float:
        """
        Calculate portfolio diversification score (0-100).
        Higher = more diversified.
        """
        if not group_counts:
            return 100  # Empty portfolio is fully diversified

        total_positions = sum(g["count"] for g in group_counts.values())
        num_groups = len(group_counts)

        if total_positions == 0:
            return 100

        # Perfect diversification = equal distribution across groups
        # Penalize concentration in any group
        max_in_group = max(g["count"] for g in group_counts.values())
        concentration_penalty = (max_in_group / total_positions) * 50

        # Reward having more groups
        group_bonus = min(num_groups * 10, 50)

        score = 100 - concentration_penalty + group_bonus
        return max(0, min(100, score))
