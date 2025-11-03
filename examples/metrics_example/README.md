# Metrics & Monitoring Example

This example demonstrates NextMCP's built-in metrics and monitoring system.

## Features

- **Automatic Metrics Collection**: Track tool invocations, execution times, and success/failure rates
- **Custom Metrics**: Add your own counters, gauges, histograms, and summaries
- **Multiple Export Formats**: Prometheus and JSON formats supported
- **Production Ready**: Thread-safe, low overhead, standards-compliant

## Running the Example

```bash
cd examples/metrics_example
python app.py
```

You should see:
1. Tool invocations with different characteristics (fast, slow, errors)
2. Custom metrics being recorded
3. JSON format metrics output
4. Prometheus format metrics output

## What's Being Demonstrated

### 1. Automatic Metrics Collection

```python
app = NextMCP("metrics-demo")
app.enable_metrics()  # That's it! Auto-metrics enabled

@app.tool()
def my_tool():
    return "result"
```

Automatically tracks:
- `tool_invocations_total` - Counter of invocations
- `tool_duration_seconds` - Histogram of execution times
- `tool_completed_total` - Counter of completions (by status)
- `tool_errors_total` - Counter of errors (by error type)
- `tool_active_invocations` - Gauge of currently executing tools

### 2. Custom Metrics

```python
@app.tool()
def my_tool(count: int):
    # Custom counter
    app.metrics.inc_counter("custom_operations", amount=count)

    # Custom gauge
    app.metrics.set_gauge("current_value", float(count))

    # Custom histogram
    app.metrics.observe_histogram("value_distribution", float(count))

    return {"processed": count}
```

### 3. Metrics Export

#### JSON Format
```python
json_data = app.get_metrics_json(pretty=True)
print(json_data)
```

Output:
```json
{
  "metrics": {
    "counters": [
      {
        "name": "metrics-demo_tool_invocations_total",
        "type": "counter",
        "labels": {"tool": "my_tool"},
        "value": 42.0
      }
    ],
    "gauges": [...],
    "histograms": [...],
    "summaries": [...]
  },
  "total_metrics": 15
}
```

#### Prometheus Format
```python
prometheus_data = app.get_metrics_prometheus()
print(prometheus_data)
```

Output:
```
# HELP metrics-demo_tool_invocations_total Total tool invocations
# TYPE metrics-demo_tool_invocations_total counter
metrics-demo_tool_invocations_total{tool="my_tool"} 42.0

# HELP metrics-demo_tool_duration_seconds Tool execution duration
# TYPE metrics-demo_tool_duration_seconds histogram
metrics-demo_tool_duration_seconds_bucket{tool="my_tool",le="0.005"} 10
metrics-demo_tool_duration_seconds_bucket{tool="my_tool",le="0.01"} 25
metrics-demo_tool_duration_seconds_sum{tool="my_tool"} 1.234
metrics-demo_tool_duration_seconds_count{tool="my_tool"} 42
```

## Metric Types

### Counter
Monotonically increasing value. Use for: request counts, error counts, completed operations.

```python
counter = app.metrics.counter("requests_total")
counter.inc()  # Increment by 1
counter.inc(5)  # Increment by 5
```

### Gauge
Value that can go up or down. Use for: active connections, queue sizes, temperatures.

```python
gauge = app.metrics.gauge("active_connections")
gauge.set(10)  # Set to specific value
gauge.inc()    # Increment
gauge.dec()    # Decrement
```

### Histogram
Distribution of values with buckets. Use for: request durations, response sizes.

```python
histogram = app.metrics.histogram("request_duration_seconds")
histogram.observe(0.25)  # Record a value

# Or use as timer
with app.metrics.time_histogram("request_duration_seconds"):
    # Code to time
    pass
```

### Summary
Similar to histogram but calculates percentiles. Use for: percentile calculations (p50, p95, p99).

```python
summary = app.metrics.summary("latency_seconds")
summary.observe(0.15)

percentiles = summary.get_percentiles()
# {'p50': 0.15, 'p90': 0.28, 'p95': 0.35, 'p99': 0.42}
```

## Configuration Options

```python
from nextmcp import NextMCP, MetricsConfig

# Basic enable
app.enable_metrics()

# With options
app.enable_metrics(
    collect_tool_metrics=True,      # Track tool invocations
    collect_system_metrics=False,   # Track CPU/memory (future)
    collect_transport_metrics=False, # Track WebSocket/HTTP (future)
    labels={"env": "prod", "region": "us-west"}  # Global labels
)

# Advanced config
config = MetricsConfig(
    enabled=True,
    prefix="my-app",  # Metric name prefix
    sample_rate=1.0,  # Sample 100% of requests
    labels={"service": "api"}
)
```

## Metrics with Labels

Labels allow you to slice and dice your metrics:

```python
# Create metric with labels
counter = app.metrics.counter(
    "api_requests_total",
    labels={"method": "GET", "endpoint": "/users"}
)
counter.inc()

# Each unique label combination creates a separate metric
counter2 = app.metrics.counter(
    "api_requests_total",
    labels={"method": "POST", "endpoint": "/users"}
)
counter2.inc()
```

## Integration with Monitoring Systems

### Prometheus

1. Expose metrics endpoint:
```python
@app.tool()
def get_metrics():
    return app.get_metrics_prometheus()
```

2. Configure Prometheus to scrape your endpoint

3. Create dashboards and alerts in Grafana

### Custom Monitoring

```python
# Get all metrics as dict
metrics = app.metrics.get_all_metrics()

# Send to your monitoring system
for metric_name, metric_data in metrics.items():
    send_to_monitoring(metric_name, metric_data)
```

## Performance Impact

The metrics system is designed for minimal overhead:
- **Thread-safe**: Uses locks only when modifying metrics
- **Low memory**: In-memory storage with configurable limits
- **Fast**: Sub-millisecond overhead per metric operation
- **Optional**: Disabled by default, zero cost if not used

Typical overhead with metrics enabled: <1% CPU, <10MB memory

## Best Practices

1. **Use descriptive names**: `http_requests_total` not `requests`
2. **Add labels sparingly**: Too many labels = too many metrics
3. **Consistent naming**: Use `_total` suffix for counters, `_seconds` for durations
4. **Avoid high-cardinality labels**: Don't use user IDs, timestamps, etc. as labels
5. **Document your metrics**: Add descriptions to custom metrics

## Troubleshooting

### Metrics not appearing

Check that metrics are enabled:
```python
app.enable_metrics()
```

### Too many metrics

Reduce label cardinality or use sampling:
```python
config = MetricsConfig(sample_rate=0.1)  # Sample 10% of requests
```

### Memory usage

Metrics are stored in-memory. For large-scale deployments, use sampling or external storage.

## Next Steps

- Add Prometheus scraping endpoint
- Set up Grafana dashboards
- Configure alerting rules
- Implement custom metrics for business logic
- Add system metrics (CPU, memory)
- Add transport metrics (WebSocket connections)

## Resources

- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)
- [Metric Naming Best Practices](https://prometheus.io/docs/practices/naming/)
- [NextMCP Documentation](../../README.md)
