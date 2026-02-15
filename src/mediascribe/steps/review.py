"""Review step — second-pass AI quality check on translations.

TODO: Extract from reference pipeline.py. Key logic to port:
- Send JP + draft EN side-by-side to reviewer prompt
- Fix character names, tics, profanity levels
- Ensure humor lands, lines are subtitle-friendly
"""
