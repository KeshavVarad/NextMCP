#!/bin/bash
# Setup script for OAuth integration testing environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

echo "=========================================="
echo "NextMCP OAuth Environment Setup"
echo "=========================================="
echo

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  .env file already exists at: $ENV_FILE"
    echo
    read -p "Do you want to overwrite it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Your existing .env file was not modified."
        exit 0
    fi
fi

# Copy example file
echo "Creating .env file from template..."
cp "$ENV_EXAMPLE" "$ENV_FILE"
echo "✓ Created .env file at: $ENV_FILE"
echo

# Provide instructions
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo
echo "1. Get OAuth credentials:"
echo "   • GitHub: https://github.com/settings/developers"
echo "   • Google: https://console.cloud.google.com"
echo
echo "2. Obtain access tokens using the helper script:"
echo "   python examples/auth/oauth_token_helper.py"
echo
echo "3. Edit .env file and fill in your credentials:"
echo "   ${EDITOR:-nano} .env"
echo
echo "4. Load environment variables:"
echo "   export \$(cat .env | grep -v '^#' | xargs)"
echo
echo "5. Verify setup:"
echo "   echo \$GITHUB_CLIENT_ID"
echo "   echo \$GITHUB_ACCESS_TOKEN"
echo
echo "6. Run integration tests:"
echo "   pytest tests/test_oauth_integration.py -v -m integration"
echo
echo "=========================================="
echo "For detailed setup instructions, see:"
echo "docs/OAUTH_TESTING_SETUP.md"
echo "=========================================="
