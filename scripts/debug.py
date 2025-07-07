import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def main():
    # Connect to your MCP server (adjust the URL if needed)
    async with streamablehttp_client("http://localhost:8080/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "discord_read_messages",
                {
                    "guildId": "1378827399948406906",
                    "channelId": "1382705201827545169",
                    "limit": 10
                }
            )
            print(result)

if __name__ == "__main__":
    asyncio.run(main())