from __future__ import annotations

import json
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
    collect_bucket_counts,
    compare_against_baseline,
    format_pilot_closed_loop_summary,
    generate_tightening_recommendations,
    load_feedback_session_cases,
    load_feedback_single_turn_cases,
    run_pilot_closed_loop,
    score_closed_loop_report,
)


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


def test_run_pilot_closed_loop_writes_json_and_summary(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    json_out = tmp_path / "pilot-loop.json"

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        return GateResult(name=name, ok=True, summary="pass", details="pass", returncode=0)

    report = run_pilot_closed_loop(
        repo_root,
        json_out=json_out,
        command_gate_runner=fake_gate_runner,
    )

    assert report.scorecard.quality_score >= 0
    assert json_out.exists()
    payload = json.loads(json_out.read_text())
    assert "pilot_readiness" in payload
    assert "scorecard" in payload
    assert "recommendations" in payload

    summary = format_pilot_closed_loop_summary(report)
    assert "Quality score:" in summary
    assert "Risk level:" in summary
