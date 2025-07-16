# Customer Support Conversation Analysis

This document analyzes real customer support conversations from `customer-conversations-3-weeks.txt` to identify common patterns and inform the development of the Customer Support AI Assistant.

## Key Problem Categories

Based on the conversations, customer issues can be grouped into five main categories.

### 1. Device & Code Investigation
This is the most common category. Customers frequently need help understanding why a device or access code is not behaving as expected. The AI assistant should excel at these tasks.

*   **Symptoms:**
    *   Access code not setting/working (Conv 9, 11, 33, 38, 45, 67, 78, 91, 100)
    *   Device showing wrong status (e.g., offline, removed) (Conv 4, 9, 12, 15, 41, 72, 77)
    *   Incorrect device behavior (e.g., wrong code length, wrong capabilities) (Conv 7, 67)
    *   Events are missing or incorrect (Conv 4, 26)
*   **Required AI Capabilities:**
    *   Fetch device status & history from PostgreSQL.
    *   Query action attempts for success/failure/error messages.
    *   Search Quickwit logs for detailed error context.
    *   Correlate events across different systems (Seam, Provider).
    *   Compare device properties against documentation or expected values.
*   **Example Conversations:** 4, 9, 11, 15, 16, 22, 23, 31, 41, 42, 43, 44, 45, 59, 65, 67, 68, 69, 72, 74, 76, 77, 87, 91, 95, 97, 100

### 2. Provider-Specific & Integration Issues
Many issues are not with Seam's core platform but are specific to a particular device provider (e.g., Schlage, August, Kwikset) or a partner integration.

*   **Symptoms:**
    *   Provider-side outages or bugs (Conv 15, 23, 29, 34, 35, 60, 74, 76)
    *   Beta integration instability (Conv 6)
    *   Partner integration failures (Conv 21, 53)
*   **Required AI Capabilities:**
    *   Access a knowledge base of known provider issues (Notion).
    *   Check for ongoing incidents or outages.
    *   Provide status on beta integrations.
    *   Suggest workarounds when the issue is external.
*   **Example Conversations:** 6, 15, 21, 23, 29, 34, 35, 53, 55, 59, 60, 74, 76

### 3. Developer & API Support
A significant portion of support involves developers asking questions about how to use the Seam API or SDKs.

*   **Symptoms:**
    *   Confusion about API parameters or behavior (Conv 20, 51, 56, 58, 66)
    *   Bugs or unexpected behavior in the API/SDK (Conv 16, 28, 82, 90)
    *   Questions about documentation (Conv 54)
    *   Setup/authentication issues (Conv 27, 93)
*   **Required AI Capabilities:**
    *   Index and search all of `docs.seam.co`.
    *   Provide code examples for common API uses.
    *   Explain deprecated fields and suggest alternatives.
    *   Retrieve API responses for specific calls to help debug.
*   **Example Conversations:** 16, 20, 27, 28, 40, 51, 54, 56, 58, 66, 82, 90, 93

### 4. Simple Information Retrieval
These are straightforward questions that can be answered with a quick lookup. These are easy wins for an AI assistant.

*   **Symptoms:**
    *   "Is device X supported?" (Conv 2, 14, 25, 88)
    *   "What is the status of integration Y?" (Conv 30, 46, 49)
    *   Questions about pricing or billing logic (Conv 1, 17)
*   **Required AI Capabilities:**
    *   Query a supported devices list.
    *   Check the status of integrations in a knowledge base.
    *   Access billing/pricing documentation.
*   **Example Conversations:** 1, 2, 14, 17, 25, 30, 46, 49, 88

### 5. Account & Configuration Issues
These problems relate to account setup, configuration, or limits.

*   **Symptoms:**
    *   Device conflicts between accounts (Conv 10)
    *   Hitting usage limits (e.g., codes, users) (Conv 44, 50)
    *   Sandbox environment issues (Conv 80)
    *   Frequent account disconnections (Conv 71)
*   **Required AI Capabilities:**
    *   Query database for account and device ownership.
    *   Check device/user counts against limits.
    *   Provide guidance on resolving conflicts.
*   **Example Conversations:** 10, 44, 50, 71, 80, 85 