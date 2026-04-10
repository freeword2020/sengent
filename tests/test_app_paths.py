from __future__ import annotations

from sentieon_assist.app_paths import app_home_dir, default_runtime_root, default_source_dir


def test_app_home_dir_prefers_sengent_home_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SENGENT_HOME", str(tmp_path / "custom-home"))

    assert app_home_dir() == tmp_path / "custom-home"


def test_default_source_dir_uses_xdg_data_home_on_linux(monkeypatch, tmp_path):
    monkeypatch.delenv("SENGENT_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr("sys.platform", "linux")

    assert default_source_dir() == tmp_path / "xdg" / "sengent" / "sources" / "active"
    assert default_runtime_root() == tmp_path / "xdg" / "sengent" / "runtime"
