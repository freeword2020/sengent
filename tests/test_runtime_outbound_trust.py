from __future__ import annotations

from sentieon_assist.runtime_outbound_trust import (
    build_reference_answer_outbound_trust,
    build_reference_intent_outbound_trust,
    build_support_answer_outbound_trust,
)


def test_build_support_answer_outbound_trust_scrubs_sensitive_text_and_tracks_policy():
    result = build_support_answer_outbound_trust(
        issue_type="license",
        query=(
            "Please inspect /Users/alice/project/run.log, contact alice@example.com, "
            "and note token=secret-token-1234567890."
        ),
        info={
            "version": "202503.03",
            "error": "/private/tmp/license.err",
            "contact": "bob@example.com",
            "auth": "api_key=top-secret-token",
        },
        source_context={
            "primary_release": "202503.03",
            "primary_date": "2026-04-13",
            "primary_reference": "/Users/alice/docs/Sentieon Guide.pdf",
        },
        evidence=[
            {
                "name": "license note",
                "snippet": "see /opt/sentieon/conf and token=abc123",
                "trust": "vendor",
            }
        ],
    )

    assert result.policy_name == "support-answer-outbound-v1"
    assert result.issue_type == "license"
    assert "[PATH]" in result.query
    assert "[EMAIL]" in result.query
    assert "[REDACTED]" in result.query
    assert "/Users/alice/project/run.log" not in result.query
    assert "alice@example.com" not in result.query
    assert "secret-token-1234567890" not in result.query
    assert result.info["error"] == "[PATH]"
    assert result.info["contact"] == "[EMAIL]"
    assert result.info["auth"] == "api_key=[REDACTED]"
    assert result.source_context["primary_reference"] == "[PATH]"
    assert result.evidence[0]["snippet"] == "see [PATH] and token=[REDACTED]"
    assert result.trust_boundary_result.decision.policy_name == "support-answer-outbound-v1"
    assert result.trust_boundary_result.summary["allowed_count"] >= 1
    assert result.trust_boundary_result.summary["redacted_count"] >= 4
    assert result.trust_boundary_result.summary["local_only_count"] == 0


def test_build_reference_answer_outbound_trust_scrubs_source_context_and_evidence():
    result = build_reference_answer_outbound_trust(
        query="DNAscope guide for alice@example.com at /Users/alice/project/run.log",
        source_context={
            "primary_release": "202503.03",
            "primary_reference": "/Users/alice/docs/DNAscope Guide.pdf",
        },
        evidence=[
            {
                "name": "reference note",
                "snippet": "the file lives at /opt/sentieon/guide.md and token=ref-secret-123",
                "trust": "vendor",
            }
        ],
    )

    assert result.policy_name == "reference-answer-outbound-v1"
    assert "[PATH]" in result.query
    assert "[EMAIL]" in result.query
    assert result.source_context["primary_reference"] == "[PATH]"
    assert result.evidence[0]["snippet"] == "the file lives at [PATH] and token=[REDACTED]"
    assert result.raw_response == ""
    assert result.trust_boundary_result.decision.policy_name == "reference-answer-outbound-v1"
    assert result.trust_boundary_result.summary["redacted_count"] >= 3
    assert result.trust_boundary_result.summary["local_only_count"] == 0


def test_build_reference_intent_outbound_trust_scrubs_query_only():
    result = build_reference_intent_outbound_trust(
        query="What is DNAscope? see /Users/alice/project/run.log and alice@example.com token=ref-secret-123",
    )

    assert result.policy_name == "reference-intent-outbound-v1"
    assert result.query.startswith("What is DNAscope?")
    assert "[PATH]" in result.query
    assert "[EMAIL]" in result.query
    assert "[REDACTED]" in result.query
    assert result.info == {}
    assert result.source_context == {}
    assert result.evidence == ()
    assert result.raw_response == ""
    assert result.trust_boundary_result.decision.policy_name == "reference-intent-outbound-v1"
    assert result.trust_boundary_result.summary["item_count"] >= 1
    assert result.trust_boundary_result.summary["redacted_count"] >= 1
