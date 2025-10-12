# oig_cloud_mcp

MCP server for OIG cloud using the official [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Overview

This server implements the Model Context Protocol using FastMCP from the official `mcp` SDK. It provides authentication tools for OIG Cloud with session management and caching.

## Installation

```bash
pip install -r requirements.txt
```

Before running any Python command-line tools (for example `cli_tester.py`), ensure the project's virtual environment is activated:

```bash
source .venv/bin/activate
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
            
      # Call one of the OIG tools, for example get_basic_data
      result = await session.call_tool(
        "get_basic_data",
        arguments={
          "email": "user@example.com",
          "password": "your_password"
        }
      )
      if getattr(result, "structuredContent", None):
        import json
        print(json.dumps(result.structuredContent, indent=2))
      else:
        # Fallback to textual/stream content
        for content in getattr(result, "content", []):
          print(getattr(content, "text", content))


if __name__ == "__main__":
    asyncio.run(main())
```

A command-line tester is provided in `cli_tester.py`. Examples:

```bash
python cli_tester.py get_basic_data
python cli_tester.py get_extended_data --start-date 2025-01-01 --end-date 2025-01-31
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
- **OIG Tools**: `get_basic_data`, `get_extended_data`, and `get_notifications` are provided and fetch live data from the user's OIG Cloud account
- **StreamableHTTP Transport**: Modern, scalable HTTP-based transport with SSE support

## Security Features

This release adds basic security protections for live authentication:

- Whitelist: Only users listed in `whitelist.txt` are permitted to request
  authentication and use the tools. Add your OIG Cloud email (one per line)
  to `whitelist.txt` located in the project root.

- Rate limiting: Repeated failed authentication attempts are tracked per-user
  and will temporarily lock the account using an exponential backoff strategy
  (defaults: 3 failures -> initial 10s lockout, doubling up to 30s).

These protections are implemented for single-process deployments and are
intended to be a minimal, easily-understood safety mechanism. For production
you should replace the in-memory rate-limiter with a central store such as
Redis so lockouts persist across processes and machines.

## Available Tools

`get_basic_data` - Fetches a real-time snapshot of the PV system from the authenticated user's OIG Cloud account and returns the live payload from the OIG Cloud API.

`get_extended_data` - Retrieves historical time-series data for a specified period. Accepts `start_date` and `end_date` parameters (YYYY-MM-DD) which are forwarded to the OIG Cloud API.

`get_notifications` - Fetches system alerts, warnings, and informational messages from the user's OIG Cloud account.

## Architecture

- **tools.py**: MCP tool definitions (`get_basic_data`, `get_extended_data`, `get_notifications`)
- **main.py**: Server runner that imports `oig_tools` and starts the FastMCP server
- **session_manager.py**: Session caching and OIG Cloud API authentication
- **cli_tester.py**: Command-line test client for invoking the MCP tools
- **requirements.txt**: Dependencies including `mcp` SDK

## Configuration

Server settings can be modified in `main.py`:

```python
oig_tools.settings.host = "0.0.0.0"  # Listen address
oig_tools.settings.port = 8000       # Listen port
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

### Testing

This project includes a comprehensive testing suite with unit tests, integration tests, and automated CI/CD pipeline.

#### Quick Start

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Check code quality
flake8 .
black --check .
```

For detailed testing documentation, see [TESTING.md](TESTING.md).

#### Test Coverage

- **Unit Tests**: Pure functions in `transformer.py` and `security.py`
- **Integration Tests**: Tool endpoints with mocked API calls
- **CI/CD**: Automated testing on GitHub Actions for Python 3.11 and 3.12

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
