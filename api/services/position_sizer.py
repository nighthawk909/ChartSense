"""
Dynamic Position Sizing Service
Calculates position sizes based on volatility, risk, and account conditions

This service provides:
1. ATR-based position sizing
2. Volatility-adjusted sizing
3. Kelly Criterion sizing
4. Risk parity sizing
5. Account drawdown-adjusted sizing
"""
import logging
import math
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeResult:
    """Result of position size calculation"""
    symbol: str
    recommended_shares: int
    position_value: float
    risk_amount: float
    risk_per_share: float

    # Sizing method used
    method: str
    method_details: Dict[str, Any]

    # Limits applied
    limited_by: str  # What capped the size
    max_shares_by_risk: int
    max_shares_by_position_cap: int
    max_shares_by_buying_power: int

    # Confidence
    confidence: float  # 0-100

    # Warnings
    warnings: List[str]


class PositionSizer:
    """
    Calculates dynamic position sizes based on multiple factors.

    Key principles:
    1. Never risk more than X% of account on a single trade
    2. Size inversely to volatility (more volatile = smaller size)
    3. Adjust for account drawdown (smaller during drawdowns)
    4. Consider correlation with existing positions
    """

    def __init__(self, alpaca_service=None, risk_manager=None):
        """
        Initialize position sizer.

        Args:
            alpaca_service: AlpacaService for price/volatility data
            risk_manager: RiskManager for risk parameters
        """
        self.alpaca = alpaca_service
        self.risk_manager = risk_manager

        # Default risk parameters
        self.default_risk_per_trade_pct = 0.02  # 2% per trade
        self.max_position_pct = 0.20            # 20% max per position
        self.volatility_lookback = 14           # Days for volatility calc

        # Volatility adjustment
        self.low_vol_multiplier = 1.2     # Can size up 20% in low vol
        self.high_vol_multiplier = 0.5    # Size down 50% in high vol
        self.vol_baseline = 0.02          # 2% daily vol is "normal"

        # Drawdown adjustment
        self.drawdown_reduction_start = 0.03  # Start reducing at 3% drawdown
        self.drawdown_reduction_max = 0.10    # Max 50% reduction at 10% drawdown

        # Kelly Criterion parameters
        self.kelly_fraction = 0.25  # Use 1/4 Kelly for safety

    def set_services(self, alpaca_service=None, risk_manager=None):
        """Set service dependencies"""
        if alpaca_service:
            self.alpaca = alpaca_service
        if risk_manager:
            self.risk_manager = risk_manager

    # ==================== MAIN SIZING METHODS ====================

    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        account_equity: float,
        buying_power: float,
        current_positions: List[Dict] = None,
        method: str = "volatility_adjusted",
        signal_confidence: float = 70,
    ) -> PositionSizeResult:
        """
        Calculate optimal position size.

        Args:
            symbol: Stock symbol
            entry_price: Planned entry price
            stop_loss_price: Stop-loss price
            account_equity: Total account equity
            buying_power: Available buying power
            current_positions: Current portfolio positions
            method: Sizing method ("fixed_risk", "volatility_adjusted", "kelly")
            signal_confidence: Signal confidence (0-100)

        Returns:
            PositionSizeResult
        """
        warnings = []
        current_positions = current_positions or []

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            risk_per_share = entry_price * 0.05  # Default 5% stop
            warnings.append("No valid stop provided, using 5% default")

        # Get volatility for the symbol
        daily_vol = await self._get_volatility(symbol)

        # Base risk amount (percentage of equity)
        risk_pct = self.default_risk_per_trade_pct
        if self.risk_manager:
            risk_pct = self.risk_manager.risk_per_trade_pct

        base_risk_amount = account_equity * risk_pct

        # Apply sizing method
        if method == "volatility_adjusted":
            shares, method_details = await self._volatility_adjusted_size(
                symbol=symbol,
                base_risk_amount=base_risk_amount,
                risk_per_share=risk_per_share,
                daily_vol=daily_vol,
                account_equity=account_equity,
            )
        elif method == "kelly":
            shares, method_details = self._kelly_criterion_size(
                base_risk_amount=base_risk_amount,
                risk_per_share=risk_per_share,
                entry_price=entry_price,
                signal_confidence=signal_confidence,
            )
        else:  # fixed_risk
            shares, method_details = self._fixed_risk_size(
                base_risk_amount=base_risk_amount,
                risk_per_share=risk_per_share,
            )

        # Apply position cap
        max_position_value = account_equity * self.max_position_pct
        max_shares_by_cap = int(max_position_value / entry_price) if entry_price > 0 else 0

        # Apply buying power limit
        max_shares_by_bp = int(buying_power / entry_price) if entry_price > 0 else 0

        # Apply signal confidence adjustment
        if signal_confidence < 60:
            shares = int(shares * 0.5)
            warnings.append(f"Size reduced 50% due to low confidence ({signal_confidence}%)")
        elif signal_confidence < 70:
            shares = int(shares * 0.75)
            warnings.append(f"Size reduced 25% due to moderate confidence ({signal_confidence}%)")

        # Apply portfolio concentration limit
        if current_positions:
            existing_exposure = sum(p.get("market_value", 0) for p in current_positions)
            remaining_capacity = account_equity * 0.8 - existing_exposure  # 80% max exposure
            max_shares_by_exposure = int(remaining_capacity / entry_price) if entry_price > 0 else 0
            shares = min(shares, max_shares_by_exposure)
            if shares == max_shares_by_exposure:
                warnings.append("Size limited by portfolio exposure cap")

        # Determine what limited the size
        max_shares_by_risk = int(base_risk_amount / risk_per_share) if risk_per_share > 0 else 0

        if shares == 0:
            limited_by = "insufficient_funds"
        elif shares <= max_shares_by_cap and shares < max_shares_by_risk:
            limited_by = "position_cap"
        elif shares <= max_shares_by_bp and shares < max_shares_by_risk:
            limited_by = "buying_power"
        else:
            limited_by = "risk_per_trade"

        # Final values
        final_shares = max(0, min(shares, max_shares_by_cap, max_shares_by_bp))
        position_value = final_shares * entry_price
        actual_risk = final_shares * risk_per_share

        # Calculate confidence
        confidence = self._calculate_sizing_confidence(
            daily_vol=daily_vol,
            signal_confidence=signal_confidence,
            method=method,
        )

        return PositionSizeResult(
            symbol=symbol,
            recommended_shares=final_shares,
            position_value=round(position_value, 2),
            risk_amount=round(actual_risk, 2),
            risk_per_share=round(risk_per_share, 2),
            method=method,
            method_details=method_details,
            limited_by=limited_by,
            max_shares_by_risk=max_shares_by_risk,
            max_shares_by_position_cap=max_shares_by_cap,
            max_shares_by_buying_power=max_shares_by_bp,
            confidence=confidence,
            warnings=warnings,
        )

    # ==================== SIZING METHODS ====================

    async def _volatility_adjusted_size(
        self,
        symbol: str,
        base_risk_amount: float,
        risk_per_share: float,
        daily_vol: float,
        account_equity: float,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate position size adjusted for volatility.

        Higher volatility = smaller position
        Lower volatility = larger position (up to limit)
        """
        # Volatility multiplier
        if daily_vol > 0:
            vol_ratio = daily_vol / self.vol_baseline
            if vol_ratio > 2:
                # High volatility - reduce size
                vol_multiplier = self.high_vol_multiplier
            elif vol_ratio < 0.5:
                # Low volatility - can size up
                vol_multiplier = self.low_vol_multiplier
            else:
                # Normal volatility - linear interpolation
                vol_multiplier = 1.0 - ((vol_ratio - 1) * 0.25)
                vol_multiplier = max(self.high_vol_multiplier, min(self.low_vol_multiplier, vol_multiplier))
        else:
            vol_multiplier = 1.0

        # Adjusted risk amount
        adjusted_risk = base_risk_amount * vol_multiplier

        # Calculate shares
        shares = int(adjusted_risk / risk_per_share) if risk_per_share > 0 else 0

        method_details = {
            "base_risk_amount": round(base_risk_amount, 2),
            "daily_volatility": round(daily_vol, 4),
            "vol_baseline": self.vol_baseline,
            "vol_multiplier": round(vol_multiplier, 2),
            "adjusted_risk_amount": round(adjusted_risk, 2),
        }

        return shares, method_details

    def _fixed_risk_size(
        self,
        base_risk_amount: float,
        risk_per_share: float,
    ) -> Tuple[int, Dict[str, Any]]:
        """Calculate position size using fixed risk percentage"""
        shares = int(base_risk_amount / risk_per_share) if risk_per_share > 0 else 0

        method_details = {
            "base_risk_amount": round(base_risk_amount, 2),
            "risk_per_share": round(risk_per_share, 2),
        }

        return shares, method_details

    def _kelly_criterion_size(
        self,
        base_risk_amount: float,
        risk_per_share: float,
        entry_price: float,
        signal_confidence: float,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate position size using Kelly Criterion.

        Kelly % = W - [(1-W)/R]
        Where:
        - W = Win probability
        - R = Win/Loss ratio

        We use a fractional Kelly for safety.
        """
        # Estimate win probability from signal confidence
        win_prob = signal_confidence / 100

        # Estimate win/loss ratio (assume 2:1 target)
        win_loss_ratio = 2.0

        # Full Kelly percentage
        kelly_pct = win_prob - ((1 - win_prob) / win_loss_ratio)
        kelly_pct = max(0, kelly_pct)  # Can't be negative

        # Fractional Kelly
        fractional_kelly = kelly_pct * self.kelly_fraction

        # Calculate shares based on Kelly
        kelly_risk = base_risk_amount * (1 + fractional_kelly)
        shares = int(kelly_risk / risk_per_share) if risk_per_share > 0 else 0

        method_details = {
            "win_probability": round(win_prob, 2),
            "win_loss_ratio": win_loss_ratio,
            "full_kelly_pct": round(kelly_pct * 100, 2),
            "kelly_fraction": self.kelly_fraction,
            "fractional_kelly_pct": round(fractional_kelly * 100, 2),
        }

        return shares, method_details

    # ==================== VOLATILITY ====================

    async def _get_volatility(self, symbol: str) -> float:
        """Get daily volatility for a symbol"""
        if not self.alpaca:
            return self.vol_baseline  # Default

        try:
            bars = await self.alpaca.get_bars(
                symbol=symbol,
                timeframe="1day",
                limit=self.volatility_lookback + 5,
            )

            if not bars or len(bars) < 5:
                return self.vol_baseline

            # Calculate daily returns
            returns = []
            for i in range(1, len(bars)):
                prev_close = bars[i - 1]["close"]
                curr_close = bars[i]["close"]
                if prev_close > 0:
                    ret = (curr_close - prev_close) / prev_close
                    returns.append(ret)

            if not returns:
                return self.vol_baseline

            # Calculate standard deviation of returns
            import statistics
            daily_vol = statistics.stdev(returns) if len(returns) > 1 else self.vol_baseline

            return daily_vol

        except Exception as e:
            logger.debug(f"Could not get volatility for {symbol}: {e}")
            return self.vol_baseline

    # ==================== CONFIDENCE ====================

    def _calculate_sizing_confidence(
        self,
        daily_vol: float,
        signal_confidence: float,
        method: str,
    ) -> float:
        """Calculate confidence in the sizing recommendation"""
        confidence = 50  # Base

        # Higher signal confidence = higher sizing confidence
        confidence += (signal_confidence - 70) * 0.3

        # Normal volatility = higher confidence
        vol_ratio = daily_vol / self.vol_baseline if self.vol_baseline > 0 else 1
        if 0.8 <= vol_ratio <= 1.2:
            confidence += 10
        elif vol_ratio > 2:
            confidence -= 10

        # Volatility-adjusted method generally more reliable
        if method == "volatility_adjusted":
            confidence += 5

        return max(0, min(100, confidence))

    # ==================== BATCH SIZING ====================

    async def size_multiple_positions(
        self,
        opportunities: List[Dict[str, Any]],
        account_equity: float,
        buying_power: float,
        current_positions: List[Dict] = None,
        max_new_positions: int = 3,
    ) -> List[PositionSizeResult]:
        """
        Calculate sizes for multiple potential positions.

        Divides available capital among opportunities.

        Args:
            opportunities: List of opportunities with symbol, entry_price, stop_loss_price
            account_equity: Total equity
            buying_power: Available buying power
            current_positions: Current positions
            max_new_positions: Maximum new positions to size

        Returns:
            List of PositionSizeResult
        """
        if not opportunities:
            return []

        current_positions = current_positions or []

        # Calculate per-position budget
        num_new = min(len(opportunities), max_new_positions)
        per_position_equity = account_equity * 0.15  # 15% each max
        per_position_bp = buying_power / num_new if num_new > 0 else 0

        results = []
        for opp in opportunities[:max_new_positions]:
            symbol = opp.get("symbol")
            entry_price = opp.get("entry_price", 0)
            stop_loss = opp.get("stop_loss_price", entry_price * 0.95)
            confidence = opp.get("confidence", 70)

            if not symbol or entry_price <= 0:
                continue

            # Size with reduced budget per position
            result = await self.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss_price=stop_loss,
                account_equity=min(per_position_equity, account_equity),
                buying_power=min(per_position_bp, buying_power),
                current_positions=current_positions,
                signal_confidence=confidence,
            )

            results.append(result)

            # Reduce remaining buying power
            buying_power -= result.position_value

        return results

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get position sizer status"""
        return {
            "enabled": self.alpaca is not None,
            "has_risk_manager": self.risk_manager is not None,
            "config": {
                "default_risk_per_trade_pct": self.default_risk_per_trade_pct * 100,
                "max_position_pct": self.max_position_pct * 100,
                "volatility_lookback": self.volatility_lookback,
                "vol_baseline": self.vol_baseline,
                "kelly_fraction": self.kelly_fraction,
            },
        }


# Singleton instance
_position_sizer: Optional[PositionSizer] = None


def get_position_sizer() -> PositionSizer:
    """Get the global position sizer"""
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = PositionSizer()
    return _position_sizer
