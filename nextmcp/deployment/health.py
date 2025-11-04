"""
Health check system for NextMCP applications.

Provides health and readiness endpoints for production deployments:
- /health: Liveness probe (is the app running?)
- /health/ready: Readiness probe (is the app ready to serve traffic?)
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


class HealthCheck:
    """
    Health check system for monitoring application health.

    Supports both liveness and readiness checks:
    - Liveness: Is the application running?
    - Readiness: Is the application ready to serve traffic?

    Example:
        >>> health = HealthCheck()
        >>> health.add_readiness_check("database", check_database)
        >>> result = health.check_health()
        >>> print(result["status"])  # "healthy"
    """

    def __init__(self):
        self._start_time = time.time()
        self._liveness_checks: dict[str, Callable[[], HealthCheckResult]] = {}
        self._readiness_checks: dict[str, Callable[[], HealthCheckResult]] = {}

    def add_liveness_check(
        self, name: str, check_fn: Callable[[], bool | HealthCheckResult]
    ) -> None:
        """
        Add a liveness check.

        Liveness checks determine if the application is running.
        If liveness checks fail, the application should be restarted.

        Args:
            name: Name of the check
            check_fn: Function that returns True/False or HealthCheckResult
        """
        self._liveness_checks[name] = self._wrap_check_fn(name, check_fn)

    def add_readiness_check(
        self, name: str, check_fn: Callable[[], bool | HealthCheckResult]
    ) -> None:
        """
        Add a readiness check.

        Readiness checks determine if the application is ready to serve traffic.
        If readiness checks fail, traffic should not be routed to this instance.

        Args:
            name: Name of the check
            check_fn: Function that returns True/False or HealthCheckResult
        """
        self._readiness_checks[name] = self._wrap_check_fn(name, check_fn)

    def _wrap_check_fn(
        self, name: str, check_fn: Callable[[], bool | HealthCheckResult]
    ) -> Callable[[], HealthCheckResult]:
        """Wrap a check function to always return HealthCheckResult."""

        def wrapper() -> HealthCheckResult:
            start = time.time()
            try:
                result = check_fn()
                duration = (time.time() - start) * 1000

                # If function returns bool, convert to HealthCheckResult
                if isinstance(result, bool):
                    return HealthCheckResult(
                        name=name,
                        status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                        duration_ms=duration,
                    )
                # If function returns HealthCheckResult, update duration
                result.duration_ms = duration
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {e}",
                    duration_ms=duration,
                )

        return wrapper

    def check_health(self) -> dict[str, Any]:
        """
        Perform liveness health check.

        Returns:
            Health check result with status and uptime
        """
        uptime = time.time() - self._start_time

        # Run liveness checks
        checks = {}
        overall_status = HealthStatus.HEALTHY

        for name, check_fn in self._liveness_checks.items():
            result = check_fn()
            checks[name] = {
                "status": result.status.value,
                "message": result.message,
                "duration_ms": round(result.duration_ms, 2),
                "details": result.details,
            }
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "uptime_seconds": round(uptime, 2),
            "checks": checks,
        }

    def check_readiness(self) -> dict[str, Any]:
        """
        Perform readiness health check.

        Returns:
            Readiness check result with status and check details
        """
        checks = {}
        overall_ready = True

        for name, check_fn in self._readiness_checks.items():
            result = check_fn()
            checks[name] = {
                "status": result.status.value,
                "message": result.message,
                "duration_ms": round(result.duration_ms, 2),
                "details": result.details,
            }
            if result.status != HealthStatus.HEALTHY:
                overall_ready = False

        return {
            "ready": overall_ready,
            "checks": checks,
        }

    def is_healthy(self) -> bool:
        """Check if application is healthy."""
        result = self.check_health()
        return result["status"] == HealthStatus.HEALTHY.value

    def is_ready(self) -> bool:
        """Check if application is ready."""
        result = self.check_readiness()
        return result["ready"]


# Built-in health checks


def check_always_healthy() -> HealthCheckResult:
    """A health check that always returns healthy."""
    return HealthCheckResult(
        name="always_healthy",
        status=HealthStatus.HEALTHY,
        message="Application is running",
    )
