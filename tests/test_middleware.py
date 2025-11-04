"""
Unit tests for nextmcp.middleware module
"""

import pytest

from nextmcp.middleware import (
    cache_results,
    error_handler,
    log_calls,
    rate_limit,
    require_auth,
    validate_inputs,
)


def test_log_calls_middleware():
    """Test that log_calls middleware logs function calls"""

    @log_calls
    def add(a: int, b: int) -> int:
        return a + b

    result = add(2, 3)
    assert result == 5


def test_error_handler_middleware():
    """Test that error_handler catches exceptions and returns error dict"""

    @error_handler
    def failing_function():
        raise ValueError("Test error")

    result = failing_function()
    assert result["error"] is True
    assert result["error_type"] == "ValueError"
    assert "Test error" in result["error_message"]


def test_require_auth_success():
    """Test authentication middleware with valid key"""
    auth_middleware = require_auth(valid_keys={"secret123"})

    @auth_middleware
    def protected_function(auth_key: str, data: str):
        return f"Protected: {data}"

    result = protected_function(auth_key="secret123", data="test")
    assert result == "Protected: test"


def test_require_auth_failure():
    """Test authentication middleware with invalid key"""
    auth_middleware = require_auth(valid_keys={"secret123"})

    @auth_middleware
    def protected_function(auth_key: str, data: str):
        return f"Protected: {data}"

    with pytest.raises(ValueError, match="Authentication failed"):
        protected_function(auth_key="wrong", data="test")


def test_require_auth_missing_key():
    """Test authentication middleware with missing key"""
    auth_middleware = require_auth(valid_keys={"secret123"})

    @auth_middleware
    def protected_function(data: str):
        return f"Protected: {data}"

    with pytest.raises(ValueError, match="Authentication required"):
        protected_function(data="test")


def test_rate_limit_middleware():
    """Test rate limiting middleware"""
    # Allow 3 calls per 10 seconds
    limited = rate_limit(max_calls=3, time_window=10)

    @limited
    def rate_limited_function():
        return "success"

    # First 3 calls should succeed
    assert rate_limited_function() == "success"
    assert rate_limited_function() == "success"
    assert rate_limited_function() == "success"

    # 4th call should fail
    with pytest.raises(ValueError, match="Rate limit exceeded"):
        rate_limited_function()


def test_validate_inputs_middleware():
    """Test input validation middleware"""

    def validate_positive(value):
        if value <= 0:
            raise ValueError("Must be positive")
        return value

    @validate_inputs(amount=validate_positive)
    def process_payment(amount: float):
        return {"charged": amount}

    # Valid input
    result = process_payment(amount=100.0)
    assert result == {"charged": 100.0}

    # Invalid input
    with pytest.raises(ValueError, match="Validation failed"):
        process_payment(amount=-50.0)


def test_cache_results_middleware():
    """Test caching middleware"""
    call_count = {"count": 0}

    @cache_results(ttl_seconds=5)
    def expensive_function(x: int):
        call_count["count"] += 1
        return x * 2

    # First call - should execute function
    result1 = expensive_function(5)
    assert result1 == 10
    assert call_count["count"] == 1

    # Second call with same args - should use cache
    result2 = expensive_function(5)
    assert result2 == 10
    assert call_count["count"] == 1  # Count unchanged

    # Call with different args - should execute function
    result3 = expensive_function(10)
    assert result3 == 20
    assert call_count["count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
