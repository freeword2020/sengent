import tomllib
from pathlib import Path


def test_pyproject_declares_packaging_dependencies_for_knowledge_build():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = payload["project"]["dependencies"]
    optional_dependencies = payload["project"].get("optional-dependencies", {})
    scripts = payload["project"].get("scripts", {})

    assert any(str(item).lower().startswith("pyyaml") for item in dependencies)
    assert scripts.get("sengent") == "sentieon_assist.cli:main"
    assert scripts.get("sentieon-assist") == "sentieon_assist.cli:main"
    assert "pdf-build" in optional_dependencies
    assert any(str(item).lower().startswith("docling") for item in optional_dependencies["pdf-build"])
    assert "maintainer" in optional_dependencies
    assert any(str(item).lower().startswith("pytest") for item in optional_dependencies["maintainer"])
