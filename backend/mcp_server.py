import json
import os
import time
import base64
import secrets
import hashlib
import fnmatch
import uuid
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode
from flask import Flask, request, jsonify, redirect, make_response, send_file
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from io import BytesIO

from app import create_app
from app.extensions import db
from app.models import Document, Component, Theme, OAuthClient, OAuthAuthCode, OAuthAccessToken, OAuthRefreshToken
from app.services.renderer import render_document, render_component_template_preview_details
from app.services.pdf_engine import render_pdf_from_html
from app.services.component_registry import rebuild_component_registry
from app.services.validator import validate_component_schema, validate_props

# Create Flask app for HTTP-based MCP server
mcp_app = Flask(__name__)
CORS(mcp_app)
# Respect x-forwarded-* headers from ngrok/reverse proxies so generated URLs use https.
mcp_app.wsgi_app = ProxyFix(mcp_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Get MCP API key from environment
MCP_API_KEY = os.getenv("MCP_API_KEY", "mcp-secret-key-change-in-production")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "docsly-openai-client")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "docsly-openai-secret")
OAUTH_DEFAULT_SCOPE = os.getenv("OAUTH_DEFAULT_SCOPE", "mcp:tools")
OAUTH_CODE_TTL_SECONDS = int(os.getenv("OAUTH_CODE_TTL_SECONDS", "300"))
# Default to 90 days for access tokens
OAUTH_ACCESS_TOKEN_TTL_SECONDS = int(os.getenv("OAUTH_ACCESS_TOKEN_TTL_SECONDS", "7776000"))
# Refresh tokens last 1 year
OAUTH_REFRESH_TOKEN_TTL_SECONDS = int(os.getenv("OAUTH_REFRESH_TOKEN_TTL_SECONDS", "31536000"))
OAUTH_ALLOW_PUBLIC_CLIENT = os.getenv("OAUTH_ALLOW_PUBLIC_CLIENT", "true").lower() in {"1", "true", "yes"}
OAUTH_REDIRECT_ALLOWLIST = [
    value.strip()
    for value in os.getenv("OAUTH_REDIRECT_ALLOWLIST", "").split(",")
    if value.strip()
]
OAUTH_ALLOW_ANY_REDIRECT = os.getenv("OAUTH_ALLOW_ANY_REDIRECT", "false").lower() in {"1", "true", "yes"}

# Reference to main app for database access
main_app = create_app()

# OAuth state is now persisted in SQLite via OAuthAuthCode and OAuthAccessToken models.

# Temporary file storage for downloadable PDFs (in-memory with expiration)
PDF_DOWNLOAD_TTL_SECONDS = int(os.getenv("PDF_DOWNLOAD_TTL_SECONDS", "300"))  # 5 minutes
PDF_DOWNLOADS: dict[str, dict] = {}  # {download_id: {"pdf_bytes": bytes, "filename": str, "expires_at": int}}


def _store_pdf_for_download(pdf_bytes: bytes, filename: str) -> str:
    """Store PDF temporarily and return a download ID."""
    _prune_pdf_downloads()
    download_id = uuid.uuid4().hex
    PDF_DOWNLOADS[download_id] = {
        "pdf_bytes": pdf_bytes,
        "filename": filename,
        "expires_at": int(time.time()) + PDF_DOWNLOAD_TTL_SECONDS,
    }
    return download_id


def _prune_pdf_downloads() -> None:
    """Remove expired PDF downloads."""
    now = int(time.time())
    expired = [did for did, data in PDF_DOWNLOADS.items() if data.get("expires_at", 0) <= now]
    for did in expired:
        PDF_DOWNLOADS.pop(did, None)


def _extract_api_key() -> str:
    auth = request.headers.get("Authorization", "")
    bearer = auth.replace("Bearer ", "").strip() if auth else ""
    return request.headers.get("X-API-Key", "").strip() or bearer


def _extract_bearer_token() -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return ""
    return auth[7:].strip()


def _prune_oauth_state() -> None:
    """Remove expired auth codes, access tokens, and refresh tokens from the database."""
    now = int(time.time())
    OAuthAuthCode.query.filter(OAuthAuthCode.expires_at <= now).delete()
    OAuthAccessToken.query.filter(OAuthAccessToken.expires_at <= now).delete()
    OAuthRefreshToken.query.filter(OAuthRefreshToken.expires_at <= now).delete()
    db.session.commit()


def _is_redirect_uri_allowed(uri: str) -> bool:
    if not uri:
        return False
    if OAUTH_ALLOW_ANY_REDIRECT:
        return True
    if not OAUTH_REDIRECT_ALLOWLIST:
        # Local test default: allow localhost callbacks if allowlist is not set.
        return uri.startswith("http://localhost:") or uri.startswith("https://localhost:")
    for allowed in OAUTH_REDIRECT_ALLOWLIST:
        if "*" in allowed:
            if fnmatch.fnmatch(uri, allowed):
                return True
            continue
        if uri == allowed:
            return True
    return False


def _oauth_error_redirect(redirect_uri: str, state: str | None, error: str, description: str) -> str:
    params = {"error": error, "error_description": description}
    if state:
        params["state"] = state
    delimiter = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{delimiter}{urlencode(params)}"


def _parse_client_auth() -> tuple[str, str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
            client_id, client_secret = decoded.split(":", 1)
            return client_id, client_secret
        except Exception:
            return "", ""
    payload = request.get_json(silent=True) if request.is_json else {}
    return (
        request.form.get("client_id", "") or (payload.get("client_id", "") if isinstance(payload, dict) else ""),
        request.form.get("client_secret", "") or (payload.get("client_secret", "") if isinstance(payload, dict) else ""),
    )


def _issue_auth_code(client_id: str, redirect_uri: str, scope: str, code_challenge: str | None = None, code_challenge_method: str | None = None) -> str:
    """Create and persist an OAuth authorization code."""
    code = secrets.token_urlsafe(32)
    auth_code = OAuthAuthCode(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=int(time.time()) + OAUTH_CODE_TTL_SECONDS,
    )
    db.session.add(auth_code)
    db.session.commit()
    return code


def _verify_pkce(auth_code: OAuthAuthCode, code_verifier: str) -> bool:
    """Verify PKCE code challenge against verifier."""
    challenge = auth_code.code_challenge
    if not challenge:
        return True
    method = str(auth_code.code_challenge_method or "plain").upper()
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        computed = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
        return secrets.compare_digest(computed, str(challenge))
    return secrets.compare_digest(code_verifier, str(challenge))


def _issue_refresh_token(client_id: str, scope: str) -> tuple[str, int]:
    """Create and persist an OAuth refresh token."""
    token = secrets.token_urlsafe(48)
    expires_at = int(time.time()) + OAUTH_REFRESH_TOKEN_TTL_SECONDS
    refresh_token = OAuthRefreshToken(
        token=token,
        client_id=client_id,
        scope=scope,
        expires_at=expires_at,
    )
    db.session.add(refresh_token)
    db.session.commit()
    return token, expires_at


def _issue_access_token(client_id: str, scope: str, include_refresh: bool = True) -> dict:
    """Create and persist OAuth access token (and optionally refresh token)."""
    access_token = secrets.token_urlsafe(40)
    access_expires_at = int(time.time()) + OAUTH_ACCESS_TOKEN_TTL_SECONDS

    refresh_token_str = None
    if include_refresh:
        refresh_token_str, _ = _issue_refresh_token(client_id, scope)

    access_token_obj = OAuthAccessToken(
        token=access_token,
        client_id=client_id,
        scope=scope,
        expires_at=access_expires_at,
        refresh_token=refresh_token_str,
    )
    db.session.add(access_token_obj)
    db.session.commit()

    return {
        "access_token": access_token,
        "expires_at": access_expires_at,
        "refresh_token": refresh_token_str,
    }


def _get_current_user_id() -> int | None:
    """Get the user ID from the current request's OAuth token."""
    token = _extract_api_key()
    if not token:
        return None
    if token == MCP_API_KEY:
        return None  # Global API key has no user association
    now = int(time.time())
    access_token = OAuthAccessToken.query.filter(
        OAuthAccessToken.token == token,
        OAuthAccessToken.expires_at > now
    ).first()
    if not access_token:
        return None
    # Look up the OAuth client to get the user_id
    oauth_client = OAuthClient.query.filter_by(client_id=access_token.client_id).first()
    if oauth_client:
        return oauth_client.user_id
    return None


def _is_authorized() -> bool:
    """Check if the request has valid API key or OAuth access token."""
    token = _extract_api_key()
    if token == MCP_API_KEY:
        return True
    now = int(time.time())
    access_token = OAuthAccessToken.query.filter(
        OAuthAccessToken.token == token,
        OAuthAccessToken.expires_at > now
    ).first()
    return access_token is not None


def _mcp_ok(request_id, result: dict) -> tuple[dict, int]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}, 200


def _mcp_error(request_id, code: int, message: str, status: int = 200) -> tuple[dict, int]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }, status


def _oauth_challenge_header() -> str:
    base_url = request.url_root.rstrip("/")
    return (
        'Bearer realm="docsly-mcp", '
        f'authorization_uri="{base_url}/oauth/authorize", '
        f'resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
    )


def _json_unauthorized(payload: dict, status: int = 401):
    response = make_response(jsonify(payload), status)
    response.headers["WWW-Authenticate"] = _oauth_challenge_header()
    return response


def _latest_component_by_name(name: str, include_inactive: bool = False) -> Component | None:
    query = Component.query.filter(Component.name == name)
    if not include_inactive:
        query = query.filter(Component.is_active == True)
    return query.order_by(Component.version.desc()).first()


def _specific_component(name: str, version: int | None = None, include_inactive: bool = False, user_id: int | None = None) -> Component | None:
    query = Component.query.filter(Component.name == name)
    if version is not None:
        query = query.filter(Component.version == version)
    if not include_inactive:
        query = query.filter(Component.is_active == True)
    # If user_id provided, only show builtins + user's own components
    if user_id is not None:
        query = query.filter(
            db.or_(Component.is_builtin == True, Component.user_id == user_id)
        )
    return query.order_by(Component.version.desc()).first()


def _to_component_fence(name: str, props: dict | None = None, version: int | None = None, inner_markdown: str = "") -> str:
    props = props or {}
    header = f":::{name}"
    if version is not None:
        header += f" v={version}"

    lines = [header]
    for key, value in props.items():
        if isinstance(value, str):
            lines.append(f"{key}={json.dumps(value)}")
        else:
            lines.append(f"{key}={json.dumps(value)}")
    if inner_markdown.strip():
        lines.append(inner_markdown.strip())
    lines.append(":::")
    return "\n".join(lines)


def _compose_markdown_from_components(
    intro_markdown: str,
    components: list[dict],
    outro_markdown: str,
) -> str:
    parts: list[str] = []
    if intro_markdown.strip():
        parts.append(intro_markdown.strip())

    for comp in components:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        props = comp.get("props")
        props_dict = props if isinstance(props, dict) else {}
        version = comp.get("version")
        version_int = version if isinstance(version, int) else None
        inner_markdown = comp.get("inner_markdown")
        inner = inner_markdown if isinstance(inner_markdown, str) else ""
        parts.append(
            _to_component_fence(
                name=name.strip(),
                props=props_dict,
                version=version_int,
                inner_markdown=inner,
            )
        )

    if outro_markdown.strip():
        parts.append(outro_markdown.strip())

    return "\n\n".join(part for part in parts if part.strip())


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        with main_app.app_context():
            if not _is_authorized():
                return _json_unauthorized({"error": "Unauthorized", "message": "Invalid or missing bearer/API key token"})
        return f(*args, **kwargs)
    return decorated


# Define all available tools
TOOLS = [
    {
        "name": "list_documents",
        "description": "List all documents",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_document",
        "description": "Get a document by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "Document ID"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "create_document",
        "description": "Create a new document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "object", "description": "Document content ({version, theme_id, markdown})"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "update_document",
        "description": "Update a document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "Document ID"},
                "title": {"type": "string", "description": "New title"},
                "content": {"type": "object", "description": "New content ({version, theme_id, markdown})"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "delete_document",
        "description": "Delete a document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "Document ID"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "list_components",
        "description": "List components (latest by default, or full version history)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_inactive": {"type": "boolean", "description": "Include inactive versions", "default": False},
                "include_versions": {"type": "boolean", "description": "Return all matching versions instead of latest per name", "default": False}
            },
            "required": []
        }
    },
    {
        "name": "get_component",
        "description": "Get component details by name (and optional version)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "version": {"type": "integer", "description": "Optional component version"},
                "include_inactive": {"type": "boolean", "description": "Include inactive versions", "default": False}
            },
            "required": ["name"]
        }
    },
    {
        "name": "create_component",
        "description": "Create or version-bump a component definition",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "schema": {"type": "object", "description": "JSON Schema for props validation"},
                "template": {"type": "string", "description": "Markdown template (supports {{prop}} placeholders)"},
                "style_contract": {"type": "object", "description": "Allowed slots/variants contract"},
                "default_styles": {"type": "object", "description": "Component default styles"},
                "is_builtin": {"type": "boolean", "description": "Mark as builtin", "default": False}
            },
            "required": ["name", "schema", "template"]
        }
    },
    {
        "name": "preview_component_template",
        "description": "Design-time preview for a component template with diagnostics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "template": {"type": "string", "description": "Markdown/Jinja template"},
                "props": {"type": "object", "description": "Sample props"},
                "style_contract": {"type": "object", "description": "Style contract"},
                "default_styles": {"type": "object", "description": "Default component styles"},
                "theme": {"type": "object", "description": "Optional theme override object"}
            },
            "required": ["name", "template"]
        }
    },
    {
        "name": "render_component_instance",
        "description": "Render one component instance from name+props and return markdown snippet + HTML",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "props": {"type": "object", "description": "Component props"},
                "version": {"type": "integer", "description": "Optional version"},
                "inner_markdown": {"type": "string", "description": "Optional slotted markdown content"},
                "theme_id": {"type": "integer", "description": "Optional theme id for render"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "compose_document_from_components",
        "description": "Build markdown document content from component instances and optionally save as document",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "theme_id": {"type": "integer", "description": "Optional theme id"},
                "intro_markdown": {"type": "string", "description": "Top markdown content"},
                "outro_markdown": {"type": "string", "description": "Bottom markdown content"},
                "components": {
                    "type": "array",
                    "description": "Ordered component instances",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "version": {"type": "integer"},
                            "props": {"type": "object"},
                            "inner_markdown": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                },
                "save": {"type": "boolean", "description": "Persist as a new document", "default": False}
            },
            "required": ["title", "components"]
        }
    },
    {
        "name": "list_themes",
        "description": "List all available themes",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_theme",
        "description": "Get theme details by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theme_id": {"type": "integer", "description": "Theme ID"}
            },
            "required": ["theme_id"]
        }
    },
    {
        "name": "create_theme",
        "description": "Create a new theme",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Theme name"},
                "variables": {"type": "object", "description": "CSS variables (colors, fonts, etc.)"}
            },
            "required": ["name", "variables"]
        }
    },
    {
        "name": "render_document_to_html",
        "description": "Render a document to HTML",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "Document ID"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "render_document_to_pdf",
        "description": "Render a document to PDF (returns base64)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "integer", "description": "Document ID"}
            },
            "required": ["document_id"]
        }
    },
    {
        "name": "preview_document_to_pdf",
        "description": "Render unsaved document content to PDF (returns base64)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Optional filename title"},
                "content": {"type": "object", "description": "Document content object"},
            },
            "required": ["content"]
        }
    },
    {
        "name": "preview_block",
        "description": "Preview a single block without saving",
        "inputSchema": {
            "type": "object",
            "properties": {
                "block": {"type": "object", "description": "Block object with type and content/props"}
            },
            "required": ["block"]
        }
    },
]


@mcp_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "docsly-mcp"})


@mcp_app.route("/download/<download_id>", methods=["GET"])
def download_pdf(download_id: str):
    """Download a generated PDF by its temporary ID."""
    _prune_pdf_downloads()
    data = PDF_DOWNLOADS.get(download_id)
    if not data:
        return jsonify({"error": "Download not found or expired"}), 404
    if data.get("expires_at", 0) <= int(time.time()):
        PDF_DOWNLOADS.pop(download_id, None)
        return jsonify({"error": "Download expired"}), 410

    pdf_bytes = data["pdf_bytes"]
    filename = data["filename"]

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@mcp_app.route("/.well-known/oauth-authorization-server", methods=["GET"])
def oauth_authorization_server_metadata():
    base_url = request.url_root.rstrip("/")
    return jsonify(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "scopes_supported": [OAUTH_DEFAULT_SCOPE],
        }
    )


@mcp_app.route("/.well-known/oauth-protected-resource", methods=["GET"])
def oauth_protected_resource_metadata():
    """
    RFC-compatible protected resource metadata for OAuth resource server discovery.
    Some clients probe this before establishing MCP.
    """
    base_url = request.url_root.rstrip("/")
    return jsonify(
        {
            "resource": base_url,
            "authorization_servers": [base_url],
            "bearer_methods_supported": ["header"],
            "scopes_supported": [OAUTH_DEFAULT_SCOPE],
        }
    )


@mcp_app.route("/.well-known/openid-configuration", methods=["GET"])
def openid_configuration():
    base_url = request.url_root.rstrip("/")
    return jsonify(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "scopes_supported": [OAUTH_DEFAULT_SCOPE],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["none"],
        }
    )


def _validate_oauth_client(client_id: str) -> OAuthClient | None:
    """Validate an OAuth client ID and return the client if valid."""
    if not client_id:
        return None
    # Check for user-created OAuth client first
    oauth_client = OAuthClient.query.filter_by(client_id=client_id, is_active=True).first()
    if oauth_client:
        return oauth_client
    return None


def _is_global_client(client_id: str) -> bool:
    """Check if the client_id matches the global OAuth client."""
    return client_id == OAUTH_CLIENT_ID and bool(OAUTH_CLIENT_SECRET)


@mcp_app.route("/oauth/authorize", methods=["GET"])
def oauth_authorize():
    with main_app.app_context():
        _prune_oauth_state()
        response_type = request.args.get("response_type", "")
        client_id = request.args.get("client_id", "")
        redirect_uri = request.args.get("redirect_uri", "")
        state = request.args.get("state")
        scope = request.args.get("scope", OAUTH_DEFAULT_SCOPE)
        code_challenge = request.args.get("code_challenge")
        code_challenge_method = request.args.get("code_challenge_method", "plain")

        if response_type != "code":
            if _is_redirect_uri_allowed(redirect_uri):
                return redirect(_oauth_error_redirect(redirect_uri, state, "unsupported_response_type", "Only response_type=code is supported"))
            return jsonify({"error": "unsupported_response_type", "error_description": "Only response_type=code is supported"}), 400

        # Check for user-specific OAuth client or global client
        oauth_client = _validate_oauth_client(client_id)
        is_global = _is_global_client(client_id)

        if not oauth_client and not is_global:
            if _is_redirect_uri_allowed(redirect_uri):
                return redirect(_oauth_error_redirect(redirect_uri, state, "unauthorized_client", "Invalid client_id"))
            return jsonify({"error": "unauthorized_client", "error_description": "Invalid client_id"}), 401

        if not _is_redirect_uri_allowed(redirect_uri):
            return jsonify({"error": "invalid_request", "error_description": "redirect_uri is not allowed"}), 400

        code = _issue_auth_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope or OAUTH_DEFAULT_SCOPE,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method if code_challenge else None,
        )
        params = {"code": code}
        if state:
            params["state"] = state
        delimiter = "&" if "?" in redirect_uri else "?"
        return redirect(f"{redirect_uri}{delimiter}{urlencode(params)}")


def _verify_client_secret(client_id: str, client_secret: str) -> bool:
    """Verify client secret for user-specific or global OAuth clients."""
    # Check user-specific OAuth client first
    oauth_client = OAuthClient.query.filter_by(client_id=client_id, is_active=True).first()
    if oauth_client:
        if oauth_client.verify_secret(client_secret):
            # Update last_used_at
            oauth_client.last_used_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    # Fall back to global client
    if client_id == OAUTH_CLIENT_ID:
        return client_secret == OAUTH_CLIENT_SECRET

    return False


@mcp_app.route("/oauth/token", methods=["POST"])
def oauth_token():
    with main_app.app_context():
        _prune_oauth_state()
        client_id, client_secret = _parse_client_auth()
        payload = request.get_json(silent=True) or {}
        form_client_id = request.form.get("client_id") or (payload.get("client_id") if isinstance(payload, dict) else "")
        form_client_secret = request.form.get("client_secret") or (payload.get("client_secret") if isinstance(payload, dict) else "")
        effective_client_id = (client_id or form_client_id or "").strip()
        effective_client_secret = (client_secret or form_client_secret or "").strip()

        grant_type = request.form.get("grant_type") or payload.get("grant_type")

        # Handle refresh_token grant
        if grant_type == "refresh_token":
            refresh_token = request.form.get("refresh_token") or payload.get("refresh_token")
            if not refresh_token:
                return jsonify({"error": "invalid_request", "error_description": "refresh_token is required"}), 400

            refresh_obj = OAuthRefreshToken.query.filter(OAuthRefreshToken.token == refresh_token).first()
            if not refresh_obj:
                return jsonify({"error": "invalid_grant", "error_description": "Invalid refresh token"}), 400
            if refresh_obj.expires_at <= int(time.time()):
                db.session.delete(refresh_obj)
                db.session.commit()
                return jsonify({"error": "invalid_grant", "error_description": "Refresh token expired"}), 400

            # Issue new access token (reuse same refresh token)
            scope = refresh_obj.scope
            token_data = _issue_access_token(client_id=refresh_obj.client_id, scope=scope, include_refresh=False)

            # Link new access token to existing refresh token
            access_token_obj = OAuthAccessToken.query.filter(OAuthAccessToken.token == token_data["access_token"]).first()
            if access_token_obj:
                access_token_obj.refresh_token = refresh_token
                db.session.commit()

            expires_in = max(0, token_data["expires_at"] - int(time.time()))
            return jsonify({
                "access_token": token_data["access_token"],
                "token_type": "Bearer",
                "expires_in": expires_in,
                "refresh_token": refresh_token,
                "scope": scope,
            })

        # Handle client_credentials grant (for MCP clients like Claude Code)
        if grant_type == "client_credentials":
            if not effective_client_id:
                return jsonify({"error": "invalid_request", "error_description": "client_id is required"}), 400

            # Check for user-specific OAuth client
            oauth_client = _validate_oauth_client(effective_client_id)
            if not oauth_client:
                return jsonify({"error": "invalid_client", "error_description": "Unknown client_id"}), 401

            # Verify client secret
            if not effective_client_secret or not oauth_client.verify_secret(effective_client_secret):
                return jsonify({"error": "invalid_client", "error_description": "Invalid client_secret"}), 401

            # Update last_used_at
            oauth_client.last_used_at = datetime.utcnow()
            db.session.commit()

            # Issue access token
            scope = oauth_client.scopes or OAUTH_DEFAULT_SCOPE
            token_data = _issue_access_token(client_id=effective_client_id, scope=scope, include_refresh=True)
            expires_in = max(0, token_data["expires_at"] - int(time.time()))

            response_data = {
                "access_token": token_data["access_token"],
                "token_type": "Bearer",
                "expires_in": expires_in,
                "scope": scope,
            }
            if token_data.get("refresh_token"):
                response_data["refresh_token"] = token_data["refresh_token"]

            return jsonify(response_data)

        # Handle authorization_code grant
        if grant_type != "authorization_code":
            return jsonify({"error": "unsupported_grant_type"}), 400

        code = request.form.get("code") or payload.get("code")
        redirect_uri = request.form.get("redirect_uri") or payload.get("redirect_uri")
        code_verifier = request.form.get("code_verifier") or payload.get("code_verifier") or ""
        if not isinstance(code, str) or not code:
            return jsonify({"error": "invalid_request", "error_description": "code is required"}), 400
        if not isinstance(redirect_uri, str) or not redirect_uri:
            return jsonify({"error": "invalid_request", "error_description": "redirect_uri is required"}), 400

        auth_code = OAuthAuthCode.query.filter(OAuthAuthCode.code == code).first()
        if not auth_code:
            return jsonify({"error": "invalid_grant"}), 400

        expected_client_id = auth_code.client_id or ""
        if not effective_client_id:
            if not OAUTH_ALLOW_PUBLIC_CLIENT:
                return jsonify({"error": "invalid_client"}), 401
            effective_client_id = expected_client_id

        if effective_client_id != expected_client_id:
            return jsonify({"error": "invalid_client"}), 401

        # Check for user-specific OAuth client
        oauth_client = _validate_oauth_client(effective_client_id)
        is_global = _is_global_client(effective_client_id)

        # Verify client secret for confidential clients
        if not OAUTH_ALLOW_PUBLIC_CLIENT:
            if oauth_client:
                # User-specific client - verify against stored hash
                if not effective_client_secret or not oauth_client.verify_secret(effective_client_secret):
                    return jsonify({"error": "invalid_client"}), 401
                # Update last_used_at
                oauth_client.last_used_at = datetime.utcnow()
            elif is_global:
                # Global client - verify against env var
                if not effective_client_secret or effective_client_secret != OAUTH_CLIENT_SECRET:
                    return jsonify({"error": "invalid_client"}), 401
            else:
                return jsonify({"error": "invalid_client"}), 401

        if auth_code.redirect_uri != redirect_uri:
            return jsonify({"error": "invalid_grant"}), 400
        if auth_code.expires_at <= int(time.time()):
            return jsonify({"error": "invalid_grant"}), 400
        if not _verify_pkce(auth_code, str(code_verifier)):
            return jsonify({"error": "invalid_grant", "error_description": "PKCE verification failed"}), 400

        # Authorization code is one-time use - delete it.
        scope = auth_code.scope or OAUTH_DEFAULT_SCOPE
        db.session.delete(auth_code)
        db.session.commit()

        token_data = _issue_access_token(client_id=effective_client_id, scope=scope, include_refresh=True)
        expires_in = max(0, token_data["expires_at"] - int(time.time()))

        response_data = {
            "access_token": token_data["access_token"],
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": scope,
        }
        if token_data.get("refresh_token"):
            response_data["refresh_token"] = token_data["refresh_token"]

        return jsonify(response_data)


@mcp_app.route("/.well-known/mcp", methods=["GET"])
def mcp_well_known():
    """Basic MCP discovery metadata for remote clients."""
    base_url = request.url_root.rstrip("/")
    return jsonify(
        {
            "name": "docsly-mcp",
            "version": "1.0.0",
            "transport": "http",
            "mcp_endpoint": f"{base_url}/mcp",
            "authentication": {
                "type": "oauth2_or_bearer_api_key",
                "header": "Authorization",
                "authorization_server_metadata": f"{base_url}/.well-known/oauth-authorization-server",
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
            },
        }
    )


@mcp_app.route("/tools", methods=["GET"])
@require_api_key
def list_tools():
    """List all available tools."""
    return jsonify({"tools": TOOLS})


@mcp_app.route("/tools/<tool_name>", methods=["POST"])
@require_api_key
def call_tool(tool_name):
    """Call a specific tool."""
    arguments = request.get_json(silent=True) or {}

    with main_app.app_context():
        user_id = _get_current_user_id()
        result = execute_tool(tool_name, arguments, user_id=user_id)
        return jsonify(result)


@mcp_app.route("/mcp", methods=["POST"])
def mcp_rpc():
    """
    MCP JSON-RPC endpoint compatible with OpenAI/ChatGPT MCP clients.
    Supports: initialize, tools/list, tools/call, ping.
    """
    with main_app.app_context():
        if not _is_authorized():
            payload = request.get_json(silent=True) or {}
            request_id = payload.get("id")
            body, status = _mcp_error(request_id, -32001, "Unauthorized", status=401)
            response = make_response(jsonify(body), status)
            response.headers["WWW-Authenticate"] = _oauth_challenge_header()
            return response

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        body, status = _mcp_error(None, -32700, "Invalid JSON payload")
        return jsonify(body), status

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    if method is None or not isinstance(method, str):
        body, status = _mcp_error(request_id, -32600, "Invalid Request")
        return jsonify(body), status

    if request_id is None:
        return ("", 204)

    if method == "initialize":
        body, status = _mcp_ok(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "docsly-mcp", "version": "1.0.0"},
            },
        )
        return jsonify(body), status

    if method == "ping":
        body, status = _mcp_ok(request_id, {})
        return jsonify(body), status

    if method == "tools/list":
        body, status = _mcp_ok(request_id, {"tools": TOOLS})
        return jsonify(body), status

    if method == "tools/call":
        if not isinstance(params, dict):
            body, status = _mcp_error(request_id, -32602, "params must be an object")
            return jsonify(body), status
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(tool_name, str) or not tool_name:
            body, status = _mcp_error(request_id, -32602, "Tool name is required")
            return jsonify(body), status
        if not isinstance(arguments, dict):
            body, status = _mcp_error(request_id, -32602, "Tool arguments must be an object")
            return jsonify(body), status

        with main_app.app_context():
            user_id = _get_current_user_id()
            tool_result = execute_tool(tool_name, arguments, user_id=user_id)

        if not tool_result.get("success", False):
            result = {
                "content": [
                    {"type": "text", "text": tool_result.get("error", "Tool call failed")}
                ],
                "isError": True,
            }
            body, status = _mcp_ok(request_id, result)
            return jsonify(body), status

        data = tool_result.get("data")
        # MCP protocol requires structuredContent to be an object, not an array
        if isinstance(data, list):
            structured = {"items": data, "count": len(data)}
        elif isinstance(data, dict):
            structured = data
        else:
            structured = {"value": data}
        result = {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
            "structuredContent": structured,
            "isError": False,
        }
        body, status = _mcp_ok(request_id, result)
        return jsonify(body), status

    body, status = _mcp_error(request_id, -32601, f"Method not found: {method}")
    return jsonify(body), status


@mcp_app.route("/", methods=["POST"])
def mcp_rpc_root_alias():
    """Compatibility alias: some MCP clients post JSON-RPC to root path."""
    return mcp_rpc()


@mcp_app.route("/", methods=["GET"])
def root_info_alias():
    """Compatibility alias for clients probing root metadata."""
    return mcp_info()


@mcp_app.route("/mcp", methods=["GET"])
def mcp_info():
    """Human-readable MCP endpoint metadata."""
    base_url = request.url_root.rstrip("/")
    return jsonify(
        {
            "name": "docsly-mcp",
            "version": "1.0.0",
            "endpoint": f"{base_url}/mcp",
            "auth": {
                "type": "oauth2_or_bearer_api_key",
                "headers": ["Authorization: Bearer <MCP_API_KEY>", "X-API-Key: <MCP_API_KEY>"],
                "oauth": {
                    "authorization_endpoint": f"{base_url}/oauth/authorize",
                    "token_endpoint": f"{base_url}/oauth/token",
                    "client_id": OAUTH_CLIENT_ID,
                },
            },
            "supported_methods": ["initialize", "tools/list", "tools/call", "ping"],
        }
    )


def execute_tool(name: str, arguments: dict, user_id: int | None = None) -> dict:
    """Execute a tool and return the result.

    Args:
        name: The tool name to execute
        arguments: Tool arguments
        user_id: The authenticated user's ID (None for global API key)
    """

    if name == "list_documents":
        query = Document.query
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        docs = query.all()
        result = [{"id": d.id, "title": d.title, "updated_at": d.updated_at.isoformat()} for d in docs]
        return {"success": True, "data": result}

    elif name == "get_document":
        query = Document.query.filter_by(id=arguments.get("document_id"))
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        doc = query.first()
        if not doc:
            return {"success": False, "error": "Document not found"}
        return {"success": True, "data": doc.to_dict()}

    elif name == "create_document":
        default_content = {"version": "2.0", "theme_id": None, "markdown": ""}
        doc = Document(
            title=arguments["title"],
            content=arguments.get("content") or default_content,
            doc_metadata={},
            user_id=user_id
        )
        db.session.add(doc)
        db.session.commit()
        return {"success": True, "data": doc.to_dict()}

    elif name == "update_document":
        query = Document.query.filter_by(id=arguments.get("document_id"))
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        doc = query.first()
        if not doc:
            return {"success": False, "error": "Document not found"}
        if arguments.get("title"):
            doc.title = arguments["title"]
        if arguments.get("content"):
            doc.content = arguments["content"]
        db.session.commit()
        return {"success": True, "data": doc.to_dict()}

    elif name == "delete_document":
        query = Document.query.filter_by(id=arguments.get("document_id"))
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        doc = query.first()
        if not doc:
            return {"success": False, "error": "Document not found"}
        db.session.delete(doc)
        db.session.commit()
        return {"success": True, "data": {"deleted": True}}

    elif name == "list_components":
        include_inactive = bool(arguments.get("include_inactive", False))
        include_versions = bool(arguments.get("include_versions", False))
        query = Component.query
        if not include_inactive:
            query = query.filter(Component.is_active == True)
        # Show builtins + user's own components
        if user_id is not None:
            query = query.filter(
                db.or_(Component.is_builtin == True, Component.user_id == user_id)
            )

        if include_versions:
            comps = query.order_by(Component.name.asc(), Component.version.desc()).all()
        else:
            by_name: dict[str, Component] = {}
            for comp in query.order_by(Component.name.asc(), Component.version.desc()).all():
                by_name.setdefault(comp.name, comp)
            comps = list(by_name.values())

        result = [
            {
                "name": c.name,
                "version": c.version,
                "is_builtin": c.is_builtin,
                "is_active": c.is_active,
                "schema": c.schema,
                "style_contract": c.style_contract,
                "default_styles": c.default_styles,
            }
            for c in comps
        ]
        return {"success": True, "data": result}

    elif name == "get_component":
        comp_name = arguments.get("name")
        if not isinstance(comp_name, str) or not comp_name.strip():
            return {"success": False, "error": "name is required"}
        version = arguments.get("version")
        if version is not None and not isinstance(version, int):
            return {"success": False, "error": "version must be an integer"}
        include_inactive = bool(arguments.get("include_inactive", False))

        # Build query for builtins + user's own components
        query = Component.query.filter(Component.name == comp_name.strip())
        if version is not None:
            query = query.filter(Component.version == version)
        if not include_inactive:
            query = query.filter(Component.is_active == True)
        if user_id is not None:
            query = query.filter(
                db.or_(Component.is_builtin == True, Component.user_id == user_id)
            )
        comp = query.order_by(Component.version.desc()).first()

        if not comp:
            return {"success": False, "error": "Component not found"}
        return {"success": True, "data": comp.to_dict()}

    elif name == "create_component":
        schema = arguments.get("schema")
        if not isinstance(schema, dict):
            return {"success": False, "error": "schema must be an object"}
        schema_error = validate_component_schema(schema)
        if schema_error:
            return {"success": False, "error": schema_error}

        component_name = arguments.get("name")
        template = arguments.get("template")
        if not isinstance(component_name, str) or not component_name.strip():
            return {"success": False, "error": "name is required"}
        if not isinstance(template, str) or not template.strip():
            return {"success": False, "error": "template is required"}

        style_contract = arguments.get("style_contract") or {}
        default_styles = arguments.get("default_styles") or {}
        if not isinstance(style_contract, dict):
            return {"success": False, "error": "style_contract must be an object"}
        if not isinstance(default_styles, dict):
            return {"success": False, "error": "default_styles must be an object"}

        # Find latest version for this user's component (not builtins)
        latest_query = Component.query.filter(
            Component.name == component_name.strip(),
            Component.is_builtin == False
        )
        if user_id is not None:
            latest_query = latest_query.filter(Component.user_id == user_id)
        latest = latest_query.order_by(Component.version.desc()).first()

        next_version = 1
        if latest:
            next_version = latest.version + 1
            if latest.is_active:
                latest.is_active = False
                db.session.add(latest)

        comp = Component(
            name=component_name.strip(),
            schema=schema,
            template=template,
            style_contract=style_contract,
            default_styles=default_styles,
            version=next_version,
            is_builtin=bool(arguments.get("is_builtin", False)),
            is_active=True,
            user_id=user_id
        )
        db.session.add(comp)
        db.session.commit()
        rebuild_component_registry()
        return {"success": True, "data": comp.to_dict()}

    elif name == "preview_component_template":
        component_name = arguments.get("name")
        template = arguments.get("template")
        if not isinstance(component_name, str) or not component_name.strip():
            return {"success": False, "error": "name is required"}
        if not isinstance(template, str):
            return {"success": False, "error": "template must be a string"}
        props = arguments.get("props") or {}
        style_contract = arguments.get("style_contract") or {}
        default_styles = arguments.get("default_styles") or {}
        theme = arguments.get("theme") or {}
        if not isinstance(props, dict):
            return {"success": False, "error": "props must be an object"}
        if not isinstance(style_contract, dict):
            return {"success": False, "error": "style_contract must be an object"}
        if not isinstance(default_styles, dict):
            return {"success": False, "error": "default_styles must be an object"}
        if not isinstance(theme, dict):
            return {"success": False, "error": "theme must be an object"}

        preview = render_component_template_preview_details(
            template=template,
            props=props,
            component_name=component_name.strip(),
            style_contract=style_contract,
            default_styles=default_styles,
            theme=theme,
        )
        return {"success": True, "data": preview}

    elif name == "render_component_instance":
        component_name = arguments.get("name")
        if not isinstance(component_name, str) or not component_name.strip():
            return {"success": False, "error": "name is required"}
        version = arguments.get("version")
        if version is not None and not isinstance(version, int):
            return {"success": False, "error": "version must be an integer"}
        props = arguments.get("props") or {}
        if not isinstance(props, dict):
            return {"success": False, "error": "props must be an object"}
        inner_markdown = arguments.get("inner_markdown") or ""
        if not isinstance(inner_markdown, str):
            return {"success": False, "error": "inner_markdown must be a string"}
        theme_id = arguments.get("theme_id")
        if theme_id is not None and not isinstance(theme_id, int):
            return {"success": False, "error": "theme_id must be an integer"}

        comp = _specific_component(component_name.strip(), version, user_id=user_id)
        if not comp:
            return {"success": False, "error": "Component not found"}
        validation_error = validate_props(props, comp.schema or {})
        if validation_error:
            return {"success": False, "error": f"Props validation failed: {validation_error}"}

        snippet = _to_component_fence(
            name=comp.name,
            props=props,
            version=comp.version,
            inner_markdown=inner_markdown,
        )
        content = {"version": "2.0", "theme_id": theme_id, "markdown": snippet}
        html = render_document(content)
        return {
            "success": True,
            "data": {
                "component": {"name": comp.name, "version": comp.version},
                "markdown_snippet": snippet,
                "html": html,
            }
        }

    elif name == "compose_document_from_components":
        title = arguments.get("title")
        components = arguments.get("components")
        theme_id = arguments.get("theme_id")
        intro_markdown = arguments.get("intro_markdown") or ""
        outro_markdown = arguments.get("outro_markdown") or ""
        save = bool(arguments.get("save", False))

        if not isinstance(title, str) or not title.strip():
            return {"success": False, "error": "title is required"}
        if not isinstance(components, list):
            return {"success": False, "error": "components must be an array"}
        if theme_id is not None and not isinstance(theme_id, int):
            return {"success": False, "error": "theme_id must be an integer"}
        if not isinstance(intro_markdown, str) or not isinstance(outro_markdown, str):
            return {"success": False, "error": "intro_markdown/outro_markdown must be strings"}

        validated_components = []
        for idx, comp_ref in enumerate(components):
            if not isinstance(comp_ref, dict):
                return {"success": False, "error": f"components[{idx}] must be an object"}
            name_value = comp_ref.get("name")
            if not isinstance(name_value, str) or not name_value.strip():
                return {"success": False, "error": f"components[{idx}].name is required"}
            version_value = comp_ref.get("version")
            if version_value is not None and not isinstance(version_value, int):
                return {"success": False, "error": f"components[{idx}].version must be an integer"}
            props_value = comp_ref.get("props") or {}
            if not isinstance(props_value, dict):
                return {"success": False, "error": f"components[{idx}].props must be an object"}
            inner_value = comp_ref.get("inner_markdown") or ""
            if not isinstance(inner_value, str):
                return {"success": False, "error": f"components[{idx}].inner_markdown must be a string"}

            component_obj = _specific_component(name_value.strip(), version_value, user_id=user_id)
            if not component_obj:
                return {"success": False, "error": f"Component not found: {name_value}"}
            prop_error = validate_props(props_value, component_obj.schema or {})
            if prop_error:
                return {"success": False, "error": f"components[{idx}] props invalid: {prop_error}"}

            validated_components.append(
                {
                    "name": component_obj.name,
                    "version": component_obj.version,
                    "props": props_value,
                    "inner_markdown": inner_value,
                }
            )

        markdown = _compose_markdown_from_components(intro_markdown, validated_components, outro_markdown)
        content = {"version": "2.0", "theme_id": theme_id, "markdown": markdown}
        html = render_document(content)

        payload = {
            "title": title.strip(),
            "content": content,
            "html": html,
            "components_used": [{"name": c["name"], "version": c["version"]} for c in validated_components],
        }
        if save:
            doc = Document(title=title.strip(), content=content, doc_metadata={}, user_id=user_id)
            db.session.add(doc)
            db.session.commit()
            payload["document"] = doc.to_dict()
        return {"success": True, "data": payload}

    elif name == "list_themes":
        query = Theme.query
        # Show builtins + user's own themes
        if user_id is not None:
            query = query.filter(
                db.or_(Theme.is_builtin == True, Theme.user_id == user_id)
            )
        themes = query.all()
        result = [{"id": t.id, "name": t.name, "is_builtin": t.is_builtin, "is_default": t.is_default} for t in themes]
        return {"success": True, "data": result}

    elif name == "get_theme":
        query = Theme.query.filter_by(id=arguments.get("theme_id"))
        # Allow access to builtins or user's own themes
        if user_id is not None:
            query = query.filter(
                db.or_(Theme.is_builtin == True, Theme.user_id == user_id)
            )
        theme = query.first()
        if not theme:
            return {"success": False, "error": "Theme not found"}
        return {"success": True, "data": theme.to_dict()}

    elif name == "create_theme":
        theme = Theme(
            name=arguments["name"],
            variables=arguments["variables"],
            user_id=user_id
        )
        db.session.add(theme)
        db.session.commit()
        return {"success": True, "data": theme.to_dict()}

    elif name == "render_document_to_html":
        query = Document.query.filter_by(id=arguments.get("document_id"))
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        doc = query.first()
        if not doc:
            return {"success": False, "error": "Document not found"}
        html = render_document(doc.content, doc.user_id)
        return {"success": True, "data": {"html": html}}

    elif name == "render_document_to_pdf":
        query = Document.query.filter_by(id=arguments.get("document_id"))
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        doc = query.first()
        if not doc:
            return {"success": False, "error": "Document not found"}
        html = render_document(doc.content, doc.user_id)
        pdf_bytes = render_pdf_from_html(html)
        file_name = f'{(doc.title or "document").replace("/", "-")}.pdf'
        download_id = _store_pdf_for_download(pdf_bytes, file_name)
        base_url = request.url_root.rstrip("/")
        download_url = f"{base_url}/download/{download_id}"
        return {
            "success": True,
            "data": {
                "filename": file_name,
                "download_url": download_url,
                "content_type": "application/pdf",
                "size_bytes": len(pdf_bytes),
                "expires_in_seconds": PDF_DOWNLOAD_TTL_SECONDS,
            },
        }

    elif name == "preview_document_to_pdf":
        content = arguments.get("content")
        if not isinstance(content, dict):
            return {"success": False, "error": "content must be an object"}
        title = arguments.get("title")
        if title is not None and not isinstance(title, str):
            return {"success": False, "error": "title must be a string"}
        html = render_document(content, None)
        pdf_bytes = render_pdf_from_html(html)
        file_name = f'{((title or "document").replace("/", "-"))}.pdf'
        download_id = _store_pdf_for_download(pdf_bytes, file_name)
        base_url = request.url_root.rstrip("/")
        download_url = f"{base_url}/download/{download_id}"
        return {
            "success": True,
            "data": {
                "filename": file_name,
                "download_url": download_url,
                "content_type": "application/pdf",
                "size_bytes": len(pdf_bytes),
                "expires_in_seconds": PDF_DOWNLOAD_TTL_SECONDS,
            },
        }

    elif name == "preview_block":
        from app.services.renderer import render_block
        html = render_block(arguments.get("block", {}))
        return {"success": True, "data": {"html": html}}

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 5001))
    print(f"Starting Docsly MCP Server on port {port}")
    print(f"API Key authentication enabled. Use X-API-Key header.")
    mcp_app.run(host="0.0.0.0", port=port, debug=False)
