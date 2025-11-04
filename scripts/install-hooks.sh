#!/bin/bash

# Install Git Hooks
# This script installs pre-commit hooks for NextMCP development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing Git hooks for NextMCP..."
echo ""

# Check if we're in a git repository
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Install pre-commit hook
if [ -f "$REPO_ROOT/hooks/pre-commit" ]; then
    cp "$REPO_ROOT/hooks/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Installed pre-commit hook"
else
    echo "❌ Error: hooks/pre-commit not found"
    exit 1
fi

echo ""
echo "✨ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now run automatically before each commit to:"
echo "  - Check code with ruff (auto-fix enabled)"
echo "  - Format code with black"
echo "  - Run all tests"
echo ""
echo "To bypass the hook (not recommended), use: git commit --no-verify"
