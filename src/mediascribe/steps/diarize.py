"""Diarize step — speaker attribution via pyannote.audio.

Phase 3 feature. Requires:
- pyannote.audio >= 3.0
- HuggingFace token (free, needs model license acceptance)
- GPU recommended but CPU works (slower)

Will output speaker labels per segment for podcast/meeting use cases.
"""
