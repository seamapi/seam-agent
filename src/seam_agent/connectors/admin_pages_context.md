# Admin View Pages and Query Parameters

This document lists all admin view pages in the Seam Connect application and their query parameters.

## Main Admin View Pages

### view_device.tsx
**Purpose**: View detailed information about a specific device
**Query Parameters**:
- `device_id` (optional string) - The device ID to view
- `third_party_device_id` (optional string) - Third party device identifier
- `include_requests` (optional boolean) - Whether to include request data
- `access_code_limit` (optional positive integer) - Limit for access codes displayed
- `access_code_offset` (optional integer) - Offset for access code pagination
- `skip_sections` (optional string) - Comma-separated list of sections to skip
- `quickwit` (optional string, transforms to boolean) - Use Quickwit for logs
- `test_quickwit` (optional string, transforms to boolean) - Test Quickwit functionality

### view_action_attempt.tsx
**Purpose**: View action attempts with filtering capabilities
**Query Parameters**:
- `workspace_id` (optional string) - Filter by workspace
- `status` (optional string) - Filter by attempt status
- `device_id` (optional string) - Filter by device
- `action_type` (optional string) - Filter by action type
- `error_type` (optional string) - Filter by error type
- `action_attempt_id` (optional string) - View specific attempt
- `page` (optional string) - Page number for pagination
- `quickwit` (optional string, transforms to boolean) - Use Quickwit for logs

### view_third_party_account.tsx
**Purpose**: View third party account details and related data
**Query Parameters**:
- `third_party_account_id` (required string) - The account ID to view
- `third_party_devices_page` (optional string) - Page for devices listing
- `jobs_with_relevant_device_page` (optional string) - Page for relevant device jobs
- `jobs_with_third_party_account_id_page` (optional string) - Page for account-specific jobs
- `quickwit` (optional string, transforms to boolean) - Use Quickwit for logs
- `test_quickwit` (optional string, transforms to boolean) - Test Quickwit functionality

### view_job.tsx
**Purpose**: View job details and logs
**Query Parameters**:
- `id` (optional string) - Job ID
- `job_log_id` (optional string) - Job log ID
- `start_time` (optional datetime string, transforms to DateTime) - Job start time filter
- `end_time` (optional datetime string, transforms to DateTime) - Job end time filter
- `job_time` (optional datetime string, transforms to DateTime) - Specific job time

### view_workspace.tsx
**Purpose**: View workspace details, members, and API keys
**Query Parameters**:
- `workspace_id` (required string) - The workspace ID to view

### view_user.tsx
**Purpose**: View user details and associated workspaces
**Query Parameters**:
- `user_id` (required string) - The user ID to view

### view_access_code.tsx
**Purpose**: View access code details and audit logs
**Query Parameters**:
- `access_code_id` (required string) - The access code ID to view
- `quickwit` (optional string, transforms to boolean) - Use Quickwit for logs

### view_devices.tsx
**Purpose**: List devices with filtering and pagination
**Query Parameters**:
- `workspace_id` (optional string) - Filter by workspace
- `device_type` (optional string) - Filter by device type
- `page` (optional string) - Page number for pagination

### view_access_codes.tsx
**Purpose**: List access codes with filtering
**Query Parameters**:
- `workspace_id` (optional string) - Filter by workspace
- `common_code_key` (optional string) - Filter by common code key
- `provider` (optional string) - Filter by provider
- `include_sandbox` (optional string) - Include sandbox codes
- `created_since` (optional string) - Filter by creation date

### view_third_party_accounts.tsx
**Purpose**: List third party accounts with filtering
**Query Parameters**:
- `workspace_id` (optional string) - Filter by workspace
- `account_type` (optional string) - Filter by account type
- `page` (optional string) - Page number for pagination

### view_bridges.tsx
**Purpose**: View bridge client sessions and bridge information
**Query Parameters**:
- `workspace_ids` (optional array of strings) - Filter by workspace IDs

### view_connect_webview.tsx
**Purpose**: View connect webview details
**Query Parameters**:
- `connect_webview_id` (required string) - The webview ID to view

### view_user_identity.tsx
**Purpose**: View user identity details
**Query Parameters**:
- `user_identity_id` (required string) - The user identity ID to view

### view_phone_sdk_installation.tsx
**Purpose**: View phone SDK installation details
**Query Parameters**:
- `phone_sdk_installation_id` (required string) - The installation ID to view
- `test_quickwit` (optional string, transforms to boolean) - Test Quickwit functionality
- `custom_sdk_installation_id` (optional string) - Custom SDK installation ID
- `workspace_id` (optional string) - Associated workspace ID

### view_event.tsx
**Purpose**: View events with comprehensive filtering
**Query Parameters**:
- `workspace_id` (optional string) - Filter by workspace
- `device_id` (optional string) - Filter by device
- `event_type` (optional string) - Filter by event type
- `third_party_account_id` (optional string) - Filter by third party account
- `connect_webview_id` (optional string) - Filter by connect webview
- `access_code_id` (optional string) - Filter by access code
- `event_id` (optional string) - View specific event

### view_api_key.tsx
**Purpose**: View API key details and configuration
**Query Parameters**:
- `api_key_id` (required string) - The API key ID to view

### view_client_session.tsx
**Purpose**: View client session details
**Query Parameters**:
- `client_session_id` (required string) - The client session ID to view

### view_deleted_access_codes.tsx
**Purpose**: View audit log of deleted access codes
**Query Parameters**:
- `device_id` (optional string) - Filter by device
- `workspace_id` (optional string) - Filter by workspace
- **Note**: One of device_id or workspace_id is required

### view_global_connected_accounts.tsx
**Purpose**: View global connected accounts with deduplication features
**Query Parameters**:
- `only_duplicates` (optional string) - Show only duplicate accounts
- `connected_accounts_page` (optional string) - Page number for pagination

### view_webhooks.tsx
**Purpose**: View webhooks for a workspace
**Query Parameters**:
- `workspace_id` (optional string) - The workspace ID (required for viewing webhooks)

### view_workspace_invitations.tsx
**Purpose**: View workspace invitations
**Query Parameters**:
- `workspace_id` (optional string) - The workspace ID (required for viewing invitations)

### view_sandbox_workspace_state.tsx
**Purpose**: View sandbox workspace state and configuration
**Query Parameters**:
- `workspace_id` (optional string) - The workspace ID (required for viewing state)

### find_by_uuid.tsx
**Purpose**: Search for entities by UUID across all tables
**Query Parameters**:
- `workspace_id` (optional string) - Scope search to workspace
- `uuid` (optional UUID string) - The UUID to search for

### all_workspaces.tsx
**Purpose**: List all workspaces
**Query Parameters**:
- `include_sandbox` (optional string) - Include sandbox workspaces

### view_feature_flags.tsx
**Purpose**: View and manage feature flags
**Query Parameters**:
- No query parameters (uses formData only)

### view_sla_metrics.tsx
**Purpose**: View SLA metrics
**Query Parameters**:
- No query parameters (uses formData only)

## ACS (Access Control System) View Pages

### acs/view_acs_credentials.tsx
**Purpose**: View ACS credentials for a system
**Query Parameters**:
- `acs_system_id` (required UUID string) - The ACS system ID

### acs/view_acs_system.tsx
**Purpose**: View ACS system details and configuration
**Query Parameters**:
- `acs_system_id` (required UUID string) - The ACS system ID
- `workspace_id` (optional UUID string) - Associated workspace ID

## Salto Integration View Pages

### salto/view_salto_workspace.tsx
**Purpose**: View Salto workspace integration details
**Query Parameters**:
- `workspace_id` (required string) - The workspace ID

## Additional Specialized View Pages

### view_thermostat_details.tsx
**Purpose**: View thermostat device details and schedules
**Query Parameters**:
- `device_id` (string) - The thermostat device ID
- `thermostat_schedule_id` (string) - The schedule ID

### view_access_code_logs.tsx
**Purpose**: View access code audit logs
**Query Parameters**:
- `access_code_id` (string) - The access code ID
- `starting_at` (string) - Starting timestamp for logs

### view_device_action_attempts.tsx
**Purpose**: View action attempts for a specific device
**Query Parameters**:
- `device_id` (string) - The device ID
- `starting_at` (string) - Starting timestamp for attempts

### view_phone_registrations.tsx
**Purpose**: View phone registrations for ACS system
**Query Parameters**:
- `acs_system_id` (string) - The ACS system ID

### view_phone_registration.tsx
**Purpose**: View specific phone registration details
**Query Parameters**:
- `phone_registration_id` (string) - The phone registration ID

### view_user_identities.tsx
**Purpose**: View user identities for a workspace
**Query Parameters**:
- `workspace_id` (string) - The workspace ID

### view_workspace_bridges.tsx
**Purpose**: View bridges for a specific workspace
**Query Parameters**:
- `workspace_id` (string) - The workspace ID

### view_request.tsx
**Purpose**: View specific request details
**Query Parameters**:
- `request_id` (string) - The request ID

### view_metadata.tsx
**Purpose**: View metadata for a workspace
**Query Parameters**:
- `workspace_id` (string) - The workspace ID

### view_playwright_trace.tsx
**Purpose**: View Playwright test traces
**Query Parameters**:
- `playwright_trace_id` (string) - The trace ID

### view_access_code_public_log.tsx
**Purpose**: View public access code logs
**Query Parameters**:
- `access_code_id` (string) - The access code ID

### view_access_code_corresponding_managed_code.tsx
**Purpose**: View managed code corresponding to access code
**Query Parameters**:
- `access_code_id` (string) - The access code ID

### view_workspace_table_counts.tsx
**Purpose**: View table counts and statistics for workspace
**Query Parameters**:
- `workspace_id` (string) - The workspace ID
- `report_schemas_only` (string) - Show only schema reports

### view_third_party_devices.tsx
**Purpose**: View third party devices for workspace
**Query Parameters**:
- `workspace_id` (string) - The workspace ID

### view_connected_accounts_duplicate_group.tsx
**Purpose**: View duplicate connected account groups
**Query Parameters**:
- `workspace_id` (string) - The workspace ID
- `account_type` (string) - The account type
- `user_identifier` (JSON string) - User identifier data

### view_disconnected_accounts.tsx
**Purpose**: View disconnected accounts
**Query Parameters**:
- `workspace_id` (string) - The workspace ID
- `account_type` (string) - The account type

### view_devices_experimental_supported_code_length.tsx
**Purpose**: View devices with experimental code length support
**Query Parameters**:
- `workspace_id` (string) - The workspace ID
- `page_num` (number, default 1) - Page number
- `page_size` (number, default 50) - Items per page
- `device_type` (string) - Filter by device type

### view_devices_missmatched_capability_flags_and_state.tsx
**Purpose**: View devices with mismatched capability flags
**Query Parameters**:
- `workspace_id` (string) - The workspace ID
- `page` (string) - Page number
- `limit` (string) - Items per page limit

### view_queue.tsx
**Purpose**: View job queue details
**Query Parameters**:
- `queue_name` (string) - The queue name

## Common Parameter Patterns

### Boolean Parameters
Many pages use string parameters that are transformed to booleans:
- `quickwit`: Typically transforms "true" or "1" to boolean true
- `test_quickwit`: Similar boolean transformation
- `include_sandbox`: String "true" becomes boolean true

### Pagination Parameters
Common pagination patterns:
- `page`: String representation of page number
- `page_num`: Numeric page number with default
- `page_size`: Items per page with default
- `limit`: Maximum items to return
- `offset`: Starting position for results

### ID Parameters
Most ID parameters are strings, with some requiring UUID format:
- Required IDs: Must be provided for the page to function
- Optional IDs: Used for filtering when provided
- UUID validation: Some IDs require valid UUID format

### Workspace Scoping
Many pages support workspace-scoped viewing:
- `workspace_id`: Most common parameter for scoping data to a workspace
- Some pages require workspace_id, others make it optional for admin users

## Usage Notes

1. **Authentication**: All pages require either "support" or "admin" authentication levels
2. **Parameter Validation**: Most pages use Zod schemas for parameter validation
3. **Pagination**: Many list views support pagination with various parameter names
4. **Filtering**: Most list views support multiple filtering options
5. **Logging Integration**: Many pages support Quickwit integration for enhanced logging
6. **Admin vs Support**: Some pages have different behavior based on admin vs support user roles
