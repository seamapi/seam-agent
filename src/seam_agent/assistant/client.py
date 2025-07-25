import asyncio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import os

SEAM_API_KEY = os.getenv("SEAM_API_KEY")
QUICKWIT_URL = os.getenv("QUICKWIT_URL")
QUICKWIT_API_KEY = os.getenv("QUICKWIT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not SEAM_API_KEY:
    raise ValueError("SEAM_API_KEY is not set")

if not QUICKWIT_URL:
    raise ValueError("QUICKWIT_URL is not set")

if not QUICKWIT_API_KEY:
    raise ValueError("QUICKWIT_API_KEY is not set")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

client = Client(
    StdioTransport(
        command="python",
        args=["server.py"],
        env={
            "SEAM_API_KEY": SEAM_API_KEY,
            "QUICKWIT_URL": QUICKWIT_URL,
            "QUICKWIT_API_KEY": QUICKWIT_API_KEY,
            "DATABASE_URL": DATABASE_URL,
        },
        cwd="src/seam_agent/assistant",
    ),
)


async def main():
    async with client:
        # List available resources
        resources = await client.list_resources()
        print("Available resources:")
        for resource in resources:
            print(f"  - {resource.uri}: {resource.description}")

        # List available tools
        tools = await client.list_tools()
        print("\nAvailable tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        print("\n" + "=" * 50 + "\n")

        # Test reading all devices
        print("Testing seam://devices...")
        try:
            result = await client.read_resource(uri="seam://devices")
            print("✅ Successfully read devices resource")
            print(f"   Result type: {type(result)}")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"❌ Error reading devices: {e}")

        print("\n" + "=" * 30 + "\n")

        # Test using the search tool
        print("Testing search_devices tool...")
        try:
            search_result = await client.call_tool("search_devices", {"limit": 5})
            print("✅ Successfully called search_devices tool")
            print(f"   Result: {search_result}")
        except Exception as e:
            print(f"❌ Error calling search_devices: {e}")

        print("\n" + "=" * 30 + "\n")

        # Test using the search_logs tool
        print("Testing search_logs tool...")
        try:
            log_search_result = await client.call_tool(
                "search_logs",
                {
                    "query": "level:ERROR",
                    "limit": 5,
                    "index": "application_logs_v4",
                },
            )
            print("✅ Successfully called search_logs tool")
            print(f"   Result: {log_search_result}")
        except Exception as e:
            print(f"❌ Error calling search_logs: {e}")

        print("\n" + "=" * 30 + "\n")

        # Test using the search_logs tool with offset
        print("Testing search_logs tool with offset...")
        try:
            await client.call_tool(
                "search_logs",
                {
                    "query": "level:ERROR",
                    "limit": 2,
                    "offset": 5,
                    "index": "application_logs_v4",
                },
            )
            print("✅ Successfully called search_logs tool with offset")
        except Exception as e:
            print(f"❌ Error calling search_logs with offset: {e}")


if __name__ == "__main__":
    asyncio.run(main())
