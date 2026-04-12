from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


LOGICAL_PACK_KINDS: tuple[str, ...] = (
    "vendor-reference",
    "vendor-decision",
    "domain-standard",
    "playbook",
    "troubleshooting",
    "incident-memory",
)


@dataclass(frozen=True)
class PackManifestEntry:
    required: bool
    file_name: str
    entry_schema_version: str
    load_order: int


def missing_required_pack_kinds(
    pack_manifest: Mapping[str, PackManifestEntry],
) -> tuple[str, ...]:
    missing: list[str] = []
    for logical_kind in LOGICAL_PACK_KINDS:
        entry = pack_manifest.get(logical_kind)
        if entry is None or not entry.required:
            missing.append(logical_kind)
    return tuple(missing)


def assert_required_pack_completeness(
    pack_manifest: Mapping[str, PackManifestEntry],
) -> None:
    missing = missing_required_pack_kinds(pack_manifest)
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"missing required logical pack kinds: {missing_text}")
