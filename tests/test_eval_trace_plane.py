from __future__ import annotations

from sentieon_assist.eval_trace_plane import (
    aggregate_runtime_eval_traces,
    project_factory_eval_trace,
    project_runtime_eval_trace,
)


def test_project_runtime_eval_trace_captures_clarify_and_trust_boundary_signal():
    projection = project_runtime_eval_trace(
        {
            "planner": {
                "support_intent": "troubleshooting",
                "fallback_mode": "clarification_open",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
            },
            "answer": {
                "response_mode": "clarify",
                "sources": ["Sentieon202503.03.pdf"],
                "boundary_tags": [],
                "resolver_path": ["troubleshooting_knowledge_gap"],
                "gap_record": {"gap_type": "clarification_open"},
            },
            "trust_boundary_summary": {
                "policy_name": "hosted-llm",
                "allowed_count": 1,
                "local_only_count": 2,
                "redacted_count": 0,
            },
        }
    )

    assert projection["boundary_adherence"] == "clarify"
    assert projection["clarify_required"] is True
    assert projection["tool_required"] is False
    assert projection["evidence_fidelity"] == "source_grounded"
    assert projection["trust_boundary_policy_name"] == "hosted-llm"
    assert projection["trust_boundary_local_only_count"] == 2


def test_project_runtime_eval_trace_captures_trust_boundary_audit_presence_and_posture():
    projection = project_runtime_eval_trace(
        {
            "planner": {
                "support_intent": "troubleshooting",
                "fallback_mode": "clarification_open",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
            },
            "answer": {
                "response_mode": "clarify",
                "sources": ["Sentieon202503.03.pdf"],
                "boundary_tags": [],
                "resolver_path": ["troubleshooting_knowledge_gap"],
                "gap_record": {"gap_type": "clarification_open"},
            },
            "trust_boundary_summary": {
                "policy_name": "hosted-llm",
                "allowed_count": 1,
                "local_only_count": 1,
                "redacted_count": 1,
            },
            "trust_boundary_audit": [
                {
                    "key": "query",
                    "disposition": "redacted",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
                {
                    "key": "session_secret",
                    "disposition": "local_only",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
            ],
        }
    )

    assert projection["trust_boundary_audit_present"] is True
    assert projection["trust_boundary_audit_policy_name"] == "hosted-llm"
    assert projection["trust_boundary_audit_item_count"] == 2
    assert projection["trust_boundary_audit_redacted_count"] == 1
    assert projection["trust_boundary_audit_local_only_count"] == 1
    assert projection["trust_boundary_audit_provenance_only"] is True
    assert projection["trust_boundary_audit_posture"] == "provenance_only"


def test_project_runtime_eval_trace_marks_audit_as_mixed_when_raw_fields_are_present():
    projection = project_runtime_eval_trace(
        {
            "planner": {
                "support_intent": "troubleshooting",
                "fallback_mode": "clarification_open",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
            },
            "answer": {
                "response_mode": "clarify",
                "sources": ["Sentieon202503.03.pdf"],
                "boundary_tags": [],
                "resolver_path": ["troubleshooting_knowledge_gap"],
                "gap_record": {"gap_type": "clarification_open"},
            },
            "trust_boundary_summary": {
                "policy_name": "hosted-llm",
                "allowed_count": 1,
                "local_only_count": 1,
                "redacted_count": 1,
            },
            "trust_boundary_audit": [
                {
                    "key": "query",
                    "value": "license error",
                    "disposition": "redacted",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
                {
                    "key": "session_secret",
                    "raw_value": "super-secret",
                    "disposition": "local_only",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
            ],
        }
    )

    assert projection["trust_boundary_audit_present"] is True
    assert projection["trust_boundary_audit_item_count"] == 2
    assert projection["trust_boundary_audit_provenance_only"] is False
    assert projection["trust_boundary_audit_posture"] == "mixed"


def test_project_runtime_eval_trace_marks_arbitration_must_tool():
    projection = project_runtime_eval_trace(
        {
            "planner": {
                "support_intent": "troubleshooting",
                "fallback_mode": "",
            },
            "answer": {
                "response_mode": "boundary",
                "sources": [],
                "boundary_tags": ["must-tool"],
                "resolver_path": ["arbitration_must_tool"],
            },
        }
    )

    assert projection["boundary_adherence"] == "must_tool"
    assert projection["tool_required"] is True
    assert projection["evidence_fidelity"] == "contract_only"


def test_project_factory_eval_trace_preserves_lifecycle_and_review_metadata():
    projection = project_factory_eval_trace(
        {
            "draft_id": "factory-draft.dataset.001",
            "lifecycle_state": "review_needed",
            "review_status": "needs_review",
            "review_required": True,
            "trust_boundary_provenance": {
                "policy_name": "factory-draft-local-only",
                "local_only_count": 1,
                "redacted_count": 0,
                "allowed_count": 0,
            },
        }
    )

    assert projection["lifecycle_state"] == "review_needed"
    assert projection["review_status"] == "needs_review"
    assert projection["review_required"] is True
    assert projection["trust_boundary_policy_name"] == "factory-draft-local-only"
    assert projection["trust_boundary_local_only_count"] == 1
    assert projection["evidence_fidelity"] == "draft_only"


def test_aggregate_runtime_eval_traces_tracks_boundary_and_fidelity_summary():
    summary = aggregate_runtime_eval_traces(
        [
            {
                "boundary_adherence": "clarify",
                "evidence_fidelity": "source_grounded",
                "clarify_required": True,
                "tool_required": False,
                "refusal_required": False,
                "escalation_required": False,
                "trust_boundary_audit_present": True,
                "trust_boundary_audit_posture": "provenance_only",
            },
            {
                "boundary_adherence": "must_tool",
                "evidence_fidelity": "contract_only",
                "clarify_required": False,
                "tool_required": True,
                "refusal_required": False,
                "escalation_required": False,
                "trust_boundary_audit_present": True,
                "trust_boundary_audit_posture": "provenance_only",
            },
        ]
    )

    assert summary["boundary_adherence"] == "must_tool"
    assert summary["evidence_fidelity"] == "mixed"
    assert summary["clarify_turn_count"] == 1
    assert summary["tool_turn_count"] == 1
    assert summary["trust_boundary_audit_turn_count"] == 2
    assert summary["trust_boundary_audit_posture"] == "provenance_only"
