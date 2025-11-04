# NextMCP

[![Tests](https://github.com/KeshavVarad/NextMCP/workflows/Tests/badge.svg)](https://github.com/KeshavVarad/NextMCP/actions)
[![PyPI version](https://badge.fury.io/py/nextmcp.svg)](https://badge.fury.io/py/nextmcp)
[![Python versions](https://img.shields.io/pypi/pyversions/nextmcp.svg)](https://pypi.org/project/nextmcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Production-grade MCP server toolkit with minimal boilerplate**

NextMCP is a Python SDK built on top of FastMCP that provides a developer-friendly experience for building MCP (Model Context Protocol) servers. Inspired by Next.js, it offers minimal setup, powerful middleware, and a rich CLI for rapid development.

## Features

- **Full MCP Specification** - Complete support for Tools, Prompts, and Resources primitives
- **Convention-Based Structure** - Next.js-inspired file-based organization with auto-discovery
- **Zero-Config Setup** - Single-line `NextMCP.from_config()` for instant project setup
- **Auto-Discovery** - Automatically discover and register primitives from directory structure
- **Minimal Boilerplate** - Get started with just a few lines of code
- **Decorator-based API** - Register tools, prompts, and resources with simple decorators
- **Async Support** - Full support for async/await across all primitives
- **Argument Completion** - Smart suggestions for prompt arguments and resource templates
- **Resource Subscriptions** - Real-time notifications when resources change
- **WebSocket Transport** - Real-time bidirectional communication for interactive applications
- **Global & Primitive-specific Middleware** - Add logging, auth, rate limiting, caching, and more
- **Rich CLI** - Scaffold projects, run servers, and generate docs with `mcp` commands
- **Configuration Management** - Support for `.env`, YAML config files, and environment variables
- **Schema Validation** - Optional Pydantic integration for type-safe inputs
- **Production Ready** - Built-in error handling, logging, and comprehensive testing

## Installation

### Basic Installation

```bash
pip install nextmcp
```

### With Optional Dependencies

```bash
# CLI tools (recommended)
pip install nextmcp[cli]

# Configuration support
pip install nextmcp[config]

# Schema validation with Pydantic
pip install nextmcp[schema]

# WebSocket transport
pip install nextmcp[websocket]

# Everything
pip install nextmcp[all]

# Development dependencies
pip install nextmcp[dev]
```

## Quick Start

NextMCP offers two approaches: **Convention-Based** (recommended) for scalable projects, and **Manual** for simple use cases.

### Convention-Based Approach (Recommended)

Perfect for projects with multiple tools, prompts, and resources. Uses file-based organization for automatic discovery.

#### 1. Create project structure

```bash
my-blog-server/
├── nextmcp.config.yaml
├── server.py
├── tools/
│   ├── __init__.py
│   └── posts.py
├── prompts/
│   ├── __init__.py
│   └── workflows.py
└── resources/
    ├── __init__.py
    └── blog_resources.py
```

#### 2. Configure your project

```yaml
# nextmcp.config.yaml
name: blog-server
version: 1.0.0
description: A blog management MCP server

auto_discover: true

discovery:
  tools: tools/
  prompts: prompts/
  resources: resources/
```

#### 3. Write tools in organized files

```python
# tools/posts.py
from nextmcp import NextMCP

app = NextMCP.from_config()

@app.tool()
def create_post(title: str, content: str) -> dict:
    """Create a new blog post"""
    return {"id": 1, "title": title, "content": content}

@app.tool()
def list_posts() -> list:
    """List all blog posts"""
    return [{"id": 1, "title": "First Post"}]
```

#### 4. Single-line server setup

```python
# server.py
from nextmcp import NextMCP

# Auto-discovers all tools, prompts, and resources
app = NextMCP.from_config()

if __name__ == "__main__":
    app.run()
```

#### 5. Run your server

```bash
python server.py
```

That's it! All tools, prompts, and resources are automatically discovered and registered.

### Manual Approach

For simple projects with just a few tools.

#### 1. Create a new project

```bash
mcp init my-bot
cd my-bot
```

#### 2. Write your first tool

```python
# app.py
from nextmcp import NextMCP

app = NextMCP("my-bot")

@app.tool()
def greet(name: str) -> str:
    """Greet someone by name"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    app.run()
```

#### 3. Run your server

```bash
mcp run app.py
```

Your MCP server is now running with the `greet` tool available.

## Convention-Based Project Structure

NextMCP v0.3.0 introduces a powerful convention-based architecture inspired by Next.js's file-based routing. This approach enables automatic discovery and registration of tools, prompts, and resources from your directory structure, eliminating boilerplate and improving project organization.

### Why Convention-Based?

**Before (Manual Registration):**
```python
# app.py - 200+ lines of boilerplate
from nextmcp import NextMCP

app = NextMCP("my-server")

@app.tool()
def create_post(...):
    ...

@app.tool()
def update_post(...):
    ...

@app.tool()
def delete_post(...):
    ...

@app.prompt()
def writing_workflow(...):
    ...

@app.resource("blog://posts/recent")
def recent_posts():
    ...

# ... 20+ more primitives mixed together
```

**After (Convention-Based):**
```python
# server.py - Just 3 lines!
from nextmcp import NextMCP

app = NextMCP.from_config()

if __name__ == "__main__":
    app.run()
```

### Project Structure

Organize your primitives in standard directories:

```
my-mcp-server/
├── nextmcp.config.yaml      # Project configuration
├── server.py                # Entry point
├── tools/                   # Tool definitions
│   ├── __init__.py
│   ├── posts.py            # Post management tools
│   └── comments.py         # Comment management tools
├── prompts/                 # Prompt templates
│   ├── __init__.py
│   └── workflows.py        # Workflow prompts
└── resources/               # Resource providers
    ├── __init__.py
    └── blog_resources.py   # Blog data resources
```

### How It Works

#### 1. Auto-Discovery Engine

NextMCP scans your directory structure and automatically discovers decorated functions:

```python
# tools/posts.py
from nextmcp import NextMCP

app = NextMCP.from_config()

@app.tool()
def create_post(title: str, content: str) -> dict:
    """Create a new blog post"""
    return {"id": 1, "title": title}

@app.tool()
def list_posts(limit: int = 10) -> list:
    """List recent blog posts"""
    return []
```

The discovery engine:
- Recursively scans `tools/`, `prompts/`, and `resources/` directories
- Imports Python modules and inspects decorated functions
- Automatically registers all discovered primitives
- Skips `__init__.py` and `test_*.py` files

#### 2. Configuration File

Control discovery behavior with `nextmcp.config.yaml`:

```yaml
name: my-mcp-server
version: 1.0.0
description: My awesome MCP server

# Enable/disable auto-discovery
auto_discover: true

# Customize directory paths
discovery:
  tools: tools/
  prompts: prompts/
  resources: resources/

# Server configuration
server:
  host: 0.0.0.0
  port: 8000
  transport: stdio

# Middleware pipeline
middleware:
  - nextmcp.middleware.log_calls
  - nextmcp.middleware.error_handler
```

#### 3. Loading from Config

Use the `from_config()` class method for automatic setup:

```python
from nextmcp import NextMCP

# Load configuration and auto-discover primitives
app = NextMCP.from_config()

# Optional: specify custom config file or base path
app = NextMCP.from_config(
    config_file="custom.yaml",
    base_path="/path/to/project"
)
```

### Discovery Rules

The auto-discovery engine follows these rules:

1. **Directory Scanning**: Recursively searches configured directories
2. **Module Importing**: Dynamically imports all `.py` files
3. **Decorator Detection**: Finds functions with MCP decorator markers
4. **Automatic Registration**: Registers discovered primitives with the app
5. **File Exclusions**: Skips `__init__.py` and `test_*.py` files

### Organizing Large Projects

For large projects, use subdirectories and modules:

```
tools/
├── __init__.py
├── posts/
│   ├── __init__.py
│   ├── create.py
│   ├── update.py
│   └── delete.py
├── comments/
│   ├── __init__.py
│   └── moderate.py
└── users/
    ├── __init__.py
    └── manage.py
```

All tools in subdirectories are automatically discovered.

### Validation

Validate your project structure:

```python
from nextmcp import validate_project_structure

# Check if project follows conventions
results = validate_project_structure()

if results["valid"]:
    print(f"✓ Found {results['stats']['tools']} tool files")
    print(f"✓ Found {results['stats']['prompts']} prompt files")
    print(f"✓ Found {results['stats']['resources']} resource files")
else:
    print("Errors:", results["errors"])
    print("Warnings:", results["warnings"])
```

### Benefits

1. **Separation of Concerns** - Tools, prompts, and resources in dedicated directories
2. **Scalability** - Add new primitives by creating files, no registration needed
3. **Team Collaboration** - Clear structure for multiple developers
4. **Zero Boilerplate** - No manual registration code
5. **Type Safety** - Full IDE support with organized modules
6. **Testing** - Easy to test individual modules in isolation

### Migrating from Manual Registration

Existing manual projects work unchanged. To migrate gradually:

```python
# You can mix both approaches!
from nextmcp import NextMCP

# Start with auto-discovery
app = NextMCP.from_config()

# Add manual tools as needed
@app.tool()
def legacy_tool():
    """This still works!"""
    return "result"
```

See `examples/blog_server/` for a complete convention-based project.

## Authentication & Authorization

NextMCP v0.4.0 introduces a comprehensive authentication and authorization system inspired by next-auth, adapted for the Model Context Protocol.

### Why Authentication for MCP?

MCP servers often need to:
- **Protect sensitive tools** from unauthorized access
- **Implement role-based access** (admin, user, viewer)
- **Track who performed actions** for audit logs
- **Integrate with existing auth systems** (API keys, JWT, OAuth)

### Quick Start

#### API Key Authentication

The simplest way to protect your tools:

```python
from nextmcp import NextMCP
from nextmcp.auth import APIKeyProvider, AuthContext, requires_auth_async

app = NextMCP("secure-server")

# Configure API key provider
api_key_provider = APIKeyProvider(
    valid_keys={
        "admin-key-123": {
            "user_id": "admin1",
            "username": "admin",
            "roles": ["admin"],
            "permissions": ["read:*", "write:*"],
        },
        "user-key-456": {
            "user_id": "user1",
            "username": "alice",
            "roles": ["user"],
            "permissions": ["read:posts"],
        }
    }
)

# Protected tool - requires authentication
@app.tool()
@requires_auth_async(provider=api_key_provider)
async def protected_tool(auth: AuthContext, data: str) -> dict:
    """Only authenticated users can access this."""
    return {
        "message": f"Hello {auth.username}",
        "data": data,
        "user_id": auth.user_id
    }
```

#### JWT Token Authentication

For stateless token-based auth:

```python
from nextmcp.auth import JWTProvider

# Configure JWT provider
jwt_provider = JWTProvider(
    secret_key="your-secret-key",
    algorithm="HS256",
    verify_exp=True
)

# Login endpoint that generates tokens
@app.tool()
async def login(username: str, password: str) -> dict:
    """Login and receive a JWT token."""
    # Validate credentials (check database, etc.)

    # Generate token
    token = jwt_provider.create_token(
        user_id=f"user_{username}",
        roles=["user"],
        permissions=["read:posts", "write:posts"],
        username=username,
        expires_in=3600  # 1 hour
    )

    return {"token": token, "expires_in": 3600}

# Use the token for authentication
@app.tool()
@requires_auth_async(provider=jwt_provider)
async def secure_action(auth: AuthContext) -> dict:
    """Requires valid JWT token."""
    return {"user": auth.username, "action": "performed"}
```

### Built-in Auth Providers

NextMCP includes three production-ready authentication providers:

| Provider | Use Case | Features |
|----------|----------|----------|
| **APIKeyProvider** | Simple API key auth | Pre-configured keys, custom validators, secure generation |
| **JWTProvider** | Token-based auth | Automatic expiration, signature verification, stateless |
| **SessionProvider** | Session-based auth | In-memory sessions, automatic cleanup, session management |

### Role-Based Access Control (RBAC)

Control access based on user roles:

```python
from nextmcp.auth import requires_role_async

# Only admins can access this tool
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("admin")
async def admin_tool(auth: AuthContext) -> dict:
    """Admin-only functionality."""
    return {"action": "admin action performed"}

# Users or admins can access
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_role_async("user", "admin")  # Either role works
async def user_tool(auth: AuthContext) -> dict:
    """User or admin can access."""
    return {"action": "user action"}
```

### Permission-Based Access Control

Fine-grained control with specific permissions:

```python
from nextmcp.auth import RBAC, requires_permission_async

# Set up RBAC system
rbac = RBAC()

# Define permissions
rbac.define_permission("read:posts", "Read blog posts")
rbac.define_permission("write:posts", "Create and edit posts")
rbac.define_permission("delete:posts", "Delete posts")

# Define roles with permissions
rbac.define_role("viewer", "Read-only access")
rbac.assign_permission_to_role("viewer", "read:posts")

rbac.define_role("editor", "Full content management")
rbac.assign_permission_to_role("editor", "read:posts")
rbac.assign_permission_to_role("editor", "write:posts")
rbac.assign_permission_to_role("editor", "delete:posts")

# Require specific permission
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("write:posts")
async def create_post(auth: AuthContext, title: str) -> dict:
    """Requires write:posts permission."""
    return {"status": "created", "title": title}

# Multiple permissions (user needs at least one)
@app.tool()
@requires_auth_async(provider=api_key_provider)
@requires_permission_async("admin:posts", "delete:posts")
async def delete_post(auth: AuthContext, post_id: int) -> dict:
    """Requires admin:posts OR delete:posts permission."""
    return {"status": "deleted", "post_id": post_id}
```

### Permission Wildcards

Support for wildcard permissions:

```python
# Admin with wildcard - matches ALL permissions
rbac.define_role("admin", "Full access")
rbac.assign_permission_to_role("admin", "*")

# Namespace wildcard - matches all admin permissions
rbac.assign_permission_to_role("moderator", "admin:*")

# moderator has: admin:users, admin:posts, admin:settings, etc.
```

### AuthContext

The `AuthContext` object is injected as the first parameter to protected tools:

```python
@app.tool()
@requires_auth_async(provider=api_key_provider)
async def my_tool(auth: AuthContext, param: str) -> dict:
    # Access user information
    user_id = auth.user_id           # Unique user ID
    username = auth.username         # Human-readable name

    # Check roles and permissions
    is_admin = auth.has_role("admin")
    can_write = auth.has_permission("write:posts")

    # Access metadata
    department = auth.metadata.get("department")

    return {
        "user": username,
        "is_admin": is_admin,
        "can_write": can_write
    }
```

### Middleware Stacking

Stack authentication and authorization decorators:

```python
@app.tool()                                           # 4. Register as tool
@requires_auth_async(provider=api_key_provider)      # 3. Authenticate user
@requires_role_async("admin")                        # 2. Check role
@requires_permission_async("delete:users")           # 1. Check permission (executes first)
async def delete_user(auth: AuthContext, user_id: int) -> dict:
    """Requires authentication, admin role, AND delete:users permission."""
    return {"status": "deleted", "user_id": user_id}
```

### Session Management

Using the SessionProvider for session-based authentication:

```python
from nextmcp.auth import SessionProvider

session_provider = SessionProvider(session_timeout=3600)  # 1 hour

@app.tool()
async def login(username: str, password: str) -> dict:
    """Create a new session."""
    # Validate credentials...

    # Create session
    session_id = session_provider.create_session(
        user_id=f"user_{username}",
        username=username,
        roles=["user"],
        permissions=["read:posts"]
    )

    return {"session_id": session_id, "expires_in": 3600}

@app.tool()
async def logout(session_id: str) -> dict:
    """Destroy a session."""
    success = session_provider.destroy_session(session_id)
    return {"logged_out": success}

# Use session for authentication
@app.tool()
@requires_auth_async(provider=session_provider)
async def protected_tool(auth: AuthContext) -> dict:
    """Requires valid session."""
    return {"user": auth.username}
```

### Loading RBAC from Configuration

Define roles and permissions in configuration:

```python
from nextmcp.auth import RBAC

rbac = RBAC()

config = {
    "permissions": [
        {"name": "read:posts", "description": "Read posts"},
        {"name": "write:posts", "description": "Write posts"},
        {"name": "delete:posts", "description": "Delete posts"},
    ],
    "roles": [
        {
            "name": "viewer",
            "description": "Read-only",
            "permissions": ["read:posts"]
        },
        {
            "name": "editor",
            "description": "Full content management",
            "permissions": ["read:posts", "write:posts", "delete:posts"]
        }
    ]
}

rbac.load_from_config(config)
```

### Custom Auth Providers

Create your own authentication provider:

```python
from nextmcp.auth import AuthProvider, AuthResult, AuthContext

class CustomAuthProvider(AuthProvider):
    """Custom authentication using external service."""

    async def authenticate(self, credentials: dict) -> AuthResult:
        """Validate credentials against external service."""
        token = credentials.get("token")

        # Call your external auth service
        user_data = await external_auth_service.validate(token)

        if not user_data:
            return AuthResult.failure("Invalid token")

        # Build auth context
        context = AuthContext(
            authenticated=True,
            user_id=user_data["id"],
            username=user_data["name"],
        )

        # Add roles from external service
        for role in user_data.get("roles", []):
            context.add_role(role)

        return AuthResult.success_result(context)
```

### Error Handling

Authentication errors are raised as exceptions:

```python
from nextmcp.auth import PermissionDeniedError
from nextmcp.auth.middleware import AuthenticationError

try:
    # Call protected tool without credentials
    result = await protected_tool(data="test")
except AuthenticationError as e:
    print(f"Auth failed: {e}")

try:
    # Call tool without required permission
    result = await admin_tool()
except PermissionDeniedError as e:
    print(f"Permission denied: {e}")
    print(f"Required: {e.required}")
    print(f"User: {e.user_id}")
```

### Security Best Practices

1. **Never commit secrets**: Use environment variables for keys/secrets
2. **Use HTTPS/TLS**: Always encrypt traffic in production
3. **Rotate keys regularly**: Implement key rotation policies
4. **Short token expiration**: Balance security and UX (1-24 hours)
5. **Log auth attempts**: Track successful and failed authentication
6. **Validate all inputs**: Never trust client-provided data
7. **Use strong secrets**: Generate with `secrets.token_urlsafe(32)`
8. **Implement rate limiting**: Prevent brute force attacks

### Examples

Check out complete authentication examples:

- **`examples/auth_api_key/`** - API key authentication with role-based access
- **`examples/auth_jwt/`** - JWT token authentication with login endpoint
- **`examples/auth_rbac/`** - Advanced RBAC with fine-grained permissions

## Core Concepts

### Creating an Application

```python
from nextmcp import NextMCP

app = NextMCP(
    name="my-mcp-server",
    description="A custom MCP server"
)
```

### Registering Tools

```python
@app.tool()
def calculate(x: int, y: int) -> int:
    """Add two numbers"""
    return x + y

# With custom name and description
@app.tool(name="custom_name", description="A custom tool")
def my_function(data: str) -> dict:
    return {"result": data}
```

### Adding Middleware

Middleware wraps your tools to add cross-cutting functionality.

#### Global Middleware (applied to all tools)

```python
from nextmcp import log_calls, error_handler

# Add middleware that applies to all tools
app.add_middleware(log_calls)
app.add_middleware(error_handler)

@app.tool()
def my_tool(x: int) -> int:
    return x * 2  # This will be logged and error-handled automatically
```

#### Tool-specific Middleware

```python
from nextmcp import cache_results, require_auth

@app.tool()
@cache_results(ttl_seconds=300)  # Cache for 5 minutes
def expensive_operation(param: str) -> dict:
    # Expensive computation here
    return {"result": perform_calculation(param)}

@app.tool()
@require_auth(valid_keys={"secret-key-123"})
def protected_tool(auth_key: str, data: str) -> str:
    return f"Protected: {data}"
```

### Built-in Middleware

NextMCP includes several production-ready middleware:

- **`log_calls`** - Log all tool invocations with timing
- **`error_handler`** - Catch exceptions and return structured errors
- **`require_auth(valid_keys)`** - API key authentication
- **`rate_limit(max_calls, time_window)`** - Rate limiting
- **`cache_results(ttl_seconds)`** - Response caching
- **`validate_inputs(**validators)`** - Custom input validation
- **`timeout(seconds)`** - Execution timeout

All middleware also have async variants (e.g., `log_calls_async`, `error_handler_async`, etc.) for use with async tools.

### Async Support

NextMCP has full support for async/await patterns, allowing you to build high-performance tools that can handle concurrent I/O operations.

#### Basic Async Tool

```python
from nextmcp import NextMCP
import asyncio

app = NextMCP("async-app")

@app.tool()
async def fetch_data(url: str) -> dict:
    """Fetch data from an API asynchronously"""
    # Use async libraries like httpx, aiohttp, etc.
    await asyncio.sleep(0.1)  # Simulate API call
    return {"url": url, "data": "fetched"}
```

#### Async Middleware

Use async middleware variants for async tools:

```python
from nextmcp import log_calls_async, error_handler_async, cache_results_async

app.add_middleware(log_calls_async)
app.add_middleware(error_handler_async)

@app.tool()
@cache_results_async(ttl_seconds=300)
async def expensive_async_operation(param: str) -> dict:
    await asyncio.sleep(1)  # Simulate expensive operation
    return {"result": param}
```

#### Concurrent Operations

The real power of async is handling multiple operations concurrently:

```python
@app.tool()
async def fetch_multiple_sources(sources: list) -> dict:
    """Fetch data from multiple sources concurrently"""
    async def fetch_one(source: str):
        # Each fetch happens concurrently, not sequentially
        await asyncio.sleep(0.1)
        return {"source": source, "data": "..."}

    # Gather results concurrently - much faster than sequential!
    results = await asyncio.gather(*[fetch_one(s) for s in sources])
    return {"sources": results}
```

**Performance Comparison:**
- Sequential: 4 sources × 0.1s = 0.4s
- Concurrent (async): ~0.1s (all at once!)

#### Mixed Sync and Async Tools

You can have both sync and async tools in the same application:

```python
@app.tool()
def sync_tool(x: int) -> int:
    """Regular synchronous tool"""
    return x * 2

@app.tool()
async def async_tool(x: int) -> int:
    """Async tool for I/O operations"""
    await asyncio.sleep(0.1)
    return x * 3
```

#### When to Use Async

**Use async for:**
- HTTP API calls (with `httpx`, `aiohttp`)
- Database queries (with `asyncpg`, `motor`)
- File I/O operations
- Multiple concurrent operations
- WebSocket connections

**Stick with sync for:**
- CPU-bound operations (heavy computations)
- Simple operations with no I/O
- When third-party libraries don't support async

See `examples/async_weather_bot/` for a complete async example.

### Schema Validation with Pydantic

```python
from nextmcp import NextMCP
from pydantic import BaseModel

app = NextMCP("my-server")

class WeatherInput(BaseModel):
    city: str
    units: str = "fahrenheit"

@app.tool()
def get_weather(city: str, units: str = "fahrenheit") -> dict:
    # Input automatically validated against WeatherInput schema
    return {"city": city, "temp": 72, "units": units}
```

### Prompts

Prompts are user-driven workflow templates that guide AI interactions. They're explicitly invoked by users (not automatically by the AI) and can reference available tools and resources.

#### Basic Prompts

```python
from nextmcp import NextMCP

app = NextMCP("my-server")

@app.prompt()
def vacation_planner(destination: str, budget: int) -> str:
    """Plan a vacation itinerary."""
    return f"""
    Plan a vacation to {destination} with a budget of ${budget}.

    Use these tools:
    - flight_search: Find flights
    - hotel_search: Find accommodations

    Check these resources:
    - resource://user/preferences
    - resource://calendar/availability
    """
```

#### Prompts with Argument Completion

```python
from nextmcp import argument

@app.prompt(description="Research a topic", tags=["research"])
@argument("topic", description="What to research", suggestions=["Python", "MCP", "FastMCP"])
@argument("depth", suggestions=["basic", "detailed", "comprehensive"])
def research_prompt(topic: str, depth: str = "basic") -> str:
    """Generate a research prompt with the specified depth."""
    return f"Research {topic} at {depth} level..."

# Dynamic completion
@app.prompt_completion("research_prompt", "topic")
async def complete_topics(partial: str) -> list[str]:
    """Provide dynamic topic suggestions."""
    topics = await fetch_available_topics()
    return [t for t in topics if partial.lower() in t.lower()]
```

#### Async Prompts

```python
@app.prompt(tags=["analysis"])
async def analyze_prompt(data_source: str) -> str:
    """Generate analysis prompt with real-time data."""
    data = await fetch_data(data_source)
    return f"Analyze this data: {data}"
```

**When to use prompts:**
- Guide complex multi-step workflows
- Provide templates for common tasks
- Structure AI interactions
- Reference available tools and resources

See `examples/knowledge_base/` for a complete example using prompts.

### Resources

Resources provide read-only access to contextual data through unique URIs. They're application-driven and give the AI access to information without triggering actions.

#### Direct Resources

```python
from nextmcp import NextMCP

app = NextMCP("my-server")

@app.resource("file:///logs/app.log", description="Application logs")
def app_logs() -> str:
    """Provide access to application logs."""
    with open("/var/logs/app.log") as f:
        return f.read()

@app.resource("config://app/settings", mime_type="application/json")
def app_settings() -> dict:
    """Provide application configuration."""
    return {
        "theme": "dark",
        "language": "en",
        "max_results": 100
    }
```

#### Resource Templates

Templates allow parameterized access to dynamic resources:

```python
@app.resource_template("weather://forecast/{city}/{date}")
async def weather_forecast(city: str, date: str) -> dict:
    """Get weather forecast for a specific city and date."""
    return await fetch_weather(city, date)

@app.resource_template("file:///docs/{category}/{filename}")
def documentation(category: str, filename: str) -> str:
    """Access documentation files."""
    return Path(f"/docs/{category}/{filename}").read_text()

# Template parameter completion
@app.template_completion("weather_forecast", "city")
def complete_cities(partial: str) -> list[str]:
    """Suggest city names."""
    return ["London", "Paris", "Tokyo", "New York"]
```

#### Subscribable Resources

Resources can notify subscribers when they change:

```python
@app.resource(
    "config://live/settings",
    subscribable=True,
    max_subscribers=50
)
async def live_settings() -> dict:
    """Provide live configuration that can change."""
    return await load_live_config()

# Notify subscribers when config changes
app.notify_resource_changed("config://live/settings")

# Manage subscriptions
app.subscribe_to_resource("config://live/settings", "subscriber_id")
app.unsubscribe_from_resource("config://live/settings", "subscriber_id")
```

#### Async Resources

```python
@app.resource("db://users/recent")
async def recent_users() -> list[dict]:
    """Get recently active users from database."""
    return await db.query("SELECT * FROM users ORDER BY last_active DESC LIMIT 10")
```

**When to use resources:**
- Provide read-only data access
- Expose configuration and settings
- Share application state
- Offer real-time data feeds (with subscriptions)

**Resource URIs can use any scheme:**
- `file://` - File system access
- `config://` - Configuration data
- `db://` - Database queries
- `api://` - External API data
- Custom schemes for your use case

See `examples/knowledge_base/` for a complete example using resources and templates.

### Configuration

NextMCP supports multiple configuration sources with automatic merging:

```python
from nextmcp import load_config

# Load from config.yaml and .env
config = load_config(config_file="config.yaml")

# Access configuration
host = config.get_host()
port = config.get_port()
debug = config.is_debug()

# Custom config values
api_key = config.get("api_key", default="default-key")
```

**config.yaml**:
```yaml
host: "0.0.0.0"
port: 8080
log_level: "DEBUG"
api_key: "my-secret-key"
```

**.env**:
```
MCP_HOST=0.0.0.0
MCP_PORT=8080
API_KEY=my-secret-key
```

### WebSocket Transport

NextMCP supports WebSocket transport for real-time, bidirectional communication - perfect for chat applications, live updates, and interactive tools.

#### Server Setup

```python
from nextmcp import NextMCP
from nextmcp.transport import WebSocketTransport

app = NextMCP("websocket-server")

@app.tool()
async def send_message(username: str, message: str) -> dict:
    return {
        "status": "sent",
        "username": username,
        "message": message
    }

# Create WebSocket transport
transport = WebSocketTransport(app)

# Run on ws://localhost:8765
transport.run(host="0.0.0.0", port=8765)
```

#### Client Usage

```python
from nextmcp.transport import WebSocketClient

async def main():
    async with WebSocketClient("ws://localhost:8765") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        # Invoke a tool
        result = await client.invoke_tool(
            "send_message",
            {"username": "Alice", "message": "Hello!"}
        )
        print(f"Result: {result}")
```

#### WebSocket Features

- **Real-time Communication**: Persistent connections with low latency
- **Bidirectional**: Server can push updates to clients
- **JSON-RPC Protocol**: Clean message format for tool invocation
- **Multiple Clients**: Handle multiple concurrent connections
- **Async Native**: Built on Python's async/await for high performance

#### When to Use WebSocket vs HTTP

| Feature | HTTP (FastMCP) | WebSocket |
|---------|----------------|-----------|
| Connection type | One per request | Persistent |
| Latency | Higher overhead | Lower latency |
| Bidirectional | No | Yes |
| Use case | Traditional APIs | Real-time apps |
| Best for | Request/response | Chat, notifications, live data |

See `examples/websocket_chat/` for a complete WebSocket application.

## Plugin System

NextMCP features a powerful plugin system that allows you to extend functionality through modular, reusable components.

### What are Plugins?

Plugins are self-contained modules that can:
- Register new tools with your application
- Add middleware for cross-cutting concerns
- Extend core functionality
- Be easily shared and reused across projects

### Creating a Plugin

```python
from nextmcp import Plugin

class MathPlugin(Plugin):
    name = "math-plugin"
    version = "1.0.0"
    description = "Mathematical operations"
    author = "Your Name"

    def on_load(self, app):
        @app.tool()
        def add(a: float, b: float) -> float:
            """Add two numbers"""
            return a + b

        @app.tool()
        def multiply(a: float, b: float) -> float:
            """Multiply two numbers"""
            return a * b
```

### Using Plugins

#### Method 1: Auto-discovery

```python
from nextmcp import NextMCP

app = NextMCP("my-app")

# Discover all plugins in a directory
app.discover_plugins("./plugins")

# Load all discovered plugins
app.load_plugins()
```

#### Method 2: Direct Loading

```python
from nextmcp import NextMCP
from my_plugins import MathPlugin

app = NextMCP("my-app")

# Load a specific plugin
app.use_plugin(MathPlugin)
```

### Plugin Lifecycle

Plugins have three lifecycle hooks:

1. **`on_init()`** - Called during plugin initialization
2. **`on_load(app)`** - Called when plugin is loaded (register tools here)
3. **on_unload()** - Called when plugin is unloaded (cleanup)

```python
class LifecyclePlugin(Plugin):
    name = "lifecycle-example"
    version = "1.0.0"

    def on_init(self):
        # Early initialization
        self.config = {}

    def on_load(self, app):
        # Register tools and middleware
        @app.tool()
        def my_tool():
            return "result"

    def on_unload(self):
        # Cleanup resources
        self.config.clear()
```

### Plugin with Middleware

```python
class TimingPlugin(Plugin):
    name = "timing"
    version = "1.0.0"

    def on_load(self, app):
        import time

        def timing_middleware(fn):
            def wrapper(*args, **kwargs):
                start = time.time()
                result = fn(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                print(f"⏱️ {fn.__name__} took {elapsed:.2f}ms")
                return result
            return wrapper

        app.add_middleware(timing_middleware)
```

### Plugin Dependencies

Plugins can declare dependencies on other plugins:

```python
class DependentPlugin(Plugin):
    name = "advanced-math"
    version = "1.0.0"
    dependencies = ["math-plugin"]  # Loads math-plugin first

    def on_load(self, app):
        @app.tool()
        def factorial(n: int) -> int:
            # Can use tools from math-plugin
            return 1 if n <= 1 else n * factorial(n - 1)
```

### Managing Plugins

```python
# List all loaded plugins
for plugin in app.plugins.list_plugins():
    print(f"{plugin['name']} v{plugin['version']} - {plugin['loaded']}")

# Get a specific plugin
plugin = app.plugins.get_plugin("math-plugin")

# Unload a plugin
app.plugins.unload_plugin("math-plugin")

# Check if plugin is loaded
if "math-plugin" in app.plugins:
    print("Math plugin is available")
```

### Plugin Best Practices

1. **Use descriptive names** - Make plugin names clear and unique
2. **Version semantically** - Follow semver (major.minor.patch)
3. **Document thoroughly** - Add descriptions and docstrings
4. **Handle errors gracefully** - Catch exceptions in lifecycle hooks
5. **Declare dependencies** - List required plugins explicitly
6. **Implement cleanup** - Use `on_unload()` to release resources

See `examples/plugin_example/` for a complete plugin demonstration with multiple plugin types.

## Metrics & Monitoring

NextMCP includes a built-in metrics system for monitoring your MCP applications in production.

### Quick Start

```python
from nextmcp import NextMCP

app = NextMCP("my-app")
app.enable_metrics()  # That's it! Automatic metrics collection

@app.tool()
def my_tool():
    return "result"
```

### Automatic Metrics

When metrics are enabled, NextMCP automatically tracks:

- **`tool_invocations_total`** - Total number of tool invocations
- **`tool_duration_seconds`** - Histogram of tool execution times
- **`tool_completed_total`** - Completed invocations by status (success/error)
- **`tool_errors_total`** - Errors by error type
- **`tool_active_invocations`** - Currently executing tools

All metrics include labels for the tool name and any global labels you configure.

### Custom Metrics

Add your own metrics for business logic:

```python
@app.tool()
def process_order(order_id: int):
    # Custom counter
    app.metrics.inc_counter("orders_processed")

    # Custom gauge
    app.metrics.set_gauge("current_queue_size", get_queue_size())

    # Custom histogram with timer
    with app.metrics.time_histogram("processing_duration"):
        result = process(order_id)

    return result
```

### Metric Types

#### Counter
Monotonically increasing value. Use for: counts, totals.

```python
counter = app.metrics.counter("requests_total")
counter.inc()  # Increment by 1
counter.inc(5)  # Increment by 5
```

#### Gauge
Value that can go up or down. Use for: current values, temperatures, queue sizes.

```python
gauge = app.metrics.gauge("active_connections")
gauge.set(10)  # Set to specific value
gauge.inc()    # Increment
gauge.dec()    # Decrement
```

#### Histogram
Distribution of values. Use for: durations, sizes.

```python
histogram = app.metrics.histogram("request_duration_seconds")
histogram.observe(0.25)

# Or use as timer
with app.metrics.time_histogram("duration"):
    # Code to time
    pass
```

### Exporting Metrics

#### Prometheus Format

```python
# Get metrics in Prometheus format
prometheus_data = app.get_metrics_prometheus()
print(prometheus_data)
```

Output:
```
# HELP my-app_tool_invocations_total Total tool invocations
# TYPE my-app_tool_invocations_total counter
my-app_tool_invocations_total{tool="my_tool"} 42.0

# HELP my-app_tool_duration_seconds Tool execution duration
# TYPE my-app_tool_duration_seconds histogram
my-app_tool_duration_seconds_bucket{tool="my_tool",le="0.005"} 10
my-app_tool_duration_seconds_bucket{tool="my_tool",le="0.01"} 25
my-app_tool_duration_seconds_sum{tool="my_tool"} 1.234
my-app_tool_duration_seconds_count{tool="my_tool"} 42
```

#### JSON Format

```python
# Get metrics as JSON
json_data = app.get_metrics_json(pretty=True)
```

### Configuration

```python
app.enable_metrics(
    collect_tool_metrics=True,      # Track tool invocations
    collect_system_metrics=False,   # Track CPU/memory (future)
    collect_transport_metrics=False, # Track WebSocket/HTTP (future)
    labels={"env": "prod", "region": "us-west"}  # Global labels
)
```

### Metrics with Labels

Labels allow you to slice and dice your metrics:

```python
counter = app.metrics.counter(
    "api_requests",
    labels={"method": "GET", "endpoint": "/users"}
)
counter.inc()
```

### Integration with Monitoring Systems

The Prometheus format is compatible with:
- Prometheus for scraping and storage
- Grafana for visualization
- AlertManager for alerting
- Any Prometheus-compatible system

See `examples/metrics_example/` for a complete metrics demonstration.

## CLI Commands

NextMCP provides a rich CLI for common development tasks.

### Initialize a new project

```bash
mcp init my-project
mcp init my-project --template weather_bot
mcp init my-project --path /custom/path
```

### Run a server

```bash
mcp run app.py
mcp run app.py --host 0.0.0.0 --port 8080
mcp run app.py --reload  # Auto-reload on changes
```

### Generate documentation

```bash
mcp docs app.py
mcp docs app.py --output docs.md
mcp docs app.py --format json
```

### Show version

```bash
mcp version
```

## Examples

Check out the `examples/` directory for complete working examples:

- **blog_server** - Convention-based project structure with auto-discovery (5 tools, 3 prompts, 4 resources)
- **auth_api_key** - API key authentication with role-based access control
- **auth_jwt** - JWT token authentication with login endpoint and token generation
- **auth_rbac** - Advanced RBAC with fine-grained permissions and wildcards
- **weather_bot** - A weather information server with multiple tools
- **async_weather_bot** - Async version demonstrating concurrent operations and async middleware
- **websocket_chat** - Real-time chat server using WebSocket transport
- **plugin_example** - Plugin system demonstration with multiple plugin types
- **metrics_example** - Metrics and monitoring demonstration with automatic and custom metrics

## Development

### Setting up for development

```bash
# Clone the repository
git clone https://github.com/KeshavVarad/NextMCP.git
cd nextmcp

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install git pre-commit hooks (recommended)
./scripts/install-hooks.sh

# Run tests
pytest

# Run tests with coverage
pytest --cov=nextmcp --cov-report=html

# Format code
black nextmcp tests

# Lint code
ruff check nextmcp tests

# Type check
mypy nextmcp
```

#### Pre-commit Hooks

The repository includes a pre-commit hook that automatically runs before each commit to:
- Check and auto-fix code with ruff
- Format code with black
- Run all tests

Install the hook with:
```bash
./scripts/install-hooks.sh
```

The hook ensures all commits pass linting and tests, preventing CI failures. To bypass the hook (not recommended), use:
```bash
git commit --no-verify
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=nextmcp
```

## Architecture

NextMCP is organized into several modules:

- **`core.py`** - Main `NextMCP` class, application lifecycle, and `from_config()` method
- **`discovery.py`** - Auto-discovery engine for convention-based project structure
- **`tools.py`** - Tool registration, metadata, and documentation generation
- **`middleware.py`** - Built-in middleware for common use cases
- **`config.py`** - Configuration management (YAML, .env, environment variables)
- **`cli.py`** - Typer-based CLI commands
- **`logging.py`** - Centralized logging setup and utilities

## Comparison with FastMCP

NextMCP builds on FastMCP to provide:

| Feature | FastMCP | NextMCP |
|---------|---------|-----------|
| Basic MCP server | ✅ | ✅ |
| Tool registration | Manual | Decorator-based + auto-discovery |
| Convention-based structure | ❌ | ✅ File-based organization |
| Auto-discovery | ❌ | ✅ Automatic primitive registration |
| Zero-config setup | ❌ | ✅ `NextMCP.from_config()` |
| **Authentication & Authorization** | ❌ | ✅ **Built-in auth system** |
| API key auth | ❌ | ✅ APIKeyProvider |
| JWT auth | ❌ | ✅ JWTProvider |
| Session auth | ❌ | ✅ SessionProvider |
| RBAC | ❌ | ✅ Full RBAC system |
| Permission-based access | ❌ | ✅ Fine-grained permissions |
| Async/await support | ❌ | ✅ Full support |
| WebSocket transport | ❌ | ✅ Built-in |
| Middleware | ❌ | Global + tool-specific |
| Plugin system | ❌ | ✅ Full-featured |
| Metrics & monitoring | ❌ | ✅ Built-in |
| CLI commands | ❌ | `init`, `run`, `docs` |
| Project scaffolding | ❌ | Templates & examples |
| Configuration management | ❌ | YAML + .env support |
| Built-in logging | Basic | Colored, structured |
| Schema validation | ❌ | Pydantic integration |
| Testing utilities | ❌ | Included |

## Roadmap

### Completed
- [x] **v0.1.0** - Core MCP server with Tools primitive
- [x] **v0.2.0** - Full MCP Primitives (Prompts, Resources, Resource Templates, Subscriptions)
- [x] **v0.3.0** - Convention-Based Architecture (Auto-discovery, `from_config()`, Project structure)
- [x] **v0.4.0** - Authentication & Authorization (API keys, JWT, Sessions, RBAC)
- [x] Async tool support
- [x] WebSocket transport
- [x] Plugin system
- [x] Built-in monitoring and metrics

### In Progress
- [ ] Production deployment guides
- [ ] Docker support
- [ ] More example projects
- [ ] Documentation site

### Planned

#### v0.5.0 - Production & Deployment
- **Deployment Manifests**: Generate Docker, AWS Lambda, and serverless configs
- **One-Command Deploy**: `mcp deploy --target=aws-lambda`
- **Production Builds**: Optimized bundles with `mcp build`
- **Package Distribution**: `mcp package` for Docker, PyPI, and serverless
- **Hot Reload**: Development mode with automatic file watching
- **Enhanced CLI**: `mcp dev`, `mcp validate`, `mcp test` commands

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on top of [FastMCP](https://github.com/jlowin/fastmcp)
- Inspired by [Next.js](https://nextjs.org/) developer experience
- CLI powered by [Typer](https://typer.tiangolo.com/)

## Support

- GitHub Issues: [https://github.com/KeshavVarad/NextMCP/issues](https://github.com/KeshavVarad/NextMCP/issues)
- Documentation: [Coming soon]

---

**Made with ❤️ by the NextMCP community**
