# 🔐 Seam Agent

**AI-Powered Customer Support Investigation Assistant**

An intelligent assistant that helps support agents debug customer issues by automatically gathering, analyzing, and presenting relevant data from multiple sources. Built for [Seam](https://www.seam.co/), the API for smart locks and access control.

---

## 🎯 The Problem

Customer support teams spend significant time (30%+ of cases) manually navigating through admin dashboards, job logs, and various data sources to debug customer issues:

- **Multiple clicks** through complex admin interfaces
- **Manual log analysis** with poor search capabilities
- **Time-consuming triangulation** of timestamps across jobs, action attempts, and errors
- **Inability to link** to specific logs, causing duplicated effort
- **Manual timeline reconstruction** for issues reported days/weeks after occurrence

## 💡 The Solution

Seam Agent is an AI orchestrator that instantly gathers, analyzes, and presents debugging information from multiple data sources—reducing manual effort and improving response times from hours to minutes.

```
Support Agent: "What's wrong with device 267ed8d4-3933-4e71-921a-53ce3736879a?"
                                    ↓
                            ┌───────────────┐
                            │  Seam Agent   │
                            │  Orchestrator │
                            └───────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ↓                       ↓                       ↓
    ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
    │   PostgreSQL  │      │   Quickwit    │      │   Seam API    │
    │   Database    │      │     Logs      │      │   Endpoints   │
    └───────────────┘      └───────────────┘      └───────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ↓
                        ┌───────────────────────┐
                        │  Formatted Analysis   │
                        │  + Admin Links        │
                        │  + Next Steps         │
                        └───────────────────────┘
```

---

## ✨ Features

### 🔍 Intelligent Query Parsing
- Extracts device IDs, workspace IDs, access codes, and time references from natural language
- Classifies query types: `device_behavior`, `troubleshooting`, `api_help`, `account_issue`
- Uses GPT-4o-mini for cost-efficient structured extraction

### 🛠️ Dynamic Tool Selection
- Automatically selects relevant investigation tools based on query type
- Supports multi-round tool calling with configurable limits
- Includes follow-up tool recommendations based on initial findings

### 📊 Rich Data Gathering
| Tool | Description |
|------|-------------|
| `get_device_info` | Device properties, status, capabilities, and errors |
| `get_access_codes` | Access codes with managed/unmanaged status |
| `get_action_attempts` | Operation history with success/failure patterns |
| `get_device_events` | Event timeline including connectivity changes |
| `get_audit_logs` | Access code INSERT/DELETE audit trail |
| `get_admin_links` | Generated admin panel URLs for deeper investigation |

### 📝 Formatted Output
Generates structured internal notes with:
- 🔍 Device Analysis summary
- ⚠️ Issue identification
- 📋 Timeline reconstruction
- 🔧 Root cause analysis
- 🎯 Actionable next steps
- 📎 Admin links for follow-up

---

## 🏗️ Architecture

```
src/seam_agent/
├── assistant/                  # Core AI orchestration
│   ├── simple_investigator.py  # Main investigation orchestrator
│   ├── tool_orchestrator.py    # Tool execution and result summarization
│   ├── tool_registry.py        # Maps issue types to required tools
│   ├── dynamic_tool_selector.py # Intelligent tool selection
│   ├── query_parser.py         # LLM-based query parsing
│   ├── prompt_manager.py       # Investigation prompt templates
│   ├── investigation_config.py # Limits and resource management
│   └── investigation_logger.py # Structured logging
├── connectors/                 # Data source integrations
│   ├── db.py                   # PostgreSQL async client
│   ├── quickwit.py             # Quickwit log search client
│   ├── seam_api.py             # Seam REST API client
│   └── admin_links.py          # Admin URL generator
└── integrations/               # External service integrations
    ├── slack.py                # Slack integration (planned)
    └── unthread.py             # Unthread integration (planned)
```

### Key Components

**SimpleInvestigator** — The main entry point that coordinates the entire investigation flow:
1. Parses the support query to extract structured data
2. Calls Claude with available tools based on query type
3. Handles multi-round tool calling with configurable limits
4. Formats findings into a structured support note

**ToolOrchestrator** — Manages tool execution and result processing:
- Executes database queries and API calls
- Summarizes results to preserve critical debugging info
- Caches results to prevent hallucinations in follow-up tools

**DynamicToolSelector** — Intelligently chooses investigation paths:
- Selects initial tools based on parsed query
- Recommends follow-up tools based on findings
- Respects configurable tool calling limits

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL database access (Seam production/staging)
- API keys for Anthropic, OpenAI

### Installation

```bash
# Clone the repository
git clone https://github.com/seamapi/seam-agent.git
cd seam-agent

# Install with uv (recommended)
uv sync
```

### Configuration

Create a `.env` file or export environment variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...      # For Claude (investigation)
OPENAI_API_KEY=sk-...             # For GPT-4o-mini (query parsing)
DATABASE_URL=postgresql://...      # Seam PostgreSQL connection

# Optional
QUICKWIT_URL=http://localhost:7280  # Quickwit log search
QUICKWIT_API_KEY=...               # Quickwit authentication
SEAM_API_KEY=seam_...              # Seam API access
```

### Basic Usage

```python
import asyncio
from seam_agent.assistant.simple_investigator import SimpleInvestigator

async def main():
    investigator = SimpleInvestigator(debug_mode=True)

    result = await investigator.investigate("""
        Hello team!
        We are checking an Igloohome device that does not seem to be
        connected to a bridge, so it only supports offline functionality.
        However, the device response says that it can program online
        access codes. Is that correct?

        Device ID: 267ed8d4-3933-4e71-921a-53ce3736879a
    """)

    # Print formatted investigation
    print(result["investigation"])

    # Export to markdown file
    filename = investigator.export_investigation_to_md(result)
    print(f"Report saved to: {filename}")

asyncio.run(main())
```

---

## 📖 Example Output

```markdown
🔍 **Device Analysis**: Igloohome Device (267ed8d4-3933-4e71-921a-53ce3736879a)

⚠️ **Issue Identified**: Device shows conflicting capability flags - indicates
online access code support while offline and not bridge-connected

📊 **Status**: Under investigation - potential platform capability reporting issue

📋 **Timeline**:
• Device last disconnected: 2025-07-27T13:06:05.495Z
• Last 10 connection reports all show "DEVICE_OFFLINE"
• Device remains offline with no bridge connectivity

🔧 **Root Cause**: System showing `can_program_online_access_codes: true` based
on device model capabilities, but device is offline and not connected to bridge.
Capability flags are not dynamically updated based on actual connectivity status.

🎯 **Next Steps**:
1. **Customer Communication**: Confirm online access codes require bridge
   connectivity - currently only offline codes are functional
2. **Technical Review**: Verify connectivity attempts through admin panel
3. **Platform Escalation**: Consider engineering review of capability flag logic

📎 **Admin Links for Further Investigation:**
- [Device Details](https://connect.getseam.com/admin/view_device?device_id=...)
- [Device Action History](https://connect.getseam.com/admin/view_device_action_attempts?device_id=...)
```

---

## ⚙️ Configuration Options

### Investigation Limits

```python
from seam_agent.assistant.investigation_config import InvestigationConfig

# Production config (conservative)
config = InvestigationConfig.create_production_config()
# MAX_TOOL_ROUNDS: 2
# MAX_TOOLS_PER_ROUND: 3
# MAX_TOTAL_TOOLS: 6

# Debug config (permissive)
config = InvestigationConfig.create_debug_config()
# MAX_TOOL_ROUNDS: 5
# MAX_TOOLS_PER_ROUND: 8
# MAX_TOTAL_TOOLS: 20

# Custom config
config = InvestigationConfig(
    MAX_TOOL_ROUNDS=3,
    MAX_TOOLS_PER_ROUND=5,
    MAX_TOTAL_TOOLS=10,
    TOTAL_INVESTIGATION_TIMEOUT=120
)

investigator = SimpleInvestigator(config=config)
```

### Logging Modes

```python
# Human-readable logs
investigator = SimpleInvestigator(debug_mode=True, log_format="human")

# JSON logs (for parsing)
investigator = SimpleInvestigator(debug_mode=True, log_format="json")
```

---

## 🎮 Running Examples

### Demo Investigation (Mocked)

Run a full investigation demo with mocked external services—no API keys required:

```bash
uv run python demo_investigation.py
```

This demonstrates:
- Dynamic tool selection based on issue type
- Multi-round tool calling with limit enforcement
- Structured analysis and recommendations

### Live Investigation (Requires Credentials)

Run a real investigation against production databases:

```bash
# Single investigation (loads .env automatically)
uv run --env-file .env python -m seam_agent.assistant.simple_investigator

# Or run the test suite with live data
uv run --env-file .env pytest tests/test_investigator_live.py -v -s
```

### Query Parser Demo

Test the LLM-based query parser in isolation:

```bash
uv run --env-file .env python -m seam_agent.assistant.query_parser
```

---

## 🧪 Development

### Running Tests

```bash
# Run unit tests (no credentials needed)
uv run pytest tests/test_dynamic_tool_selector.py tests/test_investigation_config.py -v

# Run all tests with env
uv run --env-file .env pytest

# Run with verbose output
uv run --env-file .env pytest -v

# Run live integration tests (requires credentials)
uv run --env-file .env pytest tests/test_investigator_live.py -v -s
```

### Code Quality

```bash
# Format code
uv run ruff format src tests

# Lint
uv run ruff check src tests

# Fix lint issues automatically
uv run ruff check src tests --fix

# Type checking
uv run pyright src tests
```

---

## 🗺️ Roadmap

- [x] Core investigation orchestration
- [x] PostgreSQL database integration
- [x] Dynamic tool selection
- [x] Configurable investigation limits
- [x] Admin link generation
- [ ] Quickwit log search integration
- [ ] Slack integration for triggering investigations
- [ ] Unthread integration for posting internal notes
- [ ] Timeline reconstruction with event correlation
- [ ] Provider-specific issue detection
- [ ] Proactive alerting for error patterns

---

## 📚 Related Documentation

- [Product Requirements Document](docs/customer-support-agent-prd.md)
- [Customer Conversation Analysis](docs/conversation-analysis.md)
- [Task Tracking](task.md)

---

<p align="center">
  Built with 🤖 by the Seam team
</p>
