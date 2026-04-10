from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sentieon_assist.trace_vocab import ResponseMode, normalize_resolver_path, normalize_response_mode


SCHEMA_VERSION = "2026-04-09"

RESPONSE_MODE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("【能力说明】", ResponseMode.CAPABILITY),
    ("【资料边界】", ResponseMode.BOUNDARY),
    ("【关联判断】", ResponseMode.EXTERNAL_ERROR),
    ("【问题判断】", ResponseMode.EXTERNAL_ERROR),
    ("【参考命令】", ResponseMode.SCRIPT),
    ("【常用参数】", ResponseMode.PARAMETER),
    ("【模块介绍】", ResponseMode.MODULE_INTRO),
    ("【流程指导】", ResponseMode.WORKFLOW_GUIDANCE),
    ("【资料说明】", ResponseMode.DOC),
)
CLARIFY_MARKERS: tuple[str, ...] = (
    "需要补充以下信息",
    "需要确认模块",
    "【需要确认的信息】",
    "还没给出具体参数名",
    "请直接补充参数名",
)


def classify_response_mode(response: str, *, task: str = "reference_lookup") -> str:
    if any(marker in response for marker in CLARIFY_MARKERS):
        return ResponseMode.CLARIFY
    if "【参考命令】" in response:
        return ResponseMode.SCRIPT
    for prefix, mode in RESPONSE_MODE_PREFIXES:
        if response.startswith(prefix):
            return mode
    if task == "capability_explanation":
        return ResponseMode.CAPABILITY
    if task == "troubleshooting":
        return ResponseMode.EXTERNAL_ERROR
    return ResponseMode.DOC


def default_runtime_root() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime"


def session_index_path(*, runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root) if runtime_root is not None else default_runtime_root()
    return root / "sessions" / "index.jsonl"


def session_log_path(session_id: str, *, runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root) if runtime_root is not None else default_runtime_root()
    return root / "sessions" / f"{session_id}.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


@dataclass(frozen=True)
class SupportSessionRecord:
    session_id: str
    schema_version: str
    created_at: str
    repo_root: str
    git_sha: str
    source_directory: str
    knowledge_directory: str
    mode: str = "interactive"

    @classmethod
    def new(
        cls,
        *,
        repo_root: str,
        git_sha: str,
        source_directory: str,
        knowledge_directory: str,
        mode: str,
    ) -> "SupportSessionRecord":
        return cls(
            session_id=uuid4().hex,
            schema_version=SCHEMA_VERSION,
            created_at=_now_iso(),
            repo_root=repo_root,
            git_sha=git_sha,
            source_directory=source_directory,
            knowledge_directory=knowledge_directory,
            mode=mode,
        )

    def to_index_record(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["record_type"] = "session_index"
        return payload

    def to_event(self) -> dict[str, Any]:
        return {
            "event_type": "session_started",
            "session_id": self.session_id,
            "schema_version": self.schema_version,
            "timestamp": self.created_at,
            "repo_root": self.repo_root,
            "git_sha": self.git_sha,
            "source_directory": self.source_directory,
            "knowledge_directory": self.knowledge_directory,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class SupportTurnEvent:
    session_id: str
    turn_id: str
    turn_index: int
    timestamp: str
    planner: dict[str, Any]
    answer: dict[str, Any]
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    event_type: str = "turn_resolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "turn_index": self.turn_index,
            "timestamp": self.timestamp,
            "planner": self.planner,
            "answer": self.answer,
            "state_before": self.state_before,
            "state_after": self.state_after,
        }


@dataclass(frozen=True)
class FeedbackRecordedEvent:
    session_id: str
    feedback_record_id: str
    scope: str
    selected_turn_ids: tuple[str, ...]
    timestamp: str
    event_type: str = "feedback_recorded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "session_id": self.session_id,
            "feedback_record_id": self.feedback_record_id,
            "scope": self.scope,
            "selected_turn_ids": list(self.selected_turn_ids),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class SupportTurnView:
    session_id: str
    turn_id: str
    turn_index: int
    prompt: str
    effective_query: str
    reused_anchor: bool
    response: str
    task: str
    issue_type: str
    route_reason: str
    parsed_intent_intent: str
    parsed_intent_module: str
    response_mode: str


def build_turn_event(
    *,
    session_id: str,
    turn_index: int,
    raw_query: str,
    effective_query: str,
    reused_anchor: bool,
    task: str,
    issue_type: str,
    route_reason: str,
    parsed_intent_intent: str,
    parsed_intent_module: str,
    response_text: str,
    response_mode: str,
    state_before: dict[str, Any],
    state_after: dict[str, Any],
    sources: list[str] | None = None,
    boundary_tags: list[str] | None = None,
    resolver_path: list[str] | None = None,
) -> SupportTurnEvent:
    return SupportTurnEvent(
        session_id=session_id,
        turn_id=uuid4().hex,
        turn_index=turn_index,
        timestamp=_now_iso(),
        planner={
            "raw_query": raw_query,
            "effective_query": effective_query,
            "reused_anchor": reused_anchor,
            "task": task,
            "issue_type": issue_type,
            "route_reason": route_reason,
            "parsed_intent": {
                "intent": parsed_intent_intent,
                "module": parsed_intent_module,
            },
        },
        answer={
            "response_mode": normalize_response_mode(response_mode),
            "response_text": response_text,
            "sources": list(sources or []),
            "boundary_tags": list(boundary_tags or []),
            "resolver_path": normalize_resolver_path(resolver_path),
        },
        state_before=state_before,
        state_after=state_after,
    )


def build_feedback_recorded_event(
    *,
    session_id: str,
    feedback_record_id: str,
    scope: str,
    selected_turn_ids: list[str] | tuple[str, ...],
) -> FeedbackRecordedEvent:
    return FeedbackRecordedEvent(
        session_id=session_id,
        feedback_record_id=feedback_record_id,
        scope=scope,
        selected_turn_ids=tuple(selected_turn_ids),
        timestamp=_now_iso(),
    )


def append_session_record(session: SupportSessionRecord, *, runtime_root: str | Path | None = None) -> None:
    _append_jsonl(session_index_path(runtime_root=runtime_root), session.to_index_record())
    _append_jsonl(session_log_path(session.session_id, runtime_root=runtime_root), session.to_event())


def append_turn_event(event: SupportTurnEvent, *, runtime_root: str | Path | None = None) -> None:
    _append_jsonl(session_log_path(event.session_id, runtime_root=runtime_root), event.to_dict())


def append_feedback_recorded_event(event: FeedbackRecordedEvent, *, runtime_root: str | Path | None = None) -> None:
    _append_jsonl(session_log_path(event.session_id, runtime_root=runtime_root), event.to_dict())


def load_session_events(session_id: str, *, runtime_root: str | Path | None = None) -> list[dict[str, Any]]:
    path = session_log_path(session_id, runtime_root=runtime_root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def turn_view_from_event(event: SupportTurnEvent | dict[str, Any]) -> SupportTurnView:
    payload = event.to_dict() if isinstance(event, SupportTurnEvent) else event
    planner = payload.get("planner", {})
    answer = payload.get("answer", {})
    parsed_intent = planner.get("parsed_intent", {})
    return SupportTurnView(
        session_id=str(payload.get("session_id", "")),
        turn_id=str(payload.get("turn_id", "")),
        turn_index=int(payload.get("turn_index", 0) or 0),
        prompt=str(planner.get("raw_query", "")),
        effective_query=str(planner.get("effective_query", "")),
        reused_anchor=bool(planner.get("reused_anchor", False)),
        response=str(answer.get("response_text", "")),
        task=str(planner.get("task", "")),
        issue_type=str(planner.get("issue_type", "")),
        route_reason=str(planner.get("route_reason", "")),
        parsed_intent_intent=str(parsed_intent.get("intent", "")),
        parsed_intent_module=str(parsed_intent.get("module", "")),
        response_mode=normalize_response_mode(str(answer.get("response_mode", ""))),
    )


def load_turn_views(session_id: str, *, runtime_root: str | Path | None = None) -> list[SupportTurnView]:
    views: list[SupportTurnView] = []
    for event in load_session_events(session_id, runtime_root=runtime_root):
        if event.get("event_type") != "turn_resolved":
            continue
        views.append(turn_view_from_event(event))
    return views


def load_selected_turn_views(
    session_id: str,
    turn_ids: list[str] | tuple[str, ...],
    *,
    runtime_root: str | Path | None = None,
) -> list[SupportTurnView]:
    requested = [str(turn_id).strip() for turn_id in turn_ids if str(turn_id).strip()]
    if not requested:
        return []
    indexed = {view.turn_id: view for view in load_turn_views(session_id, runtime_root=runtime_root)}
    return [indexed[turn_id] for turn_id in requested if turn_id in indexed]
