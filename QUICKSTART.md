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

Use the provided command-line tester:

```bash
python cli_tester.py get_basic_data
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

- `get_basic_data` - Fetch a real-time snapshot of the PV system
  - Parameters: `email`, `password`

- `get_extended_data` - Retrieve historical time-series data
  - Parameters: `email`, `password`, `start_date`, `end_date`

- `get_notifications` - Get system alerts and informational messages
  - Parameters: `email`, `password`
