from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from sentieon_assist.boundary_pack import BoundaryPack, default_boundary_pack, select_boundary_rule
from sentieon_assist.support_contracts import (
    BoundaryOutcome,
    FallbackMode,
    SupportIntent,
    ToolRequirement,
    normalize_boundary_outcome,
    normalize_fallback_mode,
    normalize_support_intent,
    normalize_tool_requirement,
    tool_requirement_for_support_intent,
)


@dataclass(frozen=True)
class ToolArbitrationDecision:
    action: str = BoundaryOutcome.SHOULD_ANSWER
    reason: str = ""
    rule_id: str = ""
    support_intent: str = SupportIntent.CONCEPT_UNDERSTANDING
    fallback_mode: str = FallbackMode.NONE
    tool_requirement: str = ToolRequirement.NONE
    matched_boundary_tags: tuple[str, ...] = ()

    @property
    def outcome(self) -> str:
        return self.action


def _normalize_tags(values: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in (values or []) if str(item).strip())


def _has_tool_context(info: Mapping[str, str] | None) -> bool:
    context = info or {}
    evidence_fields = ("version", "input_type", "error", "step", "data_type")
    return any(str(context.get(field, "")).strip() for field in evidence_fields)


def _effective_tool_requirement(parsed_intent: Any | None, support_intent: str) -> str:
    intent_requirement = normalize_tool_requirement(getattr(parsed_intent, "tool_requirement", ""))
    if intent_requirement == ToolRequirement.REQUIRED:
        return ToolRequirement.REQUIRED
    return normalize_tool_requirement(tool_requirement_for_support_intent(support_intent))


def arbitrate_support_action(
    query: str,
    *,
    issue_type: str,
    support_intent: str | SupportIntent | None,
    info: Mapping[str, str] | None,
    vendor_version: str = "",
    parsed_intent: Any | None = None,
    fallback_mode: str | FallbackMode | None = None,
    boundary_pack: BoundaryPack | None = None,
    boundary_tags: Sequence[str] | None = None,
) -> ToolArbitrationDecision:
    normalized_support_intent = normalize_support_intent(support_intent)
    normalized_fallback_mode = normalize_fallback_mode(fallback_mode)
    normalized_info = dict(info or {})
    normalized_tags = _normalize_tags(boundary_tags)
    effective_tool_requirement = _effective_tool_requirement(parsed_intent, normalized_support_intent)

    selected_rule = select_boundary_rule(
        query,
        boundary_pack or default_boundary_pack(),
        boundary_tags=normalized_tags,
        info={"version": vendor_version or str(normalized_info.get("version", "")).strip()},
        support_intent=normalized_support_intent,
    )
    if selected_rule is not None:
        selected_outcome = normalize_boundary_outcome(selected_rule.outcome)
        rule_tool_requirement = normalize_tool_requirement(selected_rule.tool_requirement)
        if selected_outcome == BoundaryOutcome.SHOULD_ANSWER and rule_tool_requirement == ToolRequirement.REQUIRED:
            selected_outcome = BoundaryOutcome.MUST_TOOL
            effective_tool_requirement = ToolRequirement.REQUIRED
        return ToolArbitrationDecision(
            action=selected_outcome,
            reason=selected_rule.reason or f"boundary_rule:{selected_rule.name}",
            rule_id=selected_rule.name,
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=rule_tool_requirement if rule_tool_requirement else effective_tool_requirement,
            matched_boundary_tags=tuple(selected_rule.boundary_tags),
        )

    if normalized_fallback_mode == FallbackMode.UNSUPPORTED_VERSION:
        return ToolArbitrationDecision(
            action=BoundaryOutcome.MUST_ESCALATE,
            reason="fallback_mode:unsupported-version",
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=effective_tool_requirement,
        )
    if normalized_fallback_mode == FallbackMode.CLARIFICATION_OPEN:
        return ToolArbitrationDecision(
            action=BoundaryOutcome.MUST_CLARIFY,
            reason="fallback_mode:clarification-open",
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=effective_tool_requirement,
        )
    if normalized_fallback_mode == FallbackMode.NO_ANSWER_WITH_BOUNDARY:
        return ToolArbitrationDecision(
            action=BoundaryOutcome.MUST_REFUSE,
            reason="fallback_mode:no-answer-with-boundary",
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=effective_tool_requirement,
        )
    if normalized_fallback_mode == FallbackMode.CONFLICTING_EVIDENCE:
        return ToolArbitrationDecision(
            action=BoundaryOutcome.MUST_ESCALATE,
            reason="fallback_mode:conflicting-evidence",
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=effective_tool_requirement,
        )

    if effective_tool_requirement == ToolRequirement.REQUIRED:
        if normalized_support_intent == SupportIntent.TROUBLESHOOTING and issue_type != "other" and not _has_tool_context(normalized_info):
            return ToolArbitrationDecision(
                action=BoundaryOutcome.MUST_CLARIFY,
                reason="tool_required_needs_more_context",
                support_intent=normalized_support_intent,
                fallback_mode=normalized_fallback_mode,
                tool_requirement=effective_tool_requirement,
            )
        return ToolArbitrationDecision(
            action=BoundaryOutcome.MUST_TOOL,
            reason="tool_required_intent",
            support_intent=normalized_support_intent,
            fallback_mode=normalized_fallback_mode,
            tool_requirement=effective_tool_requirement,
            matched_boundary_tags=normalized_tags,
        )

    return ToolArbitrationDecision(
        action=BoundaryOutcome.SHOULD_ANSWER,
        reason="conservative-default",
        support_intent=normalized_support_intent,
        fallback_mode=normalized_fallback_mode,
        tool_requirement=effective_tool_requirement,
        matched_boundary_tags=normalized_tags,
    )


def arbitrate_tool_action(
    query: str,
    *,
    route_decision: Any,
    boundary_pack: BoundaryPack | None = None,
    boundary_tags: Sequence[str] | None = None,
    info: Mapping[str, str] | None = None,
) -> ToolArbitrationDecision:
    return arbitrate_support_action(
        query,
        issue_type=str(getattr(route_decision, "issue_type", "")).strip(),
        support_intent=str(getattr(route_decision, "support_intent", "")).strip(),
        info=info or getattr(route_decision, "info", {}) or {},
        vendor_version=str(getattr(route_decision, "vendor_version", "")).strip(),
        parsed_intent=getattr(route_decision, "parsed_intent", None),
        fallback_mode=str(getattr(route_decision, "fallback_mode", "")).strip(),
        boundary_pack=boundary_pack,
        boundary_tags=boundary_tags,
    )


__all__ = [
    "ToolArbitrationDecision",
    "arbitrate_support_action",
    "arbitrate_tool_action",
]
