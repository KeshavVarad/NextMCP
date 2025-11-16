"""
Authentication middleware for NextMCP.

This module provides middleware decorators for protecting tools with
authentication and authorization requirements.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

from nextmcp.auth.core import AuthContext, AuthProvider
from nextmcp.auth.rbac import PermissionDeniedError

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


def requires_auth(
    provider: AuthProvider | None = None,
    credentials_key: str = "auth",
) -> Callable:
    """
    Middleware decorator that requires authentication.

    The decorated tool will only execute if valid credentials are provided.
    The auth context is injected as the first parameter.

    Args:
        provider: Auth provider to use (if None, must be set later)
        credentials_key: Key in kwargs where credentials are passed

    Example:
        @app.tool()
        @requires_auth(provider=api_key_provider)
        def protected_tool(auth: AuthContext, param: str) -> str:
            return f"Hello {auth.user_id}"
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get credentials from kwargs
            credentials = kwargs.pop(credentials_key, {})

            if not credentials:
                raise AuthenticationError("No credentials provided")

            if provider is None:
                raise AuthenticationError("No auth provider configured")

            # Authenticate
            # Note: We need to handle sync/async provider authentication
            # For now, we'll require providers to have sync authenticate method
            import asyncio

            if asyncio.iscoroutinefunction(provider.authenticate):
                # If provider is async, we need to run it
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in async context, this won't work
                    # We'll need the async version of this middleware
                    raise RuntimeError(
                        "Async auth provider requires requires_auth_async middleware"
                    )
                result = loop.run_until_complete(provider.authenticate(credentials))
            else:
                # Sync provider - but authenticate is async, so we need to await it
                raise RuntimeError("Auth providers must be async - use requires_auth_async")

            if not result.success:
                raise AuthenticationError(result.error or "Authentication failed")

            # Inject auth context as first argument
            return fn(result.context, *args, **kwargs)

        # Mark function as requiring auth
        wrapper._requires_auth = True  # type: ignore
        wrapper._auth_provider = provider  # type: ignore

        return wrapper

    return decorator


def requires_auth_async(
    provider: AuthProvider | None = None,
    credentials_key: str = "auth",
) -> Callable:
    """
    Async middleware decorator that requires authentication.

    The decorated async tool will only execute if valid credentials are provided.
    The auth context is injected as the first parameter.

    Args:
        provider: Auth provider to use (if None, must be set later)
        credentials_key: Key in kwargs where credentials are passed

    Example:
        @app.tool()
        @requires_auth_async(provider=jwt_provider)
        async def protected_tool(auth: AuthContext, param: str) -> str:
            return f"Hello {auth.user_id}"
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get credentials from kwargs
            credentials = kwargs.pop(credentials_key, {})

            if not credentials:
                raise AuthenticationError("No credentials provided")

            if provider is None:
                raise AuthenticationError("No auth provider configured")

            # Authenticate (provider.authenticate is async)
            result = await provider.authenticate(credentials)

            if not result.success:
                raise AuthenticationError(result.error or "Authentication failed")

            # Inject auth context as first argument
            if asyncio.iscoroutinefunction(fn):
                return await fn(result.context, *args, **kwargs)
            else:
                return fn(result.context, *args, **kwargs)

        # Mark function as requiring auth
        wrapper._requires_auth = True  # type: ignore
        wrapper._auth_provider = provider  # type: ignore

        return wrapper

    return decorator


def requires_role(*required_roles: str) -> Callable:
    """
    Middleware decorator that requires specific roles.

    Must be used with @requires_auth or @requires_auth_async.
    The auth context from the auth middleware is checked for required roles.

    Args:
        *required_roles: Role names required (user must have at least one)

    Example:
        @app.tool()
        @requires_auth_async(provider=api_key_provider)
        @requires_role("admin", "moderator")
        async def admin_tool(auth: AuthContext) -> str:
            return "Admin action performed"
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext (from requires_auth)
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_role must be used with requires_auth or requires_auth_async"
                )

            auth_context = args[0]

            # Check if user has any of the required roles
            has_role = any(auth_context.has_role(role) for role in required_roles)

            if not has_role:
                roles_str = ", ".join(required_roles)
                raise PermissionDeniedError(
                    f"One of the following roles required: {roles_str}",
                    required=roles_str,
                    user_id=auth_context.user_id,
                )

            return fn(*args, **kwargs)

        # Mark function as requiring roles
        wrapper._requires_roles = required_roles  # type: ignore

        return wrapper

    return decorator


def requires_role_async(*required_roles: str) -> Callable:
    """
    Async middleware decorator that requires specific roles.

    Must be used with @requires_auth_async.
    The auth context from the auth middleware is checked for required roles.

    Args:
        *required_roles: Role names required (user must have at least one)

    Example:
        @app.tool()
        @requires_auth_async(provider=api_key_provider)
        @requires_role_async("admin")
        async def admin_tool(auth: AuthContext) -> str:
            return "Admin action performed"
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext (from requires_auth_async)
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_role_async must be used with requires_auth_async"
                )

            auth_context = args[0]

            # Check if user has any of the required roles
            has_role = any(auth_context.has_role(role) for role in required_roles)

            if not has_role:
                roles_str = ", ".join(required_roles)
                raise PermissionDeniedError(
                    f"One of the following roles required: {roles_str}",
                    required=roles_str,
                    user_id=auth_context.user_id,
                )

            import asyncio

            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            else:
                return fn(*args, **kwargs)

        # Mark function as requiring roles
        wrapper._requires_roles = required_roles  # type: ignore

        return wrapper

    return decorator


def requires_permission(*required_permissions: str) -> Callable:
    """
    Middleware decorator that requires specific permissions.

    Must be used with @requires_auth or @requires_auth_async.
    The auth context is checked for required permissions.

    Args:
        *required_permissions: Permission names required (user must have at least one)

    Example:
        @app.tool()
        @requires_auth_async(provider=api_key_provider)
        @requires_permission("write:posts", "admin:posts")
        async def create_post(auth: AuthContext, title: str) -> dict:
            return {"title": title, "author": auth.user_id}
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_permission must be used with requires_auth or requires_auth_async"
                )

            auth_context = args[0]

            # Check if user has any of the required permissions
            has_permission = any(auth_context.has_permission(perm) for perm in required_permissions)

            if not has_permission:
                perms_str = ", ".join(required_permissions)
                raise PermissionDeniedError(
                    f"One of the following permissions required: {perms_str}",
                    required=perms_str,
                    user_id=auth_context.user_id,
                )

            return fn(*args, **kwargs)

        # Mark function as requiring permissions
        wrapper._requires_permissions = required_permissions  # type: ignore

        return wrapper

    return decorator


def requires_permission_async(*required_permissions: str) -> Callable:
    """
    Async middleware decorator that requires specific permissions.

    Must be used with @requires_auth_async.
    The auth context is checked for required permissions.

    Args:
        *required_permissions: Permission names required (user must have at least one)

    Example:
        @app.tool()
        @requires_auth_async(provider=api_key_provider)
        @requires_permission_async("delete:posts")
        async def delete_post(auth: AuthContext, post_id: int) -> dict:
            return {"deleted": post_id}
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_permission_async must be used with requires_auth_async"
                )

            auth_context = args[0]

            # Check if user has any of the required permissions
            has_permission = any(auth_context.has_permission(perm) for perm in required_permissions)

            if not has_permission:
                perms_str = ", ".join(required_permissions)
                raise PermissionDeniedError(
                    f"One of the following permissions required: {perms_str}",
                    required=perms_str,
                    user_id=auth_context.user_id,
                )

            import asyncio

            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            else:
                return fn(*args, **kwargs)

        # Mark function as requiring permissions
        wrapper._requires_permissions = required_permissions  # type: ignore

        return wrapper

    return decorator


def requires_scope_async(*required_scopes: str) -> Callable:
    """
    Async middleware decorator that requires specific OAuth scopes.

    Must be used with @requires_auth_async.
    The auth context from the auth middleware is checked for required scopes.

    Args:
        *required_scopes: Scope names required (user must have at least one)

    Example:
        @app.tool()
        @requires_auth_async(provider=github_oauth)
        @requires_scope_async("repo:read", "repo:write")
        async def access_repo(auth: AuthContext) -> dict:
            return {"status": "authorized"}
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext (from requires_auth_async)
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_scope_async must be used with requires_auth_async"
                )

            auth_context = args[0]

            # Check if user has any of the required scopes
            has_scope = any(auth_context.has_scope(scope) for scope in required_scopes)

            if not has_scope:
                scopes_str = ", ".join(required_scopes)
                raise PermissionDeniedError(
                    f"One of the following scopes required: {scopes_str}",
                    required=scopes_str,
                    user_id=auth_context.user_id,
                )

            import asyncio

            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            else:
                return fn(*args, **kwargs)

        # Mark function as requiring scopes
        wrapper._requires_scopes = required_scopes  # type: ignore

        return wrapper

    return decorator


def requires_manifest_async(
    manifest: "PermissionManifest | None" = None,
    tool_name: str | None = None,
) -> Callable:
    """
    Async middleware decorator that enforces PermissionManifest access control.

    Must be used with @requires_auth_async.
    The auth context is checked against the manifest's tool requirements.

    Args:
        manifest: PermissionManifest to enforce
        tool_name: Name of tool to check (if None, uses function name)

    Example:
        manifest = PermissionManifest()
        manifest.define_tool_permission("admin_tool", roles=["admin"])

        @app.tool()
        @requires_auth_async(provider=api_key_provider)
        @requires_manifest_async(manifest=manifest, tool_name="admin_tool")
        async def admin_tool(auth: AuthContext) -> str:
            return "Admin action performed"
    """
    from nextmcp.auth.errors import ManifestViolationError
    from nextmcp.auth.manifest import PermissionManifest

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # First argument should be AuthContext (from requires_auth_async)
            if not args or not isinstance(args[0], AuthContext):
                raise AuthenticationError(
                    "requires_manifest_async must be used with requires_auth_async"
                )

            auth_context = args[0]

            if manifest is None:
                raise AuthenticationError("No manifest configured for requires_manifest_async")

            # Determine tool name (use parameter or function name)
            actual_tool_name = tool_name if tool_name else fn.__name__

            # Check manifest access
            allowed, error_message = manifest.check_tool_access(actual_tool_name, auth_context)

            if not allowed:
                # Get tool definition for error details
                tool_def = manifest.tools.get(actual_tool_name)

                raise ManifestViolationError(
                    message=error_message or "Access denied by manifest",
                    tool_name=actual_tool_name,
                    required_roles=tool_def.roles if tool_def else [],
                    required_permissions=tool_def.permissions if tool_def else [],
                    required_scopes=tool_def.scopes if tool_def else [],
                    user_id=auth_context.user_id,
                    auth_context=auth_context,
                )

            # Access allowed - execute function
            import asyncio

            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            else:
                return fn(*args, **kwargs)

        # Mark function as requiring manifest
        wrapper._requires_manifest = True  # type: ignore
        wrapper._manifest = manifest  # type: ignore
        wrapper._tool_name = tool_name  # type: ignore

        return wrapper

    return decorator


# Need to add this import
import asyncio  # noqa: E402
