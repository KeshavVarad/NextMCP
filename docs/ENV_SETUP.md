# Environment Variables Setup for OAuth Testing

Quick guide for setting up environment variables for OAuth integration tests.

## Quick Start

```bash
# 1. Create .env file from template
cp .env.example .env

# Or use the setup script
bash scripts/setup_env.sh

# 2. Get OAuth tokens using helper script
python examples/auth/oauth_token_helper.py

# 3. Edit .env file and paste your credentials
nano .env  # or vim, code, etc.

# 4. Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# 5. Verify
echo $GITHUB_CLIENT_ID
echo $GITHUB_ACCESS_TOKEN

# 6. Run tests
pytest tests/test_oauth_integration.py -v -m integration
```

## .env File Format

The `.env.example` file provides a template with all required variables:

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
GITHUB_ACCESS_TOKEN=gho_your_github_access_token_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_ACCESS_TOKEN=ya29.your_google_access_token_here
GOOGLE_REFRESH_TOKEN=1//your_google_refresh_token_here
```

## Loading Environment Variables

### Option 1: Shell Export (Temporary)

Loads variables for current shell session only:

```bash
# Load all variables (filters comments)
export $(cat .env | grep -v '^#' | xargs)

# Simpler version (includes comments in variable names, may cause issues)
export $(cat .env | xargs)
```

### Option 2: Shell Configuration (Persistent)

Add to `~/.bashrc` or `~/.zshrc` to load automatically:

```bash
# Add to ~/.bashrc or ~/.zshrc
if [ -f ~/path/to/nextmcp/.env ]; then
    export $(cat ~/path/to/nextmcp/.env | grep -v '^#' | xargs)
fi
```

### Option 3: Direnv (Automatic)

Install [direnv](https://direnv.net/) for automatic loading:

```bash
# Install direnv
brew install direnv  # macOS
# or
sudo apt install direnv  # Linux

# Add to shell config
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # for bash
# or
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc   # for zsh

# Allow .env in project directory
cd /path/to/nextmcp
direnv allow .

# Now .env loads automatically when you cd into the directory
```

### Option 4: Python dotenv

Load in Python code:

```python
from dotenv import load_dotenv

load_dotenv()  # Loads .env from current directory

# Now os.getenv() will find the variables
import os
client_id = os.getenv("GITHUB_CLIENT_ID")
```

## Security Best Practices

### ✅ DO:
- Keep `.env` files local only (never commit to git)
- Use different `.env` files for different environments (`.env.test`, `.env.production`)
- Rotate tokens regularly
- Use minimal scopes needed for testing
- Add `.env*` to `.gitignore` (already done)

### ❌ DON'T:
- Commit `.env` files to git (already ignored)
- Share `.env` files via email or chat
- Use production credentials for testing
- Grant unnecessary OAuth scopes
- Keep tokens that aren't being used

## Troubleshooting

### Variables Not Loading

```bash
# Check if .env exists
ls -la .env

# Check .env contents (be careful - contains secrets!)
cat .env

# Verify export command worked
echo $GITHUB_CLIENT_ID

# If empty, manually export one variable to test
export GITHUB_CLIENT_ID="test_value"
echo $GITHUB_CLIENT_ID
```

### Tests Still Skipping

```bash
# Run setup instruction test to see status
pytest tests/test_oauth_integration.py::test_show_setup_instructions -v -s

# This will show which variables are set/missing
```

### Invalid Tokens

Access tokens expire:
- **GitHub**: Personal access tokens don't expire (until revoked)
- **Google**: Access tokens expire after 1 hour

Re-run the helper script to get fresh tokens:

```bash
python examples/auth/oauth_token_helper.py --provider google
```

### Permission Denied

If the export command fails:

```bash
# Check file permissions
ls -l .env

# Should be readable by you
# If not:
chmod 600 .env
```

## Environment Variables Reference

| Variable | Required For | How to Get |
|----------|-------------|------------|
| `GITHUB_CLIENT_ID` | GitHub URL generation | GitHub Settings → Developer Settings → OAuth Apps |
| `GITHUB_CLIENT_SECRET` | GitHub URL generation | Same as above |
| `GITHUB_ACCESS_TOKEN` | GitHub API tests | Run `oauth_token_helper.py --provider github` |
| `GOOGLE_CLIENT_ID` | Google URL generation | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | Google URL generation | Same as above |
| `GOOGLE_ACCESS_TOKEN` | Google API tests | Run `oauth_token_helper.py --provider google` |
| `GOOGLE_REFRESH_TOKEN` | Token refresh tests | Same as above (issued on first auth) |

## Alternative: GitHub Actions Secrets

For CI/CD, use GitHub Actions secrets instead of .env files:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev,oauth]"

      - name: Run integration tests
        env:
          GITHUB_CLIENT_ID: ${{ secrets.GITHUB_CLIENT_ID }}
          GITHUB_CLIENT_SECRET: ${{ secrets.GITHUB_CLIENT_SECRET }}
          GITHUB_ACCESS_TOKEN: ${{ secrets.GITHUB_ACCESS_TOKEN }}
        run: |
          pytest tests/test_oauth_integration.py -v -m integration
```

Then add secrets in: Repository Settings → Secrets and variables → Actions

## See Also

- [Complete OAuth Setup Guide](OAUTH_TESTING_SETUP.md) - Detailed instructions
- [OAuth Examples](../examples/auth/) - Example implementations
- [Integration Tests](../tests/test_oauth_integration.py) - Test source code
