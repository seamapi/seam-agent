"""
Admin links connector for generating relevant admin page URLs.

Reads admin_pages_context.md and generates relevant admin page links
based on investigation context.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path


class AdminLinksConnector:
    """Connector for generating admin page links based on investigation context."""

    def __init__(self, base_admin_url: str = "https://connect.getseam.com/admin"):
        """
        Initialize the admin links connector.

        Args:
            base_admin_url: Base URL for admin pages (default: https://connect.getseam.com/admin)
        """
        self.base_admin_url = base_admin_url.rstrip("/")
        self._admin_pages_data = None
        self._load_admin_pages_context()

    def _load_admin_pages_context(self):
        """Load and parse the admin_pages_context.md file."""
        # Find the admin_pages_context.md file relative to this module
        current_dir = Path(__file__).parent
        context_file = current_dir / "admin_pages_context.md"

        if not context_file.exists():
            raise FileNotFoundError(
                f"Admin pages context file not found: {context_file}"
            )

        with open(context_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the markdown content to extract page information
        self._admin_pages_data = self._parse_admin_pages_content(content)

    def _parse_admin_pages_content(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse the markdown content to extract admin page information."""
        pages = {}
        current_page = None
        current_section = None

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Main page sections (### page_name.tsx)
            if line.startswith("### ") and line.endswith(".tsx"):
                page_name = line[4:-4]  # Remove ### and .tsx
                current_page = page_name
                pages[current_page] = {
                    "name": page_name,
                    "purpose": "",
                    "query_params": [],
                    "required_params": [],
                    "optional_params": [],
                }
                current_section = "main"

            # Purpose line
            elif line.startswith("**Purpose**:") and current_page:
                pages[current_page]["purpose"] = line[12:].strip()

            # Query parameters section
            elif line.startswith("**Query Parameters**:") and current_page:
                current_section = "params"

            # Parameter lines (- `param_name` (type) - description)
            elif (
                line.startswith("- `") and current_section == "params" and current_page
            ):
                # Parse parameter line: - `device_id` (optional string) - The device ID to view
                param_line = line[3:]  # Remove '- `'
                if "`" in param_line:
                    param_name = param_line.split("`")[0]
                    rest = param_line.split("`", 1)[1]

                    # Extract type information
                    param_info = {
                        "name": param_name,
                        "required": "required" in rest.lower(),
                        "type": "string",  # Default
                        "description": "",
                    }

                    # Extract type from parentheses
                    if "(" in rest and ")" in rest:
                        type_part = rest[rest.find("(") + 1 : rest.find(")")]
                        if "string" in type_part:
                            param_info["type"] = "string"
                        elif "integer" in type_part or "number" in type_part:
                            param_info["type"] = "integer"
                        elif "boolean" in type_part:
                            param_info["type"] = "boolean"

                    # Extract description after the dash
                    if " - " in rest:
                        param_info["description"] = rest.split(" - ", 1)[1]

                    pages[current_page]["query_params"].append(param_info)

                    if param_info["required"]:
                        pages[current_page]["required_params"].append(param_name)
                    else:
                        pages[current_page]["optional_params"].append(param_name)

            i += 1

        return pages

    def get_relevant_admin_links(
        self, investigation_context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Generate relevant admin page links based on investigation context.

        Args:
            investigation_context: Dict containing device_id, workspace_id, access_codes, etc.
                                  Can also contain structured insights from ToolResultProcessor

        Returns:
            List of dicts with 'title', 'url', and 'description' keys
        """
        if not self._admin_pages_data:
            return []

        relevant_links = []

        # Extract key identifiers from context (supports both old and new formats)
        device_id = investigation_context.get("device_id")
        workspace_id = investigation_context.get("workspace_id")
        access_codes = investigation_context.get("access_codes", [])
        action_attempts = investigation_context.get("action_attempts", [])
        third_party_account_id = investigation_context.get("third_party_account_id")

        # Extract from structured processor context if available
        mentioned_code_ids = investigation_context.get("mentioned_code_ids", [])
        unmanaged_code_ids = investigation_context.get("unmanaged_code_ids", [])
        has_failures = investigation_context.get("has_failures", False)
        failure_types = investigation_context.get("failure_types", [])
        cross_tool_insights = investigation_context.get("cross_tool_insights", [])

        # Device-specific links
        if device_id:
            # Main device view with enhanced description based on investigation
            device_link = self._build_admin_link(
                "view_device", {"device_id": device_id, "quickwit": "true"}
            )
            if device_link:
                device_description = "Check comprehensive device logs and properties"
                if any("offline" in insight.lower() for insight in cross_tool_insights):
                    device_description += " - Focus on connectivity status"
                if unmanaged_code_ids:
                    device_description += " - Review access code management"

                relevant_links.append(
                    {
                        "title": "Device Details",
                        "url": device_link,
                        "description": device_description,
                    }
                )

            # Device action attempts - prioritize if failures detected
            if action_attempts or has_failures or failure_types:
                action_link = self._build_admin_link(
                    "view_action_attempt", {"device_id": device_id, "quickwit": "true"}
                )
                if action_link:
                    action_description = "Examine the failed attempt details and timing"
                    if failure_types:
                        action_description += (
                            f" - Check {', '.join(failure_types)} failures"
                        )
                    else:
                        action_description = "View device action attempts and their success/failure status"

                    relevant_links.append(
                        {
                            "title": "Action Attempts",
                            "url": action_link,
                            "description": action_description,
                        }
                    )

            # Device events - emphasize if connectivity issues
            device_events_link = self._build_admin_link(
                "view_device_action_attempts", {"device_id": device_id}
            )
            if device_events_link:
                events_description = "Review complete action timeline"
                if any(
                    "connectivity" in insight.lower() or "offline" in insight.lower()
                    for insight in cross_tool_insights
                ):
                    events_description += " - Focus on connectivity patterns"

                relevant_links.append(
                    {
                        "title": "Device Action History",
                        "url": device_events_link,
                        "description": events_description,
                    }
                )

        # Access code links - prioritize mentioned and unmanaged codes
        processed_code_ids = set()

        # First, add links for codes mentioned in the investigation
        for code_id in mentioned_code_ids:
            if code_id and code_id not in processed_code_ids:
                access_code_link = self._build_admin_link(
                    "view_access_code", {"access_code_id": code_id, "quickwit": "true"}
                )
                if access_code_link:
                    is_unmanaged = code_id in unmanaged_code_ids
                    status_note = (
                        " (UNMANAGED - investigate management history)"
                        if is_unmanaged
                        else ""
                    )
                    relevant_links.append(
                        {
                            "title": f"Query Access Code{status_note}",
                            "url": access_code_link,
                            "description": f"View details for access code mentioned in query - check audit trail{status_note}",
                        }
                    )
                    processed_code_ids.add(code_id)

        # Then add other unmanaged codes if not already included
        for code_id in unmanaged_code_ids:
            if code_id and code_id not in processed_code_ids:
                access_code_link = self._build_admin_link(
                    "view_access_code", {"access_code_id": code_id, "quickwit": "true"}
                )
                if access_code_link:
                    relevant_links.append(
                        {
                            "title": "Unmanaged Access Code",
                            "url": access_code_link,
                            "description": "Review unmanaged access code - check creation and management history",
                        }
                    )
                    processed_code_ids.add(code_id)

        # Finally, add remaining access codes from legacy format
        if access_codes:
            for access_code in access_codes:
                if isinstance(access_code, dict) and access_code.get("access_code_id"):
                    access_code_id = access_code["access_code_id"]
                    if access_code_id not in processed_code_ids:
                        access_code_link = self._build_admin_link(
                            "view_access_code",
                            {"access_code_id": access_code_id, "quickwit": "true"},
                        )
                        if access_code_link:
                            code_name = access_code.get("name", "Unknown")
                            relevant_links.append(
                                {
                                    "title": f"Access Code: {code_name}",
                                    "url": access_code_link,
                                    "description": f"View access code details and audit logs for {code_name}",
                                }
                            )
                            processed_code_ids.add(access_code_id)

        # Workspace links
        if workspace_id:
            workspace_link = self._build_admin_link(
                "view_workspace", {"workspace_id": workspace_id}
            )
            if workspace_link:
                relevant_links.append(
                    {
                        "title": "Workspace Overview",
                        "url": workspace_link,
                        "description": "View workspace details, members, and API keys",
                    }
                )

        # Third-party account links
        if third_party_account_id:
            account_link = self._build_admin_link(
                "view_third_party_account",
                {"third_party_account_id": third_party_account_id, "quickwit": "true"},
            )
            if account_link:
                relevant_links.append(
                    {
                        "title": "Third-Party Account",
                        "url": account_link,
                        "description": "View third-party account details and related devices",
                    }
                )

        return relevant_links

    def _build_admin_link(
        self, page_name: str, query_params: Dict[str, str]
    ) -> Optional[str]:
        """
        Build an admin page URL with query parameters.

        Args:
            page_name: Name of the admin page (e.g., 'view_device')
            query_params: Dict of query parameters

        Returns:
            Complete admin URL or None if page not found
        """
        if not self._admin_pages_data or page_name not in self._admin_pages_data:
            return None

        page_info = self._admin_pages_data[page_name]

        # Check if required parameters are provided
        for required_param in page_info["required_params"]:
            if required_param not in query_params:
                return None

        # ANTI-HALLUCINATION: Only allow known parameters for this page
        valid_param_names = set(param["name"] for param in page_info["query_params"])
        validated_params = {}

        for param_name, param_value in query_params.items():
            if param_name in valid_param_names:
                # Additional validation: ensure non-empty values
                if param_value and str(param_value).strip():
                    validated_params[param_name] = str(param_value).strip()
            # Silently skip invalid parameters to prevent hallucinations

        # Ensure we still have required params after validation
        for required_param in page_info["required_params"]:
            if required_param not in validated_params:
                return None

        # Build query string only with validated parameters
        if validated_params:
            query_string = "&".join([f"{k}={v}" for k, v in validated_params.items()])
            return f"{self.base_admin_url}/{page_name}?{query_string}"
        else:
            return f"{self.base_admin_url}/{page_name}"

    def get_available_pages(self) -> List[str]:
        """Get list of all available admin pages."""
        return list(self._admin_pages_data.keys()) if self._admin_pages_data else []

    def get_page_info(self, page_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific admin page."""
        return self._admin_pages_data.get(page_name) if self._admin_pages_data else None
