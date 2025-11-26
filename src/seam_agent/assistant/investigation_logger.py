"""
Structured logging system for investigation tracking and debugging.

Provides structured logging with context, timing, and configurable output formats.
"""

import json
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import contextmanager


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class LogContext(Enum):
    INVESTIGATION = "investigation"
    TOOL_EXECUTION = "tool_execution"
    AI_RESPONSE = "ai_response"
    QUERY_PARSING = "query_parsing"
    DATABASE = "database"
    API_CALL = "api_call"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    context: LogContext
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "context": self.context.value,
            "message": self.message,
            "data": self.data,
            "duration_ms": self.duration_ms,
        }


class InvestigationLogger:
    """Structured logger for investigation processes."""

    def __init__(self, debug_mode: bool = False, output_format: str = "human"):
        self.debug_mode = debug_mode
        self.output_format = output_format  # "human", "json", "silent"
        self.entries: List[LogEntry] = []
        self._timers: Dict[str, float] = {}

    def _log(
        self,
        level: LogLevel,
        context: LogContext,
        message: str,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        """Internal logging method."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            context=context,
            message=message,
            data=data or {},
            duration_ms=duration_ms,
        )

        self.entries.append(entry)

        if self.output_format != "silent":
            self._output_entry(entry)

    def _output_entry(self, entry: LogEntry):
        """Output log entry based on format."""
        if self.output_format == "json":
            print(json.dumps(entry.to_dict()))
        elif self.output_format == "human":
            self._output_human_format(entry)

    def _output_human_format(self, entry: LogEntry):
        """Output in human-readable format."""
        # Skip debug logs unless in debug mode
        if entry.level == LogLevel.DEBUG and not self.debug_mode:
            return

        # Format timestamp
        time_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]

        # Choose emoji based on level
        level_emoji = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.SUCCESS: "✅",
        }

        # Format duration if available
        duration_str = f" ({entry.duration_ms:.0f}ms)" if entry.duration_ms else ""

        # Format context
        context_str = f"[{entry.context.value.upper()}]"

        print(
            f"{level_emoji[entry.level]} {time_str} {context_str} {entry.message}{duration_str}"
        )

        # Show data if available and in debug mode
        if entry.data and self.debug_mode:
            for key, value in entry.data.items():
                if isinstance(value, dict) or isinstance(value, list):
                    print(f"    {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"    {key}: {value}")

    # Convenience methods for different log levels
    def debug(
        self,
        message: str,
        context: LogContext = LogContext.INVESTIGATION,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        self._log(LogLevel.DEBUG, context, message, data, duration_ms)

    def info(
        self,
        message: str,
        context: LogContext = LogContext.INVESTIGATION,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        self._log(LogLevel.INFO, context, message, data, duration_ms)

    def warning(
        self,
        message: str,
        context: LogContext = LogContext.INVESTIGATION,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        self._log(LogLevel.WARNING, context, message, data, duration_ms)

    def error(
        self,
        message: str,
        context: LogContext = LogContext.INVESTIGATION,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        self._log(LogLevel.ERROR, context, message, data, duration_ms)

    def success(
        self,
        message: str,
        context: LogContext = LogContext.INVESTIGATION,
        data: Dict[str, Any] | None = None,
        duration_ms: Optional[float] = None,
    ):
        self._log(LogLevel.SUCCESS, context, message, data, duration_ms)

    # Context-specific convenience methods
    def tool_start(self, tool_name: str, input_params: Dict[str, Any]):
        """Log the start of a tool execution."""
        self.info(
            f"Executing tool: {tool_name}",
            LogContext.TOOL_EXECUTION,
            {"tool_name": tool_name, "input_params": input_params},
        )
        self._start_timer(f"tool_{tool_name}")

    def tool_success(
        self, tool_name: str, result_size: int, key_findings: str | None = None
    ):
        """Log successful tool execution."""
        duration = self._end_timer(f"tool_{tool_name}")
        data = {"tool_name": tool_name, "result_size": result_size}
        if key_findings:
            data["key_findings"] = key_findings

        self.success(
            f"Tool '{tool_name}' completed successfully",
            LogContext.TOOL_EXECUTION,
            data,
            duration_ms=duration,
        )

    def tool_error(self, tool_name: str, error: str):
        """Log tool execution error."""
        duration = self._end_timer(f"tool_{tool_name}")
        self.error(
            f"Tool '{tool_name}' failed",
            LogContext.TOOL_EXECUTION,
            {"tool_name": tool_name, "error": error},
            duration_ms=duration,
        )

    def ai_response(self, response_type: str, content_length: int):
        """Log AI response."""
        self.info(
            f"AI {response_type} response received",
            LogContext.AI_RESPONSE,
            {"response_type": response_type, "content_length": content_length},
        )

    def query_parsed(self, parsed_data: Dict[str, Any], confidence: float):
        """Log query parsing result."""
        self.info(
            "Query parsed successfully",
            LogContext.QUERY_PARSING,
            {"parsed_data": parsed_data, "confidence": confidence},
        )

    def investigation_start(self, query: str):
        """Log investigation start."""
        self.info(
            "Investigation started", LogContext.INVESTIGATION, {"query": query[:200]}
        )
        self._start_timer("investigation")

    def investigation_complete(self, analysis_length: int):
        """Log investigation completion."""
        duration = self._end_timer("investigation")
        self.success(
            "Investigation completed",
            LogContext.INVESTIGATION,
            {"analysis_length": analysis_length},
            duration_ms=duration,
        )

    # Timer methods
    def _start_timer(self, timer_name: str):
        """Start a timer for measuring duration."""
        self._timers[timer_name] = time.time()

    def _end_timer(self, timer_name: str) -> Optional[float]:
        """End a timer and return duration in milliseconds."""
        if timer_name in self._timers:
            duration = (time.time() - self._timers[timer_name]) * 1000
            del self._timers[timer_name]
            return duration
        return None

    @contextmanager
    def timer_context(
        self, operation_name: str, context: LogContext = LogContext.INVESTIGATION
    ):
        """Context manager for timing operations."""
        start_time = time.time()
        self.debug(f"Starting {operation_name}", context)
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000
            self.debug(f"Completed {operation_name}", context, duration_ms=duration)

    # Export methods
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the investigation log."""
        total_entries = len(self.entries)
        by_level = {}
        by_context = {}

        for entry in self.entries:
            by_level[entry.level.value] = by_level.get(entry.level.value, 0) + 1
            by_context[entry.context.value] = by_context.get(entry.context.value, 0) + 1

        return {
            "total_entries": total_entries,
            "by_level": by_level,
            "by_context": by_context,
            "start_time": self.entries[0].timestamp.isoformat()
            if self.entries
            else None,
            "end_time": self.entries[-1].timestamp.isoformat()
            if self.entries
            else None,
        }

    def export_json(self) -> str:
        """Export all log entries as JSON."""
        return json.dumps([entry.to_dict() for entry in self.entries], indent=2)

    def clear(self):
        """Clear all log entries."""
        self.entries.clear()
        self._timers.clear()
