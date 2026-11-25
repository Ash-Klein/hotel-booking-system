"""Runtime paths and environment configuration."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = ROOT_DIR / "data" / "exports"
DEFAULT_DB_PATH = DATA_DIR / "hotel.db"

APP_NAME = "云栖酒店集团 · 预订管理系统"
APP_VERSION = "1.0.0"
DEFAULT_FONT = "Microsoft YaHei UI"
WINDOW_SIZE = "1360x860"
MIN_WINDOW_SIZE = (1180, 720)


def database_path() -> Path:
    """Return the database path, allowing tests to override it."""
    override = os.environ.get("HOTEL_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH


def ensure_runtime_dirs() -> None:
    """Create writable runtime directories."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
