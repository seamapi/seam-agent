---
trigger: model_decision
description: Use this when editing any python files. This describes data modeling and structure.
globs:
---
# Seam Agent Coding Rules

This document outlines the coding standards and best practices for the Seam Agent project.

## 1. Data Modeling with Pydantic

**Rule:** All data models, schemas, and configuration objects MUST be implemented using `pydantic`.

**Rationale:** `pydantic` provides runtime type checking, data validation, and serialization, which is critical for building robust and reliable integrations with external APIs and data sources. It ensures that the data flowing through the system is always well-formed.

**Example:**

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class DeviceInfo(BaseModel):
    device_id: str = Field(..., description="The unique identifier for the device.")
    display_name: str
    is_online: bool
    errors: List[str] = []

class AnalysisResult(BaseModel):
    device_info: DeviceInfo
    summary: str
    timeline: List[str]
    root_cause: Optional[str] = None
```

## 2. Tool Creation with FastMCP

**Rule:** All functions intended to be used by the AI assistant MUST be exposed as tools using the `FastMCP` framework.

**Rationale:** `FastMCP` provides a standardized, safe, and discoverable way to expose Python functions to an LLM. It handles the protocol complexities, allowing us to focus on the tool's logic. This ensures that the AI's capabilities are well-defined, versioned, and secure.

**Example:**

```python
from fastmcp import FastMCP
from .models import DeviceInfo

mcp = FastMCP(name="SeamSupportTools")

@mcp.tool
def get_device_status(device_id: str) -> DeviceInfo:
    """
    Retrieves the current status and details for a given device ID.
    """
    # ... implementation to query PostgreSQL or Seam API ...
    return DeviceInfo(...)
```

## 3. Configuration Management

**Rule:** Application configuration (API keys, database URIs, etc.) SHOULD be managed via `pydantic`'s `BaseSettings`.

**Rationale:** Using `pydantic` for settings management allows for type-safe configuration that can be loaded from environment variables or `.env` files, providing a consistent and reliable way to configure the application in different environments.

## 4. Code Style and Linting

**Rule:** All code MUST adhere to the formatting standards enforced by `ruff` and pass all linter checks.

**Rationale:** A consistent code style improves readability and maintainability. `ruff` is used as an all-in-one linter and formatter to ensure consistency across the project. Pre-commit hooks should be used to enforce this automatically. # Seam Agent Coding Rules

This document outlines the coding standards and best practices for the Seam Agent project.

## 1. Data Modeling with Pydantic

**Rule:** All data models, schemas, and configuration objects MUST be implemented using `pydantic`.

**Rationale:** `pydantic` provides runtime type checking, data validation, and serialization, which is critical for building robust and reliable integrations with external APIs and data sources. It ensures that the data flowing through the system is always well-formed.

**Example:**

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class DeviceInfo(BaseModel):
    device_id: str = Field(..., description="The unique identifier for the device.")
    display_name: str
    is_online: bool
    errors: List[str] = []

class AnalysisResult(BaseModel):
    device_info: DeviceInfo
    summary: str
    timeline: List[str]
    root_cause: Optional[str] = None
```

## 2. Tool Creation with FastMCP

**Rule:** All functions intended to be used by the AI assistant MUST be exposed as tools using the `FastMCP` framework.

**Rationale:** `FastMCP` provides a standardized, safe, and discoverable way to expose Python functions to an LLM. It handles the protocol complexities, allowing us to focus on the tool's logic. This ensures that the AI's capabilities are well-defined, versioned, and secure.

**Example:**

```python
from fastmcp import FastMCP
from .models import DeviceInfo

mcp = FastMCP(name="SeamSupportTools")

@mcp.tool
def get_device_status(device_id: str) -> DeviceInfo:
    """
    Retrieves the current status and details for a given device ID.
    """
    # ... implementation to query PostgreSQL or Seam API ...
    return DeviceInfo(...)
```

## 3. Configuration Management

**Rule:** Application configuration (API keys, database URIs, etc.) SHOULD be managed via `pydantic`'s `BaseSettings`.

**Rationale:** Using `pydantic` for settings management allows for type-safe configuration that can be loaded from environment variables or `.env` files, providing a consistent and reliable way to configure the application in different environments.

## 4. Code Style and Linting

**Rule:** All code MUST adhere to the formatting standards enforced by `ruff` and pass all linter checks.

**Rationale:** A consistent code style improves readability and maintainability. `ruff` is used as an all-in-one linter and formatter to ensure consistency across the project. Pre-commit hooks should be used to enforce this automatically.
