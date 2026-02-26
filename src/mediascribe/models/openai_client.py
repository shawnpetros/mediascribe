"""OpenAI API client wrapper for translation and analysis.

Provides a structured interface for making OpenAI API calls with
JSON request/response parsing and error handling.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI


def get_client(api_key: str | None = None) -> OpenAI:
    """Create an OpenAI client.

    If api_key is provided, uses it directly. Otherwise relies on
    OPENAI_API_KEY environment variable (set via .env or config).
    """
    if api_key:
        return OpenAI(api_key=api_key)
    return OpenAI()  # uses env var


def call_openai_json(
    client: OpenAI,
    model: str,
    system_prompt: str,
    payload: list[dict[str, Any]],
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> list[dict[str, Any]]:
    """Call OpenAI with a JSON payload and parse the JSON response.

    Sends the system prompt and a JSON-encoded user message.
    Expects the model to return a JSON array.

    Args:
        client: OpenAI client instance.
        model: Model name (e.g., "gpt-4.1").
        system_prompt: System message with instructions.
        payload: List of dicts to send as JSON user message.
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature.

    Returns:
        Parsed JSON response as a list of dicts.

    Raises:
        json.JSONDecodeError: If the response isn't valid JSON.
    """
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        max_output_tokens=max_tokens,
        temperature=temperature,
    )

    raw = resp.output_text.strip()
    # Strip markdown fences if the model wraps them
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result: list[dict[str, Any]] = json.loads(raw)
    return result
