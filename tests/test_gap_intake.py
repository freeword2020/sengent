from __future__ import annotations

from pathlib import Path

import yaml

from sentieon_assist.gap_intake import export_gap_turn_to_inbox
from sentieon_assist.session_events import SupportSessionRecord, append_session_record, append_turn_event, build_turn_event


def _create_gap_session(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    inbox_directory = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_directory.mkdir(parents=True)

    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)
    return runtime_root, inbox_directory, session


def _write_turn(
    *,
    session_id: str,
    runtime_root: Path,
    turn_index: int,
    raw_query: str,
    gap_record: dict[str, object] | None,
):
    event = build_turn_event(
        session_id=session_id,
        turn_index=turn_index,
        raw_query=raw_query,
        effective_query=raw_query,
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
        gap_record=gap_record,
    )
    append_turn_event(event, runtime_root=runtime_root)
    return event


def test_export_gap_turn_to_inbox_writes_explicit_turn_artifacts(tmp_path: Path):
    runtime_root, inbox_directory, session = _create_gap_session(tmp_path)
    turn = _write_turn(
        session_id=session.session_id,
        runtime_root=runtime_root,
        turn_index=1,
        raw_query="license 报错",
        gap_record={
            "vendor_id": "sentieon",
            "vendor_version": "202503.03",
            "intent": "troubleshooting",
            "gap_type": "clarification_open",
            "user_question": "license 报错",
            "known_context": {"error": "license 报错", "version": "202503.03"},
            "missing_materials": ["Sentieon 版本"],
            "captured_at": "2026-04-13T00:00:00+00:00",
            "status": "open",
        },
    )

    result = export_gap_turn_to_inbox(
        session_id=session.session_id,
        inbox_directory=inbox_directory,
        runtime_root=runtime_root,
        turn_id=turn.turn_id,
    )

    assert result.session_id == session.session_id
    assert result.turn_id == turn.turn_id
    assert result.gap_type == "clarification_open"
    assert result.markdown_path.exists()
    assert result.metadata_path.exists()

    metadata = yaml.safe_load(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["pack_target"] == "incident-memory.json"
    assert metadata["entry_type"] == "incident"
    assert metadata["action"] == "upsert"
    assert metadata["origin"] == "runtime-gap-capture"
    assert metadata["gap_type"] == "clarification_open"
    assert metadata["vendor_version"] == "202503.03"
    assert metadata["missing_materials"] == ["Sentieon 版本"]
    assert "license 报错" in result.markdown_path.read_text(encoding="utf-8")


def test_export_gap_turn_to_inbox_selects_latest_gap_when_requested(tmp_path: Path):
    runtime_root, inbox_directory, session = _create_gap_session(tmp_path)
    _write_turn(
        session_id=session.session_id,
        runtime_root=runtime_root,
        turn_index=1,
        raw_query="first",
        gap_record={
            "vendor_id": "sentieon",
            "vendor_version": "202503.03",
            "intent": "troubleshooting",
            "gap_type": "clarification_open",
            "user_question": "first",
            "known_context": {"note": "first"},
            "missing_materials": ["one"],
            "captured_at": "2026-04-13T00:00:00+00:00",
            "status": "open",
        },
    )
    latest_turn = _write_turn(
        session_id=session.session_id,
        runtime_root=runtime_root,
        turn_index=2,
        raw_query="second",
        gap_record={
            "vendor_id": "sentieon",
            "vendor_version": "202503.03",
            "intent": "troubleshooting",
            "gap_type": "unsupported_version",
            "user_question": "second",
            "known_context": {"note": "second"},
            "missing_materials": ["two"],
            "captured_at": "2026-04-13T00:00:01+00:00",
            "status": "open",
        },
    )

    result = export_gap_turn_to_inbox(
        session_id=session.session_id,
        inbox_directory=inbox_directory,
        runtime_root=runtime_root,
        latest=True,
    )

    assert result.turn_id == latest_turn.turn_id
    assert result.gap_type == "unsupported_version"
    assert result.markdown_path.name.startswith(f"{session.session_id}.")


def test_export_gap_turn_to_inbox_rejects_turns_without_gap_record(tmp_path: Path):
    runtime_root, inbox_directory, session = _create_gap_session(tmp_path)
    turn = _write_turn(
        session_id=session.session_id,
        runtime_root=runtime_root,
        turn_index=1,
        raw_query="plain response",
        gap_record=None,
    )

    try:
        export_gap_turn_to_inbox(
            session_id=session.session_id,
            inbox_directory=inbox_directory,
            runtime_root=runtime_root,
            turn_id=turn.turn_id,
        )
    except ValueError as error:
        assert "gap_record" in str(error)
    else:
        raise AssertionError("expected export_gap_turn_to_inbox to reject a turn without gap_record")


def test_export_gap_turn_to_inbox_uses_deterministic_file_names(tmp_path: Path):
    runtime_root, inbox_directory, session = _create_gap_session(tmp_path)
    turn = _write_turn(
        session_id=session.session_id,
        runtime_root=runtime_root,
        turn_index=1,
        raw_query="license 报错",
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

    first = export_gap_turn_to_inbox(
        session_id=session.session_id,
        inbox_directory=inbox_directory,
        runtime_root=runtime_root,
        turn_id=turn.turn_id,
    )
    second = export_gap_turn_to_inbox(
        session_id=session.session_id,
        inbox_directory=inbox_directory,
        runtime_root=runtime_root,
        turn_id=turn.turn_id,
    )

    assert first.markdown_path == second.markdown_path
    assert first.metadata_path == second.metadata_path
    assert first.markdown_path.name == f"{session.session_id}.{turn.turn_id}.clarification_open.md"
    assert first.metadata_path.name == f"{session.session_id}.{turn.turn_id}.clarification_open.meta.yaml"
