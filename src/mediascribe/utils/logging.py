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

    if rich_output:
        handler = RichHandler(
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

    logger.addHandler(handler)
    return logger
