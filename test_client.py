#!/usr/bin/env python3
"""
Example client demonstrating how to connect to the OIG Cloud MCP server.
"""

import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    """Connect to the MCP server and test the check_auth tool."""
    
    # Connect to the server
    server_url = "http://localhost:8000/mcp"
    
    print(f"Connecting to MCP server at {server_url}...")
    
    async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            print("✓ Connected and initialized")
            
            # List available tools
            tools = await session.list_tools()
            print(f"\n✓ Available tools ({len(tools.tools)}):")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Call the check_auth tool
            print("\n✓ Testing check_auth tool...")
            result = await session.call_tool(
                "check_auth",
                arguments={
                    "email": "test@example.com",
                    "password": "test_password_123"
                }
            )
            
            # Display the result
            print("\n✓ Result:")
            if result.content:
                for content in result.content:
                    print(f"  {content.text if hasattr(content, 'text') else content}")
            
            if hasattr(result, 'structuredContent') and result.structuredContent:
                print("\n✓ Structured result:")
                for key, value in result.structuredContent.items():
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
