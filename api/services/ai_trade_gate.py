"""
AI Trade Gate Service
Requires AI approval before executing trades

This service provides:
1. AI-based trade validation before execution
2. Risk assessment and confidence scoring
3. Trade rejection with explanations
4. Exit signal evaluation
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TradeDecision(str, Enum):
    """AI decision for a trade"""
    APPROVE = "approve"
    REJECT = "reject"
    WAIT = "wait"  # Wait for better conditions
    REDUCE_SIZE = "reduce_size"  # Approve but with smaller size


class ExitDecision(str, Enum):
    """AI decision for an exit"""
    HOLD = "hold"
    PARTIAL_EXIT = "partial_exit"
    FULL_EXIT = "full_exit"
    TIGHTEN_STOP = "tighten_stop"


@dataclass
class TradeGateResult:
    """Result of AI trade evaluation"""
    decision: TradeDecision
    confidence: float  # 0-100
    reasons: List[str]
    concerns: List[str]
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    suggested_size_multiplier: float = 1.0  # 1.0 = full size, 0.5 = half
    evaluation_time_ms: int = 0
    raw_response: Optional[str] = None


@dataclass
class ExitGateResult:
    """Result of AI exit evaluation"""
    decision: ExitDecision
    confidence: float
    reasons: List[str]
    suggested_exit_pct: float = 0  # What % to exit (for partial)
    suggested_new_stop: Optional[float] = None
    evaluation_time_ms: int = 0


class AITradeGate:
    """
    AI-powered trade gating system.

    All trades must pass through this gate before execution.
    The AI evaluates:
    1. Signal quality and confluence
    2. Market conditions
    3. Portfolio risk
    4. Historical pattern success
    """

    def __init__(self, ai_advisor=None, enabled: bool = True):
        """
        Initialize AI trade gate.

        Args:
            ai_advisor: AIAdvisor instance for LLM calls
            enabled: Whether gating is enabled
        """
        self.ai_advisor = ai_advisor
        self.enabled = enabled

        # Minimum thresholds
        self.min_confidence_threshold = 65.0
        self.auto_approve_threshold = 85.0  # Auto-approve above this
        self.auto_reject_threshold = 40.0   # Auto-reject below this

        # Configuration
        self.require_multiple_confirmations = True
        self.check_market_conditions = True
        self.check_portfolio_correlation = True
        self.check_recent_performance = True

        # Recent decisions cache
        self._decision_cache: Dict[str, TradeGateResult] = {}
        self._cache_ttl_seconds = 300  # 5 minutes

        # Statistics
        self._stats = {
            "total_evaluations": 0,
            "approved": 0,
            "rejected": 0,
            "wait": 0,
            "reduced_size": 0,
            "avg_confidence": 0,
        }

        # Decision history
        self._decision_history: List[Dict[str, Any]] = []
        self._max_history = 200

    def set_ai_advisor(self, ai_advisor):
        """Set the AI advisor"""
        self.ai_advisor = ai_advisor

    # ==================== TRADE GATING ====================

    async def evaluate_trade(
        self,
        symbol: str,
        side: str,  # buy, sell
        quantity: int,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: Optional[float],
        signal_score: float,
        signal_type: str,  # SWING, INTRADAY, SCALP
        indicators: Dict[str, Any],
        patterns_detected: List[str],
        account_info: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
    ) -> TradeGateResult:
        """
        Evaluate a trade before execution.

        Args:
            symbol: Stock symbol
            side: buy or sell
            quantity: Proposed quantity
            entry_price: Proposed entry price
            stop_loss_price: Proposed stop-loss
            take_profit_price: Proposed take-profit
            signal_score: Signal confidence score (0-100)
            signal_type: Type of trade
            indicators: Technical indicator values
            patterns_detected: Chart patterns found
            account_info: Account equity, buying power, etc.
            current_positions: Existing positions

        Returns:
            TradeGateResult with decision and reasoning
        """
        start_time = datetime.now()
        self._stats["total_evaluations"] += 1

        # Check cache first
        cache_key = f"{symbol}_{side}_{signal_score}"
        cached = self._get_cached_decision(cache_key)
        if cached:
            logger.debug(f"Using cached decision for {symbol}")
            return cached

        # If AI is disabled, use rule-based evaluation
        if not self.enabled or not self.ai_advisor or not self.ai_advisor.enabled:
            result = await self._rule_based_evaluation(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                signal_score=signal_score,
                signal_type=signal_type,
                indicators=indicators,
                patterns_detected=patterns_detected,
                account_info=account_info,
                current_positions=current_positions,
            )
        else:
            # Use AI evaluation
            result = await self._ai_evaluation(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                signal_score=signal_score,
                signal_type=signal_type,
                indicators=indicators,
                patterns_detected=patterns_detected,
                account_info=account_info,
                current_positions=current_positions,
            )

        # Calculate evaluation time
        result.evaluation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Update statistics
        self._update_stats(result)

        # Cache the result
        self._cache_decision(cache_key, result)

        # Record in history
        self._record_decision(symbol, side, signal_score, result)

        logger.info(
            f"Trade gate: {symbol} {side} -> {result.decision.value} "
            f"(confidence: {result.confidence:.1f}%, time: {result.evaluation_time_ms}ms)"
        )

        return result

    async def _rule_based_evaluation(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: Optional[float],
        signal_score: float,
        signal_type: str,
        indicators: Dict[str, Any],
        patterns_detected: List[str],
        account_info: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
    ) -> TradeGateResult:
        """Rule-based trade evaluation when AI is disabled"""
        reasons = []
        concerns = []
        confidence = signal_score

        # Auto-approve high confidence signals
        if signal_score >= self.auto_approve_threshold:
            reasons.append(f"High confidence signal ({signal_score:.1f}%)")
            return TradeGateResult(
                decision=TradeDecision.APPROVE,
                confidence=confidence,
                reasons=reasons,
                concerns=[],
            )

        # Auto-reject low confidence signals
        if signal_score < self.auto_reject_threshold:
            reasons.append(f"Signal confidence too low ({signal_score:.1f}%)")
            return TradeGateResult(
                decision=TradeDecision.REJECT,
                confidence=confidence,
                reasons=reasons,
                concerns=["Signal strength below minimum threshold"],
            )

        # Check risk/reward ratio
        if take_profit_price and stop_loss_price:
            risk = abs(entry_price - stop_loss_price)
            reward = abs(take_profit_price - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0

            if rr_ratio < 1.5:
                concerns.append(f"Risk/reward ratio poor ({rr_ratio:.2f}:1)")
                confidence -= 10
            elif rr_ratio >= 2.0:
                reasons.append(f"Good risk/reward ({rr_ratio:.2f}:1)")
                confidence += 5

        # Check position count
        max_positions = 5
        if len(current_positions) >= max_positions:
            concerns.append(f"At maximum positions ({max_positions})")
            return TradeGateResult(
                decision=TradeDecision.REJECT,
                confidence=confidence,
                reasons=reasons,
                concerns=concerns,
            )

        # Check for existing position in same symbol
        if any(p.get("symbol") == symbol for p in current_positions):
            concerns.append("Already have position in this symbol")
            confidence -= 15

        # Check RSI extremes
        rsi = indicators.get("rsi", 50)
        if side == "buy" and rsi > 70:
            concerns.append(f"RSI overbought ({rsi:.1f})")
            confidence -= 10
        elif side == "sell" and rsi < 30:
            concerns.append(f"RSI oversold ({rsi:.1f})")
            confidence -= 10

        # Check for patterns
        if patterns_detected:
            reasons.append(f"Patterns: {', '.join(patterns_detected[:3])}")
            confidence += 5

        # Check buying power
        position_value = quantity * entry_price
        buying_power = account_info.get("buying_power", 0)
        if position_value > buying_power * 0.3:
            concerns.append("Position would use >30% of buying power")
            confidence -= 5

        # Make decision based on adjusted confidence
        if confidence >= self.min_confidence_threshold:
            if len(concerns) > 2:
                return TradeGateResult(
                    decision=TradeDecision.REDUCE_SIZE,
                    confidence=confidence,
                    reasons=reasons,
                    concerns=concerns,
                    suggested_size_multiplier=0.5,
                )
            return TradeGateResult(
                decision=TradeDecision.APPROVE,
                confidence=confidence,
                reasons=reasons,
                concerns=concerns,
            )
        else:
            return TradeGateResult(
                decision=TradeDecision.WAIT,
                confidence=confidence,
                reasons=reasons,
                concerns=concerns,
            )

    async def _ai_evaluation(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: Optional[float],
        signal_score: float,
        signal_type: str,
        indicators: Dict[str, Any],
        patterns_detected: List[str],
        account_info: Dict[str, Any],
        current_positions: List[Dict[str, Any]],
    ) -> TradeGateResult:
        """AI-based trade evaluation using LLM"""

        # Prepare context for AI
        risk = abs(entry_price - stop_loss_price) / entry_price * 100
        reward = abs(take_profit_price - entry_price) / entry_price * 100 if take_profit_price else 0

        context = f"""
Evaluate this trade proposal:

TRADE DETAILS:
- Symbol: {symbol}
- Side: {side.upper()}
- Quantity: {quantity} shares
- Entry Price: ${entry_price:.2f}
- Stop Loss: ${stop_loss_price:.2f} ({risk:.2f}% risk)
- Take Profit: ${take_profit_price:.2f if take_profit_price else 'Not set'} ({reward:.2f}% target)
- Signal Score: {signal_score:.1f}/100
- Trade Type: {signal_type}

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- Bollinger Position: {indicators.get('bb_position', 'N/A')}
- 50 SMA: ${indicators.get('sma_50', 'N/A')}
- 200 SMA: ${indicators.get('sma_200', 'N/A')}
- Volume Ratio: {indicators.get('volume_ratio', 'N/A')}x

PATTERNS DETECTED:
{', '.join(patterns_detected) if patterns_detected else 'None'}

ACCOUNT STATUS:
- Equity: ${account_info.get('equity', 0):.2f}
- Buying Power: ${account_info.get('buying_power', 0):.2f}
- Current Positions: {len(current_positions)}
- Position Symbols: {', '.join([p.get('symbol', '') for p in current_positions]) if current_positions else 'None'}

Based on this information, should this trade be executed?
Provide your decision as APPROVE, REJECT, WAIT, or REDUCE_SIZE.
Also provide:
1. Confidence level (0-100)
2. Key reasons for your decision
3. Any concerns
4. Suggested modifications (if any)
"""

        try:
            # Call AI advisor for evaluation
            if hasattr(self.ai_advisor, 'evaluate_stock_trade'):
                ai_result = await self.ai_advisor.evaluate_stock_trade(
                    symbol=symbol,
                    signal_type=signal_type,
                    signal_score=signal_score,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    indicators=indicators,
                    account_info=account_info,
                    portfolio_positions=current_positions,
                )

                # Parse AI result
                decision_str = ai_result.get("decision", "WAIT").upper()
                decision_map = {
                    "APPROVE": TradeDecision.APPROVE,
                    "REJECT": TradeDecision.REJECT,
                    "WAIT": TradeDecision.WAIT,
                    "REDUCE_SIZE": TradeDecision.REDUCE_SIZE,
                }
                decision = decision_map.get(decision_str, TradeDecision.WAIT)

                return TradeGateResult(
                    decision=decision,
                    confidence=ai_result.get("confidence", signal_score),
                    reasons=ai_result.get("reasons", []),
                    concerns=ai_result.get("concerns", []),
                    suggested_stop_loss=ai_result.get("suggested_stop_loss"),
                    suggested_take_profit=ai_result.get("suggested_take_profit"),
                    suggested_size_multiplier=ai_result.get("size_multiplier", 1.0),
                    raw_response=str(ai_result),
                )

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            # Fall back to rule-based
            return await self._rule_based_evaluation(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                signal_score=signal_score,
                signal_type=signal_type,
                indicators=indicators,
                patterns_detected=patterns_detected,
                account_info=account_info,
                current_positions=current_positions,
            )

    # ==================== EXIT GATING ====================

    async def evaluate_exit(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        stop_loss_price: float,
        take_profit_price: Optional[float],
        entry_time: datetime,
        current_indicators: Dict[str, Any],
        pnl_percent: float,
        trade_type: str,
    ) -> ExitGateResult:
        """
        Evaluate whether to exit a position.

        Args:
            symbol: Stock symbol
            entry_price: Original entry price
            current_price: Current market price
            stop_loss_price: Current stop-loss
            take_profit_price: Current take-profit
            entry_time: When position was opened
            current_indicators: Current technical indicators
            pnl_percent: Current P&L percentage
            trade_type: SWING, INTRADAY, SCALP

        Returns:
            ExitGateResult with decision
        """
        start_time = datetime.now()

        reasons = []
        confidence = 50.0

        # Calculate hold duration
        hold_duration = datetime.now() - entry_time
        hold_hours = hold_duration.total_seconds() / 3600

        # Check RSI for momentum
        rsi = current_indicators.get("rsi", 50)

        # Check for profit taking opportunities
        if pnl_percent >= 5.0:  # 5% profit
            confidence += 20
            reasons.append(f"Good profit (+{pnl_percent:.1f}%)")

            if rsi > 75:  # Overbought
                reasons.append("RSI overbought - consider taking profit")
                return ExitGateResult(
                    decision=ExitDecision.PARTIAL_EXIT,
                    confidence=confidence + 15,
                    reasons=reasons,
                    suggested_exit_pct=50,
                )

        # Check for loss cutting
        if pnl_percent <= -3.0:  # 3% loss
            confidence += 15
            reasons.append(f"Position in loss ({pnl_percent:.1f}%)")

            if rsi < 25:  # Very oversold
                reasons.append("RSI very oversold - may bounce")
                return ExitGateResult(
                    decision=ExitDecision.TIGHTEN_STOP,
                    confidence=confidence,
                    reasons=reasons,
                    suggested_new_stop=stop_loss_price * 1.02,  # Tighter stop
                )

        # Check time-based rules
        max_hold_hours = {"SCALP": 1, "INTRADAY": 8, "SWING": 168}  # 168 = 7 days
        max_hours = max_hold_hours.get(trade_type, 168)

        if hold_hours > max_hours:
            reasons.append(f"Position held longer than {trade_type} target ({hold_hours:.1f}h)")
            return ExitGateResult(
                decision=ExitDecision.FULL_EXIT,
                confidence=confidence + 10,
                reasons=reasons,
            )

        # Default: hold
        return ExitGateResult(
            decision=ExitDecision.HOLD,
            confidence=confidence,
            reasons=["No exit conditions met"],
            evaluation_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        )

    # ==================== CACHING ====================

    def _get_cached_decision(self, cache_key: str) -> Optional[TradeGateResult]:
        """Get a cached decision if still valid"""
        if cache_key not in self._decision_cache:
            return None

        # Check TTL (not stored, so just return if exists within window)
        return None  # Disable cache for now to ensure fresh evaluations

    def _cache_decision(self, cache_key: str, result: TradeGateResult):
        """Cache a decision"""
        self._decision_cache[cache_key] = result

        # Limit cache size
        if len(self._decision_cache) > 100:
            # Remove oldest entries
            keys = list(self._decision_cache.keys())
            for key in keys[:50]:
                del self._decision_cache[key]

    # ==================== STATISTICS ====================

    def _update_stats(self, result: TradeGateResult):
        """Update statistics"""
        if result.decision == TradeDecision.APPROVE:
            self._stats["approved"] += 1
        elif result.decision == TradeDecision.REJECT:
            self._stats["rejected"] += 1
        elif result.decision == TradeDecision.WAIT:
            self._stats["wait"] += 1
        elif result.decision == TradeDecision.REDUCE_SIZE:
            self._stats["reduced_size"] += 1

        # Update average confidence (running average)
        n = self._stats["total_evaluations"]
        old_avg = self._stats["avg_confidence"]
        self._stats["avg_confidence"] = old_avg + (result.confidence - old_avg) / n

    def _record_decision(self, symbol: str, side: str, signal_score: float, result: TradeGateResult):
        """Record decision in history"""
        self._decision_history.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "signal_score": signal_score,
            "decision": result.decision.value,
            "confidence": result.confidence,
            "reasons": result.reasons,
            "concerns": result.concerns,
        })

        # Trim history
        if len(self._decision_history) > self._max_history:
            self._decision_history = self._decision_history[-self._max_history:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get gate statistics"""
        total = self._stats["total_evaluations"]
        return {
            **self._stats,
            "approval_rate": self._stats["approved"] / total * 100 if total > 0 else 0,
            "rejection_rate": self._stats["rejected"] / total * 100 if total > 0 else 0,
        }

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent decisions"""
        return self._decision_history[-limit:]

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get AI trade gate status"""
        return {
            "enabled": self.enabled,
            "ai_enabled": self.ai_advisor.enabled if self.ai_advisor else False,
            "min_confidence_threshold": self.min_confidence_threshold,
            "auto_approve_threshold": self.auto_approve_threshold,
            "auto_reject_threshold": self.auto_reject_threshold,
            "statistics": self.get_statistics(),
            "recent_decisions": self.get_recent_decisions(10),
        }


# Singleton instance
_ai_trade_gate: Optional[AITradeGate] = None


def get_ai_trade_gate() -> AITradeGate:
    """Get the global AI trade gate instance"""
    global _ai_trade_gate
    if _ai_trade_gate is None:
        _ai_trade_gate = AITradeGate()
    return _ai_trade_gate
