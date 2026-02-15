"""Timing step — optimize subtitle display timing.

TODO: Extract from reference pipeline.py. Key logic to port:
- Word-timestamp-based segment boundaries
- Duration cap based on text length (chars_per_second heuristic)
- Minimum gap enforcement between subtitles
- Sync translated SRT timing to source language SRT
"""
