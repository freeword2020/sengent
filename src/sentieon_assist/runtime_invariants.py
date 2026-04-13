from __future__ import annotations

from enum import StrEnum


class TruthSource(StrEnum):
    ACTIVE_KNOWLEDGE = "active_knowledge"
    EXPLICIT_COMPILED_LAYER = "explicit_compiled_layer"
    CURRENT_SESSION_CONTEXT = "current_session_context"
    MODEL_OUTPUT = "model_output"
    RAW_INGESTION = "raw_ingestion"


class PromotionState(StrEnum):
    RAW = "raw"
    CANDIDATE = "candidate"
    REVIEW_NEEDED = "review_needed"
    REVIEWED = "reviewed"
    ACTIVATED = "activated"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class ToolRequirement(StrEnum):
    NONE = "none"
    REQUIRED = "required"


_TRUTH_SOURCE_ALIASES = {
    "active-knowledge": TruthSource.ACTIVE_KNOWLEDGE,
    "compiled-layer": TruthSource.EXPLICIT_COMPILED_LAYER,
    "explicit-compiled-layer": TruthSource.EXPLICIT_COMPILED_LAYER,
    "session-context": TruthSource.CURRENT_SESSION_CONTEXT,
    "current-session-context": TruthSource.CURRENT_SESSION_CONTEXT,
    "model-output": TruthSource.MODEL_OUTPUT,
    "raw-ingestion": TruthSource.RAW_INGESTION,
}

_PROMOTION_STATE_ALIASES = {
    "draft": PromotionState.REVIEW_NEEDED,
    "pending": PromotionState.REVIEW_NEEDED,
    "pending-promotion": PromotionState.REVIEW_NEEDED,
    "pending_review": PromotionState.REVIEW_NEEDED,
    "review-needed": PromotionState.REVIEW_NEEDED,
}

_TOOL_REQUIREMENT_ALIASES = {
    "tool-required": ToolRequirement.REQUIRED,
    "must-tool": ToolRequirement.REQUIRED,
}


def normalize_truth_source(value: str | TruthSource | None, *, allow_raw_ingestion: bool = False) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise ValueError("truth source is required")
    try:
        truth_source = TruthSource(candidate)
    except ValueError:
        truth_source = _TRUTH_SOURCE_ALIASES.get(candidate.lower())
        if truth_source is None:
            raise ValueError(f"unsupported truth source: {value}") from None
    if truth_source == TruthSource.RAW_INGESTION and not allow_raw_ingestion:
        raise ValueError("raw ingestion cannot be treated as runtime truth")
    return truth_source


def normalize_promotion_state(value: str | PromotionState | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return PromotionState.REVIEW_NEEDED
    try:
        return PromotionState(candidate)
    except ValueError:
        alias = _PROMOTION_STATE_ALIASES.get(candidate.lower())
        if alias is None:
            raise ValueError(f"unsupported promotion state: {value}") from None
        return alias


def normalize_tool_requirement(value: str | ToolRequirement | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ToolRequirement.NONE
    try:
        return ToolRequirement(candidate)
    except ValueError:
        alias = _TOOL_REQUIREMENT_ALIASES.get(candidate.lower())
        if alias is None:
            raise ValueError(f"unsupported tool requirement: {value}") from None
        return alias


def is_runtime_truth_source(value: str | TruthSource | None) -> bool:
    return normalize_truth_source(value, allow_raw_ingestion=True) in {
        TruthSource.ACTIVE_KNOWLEDGE,
        TruthSource.EXPLICIT_COMPILED_LAYER,
        TruthSource.CURRENT_SESSION_CONTEXT,
    }


def is_tool_required(value: str | ToolRequirement | None) -> bool:
    return normalize_tool_requirement(value) == ToolRequirement.REQUIRED


def is_pending_promotion(value: str | PromotionState | None) -> bool:
    return normalize_promotion_state(value) in {
        PromotionState.RAW,
        PromotionState.CANDIDATE,
        PromotionState.REVIEW_NEEDED,
    }


__all__ = [
    "PromotionState",
    "ToolRequirement",
    "TruthSource",
    "is_pending_promotion",
    "is_runtime_truth_source",
    "is_tool_required",
    "normalize_promotion_state",
    "normalize_tool_requirement",
    "normalize_truth_source",
]
