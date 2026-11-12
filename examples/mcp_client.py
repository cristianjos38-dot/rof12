"""Minimal MCP client configuration for a local ROF12 server."""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


server = StdioServerParameters(command="python", args=["-m", "rof12.mcp_server"])


async def main() -> None:
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "evaluate_proposal",
                arguments={
                    "proposal": {"tool_name": "refund_service", "args": {}},
                },
            )
            print(result)
