from __future__ import annotations

from pathlib import Path

from sentieon_assist.feedback_runtime import build_feedback_record


def test_build_feedback_record_references_session_and_turn_ids(tmp_path: Path):
    feedback_path = tmp_path / "runtime-feedback.jsonl"

    record = build_feedback_record(
        scope="session",
        session_id="sess-1",
        selected_turn_ids=["turn-1", "turn-2"],
        summary="第二轮才给脚本",
        expected_answer="第一轮先明确下一步",
        expected_mode="script",
        expected_task="reference_lookup",
        feedback_path=feedback_path,
    )

    assert record["scope"] == "session"
    assert record["session_id"] == "sess-1"
    assert record["selected_turn_ids"] == ["turn-1", "turn-2"]
    assert record["scorable"] is True
    assert "captured_turns" not in record
