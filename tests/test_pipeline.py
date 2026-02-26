"""Tests for pipeline orchestrator — step sequencing and events.

Covers:
- Steps execute in order
- Step skipping (can_skip returns True)
- Event emission (start, complete, skip, error)
- Job status transitions
- Error handling (step raises → job fails, pipeline stops)
- EventBus subscription and delivery
"""

from pathlib import Path

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job, JobStatus
from mediascribe.core.pipeline import Pipeline
from mediascribe.steps.base import PipelineStep, StepResult

# ── Mock Steps ───────────────────────────────────────────────────────────────


class RecordingStep(PipelineStep):
    """A step that records it was called."""

    def __init__(self, step_name: str, skip: bool = False):
        self.name = step_name
        self.description = f"Mock step: {step_name}"
        self._skip = skip
        self.executed = False

    def execute(self, job, settings, events):
        self.executed = True
        return StepResult(data={"step": self.name})

    def can_skip(self, job):
        return self._skip


class FailingStep(PipelineStep):
    name = "fail"
    description = "Always fails"

    def execute(self, job, settings, events):
        raise RuntimeError("Something went wrong")


class StateWritingStep(PipelineStep):
    """Step that writes to job.analysis to test data flow."""

    name = "writer"
    description = "Writes to job"

    def __init__(self, key: str, value: str):
        self._key = key
        self._value = value

    def execute(self, job, settings, events):
        job.analysis[self._key] = self._value
        return StepResult()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_job(tmp_path: Path) -> Job:
    f = tmp_path / "test.mp4"
    f.touch()
    return Job(input_path=f, output_dir=tmp_path / "out")


def _make_pipeline(tmp_path: Path) -> tuple[Pipeline, EventBus, list[PipelineEvent]]:
    events = EventBus()
    log: list[PipelineEvent] = []
    events.subscribe(log.append)
    settings = MediascribeSettings()
    pipeline = Pipeline(settings, events)
    return pipeline, events, log


# ── Tests ────────────────────────────────────────────────────────────────────


class TestStepExecution:
    def test_steps_execute_in_order(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        step_a = RecordingStep("step_a")
        step_b = RecordingStep("step_b")
        step_c = RecordingStep("step_c")

        pipeline.add_step(step_a)
        pipeline.add_step(step_b)
        pipeline.add_step(step_c)

        job = _make_job(tmp_path)
        pipeline.run(job)

        assert step_a.executed
        assert step_b.executed
        assert step_c.executed

    def test_job_completes_on_success(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(RecordingStep("one"))
        job = _make_job(tmp_path)
        result = pipeline.run(job)
        assert result.status == JobStatus.COMPLETED

    def test_data_flows_between_steps(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(StateWritingStep("key1", "value1"))
        pipeline.add_step(StateWritingStep("key2", "value2"))

        job = _make_job(tmp_path)
        pipeline.run(job)

        assert job.analysis["key1"] == "value1"
        assert job.analysis["key2"] == "value2"


class TestStepSkipping:
    def test_skipped_step_not_executed(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        skippable = RecordingStep("skip_me", skip=True)
        pipeline.add_step(skippable)

        job = _make_job(tmp_path)
        pipeline.run(job)

        assert skippable.executed is False

    def test_skip_emits_event(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(RecordingStep("skip_me", skip=True))

        job = _make_job(tmp_path)
        pipeline.run(job)

        skip_events = [e for e in log if e.type == EventType.STEP_SKIPPED]
        assert len(skip_events) == 1
        assert skip_events[0].step_name == "skip_me"

    def test_mixed_skip_and_execute(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        step_a = RecordingStep("run_me")
        step_b = RecordingStep("skip_me", skip=True)
        step_c = RecordingStep("also_run")

        pipeline.add_step(step_a)
        pipeline.add_step(step_b)
        pipeline.add_step(step_c)

        job = _make_job(tmp_path)
        pipeline.run(job)

        assert step_a.executed is True
        assert step_b.executed is False
        assert step_c.executed is True


class TestErrorHandling:
    def test_failing_step_marks_job_failed(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(FailingStep())

        job = _make_job(tmp_path)
        result = pipeline.run(job)

        assert result.status == JobStatus.FAILED
        assert "Something went wrong" in result.error

    def test_failing_step_stops_pipeline(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        before = RecordingStep("before")
        fail = FailingStep()
        after = RecordingStep("after")

        pipeline.add_step(before)
        pipeline.add_step(fail)
        pipeline.add_step(after)

        job = _make_job(tmp_path)
        pipeline.run(job)

        assert before.executed is True
        assert after.executed is False

    def test_error_emits_events(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(FailingStep())

        job = _make_job(tmp_path)
        pipeline.run(job)

        error_events = [e for e in log if e.type == EventType.STEP_ERROR]
        job_error_events = [e for e in log if e.type == EventType.JOB_ERROR]
        assert len(error_events) == 1
        assert len(job_error_events) == 1


class TestEventEmission:
    def test_job_start_and_complete_events(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(RecordingStep("test"))

        job = _make_job(tmp_path)
        pipeline.run(job)

        event_types = [e.type for e in log]
        assert EventType.JOB_START in event_types
        assert EventType.JOB_COMPLETE in event_types

    def test_step_start_and_complete_events(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(RecordingStep("my_step"))

        job = _make_job(tmp_path)
        pipeline.run(job)

        step_starts = [e for e in log if e.type == EventType.STEP_START]
        step_completes = [e for e in log if e.type == EventType.STEP_COMPLETE]
        assert len(step_starts) == 1
        assert step_starts[0].step_name == "my_step"
        assert len(step_completes) == 1

    def test_event_order(self, tmp_path: Path):
        pipeline, events, log = _make_pipeline(tmp_path)
        pipeline.add_step(RecordingStep("step_a"))
        pipeline.add_step(RecordingStep("step_b"))

        job = _make_job(tmp_path)
        pipeline.run(job)

        types = [e.type for e in log]
        # Expected order:
        # JOB_START → STEP_START(a) → STEP_COMPLETE(a) →
        # STEP_START(b) → STEP_COMPLETE(b) → JOB_COMPLETE
        assert types[0] == EventType.JOB_START
        assert types[-1] == EventType.JOB_COMPLETE

        step_types = [e.type for e in log if "step" in e.type.value]
        assert step_types == [
            EventType.STEP_START,
            EventType.STEP_COMPLETE,
            EventType.STEP_START,
            EventType.STEP_COMPLETE,
        ]


class TestEventBus:
    def test_multiple_subscribers(self):
        bus = EventBus()
        log1: list[PipelineEvent] = []
        log2: list[PipelineEvent] = []
        bus.subscribe(log1.append)
        bus.subscribe(log2.append)

        bus.emit(PipelineEvent(type=EventType.LOG, message="test"))
        assert len(log1) == 1
        assert len(log2) == 1

    def test_log_convenience(self):
        bus = EventBus()
        log: list[PipelineEvent] = []
        bus.subscribe(log.append)

        bus.log("hello", step="test")
        assert log[0].type == EventType.LOG
        assert log[0].message == "hello"
        assert log[0].step_name == "test"

    def test_warn_convenience(self):
        bus = EventBus()
        log: list[PipelineEvent] = []
        bus.subscribe(log.append)

        bus.warn("danger", step="test")
        assert log[0].type == EventType.WARNING
        assert log[0].message == "danger"

    def test_no_subscribers_doesnt_crash(self):
        bus = EventBus()
        bus.emit(PipelineEvent(type=EventType.LOG))  # should not raise
        bus.log("hi")
        bus.warn("warning")
