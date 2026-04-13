from __future__ import annotations

import pytest

from sentieon_assist.boundary_pack import BoundaryPack, BoundaryRule, select_boundary_rule
from sentieon_assist.support_contracts import BoundaryOutcome, SupportIntent, ToolRequirement


def test_boundary_pack_from_mapping_normalizes_rules_and_versions():
    pack = BoundaryPack.from_mapping(
        {
            "schema_version": " 2.1 ",
            "pack_version": " 2026.04 ",
            "rules": [
                {
                    "name": "tool_required",
                    "outcome": "must_tool",
                    "boundary_tags": ["tool"],
                    "cues": ["need a tool"],
                    "tool_requirement": "required",
                    "support_intents": ["validation_next_step"],
                    "min_version": "202503.03",
                }
            ],
        }
    )

    assert pack.schema_version == "2.1"
    assert pack.pack_version == "2026.04"
    assert len(pack.rules) == 1
    assert pack.rules[0].outcome == BoundaryOutcome.MUST_TOOL
    assert pack.rules[0].tool_requirement == ToolRequirement.REQUIRED
    assert pack.rules[0].support_intents == (SupportIntent.VALIDATION_NEXT_STEP,)


def test_select_boundary_rule_prefers_boundary_tags_and_respects_version_gate():
    pack = BoundaryPack(
        schema_version="2.1",
        pack_version="2026.04",
        rules=(
            BoundaryRule(
                name="version_gate",
                outcome=BoundaryOutcome.MUST_CLARIFY,
                boundary_tags=("clarify-open",),
                cues=("need version",),
                min_version="202600",
            ),
            BoundaryRule(
                name="tool_gate",
                outcome=BoundaryOutcome.MUST_TOOL,
                boundary_tags=("tool-required",),
                cues=("use a tool",),
                tool_requirement=ToolRequirement.REQUIRED,
                support_intents=(SupportIntent.VALIDATION_NEXT_STEP,),
            ),
        ),
    )

    selected = select_boundary_rule(
        "please use a tool",
        pack,
        boundary_tags=["tool-required"],
        info={"version": "202603.01"},
        support_intent=SupportIntent.VALIDATION_NEXT_STEP,
    )

    assert selected is not None
    assert selected.name == "tool_gate"

    assert (
        select_boundary_rule(
            "need version to proceed",
            pack,
            boundary_tags=["clarify-open"],
            info={"version": "202503.01"},
            support_intent=SupportIntent.CONCEPT_UNDERSTANDING,
        )
        is None
    )


def test_boundary_pack_rejects_invalid_boundary_pack_entries():
    with pytest.raises(ValueError, match="unsupported boundary outcome"):
        BoundaryPack.from_mapping(
            {
                "rules": [
                    {
                        "name": "bad-rule",
                        "outcome": "unknown",
                    }
                ]
            }
        )
