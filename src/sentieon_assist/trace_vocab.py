from __future__ import annotations

from enum import StrEnum
from typing import Iterable


class ResponseMode(StrEnum):
    CAPABILITY = "capability"
    BOUNDARY = "boundary"
    EXTERNAL_ERROR = "external_error"
    SCRIPT = "script"
    PARAMETER = "parameter"
    MODULE_INTRO = "module_intro"
    WORKFLOW_GUIDANCE = "workflow_guidance"
    DOC = "doc"
    CLARIFY = "clarify"


class ResolverPath(StrEnum):
    CAPABILITY_EXPLANATION = "capability_explanation"
    TROUBLESHOOTING_MISSING_INFO = "troubleshooting_missing_info"
    TROUBLESHOOTING_KNOWLEDGE_GAP = "troubleshooting_knowledge_gap"
    TROUBLESHOOTING_CLARIFY_LIMIT = "troubleshooting_clarify_limit"
    TROUBLESHOOTING_UNSUPPORTED_VERSION = "troubleshooting_unsupported_version"
    TROUBLESHOOTING_RULE = "troubleshooting_rule"
    TROUBLESHOOTING_OTHER_UNSUPPORTED = "troubleshooting_other_unsupported"
    TROUBLESHOOTING_MODEL_FALLBACK = "troubleshooting_model_fallback"
    TROUBLESHOOTING_GENERATED_FALLBACK = "troubleshooting_generated_fallback"
    REFERENCE_UNSUPPORTED_VERSION = "reference_unsupported_version"
    DOC_REFERENCE = "doc_reference"
    BOUNDARY_REFERENCE = "boundary_reference"
    WORKFLOW_UNCOVERED = "workflow_uncovered"
    WORKFLOW_DIRECT_SCRIPT = "workflow_direct_script"
    WORKFLOW_GUIDANCE = "workflow_guidance"
    EXTERNAL_ERROR_ASSOCIATION = "external_error_association"
    MISSING_MODULE_BOUNDARY = "missing_module_boundary"
    MISSING_MODULE_REFERENCE = "missing_module_reference"
    EXTERNAL_GUIDE = "external_guide"
    MODULE_PLACEHOLDER_REFERENCE = "module_placeholder_reference"
    MODULE_PARAMETER = "module_parameter"
    MODULE_SCRIPT = "module_script"
    MODULE_PARAMETER_UNAVAILABLE = "module_parameter_unavailable"
    MODULE_PARAMETER_FOLLOWUP = "module_parameter_followup"
    MODULE_REFERENCE = "module_reference"
    GLOBAL_PARAMETER_DISAMBIGUATION = "global_parameter_disambiguation"
    GLOBAL_PARAMETER = "global_parameter"
    MODULE_OVERVIEW = "module_overview"
    FALLBACK_BOUNDARY = "fallback_boundary"


def normalize_response_mode(value: str | ResponseMode | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ResponseMode.DOC
    try:
        return ResponseMode(candidate)
    except ValueError:
        return candidate


def normalize_resolver_path(values: Iterable[str | ResolverPath] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or ():
        candidate = str(value or "").strip()
        if not candidate:
            continue
        try:
            normalized.append(ResolverPath(candidate))
        except ValueError:
            normalized.append(candidate)
    return normalized
