# Changelog

All notable changes to NextMCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-03

### Added

#### Core Features
- Initial release of NextMCP - Production-grade MCP server toolkit
- Decorator-based tool registration with `@app.tool()`
- Full async/await support for asynchronous tools
- Global and tool-specific middleware system
- Plugin architecture for extensibility

#### Middleware
- `log_calls` - Automatic logging of tool invocations
- `error_handler` - Structured error handling and responses
- `require_auth` - API key authentication
- `rate_limit` - Rate limiting per tool
- `validate_inputs` - Input validation middleware
- `cache_results` - Response caching
- `timeout` - Execution timeout enforcement
- Async versions of all middleware

#### Transport
- WebSocket transport for real-time bidirectional communication
- WebSocket client for connecting to remote MCP servers
- Message serialization and deserialization
- Tool invocation over WebSocket

#### Metrics & Monitoring
- Complete metrics collection system
- Counter, Gauge, Histogram, and Summary metric types
- Prometheus exporter for metrics
- JSON exporter for metrics
- Automatic tool invocation tracking
- Duration and error metrics
- Metrics middleware for transparent collection

#### Configuration
- Multi-source configuration management
- Support for .env files
- Support for YAML configuration files
- Environment variable overrides
- Hierarchical configuration with defaults

#### CLI Tools
- `mcp init` - Scaffold new projects from templates
- `mcp run` - Run MCP servers
- `mcp docs` - Generate documentation
- `mcp version` - Show version information
- Rich terminal output with syntax highlighting

#### Development Tools
- Comprehensive logging system with context support
- Tool metadata and documentation generation
- Plugin discovery and management
- Type hints and Pydantic integration support

#### Examples
- Weather Bot - Basic MCP server example
- Async Weather Bot - Asynchronous operations example
- WebSocket Chat - Real-time communication example
- Plugin Example - Custom plugin implementation
- Metrics Example - Monitoring and metrics collection

#### Testing
- 134 comprehensive tests covering all features
- Unit tests for core functionality
- Integration tests for middleware and plugins
- Async test support
- 100% of critical paths tested

#### Documentation
- Comprehensive README with examples
- API documentation in docstrings
- Example projects with detailed READMEs
- Configuration guides
- Middleware usage examples

### Technical Details
- Python 3.8+ support
- Built on top of FastMCP
- Type-safe with full type hints
- Production-ready error handling
- Thread-safe metrics collection
- Modular architecture with optional dependencies

### Package Structure
- Core package: `nextmcp`
- Optional dependencies for CLI, config, WebSocket, and schema validation
- Extensible plugin system
- Clean separation of concerns

### Known Limitations
- Authentication system is basic (enhanced auth planned for v0.2.0)
- Metrics are in-memory only (persistent storage planned for future release)
- No built-in OAuth support yet (planned for v0.2.0)

---

## Upcoming Features (Roadmap)

### v0.2.0 (Planned)
- Advanced authentication system with secrets management
- OAuth 2.0 support
- Pre-built API clients (GitHub, Stripe, Slack)
- Persistent metrics storage
- Enhanced error handling
- More example integrations

### v0.3.0 (Future)
- Distributed tracing
- Health check endpoints
- API versioning support
- GraphQL transport option
- Enhanced documentation site

---

[0.1.0]: https://github.com/KeshavVarad/NextMCP/releases/tag/v0.1.0
