"""Pipeline orchestrator — sequences steps, manages jobs, emits events."""

from __future__ import annotations

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, JobStatus
from mediascribe.steps.base import PipelineStep


class Pipeline:
    """Orchestrates a sequence of steps over one or more jobs.

    Usage:
        pipeline = Pipeline(settings, event_bus)
        pipeline.add_step(DetectStep())
        pipeline.add_step(NormalizeStep())
        pipeline.add_step(TranscribeStep())
        pipeline.add_step(TranslateStep())

        for job in jobs:
            await pipeline.run(job)
    """

    def __init__(self, settings: MediascribeSettings, events: EventBus) -> None:
        self.settings = settings
        self.events = events
        self._steps: list[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> None:
        """Register a step to the pipeline."""
        self._steps.append(step)

    async def run(self, job: Job) -> Job:
        """Execute all steps on a single job."""
        job.status = JobStatus.RUNNING
        self.events.emit(PipelineEvent(
            type=EventType.JOB_START,
            message=f"Processing {job.input_path.name}",
            data={"input": str(job.input_path)},
        ))

        for step in self._steps:
            if not step.required and step.can_skip(job):
                self.events.emit(PipelineEvent(
                    type=EventType.STEP_SKIPPED,
                    step_name=step.name,
                    message=f"Skipping {step.name} — output exists",
                ))
                continue

            if step.can_skip(job):
                self.events.emit(PipelineEvent(
                    type=EventType.STEP_SKIPPED,
                    step_name=step.name,
                    message=f"Skipping {step.name} — output exists",
                ))
                continue

            job.current_step = step.name
            self.events.emit(PipelineEvent(
                type=EventType.STEP_START,
                step_name=step.name,
                message=f"Starting {step.name}: {step.description}",
            ))

            try:
                result = await step.execute(job, self.settings, self.events)
                self.events.emit(PipelineEvent(
                    type=EventType.STEP_COMPLETE,
                    step_name=step.name,
                    message=f"Completed {step.name}",
                    data=result.data if result else {},
                ))
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                self.events.emit(PipelineEvent(
                    type=EventType.STEP_ERROR,
                    step_name=step.name,
                    message=f"Error in {step.name}: {exc}",
                ))
                self.events.emit(PipelineEvent(
                    type=EventType.JOB_ERROR,
                    message=f"Job failed: {exc}",
                ))
                return job

        job.status = JobStatus.COMPLETED
        job.current_step = None
        self.events.emit(PipelineEvent(
            type=EventType.JOB_COMPLETE,
            message=f"Done: {job.input_path.name}",
        ))
        return job
