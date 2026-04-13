from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from sentieon_assist.app_paths import default_runtime_root as default_runtime_root_path
from sentieon_assist.eval_trace_plane import project_runtime_eval_trace
from sentieon_assist.support_contracts import normalize_fallback_mode, normalize_support_intent
from sentieon_assist.trace_vocab import ResponseMode, normalize_resolver_path, normalize_response_mode
from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryResult,
    normalize_outbound_context_disposition,
    sanitize_trust_boundary_summary,
)


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
    return default_runtime_root_path()


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
    trust_boundary_summary: dict[str, Any] | None = None
    trust_boundary_audit: tuple[dict[str, Any], ...] | None = None
    eval_trace: dict[str, Any] | None = None
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
            "trust_boundary_summary": self.trust_boundary_summary,
            "trust_boundary_audit": list(self.trust_boundary_audit) if self.trust_boundary_audit is not None else None,
            "eval_trace": self.eval_trace,
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
    support_intent: str = ""
    fallback_mode: str = ""
    vendor_id: str = ""
    vendor_version: str = ""
    parsed_intent_intent: str = ""
    parsed_intent_module: str = ""
    response_mode: str = ""
    gap_record: dict[str, Any] | None = None
    trust_boundary_summary: dict[str, Any] | None = None
    trust_boundary_audit: tuple[dict[str, Any], ...] | None = None
    eval_trace: dict[str, Any] | None = None


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
    support_intent: str = "",
    fallback_mode: str = "",
    vendor_id: str = "",
    vendor_version: str = "",
    sources: list[str] | None = None,
    boundary_tags: list[str] | None = None,
    resolver_path: list[str] | None = None,
    gap_record: dict[str, Any] | None = None,
    trust_boundary_result: TrustBoundaryResult | dict[str, Any] | None = None,
) -> SupportTurnEvent:
    trust_boundary_summary = _normalize_trust_boundary_summary(trust_boundary_result)
    trust_boundary_audit = _normalize_trust_boundary_audit(trust_boundary_result)
    planner = {
        "raw_query": raw_query,
        "effective_query": effective_query,
        "reused_anchor": reused_anchor,
        "task": task,
        "issue_type": issue_type,
        "route_reason": route_reason,
        "support_intent": normalize_support_intent(support_intent),
        "fallback_mode": normalize_fallback_mode(fallback_mode),
        "vendor_id": vendor_id,
        "vendor_version": vendor_version,
        "parsed_intent": {
            "intent": parsed_intent_intent,
            "module": parsed_intent_module,
        },
    }
    answer = {
        "response_mode": normalize_response_mode(response_mode),
        "response_text": response_text,
        "sources": list(sources or []),
        "boundary_tags": list(boundary_tags or []),
        "resolver_path": normalize_resolver_path(resolver_path),
        "gap_record": dict(gap_record or {}) if gap_record else None,
        "trust_boundary_summary": trust_boundary_summary,
        "trust_boundary_audit": list(trust_boundary_audit) if trust_boundary_audit is not None else None,
    }
    eval_trace = project_runtime_eval_trace(
        {
            "planner": planner,
            "answer": answer,
            "trust_boundary_result": trust_boundary_result,
            "trust_boundary_summary": trust_boundary_summary,
            "trust_boundary_audit": list(trust_boundary_audit) if trust_boundary_audit is not None else None,
        }
    )
    answer["eval_trace"] = dict(eval_trace)
    return SupportTurnEvent(
        session_id=session_id,
        turn_id=uuid4().hex,
        turn_index=turn_index,
        timestamp=_now_iso(),
        planner=planner,
        answer=answer,
        state_before=state_before,
        state_after=state_after,
        trust_boundary_summary=trust_boundary_summary,
        trust_boundary_audit=trust_boundary_audit,
        eval_trace=eval_trace,
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
    eval_trace = answer.get("eval_trace") if isinstance(answer.get("eval_trace"), dict) else payload.get("eval_trace")
    if not isinstance(eval_trace, dict):
        eval_trace = project_runtime_eval_trace(payload)
    trust_boundary_audit = _normalize_trust_boundary_audit(
        answer.get("trust_boundary_audit")
        if isinstance(answer.get("trust_boundary_audit"), (list, tuple, dict, TrustBoundaryResult))
        else payload.get("trust_boundary_audit")
    )
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
        support_intent=normalize_support_intent(str(planner.get("support_intent", ""))),
        fallback_mode=normalize_fallback_mode(str(planner.get("fallback_mode", ""))),
        vendor_id=str(planner.get("vendor_id", "")),
        vendor_version=str(planner.get("vendor_version", "")),
        parsed_intent_intent=str(parsed_intent.get("intent", "")),
        parsed_intent_module=str(parsed_intent.get("module", "")),
        response_mode=normalize_response_mode(str(answer.get("response_mode", ""))),
        gap_record=dict(answer.get("gap_record", {})) if isinstance(answer.get("gap_record"), dict) else None,
        trust_boundary_summary=
        dict(answer.get("trust_boundary_summary", {}))
        if isinstance(answer.get("trust_boundary_summary"), dict)
        else None,
        trust_boundary_audit=trust_boundary_audit,
        eval_trace=dict(eval_trace),
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


def _normalize_trust_boundary_summary(
    trust_boundary_result: TrustBoundaryResult | dict[str, Any] | None,
) -> dict[str, Any] | None:
    if trust_boundary_result is None:
        return None
    if isinstance(trust_boundary_result, TrustBoundaryResult):
        return sanitize_trust_boundary_summary(trust_boundary_result.summary)
    if isinstance(trust_boundary_result, dict):
        return sanitize_trust_boundary_summary(trust_boundary_result)
    raise TypeError(f"unsupported trust boundary result: {type(trust_boundary_result)!r}")


def _normalize_trust_boundary_audit(
    trust_boundary_result: TrustBoundaryResult | dict[str, Any] | list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
) -> tuple[dict[str, Any], ...] | None:
    if trust_boundary_result is None:
        return None
    if isinstance(trust_boundary_result, TrustBoundaryResult):
        items = trust_boundary_result.decision.items
        normalized = [_normalize_trust_boundary_audit_item(item) for item in items]
        return tuple(item for item in normalized if item is not None) or None
    if isinstance(trust_boundary_result, dict):
        candidate_items = trust_boundary_result.get("items")
        if not isinstance(candidate_items, list):
            candidate_items = trust_boundary_result.get("trust_boundary_audit")
        if not isinstance(candidate_items, list):
            candidate_items = trust_boundary_result.get("outbound_items")
        if not isinstance(candidate_items, list):
            return None
        normalized = [_normalize_trust_boundary_audit_item(item) for item in candidate_items]
        return tuple(item for item in normalized if item is not None) or None
    if isinstance(trust_boundary_result, (list, tuple)):
        normalized = [_normalize_trust_boundary_audit_item(item) for item in trust_boundary_result]
        return tuple(item for item in normalized if item is not None) or None
    return None


def _normalize_trust_boundary_audit_item(item: OutboundContextItem | Mapping[str, Any]) -> dict[str, Any] | None:
    if isinstance(item, OutboundContextItem):
        key = str(item.key).strip()
        disposition = normalize_outbound_context_disposition(item.disposition)
        provenance = _sanitize_audit_provenance(item.provenance)
        redaction_reason = str(item.redaction_reason).strip()
    elif isinstance(item, Mapping):
        key = str(item.get("key", "")).strip()
        disposition = normalize_outbound_context_disposition(item.get("disposition"))
        provenance = _sanitize_audit_provenance(item.get("provenance"))
        redaction_reason = str(item.get("redaction_reason", "")).strip()
    else:
        return None
    if not key:
        return None
    payload: dict[str, Any] = {
        "key": key,
        "disposition": str(disposition),
        "provenance": provenance,
    }
    if redaction_reason:
        payload["redaction_reason"] = redaction_reason
    return payload


def _sanitize_audit_provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        field_name = str(key).strip()
        if not field_name:
            continue
        if field_name.lower() in _AUDIT_PROVENANCE_DENYLIST:
            continue
        sanitized_value = _sanitize_audit_provenance_value(item)
        if sanitized_value is not None:
            sanitized[field_name] = sanitized_value
    return sanitized


def _sanitize_audit_provenance_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _sanitize_audit_provenance(value)
    if isinstance(value, list):
        return [_sanitize_audit_provenance_value(item) for item in value if _sanitize_audit_provenance_value(item) is not None]
    if isinstance(value, tuple):
        return tuple(
            item
            for item in (_sanitize_audit_provenance_value(element) for element in value)
            if item is not None
        )
    if isinstance(value, str):
        return _sanitize_audit_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return _sanitize_audit_text(str(value))


def _sanitize_audit_text(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    if _looks_like_path(candidate):
        return "[PATH]"
    scrubbed = _AUDIT_EMAIL_PATTERN.sub("[EMAIL]", candidate)
    if _AUDIT_SECRET_PATTERN.search(scrubbed):
        return "[REDACTED]"
    scrubbed = _AUDIT_PATH_FRAGMENT_PATTERN.sub("[PATH]", scrubbed)
    return scrubbed


def _looks_like_path(value: str) -> bool:
    if value.startswith("http://") or value.startswith("https://"):
        return False
    return value.startswith(("/", "./", "../")) or bool(re.match(r"^[A-Za-z]:[\\/]", value))


_AUDIT_PROVENANCE_DENYLIST = {
    "value",
    "raw_value",
    "sanitized_value",
    "raw",
    "text",
    "payload",
    "secret",
    "token",
    "password",
    "passwd",
    "pwd",
}
_AUDIT_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.+-])")
_AUDIT_SECRET_PATTERN = re.compile(r"(?i)\b(?:token|secret|password|passwd|pwd|api[_-]?key)\b")
_AUDIT_PATH_FRAGMENT_PATTERN = re.compile(r"(?<!\w)(?:/|[A-Za-z]:[\\/]|\.{1,2}[\\/])[^\s<>'\"`]+")
