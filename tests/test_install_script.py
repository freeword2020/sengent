from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "install_sengent.sh"


def _run_install_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = ["/bin/bash", str(SCRIPT_PATH), *args]
    return subprocess.run(command, check=False, capture_output=True, text=True, env=env)


def test_install_script_help_lists_key_flags():
    result = _run_install_script("--help")

    assert result.returncode == 0
    assert "hosted runtime host" in result.stdout.lower()
    assert "build-only host" in result.stdout.lower()
    assert "openai-compatible api" in result.stdout.lower()
    assert "sengent_runtime_llm_provider" in result.stdout.lower()
    assert "sengent_factory_hosted_provider" in result.stdout.lower()
    assert "--venv-dir" in result.stdout
    assert "--with-pdf-build" in result.stdout
    assert "--with-maintainer-tools" in result.stdout
    assert "--skip-ollama" in result.stdout
    assert "--ensure-ollama-model" in result.stdout
    assert "--dry-run" in result.stdout


def test_install_script_dry_run_prints_core_bootstrap_steps(tmp_path: Path):
    result = _run_install_script(
        "--dry-run",
        "--skip-ollama",
        "--python",
        sys.executable,
        "--venv-dir",
        str(tmp_path / ".venv"),
    )

    assert result.returncode == 0
    assert "-m venv" in result.stdout
    assert "pip install --disable-pip-version-check --no-build-isolation ." in result.stdout
    assert "pip install -e ." not in result.stdout
    assert "sengent doctor --skip-ollama" in result.stdout
    assert "Seed active source packs" in result.stdout
    assert "incident-memory.json" in result.stdout
    assert f"source {tmp_path / '.venv' / 'bin' / 'activate'}" in result.stdout
    assert "Runtime provider env" in result.stdout


def test_install_script_dry_run_with_pdf_build_prints_optional_extra(tmp_path: Path):
    result = _run_install_script(
        "--dry-run",
        "--skip-ollama",
        "--with-pdf-build",
        "--python",
        sys.executable,
        "--venv-dir",
        str(tmp_path / ".venv"),
    )

    assert result.returncode == 0
    assert "pip install --disable-pip-version-check --no-build-isolation .[pdf-build]" in result.stdout


def test_install_script_dry_run_with_maintainer_tools_prints_combined_extra(tmp_path: Path):
    result = _run_install_script(
        "--dry-run",
        "--skip-ollama",
        "--with-maintainer-tools",
        "--python",
        sys.executable,
        "--venv-dir",
        str(tmp_path / ".venv"),
    )

    assert result.returncode == 0
    assert "pip install --disable-pip-version-check --no-build-isolation .[maintainer]" in result.stdout


def test_install_script_dry_run_warns_when_ollama_cli_missing(tmp_path: Path):
    env = dict(os.environ)
    env["PATH"] = str(tmp_path / "empty-bin")
    (tmp_path / "empty-bin").mkdir(parents=True, exist_ok=True)

    result = _run_install_script(
        "--dry-run",
        "--ensure-ollama-model",
        "--python",
        sys.executable,
        "--venv-dir",
        str(tmp_path / ".venv"),
        env=env,
    )

    assert result.returncode == 0
    assert "ollama CLI not found" in result.stdout


def test_install_script_dry_run_runtime_path_mentions_activation_and_installed_command(tmp_path: Path):
    result = _run_install_script(
        "--dry-run",
        "--ensure-ollama-model",
        "--python",
        sys.executable,
        "--venv-dir",
        str(tmp_path / ".venv"),
    )

    assert result.returncode == 0
    assert f"source {tmp_path / '.venv' / 'bin' / 'activate'}" in result.stdout
    assert str(tmp_path / ".venv" / "bin" / "sengent") in result.stdout
    assert "SENGENT_RUNTIME_LLM_PROVIDER=openai_compatible" in result.stdout
    assert "SENGENT_FACTORY_HOSTED_PROVIDER=openai_compatible" in result.stdout
