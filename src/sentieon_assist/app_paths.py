from __future__ import annotations

import os
import sys
from pathlib import Path


APP_HOME_ENV = "SENGENT_HOME"
APP_NAME = "sengent"


def app_home_dir() -> Path:
    configured = os.getenv(APP_HOME_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Sengent"
    xdg_data_home = os.getenv("XDG_DATA_HOME", "").strip()
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def default_source_dir() -> Path:
    return app_home_dir() / "sources" / "active"


def default_runtime_root() -> Path:
    return app_home_dir() / "runtime"


def default_knowledge_inbox_dir(*, product: str = "sentieon") -> Path:
    return app_home_dir() / "knowledge-inbox" / product


def default_knowledge_build_root() -> Path:
    return default_runtime_root() / "knowledge-build"
