import asyncio
from datetime import datetime
from mcp import MCPToolServer, Tool, create_mcp_json

# Define the functions that will handle the tool calls
async def greet(name: str) -> str:
    """A simple function that returns a greeting."""
    return f"Hello, {name}! The server is working."

async def get_time() -> str:
    """Returns the current server time."""
    return f"The current server time is: {datetime.now().isoformat()}"

# Define the tool manifest using the SDK's helpers
# This is what will be served as mcp.json
mcp_manifest = create_mcp_json(
    tools=[
        Tool(
            name="greet",
            description="Returns a simple greeting to a given name.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person to greet."
                    }
                },
                "required": ["name"]
            },
            handler=greet
        ),
        Tool(
            name="get_server_time",
            description="Gets the current time from the server.",
            input_schema={}, # No input needed for this tool
            handler=get_time
        )
    ]
    # We are not defining an auth_schema for this simple test server
)

# Create the server instance with the manifest
server = MCPToolServer(mcp_manifest)

if __name__ == "__main__":
    print("Starting Hello World MCP Server on [http://0.0.0.0:8000](http://0.0.0.0:8000)")
    print("Access the manifest at http://localhost:8000/mcp.json")
    server.run(host="0.0.0.0", port=8000)
