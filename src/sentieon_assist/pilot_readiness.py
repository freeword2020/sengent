from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sentieon_assist.adversarial_sessions import run_support_session
from sentieon_assist.session_events import SupportTurnView
from sentieon_assist.trace_vocab import ResponseMode

LEGACY_MVP_FALLBACK = "当前 MVP 仅支持 license 和 install 问题"
PILOT_SINGLE_TURN_FILE = Path("tests/data/pilot_readiness_cases.json")
PILOT_SESSION_FILE = Path("tests/data/pilot_readiness_sessions.json")
GATE_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pytest", (sys.executable, "-m", "pytest", "-q")),
    ("adversarial-single-turn", (sys.executable, "scripts/adversarial_support_drill.py")),
    ("high-intensity-sessions", (sys.executable, "scripts/high_intensity_support_drill.py")),
)


@dataclass(frozen=True)
class PilotSingleTurnCase:
    case_id: str
    prompt: str
    expected_mode: str
    expected_task: str
    expected: tuple[str, ...]
    forbidden: tuple[str, ...] = (LEGACY_MVP_FALLBACK,)


@dataclass(frozen=True)
class PilotSessionTurnCase:
    prompt: str
    expected_mode: str
    expected_task: str
    expected: tuple[str, ...]
    forbidden: tuple[str, ...] = (LEGACY_MVP_FALLBACK,)
    expected_reused_anchor: bool | None = None
    reset_context: bool = False


@dataclass(frozen=True)
class PilotSessionCase:
    case_id: str
    turns: tuple[PilotSessionTurnCase, ...]


@dataclass(frozen=True)
class PilotEvalFailure:
    suite: str
    case_id: str
    turn_index: int
    prompt: str
    bucket: str
    expected_mode: str
    actual_mode: str
    expected_task: str
    actual_task: str
    expected_reused_anchor: bool | None
    actual_reused_anchor: bool
    missing: list[str]
    forbidden: list[str]
    response: str
    route_reason: str
    parsed_intent_intent: str
    parsed_intent_module: str
    issue_type: str
    effective_query: str

    def to_dict(self) -> dict[str, object]:
        return {
            "suite": self.suite,
            "case_id": self.case_id,
            "turn_index": self.turn_index,
            "prompt": self.prompt,
            "bucket": self.bucket,
            "expected_mode": self.expected_mode,
            "actual_mode": self.actual_mode,
            "expected_task": self.expected_task,
            "actual_task": self.actual_task,
            "expected_reused_anchor": self.expected_reused_anchor,
            "actual_reused_anchor": self.actual_reused_anchor,
            "missing": self.missing,
            "forbidden": self.forbidden,
            "response": self.response,
            "route_reason": self.route_reason,
            "parsed_intent": {
                "intent": self.parsed_intent_intent,
                "module": self.parsed_intent_module,
            },
            "issue_type": self.issue_type,
            "effective_query": self.effective_query,
        }


@dataclass(frozen=True)
class PilotSuiteResult:
    name: str
    total: int
    passed: int
    failed: int
    failures: tuple[PilotEvalFailure, ...]
    mvp_fallback_hits: int
    wrong_anchor_reuse_count: int
    wrong_reset_count: int

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.mvp_fallback_hits == 0 and self.wrong_reset_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "mvp_fallback_hits": self.mvp_fallback_hits,
            "wrong_anchor_reuse_count": self.wrong_anchor_reuse_count,
            "wrong_reset_count": self.wrong_reset_count,
            "failures": [failure.to_dict() for failure in self.failures],
        }


@dataclass(frozen=True)
class GateResult:
    name: str
    ok: bool
    summary: str
    details: str
    returncode: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "summary": self.summary,
            "details": self.details,
            "returncode": self.returncode,
        }


@dataclass(frozen=True)
class PilotReadinessReport:
    repo_root: str
    source_directory: str
    gates: tuple[GateResult, ...]
    pilot_single_turn: PilotSuiteResult
    pilot_multi_turn: PilotSuiteResult

    @property
    def ok(self) -> bool:
        return (
            all(gate.ok for gate in self.gates)
            and self.pilot_single_turn.ok
            and self.pilot_multi_turn.ok
            and self.mvp_fallback_hits == 0
            and self.wrong_reset_count == 0
        )

    @property
    def mvp_fallback_hits(self) -> int:
        return self.pilot_single_turn.mvp_fallback_hits + self.pilot_multi_turn.mvp_fallback_hits

    @property
    def wrong_reset_count(self) -> int:
        return self.pilot_single_turn.wrong_reset_count + self.pilot_multi_turn.wrong_reset_count

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_root": self.repo_root,
            "source_directory": self.source_directory,
            "ok": self.ok,
            "gates": [gate.to_dict() for gate in self.gates],
            "pilot_single_turn": self.pilot_single_turn.to_dict(),
            "pilot_multi_turn": self.pilot_multi_turn.to_dict(),
            "mvp_fallback_hits": self.mvp_fallback_hits,
            "wrong_reset_count": self.wrong_reset_count,
        }


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pilot_single_turn_cases(repo_root: Path) -> tuple[PilotSingleTurnCase, ...]:
    payload = _read_json(repo_root / PILOT_SINGLE_TURN_FILE)
    cases: list[PilotSingleTurnCase] = []
    for item in payload:
        cases.append(
            PilotSingleTurnCase(
                case_id=str(item["id"]),
                prompt=str(item["prompt"]),
                expected_mode=str(item["expected_mode"]),
                expected_task=str(item["expected_task"]),
                expected=tuple(item.get("expected", [])),
                forbidden=tuple(item.get("forbidden", [])) or (LEGACY_MVP_FALLBACK,),
            )
        )
    return tuple(cases)


def load_pilot_session_cases(repo_root: Path) -> tuple[PilotSessionCase, ...]:
    payload = _read_json(repo_root / PILOT_SESSION_FILE)
    cases: list[PilotSessionCase] = []
    for item in payload:
        turns = []
        for turn in item.get("turns", []):
            turns.append(
                PilotSessionTurnCase(
                    prompt=str(turn["prompt"]),
                    expected_mode=str(turn["expected_mode"]),
                    expected_task=str(turn["expected_task"]),
                    expected=tuple(turn.get("expected", [])),
                    forbidden=tuple(turn.get("forbidden", [])) or (LEGACY_MVP_FALLBACK,),
                    expected_reused_anchor=turn.get("expected_reused_anchor"),
                    reset_context=bool(turn.get("reset_context", False)),
                )
            )
        cases.append(PilotSessionCase(case_id=str(item["id"]), turns=tuple(turns)))
    return tuple(cases)


def run_command_gate(name: str, command: tuple[str, ...], repo_root: Path) -> GateResult:
    completed = subprocess.run(
        list(command),
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    details = completed.stdout.strip() or completed.stderr.strip()
    summary = details.splitlines()[-1] if details else f"exit={completed.returncode}"
    return GateResult(
        name=name,
        ok=completed.returncode == 0,
        summary=summary,
        details=details,
        returncode=completed.returncode,
    )


def _build_failure(
    *,
    suite: str,
    case_id: str,
    turn_index: int,
    case: PilotSingleTurnCase | PilotSessionTurnCase,
    result: SupportTurnView,
    bucket: str,
    missing: list[str],
    forbidden: list[str],
) -> PilotEvalFailure:
    expected_reused_anchor = getattr(case, "expected_reused_anchor", False)
    return PilotEvalFailure(
        suite=suite,
        case_id=case_id,
        turn_index=turn_index,
        prompt=case.prompt,
        bucket=bucket,
        expected_mode=case.expected_mode,
        actual_mode=result.response_mode,
        expected_task=case.expected_task,
        actual_task=result.task,
        expected_reused_anchor=expected_reused_anchor,
        actual_reused_anchor=result.reused_anchor,
        missing=missing,
        forbidden=forbidden,
        response=result.response,
        route_reason=result.route_reason,
        parsed_intent_intent=result.parsed_intent_intent,
        parsed_intent_module=result.parsed_intent_module,
        issue_type=result.issue_type,
        effective_query=result.effective_query,
    )


def bucket_failure(
    *,
    case: PilotSingleTurnCase | PilotSessionTurnCase,
    result: SupportTurnView,
    suite: str = "pilot",
    case_id: str = "case",
    turn_index: int = 1,
) -> PilotEvalFailure | None:
    missing = [value for value in case.expected if value not in result.response]
    forbidden = [value for value in case.forbidden if value in result.response]
    expected_reused_anchor = getattr(case, "expected_reused_anchor", None)
    reset_context = bool(getattr(case, "reset_context", False))

    bucket: str | None = None
    if expected_reused_anchor is not None and result.reused_anchor != expected_reused_anchor:
        bucket = "wrong_reset" if reset_context and result.reused_anchor else "wrong_anchor_reuse"
    elif case.expected_mode == ResponseMode.CLARIFY and result.response_mode != ResponseMode.CLARIFY:
        bucket = "under_clarify"
    elif case.expected_mode == ResponseMode.BOUNDARY and result.response_mode != ResponseMode.BOUNDARY:
        bucket = "wrong_boundary"
    elif case.expected_mode == ResponseMode.SCRIPT and result.response_mode != ResponseMode.SCRIPT:
        bucket = "wrong_script_handoff"
    elif case.expected_mode != ResponseMode.CLARIFY and result.response_mode == ResponseMode.CLARIFY:
        bucket = "over_clarify"
    elif result.task != case.expected_task:
        bucket = "misroute"
    elif missing or forbidden:
        if case.expected_mode == ResponseMode.BOUNDARY:
            bucket = "wrong_boundary"
        elif case.expected_mode == ResponseMode.SCRIPT:
            bucket = "wrong_script_handoff"
        elif case.expected_mode == ResponseMode.CLARIFY and result.response_mode != ResponseMode.CLARIFY:
            bucket = "under_clarify"
        else:
            bucket = "misroute"
    if bucket is None:
        return None
    return _build_failure(
        suite=suite,
        case_id=case_id,
        turn_index=turn_index,
        case=case,
        result=result,
        bucket=bucket,
        missing=missing,
        forbidden=forbidden,
    )


def _evaluate_single_turn_cases(source_directory: Path, cases: tuple[PilotSingleTurnCase, ...]) -> PilotSuiteResult:
    failures: list[PilotEvalFailure] = []
    mvp_fallback_hits = 0
    for case in cases:
        result = run_support_session([case.prompt], source_directory=str(source_directory))[0]
        mvp_fallback_hits += result.response.count(LEGACY_MVP_FALLBACK)
        failure = bucket_failure(case=case, result=result, suite="pilot-single-turn", case_id=case.case_id)
        if failure is not None:
            failures.append(failure)
    wrong_anchor_reuse_count = sum(1 for failure in failures if failure.bucket == "wrong_anchor_reuse")
    wrong_reset_count = sum(1 for failure in failures if failure.bucket == "wrong_reset")
    return PilotSuiteResult(
        name="pilot-single-turn",
        total=len(cases),
        passed=len(cases) - len(failures),
        failed=len(failures),
        failures=tuple(failures),
        mvp_fallback_hits=mvp_fallback_hits,
        wrong_anchor_reuse_count=wrong_anchor_reuse_count,
        wrong_reset_count=wrong_reset_count,
    )


def _evaluate_session_cases(source_directory: Path, cases: tuple[PilotSessionCase, ...]) -> PilotSuiteResult:
    failures: list[PilotEvalFailure] = []
    total_turns = 0
    mvp_fallback_hits = 0
    for case in cases:
        results = run_support_session([turn.prompt for turn in case.turns], source_directory=str(source_directory))
        for turn_index, (turn, result) in enumerate(zip(case.turns, results, strict=True), start=1):
            total_turns += 1
            mvp_fallback_hits += result.response.count(LEGACY_MVP_FALLBACK)
            failure = bucket_failure(
                case=turn,
                result=result,
                suite="pilot-multi-turn",
                case_id=case.case_id,
                turn_index=turn_index,
            )
            if failure is not None:
                failures.append(failure)
    wrong_anchor_reuse_count = sum(1 for failure in failures if failure.bucket == "wrong_anchor_reuse")
    wrong_reset_count = sum(1 for failure in failures if failure.bucket == "wrong_reset")
    return PilotSuiteResult(
        name="pilot-multi-turn",
        total=total_turns,
        passed=total_turns - len(failures),
        failed=len(failures),
        failures=tuple(failures),
        mvp_fallback_hits=mvp_fallback_hits,
        wrong_anchor_reuse_count=wrong_anchor_reuse_count,
        wrong_reset_count=wrong_reset_count,
    )


def _resolve_source_directory(repo_root: Path, source_directory: str | Path | None) -> Path:
    if source_directory is None:
        return repo_root / "sentieon-note"
    return Path(source_directory)


def _gate_commands_for_source(source_directory: Path, *, repo_root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    default_source_directory = repo_root / "sentieon-note"
    if source_directory == default_source_directory:
        return GATE_COMMANDS
    source_arg = ("--source-dir", str(source_directory))
    return (
        ("pytest", (sys.executable, "-m", "pytest", "-q")),
        ("adversarial-single-turn", (sys.executable, "scripts/adversarial_support_drill.py", *source_arg)),
        ("high-intensity-sessions", (sys.executable, "scripts/high_intensity_support_drill.py", *source_arg)),
    )


def run_pilot_readiness_evaluation(
    repo_root: Path,
    *,
    source_directory: str | Path | None = None,
    json_out: Path | None = None,
    command_gate_runner=run_command_gate,
) -> PilotReadinessReport:
    resolved_source_directory = _resolve_source_directory(repo_root, source_directory)
    gates = tuple(
        command_gate_runner(name, command, repo_root)
        for name, command in _gate_commands_for_source(resolved_source_directory, repo_root=repo_root)
    )
    pilot_single_turn = _evaluate_single_turn_cases(resolved_source_directory, load_pilot_single_turn_cases(repo_root))
    pilot_multi_turn = _evaluate_session_cases(resolved_source_directory, load_pilot_session_cases(repo_root))
    report = PilotReadinessReport(
        repo_root=str(repo_root),
        source_directory=str(resolved_source_directory),
        gates=gates,
        pilot_single_turn=pilot_single_turn,
        pilot_multi_turn=pilot_multi_turn,
    )
    if json_out is not None:
        json_out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def format_pilot_readiness_summary(report: PilotReadinessReport) -> str:
    lines = [f"Running pilot readiness evaluation from {report.repo_root}"]
    for gate in report.gates:
        status = "PASS" if gate.ok else "FAIL"
        lines.append(f"[{status}] {gate.name}: {gate.summary}")
    for suite in (report.pilot_single_turn, report.pilot_multi_turn):
        status = "PASS" if suite.ok else "FAIL"
        lines.append(f"[{status}] {suite.name}: {suite.passed}/{suite.total} passed")
        for failure in suite.failures:
            lines.append(
                f"  - {failure.case_id} turn={failure.turn_index} bucket={failure.bucket} "
                f"mode={failure.actual_mode} task={failure.actual_task}"
            )
    lines.append(f"MVP fallback hits in pilot corpora: {report.mvp_fallback_hits}")
    lines.append(f"Standalone reset failures: {report.wrong_reset_count}")
    if report.ok:
        lines.append("Pilot readiness gates passed.")
    else:
        lines.append("Pilot readiness gates failed.")
    return "\n".join(lines)
