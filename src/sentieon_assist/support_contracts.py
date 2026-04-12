from __future__ import annotations

from enum import StrEnum


class SupportIntent(StrEnum):
    CAPABILITY_EXPLANATION = "capability_explanation"
    CONCEPT_UNDERSTANDING = "concept_understanding"
    TASK_GUIDANCE = "task_guidance"
    DECISION_SUPPORT = "decision_support"
    TROUBLESHOOTING = "troubleshooting"
    VALIDATION_NEXT_STEP = "validation_next_step"
    KNOWLEDGE_GAP = "knowledge_gap"


class FallbackMode(StrEnum):
    NONE = ""
    UNSUPPORTED_VERSION = "unsupported-version"
    CONFLICTING_EVIDENCE = "conflicting-evidence"
    CLARIFICATION_OPEN = "clarification-open"
    NO_ANSWER_WITH_BOUNDARY = "no-answer-with-boundary"


class GapType(StrEnum):
    MISSING_VENDOR_REFERENCE = "missing_vendor_reference"
    MISSING_VENDOR_DECISION = "missing_vendor_decision"
    MISSING_DOMAIN_STANDARD = "missing_domain_standard"
    MISSING_PLAYBOOK = "missing_playbook"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNSUPPORTED_VERSION = "unsupported_version"


def normalize_support_intent(value: str | SupportIntent | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return SupportIntent.CONCEPT_UNDERSTANDING
    try:
        return SupportIntent(candidate)
    except ValueError:
        return candidate


def normalize_fallback_mode(value: str | FallbackMode | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return FallbackMode.NONE
    try:
        return FallbackMode(candidate)
    except ValueError:
        return candidate


__all__ = [
    "FallbackMode",
    "GapType",
    "SupportIntent",
    "normalize_fallback_mode",
    "normalize_support_intent",
]
