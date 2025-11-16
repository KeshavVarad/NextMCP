# OAuth Integration Testing Setup

This guide explains how to set up OAuth credentials and obtain access tokens for running integration tests.

## Overview

The integration tests (`tests/test_oauth_integration.py`) verify that the OAuth implementation works with real GitHub and Google APIs. To run these tests, you need:

1. **OAuth App Credentials** - Client ID and Secret from GitHub/Google
2. **Access Tokens** - Pre-obtained tokens for testing authenticated endpoints
3. **Environment Variables** - Configuration for the tests

## Quick Start

```bash
# 1. Get OAuth credentials (see detailed instructions below)
# 2. Use the helper script to obtain tokens
python examples/auth/oauth_token_helper.py

# 3. Set environment variables
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
export GITHUB_ACCESS_TOKEN="gho_..."

export GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your_client_secret"
export GOOGLE_ACCESS_TOKEN="ya29..."
export GOOGLE_REFRESH_TOKEN="1//..."

# 4. Run integration tests
pytest tests/test_oauth_integration.py -v -m integration
```

---

## GitHub OAuth Setup

### Step 1: Create a GitHub OAuth App

1. Go to **GitHub Settings** → **Developer settings** → **OAuth Apps**
   - Direct link: https://github.com/settings/developers

2. Click **"New OAuth App"**

3. Fill in the application details:
   ```
   Application name: NextMCP OAuth Testing
   Homepage URL: http://localhost:8080
   Authorization callback URL: http://localhost:8080/oauth/callback
   ```

4. Click **"Register application"**

5. You'll see your **Client ID** - copy this

6. Click **"Generate a new client secret"** and copy the secret
   - ⚠️ Save this immediately - you won't be able to see it again!

### Step 2: Get GitHub Access Token

You have two options:

#### Option A: Use the Helper Script (Recommended)

```bash
python examples/auth/oauth_token_helper.py --provider github
```

The script will:
1. Generate an authorization URL
2. Open your browser to authorize
3. Start a local callback server
4. Automatically extract the access token
5. Show you the environment variables to set

#### Option B: Manual Token Generation

1. **Generate Authorization URL**:
   ```bash
   python -c "
   from nextmcp.auth import GitHubOAuthProvider
   provider = GitHubOAuthProvider(
       client_id='YOUR_CLIENT_ID',
       client_secret='YOUR_CLIENT_SECRET',
       scope=['read:user', 'repo']
   )
   auth_data = provider.generate_authorization_url()
   print(f'Visit: {auth_data[\"url\"]}')
   print(f'Verifier: {auth_data[\"verifier\"]}')
   "
   ```

2. **Visit the URL** in your browser and click "Authorize"

3. **Copy the code** from the callback URL:
   ```
   http://localhost:8080/oauth/callback?code=AUTHORIZATION_CODE&state=...
   ```

4. **Exchange code for token**:
   ```bash
   python -c "
   import asyncio
   from nextmcp.auth import GitHubOAuthProvider

   async def get_token():
       provider = GitHubOAuthProvider(
           client_id='YOUR_CLIENT_ID',
           client_secret='YOUR_CLIENT_SECRET'
       )
       token_data = await provider.exchange_code_for_token(
           code='AUTHORIZATION_CODE',
           state='STATE_FROM_URL',
           verifier='VERIFIER_FROM_STEP_1'
       )
       print(f'Access Token: {token_data[\"access_token\"]}')

   asyncio.run(get_token())
   "
   ```

5. **Set environment variable**:
   ```bash
   export GITHUB_ACCESS_TOKEN="gho_xxxxxxxxxxxxxxxxxxxxx"
   ```

### Step 3: Configure Environment

```bash
# Add to your ~/.bashrc or ~/.zshrc
export GITHUB_CLIENT_ID="your_client_id_here"
export GITHUB_CLIENT_SECRET="your_client_secret_here"
export GITHUB_ACCESS_TOKEN="gho_your_access_token_here"
```

Or create a `.env` file:
```bash
# .env
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
GITHUB_ACCESS_TOKEN=gho_your_access_token_here
```

Then load it:
```bash
export $(cat .env | xargs)
```

---

## Google OAuth Setup

### Step 1: Create a Google Cloud Project

1. Go to **Google Cloud Console**: https://console.cloud.google.com

2. **Create a new project**:
   - Click the project dropdown at the top
   - Click "New Project"
   - Name: "NextMCP OAuth Testing"
   - Click "Create"

3. **Enable APIs**:
   - Go to "APIs & Services" → "Library"
   - Search for and enable:
     - Google Drive API
     - Gmail API
     - Google+ API (for userinfo)

### Step 2: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**

2. Click **"Create Credentials"** → **"OAuth client ID"**

3. If prompted, configure the OAuth consent screen:
   - User Type: **External**
   - App name: **NextMCP OAuth Testing**
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add these scopes:
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `.../auth/drive.readonly`
     - `.../auth/gmail.readonly`
   - Test users: Add your email address

4. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: **NextMCP OAuth Testing**
   - Authorized redirect URIs:
     - `http://localhost:8080/oauth/callback`
   - Click "Create"

5. **Download credentials** or copy:
   - Client ID (ends in `.apps.googleusercontent.com`)
   - Client Secret

### Step 3: Get Google Access Token

#### Option A: Use the Helper Script (Recommended)

```bash
python examples/auth/oauth_token_helper.py --provider google
```

The script will:
1. Generate an authorization URL with offline access
2. Open your browser to authorize
3. Start a local callback server
4. Extract access token AND refresh token
5. Show you the environment variables to set

#### Option B: Manual Token Generation

1. **Generate Authorization URL**:
   ```bash
   python -c "
   from nextmcp.auth import GoogleOAuthProvider
   provider = GoogleOAuthProvider(
       client_id='YOUR_CLIENT_ID.apps.googleusercontent.com',
       client_secret='YOUR_CLIENT_SECRET',
       scope=[
           'https://www.googleapis.com/auth/userinfo.profile',
           'https://www.googleapis.com/auth/userinfo.email',
           'https://www.googleapis.com/auth/drive.readonly'
       ]
   )
   auth_data = provider.generate_authorization_url()
   print(f'Visit: {auth_data[\"url\"]}')
   print(f'Verifier: {auth_data[\"verifier\"]}')
   "
   ```

2. **Visit the URL**, sign in, and authorize the app

3. **Copy the code** from the callback URL

4. **Exchange code for tokens**:
   ```bash
   python -c "
   import asyncio
   from nextmcp.auth import GoogleOAuthProvider

   async def get_token():
       provider = GoogleOAuthProvider(
           client_id='YOUR_CLIENT_ID',
           client_secret='YOUR_CLIENT_SECRET'
       )
       token_data = await provider.exchange_code_for_token(
           code='AUTHORIZATION_CODE',
           state='STATE_FROM_URL',
           verifier='VERIFIER_FROM_STEP_1'
       )
       print(f'Access Token: {token_data[\"access_token\"]}')
       print(f'Refresh Token: {token_data.get(\"refresh_token\", \"N/A\")}')

   asyncio.run(get_token())
   "
   ```

5. **Set environment variables**:
   ```bash
   export GOOGLE_ACCESS_TOKEN="ya29.xxxxxxxxxxxxx"
   export GOOGLE_REFRESH_TOKEN="1//xxxxxxxxxxxxx"  # If provided
   ```

### Step 4: Configure Environment

```bash
# Add to your ~/.bashrc or ~/.zshrc
export GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your_client_secret"
export GOOGLE_ACCESS_TOKEN="ya29.your_access_token"
export GOOGLE_REFRESH_TOKEN="1//your_refresh_token"
```

Or create a `.env` file:
```bash
# .env
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_ACCESS_TOKEN=ya29.your_access_token
GOOGLE_REFRESH_TOKEN=1//your_refresh_token
```

---

## Running the Tests

### Run All Integration Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run integration tests with verbose output
pytest tests/test_oauth_integration.py -v -m integration
```

### Run Specific Provider Tests

```bash
# GitHub only
pytest tests/test_oauth_integration.py::TestGitHubOAuthIntegration -v

# Google only
pytest tests/test_oauth_integration.py::TestGoogleOAuthIntegration -v
```

### Run Specific Test

```bash
# Test GitHub user info retrieval
pytest tests/test_oauth_integration.py::TestGitHubOAuthIntegration::test_github_get_user_info -v

# Test Google token refresh
pytest tests/test_oauth_integration.py::TestGoogleOAuthIntegration::test_google_token_refresh -v
```

### Skip Integration Tests (Default)

```bash
# Regular test run automatically skips integration tests
pytest

# Or explicitly skip them
pytest -m "not integration"
```

---

## Troubleshooting

### "Tests skipped" message

This means the required environment variables are not set. Check:

```bash
# Verify environment variables are set
echo $GITHUB_CLIENT_ID
echo $GITHUB_ACCESS_TOKEN
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_ACCESS_TOKEN

# If empty, source your environment file
source ~/.bashrc  # or ~/.zshrc
# or
export $(cat .env | xargs)
```

### "Invalid token" errors

Access tokens expire! GitHub tokens last indefinitely (until revoked), but Google access tokens expire after 1 hour.

**Solution**: Re-run the helper script to get a fresh token:
```bash
python examples/auth/oauth_token_helper.py --provider google
```

For Google, use the refresh token to get a new access token:
```bash
pytest tests/test_oauth_integration.py::TestGoogleOAuthIntegration::test_google_token_refresh -v -s
# Copy the new access token from the output
```

### "Redirect URI mismatch" errors

Make sure your OAuth app has `http://localhost:8080/oauth/callback` as an authorized redirect URI.

### Google "Access blocked: Authorization Error"

Your app is in testing mode. Add your Google account as a test user:
1. Go to Google Cloud Console
2. APIs & Services → OAuth consent screen
3. Scroll to "Test users"
4. Click "Add Users"
5. Add your email address

### Rate limiting

OAuth APIs have rate limits. If you hit them:
- **GitHub**: Wait a bit or use a different account
- **Google**: Wait for the quota to reset (usually hourly)

---

## Security Best Practices

⚠️ **Never commit credentials to git!**

Add to `.gitignore`:
```
.env
.env.*
*_credentials.json
*_token.json
```

Use environment variables or a secure secrets manager in production.

For testing, tokens with minimal scopes are recommended:
- **GitHub**: `read:user` is sufficient for basic tests
- **Google**: Use `userinfo.profile` and `userinfo.email` only

---

## What Each Test Verifies

### GitHub Tests

1. **Authorization URL Generation** - Verifies PKCE challenge and URL formatting
2. **User Info Retrieval** - Tests GitHub API `/user` endpoint
3. **Authentication Flow** - Tests complete auth with access token
4. **Error Handling** - Verifies invalid tokens are rejected

### Google Tests

1. **Authorization URL Generation** - Verifies offline access parameters
2. **User Info Retrieval** - Tests Google userinfo API
3. **Authentication Flow** - Tests complete auth with access token
4. **Token Refresh** - Tests refresh token flow (unique to Google)
5. **Error Handling** - Verifies invalid tokens/refresh tokens are rejected

---

## Next Steps

Once you have integration tests passing, you can:

1. **Build OAuth-protected tools** using the examples in `examples/auth/`
2. **Implement OAuth callback servers** for production use
3. **Add custom OAuth providers** by extending `OAuthProvider`
4. **Test with your own APIs** using the authenticated tokens

For production deployments, see the examples in `examples/auth/` for complete OAuth flow implementations.
