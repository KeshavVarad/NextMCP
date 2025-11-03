# SecureMCP

**Production-grade MCP server toolkit with minimal boilerplate**

SecureMCP is a Python SDK built on top of FastMCP that provides a developer-friendly experience for building MCP (Model Context Protocol) servers. Inspired by Next.js, it offers minimal setup, powerful middleware, and a rich CLI for rapid development.

## Features

- **Minimal Boilerplate** - Get started with just a few lines of code
- **Decorator-based API** - Register tools with simple `@app.tool()` decorators
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
| Middleware | ❌ | Global + tool-specific |
| CLI commands | ❌ | `init`, `run`, `docs` |
| Project scaffolding | ❌ | Templates & examples |
| Configuration management | ❌ | YAML + .env support |
| Built-in logging | Basic | Colored, structured |
| Schema validation | ❌ | Pydantic integration |
| Testing utilities | ❌ | Included |

## Roadmap

- [ ] Async tool support
- [ ] WebSocket transport
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
