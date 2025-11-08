"""
Security validation for MCP servers.

This module provides tools to validate MCP server manifests and assess
security risks. It is designed to catch obvious security issues but should
NOT be considered a complete security solution.

⚠️ SECURITY WARNINGS:
- This validator catches obvious issues but cannot detect sophisticated attacks
- Passing validation does NOT guarantee a server is secure
- Still requires: code review, penetration testing, runtime monitoring
- Cannot detect: authentication flaws, business logic bugs, runtime exploits

Use this as ONE LAYER in a defense-in-depth security strategy.
"""

from nextmcp.security.validation import (
    ManifestValidator,
    RiskAssessment,
    RiskLevel,
    SecurityIssue,
    ValidationResult,
)

__all__ = [
    "ManifestValidator",
    "ValidationResult",
    "SecurityIssue",
    "RiskLevel",
    "RiskAssessment",
]
