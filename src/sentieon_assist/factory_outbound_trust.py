from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryResult,
    TrustBoundaryDecision,
    build_trust_boundary_result,
)


@dataclass(frozen=True)
class FactoryHostedDraftRequest:
    task_kind: str
    vendor_id: str
    prompt: str
    source_references: tuple[dict[str, Any], ...]
    trust_boundary_result: TrustBoundaryResult


_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.+-])")
_SECRET_KV_PATTERN = re.compile(
    r"(?i)\b((?:token|secret|key|password|passwd|pwd)[\w-]*|[A-Za-z][\w-]*?(?:token|secret|key|password|passwd|pwd)[\w-]*)\s*([:=])\s*([^\s,;:.]+)([.,;:]?)"
)
_PATH_FRAGMENT_PATTERN = re.compile(r"(?<!\w)(?:/|[A-Za-z]:[\\/]|\.{1,2}[\\/])[^\s<>'\"`]+")


def build_factory_hosted_outbound_request(
    *,
    task_kind: str,
    vendor_id: str,
    instruction: str | None,
    source_references: list[dict[str, Any]],
) -> FactoryHostedDraftRequest:
    items: list[OutboundContextItem] = []
    hosted_source_references: list[dict[str, Any]] = []
    for index, reference in enumerate(source_references):
        label = str(reference.get("label", "")).strip()
        file_type = str(reference.get("file_type", "")).strip() or "text"
        preview = str(reference.get("preview", "")).strip()
        path = str(reference.get("path", "")).strip()
        if path:
            items.append(
                OutboundContextItem(
                    key=f"source_references[{index}].path",
                    value=path,
                    disposition=OutboundContextDisposition.LOCAL_ONLY,
                    provenance={"source": "factory-outbound-trust", "label": label, "file_type": file_type},
                    redaction_reason="factory-hosted-local-path",
                )
            )
        sanitized_preview = _scrub_text(preview)
        if preview:
            items.append(
                _build_context_item(
                    key=f"source_references[{index}].preview",
                    sanitized_value=sanitized_preview,
                    raw_value=preview,
                    provenance={"source": "factory-outbound-trust", "label": label, "file_type": file_type},
                    redaction_reason="factory-hosted-scrubber",
                )
            )
        hosted_reference = {"label": label, "file_type": file_type, "preview": sanitized_preview}
        hosted_source_references.append(hosted_reference)

    normalized_instruction = str(instruction).strip() or "No extra operator instruction provided."
    sanitized_instruction = _scrub_text(normalized_instruction)
    items.append(
        _build_context_item(
            key="instruction",
            sanitized_value=sanitized_instruction,
            raw_value=normalized_instruction,
            provenance={"source": "factory-outbound-trust"},
            redaction_reason="factory-hosted-scrubber",
        )
    )

    trust_boundary_result = build_trust_boundary_result(
        TrustBoundaryDecision(
            policy_name="factory-hosted-draft-outbound-v1",
            items=tuple(items),
        )
    )
    prompt = _build_hosted_prompt(
        task_kind=task_kind,
        vendor_id=vendor_id,
        instruction=sanitized_instruction,
        source_references=hosted_source_references,
    )
    return FactoryHostedDraftRequest(
        task_kind=task_kind,
        vendor_id=vendor_id,
        prompt=prompt,
        source_references=tuple(hosted_source_references),
        trust_boundary_result=trust_boundary_result,
    )


def _build_context_item(
    *,
    key: str,
    sanitized_value: str,
    raw_value: str,
    provenance: dict[str, Any],
    redaction_reason: str,
) -> OutboundContextItem:
    disposition = (
        OutboundContextDisposition.REDACTED if sanitized_value != raw_value else OutboundContextDisposition.ALLOWED
    )
    normalized_provenance = dict(provenance)
    if disposition == OutboundContextDisposition.REDACTED:
        normalized_provenance["sanitized_value"] = sanitized_value
    return OutboundContextItem(
        key=key,
        value=sanitized_value,
        disposition=disposition,
        provenance=normalized_provenance,
        redaction_reason=redaction_reason if disposition == OutboundContextDisposition.REDACTED else "",
    )


def _build_hosted_prompt(
    *,
    task_kind: str,
    vendor_id: str,
    instruction: str,
    source_references: list[dict[str, Any]],
) -> str:
    source_lines = "\n".join(
        f"- {reference['label']} ({reference['file_type']}): {reference['preview']}"
        for reference in source_references
    )
    return (
        "You are drafting offline factory review material for maintainer review only.\n"
        f"Task kind: {task_kind}\n"
        f"Vendor: {vendor_id}\n"
        f"Source references:\n{source_lines}\n"
        f"Operator instruction: {instruction}\n"
        "Output constraints:\n"
        "- Draft only; never activate runtime knowledge.\n"
        "- Keep review required.\n"
        "- Return maintainer-facing review candidates, not truth."
    )


def _scrub_text(value: str) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if _looks_like_path(candidate):
        return "[PATH]"
    scrubbed = _EMAIL_PATTERN.sub("[EMAIL]", value)
    scrubbed = _SECRET_KV_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]{match.group(4)}",
        scrubbed,
    )
    return _PATH_FRAGMENT_PATTERN.sub("[PATH]", scrubbed)


def _looks_like_path(value: str) -> bool:
    if value.startswith("http://") or value.startswith("https://"):
        return False
    return value.startswith(("/", "./", "../")) or bool(re.match(r"^[A-Za-z]:[\\/]", value))


__all__ = [
    "FactoryHostedDraftRequest",
    "build_factory_hosted_outbound_request",
]
