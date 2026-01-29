"""
ChartSense Custom Exception Classes

This module provides a hierarchical exception structure for API services,
enabling callers to catch specific exception types for better error handling.

Exception Hierarchy:
    ChartSenseError (base)
    |-- AlphaVantageError
    |   |-- AlphaVantageRateLimitError
    |   |-- AlphaVantageDataError
    |   +-- AlphaVantageAPIError
    |
    |-- AlpacaError
    |   |-- AlpacaAuthError
    |   |-- AlpacaInsufficientFundsError
    |   |-- AlpacaOrderError
    |   |-- AlpacaMarketClosedError
    |   |-- AlpacaPositionError
    |   +-- AlpacaConnectionError
    |
    +-- CryptoServiceError
        |-- CryptoRateLimitError
        |-- CryptoOrderError
        |-- CryptoInsufficientDataError
        +-- CryptoSymbolError

Usage:
    from exceptions import AlpacaOrderError, AlpacaInsufficientFundsError

    try:
        await alpaca_service.submit_market_order(...)
    except AlpacaInsufficientFundsError as e:
        # Handle insufficient funds specifically
        notify_user_low_balance(e.buying_power)
    except AlpacaOrderError as e:
        # Handle other order errors
        log_order_failure(e)
"""

from typing import Optional, Any, Dict


class ChartSenseError(Exception):
    """
    Base exception for all ChartSense errors.

    All custom exceptions inherit from this class, allowing callers
    to catch all ChartSense-related errors with a single except clause.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error code for logging/diagnostics
        details: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or "CHARTSENSE_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Alpha Vantage Exceptions
# =============================================================================

class AlphaVantageError(ChartSenseError):
    """
    Base exception for Alpha Vantage API errors.

    Catch this to handle any Alpha Vantage related error.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or "ALPHA_VANTAGE_ERROR",
            details=details
        )


class AlphaVantageRateLimitError(AlphaVantageError):
    """
    Raised when Alpha Vantage API rate limit is exceeded.

    Free tier limits: 25 requests/day, 5 requests/minute.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying
    """

    def __init__(
        self,
        message: str = "API rate limit reached. Please wait and try again.",
        retry_after: int = 60
    ):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            error_code="ALPHA_VANTAGE_RATE_LIMIT",
            details={"retry_after_seconds": retry_after}
        )


class AlphaVantageDataError(AlphaVantageError):
    """
    Raised when Alpha Vantage returns invalid or missing data.

    This includes cases like:
    - Invalid symbol
    - No data available for the requested time period
    - Malformed response

    Attributes:
        symbol: The symbol that caused the error (if applicable)
        response_data: The raw response data (if available)
    """

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.symbol = symbol
        self.response_data = response_data
        super().__init__(
            message=message,
            error_code="ALPHA_VANTAGE_DATA_ERROR",
            details={
                "symbol": symbol,
                "has_response": response_data is not None
            }
        )


class AlphaVantageAPIError(AlphaVantageError):
    """
    Raised when Alpha Vantage returns an explicit error message.

    This is used for errors returned in the API response body,
    such as invalid API key or invalid function parameters.

    Attributes:
        api_message: The raw error message from Alpha Vantage
    """

    def __init__(
        self,
        api_message: str,
        symbol: Optional[str] = None
    ):
        self.api_message = api_message
        super().__init__(
            message=f"Alpha Vantage API error: {api_message}",
            error_code="ALPHA_VANTAGE_API_ERROR",
            details={
                "api_message": api_message,
                "symbol": symbol
            }
        )


# =============================================================================
# Alpaca Exceptions
# =============================================================================

class AlpacaError(ChartSenseError):
    """
    Base exception for Alpaca Trading API errors.

    Catch this to handle any Alpaca-related error.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or "ALPACA_ERROR",
            details=details
        )


class AlpacaAuthError(AlpacaError):
    """
    Raised when Alpaca authentication fails.

    This includes:
    - Invalid API key or secret
    - API key lacks required permissions
    - Account suspended or restricted

    Attributes:
        permission_required: The permission that was missing (if known)
    """

    def __init__(
        self,
        message: str = "Authentication failed. Check your API key and permissions.",
        permission_required: Optional[str] = None
    ):
        self.permission_required = permission_required
        super().__init__(
            message=message,
            error_code="API_PERMISSION_ERROR",
            details={"permission_required": permission_required}
        )


class AlpacaInsufficientFundsError(AlpacaError):
    """
    Raised when there's not enough buying power for a trade.

    Attributes:
        required_amount: The amount needed for the trade
        available_amount: The current buying power
        symbol: The symbol being traded
    """

    def __init__(
        self,
        message: str = "Insufficient funds for this trade.",
        required_amount: Optional[float] = None,
        available_amount: Optional[float] = None,
        symbol: Optional[str] = None
    ):
        self.required_amount = required_amount
        self.available_amount = available_amount
        self.symbol = symbol

        # Build detailed message if amounts provided
        if required_amount and available_amount:
            message = (
                f"Insufficient funds: need ${required_amount:.2f}, "
                f"have ${available_amount:.2f}"
            )

        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            details={
                "required_amount": required_amount,
                "available_amount": available_amount,
                "symbol": symbol
            }
        )


class AlpacaOrderError(AlpacaError):
    """
    Raised when an order submission fails.

    This covers various order-related failures:
    - Invalid order parameters
    - Order rejected by exchange
    - Order size too small

    Attributes:
        order_type: The type of order that failed (market, limit, etc.)
        symbol: The symbol being traded
        side: Buy or sell
        quantity: The quantity attempted
        alpaca_message: The raw error message from Alpaca
    """

    def __init__(
        self,
        message: str,
        order_type: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        quantity: Optional[float] = None,
        alpaca_message: Optional[str] = None
    ):
        self.order_type = order_type
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.alpaca_message = alpaca_message

        super().__init__(
            message=message,
            error_code="ORDER_ERROR",
            details={
                "order_type": order_type,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "alpaca_message": alpaca_message
            }
        )


class AlpacaOrderSizeTooSmallError(AlpacaOrderError):
    """
    Raised when order size is below minimum requirements.

    Alpaca has minimum notional values and lot sizes.

    Attributes:
        minimum_notional: The minimum order value required
        actual_notional: The order value attempted
    """

    def __init__(
        self,
        message: str = "Order size below minimum requirements.",
        symbol: Optional[str] = None,
        quantity: Optional[float] = None,
        minimum_notional: Optional[float] = None,
        actual_notional: Optional[float] = None
    ):
        self.minimum_notional = minimum_notional
        self.actual_notional = actual_notional

        if minimum_notional and actual_notional:
            message = (
                f"Order size too small: ${actual_notional:.2f} "
                f"< minimum ${minimum_notional:.2f}"
            )

        super().__init__(
            message=message,
            symbol=symbol,
            quantity=quantity
        )
        self.error_code = "ORDER_SIZE_TOO_SMALL"
        self.details.update({
            "minimum_notional": minimum_notional,
            "actual_notional": actual_notional
        })


class AlpacaMarketClosedError(AlpacaError):
    """
    Raised when attempting to trade while market is closed.

    Attributes:
        next_open: When the market will next open
        current_time: Current server time
    """

    def __init__(
        self,
        message: str = "Market is closed. Trading is not available.",
        next_open: Optional[str] = None,
        current_time: Optional[str] = None
    ):
        self.next_open = next_open
        self.current_time = current_time
        super().__init__(
            message=message,
            error_code="MARKET_CLOSED",
            details={
                "next_open": next_open,
                "current_time": current_time
            }
        )


class AlpacaPositionError(AlpacaError):
    """
    Raised for position-related errors.

    This includes:
    - Position not found
    - Cannot close position
    - Invalid position operation

    Attributes:
        symbol: The symbol involved
        operation: The operation that failed (close, get, etc.)
    """

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        operation: Optional[str] = None
    ):
        self.symbol = symbol
        self.operation = operation
        super().__init__(
            message=message,
            error_code="POSITION_ERROR",
            details={
                "symbol": symbol,
                "operation": operation
            }
        )


class AlpacaConnectionError(AlpacaError):
    """
    Raised when connection to Alpaca API fails.

    This includes:
    - Network errors
    - Timeout errors
    - Service unavailable

    Attributes:
        endpoint: The endpoint that failed
        status_code: HTTP status code (if available)
    """

    def __init__(
        self,
        message: str = "Failed to connect to Alpaca API.",
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(
            message=message,
            error_code="ALPACA_CONNECTION_ERROR",
            details={
                "endpoint": endpoint,
                "status_code": status_code
            }
        )


class AlpacaRateLimitError(AlpacaError):
    """
    Raised when Alpaca API rate limit is exceeded.

    Alpaca limits: 200 requests/minute.

    Attributes:
        retry_after: Suggested wait time in seconds
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please wait before retrying.",
        retry_after: int = 60
    ):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after}
        )


# =============================================================================
# Crypto Service Exceptions
# =============================================================================

class CryptoServiceError(ChartSenseError):
    """
    Base exception for Crypto trading service errors.

    Catch this to handle any crypto-related error.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or "CRYPTO_SERVICE_ERROR",
            details=details
        )


class CryptoRateLimitError(CryptoServiceError):
    """
    Raised when crypto API rate limit is exceeded.

    Attributes:
        retry_after: Suggested wait time in seconds
    """

    def __init__(
        self,
        message: str = "Crypto API rate limit exceeded.",
        retry_after: int = 60
    ):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            error_code="CRYPTO_RATE_LIMIT",
            details={"retry_after_seconds": retry_after}
        )


class CryptoOrderError(CryptoServiceError):
    """
    Raised when a crypto order fails.

    Attributes:
        symbol: The crypto symbol
        side: Buy or sell
        quantity: The quantity attempted
        error_message: Raw error message from API
        status_code: HTTP status code
    """

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        quantity: Optional[float] = None,
        error_message: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.error_message = error_message
        self.status_code = status_code

        super().__init__(
            message=message,
            error_code="CRYPTO_ORDER_ERROR",
            details={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "error_message": error_message,
                "status_code": status_code
            }
        )


class CryptoOrderSizeTooSmallError(CryptoOrderError):
    """
    Raised when crypto order size is below minimum.

    Alpaca crypto has minimum notional value of $1.

    Attributes:
        minimum_notional: Minimum order value required
    """

    def __init__(
        self,
        message: str = "Order size too small. Minimum notional value is $1.",
        symbol: Optional[str] = None,
        quantity: Optional[float] = None,
        minimum_notional: float = 1.0
    ):
        self.minimum_notional = minimum_notional
        super().__init__(
            message=message,
            symbol=symbol,
            quantity=quantity
        )
        self.error_code = "CRYPTO_ORDER_SIZE_TOO_SMALL"
        self.details["minimum_notional"] = minimum_notional


class CryptoInsufficientDataError(CryptoServiceError):
    """
    Raised when there's insufficient data for analysis.

    Attributes:
        symbol: The crypto symbol
        required_bars: Number of bars required
        available_bars: Number of bars available
    """

    def __init__(
        self,
        message: str = "Insufficient data for analysis.",
        symbol: Optional[str] = None,
        required_bars: Optional[int] = None,
        available_bars: Optional[int] = None
    ):
        self.symbol = symbol
        self.required_bars = required_bars
        self.available_bars = available_bars

        if required_bars and available_bars:
            message = (
                f"Insufficient data: need {required_bars} bars, "
                f"have {available_bars}"
            )

        super().__init__(
            message=message,
            error_code="CRYPTO_INSUFFICIENT_DATA",
            details={
                "symbol": symbol,
                "required_bars": required_bars,
                "available_bars": available_bars
            }
        )


class CryptoSymbolError(CryptoServiceError):
    """
    Raised for crypto symbol-related errors.

    This includes:
    - Invalid symbol format
    - Unsupported cryptocurrency
    - Symbol not found

    Attributes:
        symbol: The problematic symbol
        expected_format: The expected symbol format
    """

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        expected_format: str = "BTC/USD or BTCUSD"
    ):
        self.symbol = symbol
        self.expected_format = expected_format
        super().__init__(
            message=message,
            error_code="SYMBOL_FORMAT_ERROR",
            details={
                "symbol": symbol,
                "expected_format": expected_format
            }
        )


class CryptoAPIError(CryptoServiceError):
    """
    Raised when crypto API returns an error.

    Attributes:
        status_code: HTTP status code
        api_message: Raw error message from API
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        api_message: Optional[str] = None
    ):
        self.status_code = status_code
        self.api_message = api_message
        super().__init__(
            message=message,
            error_code="CRYPTO_API_ERROR",
            details={
                "status_code": status_code,
                "api_message": api_message
            }
        )


# =============================================================================
# Utility Functions
# =============================================================================

def parse_alpaca_error(error_message: str, symbol: Optional[str] = None) -> AlpacaError:
    """
    Parse an Alpaca error message and return the appropriate exception type.

    This helps convert generic exception messages into specific exception types.

    Args:
        error_message: The raw error message
        symbol: The symbol involved (if applicable)

    Returns:
        An appropriate AlpacaError subclass instance
    """
    message_lower = error_message.lower()

    # Check for authentication errors
    if "unauthorized" in message_lower or "forbidden" in message_lower:
        return AlpacaAuthError(message=error_message)

    # Check for insufficient funds
    if "insufficient" in message_lower and "fund" in message_lower:
        return AlpacaInsufficientFundsError(message=error_message, symbol=symbol)

    if "buying power" in message_lower:
        return AlpacaInsufficientFundsError(message=error_message, symbol=symbol)

    # Check for order size errors
    if "too small" in message_lower or "minimum" in message_lower:
        return AlpacaOrderSizeTooSmallError(message=error_message, symbol=symbol)

    # Check for market closed
    if "market" in message_lower and "closed" in message_lower:
        return AlpacaMarketClosedError(message=error_message)

    # Check for rate limit
    if "rate limit" in message_lower or "too many request" in message_lower:
        return AlpacaRateLimitError(message=error_message)

    # Check for position errors
    if "position" in message_lower and "not exist" in message_lower:
        return AlpacaPositionError(
            message=error_message,
            symbol=symbol,
            operation="get"
        )

    # Default to generic order error for unrecognized messages
    return AlpacaOrderError(message=error_message, symbol=symbol)


def parse_crypto_api_error(
    status_code: int,
    error_message: str,
    symbol: Optional[str] = None
) -> CryptoServiceError:
    """
    Parse a crypto API error and return the appropriate exception type.

    Args:
        status_code: HTTP status code
        error_message: The raw error message
        symbol: The symbol involved (if applicable)

    Returns:
        An appropriate CryptoServiceError subclass instance
    """
    message_lower = error_message.lower()

    # Rate limit (typically 429)
    if status_code == 429 or "rate limit" in message_lower:
        return CryptoRateLimitError(message=error_message)

    # Order size too small
    if "too small" in message_lower or "minimum" in message_lower:
        return CryptoOrderSizeTooSmallError(
            message=error_message,
            symbol=symbol
        )

    # Symbol format error
    if "symbol" in message_lower and ("invalid" in message_lower or "not found" in message_lower):
        return CryptoSymbolError(message=error_message, symbol=symbol)

    # Generic API error
    return CryptoAPIError(
        message=error_message,
        status_code=status_code,
        api_message=error_message
    )
