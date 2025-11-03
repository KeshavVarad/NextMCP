"""
JSON format exporter for metrics.
"""

import json
import logging
from typing import Any

from nextmcp.metrics.registry import MetricsRegistry
from nextmcp.metrics.types import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class JSONExporter:
    """
    Export metrics in JSON format.

    Provides a human-readable and machine-parseable format.
    """

    def __init__(self, registry: MetricsRegistry):
        """
        Initialize JSON exporter.

        Args:
            registry: Metrics registry to export from
        """
        self.registry = registry

    def export(self, pretty: bool = False) -> str:
        """
        Export all metrics as JSON.

        Args:
            pretty: If True, format with indentation

        Returns:
            JSON string containing all metrics
        """
        data = self.export_dict()

        if pretty:
            return json.dumps(data, indent=2, sort_keys=True)
        return json.dumps(data)

    def export_dict(self) -> dict[str, Any]:
        """
        Export all metrics as a dictionary.

        Returns:
            Dictionary containing all metrics
        """
        metrics_by_type: dict[str, list[dict[str, Any]]] = {
            "counters": [],
            "gauges": [],
            "histograms": [],
            "summaries": [],
        }

        for metric in self.registry.list_metrics():
            if isinstance(metric, Counter):
                metrics_by_type["counters"].append(self._export_counter(metric))
            elif isinstance(metric, Gauge):
                metrics_by_type["gauges"].append(self._export_gauge(metric))
            elif isinstance(metric, Histogram):
                metrics_by_type["histograms"].append(self._export_histogram(metric))
            elif isinstance(metric, Summary):
                metrics_by_type["summaries"].append(self._export_summary(metric))

        return {
            "metrics": metrics_by_type,
            "total_metrics": len(self.registry.list_metrics()),
        }

    def _export_counter(self, counter: Counter) -> dict[str, Any]:
        """Export a counter metric."""
        return {
            "name": counter.name,
            "type": "counter",
            "description": counter.description,
            "labels": counter.labels,
            "value": counter.get(),
        }

    def _export_gauge(self, gauge: Gauge) -> dict[str, Any]:
        """Export a gauge metric."""
        return {
            "name": gauge.name,
            "type": "gauge",
            "description": gauge.description,
            "labels": gauge.labels,
            "value": gauge.get(),
        }

    def _export_histogram(self, histogram: Histogram) -> dict[str, Any]:
        """Export a histogram metric."""
        buckets = histogram.get_buckets()
        count = histogram.get_count()
        total = histogram.get_sum()

        return {
            "name": histogram.name,
            "type": "histogram",
            "description": histogram.description,
            "labels": histogram.labels,
            "count": count,
            "sum": total,
            "avg": total / count if count > 0 else 0,
            "buckets": {str(k) if k != float("inf") else "+Inf": v for k, v in buckets.items()},
        }

    def _export_summary(self, summary: Summary) -> dict[str, Any]:
        """Export a summary metric."""
        count = summary.get_count()
        total = summary.get_sum()
        percentiles = summary.get_percentiles()

        return {
            "name": summary.name,
            "type": "summary",
            "description": summary.description,
            "labels": summary.labels,
            "count": count,
            "sum": total,
            "avg": total / count if count > 0 else 0,
            "percentiles": percentiles,
        }
