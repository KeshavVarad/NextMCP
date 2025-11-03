"""
Prometheus format exporter for metrics.
"""

import logging

from nextmcp.metrics.registry import MetricsRegistry
from nextmcp.metrics.types import Counter, Gauge, Histogram, Metric, Summary

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """
    Export metrics in Prometheus text format.

    See: https://prometheus.io/docs/instrumenting/exposition_formats/
    """

    def __init__(self, registry: MetricsRegistry):
        """
        Initialize Prometheus exporter.

        Args:
            registry: Metrics registry to export from
        """
        self.registry = registry

    def export(self) -> str:
        """
        Export all metrics in Prometheus format.

        Returns:
            String containing Prometheus-formatted metrics
        """
        lines = []

        for metric in self.registry.list_metrics():
            lines.extend(self._export_metric(metric))

        return "\n".join(lines) + "\n"

    def _export_metric(self, metric: Metric) -> list[str]:
        """Export a single metric."""
        lines = []

        if isinstance(metric, Counter):
            lines.extend(self._export_counter(metric))
        elif isinstance(metric, Gauge):
            lines.extend(self._export_gauge(metric))
        elif isinstance(metric, Histogram):
            lines.extend(self._export_histogram(metric))
        elif isinstance(metric, Summary):
            lines.extend(self._export_summary(metric))

        return lines

    def _export_counter(self, counter: Counter) -> list[str]:
        """Export a counter metric."""
        lines = []

        # HELP line
        if counter.description:
            lines.append(f"# HELP {counter.name} {counter.description}")

        # TYPE line
        lines.append(f"# TYPE {counter.name} counter")

        # Metric line
        label_str = counter._label_string()
        lines.append(f"{counter.name}{label_str} {counter.get()}")

        return lines

    def _export_gauge(self, gauge: Gauge) -> list[str]:
        """Export a gauge metric."""
        lines = []

        # HELP line
        if gauge.description:
            lines.append(f"# HELP {gauge.name} {gauge.description}")

        # TYPE line
        lines.append(f"# TYPE {gauge.name} gauge")

        # Metric line
        label_str = gauge._label_string()
        lines.append(f"{gauge.name}{label_str} {gauge.get()}")

        return lines

    def _export_histogram(self, histogram: Histogram) -> list[str]:
        """Export a histogram metric."""
        lines = []

        # HELP line
        if histogram.description:
            lines.append(f"# HELP {histogram.name} {histogram.description}")

        # TYPE line
        lines.append(f"# TYPE {histogram.name} histogram")

        # Bucket lines
        buckets = histogram.get_buckets()
        base_labels = histogram.labels.copy()

        for bucket_bound, count in sorted(buckets.items()):
            if bucket_bound == float("inf"):
                le_value = "+Inf"
            else:
                le_value = str(bucket_bound)

            # Create labels with 'le' (less than or equal)
            bucket_labels = {**base_labels, "le": le_value}
            label_pairs = [f'{k}="{v}"' for k, v in sorted(bucket_labels.items())]
            label_str = "{" + ",".join(label_pairs) + "}"

            lines.append(f"{histogram.name}_bucket{label_str} {count}")

        # Sum line
        label_str = histogram._label_string()
        lines.append(f"{histogram.name}_sum{label_str} {histogram.get_sum()}")

        # Count line
        lines.append(f"{histogram.name}_count{label_str} {histogram.get_count()}")

        return lines

    def _export_summary(self, summary: Summary) -> list[str]:
        """Export a summary metric."""
        lines = []

        # HELP line
        if summary.description:
            lines.append(f"# HELP {summary.name} {summary.description}")

        # TYPE line
        lines.append(f"# TYPE {summary.name} summary")

        # Percentile lines
        percentiles = summary.get_percentiles()
        base_labels = summary.labels.copy()

        for quantile_name, value in percentiles.items():
            # Convert p50 -> 0.50, p95 -> 0.95, etc.
            quantile_value = float(quantile_name[1:]) / 100.0

            quantile_labels = {**base_labels, "quantile": str(quantile_value)}
            label_pairs = [f'{k}="{v}"' for k, v in sorted(quantile_labels.items())]
            label_str = "{" + ",".join(label_pairs) + "}"

            lines.append(f"{summary.name}{label_str} {value}")

        # Sum line
        label_str = summary._label_string()
        lines.append(f"{summary.name}_sum{label_str} {summary.get_sum()}")

        # Count line
        lines.append(f"{summary.name}_count{label_str} {summary.get_count()}")

        return lines
