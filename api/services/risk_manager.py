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
