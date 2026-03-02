# Docsly MCP + OAuth Setup

Docsly exposes an MCP JSON-RPC endpoint compatible with OpenAI MCP clients and ChatGPT custom app connectors.

## Endpoints

- MCP JSON-RPC: `http://localhost:5001/mcp`
- MCP discovery: `http://localhost:5001/.well-known/mcp`
- OAuth metadata: `http://localhost:5001/.well-known/oauth-authorization-server`
- OAuth authorize: `http://localhost:5001/oauth/authorize`
- OAuth token: `http://localhost:5001/oauth/token`
- Health: `http://localhost:5001/health`

## Required env vars

Set these in your backend container/env:

```bash
MCP_API_KEY=your-mcp-api-key
OAUTH_CLIENT_ID=docsly-openai-client
OAUTH_CLIENT_SECRET=docsly-openai-secret
# Comma-separated allowlist for OAuth callbacks (required for non-localhost)
OAUTH_REDIRECT_ALLOWLIST=https://chat.openai.com/aip/oauth/callback,https://chatgpt.com/aip/oauth/callback
# Testing shortcut only (disable strict redirect checks)
OAUTH_ALLOW_ANY_REDIRECT=true
```

Notes:
- If `OAUTH_REDIRECT_ALLOWLIST` is empty, only `localhost` redirect URIs are accepted.
- `OAUTH_REDIRECT_ALLOWLIST` supports wildcard patterns (example: `https://chat.openai.com/*`).
- `OAUTH_ALLOW_ANY_REDIRECT=true` disables redirect URI checks for quick testing only.
- OAuth tokens are in-memory (good for setup/testing). Restarting server clears active OAuth sessions.

## OpenAI OAuth fields (what to enter)

When OpenAI asks for OAuth values, use:

- `Client ID`: value of `OAUTH_CLIENT_ID`
- `Client Secret`: value of `OAUTH_CLIENT_SECRET`
- `Authorization URL`: `https://<your-domain>/oauth/authorize`
- `Token URL`: `https://<your-domain>/oauth/token`
- `Scope`: `mcp:tools` (or your `OAUTH_DEFAULT_SCOPE`)

MCP URL should be:

- `https://<your-domain>/mcp`

## MCP protocol methods supported

`POST /mcp` supports:
- `initialize`
- `ping`
- `tools/list`
- `tools/call`

## Tools available

### Documents
- `list_documents`
- `get_document`
- `create_document`
- `update_document`
- `delete_document`
- `render_document_to_html`
- `render_document_to_pdf`
- `preview_document_to_pdf`

### Components
- `list_components`
- `get_component`
- `create_component`
- `preview_component_template`
- `render_component_instance`
- `compose_document_from_components`

### Themes
- `list_themes`
- `get_theme`
- `create_theme`

### Misc
- `preview_block`

## Quick test with curl

### 1) MCP initialize (API-key auth)

```bash
curl -X POST http://localhost:5001/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### 2) OAuth authorize URL (open in browser)

```text
http://localhost:5001/oauth/authorize?response_type=code&client_id=docsly-openai-client&redirect_uri=http://localhost:3000/callback&scope=mcp:tools&state=test123
```

This redirects with `?code=...&state=test123`.

### 3) Exchange code for token

```bash
curl -X POST http://localhost:5001/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "docsly-openai-client:docsly-openai-secret" \
  -d "grant_type=authorization_code" \
  -d "code=<CODE_FROM_STEP_2>" \
  -d "redirect_uri=http://localhost:3000/callback"
```

### 4) Call MCP with OAuth token

```bash
curl -X POST http://localhost:5001/mcp \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```
