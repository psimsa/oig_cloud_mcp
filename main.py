from mcp import MCPToolServer, Tool, create_mcp_json
from session_manager import session_cache

# Define the new tool handler for testing authentication
async def check_auth(email: str, password: str) -> dict:
    """
    A test tool that uses the SessionCache to authenticate and get a session ID.
    Returns information about the auth attempt.
    """
    session_id, status = await session_cache.get_session_id(email, password)
    return {
        "email": email,
        "password_length": len(password),
        "cache_status": status,
        "session_id_preview": f"{session_id[:4]}...{session_id[-4:]}"
    }

# Define the MCP manifest with an authentication schema
mcp_manifest = create_mcp_json(
    auth_schema={
        "type": "object",
        "properties": {
            "email": {"type": "string"},
            "password": {"type": "string"}
        },
        "required": ["email", "password"]
    },
    tools=[
        Tool(
            name="check_auth",
            description="Checks authentication, gets a session ID, and reports cache status.",
            input_schema={}, # No input needed from the tool_code, auth comes from context
            handler=check_auth
        )
    ]
)

# Create the server instance
server = MCPToolServer(mcp_manifest)

if __name__ == "__main__":
    print("Starting MCP Server with Authentication on [http://0.0.0.0:8000](http://0.0.0.0:8000)")
    server.run(host="0.0.0.0", port=8000)
