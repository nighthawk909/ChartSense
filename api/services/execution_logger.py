"""
Execution Logger Service
Tracks all trade execution attempts and logs specific failure reasons.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


class ExecutionErrorCode(str, Enum):
    """Specific error codes for trade execution failures"""
    SUCCESS = "SUCCESS"
    API_PERMISSION_ERROR = "API_PERMISSION_ERROR"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    ORDER_SIZE_TOO_SMALL = "ORDER_SIZE_TOO_SMALL"
    SYMBOL_FORMAT_ERROR = "SYMBOL_FORMAT_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    MARKET_CLOSED = "MARKET_CLOSED"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    REJECTED_BY_AI = "REJECTED_BY_AI"
    BELOW_CONFIDENCE_THRESHOLD = "BELOW_CONFIDENCE_THRESHOLD"
    POSITION_LIMIT_REACHED = "POSITION_LIMIT_REACHED"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    PRICE_MOVED = "PRICE_MOVED"
    TIMEOUT = "TIMEOUT"


@dataclass
class ExecutionAttempt:
    """Record of a single execution attempt"""
    id: str
    timestamp: datetime
    symbol: str
    asset_class: str  # "stock" or "crypto"
    side: str  # "buy" or "sell"
    quantity: float
    price: Optional[float]
    order_type: str  # "market", "limit", etc.

    # Execution result
    success: bool
    error_code: ExecutionErrorCode
    error_message: Optional[str] = None

    # Additional context
    confidence_score: Optional[float] = None
    signal_type: Optional[str] = None
    indicators: Dict[str, Any] = field(default_factory=dict)

    # Order details (if successful)
    order_id: Optional[str] = None
    filled_quantity: Optional[float] = None
    filled_price: Optional[float] = None

    # API response
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "success": self.success,
            "error_code": self.error_code.value,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score,
            "signal_type": self.signal_type,
            "indicators": self.indicators,
            "order_id": self.order_id,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
        }


class ExecutionLogger:
    """
    Centralized execution logger that tracks all trade attempts.
    Provides detailed error analysis and diagnostics.
    """

    def __init__(self, max_history: int = 1000):
        self._attempts: List[ExecutionAttempt] = []
        self._max_history = max_history
        self._error_counts: Dict[ExecutionErrorCode, int] = {code: 0 for code in ExecutionErrorCode}
        self._last_attempt_by_symbol: Dict[str, ExecutionAttempt] = {}

    @property
    def attempts(self) -> List[ExecutionAttempt]:
        return self._attempts

    @property
    def error_counts(self) -> Dict[str, int]:
        return {code.value: count for code, count in self._error_counts.items() if count > 0}

    def log_attempt(
        self,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: float,
        price: Optional[float],
        order_type: str,
        success: bool,
        error_code: ExecutionErrorCode,
        error_message: Optional[str] = None,
        confidence_score: Optional[float] = None,
        signal_type: Optional[str] = None,
        indicators: Optional[Dict[str, Any]] = None,
        order_id: Optional[str] = None,
        filled_quantity: Optional[float] = None,
        filled_price: Optional[float] = None,
        raw_response: Optional[Dict[str, Any]] = None,
    ) -> ExecutionAttempt:
        """Log an execution attempt"""
        import uuid

        attempt = ExecutionAttempt(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            success=success,
            error_code=error_code,
            error_message=error_message,
            confidence_score=confidence_score,
            signal_type=signal_type,
            indicators=indicators or {},
            order_id=order_id,
            filled_quantity=filled_quantity,
            filled_price=filled_price,
            raw_response=raw_response,
        )

        self._attempts.append(attempt)
        self._error_counts[error_code] += 1
        self._last_attempt_by_symbol[symbol] = attempt

        # Maintain max history
        if len(self._attempts) > self._max_history:
            self._attempts = self._attempts[-self._max_history:]

        # Log to file
        self._log_to_file(attempt)

        # Log to console
        if success:
            logger.info(f"[{error_code.value}] {side.upper()} {quantity} {symbol} @ {price or 'market'} - Order ID: {order_id}")
        else:
            logger.warning(f"[{error_code.value}] FAILED {side.upper()} {quantity} {symbol} - {error_message}")

        return attempt

    def log_success(
        self,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: float,
        price: Optional[float],
        order_type: str,
        order_id: str,
        filled_quantity: float,
        filled_price: float,
        **kwargs
    ) -> ExecutionAttempt:
        """Convenience method for logging successful execution"""
        return self.log_attempt(
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            success=True,
            error_code=ExecutionErrorCode.SUCCESS,
            order_id=order_id,
            filled_quantity=filled_quantity,
            filled_price=filled_price,
            **kwargs
        )

    def log_failure(
        self,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: float,
        price: Optional[float],
        order_type: str,
        error_code: ExecutionErrorCode,
        error_message: str,
        **kwargs
    ) -> ExecutionAttempt:
        """Convenience method for logging failed execution"""
        return self.log_attempt(
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            success=False,
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )

    def _log_to_file(self, attempt: ExecutionAttempt):
        """Log attempt to file for persistence"""
        try:
            log_line = json.dumps(attempt.to_dict())
            logger.debug(f"EXECUTION_LOG: {log_line}")
        except Exception as e:
            logger.error(f"Failed to log execution attempt: {e}")

    def get_recent_attempts(self, limit: int = 10, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent execution attempts"""
        attempts = self._attempts
        if symbol:
            attempts = [a for a in attempts if a.symbol == symbol]
        return [a.to_dict() for a in attempts[-limit:]]

    def get_failed_attempts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failed attempts"""
        failed = [a for a in self._attempts if not a.success]
        return [a.to_dict() for a in failed[-limit:]]

    def get_success_rate(self, asset_class: Optional[str] = None) -> Dict[str, Any]:
        """Calculate success rate statistics"""
        attempts = self._attempts
        if asset_class:
            attempts = [a for a in attempts if a.asset_class == asset_class]

        if not attempts:
            return {"total": 0, "success": 0, "failed": 0, "success_rate": 0.0}

        successful = sum(1 for a in attempts if a.success)
        return {
            "total": len(attempts),
            "success": successful,
            "failed": len(attempts) - successful,
            "success_rate": (successful / len(attempts)) * 100,
        }

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors by type"""
        return {
            "error_counts": self.error_counts,
            "most_common_error": max(self._error_counts.items(), key=lambda x: x[1])[0].value if any(self._error_counts.values()) else None,
            "total_errors": sum(1 for a in self._attempts if not a.success),
        }

    def diagnose_failures(self) -> List[Dict[str, Any]]:
        """Analyze failures and provide diagnostic recommendations"""
        diagnostics = []

        # Check for permission errors
        if self._error_counts[ExecutionErrorCode.API_PERMISSION_ERROR] > 0:
            diagnostics.append({
                "issue": "API Permission Errors",
                "count": self._error_counts[ExecutionErrorCode.API_PERMISSION_ERROR],
                "recommendation": "Check API keys have 'Trade' permission enabled, not just 'Read'",
                "severity": "critical",
            })

        # Check for insufficient funds
        if self._error_counts[ExecutionErrorCode.INSUFFICIENT_FUNDS] > 0:
            diagnostics.append({
                "issue": "Insufficient Funds",
                "count": self._error_counts[ExecutionErrorCode.INSUFFICIENT_FUNDS],
                "recommendation": "Reduce position sizes or add funds to account",
                "severity": "high",
            })

        # Check for symbol format errors
        if self._error_counts[ExecutionErrorCode.SYMBOL_FORMAT_ERROR] > 0:
            diagnostics.append({
                "issue": "Symbol Format Errors",
                "count": self._error_counts[ExecutionErrorCode.SYMBOL_FORMAT_ERROR],
                "recommendation": "Ensure crypto symbols use format 'BTCUSDT' and stocks use 'AAPL'",
                "severity": "high",
            })

        # Check for order size issues
        if self._error_counts[ExecutionErrorCode.ORDER_SIZE_TOO_SMALL] > 0:
            diagnostics.append({
                "issue": "Order Size Too Small",
                "count": self._error_counts[ExecutionErrorCode.ORDER_SIZE_TOO_SMALL],
                "recommendation": "Increase minimum order size or position allocation",
                "severity": "medium",
            })

        # Check for rate limiting
        if self._error_counts[ExecutionErrorCode.RATE_LIMIT_EXCEEDED] > 0:
            diagnostics.append({
                "issue": "Rate Limit Exceeded",
                "count": self._error_counts[ExecutionErrorCode.RATE_LIMIT_EXCEEDED],
                "recommendation": "Implement request throttling with backoff",
                "severity": "medium",
            })

        return diagnostics

    def clear(self):
        """Clear all logged attempts"""
        self._attempts.clear()
        self._error_counts = {code: 0 for code in ExecutionErrorCode}
        self._last_attempt_by_symbol.clear()

    def get_last_attempt(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the last execution attempt for a symbol"""
        attempt = self._last_attempt_by_symbol.get(symbol)
        return attempt.to_dict() if attempt else None


# Global singleton instance
_execution_logger: Optional[ExecutionLogger] = None


def get_execution_logger() -> ExecutionLogger:
    """Get the global execution logger instance"""
    global _execution_logger
    if _execution_logger is None:
        _execution_logger = ExecutionLogger()
    return _execution_logger


def parse_api_error(error: Exception, response: Optional[Dict[str, Any]] = None) -> tuple[ExecutionErrorCode, str]:
    """
    Parse an API error and return appropriate error code and message.

    Args:
        error: The exception that was raised
        response: Optional raw API response

    Returns:
        Tuple of (ExecutionErrorCode, error_message)
    """
    error_str = str(error).lower()

    # Check for permission errors
    if any(x in error_str for x in ["permission", "unauthorized", "401", "forbidden", "403"]):
        return ExecutionErrorCode.API_PERMISSION_ERROR, f"API permission denied: {error}"

    # Check for insufficient funds
    if any(x in error_str for x in ["insufficient", "balance", "margin", "buying_power"]):
        return ExecutionErrorCode.INSUFFICIENT_FUNDS, f"Insufficient funds: {error}"

    # Check for order size
    if any(x in error_str for x in ["min_notional", "lot_size", "too_small", "minimum"]):
        return ExecutionErrorCode.ORDER_SIZE_TOO_SMALL, f"Order size too small: {error}"

    # Check for symbol errors
    if any(x in error_str for x in ["invalid_symbol", "symbol", "unknown", "not_found"]):
        return ExecutionErrorCode.SYMBOL_FORMAT_ERROR, f"Invalid symbol: {error}"

    # Check for rate limiting
    if any(x in error_str for x in ["rate", "limit", "429", "too_many"]):
        return ExecutionErrorCode.RATE_LIMIT_EXCEEDED, f"Rate limit exceeded: {error}"

    # Check for market closed
    if any(x in error_str for x in ["market_closed", "closed", "hours"]):
        return ExecutionErrorCode.MARKET_CLOSED, f"Market closed: {error}"

    # Check for network errors
    if any(x in error_str for x in ["network", "connection", "timeout", "socket"]):
        return ExecutionErrorCode.NETWORK_ERROR, f"Network error: {error}"

    # Default to unknown
    return ExecutionErrorCode.UNKNOWN_ERROR, f"Unknown error: {error}"
