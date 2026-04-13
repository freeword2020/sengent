from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryDecision,
    TrustBoundaryResult,
    build_trust_boundary_result,
)


@dataclass(frozen=True)
class RuntimeOutboundTrustResult:
    policy_name: str
    trust_boundary_result: TrustBoundaryResult
    issue_type: str = ""
    query: str = ""
    info: dict[str, str] = field(default_factory=dict)
    source_context: dict[str, str] = field(default_factory=dict)
    evidence: tuple[dict[str, str], ...] = field(default_factory=tuple)
    raw_response: str = ""


_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.+-])")
_SECRET_KV_PATTERN = re.compile(
    r"(?i)\b((?:token|secret|key|password|passwd|pwd)[\w-]*|[A-Za-z][\w-]*?(?:token|secret|key|password|passwd|pwd)[\w-]*)\s*([:=])\s*([^\s,;:.]+)([.,;:]?)"
)
_PATH_FRAGMENT_PATTERN = re.compile(r"(?<!\w)(?:/|[A-Za-z]:[\\/]|\.{1,2}[\\/])[^\s<>'\"`]+")


def build_support_answer_outbound_trust(
    *,
    issue_type: str,
    query: str,
    info: Mapping[str, Any] | None = None,
    source_context: Mapping[str, Any] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
    raw_response: str = "",
) -> RuntimeOutboundTrustResult:
    return _build_runtime_outbound_trust(
        policy_name="support-answer-outbound-v1",
        issue_type=issue_type,
        query=query,
        info=info,
        source_context=source_context,
        evidence=evidence,
        raw_response=raw_response,
    )


def build_reference_answer_outbound_trust(
    *,
    query: str,
    source_context: Mapping[str, Any] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
    raw_response: str = "",
) -> RuntimeOutboundTrustResult:
    return _build_runtime_outbound_trust(
        policy_name="reference-answer-outbound-v1",
        query=query,
        source_context=source_context,
        evidence=evidence,
        raw_response=raw_response,
    )


def build_reference_intent_outbound_trust(*, query: str) -> RuntimeOutboundTrustResult:
    return _build_runtime_outbound_trust(
        policy_name="reference-intent-outbound-v1",
        query=query,
    )


def _build_runtime_outbound_trust(
    *,
    policy_name: str,
    issue_type: str = "",
    query: str = "",
    info: Mapping[str, Any] | None = None,
    source_context: Mapping[str, Any] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
    raw_response: str = "",
) -> RuntimeOutboundTrustResult:
    items: list[OutboundContextItem] = []

    sanitized_issue_type = str(issue_type).strip()
    if sanitized_issue_type:
        items.append(_build_context_item("issue_type", sanitized_issue_type, sanitized_issue_type))

    sanitized_query = _scrub_text(str(query))
    items.append(_build_context_item("query", sanitized_query, str(query)))

    sanitized_info = _sanitize_mapping(info, prefix="info", items=items)
    sanitized_source_context = _sanitize_mapping(source_context, prefix="source_context", items=items)
    sanitized_evidence = _sanitize_evidence(evidence, items=items)

    sanitized_raw_response = _scrub_text(str(raw_response)) if raw_response else ""
    if raw_response:
        items.append(_build_context_item("raw_response", sanitized_raw_response, str(raw_response)))

    decision = TrustBoundaryDecision(policy_name=policy_name, items=tuple(items))
    trust_boundary_result = build_trust_boundary_result(decision)
    return RuntimeOutboundTrustResult(
        policy_name=policy_name,
        trust_boundary_result=trust_boundary_result,
        issue_type=sanitized_issue_type,
        query=sanitized_query,
        info=sanitized_info,
        source_context=sanitized_source_context,
        evidence=sanitized_evidence,
        raw_response=sanitized_raw_response,
    )


def _build_context_item(key: str, sanitized_value: Any, raw_value: Any) -> OutboundContextItem:
    disposition = (
        OutboundContextDisposition.REDACTED if sanitized_value != raw_value else OutboundContextDisposition.ALLOWED
    )
    provenance: dict[str, Any] = {"source": "runtime-outbound-trust"}
    if disposition == OutboundContextDisposition.REDACTED:
        provenance["sanitized_value"] = sanitized_value
    return OutboundContextItem(
        key=key,
        value=sanitized_value,
        disposition=disposition,
        provenance=provenance,
        redaction_reason="runtime-sanitizer" if disposition == OutboundContextDisposition.REDACTED else "",
    )


def _sanitize_mapping(
    values: Mapping[str, Any] | None,
    *,
    prefix: str,
    items: list[OutboundContextItem],
) -> dict[str, str]:
    if not values:
        return {}
    sanitized: dict[str, str] = {}
    for key, value in values.items():
        field_name = str(key).strip()
        if not field_name:
            continue
        scrubbed_value = _scrub_text(str(value))
        sanitized[field_name] = scrubbed_value
        items.append(_build_context_item(f"{prefix}.{field_name}", scrubbed_value, str(value)))
    return sanitized


def _sanitize_evidence(
    evidence: list[Mapping[str, Any]] | None,
    *,
    items: list[OutboundContextItem],
) -> tuple[dict[str, str], ...]:
    if not evidence:
        return ()
    sanitized_entries: list[dict[str, str]] = []
    for index, entry in enumerate(evidence):
        if not isinstance(entry, Mapping):
            continue
        sanitized_entry: dict[str, str] = {}
        for key, value in entry.items():
            field_name = str(key).strip()
            if not field_name:
                continue
            scrubbed_value = _scrub_text(str(value))
            sanitized_entry[field_name] = scrubbed_value
            items.append(_build_context_item(f"evidence[{index}].{field_name}", scrubbed_value, str(value)))
        if sanitized_entry:
            sanitized_entries.append(sanitized_entry)
    return tuple(sanitized_entries)


def _scrub_text(value: str) -> str:
    if not value:
        return value
    stripped = value.strip()
    if _looks_like_whole_path(stripped):
        return "[PATH]"
    scrubbed = _EMAIL_PATTERN.sub("[EMAIL]", value)
    scrubbed = _SECRET_KV_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]{match.group(4)}", scrubbed)
    scrubbed = _PATH_FRAGMENT_PATTERN.sub("[PATH]", scrubbed)
    return scrubbed


def _looks_like_whole_path(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return False
    if candidate.startswith(("/", "./", "../")):
        return True
    if re.match(r"^[A-Za-z]:[\\/]", candidate):
        return True
    return False


__all__ = [
    "RuntimeOutboundTrustResult",
    "build_reference_answer_outbound_trust",
    "build_reference_intent_outbound_trust",
    "build_support_answer_outbound_trust",
]
