from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentieon_assist.kernel import pack_path_for_kind


SENTIEON_VENDOR_ID = "sentieon"
INCIDENT_MEMORY_LOGICAL_KIND = "incident-memory"


def incident_memory_path(source_directory: str | Path) -> Path:
    return pack_path_for_kind(source_directory, SENTIEON_VENDOR_ID, INCIDENT_MEMORY_LOGICAL_KIND)


def load_incident_memory(source_directory: str | Path) -> dict[str, Any]:
    path = incident_memory_path(source_directory)
    if not path.exists():
        return {"version": "", "entries": []}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"incident memory must contain a JSON object: {path}")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"incident memory entries must be a JSON list: {path}")
    return data


def list_incident_entries(source_directory: str | Path) -> list[dict[str, Any]]:
    return [entry for entry in load_incident_memory(source_directory).get("entries", []) if isinstance(entry, dict)]
