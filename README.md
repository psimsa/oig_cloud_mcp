# oig_cloud_mcp

MCP server for OIG cloud using the official [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Overview

This server implements the Model Context Protocol using FastMCP from the official `mcp` SDK. It provides authentication tools for OIG Cloud with session management and caching.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

Run the server:

```bash
python main.py
```

Or use the provided startup script:

```bash
./start_server.sh
```

The server will start on `http://0.0.0.0:8000` using the StreamableHTTP transport.

You should see output like:
```
SessionCache initialized.
Starting MCP Server with Authentication on http://0.0.0.0:8000
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     StreamableHTTP session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Connecting to the Server

The MCP endpoint is available at: **`http://localhost:8000/mcp`**

#### Using the Python MCP Client

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    # Connect to the server
    async with streamablehttp_client("http://localhost:8000/mcp") as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            print("✓ Connected")
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
            
            # Call the check_auth tool
            result = await session.call_tool(
                "check_auth",
                arguments={
                    "email": "user@example.com",
                    "password": "your_password"
                }
            )
            print(f"Result: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
```

A complete example client is provided in `test_client.py`. Run it with:

```bash
python test_client.py
```

#### Using Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "oig-cloud": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

#### Manual Testing with curl

```bash
# Initialize connection
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream, application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0"}
    }
  }'
```

## Features

- **FastMCP Integration**: Uses the official MCP SDK's FastMCP for clean, decorator-based tool definitions
- **Session Management**: Caches authentication sessions with configurable eviction time (12 hours)
- **Authentication Tool**: `check_auth` tool validates credentials and returns session information
- **StreamableHTTP Transport**: Modern, scalable HTTP-based transport with SSE support

## Available Tools

### `check_auth`

Authenticates with OIG Cloud and returns session information.

**Parameters:**
- `email` (string, required): User email address
- `password` (string, required): User password

**Returns:**
```json
{
  "email": "user@example.com",
  "password_length": 12,
  "cache_status": "new_session_created",
  "session_id_preview": "a1b2...c3d4"
}
```

**Cache Status Values:**
- `new_session_created`: Fresh authentication with OIG Cloud API
- `session_from_cache`: Retrieved from local cache (no API call)

## Architecture

- **main.py**: FastMCP server implementation with tool definitions
- **session_manager.py**: Session caching and OIG Cloud API authentication
- **test_client.py**: Example client demonstrating proper connection
- **requirements.txt**: Dependencies including `mcp` SDK

## Configuration

Server settings can be modified in `main.py`:

```python
mcp.settings.host = "0.0.0.0"  # Listen address
mcp.settings.port = 8000       # Listen port
```

Session cache eviction time can be configured in `session_manager.py`:

```python
session_cache = SessionCache(eviction_time_seconds=43200)  # 12 hours
```

## Development

The server uses:
- **FastMCP**: High-level MCP server framework with decorators
- **StreamableHTTP**: Modern HTTP-based transport for MCP
- **Session Caching**: 12-hour session cache to minimize authentication calls
- **Uvicorn**: ASGI server for production-ready deployment

## Troubleshooting

### 404 Not Found

Make sure you're connecting to `/mcp` endpoint: `http://localhost:8000/mcp`

### 406 Not Acceptable

Ensure your client sends the correct Accept headers:
- `Accept: text/event-stream, application/json`

### Connection Refused

Verify the server is running:
```bash
curl http://localhost:8000/mcp
```

You should see a response (even if it's an error about headers).
