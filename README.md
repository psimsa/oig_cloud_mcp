# oig_cloud_mcp

MCP server for OIG cloud using the official [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Overview

This server implements the Model Context Protocol using FastMCP from the official `mcp` SDK. It provides authentication tools for OIG Cloud with session management and caching.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the server:

```bash
python main.py
```

The server will start on `http://0.0.0.0:8000` using the StreamableHTTP transport.

## Features

- **FastMCP Integration**: Uses the official MCP SDK's FastMCP for clean, decorator-based tool definitions
- **Session Management**: Caches authentication sessions with configurable eviction time
- **Authentication Tool**: `check_auth` tool validates credentials and returns session information

## Architecture

- **main.py**: FastMCP server implementation with tool definitions
- **session_manager.py**: Session caching and OIG Cloud API authentication
- **requirements.txt**: Dependencies including `mcp` SDK

## Development

The server uses:
- **FastMCP**: High-level MCP server framework with decorators
- **StreamableHTTP**: Modern HTTP-based transport for MCP
- **Session Caching**: 12-hour session cache to minimize authentication calls
