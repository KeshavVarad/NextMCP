# Changelog

All notable changes to NextMCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-04

### Added

#### Full MCP Primitives Support
- **Prompts**: User-driven workflow templates with argument completion
  - `@app.prompt()` decorator for registering prompts
  - `@argument()` decorator for defining prompt arguments with suggestions
  - `@app.prompt_completion()` for dynamic argument suggestions
  - Automatic metadata extraction from function signatures
  - Full async/await support for prompts
  - Middleware support for prompts

- **Resources**: Read-only context providers with URI-based access
  - `@app.resource()` decorator for direct resources
  - `@app.resource_template()` decorator for parameterized resources
  - URI validation and parameter extraction
  - MIME type auto-detection
  - Full async/await support for resources
  - Middleware support for resources

- **Resource Subscriptions**: Real-time notifications for resource changes
  - `subscribe_to_resource()` method for subscribing to changes
  - `unsubscribe_from_resource()` method for unsubscribing
  - `notify_resource_changed()` method for triggering notifications
  - Subscriber limit enforcement with FIFO ordering
  - Per-resource subscription tracking

#### New Modules
- `nextmcp/prompts.py`: Complete prompt management system
  - `PromptArgument` class for argument metadata
  - `PromptRegistry` for organizing prompts
  - `get_prompt_metadata()` for metadata extraction
  - `generate_prompt_docs()` for documentation generation

- `nextmcp/resources.py`: Complete resource management system
  - `ResourceMetadata` class for resource information
  - `ResourceTemplate` class for URI templates
  - `ResourceRegistry` for organizing resources
  - `get_resource_metadata()` for metadata extraction
  - `generate_resource_docs()` for documentation generation

#### Testing
- 75 new comprehensive tests (209 total, all passing)
- `tests/test_prompts.py`: 31 tests for prompt functionality
- `tests/test_resources.py`: 44 tests for resource functionality
- Full coverage of new features including:
  - Decorator functionality
  - Metadata extraction
  - Registry operations
  - Subscription management
  - Async operations
  - NextMCP integration

### Changed
- Updated Python version requirement to 3.10+ (from 3.8+)
- Modernized type annotations to use built-in types (e.g., `list[str]` instead of `List[str]`)
- Resource subscriptions now use list (FIFO) instead of set for proper ordering

### Technical Details
- NextMCP now supports all three MCP core primitives: Tools, Prompts, and Resources
- Complete implementation of the Model Context Protocol specification
- Maintains decorator-based API consistency across all primitives
- All primitives support middleware and async operations
- FastMCP integration for prompts and resources

### Breaking Changes
None - all changes are additive and backward compatible with v0.1.0

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
