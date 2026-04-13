from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any
from uuid import uuid4


class OutboundContextDisposition(StrEnum):
    ALLOWED = "allowed"
    REDACTED = "redacted"
    LOCAL_ONLY = "local_only"


@dataclass(frozen=True)
class OutboundContextItem:
    key: str
    value: Any
    disposition: str = OutboundContextDisposition.ALLOWED
    provenance: dict[str, Any] = field(default_factory=dict)
    redaction_reason: str = ""


@dataclass(frozen=True)
class TrustBoundaryDecision:
    policy_name: str
    items: tuple[OutboundContextItem, ...]
    created_at: str = ""
    decision_id: str = ""


@dataclass(frozen=True)
class TrustBoundaryResult:
    decision: TrustBoundaryDecision
    outbound_items: tuple[OutboundContextItem, ...]
    summary: dict[str, Any]


_SUMMARY_STRING_FIELDS = ("policy_name", "decision_id", "created_at")
_SUMMARY_COUNT_FIELDS = ("item_count", "allowed_count", "redacted_count", "local_only_count")
_SUMMARY_KEY_FIELDS = ("allowed_keys", "redacted_keys", "local_only_keys")


def normalize_outbound_context_disposition(value: str | OutboundContextDisposition | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return OutboundContextDisposition.ALLOWED
    try:
        return OutboundContextDisposition(candidate)
    except ValueError as exc:
        raise ValueError(f"unsupported outbound context disposition: {value}") from exc


def redact_value(value: Any) -> str:
    return "[REDACTED]"


def redact_outbound_context_item(item: OutboundContextItem) -> OutboundContextItem:
    disposition = normalize_outbound_context_disposition(item.disposition)
    if disposition == OutboundContextDisposition.REDACTED:
        return replace(item, value=redact_value(item.value))
    if disposition == OutboundContextDisposition.LOCAL_ONLY:
        return replace(item, value=redact_value(item.value))
    return item


def filter_local_only_context_items(items: tuple[OutboundContextItem, ...] | list[OutboundContextItem]) -> tuple[OutboundContextItem, ...]:
    return tuple(
        item
        for item in items
        if normalize_outbound_context_disposition(item.disposition) != OutboundContextDisposition.LOCAL_ONLY
    )


def build_trust_boundary_result(decision: TrustBoundaryDecision) -> TrustBoundaryResult:
    filtered_items = filter_local_only_context_items(decision.items)
    outbound_items = tuple(redact_outbound_context_item(item) for item in filtered_items)
    allowed_keys = [item.key for item in outbound_items if normalize_outbound_context_disposition(item.disposition) == OutboundContextDisposition.ALLOWED]
    redacted_keys = [item.key for item in outbound_items if normalize_outbound_context_disposition(item.disposition) == OutboundContextDisposition.REDACTED]
    local_only_keys = [item.key for item in decision.items if normalize_outbound_context_disposition(item.disposition) == OutboundContextDisposition.LOCAL_ONLY]
    summary = sanitize_trust_boundary_summary(
        {
        "policy_name": decision.policy_name,
        "decision_id": decision.decision_id or uuid4().hex,
        "created_at": decision.created_at,
        "item_count": len(decision.items),
        "allowed_count": len(allowed_keys),
        "redacted_count": len(redacted_keys),
        "local_only_count": len(local_only_keys),
        "allowed_keys": allowed_keys,
        "redacted_keys": redacted_keys,
        "local_only_keys": local_only_keys,
        }
    )
    return TrustBoundaryResult(decision=decision, outbound_items=outbound_items, summary=summary)


def sanitize_trust_boundary_summary(summary: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in _SUMMARY_STRING_FIELDS:
        normalized[field] = str(summary.get(field, "")).strip()
    for field in _SUMMARY_COUNT_FIELDS:
        normalized[field] = _normalize_non_negative_int(summary.get(field))
    for field in _SUMMARY_KEY_FIELDS:
        normalized[field] = _normalize_summary_keys(summary.get(field))
    return normalized


def _normalize_non_negative_int(value: Any) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, normalized)


def _normalize_summary_keys(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        candidate = str(item).strip()
        if candidate:
            normalized.append(candidate)
    return normalized


__all__ = [
    "OutboundContextDisposition",
    "OutboundContextItem",
    "TrustBoundaryDecision",
    "TrustBoundaryResult",
    "build_trust_boundary_result",
    "filter_local_only_context_items",
    "normalize_outbound_context_disposition",
    "redact_outbound_context_item",
    "redact_value",
    "sanitize_trust_boundary_summary",
]
