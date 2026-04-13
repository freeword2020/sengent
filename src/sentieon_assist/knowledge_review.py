from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentieon_assist.factory_model import FACTORY_DRAFT_DIRECTORY_NAME, list_attached_factory_drafts
from sentieon_assist.knowledge_build import PILOT_CLOSED_LOOP_REPORT_NAME, review_knowledge_build


@dataclass(frozen=True)
class MaintainerQueueBucket:
    bucket_id: str
    title: str
    count: int
    why: str
    next_action: str
    recommended_command: str
    artifact_path: str
    samples: tuple[str, ...]
    eval_trace: dict[str, Any] | None = None


@dataclass(frozen=True)
class MaintainerQueueResult:
    build_dir: Path
    build_id: str
    total_items: int
    buckets: tuple[MaintainerQueueBucket, ...]


def build_maintainer_queue(
    *,
    build_root: str | Path,
    build_id: str | None = None,
) -> MaintainerQueueResult:
    review = review_knowledge_build(build_root=build_root, build_id=build_id)
    build_dir = review.build_dir
    manifest_path = build_dir / "candidate-packs" / "manifest.json"
    manifest = _read_json_object(manifest_path)
    parameter_suggestions = _read_jsonl(build_dir / "parameter_review_suggestion.jsonl")
    gap_reviews = _read_jsonl(build_dir / "gap_intake_review.jsonl")
    gap_eval_seeds = _read_jsonl(build_dir / "gap_eval_seed.jsonl")
    closed_loop_report = _read_json_object(build_dir / PILOT_CLOSED_LOOP_REPORT_NAME)
    attached_factory_drafts = list_attached_factory_drafts(build_root=build_root, build_id=review.build_id)

    buckets: list[MaintainerQueueBucket] = []

    pending_gap_reviews = [item for item in gap_reviews if str(item.get("review_status", "")).strip() == "pending"]
    if pending_gap_reviews:
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="pending-gap-triage",
                title="Pending Gap Triage",
                count=len(pending_gap_reviews),
                why="Runtime gaps already entered the offline loop, but they still need a maintainer decision before they can seed eval or be closed.",
                next_action="Write a maintainer decision for each pending gap entry.",
                recommended_command=(
                    "sengent knowledge triage-gap "
                    f"--build-id {review.build_id} --entry-id {pending_gap_reviews[0].get('entry_id', '<entry_id>')} --decision <decision>"
                ),
                artifact_path=str(build_dir / "gap_intake_review.jsonl"),
                samples=tuple(
                    f"{item.get('entry_id', '')} ({item.get('gap_type', 'unknown')})"
                    for item in pending_gap_reviews[:3]
                ),
            )
        )

    source_review_items = [
        item
        for item in _list_of_dicts(manifest.get("compile_skips"))
        if str(item.get("reason", "")).strip() == "factory intake pending review"
    ]
    if source_review_items:
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="pending-source-review",
                title="Pending Source Review",
                count=len(source_review_items),
                why="Source intake imported raw material into the inbox, but it is still blocked from candidate compilation until a maintainer reviews and promotes it.",
                next_action="Open the imported source entry, confirm metadata, mark the intake ready, then rebuild.",
                recommended_command="sengent knowledge build --inbox-dir <dir> --build-root <dir>",
                artifact_path=str(manifest_path),
                samples=tuple(str(item.get("relative_path", "")) for item in source_review_items[:3]),
            )
        )

    if attached_factory_drafts:
        first_draft = attached_factory_drafts[0]
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="pending-factory-draft-review",
                title="Pending Factory Draft Review",
                count=len(attached_factory_drafts),
                why=(
                    "Offline factory workers already drafted candidate review material for this build, but "
                    "maintainers still need to validate the cited evidence before any of it can re-enter the "
                    "formal inbox/build flow."
                ),
                next_action=(
                    "Inspect each attached factory draft, confirm the evidence and draft items, then manually "
                    "convert the accepted content into inbox or metadata changes."
                ),
                recommended_command=(
                    first_draft.recommended_command
                    or f"sengent knowledge review-factory-draft --build-id {review.build_id} --build-root {Path(build_root)}"
                ),
                artifact_path=str(build_dir / FACTORY_DRAFT_DIRECTORY_NAME),
                samples=tuple(f"{draft.draft_id} ({draft.task_kind})" for draft in attached_factory_drafts[:3]),
                eval_trace=dict(first_draft.eval_trace),
            )
        )

    if parameter_suggestions:
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="pending-parameter-review",
                title="Pending Parameter Review",
                count=len(parameter_suggestions),
                why="The compiler found parameter candidates that look real enough to review, but they are not formal knowledge until a maintainer accepts or rejects them.",
                next_action="Review the suggested parameter candidates and convert the real ones into structured knowledge entries.",
                recommended_command=f"sengent knowledge review --build-id {review.build_id} --build-root {Path(build_root)}",
                artifact_path=str(build_dir / "parameter_review_suggestion.jsonl"),
                samples=tuple(
                    f"{item.get('module_id', '')}:{item.get('parameter_name', '')}"
                    for item in parameter_suggestions[:3]
                ),
            )
        )

    closed_loop_ok = bool(closed_loop_report.get("ok")) if closed_loop_report else False
    if gap_eval_seeds and not closed_loop_ok:
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="pending-gate-input",
                title="Pending Gate Input",
                count=len(gap_eval_seeds),
                why="Eval seeds exist for this build, but the closed-loop gate has not consumed them yet or has not passed.",
                next_action="Run the closed-loop gate with the generated eval seeds before considering activation.",
                recommended_command=(
                    "python scripts/pilot_closed_loop.py "
                    f"--source-dir {build_dir / 'candidate-packs'} "
                    f"--runtime-feedback-path {build_dir / 'gap_eval_seed.jsonl'} "
                    f"--json-out {build_dir / PILOT_CLOSED_LOOP_REPORT_NAME}"
                ),
                artifact_path=str(build_dir / "gap_eval_seed.jsonl"),
                samples=tuple(
                    f"{item.get('entry_id', '')}:{item.get('expected_mode', '')}/{item.get('expected_task', '')}"
                    for item in gap_eval_seeds[:3]
                ),
            )
        )

    changed_pack_samples = _changed_pack_samples(manifest)
    if changed_pack_samples:
        buckets.append(
            MaintainerQueueBucket(
                bucket_id="candidate-pack-change",
                title="Candidate Pack Change",
                count=len(changed_pack_samples),
                why="This build changed candidate knowledge packs, so a maintainer still needs to review what facts or guidance would move toward gate and activation.",
                next_action="Inspect the changed candidate IDs, confirm the update is intentional, then proceed to gate or fix the source material.",
                recommended_command=f"sengent knowledge review --build-id {review.build_id} --build-root {Path(build_root)}",
                artifact_path=str(build_dir / "report.md"),
                samples=tuple(changed_pack_samples[:3]),
            )
        )

    total_items = sum(bucket.count for bucket in buckets)
    return MaintainerQueueResult(
        build_dir=build_dir,
        build_id=review.build_id,
        total_items=total_items,
        buckets=tuple(buckets),
    )


def format_maintainer_queue(result: MaintainerQueueResult) -> str:
    lines = [
        f"Knowledge queue: {result.build_dir}",
        f"Build ID: {result.build_id}",
        f"Total pending items: {result.total_items}",
    ]
    if not result.buckets:
        lines.append("No maintainer queue items for this build.")
        lines.append("Next action: verify gate reports and only then consider activation.")
        return "\n".join(lines)

    for bucket in result.buckets:
        lines.extend(
            [
                "",
                f"## {bucket.title}",
                f"Count: {bucket.count}",
                f"Why: {bucket.why}",
                f"Next action: {bucket.next_action}",
                f"Recommended command: {bucket.recommended_command}",
                f"Artifact: {bucket.artifact_path}",
            ]
        )
        if bucket.samples:
            lines.append("Samples:")
            lines.extend(f"- {sample}" for sample in bucket.samples)
        if isinstance(bucket.eval_trace, dict) and bucket.eval_trace:
            lifecycle_state = str(bucket.eval_trace.get("lifecycle_state", "")).strip()
            evidence_fidelity = str(bucket.eval_trace.get("evidence_fidelity", "")).strip()
            trust_boundary_policy = str(bucket.eval_trace.get("trust_boundary_policy_name", "")).strip()
            trust_boundary_audit_present = bool(bucket.eval_trace.get("trust_boundary_audit_present", False))
            trust_boundary_audit_posture = str(bucket.eval_trace.get("trust_boundary_audit_posture", "")).strip()
            if lifecycle_state:
                lines.append(f"Lifecycle state: {lifecycle_state}")
            if evidence_fidelity:
                lines.append(f"Evidence fidelity: {evidence_fidelity}")
            if trust_boundary_policy:
                lines.append(f"Trust boundary policy: {trust_boundary_policy}")
            if trust_boundary_audit_present:
                lines.append("Trust boundary audit: present")
            if trust_boundary_audit_posture:
                lines.append(f"Audit posture: {trust_boundary_audit_posture}")
    return "\n".join(lines)


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


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _changed_pack_samples(manifest: dict[str, Any]) -> list[str]:
    pack_diffs = manifest.get("pack_diffs")
    if not isinstance(pack_diffs, dict):
        return []
    samples: list[str] = []
    for pack_name, diff in sorted(pack_diffs.items()):
        if not isinstance(diff, dict):
            continue
        changed_ids = []
        for field in ("added_ids", "updated_ids", "removed_ids"):
            values = diff.get(field)
            if isinstance(values, list):
                changed_ids.extend(str(item) for item in values if str(item).strip())
        if not changed_ids:
            continue
        samples.extend(f"{pack_name}:{item}" for item in changed_ids)
    return samples
