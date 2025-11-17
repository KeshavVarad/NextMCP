"""
Permission Manifest MCP Server Example.

This example demonstrates how to use PermissionManifest for declarative security.
Define security policies in YAML and enforce them automatically via decorators.

Features demonstrated:
- Loading manifests from YAML files
- Declarative security definitions
- Automatic manifest enforcement with @requires_manifest_async
- Role, permission, and scope requirements
- Dangerous operation flagging

Setup:
1. Create a manifest YAML file (see manifest.yaml below)
2. Initialize manifest and load YAML
3. Apply @requires_manifest_async to protected tools

Usage:
   python examples/auth/manifest_server.py
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from nextmcp import NextMCP
from nextmcp.auth import (
    APIKeyProvider,
    AuthContext,
    Permission,
    PermissionManifest,
    Role,
    requires_auth_async,
    requires_manifest_async,
)

# Initialize MCP server
mcp = NextMCP("Permission Manifest Example")

# Create permission manifest
manifest = PermissionManifest()

# Option 1: Define manifest programmatically
print("Defining manifest programmatically...")

manifest.define_scope(
    name="read:data",
    description="Read access to data",
    oauth_mapping={
        "github": ["repo:read"],
        "google": ["drive.readonly"],
    },
)

manifest.define_scope(
    name="write:data",
    description="Write access to data",
    oauth_mapping={
        "github": ["repo:write"],
        "google": ["drive.file"],
    },
)

manifest.define_tool_permission(
    tool_name="query_database",
    roles=["viewer", "editor", "admin"],
    permissions=["read:data"],
    description="Query database for information",
    dangerous=False,
)

manifest.define_tool_permission(
    tool_name="update_database",
    roles=["editor", "admin"],
    permissions=["write:data"],
    description="Update database records",
    dangerous=False,
)

manifest.define_tool_permission(
    tool_name="delete_all_data",
    roles=["admin"],
    permissions=["admin:all"],
    scopes=["admin:full"],
    description="Delete all data (DANGEROUS)",
    dangerous=True,
)

manifest.define_tool_permission(
    tool_name="export_user_data",
    roles=["admin", "data_analyst"],
    permissions=["export:data", "read:data"],
    description="Export user data for analysis",
    dangerous=False,
)

# Option 2: Load from YAML (demonstrate round-trip)
print("Exporting manifest to YAML...\n")

yaml_content = """
scopes:
  - name: "read:data"
    description: "Read access to data"
    oauth_mapping:
      github:
        - "repo:read"
      google:
        - "drive.readonly"

  - name: "write:data"
    description: "Write access to data"
    oauth_mapping:
      github:
        - "repo:write"
      google:
        - "drive.file"

tools:
  query_database:
    roles:
      - "viewer"
      - "editor"
      - "admin"
    permissions:
      - "read:data"
    description: "Query database for information"
    dangerous: false

  update_database:
    roles:
      - "editor"
      - "admin"
    permissions:
      - "write:data"
    description: "Update database records"
    dangerous: false

  delete_all_data:
    roles:
      - "admin"
    permissions:
      - "admin:all"
    scopes:
      - "admin:full"
    description: "Delete all data (DANGEROUS)"
    dangerous: true

  export_user_data:
    roles:
      - "admin"
      - "data_analyst"
    permissions:
      - "export:data"
      - "read:data"
    description: "Export user data for analysis"
    dangerous: false
"""

print("Example manifest.yaml:")
print("=" * 60)
print(yaml_content)
print("=" * 60)
print()

# Create auth provider with different user roles
print("Creating auth provider with test users...\n")

auth_provider = APIKeyProvider(
    valid_keys={
        "viewer_key": {
            "user_id": "viewer_user",
            "username": "Viewer User",
            "roles": ["viewer"],
            "permissions": ["read:data"],
        },
        "editor_key": {
            "user_id": "editor_user",
            "username": "Editor User",
            "roles": ["editor"],
            "permissions": ["read:data", "write:data"],
        },
        "admin_key": {
            "user_id": "admin_user",
            "username": "Admin User",
            "roles": ["admin"],
            "permissions": ["admin:all", "read:data", "write:data"],
            "scopes": ["admin:full"],
        },
        "analyst_key": {
            "user_id": "analyst_user",
            "username": "Data Analyst",
            "roles": ["data_analyst"],
            "permissions": ["read:data", "export:data"],
        },
    }
)


# Define tools with manifest enforcement

@mcp.tool()
@requires_auth_async(provider=auth_provider)
@requires_manifest_async(manifest=manifest)
async def query_database(auth: AuthContext, query: str) -> dict[str, Any]:
    """
    Query the database.

    Requires: viewer, editor, or admin role + read:data permission
    (as defined in manifest)

    Args:
        auth: Authentication context (injected)
        query: SQL-like query string

    Returns:
        Query results

    Example:
        # As viewer
        result = await query_database(
            auth={"api_key": "viewer_key"},
            query="SELECT * FROM users LIMIT 10"
        )
    """
    return {
        "success": True,
        "user": auth.username,
        "query": query,
        "results": [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "editor"},
            {"id": 3, "name": "Charlie", "role": "viewer"},
        ],
    }


@mcp.tool()
@requires_auth_async(provider=auth_provider)
@requires_manifest_async(manifest=manifest)
async def update_database(
    auth: AuthContext,
    record_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a database record.

    Requires: editor or admin role + write:data permission
    (as defined in manifest)

    Args:
        auth: Authentication context (injected)
        record_id: ID of record to update
        data: New data for record

    Returns:
        Update result

    Example:
        # As editor
        result = await update_database(
            auth={"api_key": "editor_key"},
            record_id=2,
            data={"name": "Bob Updated"}
        )
    """
    return {
        "success": True,
        "user": auth.username,
        "updated_record": record_id,
        "data": data,
        "message": "Record updated successfully",
    }


@mcp.tool()
@requires_auth_async(provider=auth_provider)
@requires_manifest_async(manifest=manifest)
async def delete_all_data(auth: AuthContext, confirmation: str) -> dict[str, Any]:
    """
    Delete ALL data (DANGEROUS operation).

    Requires: admin role + admin:all permission + admin:full scope
    (as defined in manifest - marked as dangerous)

    Args:
        auth: Authentication context (injected)
        confirmation: Must be "I UNDERSTAND THIS IS PERMANENT"

    Returns:
        Deletion result

    Example:
        # As admin
        result = await delete_all_data(
            auth={"api_key": "admin_key"},
            confirmation="I UNDERSTAND THIS IS PERMANENT"
        )
    """
    if confirmation != "I UNDERSTAND THIS IS PERMANENT":
        return {
            "success": False,
            "error": "Invalid confirmation. This is a dangerous operation.",
        }

    return {
        "success": True,
        "user": auth.username,
        "message": "All data deleted (simulated - would require additional confirmation in production)",
        "warning": "This operation is marked as DANGEROUS in the manifest",
    }


@mcp.tool()
@requires_auth_async(provider=auth_provider)
@requires_manifest_async(manifest=manifest)
async def export_user_data(
    auth: AuthContext,
    format: str = "json",
) -> dict[str, Any]:
    """
    Export user data for analysis.

    Requires: admin OR data_analyst role + (export:data OR read:data) permission
    (as defined in manifest - uses OR logic for multiple requirements)

    Args:
        auth: Authentication context (injected)
        format: Export format (json, csv, xlsx)

    Returns:
        Exported data

    Example:
        # As data analyst
        result = await export_user_data(
            auth={"api_key": "analyst_key"},
            format="csv"
        )
    """
    return {
        "success": True,
        "user": auth.username,
        "format": format,
        "data_url": f"/exports/users_{auth.user_id}.{format}",
        "record_count": 1000,
        "message": "Data export prepared successfully",
    }


# Demonstration function
async def demonstrate_manifest():
    """Demonstrate manifest enforcement with different user roles."""
    print("\n" + "=" * 60)
    print("MANIFEST ENFORCEMENT DEMONSTRATION")
    print("=" * 60 + "\n")

    # Test 1: Viewer can query
    print("Test 1: Viewer querying database (should succeed)")
    try:
        result = await query_database(
            auth={"api_key": "viewer_key"},
            query="SELECT * FROM users",
        )
        print(f"✓ Success: {result['user']} queried database\n")
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    # Test 2: Viewer cannot update
    print("Test 2: Viewer updating database (should fail)")
    try:
        result = await update_database(
            auth={"api_key": "viewer_key"},
            record_id=1,
            data={"name": "Updated"},
        )
        print(f"✓ Unexpected success\n")
    except Exception as e:
        print(f"✓ Correctly denied: {e}\n")

    # Test 3: Editor can update
    print("Test 3: Editor updating database (should succeed)")
    try:
        result = await update_database(
            auth={"api_key": "editor_key"},
            record_id=1,
            data={"name": "Updated"},
        )
        print(f"✓ Success: {result['user']} updated record\n")
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    # Test 4: Editor cannot delete
    print("Test 4: Editor deleting all data (should fail)")
    try:
        result = await delete_all_data(
            auth={"api_key": "editor_key"},
            confirmation="I UNDERSTAND THIS IS PERMANENT",
        )
        print(f"✓ Unexpected success\n")
    except Exception as e:
        print(f"✓ Correctly denied: {e}\n")

    # Test 5: Admin can delete
    print("Test 5: Admin deleting all data (should succeed)")
    try:
        result = await delete_all_data(
            auth={"api_key": "admin_key"},
            confirmation="I UNDERSTAND THIS IS PERMANENT",
        )
        print(f"✓ Success: {result['user']} performed dangerous operation\n")
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    # Test 6: Data analyst can export
    print("Test 6: Data analyst exporting data (should succeed)")
    try:
        result = await export_user_data(
            auth={"api_key": "analyst_key"},
            format="csv",
        )
        print(f"✓ Success: {result['user']} exported data\n")
    except Exception as e:
        print(f"✗ Failed: {e}\n")

    print("=" * 60)
    print("MANIFEST SUMMARY")
    print("=" * 60)
    print(f"Total scopes defined: {len(manifest.scopes)}")
    print(f"Total tools protected: {len(manifest.tools)}")
    print(f"Dangerous tools: {sum(1 for t in manifest.tools.values() if t.dangerous)}")
    print("\nProtected tools:")
    for tool_name, tool_perm in manifest.tools.items():
        danger_flag = " [DANGEROUS]" if tool_perm.dangerous else ""
        print(f"  - {tool_name}{danger_flag}")
        if tool_perm.roles:
            print(f"      Roles: {', '.join(tool_perm.roles)}")
        if tool_perm.permissions:
            print(f"      Permissions: {', '.join(tool_perm.permissions)}")
        if tool_perm.scopes:
            print(f"      Scopes: {', '.join(tool_perm.scopes)}")
    print()


if __name__ == "__main__":
    print("Starting Permission Manifest MCP Server...\n")

    # Run demonstration
    asyncio.run(demonstrate_manifest())

    print("\n" + "=" * 60)
    print("KEY CONCEPTS")
    print("=" * 60)
    print("1. Declarative Security: Define requirements in YAML/code")
    print("2. Automatic Enforcement: @requires_manifest_async decorator")
    print("3. Flexible Requirements: Roles, permissions, and scopes")
    print("4. OR Logic: User needs ANY ONE from each type")
    print("5. AND Logic: User needs ALL types that are specified")
    print("6. Dangerous Flags: Mark operations requiring extra care")
    print("=" * 60)
