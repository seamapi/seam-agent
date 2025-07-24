import asyncio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import os

SEAM_API_KEY = os.getenv("SEAM_API_KEY")

if not SEAM_API_KEY:
    raise ValueError("SEAM_API_KEY is not set")

client = Client(
    StdioTransport(
        command="python",
        args=["server.py"],
        env={
            "SEAM_API_KEY": SEAM_API_KEY,
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


if __name__ == "__main__":
    asyncio.run(main())
