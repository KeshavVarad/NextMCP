"""
Tests for the NextMCP metrics system.
"""

import time

import pytest

from nextmcp import NextMCP
from nextmcp.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    MetricsConfig,
    MetricsRegistry,
    Summary,
    get_registry,
    metrics_middleware,
)
from nextmcp.metrics.exporters import JSONExporter, PrometheusExporter

# Test Metric Types


class TestCounter:
    """Test Counter metric type."""

    def test_counter_creation(self):
        counter = Counter("test_counter", "Test counter")
        assert counter.name == "test_counter"
        assert counter.description == "Test counter"
        assert counter.get() == 0.0

    def test_counter_inc(self):
        counter = Counter("test_counter")
        counter.inc()
        assert counter.get() == 1.0

        counter.inc(5.5)
        assert counter.get() == 6.5

    def test_counter_negative_inc(self):
        counter = Counter("test_counter")
        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_counter_with_labels(self):
        counter = Counter("test_counter", labels={"env": "prod"})
        assert counter.labels == {"env": "prod"}
        assert 'env="prod"' in counter._label_string()

    def test_counter_reset(self):
        counter = Counter("test_counter")
        counter.inc(10)
        counter.reset()
        assert counter.get() == 0.0


class TestGauge:
    """Test Gauge metric type."""

    def test_gauge_creation(self):
        gauge = Gauge("test_gauge", "Test gauge")
        assert gauge.name == "test_gauge"
        assert gauge.get() == 0.0

    def test_gauge_set(self):
        gauge = Gauge("test_gauge")
        gauge.set(42.5)
        assert gauge.get() == 42.5

    def test_gauge_inc_dec(self):
        gauge = Gauge("test_gauge")
        gauge.inc(10)
        assert gauge.get() == 10.0

        gauge.dec(3)
        assert gauge.get() == 7.0

        gauge.dec(10)
        assert gauge.get() == -3.0


class TestHistogram:
    """Test Histogram metric type."""

    def test_histogram_creation(self):
        histogram = Histogram("test_histogram", "Test histogram")
        assert histogram.name == "test_histogram"
        assert histogram.get_count() == 0
        assert histogram.get_sum() == 0.0

    def test_histogram_observe(self):
        histogram = Histogram("test_histogram")
        histogram.observe(0.5)
        histogram.observe(1.5)
        histogram.observe(2.5)

        assert histogram.get_count() == 3
        assert histogram.get_sum() == 4.5

    def test_histogram_buckets(self):
        histogram = Histogram("test_histogram", buckets=[1.0, 5.0, 10.0])
        histogram.observe(0.5)
        histogram.observe(2.0)
        histogram.observe(7.0)

        buckets = histogram.get_buckets()
        assert buckets[1.0] == 1  # 0.5 falls in <=1.0
        assert buckets[5.0] == 2  # 0.5 and 2.0 fall in <=5.0
        assert buckets[10.0] == 3  # All three fall in <=10.0
        assert buckets[float("inf")] == 3

    def test_histogram_timer(self):
        histogram = Histogram("test_histogram")

        with histogram.time():
            time.sleep(0.01)

        assert histogram.get_count() == 1
        assert histogram.get_sum() >= 0.01


class TestSummary:
    """Test Summary metric type."""

    def test_summary_creation(self):
        summary = Summary("test_summary", "Test summary")
        assert summary.name == "test_summary"
        assert summary.get_count() == 0
        assert summary.get_sum() == 0.0

    def test_summary_observe(self):
        summary = Summary("test_summary")
        summary.observe(1.0)
        summary.observe(2.0)
        summary.observe(3.0)

        assert summary.get_count() == 3
        assert summary.get_sum() == 6.0

    def test_summary_percentiles(self):
        summary = Summary("test_summary")
        for i in range(1, 101):
            summary.observe(float(i))

        percentiles = summary.get_percentiles()
        assert percentiles["p50"] == pytest.approx(50.0, rel=0.1)
        assert percentiles["p95"] == pytest.approx(95.0, rel=0.1)
        assert percentiles["p99"] == pytest.approx(99.0, rel=0.1)


# Test Registry


class TestMetricsRegistry:
    """Test MetricsRegistry."""

    def test_registry_creation(self):
        registry = MetricsRegistry()
        assert len(registry) == 0

    def test_register_metric(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter")

        registered = registry.register(counter)
        assert registered == counter
        assert len(registry) == 1

    def test_duplicate_registration(self):
        registry = MetricsRegistry()
        counter1 = Counter("test_counter")
        counter2 = Counter("test_counter")

        registry.register(counter1)
        # Same type, should return existing
        existing = registry.register(counter2)
        assert existing == counter1

    def test_different_type_conflict(self):
        registry = MetricsRegistry()
        counter = Counter("test_metric")
        gauge = Gauge("test_metric")

        registry.register(counter)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(gauge)

    def test_get_metric(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter")
        registry.register(counter)

        retrieved = registry.get("test_counter")
        assert retrieved == counter

    def test_get_or_create(self):
        registry = MetricsRegistry()

        # Create new
        counter = registry.get_or_create("test_counter", Counter, "Test desc")
        assert counter.name == "test_counter"
        assert len(registry) == 1

        # Get existing
        same_counter = registry.get_or_create("test_counter", Counter)
        assert same_counter == counter
        assert len(registry) == 1

    def test_unregister(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter")
        registry.register(counter)

        assert registry.unregister("test_counter") is True
        assert len(registry) == 0
        assert registry.unregister("test_counter") is False

    def test_list_metrics(self):
        registry = MetricsRegistry()
        counter = Counter("counter1")
        gauge = Gauge("gauge1")

        registry.register(counter)
        registry.register(gauge)

        metrics = registry.list_metrics()
        assert len(metrics) == 2
        assert counter in metrics
        assert gauge in metrics

    def test_clear(self):
        registry = MetricsRegistry()
        registry.register(Counter("c1"))
        registry.register(Gauge("g1"))

        registry.clear()
        assert len(registry) == 0

    def test_global_registry(self):
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2


# Test Collector


class TestMetricsCollector:
    """Test MetricsCollector."""

    def test_collector_creation(self):
        collector = MetricsCollector(prefix="test")
        assert collector.prefix == "test"

    def test_counter_method(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        counter = collector.counter("requests")
        assert counter.name == "test_requests"
        # Check metric was created and stored
        assert counter is not None
        assert isinstance(counter, Counter)

    def test_gauge_method(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        gauge = collector.gauge("active")
        assert gauge.name == "test_active"

    def test_histogram_method(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        histogram = collector.histogram("duration")
        assert histogram.name == "test_duration"

    def test_inc_counter(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        collector.inc_counter("requests", 5)
        # Counter is created by the collector
        counter = collector.counter("requests")
        assert counter.get() == 5.0

    def test_set_gauge(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        collector.set_gauge("temperature", 72.5)
        gauge = collector.gauge("temperature")
        assert gauge.get() == 72.5

    def test_observe_histogram(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        collector.observe_histogram("duration", 1.5)
        histogram = collector.histogram("duration")
        assert histogram.get_count() == 1

    def test_time_histogram(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        with collector.time_histogram("duration"):
            time.sleep(0.01)

        histogram = collector.histogram("duration")
        # Should have exactly one observation from the context manager
        assert histogram.get_count() == 1
        # Duration should be at least what we slept
        assert histogram.get_sum() >= 0.01

    def test_get_all_metrics(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")

        collector.inc_counter("requests", 10)
        collector.set_gauge("active", 5)

        all_metrics = collector.get_all_metrics()
        assert "test_requests" in all_metrics
        assert "test_active" in all_metrics


# Test Middleware


class TestMetricsMiddleware:
    """Test metrics middleware."""

    def test_middleware_sync_tool(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")
        config = MetricsConfig(enabled=True)

        middleware = metrics_middleware(collector=collector, config=config)

        @middleware
        def test_tool():
            return "result"

        result = test_tool()
        assert result == "result"

        # Check that middleware created metrics
        metrics = registry.list_metrics()
        metric_names = [m.name for m in metrics]

        # Should have invocation, duration, and completed metrics
        assert any("invocations" in name for name in metric_names)
        assert any("duration" in name for name in metric_names)
        assert any("completed" in name for name in metric_names)

    def test_middleware_tracks_success(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")
        config = MetricsConfig(enabled=True)

        middleware = metrics_middleware(collector=collector, config=config)

        @middleware
        def test_tool():
            return "success"

        result = test_tool()
        assert result == "success"

        # Check that completed metric shows success
        metrics = registry.list_metrics()
        completed_metrics = [
            m for m in metrics if "completed" in m.name and "status" in str(m.labels)
        ]

        # Should have at least one completed metric
        assert len(completed_metrics) > 0

        # Check that at least one has success status
        success_metrics = [m for m in completed_metrics if m.labels.get("status") == "success"]
        assert len(success_metrics) > 0

    def test_middleware_tracks_errors(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")
        config = MetricsConfig(enabled=True)

        middleware = metrics_middleware(collector=collector, config=config)

        @middleware
        def test_tool():
            raise ValueError("test error")

        # Should still raise the error
        with pytest.raises(ValueError, match="test error"):
            test_tool()

        # Check that error metrics were created
        metrics = registry.list_metrics()
        error_metrics = [m for m in metrics if "errors" in m.name]

        # Should have error counter
        assert len(error_metrics) > 0

        # Check that completed metric shows error status
        completed_metrics = [
            m for m in metrics if "completed" in m.name and "status" in str(m.labels)
        ]
        error_completed = [m for m in completed_metrics if m.labels.get("status") == "error"]
        assert len(error_completed) > 0

    def test_middleware_disabled(self):
        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")
        config = MetricsConfig(enabled=False)

        middleware = metrics_middleware(collector=collector, config=config)

        @middleware
        def test_tool():
            return "result"

        test_tool()

        # Should not create metrics
        assert len(registry) == 0

    @pytest.mark.asyncio
    async def test_middleware_async_tool(self):
        import asyncio

        registry = MetricsRegistry()
        collector = MetricsCollector(registry=registry, prefix="test")
        config = MetricsConfig(enabled=True)

        middleware = metrics_middleware(collector=collector, config=config)

        @middleware
        async def test_tool():
            await asyncio.sleep(0.01)
            return "result"

        result = await test_tool()
        assert result == "result"

        # Check that middleware created metrics for async tool
        metrics = registry.list_metrics()
        metric_names = [m.name for m in metrics]

        # Should have metrics just like sync tools
        assert any("invocations" in name for name in metric_names)
        assert any("duration" in name for name in metric_names)


# Test Exporters


class TestPrometheusExporter:
    """Test Prometheus exporter."""

    def test_export_counter(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter", "Test counter description")
        counter.inc(42)
        registry.register(counter)

        exporter = PrometheusExporter(registry)
        output = exporter.export()

        assert "# HELP test_counter Test counter description" in output
        assert "# TYPE test_counter counter" in output
        assert "test_counter 42" in output

    def test_export_gauge(self):
        registry = MetricsRegistry()
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(72.5)
        registry.register(gauge)

        exporter = PrometheusExporter(registry)
        output = exporter.export()

        assert "# TYPE test_gauge gauge" in output
        assert "test_gauge 72.5" in output

    def test_export_histogram(self):
        registry = MetricsRegistry()
        histogram = Histogram("test_histogram", "Test histogram", buckets=[1.0, 5.0])
        histogram.observe(0.5)
        histogram.observe(2.0)
        registry.register(histogram)

        exporter = PrometheusExporter(registry)
        output = exporter.export()

        assert "# TYPE test_histogram histogram" in output
        assert "test_histogram_bucket" in output
        assert "test_histogram_sum" in output
        assert "test_histogram_count" in output

    def test_export_with_labels(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter", labels={"env": "prod", "region": "us"})
        counter.inc(10)
        registry.register(counter)

        exporter = PrometheusExporter(registry)
        output = exporter.export()

        assert 'env="prod"' in output
        assert 'region="us"' in output


class TestJSONExporter:
    """Test JSON exporter."""

    def test_export_json(self):
        import json

        registry = MetricsRegistry()
        counter = Counter("test_counter")
        counter.inc(10)
        registry.register(counter)

        exporter = JSONExporter(registry)
        output = exporter.export()

        data = json.loads(output)
        assert "metrics" in data
        assert "total_metrics" in data
        assert data["total_metrics"] == 1

    def test_export_pretty(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter")
        counter.inc(5)
        registry.register(counter)

        exporter = JSONExporter(registry)
        output = exporter.export(pretty=True)

        # Pretty JSON has newlines
        assert "\n" in output
        assert "  " in output

    def test_export_dict(self):
        registry = MetricsRegistry()
        counter = Counter("test_counter")
        gauge = Gauge("test_gauge")
        counter.inc(1)
        gauge.set(2)
        registry.register(counter)
        registry.register(gauge)

        exporter = JSONExporter(registry)
        data = exporter.export_dict()

        assert len(data["metrics"]["counters"]) == 1
        assert len(data["metrics"]["gauges"]) == 1


# Test Integration


class TestNextMCPIntegration:
    """Test metrics integration with NextMCP."""

    def test_metrics_property(self):
        app = NextMCP("test-app")
        collector = app.metrics
        assert isinstance(collector, MetricsCollector)
        assert collector.prefix == "test-app"

    def test_enable_metrics(self):
        # Clear registry before test
        registry = get_registry()
        registry.clear()

        app = NextMCP("test-app")
        app.enable_metrics()
        assert app._metrics_enabled is True

    def test_metrics_collect_tool_invocations(self):
        # Clear registry before test
        registry = get_registry()
        registry.clear()

        app = NextMCP("test-app")
        app.enable_metrics()

        @app.tool()
        def test_tool():
            return "result"

        # Invoke the tool
        test_tool()

        # Get metrics
        metrics = registry.list_metrics()

        # Should have invocation metrics
        invocation_metrics = [m for m in metrics if "invocations" in m.name]
        assert len(invocation_metrics) > 0

    def test_get_metrics_prometheus(self):
        # Clear registry before test
        registry = get_registry()
        registry.clear()

        app = NextMCP("test-app")
        app.enable_metrics()

        @app.tool()
        def test_tool():
            return "result"

        test_tool()

        prometheus_output = app.get_metrics_prometheus()
        assert "test-app" in prometheus_output or "test_tool" in prometheus_output

    def test_get_metrics_json(self):
        import json

        # Clear registry before test
        registry = get_registry()
        registry.clear()

        app = NextMCP("test-app")
        app.enable_metrics()

        @app.tool()
        def test_tool():
            return "result"

        test_tool()

        json_output = app.get_metrics_json()
        data = json.loads(json_output)
        assert "metrics" in data

    def test_custom_metric_in_tool(self):
        app = NextMCP("test-app")

        @app.tool()
        def test_tool():
            app.metrics.inc_counter("custom_counter")
            return "result"

        test_tool()

        registry = get_registry()
        counter = registry.get("test-app_custom_counter")
        assert counter is not None
        assert counter.get() == 1.0
