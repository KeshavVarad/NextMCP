"""
Deployment utilities for NextMCP applications.

This module provides tools for deploying NextMCP applications to production:
- Health check endpoints
- Graceful shutdown handling
- Docker templates
- Platform-specific configurations
"""

from nextmcp.deployment.health import HealthCheck, HealthStatus
from nextmcp.deployment.lifecycle import GracefulShutdown
from nextmcp.deployment.templates import TemplateRenderer, detect_app_config

__all__ = [
    "HealthCheck",
    "HealthStatus",
    "GracefulShutdown",
    "TemplateRenderer",
    "detect_app_config",
]
