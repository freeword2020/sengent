from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sentieon_assist.pilot_readiness import (
    GateResult,
    PilotEvalFailure,
    PilotSessionTurnCase,
    PilotSingleTurnCase,
    bucket_failure,
    load_pilot_session_cases,
    load_pilot_single_turn_cases,
    run_pilot_readiness_evaluation,
)
from sentieon_assist.session_events import SupportTurnView


def test_load_pilot_readiness_corpora():
    repo_root = Path(__file__).resolve().parent.parent

    single_turn_cases = load_pilot_single_turn_cases(repo_root)
    session_cases = load_pilot_session_cases(repo_root)

    assert single_turn_cases
    assert session_cases
    assert all(case.expected_mode for case in single_turn_cases)
    assert all(case.turns for case in session_cases)


def test_bucket_failure_uses_wrong_reset_for_reset_turns():
    case = PilotSessionTurnCase(
        prompt="LICSRVR、Poetry",
        expected_mode="doc",
        expected_task="reference_lookup",
        expected=("【资料说明】",),
        expected_reused_anchor=False,
        reset_context=True,
    )
    result = SupportTurnView(
        session_id="sess-1",
        turn_id="turn-1",
        turn_index=1,
        prompt="LICSRVR、Poetry",
        effective_query="DNAscope 的 --pcr_free 是什么 LICSRVR、Poetry",
        reused_anchor=True,
        response="【资料说明】\n- LICSRVR",
        task="reference_lookup",
        issue_type="other",
        route_reason="reference_other",
        parsed_intent_intent="reference_other",
        parsed_intent_module="",
        response_mode="doc",
    )

    failure = bucket_failure(case=case, result=result)

    assert failure is not None
    assert failure.bucket == "wrong_reset"


def test_bucket_failure_uses_wrong_script_handoff_for_script_mode_mismatch():
    case = PilotSingleTurnCase(
        case_id="joint-call-script",
        prompt="能提供个 joint call 参考脚本吗",
        expected_mode="script",
        expected_task="reference_lookup",
        expected=("【参考命令】", "GVCFtyper"),
    )
    result = SupportTurnView(
        session_id="sess-1",
        turn_id="turn-1",
        turn_index=1,
        prompt=case.prompt,
        effective_query=case.prompt,
        reused_anchor=False,
        response="【流程指导】\n- 先确认样本类型",
        task="onboarding_guidance",
        issue_type="other",
        route_reason="workflow_guidance",
        parsed_intent_intent="workflow_guidance",
        parsed_intent_module="",
        response_mode="clarify",
    )

    failure = bucket_failure(case=case, result=result)

    assert failure is not None
    assert failure.bucket == "wrong_script_handoff"


def test_run_pilot_readiness_evaluation_writes_json_and_fails_on_gate_error(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    json_out = tmp_path / "pilot-readiness.json"

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        ok = name != "pytest"
        summary = "simulated-pass" if ok else "simulated-fail"
        return GateResult(name=name, ok=ok, summary=summary, details=summary)

    report = run_pilot_readiness_evaluation(
        repo_root,
        json_out=json_out,
        command_gate_runner=fake_gate_runner,
    )

    assert report.ok is False
    assert json_out.exists()
    payload = json.loads(json_out.read_text())
    assert payload["ok"] is False
    assert payload["gates"][0]["name"] == "pytest"
    assert payload["gates"][0]["ok"] is False
    assert "pilot_single_turn" in payload
    assert "pilot_multi_turn" in payload


def test_run_pilot_readiness_evaluation_accepts_explicit_source_directory(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    json_out = tmp_path / "pilot-readiness.json"
    source_directory = repo_root / "sentieon-note"

    def fake_gate_runner(name: str, command: tuple[str, ...], root: Path) -> GateResult:
        return GateResult(name=name, ok=True, summary="pass", details="pass")

    report = run_pilot_readiness_evaluation(
        repo_root,
        source_directory=source_directory,
        json_out=json_out,
        command_gate_runner=fake_gate_runner,
    )

    assert report.source_directory == str(source_directory)
    payload = json.loads(json_out.read_text())
    assert payload["source_directory"] == str(source_directory)


def test_pilot_readiness_script_help_lists_source_dir_flag():
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "pilot_readiness_eval.py"), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--source-dir" in result.stdout


def test_pilot_eval_failure_serialization_is_machine_readable():
    failure = PilotEvalFailure(
        suite="pilot-single-turn",
        case_id="capability-01",
        turn_index=1,
        prompt="你有什么功能",
        bucket="misroute",
        expected_mode="capability",
        actual_mode="module_intro",
        expected_task="capability_explanation",
        actual_task="reference_lookup",
        expected_reused_anchor=False,
        actual_reused_anchor=False,
        missing=["【能力说明】"],
        forbidden=[],
        response="【模块介绍】\n- Sentieon",
        route_reason="module_overview",
        parsed_intent_intent="module_overview",
        parsed_intent_module="",
        issue_type="other",
        effective_query="你有什么功能",
    )

    payload = failure.to_dict()

    assert payload["bucket"] == "misroute"
    assert payload["parsed_intent"]["intent"] == "module_overview"
    assert payload["route_reason"] == "module_overview"
