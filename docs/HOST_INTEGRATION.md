# Host Integration Guide for NextMCP Auth

This guide is for **host developers** (Claude Desktop, Cursor, Windsurf, Zed, etc.) who want to support NextMCP's authentication system in their applications.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Discovery: Reading Auth Metadata](#discovery-reading-auth-metadata)
4. [OAuth Flow Implementation](#oauth-flow-implementation)
5. [Sending Authenticated Requests](#sending-authenticated-requests)
6. [Token Management](#token-management)
7. [Error Handling](#error-handling)
8. [UI/UX Recommendations](#uiux-recommendations)
9. [Implementation Checklist](#implementation-checklist)

---

## Overview

### What is NextMCP Auth?

NextMCP provides a standard way for MCP servers to require authentication. Servers can:
- Announce their auth requirements (OAuth providers, scopes, permissions)
- Enforce authentication automatically on all requests
- Manage user sessions with token refresh

### What Hosts Need to Do:

1. **Discovery**: Read server's auth metadata
2. **OAuth Flow**: Implement OAuth 2.0 with PKCE
3. **Token Storage**: Store and manage user tokens
4. **Request Injection**: Include auth credentials in requests
5. **Error Handling**: Handle auth failures gracefully

---

## Quick Start

### Minimum Viable Integration:

```typescript
// 1. Check if server requires auth
const metadata = await server.call("get_auth_metadata");

if (metadata.auth.requirement === "required") {
  // 2. Get OAuth provider info
  const provider = metadata.auth.providers[0]; // e.g., Google

  // 3. Run OAuth flow (see detailed section)
  const tokens = await runOAuthFlow(provider);

  // 4. Store tokens
  await storage.setTokens(serverId, tokens);
}

// 5. Make authenticated requests
const result = await server.call("some_tool", {
  auth: {
    access_token: tokens.access_token
  }
});
```

---

## Discovery: Reading Auth Metadata

### Step 1: Check if Server Exposes Metadata

Not all servers will have this tool, so check:

```typescript
const tools = await server.listTools();
const hasAuthMetadata = tools.some(t => t.name === "get_auth_metadata");

if (hasAuthMetadata) {
  const metadata = await server.call("get_auth_metadata");
  // Process metadata...
}
```

### Step 2: Parse Auth Metadata

The metadata follows this schema:

```typescript
interface AuthMetadata {
  requirement: "required" | "optional" | "none";
  providers: AuthProvider[];
  required_scopes: string[];
  optional_scopes: string[];
  permissions: string[];
  roles: string[];
  supports_multi_user: boolean;
  session_management: "server-side" | "client-side" | "stateless";
  token_refresh_enabled: boolean;
}

interface AuthProvider {
  name: string; // "google", "github"
  type: string; // "oauth2"
  flows: string[]; // ["oauth2-pkce"]
  authorization_url: string;
  token_url: string;
  scopes: string[];
  supports_refresh: boolean;
  supports_pkce: boolean;
}
```

### Example Metadata Response:

```json
{
  "requirement": "required",
  "providers": [
    {
      "name": "google",
      "type": "oauth2",
      "flows": ["oauth2-pkce"],
      "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
      "token_url": "https://oauth2.googleapis.com/token",
      "scopes": ["openid", "email", "profile"],
      "supports_refresh": true,
      "supports_pkce": true
    }
  ],
  "required_scopes": ["openid", "email"],
  "optional_scopes": ["profile"],
  "supports_multi_user": true,
  "token_refresh_enabled": true
}
```

### Step 3: Decision Logic

```typescript
function handleAuthMetadata(metadata: AuthMetadata) {
  switch (metadata.requirement) {
    case "none":
      // No auth needed, proceed normally
      return;

    case "optional":
      // Show "Sign in to unlock features" UI
      showOptionalAuthPrompt(metadata);
      break;

    case "required":
      // Block until user authenticates
      showRequiredAuthPrompt(metadata);
      break;
  }
}
```

---

## OAuth Flow Implementation

### Overview: OAuth 2.0 with PKCE

```
1. Host generates PKCE verifier + challenge
2. Host opens browser to authorization_url
3. User authorizes
4. Provider redirects back with code
5. Host exchanges code + verifier for tokens
6. Host stores tokens
```

### Step 1: Generate PKCE Challenge

```typescript
import crypto from 'crypto';

function generatePKCE() {
  // Generate random verifier (43-128 chars)
  const verifier = crypto.randomBytes(32)
    .toString('base64url');

  // Generate SHA256 challenge
  const challenge = crypto.createHash('sha256')
    .update(verifier)
    .digest('base64url');

  return { verifier, challenge };
}
```

### Step 2: Build Authorization URL

```typescript
function buildAuthUrl(provider: AuthProvider, pkce: PKCE): string {
  const state = crypto.randomBytes(16).toString('hex');

  const params = new URLSearchParams({
    client_id: provider.client_id, // From your OAuth app
    redirect_uri: "http://localhost:8080/oauth/callback",
    response_type: "code",
    state: state,
    code_challenge: pkce.challenge,
    code_challenge_method: "S256",
    scope: provider.scopes.join(" "),
  });

  // For Google, add access_type=offline for refresh tokens
  if (provider.name === "google" && provider.supports_refresh) {
    params.set("access_type", "offline");
    params.set("prompt", "consent");
  }

  return `${provider.authorization_url}?${params}`;
}
```

### Step 3: Handle OAuth Callback

You need a local HTTP server to receive the redirect:

```typescript
import http from 'http';

async function waitForCallback(): Promise<{ code: string; state: string }> {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url!, 'http://localhost:8080');

      if (url.pathname === '/oauth/callback') {
        const code = url.searchParams.get('code');
        const error = url.searchParams.get('error');
        const state = url.searchParams.get('state');

        if (error) {
          res.writeHead(400);
          res.end(`Error: ${error}`);
          reject(new Error(error));
        } else if (code && state) {
          res.writeHead(200);
          res.end('✅ Authorization successful! You can close this window.');
          resolve({ code, state });
        }

        server.close();
      }
    });

    server.listen(8080);
  });
}
```

### Step 4: Exchange Code for Tokens

```typescript
async function exchangeCodeForTokens(
  provider: AuthProvider,
  code: string,
  verifier: string,
): Promise<Tokens> {
  const response = await fetch(provider.token_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: 'http://localhost:8080/oauth/callback',
      client_id: provider.client_id,
      code_verifier: verifier,
      // client_secret only if you have one (confidential clients)
    }),
  });

  if (!response.ok) {
    throw new Error(`Token exchange failed: ${response.statusText}`);
  }

  // GitHub returns form-encoded, Google returns JSON
  const contentType = response.headers.get('content-type');

  if (contentType?.includes('application/json')) {
    return await response.json();
  } else {
    // Parse form-encoded response
    const text = await response.text();
    const params = new URLSearchParams(text);
    return {
      access_token: params.get('access_token'),
      token_type: params.get('token_type'),
      expires_in: parseInt(params.get('expires_in') || '3600'),
      refresh_token: params.get('refresh_token'),
      scope: params.get('scope'),
    };
  }
}
```

### Complete Flow:

```typescript
async function runOAuthFlow(provider: AuthProvider): Promise<Tokens> {
  // 1. Generate PKCE
  const pkce = generatePKCE();
  const state = crypto.randomBytes(16).toString('hex');

  // 2. Build auth URL
  const authUrl = buildAuthUrl(provider, pkce, state);

  // 3. Open browser
  await openBrowser(authUrl);

  // 4. Start local server and wait for callback
  const { code, state: returnedState } = await waitForCallback();

  // 5. Validate state (CSRF protection)
  if (returnedState !== state) {
    throw new Error('State mismatch - possible CSRF attack');
  }

  // 6. Exchange code for tokens
  const tokens = await exchangeCodeForTokens(provider, code, pkce.verifier);

  return tokens;
}
```

---

## Sending Authenticated Requests

### Include Auth in Every Request

Once you have tokens, include them in the request:

```typescript
const request = {
  method: "tools/call",
  params: {
    name: "get_user_data",
    arguments: {
      user_id: "123"
    }
  },
  auth: {
    access_token: tokens.access_token,
    // Optional: include other token info
    refresh_token: tokens.refresh_token,
    scopes: tokens.scope?.split(' '),
  }
};

const response = await server.send(request);
```

### Where to Inject Auth:

NextMCP middleware looks for `request["auth"]`, so:

```typescript
// Correct ✅
{
  "method": "tools/call",
  "params": {...},
  "auth": {
    "access_token": "ya29.a0..."
  }
}

// Incorrect ❌ (won't work)
{
  "method": "tools/call",
  "params": {...},
  "headers": {
    "Authorization": "Bearer ya29.a0..."
  }
}
```

---

## Token Management

### Store Tokens Securely

```typescript
interface StoredTokens {
  access_token: string;
  refresh_token?: string;
  expires_at: number; // Unix timestamp
  scope: string;
  provider: string;
  user_info?: {
    email: string;
    name: string;
  };
}

class TokenStore {
  async saveTokens(serverId: string, tokens: StoredTokens) {
    // Use OS keychain, encrypted storage, etc.
    await keychain.set(`mcp:${serverId}`, JSON.stringify(tokens));
  }

  async loadTokens(serverId: string): Promise<StoredTokens | null> {
    const data = await keychain.get(`mcp:${serverId}`);
    return data ? JSON.parse(data) : null;
  }

  async deleteTokens(serverId: string) {
    await keychain.delete(`mcp:${serverId}`);
  }
}
```

### Check Token Expiration

```typescript
function isTokenExpired(tokens: StoredTokens): boolean {
  if (!tokens.expires_at) return false;
  return Date.now() / 1000 >= tokens.expires_at;
}

function needsRefresh(tokens: StoredTokens, bufferSeconds = 300): boolean {
  if (!tokens.expires_at) return false;
  return Date.now() / 1000 >= tokens.expires_at - bufferSeconds;
}
```

### Refresh Tokens

```typescript
async function refreshTokens(
  provider: AuthProvider,
  refreshToken: string,
): Promise<Tokens> {
  const response = await fetch(provider.token_url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: provider.client_id,
    }),
  });

  if (!response.ok) {
    // Refresh failed - need to re-authenticate
    throw new Error('Token refresh failed');
  }

  return await response.json();
}
```

### Auto-Refresh Strategy

```typescript
async function getValidToken(serverId: string): Promise<string> {
  const stored = await tokenStore.loadTokens(serverId);

  if (!stored) {
    // No tokens - need to authenticate
    throw new Error('Not authenticated');
  }

  if (isTokenExpired(stored)) {
    // Token expired and no refresh token
    if (!stored.refresh_token) {
      throw new Error('Token expired - please re-authenticate');
    }

    // Try to refresh
    try {
      const newTokens = await refreshTokens(provider, stored.refresh_token);
      await tokenStore.saveTokens(serverId, {
        ...newTokens,
        expires_at: Date.now() / 1000 + newTokens.expires_in,
      });
      return newTokens.access_token;
    } catch (e) {
      // Refresh failed - need to re-authenticate
      throw new Error('Token refresh failed - please re-authenticate');
    }
  }

  if (needsRefresh(stored)) {
    // Preemptively refresh (don't wait for request to fail)
    refreshTokens(provider, stored.refresh_token!)
      .then(newTokens => tokenStore.saveTokens(serverId, {
        ...newTokens,
        expires_at: Date.now() / 1000 + newTokens.expires_in,
      }))
      .catch(() => {
        // Refresh failed, but current token still valid
        // Will be handled on next check
      });
  }

  return stored.access_token;
}
```

---

## Error Handling

### Auth Error Types

NextMCP servers return structured errors:

```typescript
interface AuthError {
  error: "authentication_required" | "authorization_denied" | "token_expired";
  message: string;
  required_scopes?: string[];
  providers?: AuthProvider[];
}
```

### Handle Authentication Errors

```typescript
async function handleRequest(request: any) {
  try {
    const response = await server.send(request);
    return response;
  } catch (error) {
    if (error.error === "authentication_required") {
      // Show "Sign in required" UI
      const tokens = await promptUserToSignIn(error.providers);
      // Retry request
      return await server.send({
        ...request,
        auth: { access_token: tokens.access_token }
      });
    }

    if (error.error === "authorization_denied") {
      // User lacks required scopes
      showError(`Missing permissions: ${error.required_scopes.join(', ')}`);
      // Optionally: re-run OAuth flow with additional scopes
    }

    if (error.error === "token_expired") {
      // Token expired - try refresh
      const tokens = await refreshOrReauth(serverId);
      return await server.send({
        ...request,
        auth: { access_token: tokens.access_token }
      });
    }

    throw error;
  }
}
```

---

## UI/UX Recommendations

### 1. Server Connection Flow

```
User adds server
    │
    ▼
Check auth metadata
    │
    ├─► No auth required
    │   → Connect immediately
    │
    └─► Auth required
        │
        ▼
    Show auth prompt:
    "This server requires authentication"
    [Connect with Google] [Connect with GitHub]
        │
        ▼
    Run OAuth flow
        │
        ▼
    Store tokens
        │
        ▼
    Server connected ✓
```

### 2. Auth Prompt Design

**For Required Auth**:
```
┌─────────────────────────────────────────┐
│  📡 Connect to "My MCP Server"          │
│                                         │
│  This server requires authentication    │
│  to protect your data.                  │
│                                         │
│  Required permissions:                  │
│  • Read your profile                    │
│  • Access your files                    │
│                                         │
│  [🔐 Connect with Google]               │
│  [🔐 Connect with GitHub]               │
│                                         │
│  [ Cancel ]                             │
└─────────────────────────────────────────┘
```

**For Optional Auth**:
```
┌─────────────────────────────────────────┐
│  📡 "My MCP Server"                     │
│                                         │
│  ✓ Connected (Limited Features)         │
│                                         │
│  Sign in to unlock:                     │
│  • Personalized responses               │
│  • Save your preferences                │
│  • Access premium features              │
│                                         │
│  [Sign in]  [Maybe later]               │
└─────────────────────────────────────────┘
```

### 3. Token Status Indicator

```
Server: My MCP Server
Status: ✓ Authenticated as user@example.com
Token expires: in 45 minutes
[Refresh] [Sign out]
```

### 4. Error Messages

**Good**:
```
❌ Authentication expired

Your session has expired. Please sign in again.

[Sign in with Google]
```

**Bad**:
```
Error: 401 Unauthorized
```

---

## Implementation Checklist

### Core Features:
- [ ] Read auth metadata from servers
- [ ] Implement OAuth 2.0 with PKCE
- [ ] Local callback server (http://localhost:8080)
- [ ] Token storage (encrypted/keychain)
- [ ] Inject auth in requests
- [ ] Handle auth errors
- [ ] Token refresh logic

### UX Features:
- [ ] "Connect" UI for OAuth providers
- [ ] Auth status indicator
- [ ] Token expiration warnings
- [ ] Re-authentication flow
- [ ] Sign out functionality
- [ ] Multi-account support (optional)

### Security:
- [ ] State parameter validation (CSRF)
- [ ] Secure token storage
- [ ] HTTPS for callback URL (production)
- [ ] Scope validation

### Polish:
- [ ] Provider logos (Google, GitHub)
- [ ] Loading states during OAuth
- [ ] Error recovery
- [ ] Offline mode handling

---

## Reference Implementation

For a complete reference implementation, see:

- **Python Client**: `examples/auth/oauth_token_helper.py`
- **Tests**: `tests/test_oauth_integration.py`

---

## Future Enhancements

These are not required now but may be added in future:

1. **Multiple Accounts**: Support multiple users per server
2. **Account Switching**: Switch between Google/GitHub accounts
3. **Permission Negotiation**: Dynamic scope requests
4. **SSO Integration**: Enterprise SSO support

---

## Getting Help

- NextMCP Issues: https://github.com/anthropics/nextmcp/issues
- MCP Specification: https://modelcontextprotocol.io
- OAuth 2.0 Spec: https://oauth.net/2/

---

## Summary

To support NextMCP auth in your host application:

1. **Read** auth metadata to discover requirements
2. **Implement** OAuth 2.0 with PKCE for authorization
3. **Store** tokens securely
4. **Inject** auth credentials in every request
5. **Refresh** tokens automatically
6. **Handle** errors gracefully with good UX

The auth system is designed to be straightforward to integrate while providing enterprise-grade security.
