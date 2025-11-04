"""
Metrics Example - Demonstrates NextMCP metrics and monitoring.

This example shows:
- Automatic metrics collection
- Custom metrics
- Prometheus format export
- JSON format export
"""

import random
import time

from nextmcp import NextMCP, setup_logging

# Setup logging
setup_logging(level="INFO")

# Create the application with metrics enabled
app = NextMCP(name="metrics-demo", description="Demonstration of NextMCP metrics system")

# Enable automatic metrics collection
app.enable_metrics(collect_tool_metrics=True, labels={"environment": "demo", "version": "1.0"})

print("=" * 70)
print("NextMCP Metrics & Monitoring Demo")
print("=" * 70)
print()


@app.tool()
def fast_operation(value: int) -> dict:
    """A fast operation that completes quickly."""
    return {"result": value * 2, "duration": "fast"}


@app.tool()
def slow_operation(value: int) -> dict:
    """A slow operation that takes some time."""
    # Simulate slow processing
    time.sleep(random.uniform(0.1, 0.3))
    return {"result": value**2, "duration": "slow"}


@app.tool()
def custom_metrics_demo(count: int) -> dict:
    """Demonstrates custom metrics in a tool."""
    # Custom counter
    app.metrics.inc_counter("custom_operations", amount=count)

    # Custom gauge
    app.metrics.set_gauge("current_value", float(count))

    # Custom histogram
    app.metrics.observe_histogram("value_distribution", float(count))

    return {"processed": count, "custom_metrics": "recorded"}


@app.tool()
def error_demo() -> dict:
    """Demonstrates error tracking."""
    if random.random() < 0.3:  # 30% chance of error
        raise ValueError("Random error occurred")
    return {"status": "success"}


# Demonstrate the metrics system
print("Testing Tools & Collecting Metrics:")
print("-" * 70)

# Run fast operations
print("\n1. Fast operations:")
for i in range(5):
    result = fast_operation(i)
    print(f"   fast_operation({i}) = {result['result']}")

# Run slow operations
print("\n2. Slow operations:")
for i in range(3):
    result = slow_operation(i)
    print(f"   slow_operation({i}) = {result['result']}")

# Custom metrics
print("\n3. Custom metrics:")
for i in [10, 20, 30]:
    result = custom_metrics_demo(i)
    print(f"   custom_metrics_demo({i}) = {result}")

# Error handling
print("\n4. Error handling (some may fail):")
for _i in range(5):
    try:
        result = error_demo()
        print(f"   error_demo() = {result['status']}")
    except ValueError as e:
        print(f"   error_demo() = ERROR: {e}")

print()
print("=" * 70)
print("Metrics Collection Summary")
print("=" * 70)

# Get metrics in JSON format
print("\nJSON Metrics:")
print("-" * 70)
json_metrics = app.get_metrics_json(pretty=True)
print(json_metrics)

print()
print("=" * 70)
print("Prometheus Format Metrics:")
print("-" * 70)
prometheus_metrics = app.get_metrics_prometheus()
print(prometheus_metrics)

print()
print("=" * 70)
print("Demo Complete!")
print("=" * 70)
print()
print("Metrics collected:")
print("  - Tool invocation counts")
print("  - Tool execution durations (histograms)")
print("  - Success/failure rates")
print("  - Error tracking by type")
print("  - Custom counters, gauges, and histograms")
print()
print("The metrics can be:")
print("  - Exported in Prometheus format for scraping")
print("  - Exported in JSON for APIs")
print("  - Queried programmatically")
print()
print("To run as an MCP server, uncomment the app.run() line below.")
print()

# Uncomment to run as MCP server
# if __name__ == "__main__":
#     app.run()
