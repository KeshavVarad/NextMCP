"""
NextMCP Protocol Extensions.

This module defines protocol-level extensions for MCP servers.
"""

from nextmcp.protocol.auth_metadata import (
    AuthFlowType,
    AuthMetadata,
    AuthProviderMetadata,
    AuthRequirement,
)

__all__ = [
    "AuthMetadata",
    "AuthProviderMetadata",
    "AuthRequirement",
    "AuthFlowType",
]
