from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _isolated_sengent_home(monkeypatch, tmp_path):
    monkeypatch.setenv("SENGENT_HOME", str(tmp_path / "sengent-home"))
    monkeypatch.setenv("SENTIEON_ASSIST_SOURCE_DIR", str(ROOT / "sentieon-note"))
