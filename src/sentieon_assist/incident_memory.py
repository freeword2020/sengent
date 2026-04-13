from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentieon_assist.kernel import pack_path_for_kind
from sentieon_assist.vendors import resolve_vendor_id

INCIDENT_MEMORY_LOGICAL_KIND = "incident-memory"


def incident_memory_path(source_directory: str | Path, *, vendor_id: str | None = None) -> Path:
    resolved_vendor_id = resolve_vendor_id(vendor_id)
    return pack_path_for_kind(source_directory, resolved_vendor_id, INCIDENT_MEMORY_LOGICAL_KIND)


def load_incident_memory(source_directory: str | Path, *, vendor_id: str | None = None) -> dict[str, Any]:
    path = incident_memory_path(source_directory, vendor_id=vendor_id)
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


def list_incident_entries(source_directory: str | Path, *, vendor_id: str | None = None) -> list[dict[str, Any]]:
    return [entry for entry in load_incident_memory(source_directory, vendor_id=vendor_id).get("entries", []) if isinstance(entry, dict)]
