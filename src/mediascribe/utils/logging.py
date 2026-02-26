"""Structured logging setup for mediascribe."""

from __future__ import annotations

import logging
import sys

from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO, rich_output: bool = True) -> logging.Logger:
    """Configure and return the mediascribe logger.

    Args:
        level: Logging level (default INFO).
        rich_output: If True, use Rich handler for pretty console output.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("mediascribe")
    logger.setLevel(level)

    if logger.handlers:
        return logger  # Already configured

    handler: logging.Handler
    if rich_output:
        handler = RichHandler(
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        handler = stream_handler

    logger.addHandler(handler)
    return logger
