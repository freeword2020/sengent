from __future__ import annotations

from dataclasses import dataclass

from sentieon_assist.cli import run_query
from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.external_guides import is_external_error_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.support_coordinator import plan_support_turn, update_support_state
from sentieon_assist.support_state import SupportSessionState

RESPONSE_MODE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("【能力说明】", "capability"),
    ("【资料边界】", "boundary"),
    ("【关联判断】", "external_error"),
    ("【问题判断】", "external_error"),
    ("【参考命令】", "script"),
    ("【常用参数】", "parameter"),
    ("【模块介绍】", "module_intro"),
    ("【流程指导】", "workflow_guidance"),
    ("【资料说明】", "doc"),
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
        return "clarify"
    if "【参考命令】" in response:
        return "script"
    for prefix, mode in RESPONSE_MODE_PREFIXES:
        if response.startswith(prefix):
            return mode
    if task == "capability_explanation":
        return "capability"
    if task == "troubleshooting":
        return "external_error"
    return "doc"


@dataclass(frozen=True)
class SessionTurnResult:
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


def run_support_session(
    prompts: list[str],
    *,
    source_directory: str | None = None,
    knowledge_directory: str | None = None,
    model_fallback=None,
) -> list[SessionTurnResult]:
    state = SupportSessionState()
    results: list[SessionTurnResult] = []
    for prompt in prompts:
        planned_turn = plan_support_turn(
            prompt,
            state,
            classify_query_fn=classify_query,
            parse_reference_intent_fn=parse_reference_intent,
            is_reference_query_fn=is_reference_query,
            extract_info_fn=extract_info_from_query,
            is_external_error_query_fn=is_external_error_query,
        )
        response = run_query(
            planned_turn.effective_query,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
            route_decision=planned_turn.route,
        )
        state = update_support_state(
            state,
            planned_turn=planned_turn,
            response=response,
        )
        results.append(
            SessionTurnResult(
                prompt=prompt,
                effective_query=planned_turn.effective_query,
                reused_anchor=planned_turn.reused_anchor,
                response=response,
                task=planned_turn.route.task,
                issue_type=planned_turn.route.issue_type,
                route_reason=planned_turn.route.reason,
                parsed_intent_intent=planned_turn.route.parsed_intent.intent,
                parsed_intent_module=planned_turn.route.parsed_intent.module,
                response_mode=classify_response_mode(response, task=planned_turn.route.task),
            )
        )
    return results
