# Changelog

All notable changes to NextMCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-11-04

### Added

#### Authentication & Authorization System
- **Complete Auth Framework** (`nextmcp/auth/`): Production-ready authentication and authorization
  - `AuthContext`: Authentication context with user info, roles, and permissions
  - `AuthProvider`: Base class for authentication strategies
  - `AuthResult`: Authentication result with success/failure and context
  - `Permission`: Fine-grained permission model with wildcard support
  - `Role`: Role class with permission collections

- **Built-in Auth Providers**:
  - **APIKeyProvider**: API key authentication with role/permission mapping
    - Pre-configured key validation
    - Custom validation function support
    - Secure key generation utility
  - **JWTProvider**: JSON Web Token authentication
    - HS256/RS256 algorithm support
    - Automatic expiration validation
    - Token creation and verification
    - Requires PyJWT library
  - **SessionProvider**: Session-based authentication
    - In-memory session storage
    - Automatic session expiration
    - Session creation and destruction
    - Expired session cleanup

- **RBAC System** (`nextmcp/auth/rbac.py`):
  - `RBAC` class for role and permission management
  - Define custom permissions and roles
  - Assign permissions to roles
  - Check and require permissions/roles
  - Load configuration from dictionaries
  - Export configuration to dictionaries
  - `PermissionDeniedError` exception

- **Auth Middleware Decorators**:
  - `@requires_auth` / `@requires_auth_async`: Require authentication
  - `@requires_role` / `@requires_role_async`: Require specific roles
  - `@requires_permission` / `@requires_permission_async`: Require specific permissions
  - Auth context injected as first parameter to protected tools
  - Supports middleware stacking

- **Permission Features**:
  - Exact permission matching (`read:posts`)
  - Wildcard permissions (`admin:*`, `*`)
  - Resource-scoped permissions
  - Permission inheritance through roles

#### Examples
- **API Key Auth Example** (`examples/auth_api_key/`):
  - 3 pre-configured API keys (admin, user, viewer)
  - Role-based access control demonstration
  - Public and protected tools
  - Comprehensive README

- **JWT Auth Example** (`examples/auth_jwt/`):
  - Login endpoint with JWT token generation
  - Token expiration handling
  - Token generation utility script
  - Role-based access demonstration

- **RBAC Example** (`examples/auth_rbac/`):
  - Fine-grained permission control
  - Permission wildcards demonstration
  - RBAC configuration loading
  - Permission-based access control

#### Tests
- **Auth Provider Tests** (`tests/test_auth_providers.py`): 26 tests
  - APIKeyProvider: initialization, authentication, validation, key generation
  - JWTProvider: token creation, verification, expiration, custom claims
  - SessionProvider: session management, expiration, cleanup

- **RBAC Tests** (`tests/test_rbac.py`): 36 tests
  - Permission: creation, matching, wildcards, hashing
  - Role: creation, permission management
  - AuthContext: role and permission checking
  - RBAC: configuration loading, permission checking, access control
  - PermissionDeniedError

### Changed
- **Main Exports** (`nextmcp/__init__.py`):
  - Added all auth classes and functions to public API
  - 15 new authentication-related exports

### Notes
- **100% Backward Compatible**: All 235 existing tests pass
- **62 New Tests**: Comprehensive auth system coverage
- **297 Total Tests**: All passing
- **Optional Dependency**: PyJWT required only for JWT provider

## [0.3.0] - 2025-11-04

### Added

#### Convention-Based Project Structure
- **Auto-Discovery Engine** (`nextmcp/discovery.py`): Automatically discover and register tools, prompts, and resources from directory structure
  - `AutoDiscovery` class for scanning directories
  - Discovers tools from `tools/` directory
  - Discovers prompts from `prompts/` directory
  - Discovers resources from `resources/` directory
  - Supports nested directory structures
  - Skips `__init__.py` and `test_*.py` files automatically

- **NextMCP.from_config()**: Create applications with convention-based structure
  - Load configuration from `nextmcp.config.yaml`
  - Auto-discover all primitives from standard directories
  - Zero-boilerplate server setup
  - Configurable discovery paths
  - Can be disabled with `auto_discover: false`

- **Configuration System Enhancements**:
  - Support for `nextmcp.config.yaml` configuration files
  - Project manifest with metadata (name, version, description)
  - Discovery path configuration
  - Server settings (host, port, transport)
  - Middleware configuration
  - Feature flags (metrics, hot_reload, auto_docs)

- **Project Validation**:
  - `validate_project_structure()` function
  - Validates convention-based directory structure
  - Counts Python files in each directory
  - Warns about missing `__init__.py` files
  - Checks for config file presence

#### Examples
- **Blog Server Example** (`examples/blog_server/`): Complete convention-based example
  - 5 Tools in `tools/posts.py`
  - 3 Prompts in `prompts/workflows.py`
  - 4 Resources in `resources/blog_resources.py`
  - `nextmcp.config.yaml` configuration file
  - Single-line server setup with `NextMCP.from_config()`
  - Comprehensive README with comparison to manual approach

#### Testing
- 26 new comprehensive tests for auto-discovery (245 total, all passing)
- `tests/test_discovery.py`: 19 tests for discovery engine
- `tests/test_integration_discovery.py`: 7 integration tests for from_config()
- Full coverage of:
  - Auto-discovery functionality
  - Config file loading
  - Nested module discovery
  - Error handling
  - Project validation
  - Integration with real project structures

### Changed
- Updated minimum test count from 228 to 235 tests
- Enhanced Config class with convention-based defaults
- Improved import handling in discovery engine to avoid conflicts

### Technical Details
- Convention-based structure similar to Next.js
- Automatic primitive registration eliminates boilerplate
- File-based organization for scalability
- Works with or without configuration files
- All changes are additive - fully backward compatible with v0.2.x

### Key Differentiators from FastMCP
- **Organization**: Single file → Convention-based directories with auto-discovery
- **Configuration**: Imperative Python → Declarative YAML + conventions
- **Project Structure**: Unstructured → Organized (tools/, prompts/, resources/)
- **Setup**: Manual registration → One-line `NextMCP.from_config()`
- **Modularity**: All in one file → Organized by primitive type
- **Discoverability**: Must import/register → Auto-discovery from directories

### Breaking Changes
None - all changes are additive and backward compatible with v0.2.x

## [0.2.1] - 2025-11-04

### Added

#### Examples
- **Knowledge Base Example** (`examples/knowledge_base/`): Comprehensive example demonstrating all three MCP primitives working together
  - 3 Tools: search_knowledge, add_article, list_categories
  - 3 Prompts: research_prompt, summary_report_prompt, document_prompt
  - 4 Resources: stats, config, articles/{id}, category/{name}
  - Shows practical usage of tools, prompts, and resources in a real application
  - Includes argument/parameter completion examples
  - Demonstrates subscribable resources

#### Documentation
- Added comprehensive **Prompts** section to README
  - Basic prompts with examples
  - Prompts with argument completion
  - Dynamic completion functions
  - Async prompts
  - When to use prompts

- Added comprehensive **Resources** section to README
  - Direct resources with examples
  - Resource templates with parameters
  - Subscribable resources with notifications
  - Async resources
  - URI schemes and conventions
  - When to use resources

- Updated features list to highlight:
  - Full MCP specification support
  - Argument completion
  - Resource subscriptions
  - Cross-primitive middleware

### Changed
- Enhanced feature descriptions to emphasize all three primitives

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
