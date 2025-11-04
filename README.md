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

### 1. Create a new project

```bash
mcp init my-bot
cd my-bot
```

### 2. Write your first tool

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

### 3. Run your server

```bash
mcp run app.py
```

That's it! Your MCP server is now running with the `greet` tool available.

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

- **`core.py`** - Main `NextMCP` class and application lifecycle
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
| Tool registration | Manual | Decorator-based |
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

- [x] Async tool support
- [x] WebSocket transport
- [x] Plugin system
- [x] Built-in monitoring and metrics
- [ ] Production deployment guides
- [ ] Docker support
- [ ] More example projects
- [ ] Documentation site

## Future Work

NextMCP is evolving to become a complete implementation of the Model Context Protocol specification. Currently, only the **Tools** primitive is fully supported. Future versions will include:

### v0.2.0 - Full MCP Primitives Support
- **Prompts**: User-driven workflow templates with argument completion
- **Resources**: Read-only context providers with URI-based access
- **Resource Templates**: Dynamic resources with parameter-based URIs
- **Subscriptions**: Real-time notifications for resource changes

### v0.3.0 - Convention-Based Architecture
- **File-based Auto-Discovery**: Automatic discovery of tools, prompts, and resources from directory structure
- **Project Manifest**: `nextmcp.config.yaml` for declarative configuration
- **Hot Reload**: Development mode with automatic file watching
- **Enhanced CLI**: `mcp dev`, `mcp validate`, `mcp test` commands

### v0.4.0 - Production & Deployment
- **Deployment Manifests**: Generate Docker, AWS Lambda, and serverless configs
- **One-Command Deploy**: `mcp deploy --target=aws-lambda`
- **Production Builds**: Optimized bundles with `mcp build`
- **Package Distribution**: `mcp package` for Docker, PyPI, and serverless

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
