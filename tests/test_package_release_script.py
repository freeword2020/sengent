from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "package_release.sh"


def _run_package_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_package_release_script_help_lists_main_options():
    result = _run_package_script("--help")

    assert result.returncode == 0
    assert "--output-dir" in result.stdout
    assert "--version" in result.stdout
    assert "--dry-run" in result.stdout


def test_package_release_script_dry_run_prints_archive_names(tmp_path: Path):
    result = _run_package_script("--dry-run", "--output-dir", str(tmp_path))

    assert result.returncode == 0
    assert "sengent-0.1.0.tar.gz" in result.stdout
    assert "sengent-0.1.0.zip" in result.stdout
