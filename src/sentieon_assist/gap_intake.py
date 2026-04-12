from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from sentieon_assist.session_events import SupportTurnView, load_turn_views


INCIDENT_PACK_TARGET = "incident-memory.json"
INCIDENT_ENTRY_TYPE = "incident"
INCIDENT_ACTION = "upsert"
INCIDENT_ORIGIN = "runtime-gap-capture"


@dataclass(frozen=True)
class GapIntakeResult:
    session_id: str
    turn_id: str
    turn_index: int
    gap_type: str
    markdown_path: Path
    metadata_path: Path


def export_gap_turn_to_inbox(
    *,
    session_id: str,
    inbox_directory: str | Path,
    runtime_root: str | Path | None = None,
    turn_id: str | None = None,
    latest: bool = False,
) -> GapIntakeResult:
    turn = _select_gap_turn(
        session_id=session_id,
        runtime_root=runtime_root,
        turn_id=turn_id,
        latest=latest,
    )
    if turn.gap_record is None:
        raise ValueError(f"turn {turn.turn_id} does not contain a gap_record")

    gap_type = _string_value(turn.gap_record.get("gap_type")) or "knowledge_gap"
    resolved_inbox_directory = Path(inbox_directory)
    resolved_inbox_directory.mkdir(parents=True, exist_ok=True)

    stem = _gap_file_stem(session_id=session_id, turn_id=turn.turn_id, gap_type=gap_type)
    markdown_path = resolved_inbox_directory / f"{stem}.md"
    metadata_path = resolved_inbox_directory / f"{stem}.meta.yaml"

    metadata = _gap_sidecar_metadata(
        turn=turn,
        gap_type=gap_type,
    )
    markdown_path.write_text(_gap_markdown_body(turn=turn, gap_type=gap_type), encoding="utf-8")
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True), encoding="utf-8")

    return GapIntakeResult(
        session_id=session_id,
        turn_id=turn.turn_id,
        turn_index=turn.turn_index,
        gap_type=gap_type,
        markdown_path=markdown_path,
        metadata_path=metadata_path,
    )


def _select_gap_turn(
    *,
    session_id: str,
    runtime_root: str | Path | None,
    turn_id: str | None,
    latest: bool,
) -> SupportTurnView:
    turn_views = load_turn_views(session_id, runtime_root=runtime_root)
    if not turn_views:
        raise ValueError(f"no turns found for session {session_id}")

    if turn_id:
        for turn in turn_views:
            if turn.turn_id == turn_id:
                if turn.gap_record is None:
                    raise ValueError(f"turn {turn_id} does not contain a gap_record")
                return turn
        raise ValueError(f"turn {turn_id} not found for session {session_id}")

    if not latest:
        raise ValueError("knowledge intake-gap requires --turn-id or --latest")

    for turn in reversed(turn_views):
        if turn.gap_record is not None:
            return turn

    raise ValueError(f"no gap_record found for session {session_id}")


def _gap_file_stem(*, session_id: str, turn_id: str, gap_type: str) -> str:
    return ".".join((_sanitize_path_component(session_id), _sanitize_path_component(turn_id), _sanitize_path_component(gap_type)))


def _gap_markdown_body(*, turn: SupportTurnView, gap_type: str) -> str:
    gap_record = turn.gap_record or {}
    known_context = _normalize_known_context(gap_record.get("known_context"))
    missing_materials = _normalize_string_list(gap_record.get("missing_materials"))
    captured_at = _string_value(gap_record.get("captured_at"))
    vendor_id = _string_value(gap_record.get("vendor_id")) or turn.vendor_id
    vendor_version = _string_value(gap_record.get("vendor_version")) or turn.vendor_version
    user_question = _string_value(gap_record.get("user_question")) or turn.prompt

    lines = [
        f"# Gap intake: {gap_type}",
        "",
        f"- Session: `{turn.session_id}`",
        f"- Turn: `{turn.turn_id}`",
        f"- Turn index: `{turn.turn_index}`",
        f"- Vendor: `{vendor_id}`",
        f"- Vendor version: `{vendor_version}`",
        f"- Captured at: `{captured_at}`",
        "",
        "## User Question",
        user_question or "",
        "",
        "## Known Context",
    ]
    if known_context:
        for key in sorted(known_context):
            lines.append(f"- {key}: {known_context[key]}")
    else:
        lines.append("- (none recorded)")
    lines.extend(
        [
            "",
            "## Missing Materials",
        ]
    )
    if missing_materials:
        lines.extend(f"- {item}" for item in missing_materials)
    else:
        lines.append("- (none recorded)")
    lines.extend(
        [
            "",
            "## Maintainer Notes",
            "Exported from runtime session logs for incident-memory compilation.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _gap_sidecar_metadata(*, turn: SupportTurnView, gap_type: str) -> dict[str, Any]:
    gap_record = turn.gap_record or {}
    captured_at = _string_value(gap_record.get("captured_at")) or _now_iso()
    vendor_version = _string_value(gap_record.get("vendor_version")) or turn.vendor_version
    metadata: dict[str, Any] = {
        "pack_target": INCIDENT_PACK_TARGET,
        "entry_type": INCIDENT_ENTRY_TYPE,
        "action": INCIDENT_ACTION,
        "origin": INCIDENT_ORIGIN,
        "id": _gap_entry_id(session_id=turn.session_id, turn_id=turn.turn_id, gap_type=gap_type),
        "name": f"Gap intake for {gap_type}",
        "session_id": turn.session_id,
        "turn_id": turn.turn_id,
        "turn_index": turn.turn_index,
        "gap_type": gap_type,
        "vendor_id": _string_value(gap_record.get("vendor_id")) or turn.vendor_id,
        "vendor_version": vendor_version,
        "user_question": _string_value(gap_record.get("user_question")) or turn.prompt,
        "known_context": _normalize_known_context(gap_record.get("known_context")),
        "missing_materials": _normalize_string_list(gap_record.get("missing_materials")),
        "captured_at": captured_at,
        "version": vendor_version,
        "date": _captured_date(captured_at),
    }
    return metadata


def _gap_entry_id(*, session_id: str, turn_id: str, gap_type: str) -> str:
    return _gap_file_stem(session_id=session_id, turn_id=turn_id, gap_type=gap_type)


def _captured_date(captured_at: str) -> str:
    normalized = _string_value(captured_at)
    if not normalized:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return datetime.now(timezone.utc).date().isoformat()


def _normalize_known_context(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, raw in value.items():
        key_text = _string_value(key)
        value_text = _string_value(raw)
        if not key_text or not value_text:
            continue
        normalized[key_text] = value_text
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [_string_value(item) for item in value]
    return [item for item in normalized if item]


def _string_value(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _sanitize_path_component(value: str) -> str:
    text = _string_value(value).lower()
    if not text:
        return "unknown"
    characters: list[str] = []
    previous_was_dash = False
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            characters.append(char)
            previous_was_dash = False
            continue
        if not previous_was_dash:
            characters.append("-")
            previous_was_dash = True
    sanitized = "".join(characters).strip("-._")
    return sanitized or "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
