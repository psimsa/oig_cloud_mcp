# oig_cloud_mcp

MCP server for OIG cloud using the official [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Overview

This server implements the Model Context Protocol using FastMCP from the official `mcp` SDK. It provides authentication tools for OIG Cloud with session management and caching.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

Before running any Python command-line tools (for example `bin/cli_tester.py`), ensure the project's virtual environment is activated:

```bash
source .venv/bin/activate
```

## Usage

### Starting the Server

Run the server:

```bash
python bin/main.py
```

Or use the provided startup script:

```bash
./bin/start_server.sh
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

### Authentication

The server supports two methods for authenticating your OIG Cloud credentials.

#### 1. Basic Authentication (Recommended)

This is the standard and most compatible method. You provide your credentials in the `Authorization` header.

**How to generate the token:**

1. Take your email and password and join them with a single colon: `your_email@example.com:your_password`
2. Base64-encode this string.
   * **In Python:**
     ```python
     import base64
     token = base64.b64encode(b'your_email@example.com:your_password').decode('utf-8')
     print(token)
     ```
   * **On Linux/macOS command line:**
     ```bash
     echo -n 'your_email@example.com:your_password' | base64
     ```
3. The final header should look like this: `Authorization: Basic <your_encoded_token>`

**Example with `curl`:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Basic dGVzdEBleGFtcGxlLmNvbTp0ZXN0X3Bhc3N3b3Jk" \
  -H "Content-Type: application/json" \
  -d '{ ... tool call payload ... }'
```

Some clients only allow an `Authorization: Bearer <token>` header; the server will
accept either label provided the token is a Base64-encoded `email:password` pair.

**Example using `Bearer` label with curl:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer dGVzdEBleGFtcGxlLmNvbTp0ZXN0X3Bhc3N3b3Jk" \
  -H "Content-Type: application/json" \
  -d '{ ... tool call payload ... }'
```

#### 2. Custom Headers (Alternate option)

The server also accepts credentials via two custom headers. This is an equally valid
authentication option for clients that prefer header-based credentials.

* `X-OIG-Email`: Your OIG Cloud email.
* `X-OIG-Password`: Your OIG Cloud password.

If both Basic Auth and custom headers are provided, the server will prioritize Basic Auth.

##### Base64 encoding on Windows

If you're on Windows, here are a few ways to Base64-encode the `email:password` string.

PowerShell / PowerShell Core (pwsh):

```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes('your_email@example.com:your_password'))
```

Windows PowerShell (older versions using .NET API directly):

```powershell
[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes('your_email@example.com:your_password'))
```

Command Prompt (cmd.exe) using PowerShell helper (works on most Windows machines):

```cmd
@echo off
set "creds=your_email@example.com:your_password"
powershell -NoProfile -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes('%creds%'))"
```

Alternatively, on Windows Subsystem for Linux (WSL), Git Bash or Cygwin you can use the
standard Linux command:

```bash
echo -n 'your_email@example.com:your_password' | base64
```

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

A command-line tester is provided in `bin/cli_tester.py`. Examples:

```bash
python bin/cli_tester.py get_basic_data
python bin/cli_tester.py get_extended_data --start-date 2025-01-01 --end-date 2025-01-31
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

```
oig_cloud_mcp/
├── bin/                    # Executable scripts
│   ├── main.py            # Server runner
│   ├── cli_tester.py      # Command-line test client
│   └── start_server.sh    # Startup script
├── src/oig_cloud_mcp/     # Python package
│   ├── __init__.py        # Package metadata
│   ├── tools.py           # MCP tool definitions
│   ├── session_manager.py # Session caching and API auth
│   ├── security.py        # Whitelist and rate limiting
│   └── transformer.py     # Data transformation utilities
├── tests/                 # Test suite
│   ├── fixtures/          # Test data
│   └── test_*.py          # Unit and integration tests
├── docs/                  # Documentation
├── requirements.txt       # Dependencies
└── setup.py              # Package configuration
```

## Configuration

Server settings can be modified in `bin/main.py`:

```python
oig_tools.settings.host = "0.0.0.0"  # Listen address
oig_tools.settings.port = 8000       # Listen port
```

Session cache eviction time can be configured in `src/oig_cloud_mcp/session_manager.py`:

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

For detailed testing documentation, see [docs/testing.md](docs/testing.md).

#### Test Coverage

- **Unit Tests**: Pure functions in `transformer.py` and `security.py`
- **Integration Tests**: Tool endpoints with mocked API calls
- **CI/CD**: Automated testing on GitHub Actions for Python 3.13

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
