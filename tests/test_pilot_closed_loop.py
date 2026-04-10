from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sentieon_assist.pilot_readiness import (
    GateResult,
    PilotEvalFailure,
    PilotReadinessReport,
    PilotSuiteResult,
)

from sentieon_assist.pilot_closed_loop import (
    BaselineDelta,
    ClosedLoopScorecard,
    OptimizationFocusItem,
    build_optimization_queue,
    collect_bucket_counts,
    compare_against_baseline,
    format_pilot_closed_loop_summary,
    generate_tightening_recommendations,
    load_feedback_session_cases,
    load_feedback_single_turn_cases,
    load_runtime_feedback_intake,
    run_pilot_closed_loop,
    score_closed_loop_report,
)
from sentieon_assist.session_events import SupportSessionRecord, append_session_record, append_turn_event, build_turn_event


def _suite(name: str, failures: tuple[PilotEvalFailure, ...] = ()) -> PilotSuiteResult:
    return PilotSuiteResult(
        name=name,
        total=max(1, len(failures)),
        passed=max(1, len(failures)) - len(failures),
        failed=len(failures),
        failures=failures,
        mvp_fallback_hits=0,
        wrong_anchor_reuse_count=sum(1 for failure in failures if failure.bucket == "wrong_anchor_reuse"),
        wrong_reset_count=sum(1 for failure in failures if failure.bucket == "wrong_reset"),
    )


def _failure(bucket: str, *, suite: str = "pilot", case_id: str = "case-1") -> PilotEvalFailure:
    return PilotEvalFailure(
        suite=suite,
        case_id=case_id,
        turn_index=1,
        prompt="prompt",
        bucket=bucket,
        expected_mode="script",
        actual_mode="clarify",
        expected_task="reference_lookup",
        actual_task="onboarding_guidance",
        expected_reused_anchor=False,
        actual_reused_anchor=False,
        missing=["【参考命令】"],
        forbidden=[],
        response="【流程指导】\n- 先确认",
        route_reason="workflow_guidance",
        parsed_intent_intent="workflow_guidance",
        parsed_intent_module="",
        issue_type="other",
        effective_query="prompt",
    )


def _pilot_report(*, gate_ok: bool = True, pilot_failures: tuple[PilotEvalFailure, ...] = ()) -> PilotReadinessReport:
    return PilotReadinessReport(
        repo_root="/tmp/repo",
        source_directory="/tmp/repo/sentieon-note",
        gates=(GateResult(name="pytest", ok=gate_ok, summary="ok", details="ok", returncode=0 if gate_ok else 1),),
        pilot_single_turn=_suite("pilot-single-turn", pilot_failures),
        pilot_multi_turn=_suite("pilot-multi-turn"),
    )


def test_load_feedback_corpora():
    repo_root = Path(__file__).resolve().parent.parent

    single_turn_cases = load_feedback_single_turn_cases(repo_root)
    session_cases = load_feedback_session_cases(repo_root)

    assert single_turn_cases
    assert session_cases
    assert all(case.source for case in single_turn_cases)
    assert all(case.source for case in session_cases)


def test_load_runtime_feedback_intake_splits_scorable_and_pending(tmp_path: Path):
    runtime_path = tmp_path / "runtime-feedback.jsonl"
    runtime_root = tmp_path
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)
    first_turn = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="能提供个 joint call 参考脚本吗",
        effective_query="能提供个 joint call 参考脚本吗",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="script_example",
        parsed_intent_intent="script_example",
        parsed_intent_module="Joint Call",
        response_text="【参考命令】\n- sentieon driver --algo GVCFtyper ...",
        response_mode="script",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
    )
    append_turn_event(first_turn, runtime_root=runtime_root)
    runtime_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_id": "rt-1",
                        "source": "runtime-feedback",
                        "scope": "last",
                        "session_id": session.session_id,
                        "selected_turn_ids": [first_turn.turn_id],
                        "expected_mode": "script",
                        "expected_task": "reference_lookup",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "record_id": "rt-2",
                        "source": "runtime-feedback",
                        "scope": "session",
                        "session_id": session.session_id,
                        "selected_turn_ids": [first_turn.turn_id],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    single_turn_cases, session_cases, pending_count = load_runtime_feedback_intake(runtime_path, runtime_root=runtime_root)

    assert len(single_turn_cases) == 1
    assert len(session_cases) == 0
    assert pending_count == 1
    assert single_turn_cases[0].case_id == "rt-1"


def test_load_runtime_feedback_intake_accepts_legacy_captured_turns_records(tmp_path: Path):
    runtime_path = tmp_path / "runtime-feedback.jsonl"
    runtime_path.write_text(
        json.dumps(
            {
                "record_id": "legacy-1",
                "source": "runtime-feedback",
                "scope": "last",
                "expected_mode": "script",
                "expected_task": "reference_lookup",
                "captured_turns": [
                    {
                        "prompt": "能提供个 joint call 参考脚本吗",
                        "response": "【参考命令】\n- sentieon driver --algo GVCFtyper ...",
                        "task": "reference_lookup",
                        "response_mode": "script",
                        "reused_anchor": False,
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    single_turn_cases, session_cases, pending_count = load_runtime_feedback_intake(runtime_path)

    assert len(single_turn_cases) == 1
    assert len(session_cases) == 0
    assert pending_count == 0
    assert single_turn_cases[0].case_id == "legacy-1"
    assert single_turn_cases[0].prompt == "能提供个 joint call 参考脚本吗"


def test_run_pilot_closed_loop_accepts_explicit_runtime_root_for_pointer_feedback(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    runtime_root = tmp_path / "runtime"
    feedback_path = tmp_path / "exports" / "runtime-feedback.jsonl"
    feedback_path.parent.mkdir(parents=True)
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="",
        knowledge_directory="",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)
    turn = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="能提供个 joint call 参考脚本吗",
        effective_query="能提供个 joint call 参考脚本吗",
        reused_anchor=False,
        task="reference_lookup",
        issue_type="other",
        route_reason="script_example",
        parsed_intent_intent="script_example",
        parsed_intent_module="Joint Call",
        response_text="【参考命令】\n- sentieon driver --algo GVCFtyper ...",
        response_mode="script",
        state_before={"active_task": "idle"},
        state_after={"active_task": "reference_lookup"},
    )
    append_turn_event(turn, runtime_root=runtime_root)
    feedback_path.write_text(
        json.dumps(
            {
                "record_id": "rt-runtime-root",
                "source": "runtime-feedback",
                "scope": "last",
                "session_id": session.session_id,
                "selected_turn_ids": [turn.turn_id],
                "expected_mode": "script",
                "expected_task": "reference_lookup",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        return GateResult(name=name, ok=True, summary="pass", details="pass", returncode=0)

    report = run_pilot_closed_loop(
        repo_root,
        runtime_feedback_path=feedback_path,
        runtime_root=runtime_root,
        command_gate_runner=fake_gate_runner,
    )

    assert report.runtime_feedback_pending_count == 0
    assert report.runtime_feedback_single_turn.total == 1


def test_collect_bucket_counts_aggregates_all_suites():
    suites = (
        _suite("pilot-single-turn", (_failure("wrong_script_handoff"), _failure("misroute", case_id="case-2"))),
        _suite("feedback-single-turn", (_failure("wrong_script_handoff", suite="feedback"),)),
    )

    counts = collect_bucket_counts(suites)

    assert counts["wrong_script_handoff"] == 2
    assert counts["misroute"] == 1


def test_score_closed_loop_report_penalizes_gate_and_bucket_failures():
    pilot_report = _pilot_report(gate_ok=False, pilot_failures=(_failure("wrong_reset"),))
    feedback_single_turn = _suite("feedback-single-turn", (_failure("wrong_script_handoff", suite="feedback"),))
    feedback_multi_turn = _suite("feedback-multi-turn", (_failure("over_clarify", suite="feedback", case_id="case-3"),))

    scorecard = score_closed_loop_report(
        pilot_report,
        feedback_single_turn=feedback_single_turn,
        feedback_multi_turn=feedback_multi_turn,
    )

    assert isinstance(scorecard, ClosedLoopScorecard)
    assert scorecard.quality_score < 100
    assert scorecard.gate_failures == 1
    assert scorecard.bucket_counts["wrong_reset"] == 1
    assert scorecard.risk_level == "critical"


def test_compare_against_baseline_reports_score_and_bucket_delta():
    scorecard = ClosedLoopScorecard(
        quality_score=82,
        risk_level="elevated",
        gate_failures=0,
        bucket_counts={"wrong_script_handoff": 2, "misroute": 1},
        mvp_fallback_hits=0,
        wrong_reset_count=0,
    )
    baseline_payload = {
        "scorecard": {
            "quality_score": 90,
            "bucket_counts": {"wrong_script_handoff": 1, "misroute": 3},
        }
    }

    delta = compare_against_baseline(scorecard, baseline_payload)

    assert isinstance(delta, BaselineDelta)
    assert delta.score_delta == -8
    assert delta.bucket_deltas["wrong_script_handoff"] == 1
    assert delta.bucket_deltas["misroute"] == -2


def test_generate_tightening_recommendations_orders_high_risk_buckets_first():
    scorecard = ClosedLoopScorecard(
        quality_score=72,
        risk_level="elevated",
        gate_failures=0,
        bucket_counts={
            "over_clarify": 3,
            "wrong_reset": 1,
            "wrong_script_handoff": 2,
        },
        mvp_fallback_hits=0,
        wrong_reset_count=1,
    )

    recommendations = generate_tightening_recommendations(scorecard)

    assert recommendations
    assert recommendations[0].bucket == "wrong_reset"
    assert any(path.endswith("support_coordinator.py") for path in recommendations[0].target_files)
    assert any(rec.bucket == "wrong_script_handoff" for rec in recommendations)


def test_build_optimization_queue_limits_top_buckets_and_carries_examples():
    scorecard = ClosedLoopScorecard(
        quality_score=68,
        risk_level="critical",
        gate_failures=0,
        bucket_counts={
            "wrong_reset": 2,
            "wrong_script_handoff": 3,
            "over_clarify": 4,
        },
        mvp_fallback_hits=0,
        wrong_reset_count=2,
    )
    suites = (
        _suite(
            "feedback-single-turn",
            (
                _failure("wrong_script_handoff", suite="feedback", case_id="bad-script-1"),
                _failure("wrong_script_handoff", suite="feedback", case_id="bad-script-2"),
                _failure("over_clarify", suite="feedback", case_id="over-clarify-1"),
                _failure("wrong_reset", suite="feedback", case_id="reset-1"),
            ),
        ),
    )

    queue = build_optimization_queue(scorecard, suites=suites, limit=2)

    assert len(queue) == 2
    assert isinstance(queue[0], OptimizationFocusItem)
    assert queue[0].bucket == "wrong_reset"
    assert queue[0].sample_cases
    assert any("bad-script" in case_id for case_id in queue[1].sample_cases)


def test_run_pilot_closed_loop_writes_json_and_summary(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    json_out = tmp_path / "pilot-loop.json"
    runtime_feedback_path = tmp_path / "runtime-feedback.jsonl"
    runtime_feedback_path.write_text(
        json.dumps(
            {
                "record_id": "rt-1",
                "source": "runtime-feedback",
                "scope": "last",
                "expected_mode": "script",
                "expected_task": "reference_lookup",
                "captured_turns": [
                    {
                        "prompt": "能提供个 joint call 参考脚本吗",
                        "response": "【参考命令】\n- sentieon driver --algo GVCFtyper ...",
                        "task": "reference_lookup",
                        "response_mode": "script",
                        "reused_anchor": False,
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        return GateResult(name=name, ok=True, summary="pass", details="pass", returncode=0)

    report = run_pilot_closed_loop(
        repo_root,
        json_out=json_out,
        runtime_feedback_path=runtime_feedback_path,
        command_gate_runner=fake_gate_runner,
    )

    assert report.scorecard.quality_score >= 0
    assert json_out.exists()
    payload = json.loads(json_out.read_text())
    assert "pilot_readiness" in payload
    assert "scorecard" in payload
    assert "recommendations" in payload
    assert "optimization_queue" in payload
    assert "runtime_feedback_single_turn" in payload

    summary = format_pilot_closed_loop_summary(report)
    assert "Quality score:" in summary
    assert "Risk level:" in summary
    assert "Runtime feedback pending triage:" in summary
    assert "Optimization queue:" in summary


def test_run_pilot_closed_loop_accepts_explicit_source_directory(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    json_out = tmp_path / "pilot-loop.json"
    runtime_feedback_path = tmp_path / "runtime-feedback.jsonl"
    runtime_feedback_path.write_text("", encoding="utf-8")
    source_directory = repo_root / "sentieon-note"

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        return GateResult(name=name, ok=True, summary="pass", details="pass", returncode=0)

    report = run_pilot_closed_loop(
        repo_root,
        source_directory=source_directory,
        json_out=json_out,
        runtime_feedback_path=runtime_feedback_path,
        command_gate_runner=fake_gate_runner,
    )

    assert report.source_directory == str(source_directory)
    payload = json.loads(json_out.read_text())
    assert payload["source_directory"] == str(source_directory)


def test_pilot_closed_loop_script_help_lists_source_dir_flag():
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "pilot_closed_loop.py"), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--source-dir" in result.stdout
    assert "--runtime-root" in result.stdout
