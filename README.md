# SecureMCP

**Production-grade MCP server toolkit with minimal boilerplate**

SecureMCP is a Python SDK built on top of FastMCP that provides a developer-friendly experience for building MCP (Model Context Protocol) servers. Inspired by Next.js, it offers minimal setup, powerful middleware, and a rich CLI for rapid development.

## Features

- **Minimal Boilerplate** - Get started with just a few lines of code
- **Decorator-based API** - Register tools with simple `@app.tool()` decorators
- **Async Support** - Full support for async/await with async tools and middleware
- **WebSocket Transport** - Real-time bidirectional communication for interactive applications
- **Global & Tool-specific Middleware** - Add logging, auth, rate limiting, caching, and more
- **Rich CLI** - Scaffold projects, run servers, and generate docs with `mcp` commands
- **Configuration Management** - Support for `.env`, YAML config files, and environment variables
- **Schema Validation** - Optional Pydantic integration for type-safe tool inputs
- **Production Ready** - Built-in error handling, logging, and testing utilities

## Installation

### Basic Installation

```bash
pip install securemcp
```

### With Optional Dependencies

```bash
# CLI tools (recommended)
pip install securemcp[cli]

# Configuration support
pip install securemcp[config]

# Schema validation with Pydantic
pip install securemcp[schema]

# WebSocket transport
pip install securemcp[websocket]

# Everything
pip install securemcp[all]

# Development dependencies
pip install securemcp[dev]
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
from securemcp import SecureMCP

app = SecureMCP("my-bot")

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
from securemcp import SecureMCP

app = SecureMCP(
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
from securemcp import log_calls, error_handler

# Add middleware that applies to all tools
app.add_middleware(log_calls)
app.add_middleware(error_handler)

@app.tool()
def my_tool(x: int) -> int:
    return x * 2  # This will be logged and error-handled automatically
```

#### Tool-specific Middleware

```python
from securemcp import cache_results, require_auth

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

SecureMCP includes several production-ready middleware:

- **`log_calls`** - Log all tool invocations with timing
- **`error_handler`** - Catch exceptions and return structured errors
- **`require_auth(valid_keys)`** - API key authentication
- **`rate_limit(max_calls, time_window)`** - Rate limiting
- **`cache_results(ttl_seconds)`** - Response caching
- **`validate_inputs(**validators)`** - Custom input validation
- **`timeout(seconds)`** - Execution timeout

All middleware also have async variants (e.g., `log_calls_async`, `error_handler_async`, etc.) for use with async tools.

### Async Support

SecureMCP has full support for async/await patterns, allowing you to build high-performance tools that can handle concurrent I/O operations.

#### Basic Async Tool

```python
from securemcp import SecureMCP
import asyncio

app = SecureMCP("async-app")

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
from securemcp import log_calls_async, error_handler_async, cache_results_async

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
from securemcp import SecureMCP
from pydantic import BaseModel

app = SecureMCP("my-server")

class WeatherInput(BaseModel):
    city: str
    units: str = "fahrenheit"

@app.tool()
def get_weather(city: str, units: str = "fahrenheit") -> dict:
    # Input automatically validated against WeatherInput schema
    return {"city": city, "temp": 72, "units": units}
```

### Configuration

SecureMCP supports multiple configuration sources with automatic merging:

```python
from securemcp import load_config

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

SecureMCP supports WebSocket transport for real-time, bidirectional communication - perfect for chat applications, live updates, and interactive tools.

#### Server Setup

```python
from securemcp import SecureMCP
from securemcp.transport import WebSocketTransport

app = SecureMCP("websocket-server")

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
from securemcp.transport import WebSocketClient

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

## CLI Commands

SecureMCP provides a rich CLI for common development tasks.

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

## Development

### Setting up for development

```bash
# Clone the repository
git clone https://github.com/yourusername/securemcp.git
cd securemcp

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=securemcp --cov-report=html

# Format code
black securemcp tests

# Lint code
ruff check securemcp tests

# Type check
mypy securemcp
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
pytest --cov=securemcp
```

## Architecture

SecureMCP is organized into several modules:

- **`core.py`** - Main `SecureMCP` class and application lifecycle
- **`tools.py`** - Tool registration, metadata, and documentation generation
- **`middleware.py`** - Built-in middleware for common use cases
- **`config.py`** - Configuration management (YAML, .env, environment variables)
- **`cli.py`** - Typer-based CLI commands
- **`logging.py`** - Centralized logging setup and utilities

## Comparison with FastMCP

SecureMCP builds on FastMCP to provide:

| Feature | FastMCP | SecureMCP |
|---------|---------|-----------|
| Basic MCP server | ✅ | ✅ |
| Tool registration | Manual | Decorator-based |
| Async/await support | ❌ | ✅ Full support |
| WebSocket transport | ❌ | ✅ Built-in |
| Middleware | ❌ | Global + tool-specific |
| CLI commands | ❌ | `init`, `run`, `docs` |
| Project scaffolding | ❌ | Templates & examples |
| Configuration management | ❌ | YAML + .env support |
| Built-in logging | Basic | Colored, structured |
| Schema validation | ❌ | Pydantic integration |
| Testing utilities | ❌ | Included |

## Roadmap

- [x] Async tool support
- [x] WebSocket transport
- [ ] Plugin system
- [ ] Built-in monitoring and metrics
- [ ] Production deployment guides
- [ ] Docker support
- [ ] More example projects
- [ ] Documentation site

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

- GitHub Issues: [https://github.com/yourusername/securemcp/issues](https://github.com/yourusername/securemcp/issues)
- Documentation: [Coming soon]

---

**Made with ❤️ by the SecureMCP community**
