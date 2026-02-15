"""Translate step — AI-powered translation with batched API calls.

TODO: Extract from reference pipeline.py. Key logic to port:
- Batched OpenAI translation (N subs per request with context overlap)
- System prompt template with profile-based customization
- Custom instructions from user config
- JSON-based request/response for structured translation
"""
