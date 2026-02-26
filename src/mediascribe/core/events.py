"""Event system for pipeline → UI communication.

Pipeline steps emit events; the UI layer (CLI/TUI) consumes them.
This decouples the pipeline from any specific UI implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of events the pipeline can emit."""

    # Step lifecycle
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    STEP_SKIPPED = "step_skipped"
    STEP_ERROR = "step_error"

    # Job lifecycle
    JOB_START = "job_start"
    JOB_COMPLETE = "job_complete"
    JOB_ERROR = "job_error"

    # Informational
    LOG = "log"
    WARNING = "warning"


@dataclass
class PipelineEvent:
    """A single event emitted during pipeline execution."""

    type: EventType
    step_name: str | None = None
    message: str = ""
    progress: float = 0.0  # 0.0 → 1.0
    data: dict[str, Any] = field(default_factory=dict)


# Type alias for event handlers
EventHandler = Callable[[PipelineEvent], None]


class EventBus:
    """Simple event bus for pipeline → UI communication."""

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)

    def emit(self, event: PipelineEvent) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._handlers:
            handler(event)

    def log(self, message: str, step: str | None = None) -> None:
        """Convenience: emit a LOG event."""
        self.emit(PipelineEvent(type=EventType.LOG, step_name=step, message=message))

    def warn(self, message: str, step: str | None = None) -> None:
        """Convenience: emit a WARNING event."""
        self.emit(PipelineEvent(type=EventType.WARNING, step_name=step, message=message))
