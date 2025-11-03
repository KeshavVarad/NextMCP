"""
Metric types for NextMCP monitoring.

Provides Counter, Gauge, Histogram, and Summary metric types.
"""

import threading
import time
from datetime import datetime, timezone


class Metric:
    """Base class for all metrics."""

    def __init__(self, name: str, description: str = "", labels: dict[str, str] | None = None):
        """
        Initialize a metric.

        Args:
            name: Metric name (e.g., "tool_invocations_total")
            description: Human-readable description
            labels: Optional labels/tags for the metric
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._lock = threading.Lock()
        self.created_at = datetime.now(timezone.utc)

    def _label_string(self) -> str:
        """Generate label string for metric identification."""
        if not self.labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(pairs) + "}"


class Counter(Metric):
    """
    Counter metric - monotonically increasing value.

    Use for: request counts, error counts, completed operations.
    """

    def __init__(self, name: str, description: str = "", labels: dict[str, str] | None = None):
        super().__init__(name, description, labels)
        self._value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        """
        Increment the counter.

        Args:
            amount: Amount to increment by (default: 1.0)
        """
        if amount < 0:
            raise ValueError("Counter can only be incremented by non-negative values")

        with self._lock:
            self._value += amount

    def get(self) -> float:
        """Get current counter value."""
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset counter to zero (mainly for testing)."""
        with self._lock:
            self._value = 0.0


class Gauge(Metric):
    """
    Gauge metric - value that can go up or down.

    Use for: temperatures, memory usage, queue sizes, active connections.
    """

    def __init__(self, name: str, description: str = "", labels: dict[str, str] | None = None):
        super().__init__(name, description, labels)
        self._value = 0.0

    def set(self, value: float) -> None:
        """
        Set the gauge to a specific value.

        Args:
            value: The value to set
        """
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """
        Increment the gauge.

        Args:
            amount: Amount to increment by (default: 1.0)
        """
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """
        Decrement the gauge.

        Args:
            amount: Amount to decrement by (default: 1.0)
        """
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value


class Histogram(Metric):
    """
    Histogram metric - tracks distribution of values.

    Use for: request durations, response sizes, temperatures over time.
    Provides count, sum, and bucketed values.
    """

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ):
        super().__init__(name, description, labels)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._bucket_counts = dict.fromkeys(self.buckets, 0)
        self._bucket_counts[float("inf")] = 0  # +Inf bucket
        self._sum = 0.0
        self._count = 0

    def observe(self, value: float) -> None:
        """
        Observe a value and add it to the histogram.

        Args:
            value: The value to observe
        """
        with self._lock:
            self._count += 1
            self._sum += value

            # Increment appropriate buckets
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1

            # Always increment +Inf bucket
            self._bucket_counts[float("inf")] += 1

    def get_count(self) -> int:
        """Get total number of observations."""
        with self._lock:
            return self._count

    def get_sum(self) -> float:
        """Get sum of all observed values."""
        with self._lock:
            return self._sum

    def get_buckets(self) -> dict[float, int]:
        """Get bucket counts."""
        with self._lock:
            return self._bucket_counts.copy()

    def time(self):
        """
        Context manager to time a code block.

        Example:
            with histogram.time():
                # Code to time
                pass
        """
        return _HistogramTimer(self)


class _HistogramTimer:
    """Context manager for timing code blocks with a histogram."""

    def __init__(self, histogram: Histogram):
        self.histogram = histogram
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        self.histogram.observe(elapsed)


class Summary(Metric):
    """
    Summary metric - similar to histogram but calculates percentiles.

    Use for: request durations, when you need percentiles (p50, p95, p99).
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        max_age: int = 600,  # 10 minutes
        max_samples: int = 1000,
    ):
        super().__init__(name, description, labels)
        self._samples: list[float] = []
        self._sum = 0.0
        self._count = 0
        self.max_age = max_age
        self.max_samples = max_samples

    def observe(self, value: float) -> None:
        """
        Observe a value.

        Args:
            value: The value to observe
        """
        with self._lock:
            self._samples.append(value)
            self._sum += value
            self._count += 1

            # Trim samples if needed
            if len(self._samples) > self.max_samples:
                self._samples = self._samples[-self.max_samples :]

    def get_count(self) -> int:
        """Get total number of observations."""
        with self._lock:
            return self._count

    def get_sum(self) -> float:
        """Get sum of all observed values."""
        with self._lock:
            return self._sum

    def get_percentile(self, percentile: float) -> float:
        """
        Calculate a percentile.

        Args:
            percentile: Percentile to calculate (0-100)

        Returns:
            Value at the given percentile
        """
        with self._lock:
            if not self._samples:
                return 0.0

            sorted_samples = sorted(self._samples)
            index = int(len(sorted_samples) * percentile / 100.0)
            index = min(index, len(sorted_samples) - 1)
            return sorted_samples[index]

    def get_percentiles(self) -> dict[str, float]:
        """Get common percentiles (p50, p90, p95, p99)."""
        return {
            "p50": self.get_percentile(50),
            "p90": self.get_percentile(90),
            "p95": self.get_percentile(95),
            "p99": self.get_percentile(99),
        }
