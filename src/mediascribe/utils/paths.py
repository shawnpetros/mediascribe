"""Path utilities — XDG dirs, temp file management."""

from __future__ import annotations

import os
from pathlib import Path


def xdg_config_dir() -> Path:
    """XDG-compliant config directory: ~/.config/mediascribe/"""
    base = Path(os.environ.get("XDG_CONFIG_HOME", "")) or Path.home() / ".config"
    return base / "mediascribe"


def xdg_cache_dir() -> Path:
    """XDG-compliant cache directory: ~/.cache/mediascribe/"""
    base = Path(os.environ.get("XDG_CACHE_HOME", "")) or Path.home() / ".cache"
    return base / "mediascribe"


def xdg_data_dir() -> Path:
    """XDG-compliant data directory: ~/.local/share/mediascribe/"""
    base = Path(os.environ.get("XDG_DATA_HOME", "")) or Path.home() / ".local" / "share"
    return base / "mediascribe"


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist, return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
