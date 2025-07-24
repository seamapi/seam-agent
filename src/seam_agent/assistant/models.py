from pydantic import BaseModel, Field
from datetime import datetime


class ActionAttempt(BaseModel):
    """Represents an attempt to perform an action on a device."""

    action_attempt_id: str
    action_type: str
    status: str
    error_message: str | None = None


class DeviceConfig(BaseModel):
    """Configuration model for device settings - example of when to use pydantic."""

    device_id: str = Field(..., description="The unique identifier for the device.")
    display_name: str
    is_online: bool
    errors: list[str] = []

    # Example of validation logic that benefits from pydantic
    retry_count: int = Field(
        default=3, ge=1, le=10, description="Number of retry attempts"
    )
    timeout_seconds: int = Field(default=30, gt=0, description="Timeout in seconds")


class AnalysisResult(BaseModel):
    """
    Legacy model for analysis results - consider returning JSON dict instead.
    Kept for backward compatibility but prefer dict[str, Any] for LLM-bound data.
    """

    device_id: str
    summary: str
    timeline: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


# Note: For device data going to LLMs, use raw JSON dicts instead of pydantic models.
# Example:
# device_data: dict[str, Any] = await seam_client.get_device(device_id)
# This is simpler, faster, and LLMs handle JSON natively.
