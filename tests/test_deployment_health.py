"""
Tests for the health check system.

Tests health check functionality including:
- Basic health checks
- Readiness checks
- Custom health checks
- Error handling
"""

from nextmcp.deployment.health import HealthCheck, HealthCheckResult, HealthStatus


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_create_result(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"cpu": "50%"},
            duration_ms=10.5,
        )

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details == {"cpu": "50%"}
        assert result.duration_ms == 10.5

    def test_default_values(self):
        """Test default values in health check result."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
        )

        assert result.message == ""
        assert result.details == {}
        assert result.duration_ms == 0.0


class TestHealthCheck:
    """Test HealthCheck class."""

    def test_initialization(self):
        """Test health check initialization."""
        health = HealthCheck()
        assert health.is_healthy()
        assert health.is_ready()

    def test_basic_health_check(self):
        """Test basic health check."""
        health = HealthCheck()
        result = health.check_health()

        assert result["status"] == "healthy"
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0
        assert result["checks"] == {}

    def test_basic_readiness_check(self):
        """Test basic readiness check."""
        health = HealthCheck()
        result = health.check_readiness()

        assert result["ready"] is True
        assert result["checks"] == {}

    def test_add_liveness_check_bool(self):
        """Test adding a liveness check that returns bool."""
        health = HealthCheck()

        def always_healthy():
            return True

        health.add_liveness_check("test", always_healthy)
        result = health.check_health()

        assert result["status"] == "healthy"
        assert "test" in result["checks"]
        assert result["checks"]["test"]["status"] == "healthy"

    def test_add_liveness_check_unhealthy(self):
        """Test liveness check that fails."""
        health = HealthCheck()

        def always_unhealthy():
            return False

        health.add_liveness_check("test", always_unhealthy)
        result = health.check_health()

        assert result["status"] == "unhealthy"
        assert "test" in result["checks"]
        assert result["checks"]["test"]["status"] == "unhealthy"

    def test_add_liveness_check_result(self):
        """Test adding a liveness check that returns HealthCheckResult."""
        health = HealthCheck()

        def custom_check():
            return HealthCheckResult(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="Custom check passed",
                details={"detail": "value"},
            )

        health.add_liveness_check("custom", custom_check)
        result = health.check_health()

        assert result["status"] == "healthy"
        assert "custom" in result["checks"]
        assert result["checks"]["custom"]["status"] == "healthy"
        assert result["checks"]["custom"]["message"] == "Custom check passed"
        assert result["checks"]["custom"]["details"] == {"detail": "value"}

    def test_add_readiness_check(self):
        """Test adding a readiness check."""
        health = HealthCheck()

        def database_ready():
            return True

        health.add_readiness_check("database", database_ready)
        result = health.check_readiness()

        assert result["ready"] is True
        assert "database" in result["checks"]
        assert result["checks"]["database"]["status"] == "healthy"

    def test_readiness_check_not_ready(self):
        """Test readiness check that fails."""
        health = HealthCheck()

        def database_not_ready():
            return False

        health.add_readiness_check("database", database_not_ready)
        result = health.check_readiness()

        assert result["ready"] is False
        assert "database" in result["checks"]
        assert result["checks"]["database"]["status"] == "unhealthy"

    def test_multiple_health_checks(self):
        """Test multiple health checks."""
        health = HealthCheck()

        def check1():
            return True

        def check2():
            return True

        health.add_liveness_check("check1", check1)
        health.add_liveness_check("check2", check2)
        result = health.check_health()

        assert result["status"] == "healthy"
        assert len(result["checks"]) == 2
        assert "check1" in result["checks"]
        assert "check2" in result["checks"]

    def test_one_unhealthy_makes_all_unhealthy(self):
        """Test that one unhealthy check makes overall status unhealthy."""
        health = HealthCheck()

        def healthy_check():
            return True

        def unhealthy_check():
            return False

        health.add_liveness_check("healthy", healthy_check)
        health.add_liveness_check("unhealthy", unhealthy_check)
        result = health.check_health()

        assert result["status"] == "unhealthy"

    def test_degraded_status(self):
        """Test degraded health status."""
        health = HealthCheck()

        def degraded_check():
            return HealthCheckResult(
                name="degraded",
                status=HealthStatus.DEGRADED,
                message="Service degraded",
            )

        health.add_liveness_check("degraded", degraded_check)
        result = health.check_health()

        assert result["status"] == "degraded"

    def test_unhealthy_overrides_degraded(self):
        """Test that unhealthy status overrides degraded."""
        health = HealthCheck()

        def degraded_check():
            return HealthCheckResult(
                name="degraded",
                status=HealthStatus.DEGRADED,
            )

        def unhealthy_check():
            return False

        health.add_liveness_check("degraded", degraded_check)
        health.add_liveness_check("unhealthy", unhealthy_check)
        result = health.check_health()

        assert result["status"] == "unhealthy"

    def test_check_handles_exception(self):
        """Test that exceptions in checks are caught."""
        health = HealthCheck()

        def failing_check():
            raise ValueError("Something went wrong")

        health.add_liveness_check("failing", failing_check)
        result = health.check_health()

        assert result["status"] == "unhealthy"
        assert "failing" in result["checks"]
        assert result["checks"]["failing"]["status"] == "unhealthy"
        assert "Something went wrong" in result["checks"]["failing"]["message"]

    def test_is_healthy_method(self):
        """Test is_healthy convenience method."""
        health = HealthCheck()

        assert health.is_healthy() is True

        health.add_liveness_check("fail", lambda: False)
        assert health.is_healthy() is False

    def test_is_ready_method(self):
        """Test is_ready convenience method."""
        health = HealthCheck()

        assert health.is_ready() is True

        health.add_readiness_check("fail", lambda: False)
        assert health.is_ready() is False

    def test_duration_measurement(self):
        """Test that check duration is measured."""
        import time

        health = HealthCheck()

        def slow_check():
            time.sleep(0.01)  # 10ms
            return True

        health.add_liveness_check("slow", slow_check)
        result = health.check_health()

        assert result["checks"]["slow"]["duration_ms"] > 5  # At least 5ms

    def test_readiness_checks_independent(self):
        """Test that readiness checks don't affect liveness."""
        health = HealthCheck()

        health.add_liveness_check("live", lambda: True)
        health.add_readiness_check("ready", lambda: False)

        # Health should be good
        assert health.is_healthy() is True

        # But not ready
        assert health.is_ready() is False

    def test_multiple_readiness_checks(self):
        """Test multiple readiness checks."""
        health = HealthCheck()

        health.add_readiness_check("db", lambda: True)
        health.add_readiness_check("cache", lambda: True)

        result = health.check_readiness()
        assert result["ready"] is True
        assert len(result["checks"]) == 2

    def test_one_failing_readiness_check(self):
        """Test that one failing readiness check makes app not ready."""
        health = HealthCheck()

        health.add_readiness_check("db", lambda: True)
        health.add_readiness_check("cache", lambda: False)

        result = health.check_readiness()
        assert result["ready"] is False
