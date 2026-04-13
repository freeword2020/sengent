from __future__ import annotations

import json
from pathlib import Path

from sentieon_assist.session_events import (
    SCHEMA_VERSION,
    SupportSessionRecord,
    append_session_record,
    append_turn_event,
    build_turn_event,
    load_selected_turn_views,
    load_turn_views,
    session_log_path,
    turn_view_from_event,
)
from sentieon_assist.trace_vocab import ResolverPath, ResponseMode, normalize_resolver_path, normalize_response_mode
from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryDecision,
    build_trust_boundary_result,
)


def test_session_event_log_round_trip_produces_unified_turn_view(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory=str(tmp_path / "sentieon-note"),
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)

    turn_event = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="DNAscope 是做什么的",
        effective_query="DNAscope 是做什么的",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="module_intro",
        parsed_intent_intent="module_intro",
        parsed_intent_module="DNAscope",
        response_text="【模块介绍】\nDNAscope：用于 germline variant calling",
        response_mode="module_intro",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
    )
    append_turn_event(turn_event, runtime_root=runtime_root)

    assert session.schema_version == SCHEMA_VERSION
    assert session_log_path(session.session_id, runtime_root=runtime_root).exists()

    views = load_turn_views(session.session_id, runtime_root=runtime_root)

    assert len(views) == 1
    view = views[0]
    assert view.session_id == session.session_id
    assert view.turn_index == 1
    assert view.prompt == "DNAscope 是做什么的"
    assert view.route_reason == "module_intro"
    assert view.parsed_intent_module == "DNAscope"
    assert view.response.startswith("【模块介绍】")


def test_load_selected_turn_views_preserves_requested_turn_order(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)

    first = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="第一问",
        effective_query="第一问",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="reference_other",
        parsed_intent_intent="reference_other",
        parsed_intent_module="",
        response_text="【资料说明】\n- A",
        response_mode="doc",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
    )
    second = build_turn_event(
        session_id=session.session_id,
        turn_index=2,
        raw_query="第二问",
        effective_query="第一问 第二问",
        reused_anchor=True,
        task="reference_lookup",
        issue_type="other",
        route_reason="reference_other",
        parsed_intent_intent="reference_other",
        parsed_intent_module="",
        response_text="【资料说明】\n- B",
        response_mode="doc",
        state_before={"active_task": "reference_lookup"},
        state_after={"active_task": "reference_lookup"},
    )
    append_turn_event(first, runtime_root=runtime_root)
    append_turn_event(second, runtime_root=runtime_root)

    selected = load_selected_turn_views(
        session.session_id,
        [second.turn_id, first.turn_id],
        runtime_root=runtime_root,
    )

    assert [view.prompt for view in selected] == ["第二问", "第一问"]


def test_build_turn_event_normalizes_trace_vocab_values():
    turn_event = build_turn_event(
        session_id="session-1",
        turn_index=1,
        raw_query="第一问",
        effective_query="第一问",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="reference_other",
        parsed_intent_intent="reference_other",
        parsed_intent_module="",
        response_text="【资料说明】\n- A",
        response_mode="",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
        resolver_path=[ResolverPath.DOC_REFERENCE, "", "future_path"],
    )

    assert turn_event.answer["response_mode"] == ResponseMode.DOC
    assert turn_event.answer["resolver_path"] == [ResolverPath.DOC_REFERENCE, "future_path"]


def test_session_event_round_trip_preserves_gap_record(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)

    turn_event = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="license 报错",
        effective_query="license 报错",
        reused_anchor=False,
        task="troubleshooting",
        issue_type="license",
        route_reason="issue_type:license",
        support_intent="troubleshooting",
        fallback_mode="clarification-open",
        vendor_id="sentieon",
        vendor_version="202503.03",
        parsed_intent_intent="not_reference",
        parsed_intent_module="",
        response_text="需要补充以下信息：Sentieon 版本",
        response_mode="clarify",
        state_before={"active_task": "idle"},
        state_after={"active_task": "troubleshooting"},
        gap_record={
            "vendor_id": "sentieon",
            "vendor_version": "202503.03",
            "intent": "troubleshooting",
            "gap_type": "clarification_open",
            "user_question": "license 报错",
            "known_context": {"error": "license 报错"},
            "missing_materials": ["Sentieon 版本"],
            "captured_at": "2026-04-13T00:00:00+00:00",
            "status": "open",
        },
    )
    append_turn_event(turn_event, runtime_root=runtime_root)

    view = load_turn_views(session.session_id, runtime_root=runtime_root)[0]

    assert view.gap_record is not None
    assert view.gap_record["gap_type"] == "clarification_open"
    assert view.gap_record["missing_materials"] == ["Sentieon 版本"]


def test_session_event_round_trip_preserves_trust_boundary_summary_without_raw_sensitive_values(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)

    trust_boundary = build_trust_boundary_result(
        TrustBoundaryDecision(
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
    )

    turn_event = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="DNAscope 是做什么的",
        effective_query="DNAscope 是做什么的",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="module_intro",
        parsed_intent_intent="module_intro",
        parsed_intent_module="DNAscope",
        response_text="【模块介绍】\nDNAscope：用于 germline variant calling",
        response_mode="module_intro",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
        trust_boundary_result=trust_boundary,
    )
    append_turn_event(turn_event, runtime_root=runtime_root)

    view = load_turn_views(session.session_id, runtime_root=runtime_root)[0]
    assert view.trust_boundary_summary is not None
    assert view.trust_boundary_summary["allowed_count"] == 1
    assert view.trust_boundary_summary["local_only_count"] == 1
    assert "super-secret" not in json.dumps(view.trust_boundary_summary, ensure_ascii=False)


def test_session_event_sanitizes_trust_boundary_summary_dict_input(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)

    turn_event = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="DNAscope 是做什么的",
        effective_query="DNAscope 是做什么的",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="module_intro",
        parsed_intent_intent="module_intro",
        parsed_intent_module="DNAscope",
        response_text="【模块介绍】\nDNAscope：用于 germline variant calling",
        response_mode="module_intro",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
        trust_boundary_result={
            "policy_name": "hosted-llm",
            "allowed_count": 1,
            "allowed_keys": ["module_name"],
            "leaked_value": "super-secret",
        },
    )
    append_turn_event(turn_event, runtime_root=runtime_root)

    view = load_turn_views(session.session_id, runtime_root=runtime_root)[0]
    assert view.trust_boundary_summary is not None
    assert view.trust_boundary_summary["policy_name"] == "hosted-llm"
    assert view.trust_boundary_summary["allowed_count"] == 1
    assert "leaked_value" not in view.trust_boundary_summary
    assert "super-secret" not in json.dumps(view.trust_boundary_summary, ensure_ascii=False)


def test_turn_view_from_event_normalizes_legacy_blank_response_mode():
    view = turn_view_from_event(
        {
            "event_type": "turn_resolved",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "turn_index": 1,
            "planner": {
                "raw_query": "第一问",
                "effective_query": "第一问",
                "reused_anchor": False,
                "task": "reference_lookup",
                "issue_type": "other",
                "route_reason": "reference_other",
                "parsed_intent": {"intent": "reference_other", "module": ""},
            },
            "answer": {
                "response_text": "【资料说明】\n- A",
                "response_mode": "",
                "resolver_path": ["", "future_path"],
            },
        }
    )

    assert view.response_mode == ResponseMode.DOC


def test_trace_vocab_normalizers_keep_known_values_and_preserve_future_extensions():
    assert normalize_response_mode(ResponseMode.SCRIPT) == ResponseMode.SCRIPT
    assert normalize_response_mode("") == ResponseMode.DOC
    assert normalize_resolver_path([ResolverPath.DOC_REFERENCE, "", "future_path"]) == [
        ResolverPath.DOC_REFERENCE,
        "future_path",
    ]
