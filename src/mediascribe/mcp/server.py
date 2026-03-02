"""MCP server — exposes mediascribe pipeline tools to LLM agents."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from mediascribe.core.events import EventHandler, EventType, PipelineEvent
from mediascribe.mcp.bridge import PipelineError, run_transcription, run_translation
from mediascribe.mcp.serializers import job_to_result, profiles_to_result, settings_to_result

mcp = FastMCP(
    "mediascribe",
    instructions=(
        "mediascribe transcribes, translates, and analyzes audio/video media. "
        "Use 'transcribe' for full pipeline processing of media files. "
        "Use 'translate' to translate an existing SRT subtitle file. "
        "Use 'list_profiles' to see available configuration presets. "
        "Use 'get_config' to view the current configuration."
    ),
)

_executor = ThreadPoolExecutor(max_workers=2)


def _make_progress_forwarder(
    ctx: Context, loop: asyncio.AbstractEventLoop
) -> EventHandler:
    """Create a sync callback that forwards pipeline events to MCP Context.

    Pipeline steps run in a worker thread; this bridges events back to the
    async MCP context via ``run_coroutine_threadsafe``.
    """

    def forward(event: PipelineEvent) -> None:
        match event.type:
            case EventType.STEP_PROGRESS:
                fut = asyncio.run_coroutine_threadsafe(
                    ctx.report_progress(event.progress, 1.0), loop
                )
                fut.result(timeout=5)
            case EventType.STEP_START | EventType.STEP_COMPLETE:
                fut = asyncio.run_coroutine_threadsafe(ctx.info(event.message), loop)
                fut.result(timeout=5)
            case EventType.STEP_ERROR | EventType.WARNING:
                fut = asyncio.run_coroutine_threadsafe(ctx.warning(event.message), loop)
                fut.result(timeout=5)
            case EventType.JOB_ERROR:
                fut = asyncio.run_coroutine_threadsafe(ctx.error(event.message), loop)
                fut.result(timeout=5)

    return forward


def _error_response(message: str, **extra: Any) -> str:
    """Build a JSON error response string."""
    return json.dumps({"error": True, "message": message, **extra})


@mcp.tool()  # type: ignore[untyped-decorator]
async def transcribe(
    file_path: str,
    ctx: Context,
    source_language: str | None = None,
    target_language: str | None = None,
    profile: str = "general",
    whisper_model: str = "large-v3",
    output_formats: list[str] | None = None,
    enable_analyze: bool = False,
) -> str:
    """Transcribe an audio or video file.

    Full pipeline: detect, normalize, transcribe, translate (if target_language
    set), analyze (if enabled), and export.

    Args:
        file_path: Path to the input audio/video file.
        source_language: Source language code (e.g. "ja", "en"). Auto-detects if omitted.
        target_language: Target language for translation (e.g. "en"). Omit to skip.
        profile: Config preset: general, anime, podcast, or meeting.
        whisper_model: Whisper model size (e.g. "large-v3", "medium", "small").
        output_formats: Output formats to write (e.g. ["srt", "vtt", "txt", "json"]).
        enable_analyze: Enable AI analysis (summary, topics, action items).
    """
    loop = asyncio.get_running_loop()
    progress_cb = _make_progress_forwarder(ctx, loop)

    try:
        job = await loop.run_in_executor(
            _executor,
            lambda: run_transcription(
                file_path=file_path,
                source_language=source_language,
                target_language=target_language,
                profile=profile,
                whisper_model=whisper_model,
                output_formats=output_formats,
                enable_analyze=enable_analyze,
                on_progress=progress_cb,
            ),
        )
        return json.dumps(job_to_result(job))
    except FileNotFoundError as e:
        return _error_response(str(e))
    except PipelineError as e:
        result = job_to_result(e.job) if e.job else {}
        return _error_response(str(e), partial_result=result)


@mcp.tool()  # type: ignore[untyped-decorator]
async def translate(
    srt_path: str,
    ctx: Context,
    target_language: str = "en",
    profile: str = "general",
    translation_model: str = "gpt-4.1",
) -> str:
    """Translate an existing SRT subtitle file without re-transcribing.

    Args:
        srt_path: Path to the input SRT file.
        target_language: Target language for translation (e.g. "en", "es", "fr").
        profile: Config preset: general, anime, podcast, or meeting.
        translation_model: Translation model (e.g. "gpt-4.1", "gpt-4o").
    """
    loop = asyncio.get_running_loop()
    progress_cb = _make_progress_forwarder(ctx, loop)

    try:
        job = await loop.run_in_executor(
            _executor,
            lambda: run_translation(
                srt_path=srt_path,
                target_language=target_language,
                profile=profile,
                translation_model=translation_model,
                on_progress=progress_cb,
            ),
        )
        return json.dumps(job_to_result(job))
    except FileNotFoundError as e:
        return _error_response(str(e))
    except PipelineError as e:
        result = job_to_result(e.job) if e.job else {}
        return _error_response(str(e), partial_result=result)


@mcp.tool()  # type: ignore[untyped-decorator]
async def list_profiles() -> str:
    """List all available mediascribe configuration profiles.

    Profiles are named presets (general, anime, podcast, meeting) that adjust
    pipeline behavior for different content types.
    """
    return json.dumps(profiles_to_result())


@mcp.tool()  # type: ignore[untyped-decorator]
async def get_config() -> str:
    """Show the current mediascribe configuration with secrets redacted."""
    from mediascribe.core.config import MediascribeSettings

    settings = MediascribeSettings()
    return json.dumps(settings_to_result(settings))
