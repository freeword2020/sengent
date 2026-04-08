from __future__ import annotations

import json
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from sentieon_assist.config import load_config


def package_knowledge_dir() -> Path:
    resource = files("sentieon_assist").joinpath("knowledge", "base")
    with as_file(resource) as resolved:
        return Path(resolved)


def knowledge_dir() -> Path:
    configured = load_config().knowledge_dir.strip()
    if configured:
        return Path(configured)
    return package_knowledge_dir()


def load_rules(directory: str | Path | None = None) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    base_dir = Path(directory) if directory is not None else knowledge_dir()
    for path in sorted(base_dir.glob("*.json")):
        with open(path) as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"knowledge file must contain a JSON list: {path}")
        rules.extend(data)
    return rules


def match_rule(query: str, directory: str | Path | None = None) -> dict[str, Any] | None:
    normalized_query = query.lower()
    for rule in load_rules(directory):
        for pattern in rule.get("patterns", []):
            if str(pattern).lower() in normalized_query:
                return rule
    return None
