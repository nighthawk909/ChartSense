"""
Structured Logging Configuration with Correlation IDs

Provides centralized, structured JSON logging for all backend services.
Features:
- Correlation ID tracking across requests
- Standardized log format: {timestamp, correlation_id, service, level, message}
- @log_method decorator for execution time tracking
- API call logging with method, endpoint, status_code, response_time
"""
import logging
import json
import uuid
import time
import functools
from datetime import datetime, timezone
from typing import Optional, Any, Callable, TypeVar
from contextvars import ContextVar

# Context variable for correlation ID - thread-safe and async-safe
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Type variable for decorator return type preservation
F = TypeVar("F", bound=Callable[..., Any])


def get_correlation_id() -> str:
    """
    Get the current correlation ID for the request context.
    Creates a new one if none exists.
    """
    cid = _correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
    return cid


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set a correlation ID for the current context.
    If none provided, generates a new UUID.
    Returns the set correlation ID.
    """
    cid = correlation_id or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id.set(None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON structured logs.

    Format:
    {
        "timestamp": "2026-01-28T14:30:00.123456Z",
        "correlation_id": "abc123-...",
        "service": "alpha_vantage",
        "level": "INFO",
        "message": "Fetching quote for AAPL",
        "extra": {...}  # Any additional context
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build the structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": get_correlation_id(),
            "service": record.name.split(".")[-1] if "." in record.name else record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra attributes passed to the log call
        # Exclude standard LogRecord attributes
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message"
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                # Try to serialize the value; skip if not serializable
                try:
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)

        if extra:
            log_entry["extra"] = extra

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter for development.
    Still includes correlation ID but in a readable format.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        correlation_id = get_correlation_id()
        short_cid = correlation_id[:8] if correlation_id else "--------"

        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        # Format: [correlation_id] LEVEL service - message
        formatted = (
            f"[{short_cid}] "
            f"{color}{record.levelname:8}{reset} "
            f"{record.name.split('.')[-1]:20} - "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def get_logger(name: str, use_json: bool = False) -> logging.Logger:
    """
    Get a configured logger for a service.

    Args:
        name: Logger name (typically __name__ of the module)
        use_json: If True, use JSON structured output; otherwise console format

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        if use_json:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(ConsoleFormatter())

        logger.addHandler(handler)

        # Don't propagate to root logger to avoid duplicate logs
        logger.propagate = False

    return logger


def log_api_call(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    error: Optional[str] = None,
    **extra: Any
) -> None:
    """
    Log an API call with standardized fields.

    Args:
        logger: Logger instance to use
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint URL
        status_code: HTTP response status code
        response_time_ms: Response time in milliseconds
        error: Error message if the call failed
        **extra: Additional context to log
    """
    log_data = {
        "api_method": method,
        "api_endpoint": endpoint,
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if response_time_ms is not None:
        log_data["response_time_ms"] = round(response_time_ms, 2)

    if error:
        log_data["error"] = error

    log_data.update(extra)

    # Determine log level based on status
    if error or (status_code and status_code >= 400):
        level = logging.ERROR
        message = f"API ERROR: {method} {endpoint}"
    elif status_code and status_code >= 300:
        level = logging.WARNING
        message = f"API REDIRECT: {method} {endpoint}"
    else:
        level = logging.INFO
        message = f"API CALL: {method} {endpoint}"

    if response_time_ms is not None:
        message += f" ({response_time_ms:.0f}ms)"
    if status_code is not None:
        message += f" -> {status_code}"

    logger.log(level, message, extra=log_data)


def log_method(
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
    log_args: bool = False,
    log_result: bool = False
) -> Callable[[F], F]:
    """
    Decorator to log method entry, exit, and execution time.

    Args:
        logger: Logger to use (if None, uses module logger)
        level: Log level for the messages
        log_args: If True, log method arguments
        log_result: If True, log method return value

    Usage:
        @log_method(logger=logger)
        async def fetch_data(symbol: str):
            ...

        @log_method(log_args=True, log_result=True)
        def calculate_rsi(prices: List[float], period: int):
            ...
    """
    def decorator(func: F) -> F:
        # Get the appropriate logger
        _logger = logger or logging.getLogger(func.__module__)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            start_time = time.perf_counter()

            # Build log context
            log_extra = {"function": func_name}
            if log_args:
                # Safely represent args (skip 'self' for methods)
                safe_args = args[1:] if args and hasattr(args[0], func.__name__) else args
                log_extra["args"] = _safe_repr(safe_args)
                log_extra["kwargs"] = _safe_repr(kwargs)

            _logger.log(level, f"ENTER: {func_name}", extra=log_extra)

            try:
                result = await func(*args, **kwargs)

                execution_time_ms = (time.perf_counter() - start_time) * 1000
                exit_extra = {
                    "function": func_name,
                    "execution_time_ms": round(execution_time_ms, 2),
                }
                if log_result:
                    exit_extra["result"] = _safe_repr(result)

                _logger.log(
                    level,
                    f"EXIT: {func_name} ({execution_time_ms:.2f}ms)",
                    extra=exit_extra
                )
                return result

            except Exception as e:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                _logger.error(
                    f"ERROR: {func_name} ({execution_time_ms:.2f}ms) - {type(e).__name__}: {e}",
                    extra={
                        "function": func_name,
                        "execution_time_ms": round(execution_time_ms, 2),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            start_time = time.perf_counter()

            # Build log context
            log_extra = {"function": func_name}
            if log_args:
                safe_args = args[1:] if args and hasattr(args[0], func.__name__) else args
                log_extra["args"] = _safe_repr(safe_args)
                log_extra["kwargs"] = _safe_repr(kwargs)

            _logger.log(level, f"ENTER: {func_name}", extra=log_extra)

            try:
                result = func(*args, **kwargs)

                execution_time_ms = (time.perf_counter() - start_time) * 1000
                exit_extra = {
                    "function": func_name,
                    "execution_time_ms": round(execution_time_ms, 2),
                }
                if log_result:
                    exit_extra["result"] = _safe_repr(result)

                _logger.log(
                    level,
                    f"EXIT: {func_name} ({execution_time_ms:.2f}ms)",
                    extra=exit_extra
                )
                return result

            except Exception as e:
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                _logger.error(
                    f"ERROR: {func_name} ({execution_time_ms:.2f}ms) - {type(e).__name__}: {e}",
                    extra={
                        "function": func_name,
                        "execution_time_ms": round(execution_time_ms, 2),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True
                )
                raise

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def _safe_repr(obj: Any, max_length: int = 200) -> str:
    """
    Create a safe string representation of an object for logging.
    Truncates long strings and handles non-serializable objects.
    """
    try:
        # Try JSON serialization first for clean output
        result = json.dumps(obj)
    except (TypeError, ValueError):
        # Fall back to repr
        result = repr(obj)

    if len(result) > max_length:
        return result[:max_length - 3] + "..."
    return result


# FastAPI middleware for correlation ID injection
class CorrelationIdMiddleware:
    """
    ASGI middleware that sets a correlation ID for each request.

    Checks for existing correlation ID in X-Correlation-ID header,
    otherwise generates a new one.

    Usage in FastAPI:
        from services.logging_config import CorrelationIdMiddleware
        app.add_middleware(CorrelationIdMiddleware)
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] == "http":
            # Extract correlation ID from headers if present
            headers = dict(scope.get("headers", []))
            correlation_id = headers.get(b"x-correlation-id", b"").decode() or None

            # Set correlation ID for this request context
            set_correlation_id(correlation_id)

            # Add correlation ID to response headers
            async def send_with_correlation_id(message: dict) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-correlation-id", get_correlation_id().encode()))
                    message["headers"] = headers
                await send(message)

            try:
                await self.app(scope, receive, send_with_correlation_id)
            finally:
                # Clear correlation ID after request
                clear_correlation_id()
        else:
            await self.app(scope, receive, send)


# Convenience function to setup logging for the entire application
def setup_logging(use_json: bool = False, level: int = logging.INFO) -> None:
    """
    Configure logging for the entire application.

    Args:
        use_json: If True, use JSON structured output
        level: Root logging level
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler with appropriate formatter
    handler = logging.StreamHandler()
    handler.setLevel(level)

    if use_json:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(handler)
