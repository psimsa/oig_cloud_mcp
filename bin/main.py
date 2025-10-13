from oig_cloud_mcp.tools import oig_tools
from oig_cloud_mcp.observability import setup_observability

if __name__ == "__main__":
    # Configure host and port for the tools-driven FastMCP instance
    oig_tools.settings.host = "0.0.0.0"
    oig_tools.settings.port = 8000

    # Initialize OpenTelemetry (robust to FastMCP implementation details)
    setup_observability(getattr(oig_tools, "app", oig_tools))

    print("Starting OIG Cloud MCP Server on http://0.0.0.0:8000")
    oig_tools.run(transport="streamable-http")
