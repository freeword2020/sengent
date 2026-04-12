from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentieon_assist.kernel.pack_contract import PackManifestEntry


@dataclass(frozen=True)
class ResolvedPackEntry:
    vendor_id: str
    logical_kind: str
    file_name: str
    entry_schema_version: str
    load_order: int
    required: bool


@dataclass(frozen=True)
class RequiredPackStatus:
    logical_kind: str
    file_name: str
    path: Path
    exists: bool
    required: bool
    valid: bool
    error: str = ""


def _manifest_entry_value(entry: PackManifestEntry, field_name: str) -> Any:
    value = getattr(entry, field_name, None)
    if value is None:
        raise AttributeError(f"pack manifest entry does not expose {field_name}")
    return value


def get_vendor_profile(vendor_id: str):
    from sentieon_assist.vendors import get_vendor_profile as resolve_vendor_profile

    return resolve_vendor_profile(vendor_id)


def _ordered_required_manifest_items(vendor_id: str) -> tuple[tuple[str, PackManifestEntry], ...]:
    profile = get_vendor_profile(vendor_id)
    required_items = (
        (logical_kind, entry)
        for logical_kind, entry in profile.pack_manifest.items()
        if _manifest_entry_value(entry, "required")
    )
    return tuple(sorted(required_items, key=lambda item: (_manifest_entry_value(item[1], "load_order"), item[0])))


def resolve_pack_entry(vendor_id: str, logical_kind: str) -> ResolvedPackEntry:
    profile = get_vendor_profile(vendor_id)
    try:
        entry = profile.pack_manifest[logical_kind]
    except KeyError as exc:
        raise KeyError(f"unknown logical pack kind for vendor {vendor_id}: {logical_kind}") from exc
    return ResolvedPackEntry(
        vendor_id=profile.vendor_id,
        logical_kind=logical_kind,
        file_name=_manifest_entry_value(entry, "file_name"),
        entry_schema_version=_manifest_entry_value(entry, "entry_schema_version"),
        load_order=_manifest_entry_value(entry, "load_order"),
        required=bool(_manifest_entry_value(entry, "required")),
    )


def pack_path_for_kind(source_directory: str | Path, vendor_id: str, logical_kind: str) -> Path:
    return Path(source_directory) / resolve_pack_entry(vendor_id, logical_kind).file_name


def _validate_runtime_pack(path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, "invalid-json"
    if not isinstance(payload, dict):
        return False, "json-object-required"
    version = payload.get("version")
    if not isinstance(version, str):
        return False, "version-string-required"
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return False, "entries-list-required"
    if any(not isinstance(entry, dict) for entry in entries):
        return False, "entries-dict-items-required"
    return True, ""


def required_pack_status(source_directory: str | Path, vendor_id: str) -> tuple[RequiredPackStatus, ...]:
    base_directory = Path(source_directory)
    status: list[RequiredPackStatus] = []
    for logical_kind, entry in _ordered_required_manifest_items(vendor_id):
        file_name = _manifest_entry_value(entry, "file_name")
        path = base_directory / file_name
        exists = path.exists()
        valid = False
        error = ""
        if exists:
            valid, error = _validate_runtime_pack(path)
        status.append(
            RequiredPackStatus(
                logical_kind=logical_kind,
                file_name=file_name,
                path=path,
                exists=exists,
                required=bool(_manifest_entry_value(entry, "required")),
                valid=valid,
                error=error,
            )
        )
    return tuple(status)


def ordered_required_pack_file_names(vendor_id: str) -> tuple[str, ...]:
    return tuple(
        _manifest_entry_value(entry, "file_name")
        for _, entry in _ordered_required_manifest_items(vendor_id)
    )


__all__ = [
    "ResolvedPackEntry",
    "RequiredPackStatus",
    "ordered_required_pack_file_names",
    "pack_path_for_kind",
    "required_pack_status",
    "resolve_pack_entry",
]
