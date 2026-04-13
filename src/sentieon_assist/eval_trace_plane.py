from __future__ import annotations

from typing import Any, Mapping, Sequence

from sentieon_assist.runtime_invariants import normalize_promotion_state
from sentieon_assist.trace_vocab import ResponseMode, ResolverPath, normalize_resolver_path, normalize_response_mode
from sentieon_assist.trust_boundary import OutboundContextItem, TrustBoundaryResult


_BOUNDARY_PRIORITY = {
    "answer": 0,
    "boundary": 1,
    "clarify": 2,
    "must_tool": 3,
    "must_refuse": 4,
    "must_escalate": 5,
}


def project_runtime_eval_trace(payload: Mapping[str, Any]) -> dict[str, Any]:
    planner = payload.get("planner") if isinstance(payload.get("planner"), Mapping) else {}
    answer = payload.get("answer") if isinstance(payload.get("answer"), Mapping) else {}
    trust_boundary_summary = (
        payload.get("trust_boundary_summary")
        if isinstance(payload.get("trust_boundary_summary"), Mapping)
        else answer.get("trust_boundary_summary")
        if isinstance(answer.get("trust_boundary_summary"), Mapping)
        else {}
    )
    trust_boundary_audit, trust_boundary_audit_posture = _runtime_trust_boundary_audit(payload, answer)
    response_mode = str(normalize_response_mode(answer.get("response_mode")))
    resolver_path = [str(item) for item in normalize_resolver_path(answer.get("resolver_path"))]
    boundary_tags = [str(item).strip() for item in answer.get("boundary_tags", []) if str(item).strip()]
    gap_record = answer.get("gap_record") if isinstance(answer.get("gap_record"), Mapping) else {}
    sources = [str(item).strip() for item in answer.get("sources", []) if str(item).strip()]
    boundary_adherence = _runtime_boundary_adherence(
        response_mode=response_mode,
        resolver_path=resolver_path,
        boundary_tags=boundary_tags,
        gap_record=gap_record,
    )
    return {
        "task": str(planner.get("task", "")).strip(),
        "issue_type": str(planner.get("issue_type", "")).strip(),
        "response_mode": response_mode,
        "support_intent": str(planner.get("support_intent", "")).strip(),
        "fallback_mode": str(planner.get("fallback_mode", "")).strip(),
        "vendor_id": str(planner.get("vendor_id", "")).strip(),
        "vendor_version": str(planner.get("vendor_version", "")).strip(),
        "boundary_tags": boundary_tags,
        "resolver_path": resolver_path,
        "boundary_adherence": boundary_adherence,
        "clarify_required": boundary_adherence == "clarify",
        "tool_required": boundary_adherence == "must_tool",
        "refusal_required": boundary_adherence == "must_refuse",
        "escalation_required": boundary_adherence == "must_escalate",
        "gap_type": str(gap_record.get("gap_type", "")).strip(),
        "evidence_fidelity": _runtime_evidence_fidelity(resolver_path=resolver_path, sources=sources),
        "source_count": len(sources),
        "trust_boundary_present": bool(trust_boundary_summary),
        "trust_boundary_policy_name": str(trust_boundary_summary.get("policy_name", "")).strip(),
        "trust_boundary_allowed_count": _int_value(trust_boundary_summary.get("allowed_count")),
        "trust_boundary_redacted_count": _int_value(trust_boundary_summary.get("redacted_count")),
        "trust_boundary_local_only_count": _int_value(trust_boundary_summary.get("local_only_count")),
        "trust_boundary_audit_present": bool(trust_boundary_audit),
        "trust_boundary_audit_policy_name": str(trust_boundary_summary.get("policy_name", "")).strip(),
        "trust_boundary_audit_item_count": len(trust_boundary_audit),
        "trust_boundary_audit_allowed_count": sum(
            1
            for item in trust_boundary_audit
            if str(item.get("disposition", "")).strip() == "allowed"
        ),
        "trust_boundary_audit_redacted_count": sum(
            1
            for item in trust_boundary_audit
            if str(item.get("disposition", "")).strip() == "redacted"
        ),
        "trust_boundary_audit_local_only_count": sum(
            1
            for item in trust_boundary_audit
            if str(item.get("disposition", "")).strip() == "local_only"
        ),
        "trust_boundary_audit_provenance_only": trust_boundary_audit_posture == "provenance_only",
        "trust_boundary_audit_posture": trust_boundary_audit_posture,
    }


def aggregate_runtime_eval_traces(projections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [projection for projection in projections if isinstance(projection, Mapping)]
    if not normalized:
        return {
            "turn_count": 0,
            "boundary_adherence": "answer",
            "evidence_fidelity": "",
            "clarify_turn_count": 0,
            "tool_turn_count": 0,
            "refusal_turn_count": 0,
            "escalation_turn_count": 0,
        }
    boundary_adherence = max(
        (str(item.get("boundary_adherence", "answer")).strip() or "answer" for item in normalized),
        key=lambda candidate: _BOUNDARY_PRIORITY.get(candidate, -1),
    )
    fidelities = {
        str(item.get("evidence_fidelity", "")).strip()
        for item in normalized
        if str(item.get("evidence_fidelity", "")).strip()
    }
    return {
        "turn_count": len(normalized),
        "boundary_adherence": boundary_adherence,
        "evidence_fidelity": next(iter(fidelities)) if len(fidelities) == 1 else "mixed",
        "clarify_turn_count": sum(1 for item in normalized if bool(item.get("clarify_required"))),
        "tool_turn_count": sum(1 for item in normalized if bool(item.get("tool_required"))),
        "refusal_turn_count": sum(1 for item in normalized if bool(item.get("refusal_required"))),
        "escalation_turn_count": sum(1 for item in normalized if bool(item.get("escalation_required"))),
        "trust_boundary_turn_count": sum(1 for item in normalized if bool(item.get("trust_boundary_present"))),
        "trust_boundary_audit_turn_count": sum(1 for item in normalized if bool(item.get("trust_boundary_audit_present"))),
        "trust_boundary_audit_posture": _aggregate_trust_boundary_audit_posture(normalized),
    }


def project_factory_eval_trace(payload: Mapping[str, Any]) -> dict[str, Any]:
    trust_boundary = payload.get("trust_boundary_provenance")
    if not isinstance(trust_boundary, Mapping):
        trust_boundary = {}
    lifecycle_state = str(normalize_promotion_state(payload.get("lifecycle_state")))
    return {
        "lifecycle_state": lifecycle_state,
        "review_status": str(payload.get("review_status", "")).strip(),
        "review_required": bool(payload.get("review_required", False) or str(payload.get("review_status", "")).strip() == "needs_review"),
        "evidence_fidelity": "draft_only",
        "trust_boundary_policy_name": str(trust_boundary.get("policy_name", "")).strip(),
        "trust_boundary_allowed_count": _int_value(trust_boundary.get("allowed_count")),
        "trust_boundary_redacted_count": _int_value(trust_boundary.get("redacted_count")),
        "trust_boundary_local_only_count": _int_value(trust_boundary.get("local_only_count")),
    }


def _runtime_boundary_adherence(
    *,
    response_mode: str,
    resolver_path: Sequence[str],
    boundary_tags: Sequence[str],
    gap_record: Mapping[str, Any],
) -> str:
    normalized_paths = set(resolver_path)
    normalized_tags = {str(item).strip() for item in boundary_tags if str(item).strip()}
    if ResolverPath.ARBITRATION_MUST_TOOL in normalized_paths or "must-tool" in normalized_tags:
        return "must_tool"
    if ResolverPath.ARBITRATION_MUST_REFUSE in normalized_paths or "must-refuse" in normalized_tags:
        return "must_refuse"
    if ResolverPath.ARBITRATION_MUST_ESCALATE in normalized_paths or "must-escalate" in normalized_tags:
        return "must_escalate"
    if (
        ResolverPath.ARBITRATION_MUST_CLARIFY in normalized_paths
        or response_mode == ResponseMode.CLARIFY
        or str(gap_record.get("gap_type", "")).strip() == "clarification_open"
    ):
        return "clarify"
    if response_mode == ResponseMode.BOUNDARY:
        return "boundary"
    return "answer"


def _runtime_evidence_fidelity(*, resolver_path: Sequence[str], sources: Sequence[str]) -> str:
    normalized_paths = set(resolver_path)
    if ResolverPath.TROUBLESHOOTING_MODEL_FALLBACK in normalized_paths or ResolverPath.TROUBLESHOOTING_GENERATED_FALLBACK in normalized_paths:
        return "model_generated"
    if sources:
        return "source_grounded"
    return "contract_only"


def _int_value(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _runtime_trust_boundary_audit(
    payload: Mapping[str, Any],
    answer: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    candidate = payload.get("trust_boundary_result")
    if candidate is None:
        candidate = payload.get("trust_boundary_audit")
    if candidate is None:
        candidate = answer.get("trust_boundary_result")
    if candidate is None:
        candidate = answer.get("trust_boundary_audit")
    normalized: list[dict[str, Any]] = []
    raw_bearing = False
    for item in _iter_runtime_trust_boundary_audit_items(candidate):
        if isinstance(item, OutboundContextItem):
            key = str(item.key).strip()
            if not key:
                continue
            raw_bearing = True
            normalized.append(
                {
                    "key": key,
                    "disposition": str(item.disposition).strip(),
                    "provenance": item.provenance if isinstance(item.provenance, Mapping) else {},
                    "redaction_reason": str(item.redaction_reason).strip(),
                }
            )
            continue
        if not isinstance(item, Mapping):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            continue
        raw_bearing = raw_bearing or _trust_boundary_audit_item_has_raw_fields(item)
        normalized.append(
            {
                "key": key,
                "disposition": str(item.get("disposition", "")).strip(),
                "provenance": item.get("provenance", {}),
                "redaction_reason": str(item.get("redaction_reason", "")).strip(),
            }
        )
    if not normalized:
        return [], ""
    return normalized, "mixed" if raw_bearing else "provenance_only"


def _iter_runtime_trust_boundary_audit_items(candidate: Any) -> Sequence[Any]:
    if isinstance(candidate, TrustBoundaryResult):
        return candidate.decision.items
    if isinstance(candidate, Mapping):
        for field in ("items", "trust_boundary_audit", "outbound_items"):
            items = candidate.get(field)
            if isinstance(items, (list, tuple)):
                return items
        return ()
    if isinstance(candidate, (list, tuple)):
        return candidate
    return ()


def _trust_boundary_audit_item_has_raw_fields(item: Mapping[str, Any]) -> bool:
    return any(field in item for field in ("value", "raw_value", "sanitized_value"))


def _aggregate_trust_boundary_audit_posture(items: Sequence[Mapping[str, Any]]) -> str:
    postures = {
        str(item.get("trust_boundary_audit_posture", "")).strip()
        for item in items
        if str(item.get("trust_boundary_audit_posture", "")).strip()
    }
    if not postures:
        return ""
    if len(postures) == 1:
        return next(iter(postures))
    return "mixed"


__all__ = [
    "aggregate_runtime_eval_traces",
    "project_factory_eval_trace",
    "project_runtime_eval_trace",
]
