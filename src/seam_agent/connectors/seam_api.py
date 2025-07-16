from seam_agent.assistant.models import Device, ActionAttempt


def get_device(device_id: str) -> Device:
    """
    Retrieves a device by its ID.

    This is a mock implementation.
    """
    return Device(
        device_id=device_id,
        display_name="Mock Thermostat",
        is_online=True,
        errors=[],
    )


def list_action_attempts(device_id: str) -> list[ActionAttempt]:
    """
    Lists action attempts for a given device.

    This is a mock implementation.
    """
    return [
        ActionAttempt(
            action_attempt_id="at_1",
            action_type="set_thermostat_mode",
            status="success",
        ),
        ActionAttempt(
            action_attempt_id="at_2",
            action_type="set_thermostat_mode",
            status="error",
            error_message="Device is offline.",
        ),
    ]
