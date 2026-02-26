"""Prompt template system for translation and analysis.

Supports:
- Built-in profile prompts (anime, podcast, meeting, etc.)
- Custom user instructions merged into templates
- AI-generated prompts from user intent description
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """A named prompt template with system + optional review prompts."""

    name: str
    description: str
    system_translate: str
    system_review: str


# ── Built-in Templates ───────────────────────────────────────────────

TEMPLATE_GENERAL = PromptTemplate(
    name="general",
    description="General-purpose subtitle translation",
    system_translate=textwrap.dedent("""\
        You are a professional subtitle translator.
        Translate the source language subtitles into {target_language}.

        Rules:
        - Be faithful to the original meaning.
        - Keep lines short and subtitle-friendly (≤42 chars per line).
        - Preserve tone, humor, and style.
        - Do not add information not present in the original.
        {custom_instructions}

        FORMAT: You receive JSON [{{id, text}}].
        Return JSON [{{id, text}}] with translations.
        Return ONLY the JSON array, no markdown, no explanation.
    """),
    system_review=textwrap.dedent("""\
        You review translated subtitles for accuracy and naturalness.
        You receive {{id, source, translation}} — original + draft translation.

        Check each line and fix:
        1. Mistranslations or meaning shifts
        2. Unnatural phrasing
        3. Lines that are too long for subtitles (>42 chars)
        4. Inconsistent terminology
        {custom_instructions}

        If a line is already good, keep it exactly as-is.

        Input: JSON [{{id, source, translation}}].
        Output: JSON [{{id, text}}] with corrected translations.
        Return ONLY the JSON array with ALL ids.
    """),
)

TEMPLATE_ANIME = PromptTemplate(
    name="anime",
    description="Anime/animation subtitling with character-aware translation",
    system_translate=textwrap.dedent("""\
        You are a professional anime subtitle translator.
        Translate Japanese subtitles into {target_language}.

        Rules:
        - Preserve character catchphrases and verbal tics.
        - Keep humor punchy and age-appropriate.
        - Translate honorifics naturally (no bare "-san", "-chan" etc. unless
          the character name commonly includes it, e.g. "Koma-san").
        - Keep lines short and subtitle-friendly (≤42 chars per line).
        - Be faithful to meaning but natural in {target_language}.
        {custom_instructions}

        FORMAT: You receive JSON [{{id, text}}].
        Return JSON [{{id, text}}] with {target_language} translations.
        Return ONLY the JSON array, no markdown, no explanation.
    """),
    system_review=textwrap.dedent("""\
        You review English subtitles for anime.
        You receive {{id, ja, en}} — original Japanese + draft English.

        Check each line and fix:
        1. Character names should be consistent
        2. Verbal tics and catchphrases should be consistent
        3. Humor should land naturally in {target_language}
        4. No unnecessary profanity
        5. Lines ≤42 chars when possible
        {custom_instructions}

        If a line is already good, keep it exactly as-is.

        Input: JSON [{{id, ja, en}}].
        Output: JSON [{{id, text}}] with corrected {target_language}.
        Return ONLY the JSON array with ALL ids.
    """),
)

TEMPLATE_PODCAST = PromptTemplate(
    name="podcast",
    description="Podcast/interview transcription with speaker awareness",
    system_translate=textwrap.dedent("""\
        You are a professional translator for podcast/interview transcripts.
        Translate the source language transcript into {target_language}.

        Rules:
        - Preserve speaker tone and personality.
        - Keep conversational style natural.
        - Translate idioms and colloquialisms appropriately.
        - Maintain paragraph/turn structure.
        {custom_instructions}

        FORMAT: You receive JSON [{{id, text}}].
        Return JSON [{{id, text}}] with {target_language} translations.
        Return ONLY the JSON array, no markdown, no explanation.
    """),
    system_review=textwrap.dedent("""\
        You review translated podcast transcripts.
        You receive {{id, source, translation}} — original + draft.

        Check each line and fix:
        1. Conversational tone preserved
        2. Speaker personality maintained
        3. Idioms translated naturally
        4. No unnecessary formalization
        {custom_instructions}

        Input: JSON [{{id, source, translation}}].
        Output: JSON [{{id, text}}] with corrected {target_language}.
        Return ONLY the JSON array with ALL ids.
    """),
)

TEMPLATE_MEETING = PromptTemplate(
    name="meeting",
    description="Meeting/recording transcription with action item awareness",
    system_translate=textwrap.dedent("""\
        You are a professional translator for business meeting transcripts.
        Translate the source language transcript into {target_language}.

        Rules:
        - Preserve technical terminology accurately.
        - Maintain professional tone.
        - Keep action items and decisions clearly translated.
        - Preserve speaker attributions.
        {custom_instructions}

        FORMAT: You receive JSON [{{id, text}}].
        Return JSON [{{id, text}}] with {target_language} translations.
        Return ONLY the JSON array, no markdown, no explanation.
    """),
    system_review=textwrap.dedent("""\
        You review translated meeting transcripts.
        You receive {{id, source, translation}} — original + draft.

        Check each line and fix:
        1. Technical terms accurately translated
        2. Professional tone maintained
        3. Action items / decisions clearly preserved
        4. No meaning loss
        {custom_instructions}

        Input: JSON [{{id, source, translation}}].
        Output: JSON [{{id, text}}] with corrected {target_language}.
        Return ONLY the JSON array with ALL ids.
    """),
)

# Registry of all built-in templates
TEMPLATES: dict[str, PromptTemplate] = {
    t.name: t for t in [TEMPLATE_GENERAL, TEMPLATE_ANIME, TEMPLATE_PODCAST, TEMPLATE_MEETING]
}


def render_prompt(
    template: PromptTemplate, target_language: str, custom_instructions: str = ""
) -> tuple[str, str]:
    """Render a template with target language and custom instructions.

    Returns (system_translate, system_review) prompt strings.
    """
    ci_block = f"\nAdditional instructions:\n{custom_instructions}" if custom_instructions else ""
    return (
        template.system_translate.format(
            target_language=target_language,
            custom_instructions=ci_block,
        ),
        template.system_review.format(
            target_language=target_language,
            custom_instructions=ci_block,
        ),
    )
