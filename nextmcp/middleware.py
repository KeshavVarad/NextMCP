"""
Middleware utilities for NextMCP.

Middleware functions wrap tool functions to add cross-cutting concerns
like logging, authentication, rate limiting, error handling, etc.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import wraps

logger = logging.getLogger(__name__)


def log_calls(fn: Callable) -> Callable:
    """
    Middleware that logs all tool calls with parameters and execution time.

    Example:
        app.add_middleware(log_calls)
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        tool_name = getattr(fn, "_tool_name", fn.__name__)
        start_time = time.time()

        logger.info(f"[CALL] {tool_name} - args={args}, kwargs={kwargs}")

        try:
            result = fn(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"[SUCCESS] {tool_name} - elapsed={elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[ERROR] {tool_name} - {type(e).__name__}: {e} - elapsed={elapsed:.3f}s")
            raise

    return wrapper


def require_auth(api_key_param: str = "auth_key", valid_keys: set | None = None):
    """
    Middleware factory that requires authentication via an API key.

    Args:
        api_key_param: Name of the parameter that contains the API key
        valid_keys: Set of valid API keys (if None, checks for any non-empty key)

    Example:
        app.add_middleware(require_auth(valid_keys={"secret-key-123"}))

        @app.tool()
        def protected_tool(auth_key: str, data: str):
            return f"Processing: {data}"
    """

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)
            auth_key = kwargs.get(api_key_param)

            if not auth_key:
                logger.warning(f"[AUTH] {tool_name} - Missing API key")
                raise ValueError(f"Authentication required: missing {api_key_param}")

            if valid_keys is not None and auth_key not in valid_keys:
                logger.warning(f"[AUTH] {tool_name} - Invalid API key")
                raise ValueError("Authentication failed: invalid API key")

            logger.debug(f"[AUTH] {tool_name} - Authentication successful")
            return fn(*args, **kwargs)

        return wrapper

    return middleware


def error_handler(fn: Callable) -> Callable:
    """
    Middleware that catches exceptions and returns them as structured error responses.

    Example:
        app.add_middleware(error_handler)
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        tool_name = getattr(fn, "_tool_name", fn.__name__)

        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ERROR_HANDLER] {tool_name} - {type(e).__name__}: {e}")
            return {
                "error": True,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "tool": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    return wrapper


def rate_limit(max_calls: int, time_window: int):
    """
    Middleware factory that implements rate limiting.

    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds

    Example:
        # Allow 10 calls per minute
        app.add_middleware(rate_limit(max_calls=10, time_window=60))
    """
    call_history: dict[str, list] = {}

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)
            now = datetime.now(timezone.utc)

            # Initialize call history for this tool
            if tool_name not in call_history:
                call_history[tool_name] = []

            # Remove old calls outside the time window
            cutoff = now - timedelta(seconds=time_window)
            call_history[tool_name] = [
                call_time for call_time in call_history[tool_name] if call_time > cutoff
            ]

            # Check rate limit
            if len(call_history[tool_name]) >= max_calls:
                logger.warning(
                    f"[RATE_LIMIT] {tool_name} - Rate limit exceeded: "
                    f"{max_calls} calls per {time_window}s"
                )
                raise ValueError(
                    f"Rate limit exceeded: max {max_calls} calls per {time_window} seconds"
                )

            # Record this call
            call_history[tool_name].append(now)

            return fn(*args, **kwargs)

        return wrapper

    return middleware


def validate_inputs(**validators):
    """
    Middleware factory that validates inputs using custom validator functions.

    Args:
        **validators: Keyword arguments mapping parameter names to validator functions

    Example:
        def validate_positive(value):
            if value <= 0:
                raise ValueError("Must be positive")
            return value

        @app.tool()
        @validate_inputs(amount=validate_positive)
        def process_payment(amount: float):
            return {"charged": amount}
    """

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)

            # Validate each specified parameter
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    try:
                        kwargs[param_name] = validator(kwargs[param_name])
                    except Exception as e:
                        logger.error(
                            f"[VALIDATION] {tool_name} - Validation failed for {param_name}: {e}"
                        )
                        raise ValueError(f"Validation failed for {param_name}: {e}") from e

            return fn(*args, **kwargs)

        return wrapper

    return middleware


def cache_results(ttl_seconds: int = 300):
    """
    Middleware factory that caches tool results for a specified TTL.

    Args:
        ttl_seconds: Time to live for cached results in seconds

    Example:
        # Cache results for 5 minutes
        @app.tool()
        @cache_results(ttl_seconds=300)
        def expensive_operation(param: str):
            return perform_expensive_computation(param)
    """
    cache: dict[str, tuple] = {}  # key -> (result, expiry_time)

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)

            # Create cache key from function name and arguments
            cache_key = f"{tool_name}:{args}:{sorted(kwargs.items())}"

            # Check if we have a valid cached result
            now = time.time()
            if cache_key in cache:
                result, expiry = cache[cache_key]
                if now < expiry:
                    logger.debug(f"[CACHE] {tool_name} - Cache hit")
                    return result
                else:
                    logger.debug(f"[CACHE] {tool_name} - Cache expired")
                    del cache[cache_key]

            # Call the function and cache the result
            logger.debug(f"[CACHE] {tool_name} - Cache miss, executing function")
            result = fn(*args, **kwargs)
            cache[cache_key] = (result, now + ttl_seconds)

            return result

        return wrapper

    return middleware


def timeout(seconds: int):
    """
    Middleware factory that enforces a timeout on tool execution.

    Note: This uses a basic approach and may not work for all functions.
    For production use, consider using asyncio or threading-based timeouts.

    Args:
        seconds: Maximum execution time in seconds

    Example:
        @app.tool()
        @timeout(seconds=30)
        def long_running_task(data: str):
            return process_data(data)
    """

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            import signal

            tool_name = getattr(fn, "_tool_name", fn.__name__)

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Tool {tool_name} exceeded {seconds} second timeout")

            # Set the timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)

            try:
                result = fn(*args, **kwargs)
                signal.alarm(0)  # Disable the alarm
                return result
            except TimeoutError:
                logger.error(f"[TIMEOUT] {tool_name} - Exceeded {seconds}s timeout")
                raise

        return wrapper

    return middleware


# ============================================================================
# Async Middleware Functions
# ============================================================================


def log_calls_async(fn: Callable) -> Callable:
    """
    Async middleware that logs all tool calls with parameters and execution time.

    Example:
        app.add_middleware(log_calls_async)

        @app.tool()
        async def my_async_tool(param: str):
            return await some_async_operation(param)
    """

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        tool_name = getattr(fn, "_tool_name", fn.__name__)
        start_time = time.time()

        logger.info(f"[CALL] {tool_name} - args={args}, kwargs={kwargs}")

        try:
            result = await fn(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"[SUCCESS] {tool_name} - elapsed={elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[ERROR] {tool_name} - {type(e).__name__}: {e} - elapsed={elapsed:.3f}s")
            raise

    return wrapper


def require_auth_async(api_key_param: str = "auth_key", valid_keys: set | None = None):
    """
    Async middleware factory that requires authentication via an API key.

    Args:
        api_key_param: Name of the parameter that contains the API key
        valid_keys: Set of valid API keys (if None, checks for any non-empty key)

    Example:
        app.add_middleware(require_auth_async(valid_keys={"secret-key-123"}))

        @app.tool()
        async def protected_tool(auth_key: str, data: str):
            result = await process_data(data)
            return result
    """

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)
            auth_key = kwargs.get(api_key_param)

            if not auth_key:
                logger.warning(f"[AUTH] {tool_name} - Missing API key")
                raise ValueError(f"Authentication required: missing {api_key_param}")

            if valid_keys is not None and auth_key not in valid_keys:
                logger.warning(f"[AUTH] {tool_name} - Invalid API key")
                raise ValueError("Authentication failed: invalid API key")

            logger.debug(f"[AUTH] {tool_name} - Authentication successful")
            return await fn(*args, **kwargs)

        return wrapper

    return middleware


def error_handler_async(fn: Callable) -> Callable:
    """
    Async middleware that catches exceptions and returns them as structured error responses.

    Example:
        app.add_middleware(error_handler_async)

        @app.tool()
        async def my_async_tool(param: str):
            return await some_operation(param)
    """

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        tool_name = getattr(fn, "_tool_name", fn.__name__)

        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ERROR_HANDLER] {tool_name} - {type(e).__name__}: {e}")
            return {
                "error": True,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "tool": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    return wrapper


def rate_limit_async(max_calls: int, time_window: int):
    """
    Async middleware factory that implements rate limiting.

    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds

    Example:
        # Allow 10 calls per minute
        app.add_middleware(rate_limit_async(max_calls=10, time_window=60))

        @app.tool()
        async def rate_limited_tool(data: str):
            return await process_data(data)
    """
    call_history: dict[str, list] = {}

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)
            now = datetime.now(timezone.utc)

            # Initialize call history for this tool
            if tool_name not in call_history:
                call_history[tool_name] = []

            # Remove old calls outside the time window
            cutoff = now - timedelta(seconds=time_window)
            call_history[tool_name] = [
                call_time for call_time in call_history[tool_name] if call_time > cutoff
            ]

            # Check rate limit
            if len(call_history[tool_name]) >= max_calls:
                logger.warning(
                    f"[RATE_LIMIT] {tool_name} - Rate limit exceeded: "
                    f"{max_calls} calls per {time_window}s"
                )
                raise ValueError(
                    f"Rate limit exceeded: max {max_calls} calls per {time_window} seconds"
                )

            # Record this call
            call_history[tool_name].append(now)

            return await fn(*args, **kwargs)

        return wrapper

    return middleware


def cache_results_async(ttl_seconds: int = 300):
    """
    Async middleware factory that caches tool results for a specified TTL.

    Args:
        ttl_seconds: Time to live for cached results in seconds

    Example:
        # Cache results for 5 minutes
        @app.tool()
        @cache_results_async(ttl_seconds=300)
        async def expensive_operation(param: str):
            return await perform_expensive_computation(param)
    """
    cache: dict[str, tuple] = {}  # key -> (result, expiry_time)

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            tool_name = getattr(fn, "_tool_name", fn.__name__)

            # Create cache key from function name and arguments
            cache_key = f"{tool_name}:{args}:{sorted(kwargs.items())}"

            # Check if we have a valid cached result
            now = time.time()
            if cache_key in cache:
                result, expiry = cache[cache_key]
                if now < expiry:
                    logger.debug(f"[CACHE] {tool_name} - Cache hit")
                    return result
                else:
                    logger.debug(f"[CACHE] {tool_name} - Cache expired")
                    del cache[cache_key]

            # Call the function and cache the result
            logger.debug(f"[CACHE] {tool_name} - Cache miss, executing function")
            result = await fn(*args, **kwargs)
            cache[cache_key] = (result, now + ttl_seconds)

            return result

        return wrapper

    return middleware


def timeout_async(seconds: int):
    """
    Async middleware factory that enforces a timeout on async tool execution.

    Args:
        seconds: Maximum execution time in seconds

    Example:
        @app.tool()
        @timeout_async(seconds=30)
        async def long_running_task(data: str):
            return await process_data(data)
    """

    def middleware(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            import asyncio

            tool_name = getattr(fn, "_tool_name", fn.__name__)

            try:
                result = await asyncio.wait_for(fn(*args, **kwargs), timeout=seconds)
                return result
            except asyncio.TimeoutError as e:
                logger.error(f"[TIMEOUT] {tool_name} - Exceeded {seconds}s timeout")
                raise TimeoutError(f"Tool {tool_name} exceeded {seconds} second timeout") from e

        return wrapper

    return middleware
