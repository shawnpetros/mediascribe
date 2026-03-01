"""Analyze step — AI-powered post-processing of transcriptions.

Uses the OpenAI chat API to generate:
- A concise summary of the content
- Key topics/themes extracted from the transcript
- Action items (for meeting recordings)

Results are stored in ``job.analysis`` for downstream export (JSON, etc.).
"""

from __future__ import annotations

import json
import re
import textwrap

from mediascribe.core.config import MediascribeSettings
from mediascribe.core.events import EventBus
from mediascribe.core.job import Job
from mediascribe.models.openai_client import get_client
from mediascribe.steps.base import PipelineStep, StepResult

ANALYSIS_PROMPT = textwrap.dedent("""\
    You are an expert content analyst. You will receive a transcript of an
    audio or video recording. Analyze it and return a JSON object with:

    {{
      "summary": "A concise 2-4 sentence summary of the content.",
      "topics": ["topic1", "topic2", ...],
      "action_items": ["action1", "action2", ...],
      "key_points": ["point1", "point2", ...]
    }}

    Rules:
    - summary: Clear, concise, captures the main point.
    - topics: 3-10 key topics/themes discussed.
    - action_items: Any follow-up tasks, decisions, or commitments mentioned.
      Return an empty list if none.
    - key_points: 3-8 important points or takeaways.
    {custom_instructions}

    Return ONLY the JSON object, no markdown fences, no explanation.
""")

MAX_TRANSCRIPT_CHARS = 30000


class AnalyzeStep(PipelineStep):
    """AI analysis of transcript content.

    Sends the full transcript (or a truncated version for very long
    recordings) to the AI for summarization, topic extraction, and
    action item detection. Results are stored in ``job.analysis``.
    """

    name = "analyze"
    description = "Analyzing content"
    required = False

    def execute(
        self,
        job: Job,
        settings: MediascribeSettings,
        events: EventBus,
    ) -> StepResult:
        if not job.segments:
            events.warn("No segments to analyze", step=self.name)
            return StepResult(data={"skipped": True, "reason": "no segments"})

        api_key: str | None = None
        if settings.openai_api_key:
            api_key = settings.openai_api_key.get_secret_value()

        try:
            client = get_client(api_key)
        except Exception as exc:
            events.warn(f"Cannot initialize API client: {exc}", step=self.name)
            return StepResult(data={"skipped": True, "reason": "no API key"})

        # Build transcript text for analysis
        lines = []
        for seg in job.segments:
            text = seg.translation or seg.text
            speaker = f"[{seg.speaker}] " if seg.speaker else ""
            lines.append(f"{speaker}{text}")

        transcript = "\n".join(lines)

        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            events.log(
                f"Transcript truncated from {len(transcript)} to {MAX_TRANSCRIPT_CHARS} chars",
                step=self.name,
            )
            transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n[... truncated ...]"

        ci = settings.custom_instructions
        ci_block = f"\nAdditional instructions:\n{ci}" if ci else ""
        system_prompt = ANALYSIS_PROMPT.format(custom_instructions=ci_block)

        events.log(f"Model: {settings.translation_model}", step=self.name)
        events.log(f"Analyzing {len(job.segments)} segments...", step=self.name)

        try:
            resp = client.responses.create(
                model=settings.translation_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                max_output_tokens=2000,
                temperature=0.3,
            )

            raw = resp.output_text.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            analysis = json.loads(raw)
        except Exception as exc:
            events.warn(f"Analysis parse error: {exc}", step=self.name)
            analysis = {
                "summary": "Analysis failed — could not parse AI response.",
                "topics": [],
                "action_items": [],
                "key_points": [],
                "error": str(exc),
            }

        job.analysis = analysis

        summary_preview = analysis.get("summary", "")[:80]
        topic_count = len(analysis.get("topics", []))
        action_count = len(analysis.get("action_items", []))
        events.log(
            f"Summary: {summary_preview}...",
            step=self.name,
        )
        events.log(
            f"Found {topic_count} topics, {action_count} action items",
            step=self.name,
        )

        return StepResult(
            data={
                "topic_count": topic_count,
                "action_item_count": action_count,
                "has_summary": bool(analysis.get("summary")),
            }
        )

    def can_skip(self, job: Job) -> bool:
        return bool(job.analysis.get("summary"))
