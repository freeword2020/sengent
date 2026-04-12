from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sentieon_assist.support_contracts import GapType, normalize_support_intent


class GapStatus:
    OPEN = "open"
    RESOLVED = "resolved"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_gap_type(value: str | GapType | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return "knowledge_gap"
    known_values = {item.value for item in GapType} | {"clarification_open", "knowledge_gap"}
    return candidate if candidate in known_values else candidate


def normalize_gap_status(value: str | None) -> str:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return GapStatus.OPEN
    if candidate in {GapStatus.OPEN, GapStatus.RESOLVED}:
        return candidate
    return candidate


def normalize_known_context(value: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, raw in (value or {}).items():
        key_text = str(key).strip()
        value_text = str(raw).strip()
        if not key_text or not value_text:
            continue
        normalized[key_text] = value_text
    return normalized


@dataclass(frozen=True)
class GapRecord:
    vendor_id: str
    vendor_version: str
    intent: str
    gap_type: str
    user_question: str
    known_context: dict[str, str]
    missing_materials: list[str]
    captured_at: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_gap_record(
    *,
    vendor_id: str,
    vendor_version: str,
    intent: str,
    gap_type: str | GapType,
    user_question: str,
    known_context: dict[str, Any] | None = None,
    missing_materials: list[str] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    record = GapRecord(
        vendor_id=str(vendor_id).strip(),
        vendor_version=str(vendor_version).strip(),
        intent=normalize_support_intent(intent),
        gap_type=normalize_gap_type(gap_type),
        user_question=str(user_question).strip(),
        known_context=normalize_known_context(known_context),
        missing_materials=[str(item).strip() for item in (missing_materials or []) if str(item).strip()],
        captured_at=_now_iso(),
        status=normalize_gap_status(status),
    )
    return record.to_dict()
