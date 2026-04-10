from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sentieon_assist.feedback_runtime import default_feedback_path, load_feedback_records
from sentieon_assist.pilot_readiness import (
    LEGACY_MVP_FALLBACK,
    GateResult,
    PilotEvalFailure,
    PilotReadinessReport,
    PilotSessionCase,
    PilotSessionTurnCase,
    PilotSingleTurnCase,
    PilotSuiteResult,
    bucket_failure,
    run_command_gate,
    run_pilot_readiness_evaluation,
)
from sentieon_assist.adversarial_sessions import run_support_session
from sentieon_assist.session_events import SupportTurnView, load_selected_turn_views
from sentieon_assist.trace_vocab import ResponseMode

FEEDBACK_SINGLE_TURN_FILE = Path("tests/data/pilot_feedback_cases.json")
FEEDBACK_SESSION_FILE = Path("tests/data/pilot_feedback_sessions.json")
GATE_FAILURE_PENALTY = 20
MVP_FALLBACK_PENALTY = 25
BUCKET_WEIGHTS: dict[str, int] = {
    "wrong_reset": 25,
    "wrong_anchor_reuse": 22,
    "wrong_script_handoff": 18,
    "misroute": 15,
    "wrong_boundary": 12,
    "under_clarify": 10,
    "over_clarify": 8,
}
RECOMMENDATION_MAP: dict[str, dict[str, object]] = {
    "wrong_reset": {
        "target_files": ("src/sentieon_assist/support_coordinator.py", "src/sentieon_assist/support_state.py"),
        "why_now": "上下文 reset 失败会直接污染后续所有对话 turn。",
        "suggested_action": "先检查 standalone 新问题是否仍错误复用 anchor，再收紧 reset 条件。",
    },
    "wrong_anchor_reuse": {
        "target_files": ("src/sentieon_assist/support_coordinator.py", "src/sentieon_assist/support_state.py"),
        "why_now": "anchor 误复用会把用户带到错误主线，风险接近 reset 失败。",
        "suggested_action": "收紧 follow-up reuse 条件，只允许明确的上下文承接进入 anchor 合成。",
    },
    "wrong_script_handoff": {
        "target_files": ("src/sentieon_assist/reference_resolution.py", "src/sentieon_assist/workflow_index.py"),
        "why_now": "脚本 handoff 错误会让用户明明给够信息却拿不到可执行骨架。",
        "suggested_action": "检查 direct_script_handoff 和 workflow 条件是否已经满足但仍落在澄清或介绍层。",
    },
    "misroute": {
        "target_files": ("src/sentieon_assist/reference_intents.py", "src/sentieon_assist/support_coordinator.py"),
        "why_now": "主路由错误会放大后续所有 resolver 判断偏差。",
        "suggested_action": "先修 reference intent 或 top-level route，再看下游 answer formatting。",
    },
    "wrong_boundary": {
        "target_files": ("src/sentieon_assist/reference_boundaries.py", "src/sentieon_assist/reference_resolution.py"),
        "why_now": "边界判断过松或过紧会直接影响可用性与可信度。",
        "suggested_action": "只针对失败题里的边界标签修最小规则，不扩大到资料扩张。",
    },
    "under_clarify": {
        "target_files": ("src/sentieon_assist/workflow_index.py", "src/sentieon_assist/reference_resolution.py"),
        "why_now": "该澄清不澄清会把用户过早带到错误脚本或错误模块层。",
        "suggested_action": "检查 workflow slot 是否还缺关键信息，避免过早 direct handoff。",
    },
    "over_clarify": {
        "target_files": ("src/sentieon_assist/workflow_index.py", "src/sentieon_assist/reference_resolution.py"),
        "why_now": "过度澄清会降低试点体验并拖慢定位速度。",
        "suggested_action": "检查 direct_script_handoff 条件是否过严，或已有 facts 没有被完整消费。",
    },
}


@dataclass(frozen=True)
class FeedbackSingleTurnCase(PilotSingleTurnCase):
    source: str = "unknown"


@dataclass(frozen=True)
class FeedbackSessionCase(PilotSessionCase):
    source: str = "unknown"


@dataclass(frozen=True)
class ClosedLoopScorecard:
    quality_score: int
    risk_level: str
    gate_failures: int
    bucket_counts: dict[str, int]
    mvp_fallback_hits: int
    wrong_reset_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "quality_score": self.quality_score,
            "risk_level": self.risk_level,
            "gate_failures": self.gate_failures,
            "bucket_counts": self.bucket_counts,
            "mvp_fallback_hits": self.mvp_fallback_hits,
            "wrong_reset_count": self.wrong_reset_count,
        }


@dataclass(frozen=True)
class BaselineDelta:
    score_delta: int
    bucket_deltas: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "score_delta": self.score_delta,
            "bucket_deltas": self.bucket_deltas,
        }


@dataclass(frozen=True)
class TighteningRecommendation:
    priority: int
    bucket: str
    count: int
    target_files: tuple[str, ...]
    why_now: str
    suggested_action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "priority": self.priority,
            "bucket": self.bucket,
            "count": self.count,
            "target_files": list(self.target_files),
            "why_now": self.why_now,
            "suggested_action": self.suggested_action,
        }


@dataclass(frozen=True)
class OptimizationFocusItem:
    priority: int
    bucket: str
    count: int
    target_files: tuple[str, ...]
    why_now: str
    suggested_action: str
    sample_cases: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "priority": self.priority,
            "bucket": self.bucket,
            "count": self.count,
            "target_files": list(self.target_files),
            "why_now": self.why_now,
            "suggested_action": self.suggested_action,
            "sample_cases": list(self.sample_cases),
        }


@dataclass(frozen=True)
class PilotClosedLoopReport:
    repo_root: str
    source_directory: str
    pilot_readiness: PilotReadinessReport
    feedback_single_turn: PilotSuiteResult
    feedback_multi_turn: PilotSuiteResult
    runtime_feedback_single_turn: PilotSuiteResult
    runtime_feedback_multi_turn: PilotSuiteResult
    runtime_feedback_pending_count: int
    scorecard: ClosedLoopScorecard
    baseline: BaselineDelta | None
    recommendations: tuple[TighteningRecommendation, ...]
    optimization_queue: tuple[OptimizationFocusItem, ...]

    @property
    def ok(self) -> bool:
        return (
            self.pilot_readiness.ok
            and self.feedback_single_turn.ok
            and self.feedback_multi_turn.ok
            and self.runtime_feedback_single_turn.ok
            and self.runtime_feedback_multi_turn.ok
            and self.scorecard.gate_failures == 0
            and self.scorecard.mvp_fallback_hits == 0
            and self.scorecard.wrong_reset_count == 0
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_root": self.repo_root,
            "source_directory": self.source_directory,
            "ok": self.ok,
            "pilot_readiness": self.pilot_readiness.to_dict(),
            "feedback_single_turn": self.feedback_single_turn.to_dict(),
            "feedback_multi_turn": self.feedback_multi_turn.to_dict(),
            "runtime_feedback_single_turn": self.runtime_feedback_single_turn.to_dict(),
            "runtime_feedback_multi_turn": self.runtime_feedback_multi_turn.to_dict(),
            "runtime_feedback_pending_count": self.runtime_feedback_pending_count,
            "scorecard": self.scorecard.to_dict(),
            "baseline": self.baseline.to_dict() if self.baseline is not None else None,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "optimization_queue": [item.to_dict() for item in self.optimization_queue],
        }


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_feedback_single_turn_cases(repo_root: Path) -> tuple[FeedbackSingleTurnCase, ...]:
    payload = _read_json(repo_root / FEEDBACK_SINGLE_TURN_FILE)
    cases: list[FeedbackSingleTurnCase] = []
    for item in payload:
        cases.append(
            FeedbackSingleTurnCase(
                case_id=str(item["id"]),
                source=str(item.get("source", "unknown")),
                prompt=str(item["prompt"]),
                expected_mode=str(item["expected_mode"]),
                expected_task=str(item["expected_task"]),
                expected=tuple(item.get("expected", [])),
                forbidden=tuple(item.get("forbidden", [])) or (LEGACY_MVP_FALLBACK,),
            )
        )
    return tuple(cases)


def load_feedback_session_cases(repo_root: Path) -> tuple[FeedbackSessionCase, ...]:
    payload = _read_json(repo_root / FEEDBACK_SESSION_FILE)
    cases: list[FeedbackSessionCase] = []
    for item in payload:
        turns: list[PilotSessionTurnCase] = []
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
        cases.append(
            FeedbackSessionCase(
                case_id=str(item["id"]),
                source=str(item.get("source", "unknown")),
                turns=tuple(turns),
            )
        )
    return tuple(cases)


def load_runtime_feedback_intake(
    path: Path,
    *,
    runtime_root: Path | None = None,
) -> tuple[tuple[FeedbackSingleTurnCase, ...], tuple[FeedbackSessionCase, ...], int]:
    records = load_feedback_records(path)
    single_turn_cases: list[FeedbackSingleTurnCase] = []
    session_cases: list[FeedbackSessionCase] = []
    pending_count = 0
    resolved_runtime_root = runtime_root or path.parent
    for record in records:
        expected_mode = str(record.get("expected_mode", "")).strip()
        expected_task = str(record.get("expected_task", "")).strip()
        if not (expected_mode and expected_task):
            pending_count += 1
            continue
        session_id = str(record.get("session_id", "")).strip()
        selected_turn_ids = [
            str(turn_id).strip()
            for turn_id in record.get("selected_turn_ids", [])
            if str(turn_id).strip()
        ]
        selected_turns = []
        if session_id and selected_turn_ids:
            selected_turns = load_selected_turn_views(
                session_id,
                selected_turn_ids,
                runtime_root=resolved_runtime_root,
            )
        if not selected_turns:
            selected_turns = _legacy_selected_turn_views(record)
        if not selected_turns:
            pending_count += 1
            continue
        record_id = str(record.get("record_id", f"runtime-{len(single_turn_cases) + len(session_cases) + 1}"))
        source = str(record.get("source", "runtime-feedback"))
        scope = str(record.get("scope", "last")).strip() or "last"
        if scope == "session" and len(selected_turns) > 1:
            turns: list[PilotSessionTurnCase] = []
            for index, turn in enumerate(selected_turns):
                actual_mode = turn.response_mode or ResponseMode.DOC
                actual_task = turn.task or "reference_lookup"
                turns.append(
                    PilotSessionTurnCase(
                        prompt=turn.prompt,
                        expected_mode=expected_mode if index == len(selected_turns) - 1 else actual_mode,
                        expected_task=expected_task if index == len(selected_turns) - 1 else actual_task,
                        expected=(),
                        expected_reused_anchor=turn.reused_anchor,
                    )
                )
            session_cases.append(
                FeedbackSessionCase(
                    case_id=record_id,
                    source=source,
                    turns=tuple(turns),
                )
            )
            continue
        focus_turn = selected_turns[-1]
        single_turn_cases.append(
            FeedbackSingleTurnCase(
                case_id=record_id,
                source=source,
                prompt=focus_turn.prompt,
                expected_mode=expected_mode,
                expected_task=expected_task,
                expected=(),
            )
        )
    return tuple(single_turn_cases), tuple(session_cases), pending_count


def _legacy_selected_turn_views(record: dict[str, object]) -> list[SupportTurnView]:
    captured_turns = record.get("captured_turns", [])
    if not isinstance(captured_turns, list):
        return []
    turns: list[SupportTurnView] = []
    for index, item in enumerate(captured_turns, start=1):
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt", "")).strip()
        response = str(item.get("response", "")).strip()
        if not prompt or not response:
            continue
        task = str(item.get("task", "")).strip() or "reference_lookup"
        turns.append(
            SupportTurnView(
                session_id=str(record.get("session_id", "")),
                turn_id=f"legacy-turn-{index}",
                turn_index=index,
                prompt=prompt,
                effective_query=str(item.get("effective_query", prompt)).strip() or prompt,
                reused_anchor=bool(item.get("reused_anchor", False)),
                response=response,
                task=task,
                issue_type=str(item.get("issue_type", "")),
                route_reason=str(item.get("route_reason", "")),
                parsed_intent_intent=str(item.get("parsed_intent_intent", "")),
                parsed_intent_module=str(item.get("parsed_intent_module", "")),
                response_mode=str(item.get("response_mode", "")).strip() or ResponseMode.DOC,
            )
        )
    return turns


def _infer_runtime_root_from_feedback_path(path: Path) -> Path:
    if path.parent.name == "feedback" and path.parent.parent.name == "runtime":
        return path.parent.parent
    return path.parent


def _evaluate_feedback_single_turn(
    source_directory: Path,
    cases: tuple[FeedbackSingleTurnCase, ...],
    *,
    suite_name: str = "feedback-single-turn",
    suite_label: str = "feedback-single-turn",
) -> PilotSuiteResult:
    failures: list[PilotEvalFailure] = []
    mvp_fallback_hits = 0
    for case in cases:
        result = run_support_session([case.prompt], source_directory=str(source_directory))[0]
        mvp_fallback_hits += result.response.count(LEGACY_MVP_FALLBACK)
        failure = bucket_failure(
            case=case,
            result=result,
            suite=suite_name,
            case_id=f"{case.source}:{case.case_id}",
        )
        if failure is not None:
            failures.append(failure)
    wrong_anchor_reuse_count = sum(1 for failure in failures if failure.bucket == "wrong_anchor_reuse")
    wrong_reset_count = sum(1 for failure in failures if failure.bucket == "wrong_reset")
    return PilotSuiteResult(
        name=suite_label,
        total=len(cases),
        passed=len(cases) - len(failures),
        failed=len(failures),
        failures=tuple(failures),
        mvp_fallback_hits=mvp_fallback_hits,
        wrong_anchor_reuse_count=wrong_anchor_reuse_count,
        wrong_reset_count=wrong_reset_count,
    )


def _evaluate_feedback_sessions(
    source_directory: Path,
    cases: tuple[FeedbackSessionCase, ...],
    *,
    suite_name: str = "feedback-multi-turn",
    suite_label: str = "feedback-multi-turn",
) -> PilotSuiteResult:
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
                suite=suite_name,
                case_id=f"{case.source}:{case.case_id}",
                turn_index=turn_index,
            )
            if failure is not None:
                failures.append(failure)
    wrong_anchor_reuse_count = sum(1 for failure in failures if failure.bucket == "wrong_anchor_reuse")
    wrong_reset_count = sum(1 for failure in failures if failure.bucket == "wrong_reset")
    return PilotSuiteResult(
        name=suite_label,
        total=total_turns,
        passed=total_turns - len(failures),
        failed=len(failures),
        failures=tuple(failures),
        mvp_fallback_hits=mvp_fallback_hits,
        wrong_anchor_reuse_count=wrong_anchor_reuse_count,
        wrong_reset_count=wrong_reset_count,
    )


def collect_bucket_counts(suites: tuple[PilotSuiteResult, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for suite in suites:
        for failure in suite.failures:
            counts[failure.bucket] = counts.get(failure.bucket, 0) + 1
    return counts


def _risk_level(*, quality_score: int, gate_failures: int, mvp_fallback_hits: int) -> str:
    if gate_failures or mvp_fallback_hits or quality_score < 70:
        return "critical"
    if quality_score < 85:
        return "elevated"
    if quality_score < 95:
        return "guarded"
    return "stable"


def score_closed_loop_report(
    pilot_report: PilotReadinessReport,
    *,
    feedback_single_turn: PilotSuiteResult,
    feedback_multi_turn: PilotSuiteResult,
    runtime_feedback_single_turn: PilotSuiteResult | None = None,
    runtime_feedback_multi_turn: PilotSuiteResult | None = None,
) -> ClosedLoopScorecard:
    suites = (
        pilot_report.pilot_single_turn,
        pilot_report.pilot_multi_turn,
        feedback_single_turn,
        feedback_multi_turn,
        runtime_feedback_single_turn or PilotSuiteResult("runtime-feedback-single-turn", 0, 0, 0, (), 0, 0, 0),
        runtime_feedback_multi_turn or PilotSuiteResult("runtime-feedback-multi-turn", 0, 0, 0, (), 0, 0, 0),
    )
    gate_failures = sum(1 for gate in pilot_report.gates if not gate.ok)
    bucket_counts = collect_bucket_counts(suites)
    mvp_fallback_hits = (
        pilot_report.mvp_fallback_hits
        + feedback_single_turn.mvp_fallback_hits
        + feedback_multi_turn.mvp_fallback_hits
        + (runtime_feedback_single_turn.mvp_fallback_hits if runtime_feedback_single_turn else 0)
        + (runtime_feedback_multi_turn.mvp_fallback_hits if runtime_feedback_multi_turn else 0)
    )
    wrong_reset_count = (
        pilot_report.wrong_reset_count
        + feedback_single_turn.wrong_reset_count
        + feedback_multi_turn.wrong_reset_count
        + (runtime_feedback_single_turn.wrong_reset_count if runtime_feedback_single_turn else 0)
        + (runtime_feedback_multi_turn.wrong_reset_count if runtime_feedback_multi_turn else 0)
    )
    penalty = gate_failures * GATE_FAILURE_PENALTY + mvp_fallback_hits * MVP_FALLBACK_PENALTY
    penalty += sum(BUCKET_WEIGHTS.get(bucket, 5) * count for bucket, count in bucket_counts.items())
    quality_score = max(0, 100 - penalty)
    return ClosedLoopScorecard(
        quality_score=quality_score,
        risk_level=_risk_level(
            quality_score=quality_score,
            gate_failures=gate_failures,
            mvp_fallback_hits=mvp_fallback_hits,
        ),
        gate_failures=gate_failures,
        bucket_counts=bucket_counts,
        mvp_fallback_hits=mvp_fallback_hits,
        wrong_reset_count=wrong_reset_count,
    )


def compare_against_baseline(scorecard: ClosedLoopScorecard, baseline_payload: dict[str, object]) -> BaselineDelta:
    baseline_scorecard = baseline_payload.get("scorecard", {})
    if not isinstance(baseline_scorecard, dict):
        baseline_scorecard = {}
    baseline_score = int(baseline_scorecard.get("quality_score", 100))
    baseline_bucket_counts = baseline_scorecard.get("bucket_counts", {})
    if not isinstance(baseline_bucket_counts, dict):
        baseline_bucket_counts = {}

    bucket_names = set(scorecard.bucket_counts) | set(str(key) for key in baseline_bucket_counts)
    bucket_deltas: dict[str, int] = {}
    for bucket in sorted(bucket_names):
        current = scorecard.bucket_counts.get(bucket, 0)
        baseline = int(baseline_bucket_counts.get(bucket, 0))
        bucket_deltas[bucket] = current - baseline
    return BaselineDelta(
        score_delta=scorecard.quality_score - baseline_score,
        bucket_deltas=bucket_deltas,
    )


def generate_tightening_recommendations(scorecard: ClosedLoopScorecard) -> tuple[TighteningRecommendation, ...]:
    recommendations: list[TighteningRecommendation] = []
    if scorecard.gate_failures:
        recommendations.append(
            TighteningRecommendation(
                priority=0,
                bucket="gate_regression",
                count=scorecard.gate_failures,
                target_files=(
                    "src/sentieon_assist/pilot_readiness.py",
                    "scripts/pilot_readiness_eval.py",
                ),
                why_now="正式试点 gate 已经回退，必须先恢复基线。",
                suggested_action="先修 gate regression，再继续做 bucket 级行为收紧。",
            )
        )

    ranked_buckets = sorted(
        (
            (bucket, count)
            for bucket, count in scorecard.bucket_counts.items()
            if count > 0 and bucket in RECOMMENDATION_MAP
        ),
        key=lambda item: (-BUCKET_WEIGHTS.get(item[0], 0), -item[1], item[0]),
    )
    for index, (bucket, count) in enumerate(ranked_buckets, start=1):
        mapping = RECOMMENDATION_MAP[bucket]
        recommendations.append(
            TighteningRecommendation(
                priority=index,
                bucket=bucket,
                count=count,
                target_files=tuple(mapping["target_files"]),
                why_now=str(mapping["why_now"]),
                suggested_action=str(mapping["suggested_action"]),
            )
        )
    return tuple(recommendations)


def build_optimization_queue(
    scorecard: ClosedLoopScorecard,
    *,
    suites: tuple[PilotSuiteResult, ...],
    limit: int = 3,
) -> tuple[OptimizationFocusItem, ...]:
    if limit <= 0:
        return ()
    failures_by_bucket: dict[str, list[PilotEvalFailure]] = {}
    for suite in suites:
        for failure in suite.failures:
            failures_by_bucket.setdefault(failure.bucket, []).append(failure)

    queue: list[OptimizationFocusItem] = []
    ranked_buckets = sorted(
        (
            (bucket, count)
            for bucket, count in scorecard.bucket_counts.items()
            if count > 0 and bucket in RECOMMENDATION_MAP
        ),
        key=lambda item: (-BUCKET_WEIGHTS.get(item[0], 0), -item[1], item[0]),
    )
    for priority, (bucket, count) in enumerate(ranked_buckets[:limit], start=1):
        mapping = RECOMMENDATION_MAP[bucket]
        sample_cases = tuple(
            failure.case_id
            for failure in failures_by_bucket.get(bucket, [])[:3]
        )
        queue.append(
            OptimizationFocusItem(
                priority=priority,
                bucket=bucket,
                count=count,
                target_files=tuple(mapping["target_files"]),
                why_now=str(mapping["why_now"]),
                suggested_action=str(mapping["suggested_action"]),
                sample_cases=sample_cases,
            )
        )
    return tuple(queue)


def run_pilot_closed_loop(
    repo_root: Path,
    *,
    source_directory: str | Path | None = None,
    baseline_path: Path | None = None,
    json_out: Path | None = None,
    runtime_feedback_path: Path | None = None,
    runtime_root: Path | None = None,
    focus_limit: int = 3,
    command_gate_runner=run_command_gate,
) -> PilotClosedLoopReport:
    resolved_source_directory = Path(source_directory) if source_directory is not None else repo_root / "sentieon-note"
    pilot_report = run_pilot_readiness_evaluation(
        repo_root,
        source_directory=resolved_source_directory,
        command_gate_runner=command_gate_runner,
    )
    feedback_single_turn = _evaluate_feedback_single_turn(resolved_source_directory, load_feedback_single_turn_cases(repo_root))
    feedback_multi_turn = _evaluate_feedback_sessions(resolved_source_directory, load_feedback_session_cases(repo_root))
    runtime_path = runtime_feedback_path or default_feedback_path()
    runtime_single_cases, runtime_session_cases, runtime_pending_count = load_runtime_feedback_intake(
        runtime_path,
        runtime_root=runtime_root or _infer_runtime_root_from_feedback_path(runtime_path),
    )
    runtime_feedback_single_turn = _evaluate_feedback_single_turn(
        resolved_source_directory,
        runtime_single_cases,
        suite_name="runtime-feedback-single-turn",
        suite_label="runtime-feedback-single-turn",
    )
    runtime_feedback_multi_turn = _evaluate_feedback_sessions(
        resolved_source_directory,
        runtime_session_cases,
        suite_name="runtime-feedback-multi-turn",
        suite_label="runtime-feedback-multi-turn",
    )
    scorecard = score_closed_loop_report(
        pilot_report,
        feedback_single_turn=feedback_single_turn,
        feedback_multi_turn=feedback_multi_turn,
        runtime_feedback_single_turn=runtime_feedback_single_turn,
        runtime_feedback_multi_turn=runtime_feedback_multi_turn,
    )
    baseline = None
    if baseline_path is not None:
        baseline = compare_against_baseline(scorecard, _read_json(baseline_path))
    recommendations = generate_tightening_recommendations(scorecard)
    optimization_queue = build_optimization_queue(
        scorecard,
        suites=(
            pilot_report.pilot_single_turn,
            pilot_report.pilot_multi_turn,
            feedback_single_turn,
            feedback_multi_turn,
            runtime_feedback_single_turn,
            runtime_feedback_multi_turn,
        ),
        limit=focus_limit,
    )
    report = PilotClosedLoopReport(
        repo_root=str(repo_root),
        source_directory=str(resolved_source_directory),
        pilot_readiness=pilot_report,
        feedback_single_turn=feedback_single_turn,
        feedback_multi_turn=feedback_multi_turn,
        runtime_feedback_single_turn=runtime_feedback_single_turn,
        runtime_feedback_multi_turn=runtime_feedback_multi_turn,
        runtime_feedback_pending_count=runtime_pending_count,
        scorecard=scorecard,
        baseline=baseline,
        recommendations=recommendations,
        optimization_queue=optimization_queue,
    )
    if json_out is not None:
        json_out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def format_pilot_closed_loop_summary(report: PilotClosedLoopReport) -> str:
    lines = [f"Running pilot closed loop from {report.repo_root}"]
    for gate in report.pilot_readiness.gates:
        status = "PASS" if gate.ok else "FAIL"
        lines.append(f"[{status}] gate:{gate.name}: {gate.summary}")
    for suite in (
        report.pilot_readiness.pilot_single_turn,
        report.pilot_readiness.pilot_multi_turn,
        report.feedback_single_turn,
        report.feedback_multi_turn,
        report.runtime_feedback_single_turn,
        report.runtime_feedback_multi_turn,
    ):
        status = "PASS" if suite.ok else "FAIL"
        lines.append(f"[{status}] {suite.name}: {suite.passed}/{suite.total} passed")
    lines.append(f"Runtime feedback pending triage: {report.runtime_feedback_pending_count}")
    lines.append(f"Quality score: {report.scorecard.quality_score}")
    lines.append(f"Risk level: {report.scorecard.risk_level}")
    lines.append(f"Gate failures: {report.scorecard.gate_failures}")
    lines.append(f"MVP fallback hits: {report.scorecard.mvp_fallback_hits}")
    lines.append(f"Wrong reset count: {report.scorecard.wrong_reset_count}")
    if report.scorecard.bucket_counts:
        lines.append("Bucket counts:")
        for bucket, count in sorted(report.scorecard.bucket_counts.items()):
            lines.append(f"- {bucket}: {count}")
    else:
        lines.append("Bucket counts: none")
    if report.baseline is not None:
        lines.append(f"Baseline score delta: {report.baseline.score_delta:+d}")
        for bucket, delta in sorted(report.baseline.bucket_deltas.items()):
            if delta:
                lines.append(f"- baseline delta {bucket}: {delta:+d}")
    if report.recommendations:
        lines.append("Tightening recommendations:")
        for recommendation in report.recommendations:
            lines.append(
                f"- P{recommendation.priority} {recommendation.bucket} x{recommendation.count}: "
                + ", ".join(recommendation.target_files)
            )
    else:
        lines.append("Tightening recommendations: none; keep collecting fresh pilot failures.")
    if report.optimization_queue:
        lines.append("Optimization queue:")
        for item in report.optimization_queue:
            sample_text = f" | sample: {', '.join(item.sample_cases)}" if item.sample_cases else ""
            lines.append(
                f"- P{item.priority} {item.bucket} x{item.count}: "
                + ", ".join(item.target_files)
                + sample_text
            )
    else:
        lines.append("Optimization queue: none")
    if report.ok:
        lines.append("Pilot closed loop is stable.")
    else:
        lines.append("Pilot closed loop needs tightening.")
    return "\n".join(lines)
