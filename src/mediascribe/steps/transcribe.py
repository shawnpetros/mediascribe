"""Transcribe step — speech-to-text via local Whisper or OpenAI API.

TODO: Extract from reference pipeline.py. Key logic to port:
- Chunked transcription (split audio → transcribe per chunk → merge)
- Loop/hallucination detection (validate_segments)
- Retry with stricter anti-hallucination params
- Word-level timestamps for accurate timing
- Progress reporting per chunk
- Both local (faster-whisper) and API (OpenAI) modes
"""
