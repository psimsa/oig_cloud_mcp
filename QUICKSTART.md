# Quick Start Guide

## Start the Server

```bash
./start_server.sh
```

Or:

```bash
python main.py
```

Server will be available at: **http://localhost:8000/mcp**

## Test the Server

```bash
python test_client.py
```

## Quick curl Test

```bash
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
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }'
```

## Important

✅ **Correct URL**: `http://localhost:8000/mcp`
❌ **Wrong URL**: `http://localhost:8000/`

The MCP endpoint must include `/mcp` path!

## Available Tools

- `check_auth` - Authenticate and get session information
  - Parameters: `email`, `password`
  - Returns: Session ID preview and cache status
