# Contributing to NextMCP

Thank you for your interest in contributing to NextMCP! We welcome contributions from the community.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- pip

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/NextMCP.git
   cd NextMCP
   ```

3. Create a virtual environment and install development dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

4. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

Run the full test suite:
```bash
pytest tests/ -v
```

Run tests with coverage:
```bash
pytest tests/ --cov=nextmcp --cov-report=term-missing
```

### Code Quality

We use several tools to maintain code quality:

**Linting:**
```bash
ruff check nextmcp/
```

**Formatting:**
```bash
black nextmcp/
```

**Type Checking:**
```bash
mypy nextmcp/
```

**Run all checks:**
```bash
ruff check nextmcp/ && black --check nextmcp/ && mypy nextmcp/
```

### Making Changes

1. Write your code
2. Add tests for new functionality
3. Ensure all tests pass
4. Run code quality checks
5. Update documentation if needed
6. Commit your changes with clear, descriptive messages

### Commit Messages

Follow conventional commit format:
- `feat: Add new feature`
- `fix: Fix bug in X`
- `docs: Update documentation`
- `test: Add tests for X`
- `refactor: Refactor X`
- `chore: Update dependencies`

Example:
```
feat: Add WebSocket heartbeat support

- Add ping/pong mechanism
- Configure heartbeat interval
- Add tests for connection keepalive
```

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass and code quality checks succeed
2. Update the README.md with details of changes if needed
3. Update the CHANGELOG.md if this is a significant change
4. Push to your fork and submit a pull request to the `main` branch
5. Wait for review and address any feedback

### Pull Request Guidelines

- **Title**: Clear, descriptive title
- **Description**: Explain what changes you made and why
- **Tests**: Include tests for new features
- **Documentation**: Update docs for user-facing changes
- **Breaking Changes**: Clearly mark breaking changes

Example PR description:
```markdown
## Description
Adds WebSocket heartbeat support to prevent connection timeouts

## Changes
- Added ping/pong mechanism in WebSocketTransport
- Configurable heartbeat interval (default: 30s)
- Automatic reconnection on timeout

## Testing
- Added unit tests for heartbeat mechanism
- Tested with long-running connections
- All existing tests pass

## Breaking Changes
None
```

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Public or private harassment
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## Questions?

- Open a [GitHub Discussion](https://github.com/KeshavVarad/NextMCP/discussions) for questions
- Check existing [Issues](https://github.com/KeshavVarad/NextMCP/issues) and [Pull Requests](https://github.com/KeshavVarad/NextMCP/pulls)
- Read the [Documentation](https://github.com/KeshavVarad/NextMCP#readme)

## Areas for Contribution

We especially welcome contributions in these areas:

### High Priority
- 🐛 Bug fixes
- 📚 Documentation improvements
- ✨ Example projects
- 🧪 Additional tests

### Medium Priority
- 🎨 New middleware implementations
- 🔌 Plugin examples
- 🚀 Performance improvements
- 🌐 Transport implementations

### Ideas Welcome
- 💡 New features (open an issue first to discuss)
- 🛠 Developer tools
- 📊 Monitoring integrations
- 🔐 Security enhancements

## Recognition

Contributors will be:
- Listed in our README
- Mentioned in release notes
- Given credit in commit messages (Co-Authored-By)

## License

By contributing to NextMCP, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to NextMCP! 🎉
