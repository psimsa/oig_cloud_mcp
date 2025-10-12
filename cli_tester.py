#!/usr/bin/env python3
"""Command-line test client for the OIG Cloud MCP server.

This script replaces the previous `test_client.py` and provides a
simple, flexible interface to call the MCP tools exposed by the
server for quick manual testing.
"""
import argparse
import asyncio
import json
from typing import Dict, Any

import os
import sys

# Enforce virtual environment activation for safety per project instructions
if not os.environ.get("VIRTUAL_ENV"):
    print(
        "Error: Python virtual environment is not active.\n"
        "Activate it before running this tool: source .venv/bin/activate"
    )
    sys.exit(1)

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def call_tool(
    server_url: str, tool_name: str, arguments: Dict[str, Any], headers: Dict[str, str]
) -> None:
    async with streamablehttp_client(server_url, headers=headers) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)

            # Prefer structuredContent when available
            structured = getattr(result, "structuredContent", None)
            if structured:
                print(json.dumps(structured, indent=2))
                return

            # Fall back to streaming content if structured content is not present
            if getattr(result, "content", None):
                out_items = []
                for c in result.content:
                    text = getattr(c, "text", None)
                    if text:
                        try:
                            out_items.append(json.loads(text))
                        except Exception:
                            out_items.append(text)
                    else:
                        out_items.append(c)
                print(json.dumps(out_items, indent=2, default=str))
            else:
                print("No content returned from tool.")


def build_arguments(ns: argparse.Namespace) -> Dict[str, Any]:
    args: Dict[str, Any] = {}
    if ns.tool_name == "get_extended_data":
        # Include date parameters (may be empty strings if not supplied)
        args["start_date"] = ns.start_date or ""
        args["end_date"] = ns.end_date or ""
    elif ns.tool_name == "set_box_mode":
        if not ns.box_mode:
            raise ValueError("Error: --box-mode is required for set_box_mode tool.")
        args["mode"] = ns.box_mode
    elif ns.tool_name == "set_grid_delivery":
        if ns.grid_mode is None:
            raise ValueError(
                "Error: --grid-mode is required for set_grid_delivery tool."
            )
        args["mode"] = ns.grid_mode
    return args


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Call OIG Cloud MCP tools from the command line"
    )
    parser.add_argument(
        "tool_name",
        choices=[
            "get_basic_data",
            "get_extended_data",
            "get_notifications",
            "set_box_mode",
            "set_grid_delivery",
        ],
        help="Tool to invoke on the MCP server",
    )
    parser.add_argument(
        "--email", default="test@example.com", help="User email for authentication"
    )
    parser.add_argument(
        "--password",
        default="test_password_123",
        help="User password for authentication",
    )
    parser.add_argument(
        "--start-date",
        dest="start_date",
        default=None,
        help="Start date for historical queries (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date",
        default=None,
        help="End date for historical queries (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--url", default="http://localhost:8000/mcp", help="MCP server URL"
    )

    # New arguments for actions
    parser.add_argument(
        "--actions",
        action="store_true",
        help="Enable write actions by setting X-OIG-Readonly-Access to false.",
    )
    parser.add_argument(
        "--box-mode",
        type=str,
        help="The mode for the 'set_box_mode' action (e.g., 'Home 1').",
    )
    parser.add_argument(
        "--grid-mode",
        type=int,
        help="The mode for the 'set_grid_delivery' action (e.g., 1 or 0).",
    )
    parser.add_argument(
        "--auth-mode",
        choices=["header", "basic"],
        default="header",
        help="The authentication method to use.",
    )

    ns = parser.parse_args()
    arguments = build_arguments(ns)

    headers = {}
    if ns.auth_mode == "basic":
        print("Using Basic Authentication.")
        import base64

        creds = f"{ns.email}:{ns.password}"
        token = base64.b64encode(creds.encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    else:
        print("Using custom X-OIG header authentication.")
        headers["X-OIG-Email"] = ns.email
        headers["X-OIG-Password"] = ns.password

    if ns.actions:
        headers["X-OIG-Readonly-Access"] = "false"
        print("Action mode enabled: Sending 'X-OIG-Readonly-Access: false' header.")
    print(f"Calling {ns.tool_name} on {ns.url} with arguments: {arguments}")
    await call_tool(ns.url, ns.tool_name, arguments, headers)


if __name__ == "__main__":
    asyncio.run(main())
