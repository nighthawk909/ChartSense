"""
Simulated portfolio for backtesting.

Tracks positions, cash, and equity through a backtest simulation.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from models.backtest import Signal, SimulatedTrade, EquityPoint

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """An open position in the portfolio."""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class SimulatedPortfolio:
    """
    Simulates a trading portfolio for backtesting.

    Tracks:
    - Cash balance
    - Open positions
    - Trade history
    - Equity curve over time
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        position_size_pct: float = 10.0,
        commission_per_trade: float = 0.0,
    ):
        """
        Initialize the portfolio.

        Args:
            initial_capital: Starting cash
            position_size_pct: Default position size as % of equity
            commission_per_trade: Commission charged per trade
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position_size_pct = position_size_pct
        self.commission = commission_per_trade

        self.positions: Dict[str, Position] = {}
        self.trades: List[SimulatedTrade] = []
        self.equity_curve: List[EquityPoint] = []

        self._current_prices: Dict[str, float] = {}

    @property
    def positions_value(self) -> float:
        """Total value of all open positions at current prices."""
        total = 0.0
        for symbol, pos in self.positions.items():
            price = self._current_prices.get(symbol, pos.entry_price)
            total += pos.quantity * price
        return total

    @property
    def equity(self) -> float:
        """Total portfolio value (cash + positions)."""
        return self.cash + self.positions_value

    def update_prices(self, bars: Dict[str, "Bar"]) -> None:
        """
        Update current prices from bars.

        Args:
            bars: Dict of symbol -> Bar with current prices
        """
        for symbol, bar in bars.items():
            self._current_prices[symbol] = bar.close

    def record_equity(self, timestamp: datetime) -> None:
        """Record current equity to the equity curve."""
        self.equity_curve.append(EquityPoint(
            timestamp=timestamp,
            equity=self.equity,
            cash=self.cash,
            positions_value=self.positions_value
        ))

    def calculate_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate position size based on portfolio settings.

        Args:
            symbol: Stock symbol
            price: Current price

        Returns:
            Number of shares to buy
        """
        # Position size as % of current equity
        position_value = self.equity * (self.position_size_pct / 100)

        # Don't use more than available cash
        position_value = min(position_value, self.cash)

        # Calculate shares
        shares = position_value / price

        # Round to whole shares for simplicity
        return int(shares)

    def execute(self, signal: Signal, current_price: float) -> Optional[SimulatedTrade]:
        """
        Execute a trading signal.

        Args:
            signal: The trading signal
            current_price: Current price of the asset

        Returns:
            The executed trade, or None if not executed
        """
        symbol = signal.symbol

        if signal.action == "BUY":
            return self._execute_buy(signal, current_price)
        elif signal.action == "SELL":
            return self._execute_sell(signal, current_price)

        return None

    def _execute_buy(self, signal: Signal, current_price: float) -> Optional[SimulatedTrade]:
        """Execute a buy order."""
        symbol = signal.symbol

        # Don't buy if we already have a position
        if symbol in self.positions:
            logger.debug(f"Already have position in {symbol}, skipping buy")
            return None

        # Calculate position size
        quantity = self.calculate_position_size(symbol, current_price)
        if quantity <= 0:
            logger.debug(f"Position size too small for {symbol}")
            return None

        cost = quantity * current_price + self.commission

        # Check if we have enough cash
        if cost > self.cash:
            logger.debug(f"Insufficient cash for {symbol}: need ${cost:.2f}, have ${self.cash:.2f}")
            return None

        # Execute the trade
        self.cash -= cost
        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=current_price,
            entry_time=signal.timestamp
        )

        trade = SimulatedTrade(
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            entry_price=current_price,
            entry_time=signal.timestamp,
            reason=signal.reason
        )
        self.trades.append(trade)

        logger.info(f"BUY {quantity} {symbol} @ ${current_price:.2f} | Reason: {signal.reason}")
        return trade

    def _execute_sell(self, signal: Signal, current_price: float) -> Optional[SimulatedTrade]:
        """Execute a sell order."""
        symbol = signal.symbol

        # Can only sell if we have a position
        if symbol not in self.positions:
            logger.debug(f"No position in {symbol}, skipping sell")
            return None

        pos = self.positions.pop(symbol)
        proceeds = pos.quantity * current_price - self.commission

        # Calculate P&L
        pnl = proceeds - (pos.quantity * pos.entry_price)
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100

        # Execute the trade
        self.cash += proceeds

        # Find the matching buy trade and update it
        for trade in reversed(self.trades):
            if trade.symbol == symbol and trade.exit_price is None:
                trade.exit_price = current_price
                trade.exit_time = signal.timestamp
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                break

        logger.info(f"SELL {pos.quantity} {symbol} @ ${current_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:.1f}%) | Reason: {signal.reason}")

        return SimulatedTrade(
            symbol=symbol,
            side="SELL",
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            entry_time=pos.entry_time,
            exit_price=current_price,
            exit_time=signal.timestamp,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=signal.reason
        )

    def close_all_positions(self, timestamp: datetime) -> List[SimulatedTrade]:
        """
        Close all open positions at end of backtest.

        Args:
            timestamp: Current timestamp

        Returns:
            List of closing trades
        """
        trades = []
        for symbol in list(self.positions.keys()):
            price = self._current_prices.get(symbol, self.positions[symbol].entry_price)
            signal = Signal(
                symbol=symbol,
                action="SELL",
                timestamp=timestamp,
                reason="End of backtest"
            )
            trade = self._execute_sell(signal, price)
            if trade:
                trades.append(trade)
        return trades

    def get_completed_trades(self) -> List[SimulatedTrade]:
        """Get all trades that have been closed (have exit price)."""
        return [t for t in self.trades if t.exit_price is not None]
