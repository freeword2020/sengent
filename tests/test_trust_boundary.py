from __future__ import annotations

from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryDecision,
    build_trust_boundary_result,
    filter_local_only_context_items,
    redact_outbound_context_item,
    sanitize_trust_boundary_summary,
)


def test_trust_boundary_filters_local_only_items_and_preserves_redacted_provenance():
    items = [
        OutboundContextItem(
            key="user_email",
            value="alice@example.com",
            disposition=OutboundContextDisposition.REDACTED,
            provenance={"source": "profile"},
        ),
        OutboundContextItem(
            key="api_token",
            value="secret-token",
            disposition=OutboundContextDisposition.LOCAL_ONLY,
            provenance={"source": "env"},
        ),
    ]

    filtered = filter_local_only_context_items(items)
    assert len(filtered) == 1
    assert filtered[0].key == "user_email"
    redacted = redact_outbound_context_item(filtered[0])
    assert redacted.value == "[REDACTED]"
    assert redacted.provenance == {"source": "profile"}


def test_trust_boundary_result_summary_does_not_include_raw_sensitive_values():
    decision = TrustBoundaryDecision(
        policy_name="hosted-llm",
        items=(
            OutboundContextItem(
                key="session_secret",
                value="super-secret",
                disposition=OutboundContextDisposition.LOCAL_ONLY,
                provenance={"source": "runtime"},
            ),
            OutboundContextItem(
                key="module_name",
                value="DNAscope",
                disposition=OutboundContextDisposition.ALLOWED,
                provenance={"source": "catalog"},
            ),
        ),
    )

    result = build_trust_boundary_result(decision)

    assert result.summary["allowed_count"] == 1
    assert result.summary["local_only_count"] == 1
    assert result.summary["redacted_count"] == 0
    assert "super-secret" not in str(result.summary)


def test_sanitize_trust_boundary_summary_drops_unknown_keys_and_sensitive_values():
    summary = sanitize_trust_boundary_summary(
        {
            "policy_name": "hosted-llm",
            "allowed_count": 1,
            "allowed_keys": ["module_name"],
            "leaked_value": "super-secret",
        }
    )

    assert summary["policy_name"] == "hosted-llm"
    assert summary["allowed_count"] == 1
    assert summary["allowed_keys"] == ["module_name"]
    assert "leaked_value" not in summary
    assert "super-secret" not in str(summary)
