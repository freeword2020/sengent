from __future__ import annotations

from sentieon_assist.cli import run_query
from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.external_guides import is_external_error_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.session_events import SupportSessionRecord, SupportTurnView, build_turn_event, classify_response_mode, turn_view_from_event
from sentieon_assist.support_coordinator import plan_support_turn, update_support_state
from sentieon_assist.support_state import SupportSessionState


def run_support_session(
    prompts: list[str],
    *,
    source_directory: str | None = None,
    knowledge_directory: str | None = None,
    model_fallback=None,
) -> list[SupportTurnView]:
    state = SupportSessionState()
    session = SupportSessionRecord.new(
        repo_root=str(source_directory or ""),
        git_sha="",
        source_directory=str(source_directory or ""),
        knowledge_directory=str(knowledge_directory or ""),
        mode="replay",
    )
    results: list[SupportTurnView] = []
    for turn_index, prompt in enumerate(prompts, start=1):
        state_before = state.to_snapshot()
        planned_turn = plan_support_turn(
            prompt,
            state,
            classify_query_fn=classify_query,
            parse_reference_intent_fn=parse_reference_intent,
            is_reference_query_fn=is_reference_query,
            extract_info_fn=extract_info_from_query,
            is_external_error_query_fn=is_external_error_query,
        )
        trace: dict[str, object] = {"sources": [], "boundary_tags": [], "resolver_path": []}
        response = run_query(
            planned_turn.effective_query,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
            route_decision=planned_turn.route,
            trace_collector=lambda payload: trace.update(payload),
        )
        response_mode = classify_response_mode(response, task=planned_turn.route.task)
        state = update_support_state(
            state,
            planned_turn=planned_turn,
            response=response,
        )
        turn_event = build_turn_event(
            session_id=session.session_id,
            turn_index=turn_index,
            raw_query=prompt,
            effective_query=planned_turn.effective_query,
            reused_anchor=planned_turn.reused_anchor,
            task=planned_turn.route.task,
            issue_type=planned_turn.route.issue_type,
            route_reason=planned_turn.route.reason,
            support_intent=planned_turn.route.support_intent,
            fallback_mode=planned_turn.route.fallback_mode,
            vendor_id=planned_turn.route.vendor_id,
            vendor_version=planned_turn.route.vendor_version,
            parsed_intent_intent=planned_turn.route.parsed_intent.intent,
            parsed_intent_module=planned_turn.route.parsed_intent.module,
            response_text=response,
            response_mode=response_mode,
            state_before=state_before,
            state_after=state.to_snapshot(),
            sources=[str(item) for item in trace.get("sources", [])],
            boundary_tags=[str(item) for item in trace.get("boundary_tags", [])],
            resolver_path=[str(item) for item in trace.get("resolver_path", [])],
        )
        results.append(turn_view_from_event(turn_event))
    return results
