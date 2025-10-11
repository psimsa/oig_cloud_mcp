"""A tiny local replacement for the `mcp` SDK used by the example server.

This module implements the minimal API surface the example expects:

- Tool: a simple dataclass carrying metadata and a handler callable
- create_mcp_json: builds a manifest-like object that can be serialized
- MCPToolServer: a small HTTP server that exposes /mcp.json and
  POST /tools/<tool_name> endpoints and invokes the tool handlers.

This is intentionally small and dependency-free so the example can run
without requiring the real SDK to be installed or to match a specific
implementation detail.
"""
from __future__ import annotations

import json
import asyncio
import inspect
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


class MCPManifest:
    """Holds both the Tool objects and a JSON-serializable representation."""

    def __init__(self, tools: List[Tool], auth_schema: Optional[Dict[str, Any]] = None):
        self.tools: List[Tool] = list(tools)
        self.auth_schema = auth_schema

    def to_json(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in self.tools
            ],
            "auth_schema": self.auth_schema,
        }


def create_mcp_json(*, tools: List[Tool], auth_schema: Optional[Dict[str, Any]] = None) -> MCPManifest:
    """Create and return an MCPManifest instance.

    The real SDK likely returns a plain dict for mcp.json; here we return
    an object that preserves the tool handler references and can also
    emit a JSON-serializable manifest via `to_json()`.
    """

    return MCPManifest(tools=tools, auth_schema=auth_schema)


class _ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MCPToolServer:
    def __init__(self, manifest: MCPManifest):
        self.manifest = manifest
        # Map tool name -> Tool for quick lookup during requests
        self._tool_map: Dict[str, Tool] = {t.name: t for t in manifest.tools}

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        manifest_json = self.manifest.to_json()

        server_address = (host, port)

        # Handler factory to capture manifest and tool handlers in closure
        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, data: Any, status: int = 200) -> None:
                payload = json.dumps(data, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:
                if self.path == "/mcp.json":
                    self._send_json(manifest_json)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self) -> None:
                if not self.path.startswith("/tools/"):
                    self.send_response(404)
                    self.end_headers()
                    return

                tool_name = self.path[len("/tools/"):]
                tool = self.server._tool_map.get(tool_name)  # type: ignore[attr-defined]
                if tool is None:
                    self._send_json({"error": f"Tool '{tool_name}' not found."}, status=404)
                    return

                # Read the request body
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length > 0 else b""
                try:
                    payload = json.loads(body.decode("utf-8")) if body else {}
                except Exception:
                    self._send_json({"error": "Invalid JSON payload."}, status=400)
                    return

                # Prepare kwargs for the handler based on its signature
                handler = tool.handler
                try:
                    sig = inspect.signature(handler)
                except (ValueError, TypeError):
                    sig = None

                kwargs = {}
                if sig is not None:
                    for name, param in sig.parameters.items():
                        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                            # pass the whole payload for flexible handlers
                            continue
                        if name in payload:
                            kwargs[name] = payload[name]
                        elif param.default is inspect.Parameter.empty:
                            # required parameter missing
                            self._send_json({"error": f"Missing required parameter: {name}"}, status=400)
                            return

                # If handler accepts **kwargs, pass whole payload as fallback
                accepts_kwargs = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in (sig.parameters.values() if sig else [])
                )
                call_kwargs = kwargs if kwargs else (payload if accepts_kwargs else {})

                # Execute handler (support async and sync functions)
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = asyncio.run(handler(**call_kwargs))
                    else:
                        result = handler(**call_kwargs)
                except TypeError as e:
                    # Handler signature mismatch or wrong args
                    self._send_json({"error": f"Handler invocation error: {str(e)}"}, status=500)
                    return
                except Exception as e:
                    self._send_json({"error": f"Handler raised an exception: {str(e)}"}, status=500)
                    return

                # Wrap result in the expected output format
                self._send_json({"output": result})

            # Suppress logging for cleaner test output
            def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - small helper
                return

        # Bind the tool map onto the server object so handlers can find it
        httpd = _ThreadingHTTPServer(server_address, Handler)
        httpd._tool_map = self._tool_map  # attach for handler access

        print(f"MCPToolServer listening on http://{host}:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()


__all__ = ["Tool", "create_mcp_json", "MCPToolServer"]
