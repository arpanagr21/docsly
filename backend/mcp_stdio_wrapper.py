#!/usr/bin/env python3
"""
Stdio wrapper for Docsly MCP Server.
This script bridges Claude Code's stdio MCP protocol to the Docsly HTTP API.
"""

import sys
import json
import os
import urllib.request
import urllib.error

# Configuration
MCP_BASE_URL = os.getenv("DOCSLY_MCP_URL", "http://localhost:5001")
MCP_API_KEY = os.getenv("DOCSLY_MCP_API_KEY", "mcp-secret-key-change-in-production")


def make_request(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP request to MCP server."""
    url = f"{MCP_BASE_URL}{path}"
    headers = {
        "X-API-Key": MCP_API_KEY,
        "Content-Type": "application/json"
    }

    body = json.dumps(data if data is not None else {}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def handle_initialize(request_id: int, params: dict) -> dict:
    """Handle initialize request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "docsly-mcp",
                "version": "1.0.0"
            }
        }
    }


def handle_tools_list(request_id: int) -> dict:
    """Handle tools/list request."""
    response = make_request("GET", "/tools")

    if "error" in response:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": response["error"]}
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": response.get("tools", [])
        }
    }


def handle_tools_call(request_id: int, params: dict) -> dict:
    """Handle tools/call request."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    response = make_request("POST", f"/tools/{tool_name}", arguments)

    if "error" in response and not response.get("success", True):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(response, indent=2)}
                ],
                "isError": True
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {"type": "text", "text": json.dumps(response, indent=2)}
            ]
        }
    }


def process_message(message: dict) -> dict | None:
    """Process incoming JSON-RPC message."""
    method = message.get("method", "")
    request_id = message.get("id")
    params = message.get("params", {})

    # Notifications (no id) don't need responses
    if request_id is None:
        if method == "notifications/initialized":
            return None
        return None

    if method == "initialize":
        return handle_initialize(request_id, params)
    elif method == "tools/list":
        return handle_tools_list(request_id)
    elif method == "tools/call":
        return handle_tools_call(request_id, params)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def main():
    """Main loop - read from stdin, write to stdout."""
    # Unbuffered output
    sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
            response = process_message(message)

            if response is not None:
                print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
