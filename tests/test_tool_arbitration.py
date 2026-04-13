from __future__ import annotations

from sentieon_assist.boundary_pack import BoundaryPack, BoundaryRule
from sentieon_assist.reference_intents import ReferenceIntent
from sentieon_assist.support_coordinator import SupportRouteDecision
from sentieon_assist.support_contracts import BoundaryOutcome, FallbackMode, SupportIntent, ToolRequirement
from sentieon_assist.tool_arbitration import arbitrate_tool_action


def _route(*, support_intent: str, fallback_mode: str = "", vendor_version: str = "202603.01") -> SupportRouteDecision:
    return SupportRouteDecision(
        task="troubleshooting",
        issue_type="license",
        parsed_intent=ReferenceIntent(),
        info={"version": vendor_version, "input_type": "bam"},
        reason="issue_type:license",
        support_intent=support_intent,
        fallback_mode=fallback_mode,
        vendor_id="sentieon",
        vendor_version=vendor_version,
        explicit=True,
    )


def test_arbitration_defaults_to_should_answer_when_no_boundary_applies():
    decision = arbitrate_tool_action(
        "explain the support flow",
        route_decision=_route(support_intent=SupportIntent.CONCEPT_UNDERSTANDING),
        boundary_pack=BoundaryPack(),
    )

    assert decision.outcome == BoundaryOutcome.SHOULD_ANSWER


def test_arbitration_demands_tool_when_intent_is_tool_required():
    decision = arbitrate_tool_action(
        "validate the next step",
        route_decision=_route(support_intent=SupportIntent.VALIDATION_NEXT_STEP),
        boundary_pack=BoundaryPack(),
    )

    assert decision.outcome == BoundaryOutcome.MUST_TOOL


def test_arbitration_demands_clarification_for_matching_boundary_rule():
    pack = BoundaryPack(
        rules=(
            BoundaryRule(
                name="needs_more_info",
                outcome=BoundaryOutcome.MUST_CLARIFY,
                boundary_tags=("clarify-open",),
                cues=("need more info",),
                tool_requirement=ToolRequirement.NONE,
            ),
        )
    )

    decision = arbitrate_tool_action(
        "need more info",
        route_decision=_route(support_intent=SupportIntent.CONCEPT_UNDERSTANDING),
        boundary_pack=pack,
        boundary_tags=["clarify-open"],
    )

    assert decision.outcome == BoundaryOutcome.MUST_CLARIFY


def test_arbitration_demands_refusal_or_escalation_from_boundary_and_version():
    pack = BoundaryPack(
        rules=(
            BoundaryRule(
                name="policy_refusal",
                outcome=BoundaryOutcome.MUST_REFUSE,
                boundary_tags=("policy",),
                cues=("refuse",),
            ),
        )
    )

    refusal = arbitrate_tool_action(
        "refuse this request",
        route_decision=_route(support_intent=SupportIntent.CONCEPT_UNDERSTANDING),
        boundary_pack=pack,
        boundary_tags=["policy"],
    )
    assert refusal.outcome == BoundaryOutcome.MUST_REFUSE

    escalated = arbitrate_tool_action(
        "latest version check",
        route_decision=_route(
            support_intent=SupportIntent.CONCEPT_UNDERSTANDING,
            fallback_mode=FallbackMode.UNSUPPORTED_VERSION,
        ),
        boundary_pack=BoundaryPack(),
    )
    assert escalated.outcome == BoundaryOutcome.MUST_ESCALATE
