from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sentieon_assist.eval_trace_plane import aggregate_runtime_eval_traces, project_runtime_eval_trace
from sentieon_assist.knowledge_build import review_knowledge_build
from sentieon_assist.session_events import default_runtime_root, load_session_events, session_log_path


@dataclass(frozen=True)
class DatasetExportResult:
    build_dir: Path
    build_id: str
    output_path: Path
    exported_count: int
    skipped_count: int
    sample_class_counts: dict[str, int]


def export_reviewed_gap_dataset(
    *,
    build_root: str | Path,
    output_path: str | Path,
    build_id: str | None = None,
    runtime_root: str | Path | None = None,
) -> DatasetExportResult:
    review = review_knowledge_build(build_root=build_root, build_id=build_id)
    build_dir = review.build_dir
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    gap_reviews = _read_jsonl(build_dir / "gap_intake_review.jsonl")
    gap_eval_seeds = _read_jsonl(build_dir / "gap_eval_seed.jsonl")
    incidents = _incident_index(build_dir / "candidate-packs" / "incident-memory.json")
    review_index = {
        str(item.get("entry_id", "")).strip(): item
        for item in gap_reviews
        if str(item.get("entry_id", "")).strip()
    }
    resolved_runtime_root = Path(runtime_root) if runtime_root is not None else default_runtime_root()

    exported_records: list[dict[str, Any]] = []
    skipped_count = 0
    for seed in gap_eval_seeds:
        record = _build_reviewed_gap_sample(
            seed=seed,
            review_record=review_index.get(str(seed.get("entry_id", "")).strip()),
            incidents=incidents,
            build_dir=build_dir,
            runtime_root=resolved_runtime_root,
        )
        if record is None:
            skipped_count += 1
            continue
        exported_records.append(record)

    with resolved_output_path.open("w", encoding="utf-8") as handle:
        for record in exported_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    sample_class_counts = {"reviewed_gap_support_sample": len(exported_records)} if exported_records else {}
    return DatasetExportResult(
        build_dir=build_dir,
        build_id=review.build_id,
        output_path=resolved_output_path,
        exported_count=len(exported_records),
        skipped_count=skipped_count,
        sample_class_counts=sample_class_counts,
    )


def format_dataset_export_summary(result: DatasetExportResult) -> str:
    lines = [
        f"Dataset export: {result.output_path}",
        f"Build ID: {result.build_id}",
        f"Exported samples: {result.exported_count}",
        f"Skipped samples: {result.skipped_count}",
    ]
    if result.sample_class_counts:
        lines.append("Sample classes:")
        for sample_class, count in sorted(result.sample_class_counts.items()):
            lines.append(f"- {sample_class}: {count}")
    else:
        lines.append("No audited dataset samples were exported for this build.")
    return "\n".join(lines)


def _build_reviewed_gap_sample(
    *,
    seed: dict[str, Any],
    review_record: dict[str, Any] | None,
    incidents: dict[str, dict[str, Any]],
    build_dir: Path,
    runtime_root: Path,
) -> dict[str, Any] | None:
    if not isinstance(review_record, dict):
        return None
    if str(review_record.get("review_status", "")).strip() != "triaged":
        return None
    if str(review_record.get("review_decision", "")).strip() != "seed_eval":
        return None

    entry_id = str(seed.get("entry_id", "")).strip()
    session_id = str(seed.get("session_id", "")).strip()
    selected_turn_ids = [str(item).strip() for item in seed.get("selected_turn_ids", []) if str(item).strip()]
    if not entry_id or not session_id or not selected_turn_ids:
        return None

    trace_events = _load_selected_turn_events(session_id, selected_turn_ids, runtime_root=runtime_root)
    if len(trace_events) != len(selected_turn_ids):
        return None

    metadata_path_text = str(review_record.get("metadata_path", "")).strip()
    metadata = _read_yaml_object(Path(metadata_path_text)) if metadata_path_text else {}
    if metadata_path_text and not metadata:
        return None

    incident = _merged_incident_context(
        entry_id=entry_id,
        incident_entry=incidents.get(entry_id, {}),
        metadata=metadata,
        review_record=review_record,
    )

    sample = {
        "sample_id": f"reviewed-gap-support.{seed.get('build_id', build_dir.name)}.{entry_id}",
        "sample_type": "reviewed_gap_support_sample",
        "build_id": str(seed.get("build_id", build_dir.name)).strip() or build_dir.name,
        "vendor_id": incident.get("vendor_id", ""),
        "vendor_version": incident.get("vendor_version", ""),
        "review_status": str(review_record.get("review_status", "")).strip(),
        "review_decision": str(review_record.get("review_decision", "")).strip(),
        "review_scope": str(review_record.get("review_scope", "")).strip(),
        "review_notes": str(review_record.get("review_notes", "")).strip(),
        "expected_answer_contract": {
            "expected_mode": str(seed.get("expected_mode", review_record.get("expected_mode", ""))).strip(),
            "expected_task": str(seed.get("expected_task", review_record.get("expected_task", ""))).strip(),
        },
        "incident": incident,
        "support_trace": {
            "session_id": session_id,
            "selected_turn_ids": selected_turn_ids,
            "scope": str(seed.get("scope", review_record.get("review_scope", ""))).strip(),
            "turns": [_trace_turn_payload(event) for event in trace_events],
        },
        "source_artifacts": _unique(
            [
                str(build_dir / "gap_eval_seed.jsonl"),
                str(build_dir / "gap_intake_review.jsonl"),
                str(build_dir / "candidate-packs" / "incident-memory.json"),
                metadata_path_text,
                str(session_log_path(session_id, runtime_root=runtime_root)),
            ]
        ),
    }
    sample["support_trace"]["eval_trace_summary"] = aggregate_runtime_eval_traces(
        [turn.get("eval_trace", {}) for turn in sample["support_trace"]["turns"]]
    )
    sample["eval_trace"] = dict(sample["support_trace"]["eval_trace_summary"])
    return sample


def _merged_incident_context(
    *,
    entry_id: str,
    incident_entry: dict[str, Any],
    metadata: dict[str, Any],
    review_record: dict[str, Any],
) -> dict[str, Any]:
    vendor_id = _first_text(metadata.get("vendor_id"), incident_entry.get("vendor_id"), "sentieon")
    vendor_version = _first_text(
        metadata.get("vendor_version"),
        incident_entry.get("vendor_version"),
        review_record.get("vendor_version"),
    )
    return {
        "entry_id": entry_id,
        "gap_type": _first_text(metadata.get("gap_type"), incident_entry.get("gap_type"), review_record.get("gap_type")),
        "user_question": _first_text(
            metadata.get("user_question"),
            incident_entry.get("user_question"),
            review_record.get("user_question"),
        ),
        "known_context": _dict_value(
            metadata.get("known_context"),
            incident_entry.get("known_context"),
            review_record.get("known_context"),
        ),
        "missing_materials": _list_value(
            metadata.get("missing_materials"),
            incident_entry.get("missing_materials"),
            review_record.get("missing_materials"),
        ),
        "captured_at": _first_text(
            metadata.get("captured_at"),
            incident_entry.get("captured_at"),
            review_record.get("captured_at"),
        ),
        "origin": _first_text(metadata.get("origin"), incident_entry.get("origin")),
        "vendor_id": vendor_id,
        "vendor_version": vendor_version,
    }


def _load_selected_turn_events(
    session_id: str,
    turn_ids: list[str],
    *,
    runtime_root: Path,
) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for event in load_session_events(session_id, runtime_root=runtime_root):
        if str(event.get("event_type", "")).strip() != "turn_resolved":
            continue
        turn_id = str(event.get("turn_id", "")).strip()
        if turn_id:
            indexed[turn_id] = event
    return [indexed[turn_id] for turn_id in turn_ids if turn_id in indexed]


def _trace_turn_payload(event: dict[str, Any]) -> dict[str, Any]:
    planner = event.get("planner", {}) if isinstance(event.get("planner"), dict) else {}
    answer = event.get("answer", {}) if isinstance(event.get("answer"), dict) else {}
    eval_trace = answer.get("eval_trace") if isinstance(answer.get("eval_trace"), dict) else project_runtime_eval_trace(event)
    return {
        "turn_id": str(event.get("turn_id", "")).strip(),
        "turn_index": int(event.get("turn_index", 0) or 0),
        "prompt": str(planner.get("raw_query", "")).strip(),
        "effective_query": str(planner.get("effective_query", "")).strip(),
        "response": str(answer.get("response_text", "")).strip(),
        "response_mode": str(answer.get("response_mode", "")).strip(),
        "task": str(planner.get("task", "")).strip(),
        "issue_type": str(planner.get("issue_type", "")).strip(),
        "support_intent": str(planner.get("support_intent", "")).strip(),
        "fallback_mode": str(planner.get("fallback_mode", "")).strip(),
        "vendor_id": str(planner.get("vendor_id", "")).strip(),
        "vendor_version": str(planner.get("vendor_version", "")).strip(),
        "reused_anchor": bool(planner.get("reused_anchor", False)),
        "sources": _list_value(answer.get("sources")),
        "boundary_tags": _list_value(answer.get("boundary_tags")),
        "resolver_path": _list_value(answer.get("resolver_path")),
        "gap_record": answer.get("gap_record") if isinstance(answer.get("gap_record"), dict) else None,
        "eval_trace": dict(eval_trace),
    }


def _incident_index(path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json_object(path)
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "")).strip()
        if entry_id:
            indexed[entry_id] = entry
    return indexed


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _read_yaml_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value).strip() if value is not None else ""
        if text:
            return text
    return ""


def _dict_value(*values: Any) -> dict[str, str]:
    for value in values:
        if not isinstance(value, dict):
            continue
        normalized = {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip() and str(item).strip()
        }
        if normalized:
            return normalized
    return {}


def _list_value(*values: Any) -> list[str]:
    for value in values:
        if not isinstance(value, list):
            continue
        normalized = [str(item).strip() for item in value if str(item).strip()]
        if normalized:
            return normalized
    return []


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items
