import json
import os
import asyncio
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

from app import create_app
from app.extensions import db
from app.models import Document, Component, Theme
from app.services.renderer import render_document

# Create Flask app for HTTP-based MCP server
mcp_app = Flask(__name__)
CORS(mcp_app)

# Get MCP API key from environment
MCP_API_KEY = os.getenv("MCP_API_KEY", "mcp-secret-key-change-in-production")

# Reference to main app for database access
main_app = create_app()


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if not api_key or api_key != MCP_API_KEY:
            return jsonify({"error": "Unauthorized", "message": "Invalid or missing API key"}), 401
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
                "content": {"type": "object", "description": "Document content with blocks"}
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
                "content": {"type": "object", "description": "New content"}
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
        "description": "List all available components",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_component",
        "description": "Get component schema by name",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "create_component",
        "description": "Create a new component",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Component name"},
                "schema": {"type": "object", "description": "JSON Schema for props validation"},
                "template": {"type": "string", "description": "Markdown template (supports {{prop}} placeholders)"}
            },
            "required": ["name", "schema", "template"]
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
    return jsonify({"status": "healthy", "service": "draftly-mcp"})


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
        result = execute_tool(tool_name, arguments)
        return jsonify(result)


def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool and return the result."""

    if name == "list_documents":
        docs = Document.query.all()
        result = [{"id": d.id, "title": d.title, "updated_at": d.updated_at.isoformat()} for d in docs]
        return {"success": True, "data": result}

    elif name == "get_document":
        doc = Document.query.get(arguments.get("document_id"))
        if not doc:
            return {"success": False, "error": "Document not found"}
        return {"success": True, "data": doc.to_dict()}

    elif name == "create_document":
        default_content = {"version": "2.0", "theme_id": None, "markdown": ""}
        doc = Document(
            title=arguments["title"],
            content=arguments.get("content") or default_content,
            doc_metadata={}
        )
        db.session.add(doc)
        db.session.commit()
        return {"success": True, "data": doc.to_dict()}

    elif name == "update_document":
        doc = Document.query.get(arguments.get("document_id"))
        if not doc:
            return {"success": False, "error": "Document not found"}
        if arguments.get("title"):
            doc.title = arguments["title"]
        if arguments.get("content"):
            doc.content = arguments["content"]
        db.session.commit()
        return {"success": True, "data": doc.to_dict()}

    elif name == "delete_document":
        doc = Document.query.get(arguments.get("document_id"))
        if not doc:
            return {"success": False, "error": "Document not found"}
        db.session.delete(doc)
        db.session.commit()
        return {"success": True, "data": {"deleted": True}}

    elif name == "list_components":
        comps = Component.query.filter_by(is_active=True).all()
        result = [{"name": c.name, "version": c.version, "is_builtin": c.is_builtin, "schema": c.schema} for c in comps]
        return {"success": True, "data": result}

    elif name == "get_component":
        comp = Component.query.filter_by(name=arguments.get("name"), is_active=True).first()
        if not comp:
            return {"success": False, "error": "Component not found"}
        return {"success": True, "data": comp.to_dict()}

    elif name == "create_component":
        comp = Component(
            name=arguments["name"],
            schema=arguments["schema"],
            template=arguments["template"],
            is_active=True
        )
        db.session.add(comp)
        db.session.commit()
        return {"success": True, "data": comp.to_dict()}

    elif name == "list_themes":
        themes = Theme.query.all()
        result = [{"id": t.id, "name": t.name, "is_builtin": t.is_builtin, "is_default": t.is_default} for t in themes]
        return {"success": True, "data": result}

    elif name == "get_theme":
        theme = Theme.query.get(arguments.get("theme_id"))
        if not theme:
            return {"success": False, "error": "Theme not found"}
        return {"success": True, "data": theme.to_dict()}

    elif name == "create_theme":
        theme = Theme(
            name=arguments["name"],
            variables=arguments["variables"]
        )
        db.session.add(theme)
        db.session.commit()
        return {"success": True, "data": theme.to_dict()}

    elif name == "render_document_to_html":
        doc = Document.query.get(arguments.get("document_id"))
        if not doc:
            return {"success": False, "error": "Document not found"}
        html = render_document(doc.content, doc.user_id)
        return {"success": True, "data": {"html": html}}

    elif name == "preview_block":
        from app.services.renderer import render_block
        html = render_block(arguments.get("block", {}))
        return {"success": True, "data": {"html": html}}

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", 5001))
    print(f"Starting Draftly MCP Server on port {port}")
    print(f"API Key authentication enabled. Use X-API-Key header.")
    mcp_app.run(host="0.0.0.0", port=port, debug=False)
