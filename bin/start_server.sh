#!/bin/bash
# Start the OIG Cloud MCP Server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo "Using virtual environment..."
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
    echo "Virtual environment not found, using system python3..."
    PYTHON="python3"
fi

# Start the server
echo "Starting OIG Cloud MCP Server..."
cd "$SCRIPT_DIR"
$PYTHON bin/main.py
