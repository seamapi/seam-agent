from fastmcp import FastMCP
from seam_agent.connectors import seam_api

# Create a server instance with a descriptive name
mcp: FastMCP[str] = FastMCP(name="Seam Support Agent Tools")


# Register the mock functions as tools
@mcp.tool
def get_device(device_id: str) -> seam_api.Device:
    return seam_api.get_device(device_id)


@mcp.tool
def list_action_attempts(device_id: str) -> list[seam_api.ActionAttempt]:
    return seam_api.list_action_attempts(device_id)


if __name__ == "__main__":
    mcp.run()
