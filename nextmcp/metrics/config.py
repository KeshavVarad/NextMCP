"""
Configuration for NextMCP metrics system.
"""

from dataclasses import dataclass, field


@dataclass
class MetricsConfig:
    """
    Configuration for metrics collection.

    Example:
        config = MetricsConfig(
            enabled=True,
            collect_tool_metrics=True,
            prometheus_enabled=True,
        )
    """

    enabled: bool = True
    """Enable metrics collection"""

    collect_tool_metrics: bool = True
    """Collect metrics for tool invocations"""

    collect_system_metrics: bool = False
    """Collect system metrics (CPU, memory, etc.)"""

    collect_transport_metrics: bool = False
    """Collect transport-level metrics (WebSocket, HTTP)"""

    prefix: str = "nextmcp"
    """Prefix for all metric names"""

    labels: dict[str, str] = field(default_factory=dict)
    """Global labels to apply to all metrics"""

    prometheus_enabled: bool = False
    """Enable Prometheus exporter"""

    prometheus_port: int | None = None
    """Port for Prometheus metrics endpoint (if None, use main app)"""

    json_enabled: bool = True
    """Enable JSON metrics export"""

    sample_rate: float = 1.0
    """Sampling rate for metrics (0.0 to 1.0)"""

    def __post_init__(self):
        """Validate configuration."""
        if not 0.0 <= self.sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")
