from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

MODE_ALIASES = {
    "capability": "capability",
    "workflow": "workflow_guidance",
    "workflow_guidance": "workflow_guidance",
    "module": "module_intro",
    "module_intro": "module_intro",
    "parameter": "parameter",
    "script": "script",
    "doc": "doc",
    "external": "external_error",
    "external_error": "external_error",
    "boundary": "boundary",
    "clarify": "clarify",
}
TASK_ALIASES = {
    "capability": "capability_explanation",
    "capability_explanation": "capability_explanation",
    "reference": "reference_lookup",
    "reference_lookup": "reference_lookup",
    "workflow": "onboarding_guidance",
    "onboarding_guidance": "onboarding_guidance",
    "troubleshooting": "troubleshooting",
}
SCOPE_ALIASES = {
    "": "last",
    "last": "last",
    "最近一轮": "last",
    "当前回答": "last",
    "session": "session",
    "整段会话": "session",
    "当前会话": "session",
}


@dataclass(frozen=True)
class FeedbackTurnSnapshot:
    prompt: str
    effective_query: str
    response: str
    task: str
    issue_type: str
    route_reason: str
    parsed_intent_intent: str
    parsed_intent_module: str
    response_mode: str
    reused_anchor: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_feedback_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "feedback" / "runtime_feedback.jsonl"


def normalize_feedback_scope(value: str) -> str:
    normalized = value.strip().lower()
    return SCOPE_ALIASES.get(normalized, "")


def normalize_expected_mode(value: str) -> str:
    normalized = value.strip().lower()
    return MODE_ALIASES.get(normalized, "")


def normalize_expected_task(value: str) -> str:
    normalized = value.strip().lower()
    return TASK_ALIASES.get(normalized, "")


def format_chat_help() -> str:
    return (
        "【帮助】\n"
        "- /help：查看可用命令和反馈入口\n"
        "- /feedback：反馈最近一轮回答，并自动附带当时的上下文和答案\n"
        "- /feedback session：反馈当前整段会话\n"
        "- /reset：清空当前补问上下文\n"
        "- /quit：退出交互模式\n\n"
        "【反馈说明】\n"
        "- /feedback 默认抓最近一轮；/feedback session 抓整段会话。\n"
        "- 反馈时可以自由写“哪里不理想”和“期望它怎么答”。\n"
        "- 如果你知道期望 mode/task，也可以补充；留空会先进入待分诊队列。"
    )


def format_feedback_hint() -> str:
    return "如需反馈当前回答：/feedback（最近一轮） 或 /feedback session（整段会话）"


def build_feedback_record(
    *,
    scope: str,
    captured_turns: list[FeedbackTurnSnapshot],
    summary: str,
    expected_answer: str,
    expected_mode: str,
    expected_task: str,
    feedback_path: Path,
) -> dict[str, Any]:
    return {
        "record_id": uuid4().hex,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "source": "runtime-feedback",
        "scope": scope,
        "summary": summary,
        "expected_answer": expected_answer,
        "expected_mode": expected_mode,
        "expected_task": expected_task,
        "scorable": bool(expected_mode and expected_task),
        "git_sha": _git_sha(feedback_path.parent),
        "captured_turns": [turn.to_dict() for turn in captured_turns],
    }


def append_feedback_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_feedback_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _git_sha(cwd: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()
