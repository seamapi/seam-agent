from pydantic import BaseModel, Field
from typing import List, Optional


class Device(BaseModel):
    """Represents a device in the Seam system."""

    device_id: str = Field(..., description="The unique identifier for the device.")
    display_name: str
    is_online: bool
    errors: List[str] = []


class ActionAttempt(BaseModel):
    """Represents an attempt to perform an action on a device."""

    action_attempt_id: str
    action_type: str
    status: str
    error_message: Optional[str] = None


class AnalysisResult(BaseModel):
    """The final analysis result to be presented to the support agent."""

    device: Device
    action_attempts: List[ActionAttempt]
    summary: str
    timeline: List[str]
    root_cause: Optional[str] = None
