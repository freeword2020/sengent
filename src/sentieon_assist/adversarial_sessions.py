from __future__ import annotations

from dataclasses import dataclass

from sentieon_assist.cli import run_query
from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.external_guides import is_external_error_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.support_coordinator import plan_support_turn, update_support_state
from sentieon_assist.support_state import SupportSessionState


@dataclass(frozen=True)
class SessionTurnResult:
    prompt: str
    effective_query: str
    reused_anchor: bool
    response: str


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
            )
        )
    return results
