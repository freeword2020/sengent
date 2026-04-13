from __future__ import annotations

from enum import StrEnum

from sentieon_assist.runtime_invariants import (
    ToolRequirement,
    normalize_tool_requirement as normalize_invariant_tool_requirement,
)


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
    KNOWLEDGE_GAP = "knowledge_gap"
    CLARIFICATION_OPEN = "clarification_open"
    MISSING_VENDOR_REFERENCE = "missing_vendor_reference"
    MISSING_VENDOR_DECISION = "missing_vendor_decision"
    MISSING_DOMAIN_STANDARD = "missing_domain_standard"
    MISSING_PLAYBOOK = "missing_playbook"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNSUPPORTED_VERSION = "unsupported_version"


class BoundaryOutcome(StrEnum):
    SHOULD_ANSWER = "should_answer"
    MUST_CLARIFY = "must_clarify"
    MUST_TOOL = "must_tool"
    MUST_REFUSE = "must_refuse"
    MUST_ESCALATE = "must_escalate"


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


def normalize_tool_requirement(value: str | ToolRequirement | None) -> str:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return ToolRequirement.NONE
    aliases = {
        "must_tool": ToolRequirement.REQUIRED,
        "required": ToolRequirement.REQUIRED,
        "tool_required": ToolRequirement.REQUIRED,
        "tool-required": ToolRequirement.REQUIRED,
        "model_only": ToolRequirement.NONE,
        "none": ToolRequirement.NONE,
    }
    if candidate in aliases:
        return normalize_invariant_tool_requirement(aliases[candidate])
    return normalize_invariant_tool_requirement(candidate)


def normalize_boundary_outcome(value: str | BoundaryOutcome | None) -> str:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return BoundaryOutcome.SHOULD_ANSWER
    aliases = {
        "answer": BoundaryOutcome.SHOULD_ANSWER,
        "should_answer": BoundaryOutcome.SHOULD_ANSWER,
        "clarify": BoundaryOutcome.MUST_CLARIFY,
        "must_clarify": BoundaryOutcome.MUST_CLARIFY,
        "tool": BoundaryOutcome.MUST_TOOL,
        "must_tool": BoundaryOutcome.MUST_TOOL,
        "refuse": BoundaryOutcome.MUST_REFUSE,
        "must_refuse": BoundaryOutcome.MUST_REFUSE,
        "escalate": BoundaryOutcome.MUST_ESCALATE,
        "must_escalate": BoundaryOutcome.MUST_ESCALATE,
    }
    if candidate in aliases:
        return aliases[candidate]
    try:
        return BoundaryOutcome(candidate)
    except ValueError:
        return candidate


def tool_requirement_for_support_intent(value: str | SupportIntent | None) -> str:
    intent = normalize_support_intent(value)
    if intent == SupportIntent.VALIDATION_NEXT_STEP:
        return ToolRequirement.REQUIRED
    return ToolRequirement.NONE


__all__ = [
    "BoundaryOutcome",
    "FallbackMode",
    "GapType",
    "SupportIntent",
    "ToolRequirement",
    "normalize_fallback_mode",
    "normalize_boundary_outcome",
    "normalize_support_intent",
    "normalize_tool_requirement",
    "tool_requirement_for_support_intent",
]
