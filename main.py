from mcp.server.fastmcp import FastMCP
from session_manager import session_cache

# Create FastMCP server instance
mcp = FastMCP("OIG Cloud MCP")

# Define the authentication checking tool using FastMCP decorator
@mcp.tool()
async def check_auth(email: str, password: str) -> dict:
    """
    Checks authentication, gets a session ID, and reports cache status.
    
    Args:
        email: User email address
        password: User password
    
    Returns:
        Dictionary with authentication details including session ID preview
    """
    session_id, status = await session_cache.get_session_id(email, password)
    return {
        "email": email,
        "password_length": len(password),
        "cache_status": status,
        "session_id_preview": f"{session_id[:4]}...{session_id[-4:]}"
    }

if __name__ == "__main__":
    # Configure host and port
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8000
    
    print("Starting MCP Server with Authentication on http://0.0.0.0:8000")
    mcp.run(transport="streamable-http")
