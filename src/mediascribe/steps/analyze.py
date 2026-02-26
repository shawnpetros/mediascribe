"""Analyze step — AI-powered post-processing of transcriptions.

Generates structured analysis of transcribed content:
- Summary generation
- Topic/theme extraction
- Action item detection (for meetings)
- Key quotes / highlights

Uses the same OpenAI client as the translation pipeline.
"""

from __future__ import annotations

import json

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus, EventType, PipelineEvent
from mediascribe.core.job import Job
from mediascribe.models.openai_client import get_client
from mediascribe.steps.base import PipelineStep, StepResult

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert content analyst. Analyze the following transcript and produce a structured analysis.

Return a JSON object with these fields:
{
  "summary": "A concise 2-4 sentence summary of the content.",
  "topics": ["topic1", "topic2", ...],
  "key_points": ["point1", "point2", ...],
  "action_items": ["item1", "item2", ...],
  "sentiment": "overall sentiment (positive/negative/neutral/mixed)",
  "word_count": <approximate word count of transcript>
}

Rules:
- Topics should be specific, not generic.
- Key points capture the most important information.
- Action items are only for meetings/discussions; use an empty list if not applicable.
- Be concise. Each string should be 1-2 sentences max.
{custom_instructions}

Return ONLY the JSON object, no markdown, no explanation.
"""


def analyze_transcript(
    transcript_text: str,
    model: str,
    api_key: str | None = None,
    custom_instructions: str = "",
) -> dict:
    """Analyze a transcript and return structured analysis."""
    client = get_client(api_key)

    ci_block = f"\nAdditional instructions:\n{custom_instructions}" if custom_instructions else ""
    system_prompt = ANALYSIS_SYSTEM_PROMPT.format(custom_instructions=ci_block)

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript_text},
        ],
        max_output_tokens=1500,
        temperature=0.3,
    )

    import re
    raw = resp.output_text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class AnalyzeStep(PipelineStep):
    """Post-processing analysis of transcribed content.

    Sends the full transcript to an AI model for structured analysis
    including summary, topics, key points, and action items.

    Populates job.analysis with the results.
    """

    name = "analyze"
    description = "Analyzing transcript content"
    required = False

    def execute(
        self, job: Job, settings: MediascribeSettings, events: EventBus,
    ) -> StepResult:
        if not job.segments:
            events.warn("No segments to analyze", step=self.name)
            return StepResult(data={"skipped": True})

        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key else None
        )

        transcript_lines = []
        for seg in job.segments:
            text = seg.translation if seg.translation else seg.text
            prefix = f"[{seg.speaker}] " if seg.speaker else ""
            transcript_lines.append(f"{prefix}{text}")

        transcript_text = "\n".join(transcript_lines)

        if len(transcript_text) < 50:
            events.warn("Transcript too short for meaningful analysis", step=self.name)
            return StepResult(data={"skipped": True, "reason": "too_short"})

        events.emit(PipelineEvent(
            type=EventType.STEP_PROGRESS,
            step_name=self.name,
            message="Sending transcript for analysis",
            progress=0.3,
        ))

        events.log(f"Model: {settings.translation_model}", step=self.name)

        try:
            analysis = analyze_transcript(
                transcript_text=transcript_text,
                model=settings.translation_model,
                api_key=api_key,
                custom_instructions=settings.custom_instructions,
            )
        except (json.JSONDecodeError, Exception) as e:
            events.warn(f"Analysis failed: {e}", step=self.name)
            return StepResult(success=False, message=str(e))

        job.analysis = analysis

        summary = analysis.get("summary", "")
        topics = analysis.get("topics", [])
        events.log(
            f"Summary: {summary[:80]}{'...' if len(summary) > 80 else ''}",
            step=self.name,
        )
        events.log(f"Topics: {', '.join(topics[:5])}", step=self.name)

        return StepResult(data={
            "summary_length": len(summary),
            "topic_count": len(topics),
            "action_item_count": len(analysis.get("action_items", [])),
        })

    def can_skip(self, job: Job) -> bool:
        """Skip if analysis already exists."""
        return bool(job.analysis)
