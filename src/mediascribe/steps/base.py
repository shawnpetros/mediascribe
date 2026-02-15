"""Abstract base class for pipeline steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job


@dataclass
class StepResult:
    """Result returned by a step after execution."""

    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""


class PipelineStep(ABC):
    """Base class for all pipeline steps.

    Each step:
    - Has a name and description
    - Can check whether it can be skipped (idempotency)
    - Executes work and returns a StepResult
    - Emits progress events via the EventBus
    - Can optionally estimate its duration

    Steps are synchronous. For TUI use, the pipeline orchestrator
    runs in a background thread while the event bus bridges to the UI.
    """

    name: str
    description: str
    required: bool = True  # If False, step can be configured off

    @abstractmethod
    def execute(
        self,
        job: Job,
        settings: MediascribeSettings,
        events: EventBus,
    ) -> StepResult:
        """Execute this step on the given job.

        Args:
            job: The job being processed (read input, write results).
            settings: Application configuration.
            events: Event bus for progress reporting.

        Returns:
            StepResult with success status and any output data.
        """
        ...

    def can_skip(self, job: Job) -> bool:
        """Return True if this step's output already exists.

        Override in subclasses to enable idempotent re-runs.
        Default: never skip.
        """
        return False

    def estimate_duration(self, job: Job) -> float | None:
        """Estimate how long this step will take (seconds).

        Returns None if estimation is not possible.
        Override in subclasses with hardware-aware estimates.
        """
        return None
