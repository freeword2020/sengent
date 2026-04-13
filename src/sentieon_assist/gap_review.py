from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sentieon_assist.trace_vocab import normalize_response_mode


REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_TRIAGED = "triaged"

REVIEW_DECISION_PENDING = "pending"
REVIEW_DECISION_CANDIDATE_ONLY = "candidate_only"
REVIEW_DECISION_SEED_EVAL = "seed_eval"
REVIEW_DECISION_NEEDS_MORE_EVIDENCE = "needs_more_evidence"
REVIEW_DECISION_CLOSE_NO_ACTION = "close_no_action"

REVIEW_SCOPE_LAST = "last"
REVIEW_SCOPE_SESSION = "session"

SUPPORTED_REVIEW_STATUSES = {REVIEW_STATUS_PENDING, REVIEW_STATUS_TRIAGED}
SUPPORTED_REVIEW_DECISIONS = {
    REVIEW_DECISION_PENDING,
    REVIEW_DECISION_CANDIDATE_ONLY,
    REVIEW_DECISION_SEED_EVAL,
    REVIEW_DECISION_NEEDS_MORE_EVIDENCE,
    REVIEW_DECISION_CLOSE_NO_ACTION,
}
SUPPORTED_REVIEW_SCOPES = {REVIEW_SCOPE_LAST, REVIEW_SCOPE_SESSION}

DEFAULT_GAP_MAINTAINER_REVIEW = {
    "status": REVIEW_STATUS_PENDING,
    "decision": REVIEW_DECISION_PENDING,
    "scope": REVIEW_SCOPE_LAST,
    "expected_mode": "",
    "expected_task": "",
    "notes": "",
}


@dataclass(frozen=True)
class GapReviewUpdateResult:
    build_dir: Path
    entry_id: str
    metadata_path: Path
    review: dict[str, str]


def normalize_gap_maintainer_review(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return dict(DEFAULT_GAP_MAINTAINER_REVIEW)
    review = dict(DEFAULT_GAP_MAINTAINER_REVIEW)
    review["status"] = _string_value(value.get("status")) or REVIEW_STATUS_PENDING
    review["decision"] = _string_value(value.get("decision")) or REVIEW_DECISION_PENDING
    review["scope"] = _string_value(value.get("scope")) or REVIEW_SCOPE_LAST
    review["expected_mode"] = _string_value(value.get("expected_mode"))
    review["expected_task"] = _string_value(value.get("expected_task"))
    review["notes"] = _string_value(value.get("notes"))
    return review


def validate_gap_maintainer_review(review: dict[str, Any]) -> dict[str, str]:
    normalized = normalize_gap_maintainer_review(review)
    status = normalized["status"]
    decision = normalized["decision"]
    scope = normalized["scope"]
    if status not in SUPPORTED_REVIEW_STATUSES:
        raise ValueError(f"unsupported gap review status: {status}")
    if decision not in SUPPORTED_REVIEW_DECISIONS:
        raise ValueError(f"unsupported gap review decision: {decision}")
    if scope not in SUPPORTED_REVIEW_SCOPES:
        raise ValueError(f"unsupported gap review scope: {scope}")
    if decision == REVIEW_DECISION_SEED_EVAL and not normalized["expected_mode"]:
        raise ValueError("seed_eval decisions require expected_mode")
    if decision == REVIEW_DECISION_SEED_EVAL and not normalized["expected_task"]:
        raise ValueError("seed_eval decisions require expected_task")
    return normalized


def build_gap_eval_seed_record(
    *,
    build_id: str,
    entry_id: str,
    gap_type: str,
    session_id: str,
    turn_id: str,
    review: dict[str, Any],
) -> dict[str, Any] | None:
    normalized = validate_gap_maintainer_review(review)
    if normalized["decision"] != REVIEW_DECISION_SEED_EVAL:
        return None
    if not _string_value(session_id):
        raise ValueError("seed_eval decisions require session_id")
    if not _string_value(turn_id):
        raise ValueError("seed_eval decisions require turn_id")
    return {
        "record_id": f"gap-eval.{build_id}.{entry_id}",
        "source": "gap-intake-review",
        "scope": normalized["scope"],
        "session_id": session_id,
        "selected_turn_ids": [turn_id],
        "expected_mode": normalized["expected_mode"],
        "expected_task": normalized["expected_task"],
        "scorable": True,
        "entry_id": entry_id,
        "gap_type": gap_type,
        "build_id": build_id,
        "eval_alignment": project_gap_review_eval_alignment(
            {
                "entry_id": entry_id,
                "review_status": normalized["status"],
                "review_decision": normalized["decision"],
                "review_scope": normalized["scope"],
                "expected_mode": normalized["expected_mode"],
                "expected_task": normalized["expected_task"],
            },
            {
                "response_mode": normalized["expected_mode"],
                "task": normalized["expected_task"],
                "support_intent": normalized["expected_task"],
                "boundary_adherence": normalized["expected_mode"],
                "evidence_fidelity": "review_expected",
            },
        ),
    }


def project_gap_review_eval_alignment(
    review_record: dict[str, Any],
    eval_projection: dict[str, Any] | None,
) -> dict[str, Any]:
    projection = eval_projection if isinstance(eval_projection, dict) else {}
    expected_mode = _string_value(review_record.get("expected_mode"))
    expected_task = _string_value(review_record.get("expected_task"))
    actual_mode = _string_value(projection.get("response_mode"))
    actual_task = _string_value(projection.get("task")) or _string_value(projection.get("support_intent"))
    expected_mode_matches = not expected_mode or normalize_response_mode(actual_mode) == normalize_response_mode(expected_mode)
    expected_task_matches = not expected_task or actual_task == expected_task
    return {
        "entry_id": _string_value(review_record.get("entry_id")),
        "review_status": _string_value(review_record.get("review_status")) or _string_value(review_record.get("status")),
        "review_decision": _string_value(review_record.get("review_decision")) or _string_value(review_record.get("decision")),
        "review_scope": _string_value(review_record.get("review_scope")) or _string_value(review_record.get("scope")),
        "expected_mode": expected_mode,
        "expected_task": expected_task,
        "expected_mode_matches": expected_mode_matches,
        "expected_task_matches": expected_task_matches,
        "alignment_state": "aligned" if expected_mode_matches and expected_task_matches else "mismatched",
        "boundary_adherence": _string_value(projection.get("boundary_adherence")),
        "evidence_fidelity": _string_value(projection.get("evidence_fidelity")),
    }


def aggregate_gap_review_eval_alignments(alignments: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [item for item in alignments if isinstance(item, dict)]
    aligned_count = sum(1 for item in normalized if _string_value(item.get("alignment_state")) == "aligned")
    mismatched_count = sum(1 for item in normalized if _string_value(item.get("alignment_state")) == "mismatched")
    if aligned_count and mismatched_count:
        alignment_state = "mixed"
    elif mismatched_count:
        alignment_state = "mismatched"
    elif aligned_count:
        alignment_state = "aligned"
    else:
        alignment_state = "unknown"
    return {
        "alignment_state": alignment_state,
        "aligned_count": aligned_count,
        "mismatched_count": mismatched_count,
        "total_count": len(normalized),
    }


def update_gap_review_metadata(
    metadata_path: str | Path,
    *,
    status: str = REVIEW_STATUS_TRIAGED,
    decision: str,
    expected_mode: str = "",
    expected_task: str = "",
    scope: str = REVIEW_SCOPE_LAST,
    note: str = "",
) -> dict[str, Any]:
    resolved_metadata_path = Path(metadata_path)
    if not resolved_metadata_path.exists():
        raise ValueError(f"gap review metadata not found: {resolved_metadata_path}")
    payload = yaml.safe_load(resolved_metadata_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"gap review metadata must be a mapping: {resolved_metadata_path}")
    payload["maintainer_review"] = validate_gap_maintainer_review(
        {
            "status": status,
            "decision": decision,
            "expected_mode": expected_mode,
            "expected_task": expected_task,
            "scope": scope,
            "notes": note,
        }
    )
    resolved_metadata_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return payload


def apply_gap_review_decision(
    build_dir: str | Path,
    *,
    entry_id: str,
    status: str = REVIEW_STATUS_TRIAGED,
    decision: str,
    expected_mode: str = "",
    expected_task: str = "",
    scope: str = REVIEW_SCOPE_LAST,
    note: str = "",
) -> GapReviewUpdateResult:
    resolved_build_dir = Path(build_dir)
    review_records_path = resolved_build_dir / "gap_intake_review.jsonl"
    if not review_records_path.exists():
        raise ValueError(f"gap intake review artifact missing: {review_records_path}")
    matches: list[dict[str, Any]] = []
    with review_records_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if _string_value(payload.get("entry_id")) == _string_value(entry_id):
                matches.append(payload)
    if not matches:
        raise ValueError(f"gap review entry not found: {entry_id}")
    if len(matches) > 1:
        raise ValueError(f"gap review entry is ambiguous: {entry_id}")
    metadata_path_text = _string_value(matches[0].get("metadata_path"))
    if not metadata_path_text:
        raise ValueError(f"gap review entry does not include metadata_path: {entry_id}")
    metadata_path = Path(metadata_path_text)
    updated = update_gap_review_metadata(
        metadata_path,
        status=status,
        decision=decision,
        expected_mode=expected_mode,
        expected_task=expected_task,
        scope=scope,
        note=note,
    )
    review = normalize_gap_maintainer_review(updated.get("maintainer_review"))
    return GapReviewUpdateResult(
        build_dir=resolved_build_dir,
        entry_id=_string_value(entry_id),
        metadata_path=metadata_path,
        review=review,
    )


def _string_value(value: Any) -> str:
    return str(value).strip() if value is not None else ""
