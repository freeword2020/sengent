from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol
from uuid import uuid4

from sentieon_assist.runtime_invariants import PromotionState, normalize_promotion_state
from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryDecision,
    build_trust_boundary_result,
)


FACTORY_MODEL_INTERFACE_VERSION = "factory-model-interface-v1"
FACTORY_DRAFT_ORIGIN = "knowledge-factory-model-interface"
FACTORY_DRAFT_DIRECTORY_NAME = "factory-drafts"
FACTORY_DRAFT_QUEUE_BUCKET_ID = "pending-factory-draft-review"
DEFAULT_FACTORY_ADAPTER = "stub"
DEFAULT_VENDOR_ID = "sentieon"
REVIEW_STATUS_NEEDS_REVIEW = "needs_review"

_TASK_ALIASES = {
    "candidate_draft": "candidate_draft",
    "candidate-draft": "candidate_draft",
    "incident_normalization": "incident_normalization",
    "incident-normalization": "incident_normalization",
    "contradiction_cluster": "contradiction_cluster",
    "contradiction-cluster": "contradiction_cluster",
    "dataset_draft": "dataset_draft",
    "dataset-draft": "dataset_draft",
}

_SOURCE_FILE_TYPES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".json": "json",
    ".jsonl": "jsonl",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".csv": "csv",
    ".tsv": "tsv",
    ".html": "html",
    ".htm": "html",
}

_PROMPT_TEMPLATES = {
    "candidate_draft": {
        "template_id": "factory.candidate_draft.v1",
        "template_version": "v1",
        "prompt": (
            "You are drafting maintainer-facing candidate notes in an offline knowledge factory.\n"
            "Task kind: candidate_draft\n"
            "Vendor: {vendor_id}\n"
            "Source references:\n{source_lines}\n"
            "Operator instruction: {instruction}\n"
            "Output constraints:\n"
            "- Draft only; never mark facts active.\n"
            "- Keep review required.\n"
            "- Summarize candidate facts and open review questions."
        ),
    },
    "incident_normalization": {
        "template_id": "factory.incident_normalization.v1",
        "template_version": "v1",
        "prompt": (
            "You are normalizing incident inputs for offline maintainer review.\n"
            "Task kind: incident_normalization\n"
            "Vendor: {vendor_id}\n"
            "Source references:\n{source_lines}\n"
            "Operator instruction: {instruction}\n"
            "Output constraints:\n"
            "- Draft only; never update runtime truth.\n"
            "- Keep review required.\n"
            "- Extract concise normalized incident candidates."
        ),
    },
    "contradiction_cluster": {
        "template_id": "factory.contradiction_cluster.v1",
        "template_version": "v1",
        "prompt": (
            "You are clustering possible contradictions for offline maintainer review.\n"
            "Task kind: contradiction_cluster\n"
            "Vendor: {vendor_id}\n"
            "Source references:\n{source_lines}\n"
            "Operator instruction: {instruction}\n"
            "Output constraints:\n"
            "- Draft only; never resolve contradictions automatically.\n"
            "- Keep review required.\n"
            "- Group likely contradiction candidates with evidence anchors."
        ),
    },
    "dataset_draft": {
        "template_id": "factory.dataset_draft.v1",
        "template_version": "v1",
        "prompt": (
            "You are drafting downstream dataset notes in an offline knowledge factory.\n"
            "Task kind: dataset_draft\n"
            "Vendor: {vendor_id}\n"
            "Source references:\n{source_lines}\n"
            "Operator instruction: {instruction}\n"
            "Output constraints:\n"
            "- Draft only; never change runtime knowledge.\n"
            "- Keep review required.\n"
            "- Capture what maintainers should verify before export."
        ),
    },
}


@dataclass(frozen=True)
class FactoryDraftResult:
    output_path: Path
    task_kind: str
    adapter_id: str
    review_status: str
    source_reference_count: int
    build_id: str | None = None


@dataclass(frozen=True)
class FactoryDraftArtifact:
    draft_id: str
    artifact_path: Path
    build_id: str | None
    task_kind: str
    lifecycle_state: str
    created_at: str
    review_status: str
    why: str
    next_action: str
    recommended_command: str
    summary: str
    trust_boundary_provenance: dict[str, Any]
    source_references: tuple[dict[str, Any], ...]
    draft_items: tuple[dict[str, Any], ...]
    review_hints: tuple[str, ...]


@dataclass(frozen=True)
class FactoryDraftReviewResult:
    build_dir: Path
    build_id: str
    selected_draft_id: str | None
    drafts: tuple[FactoryDraftArtifact, ...]


class FactoryModelAdapter(Protocol):
    adapter_id: str
    provider: str
    model_name: str

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class StubFactoryAdapter:
    adapter_id: str = DEFAULT_FACTORY_ADAPTER
    provider: str = "local-stub"
    model_name: str = "stub-factory-v1"

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        task_label = task_kind.replace("_", " ")
        draft_items = [
            {
                "item_id": f"{task_kind}-{index}",
                "title": f"{reference['label']} review candidate",
                "proposed_action": _stub_action_for_task(task_kind),
                "source_path": reference["path"],
                "evidence_preview": reference["preview"],
            }
            for index, reference in enumerate(source_references, start=1)
        ]
        return {
            "summary": (
                f"Stub {task_label} draft for vendor `{vendor_id}` built from "
                f"{len(source_references)} reviewed source reference(s)."
            ),
            "draft_items": draft_items,
            "review_hints": _stub_review_hints(task_kind),
            "adapter_notes": {
                "execution_mode": "offline-stub",
                "prompt_preview": prompt[:240],
            },
        }


def normalize_factory_task_kind(value: str) -> str:
    normalized = _TASK_ALIASES.get(str(value).strip().lower())
    if normalized is None:
        raise ValueError(f"unsupported factory draft task: {value}")
    return normalized


def run_factory_draft(
    *,
    task_kind: str,
    source_refs: Iterable[str | Path],
    output_path: str | Path | None = None,
    build_root: str | Path | None = None,
    build_id: str | None = None,
    vendor_id: str = DEFAULT_VENDOR_ID,
    instruction: str | None = None,
    adapter: str = DEFAULT_FACTORY_ADAPTER,
) -> FactoryDraftResult:
    normalized_task = normalize_factory_task_kind(task_kind)
    normalized_vendor_id = str(vendor_id).strip() or DEFAULT_VENDOR_ID
    normalized_sources = _normalize_source_references(source_refs)
    if not normalized_sources:
        raise ValueError("factory draft requires at least one source reference")

    prompt_provenance = _build_prompt_provenance(
        task_kind=normalized_task,
        vendor_id=normalized_vendor_id,
        instruction=instruction,
        source_references=normalized_sources,
    )
    adapter_impl = _build_adapter(adapter)
    draft_payload = adapter_impl.draft(
        task_kind=normalized_task,
        vendor_id=normalized_vendor_id,
        prompt=prompt_provenance["rendered_prompt"],
        source_references=normalized_sources,
    )

    created_at = datetime.now(timezone.utc).isoformat()
    draft_id = f"factory-draft.{normalized_task}.{uuid4().hex[:12]}"
    attached_build_dir = _resolve_factory_build_dir(build_root, build_id) if build_id else None
    resolved_output_path = _resolve_factory_draft_output_path(
        output_path=output_path,
        build_dir=attached_build_dir,
        draft_id=draft_id,
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    trust_boundary_provenance = _build_factory_trust_boundary_provenance(normalized_sources)
    review_guidance = _build_review_guidance(
        build_id=attached_build_dir.name if attached_build_dir else None,
        draft_id=draft_id,
    )

    artifact = {
        "draft_id": draft_id,
        "artifact_class": "factory_model_draft",
        "origin": FACTORY_DRAFT_ORIGIN,
        "interface_version": FACTORY_MODEL_INTERFACE_VERSION,
        "task_kind": normalized_task,
        "lifecycle_state": normalize_promotion_state(PromotionState.REVIEW_NEEDED),
        "build_id": attached_build_dir.name if attached_build_dir else None,
        "vendor_id": normalized_vendor_id,
        "created_at": created_at,
        "review_status": REVIEW_STATUS_NEEDS_REVIEW,
        "review_required": True,
        "adapter": {
            "adapter_id": adapter_impl.adapter_id,
            "provider": adapter_impl.provider,
            "model_name": adapter_impl.model_name,
            "interface_version": FACTORY_MODEL_INTERFACE_VERSION,
        },
        "prompt_provenance": prompt_provenance,
        "trust_boundary_provenance": trust_boundary_provenance,
        "source_references": normalized_sources,
        "draft_payload": draft_payload,
        "review_guidance": review_guidance,
        "activation_eligibility": {
            "eligible": False,
            "reason": "Factory model outputs are draft-only and require maintainer review.",
        },
    }
    resolved_output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return FactoryDraftResult(
        output_path=resolved_output_path,
        task_kind=normalized_task,
        adapter_id=adapter_impl.adapter_id,
        review_status=REVIEW_STATUS_NEEDS_REVIEW,
        source_reference_count=len(normalized_sources),
        build_id=attached_build_dir.name if attached_build_dir else None,
    )


def format_factory_draft_summary(result: FactoryDraftResult) -> str:
    lines = [
        f"Factory draft artifact: {result.output_path}",
        f"Task: {result.task_kind}",
        f"Adapter: {result.adapter_id}",
        f"Review status: {result.review_status}",
        f"Source references: {result.source_reference_count}",
    ]
    if result.build_id:
        lines.append(f"Attached build: {result.build_id}")
    return "\n".join(lines)


def list_attached_factory_drafts(
    *,
    build_root: str | Path,
    build_id: str | None = None,
) -> tuple[FactoryDraftArtifact, ...]:
    build_dir = _resolve_factory_build_dir(build_root, build_id)
    draft_dir = build_dir / FACTORY_DRAFT_DIRECTORY_NAME
    if not draft_dir.exists():
        return ()
    artifacts: list[FactoryDraftArtifact] = []
    for path in sorted(draft_dir.glob("*.json")):
        record = _load_factory_draft_artifact(path)
        if record is None:
            continue
        if record.review_status != REVIEW_STATUS_NEEDS_REVIEW:
            continue
        if record.build_id and record.build_id != build_dir.name:
            continue
        artifacts.append(record)
    return tuple(artifacts)


def review_factory_drafts(
    *,
    build_root: str | Path,
    build_id: str | None = None,
    draft_id: str | None = None,
) -> FactoryDraftReviewResult:
    build_dir = _resolve_factory_build_dir(build_root, build_id)
    drafts = list_attached_factory_drafts(build_root=build_root, build_id=build_dir.name)
    if draft_id:
        drafts = tuple(draft for draft in drafts if draft.draft_id == draft_id)
        if not drafts:
            raise ValueError(f"factory draft not found in build {build_dir.name}: {draft_id}")
    return FactoryDraftReviewResult(
        build_dir=build_dir,
        build_id=build_dir.name,
        selected_draft_id=draft_id,
        drafts=drafts,
    )


def format_factory_draft_review(result: FactoryDraftReviewResult) -> str:
    lines = [
        f"Factory draft review: {result.build_dir}",
        f"Build ID: {result.build_id}",
        f"Attached drafts: {len(result.drafts)}",
    ]
    if not result.drafts:
        lines.append("No attached factory drafts for this build.")
        lines.append(
            f"Next action: run sengent knowledge factory-draft --build-id {result.build_id} --task <kind> --source-ref <path>"
        )
        return "\n".join(lines)

    for draft in result.drafts:
        lines.extend(
            [
                "",
                f"## {draft.draft_id}",
                f"Task: {draft.task_kind}",
                f"Created at: {draft.created_at}",
                f"Review status: {draft.review_status}",
                f"Why: {draft.why}",
                f"Next action: {draft.next_action}",
                f"Recommended command: {draft.recommended_command}",
                f"Artifact: {draft.artifact_path}",
                f"Draft summary: {draft.summary}",
            ]
        )
        if draft.source_references:
            lines.append("Source references:")
            lines.extend(
                f"- {reference.get('label', '')} ({reference.get('file_type', 'unknown')}): {reference.get('path', '')}"
                for reference in draft.source_references
            )
        if draft.draft_items:
            lines.append("Draft items:")
            lines.extend(
                f"- {item.get('item_id', '')}: {item.get('title', '')}"
                for item in draft.draft_items
            )
        if draft.review_hints:
            lines.append("Review hints:")
            lines.extend(f"- {hint}" for hint in draft.review_hints)
    return "\n".join(lines)


def _build_prompt_provenance(
    *,
    task_kind: str,
    vendor_id: str,
    instruction: str | None,
    source_references: list[dict[str, Any]],
) -> dict[str, Any]:
    template = _PROMPT_TEMPLATES[task_kind]
    source_lines = "\n".join(
        f"- {reference['label']} ({reference['file_type']}): {reference['path']}"
        for reference in source_references
    )
    normalized_instruction = str(instruction).strip() or "No extra operator instruction provided."
    rendered_prompt = str(template["prompt"]).format(
        vendor_id=vendor_id,
        source_lines=source_lines,
        instruction=normalized_instruction,
    )
    return {
        "template_id": template["template_id"],
        "template_version": template["template_version"],
        "instruction": normalized_instruction,
        "source_reference_paths": [reference["path"] for reference in source_references],
        "rendered_prompt": rendered_prompt,
    }


def _normalize_source_references(source_refs: Iterable[str | Path]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for source_ref in source_refs:
        resolved_path = Path(source_ref)
        if not resolved_path.exists():
            raise ValueError(f"factory source reference not found: {resolved_path}")
        preview = _build_source_preview(resolved_path)
        normalized.append(
            {
                "path": str(resolved_path.resolve()),
                "label": resolved_path.name,
                "file_type": _detect_source_file_type(resolved_path),
                "preview": preview,
            }
        )
    return normalized


def _detect_source_file_type(path: Path) -> str:
    file_type = _SOURCE_FILE_TYPES.get(path.suffix.lower())
    if file_type is not None:
        return file_type
    if path.suffix:
        return path.suffix.lower().lstrip(".")
    return "text"


def _build_source_preview(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    collapsed = " ".join(text.split())
    if not collapsed:
        return ""
    return collapsed[:280]


def _build_adapter(adapter: str) -> FactoryModelAdapter:
    normalized_adapter = str(adapter).strip().lower() or DEFAULT_FACTORY_ADAPTER
    if normalized_adapter == DEFAULT_FACTORY_ADAPTER:
        return StubFactoryAdapter()
    raise ValueError(f"unsupported factory draft adapter: {adapter}")


def _resolve_factory_build_dir(build_root: str | Path | None, build_id: str | None) -> Path:
    if build_root is None:
        raise ValueError("factory draft build attachment requires --build-root")
    resolved_build_root = Path(build_root)
    if build_id:
        build_dir = resolved_build_root / build_id
    else:
        build_dir = _latest_build_directory(resolved_build_root)
    if build_dir is None or not build_dir.exists():
        raise ValueError(f"knowledge build not found under {resolved_build_root}")
    report_path = build_dir / "report.md"
    if not report_path.exists():
        raise ValueError(f"knowledge build report missing: {report_path}")
    return build_dir


def _latest_build_directory(build_root: Path) -> Path | None:
    if not build_root.exists():
        return None
    candidates = sorted(
        path
        for path in build_root.iterdir()
        if path.is_dir() and (path / "report.md").exists()
    )
    return candidates[-1] if candidates else None


def _resolve_factory_draft_output_path(
    *,
    output_path: str | Path | None,
    build_dir: Path | None,
    draft_id: str,
) -> Path:
    if build_dir is not None:
        return build_dir / FACTORY_DRAFT_DIRECTORY_NAME / f"{draft_id}.json"
    if output_path is not None:
        return Path(output_path)
    raise ValueError("factory draft requires --output or --build-id")


def _build_review_guidance(*, build_id: str | None, draft_id: str) -> dict[str, str]:
    if build_id:
        return {
            "queue_bucket_id": FACTORY_DRAFT_QUEUE_BUCKET_ID,
            "why": (
                "A factory worker produced a draft artifact for this build, but the draft still needs maintainer "
                "evidence review before anything can re-enter the inbox/build flow."
            ),
            "next_action": (
                "Inspect the draft, validate each item against the cited sources, then manually turn the accepted "
                "content back into inbox or metadata changes."
            ),
            "recommended_command": (
                f"sengent knowledge review-factory-draft --build-id {build_id} --draft-id {draft_id}"
            ),
        }
    return {
        "queue_bucket_id": "",
        "why": "This standalone factory draft still needs maintainer review before it can influence any offline work.",
        "next_action": "Review the artifact manually or regenerate it attached to a build to enter the maintainer queue.",
        "recommended_command": "",
    }


def _load_factory_draft_artifact(path: Path) -> FactoryDraftArtifact | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("artifact_class") != "factory_model_draft":
        return None
    draft_id = str(payload.get("draft_id", "")).strip()
    task_kind = str(payload.get("task_kind", "")).strip()
    created_at = str(payload.get("created_at", "")).strip()
    review_status = str(payload.get("review_status", "")).strip()
    if not draft_id or not task_kind or not created_at or not review_status:
        return None
    try:
        lifecycle_state = normalize_promotion_state(payload.get("lifecycle_state"))
    except ValueError:
        return None
    build_id = str(payload.get("build_id", "")).strip() or _infer_build_id_from_path(path)
    review_guidance = payload.get("review_guidance")
    if not isinstance(review_guidance, dict):
        review_guidance = _build_review_guidance(build_id=build_id or None, draft_id=draft_id)
    draft_payload = payload.get("draft_payload")
    if not isinstance(draft_payload, dict):
        draft_payload = {}
    source_references = payload.get("source_references")
    trust_boundary_provenance = payload.get("trust_boundary_provenance")
    if not isinstance(trust_boundary_provenance, dict):
        trust_boundary_provenance = _build_factory_trust_boundary_provenance(
            source_references if isinstance(source_references, list) else []
        )
    draft_items = draft_payload.get("draft_items")
    review_hints = draft_payload.get("review_hints")
    return FactoryDraftArtifact(
        draft_id=draft_id,
        artifact_path=path,
        build_id=build_id or None,
        task_kind=task_kind,
        lifecycle_state=lifecycle_state,
        created_at=created_at,
        review_status=review_status,
        why=str(review_guidance.get("why", "")).strip(),
        next_action=str(review_guidance.get("next_action", "")).strip(),
        recommended_command=str(review_guidance.get("recommended_command", "")).strip(),
        summary=str(draft_payload.get("summary", "")).strip(),
        trust_boundary_provenance=dict(trust_boundary_provenance),
        source_references=tuple(item for item in source_references if isinstance(item, dict))
        if isinstance(source_references, list)
        else (),
        draft_items=tuple(item for item in draft_items if isinstance(item, dict)) if isinstance(draft_items, list) else (),
        review_hints=tuple(str(item) for item in review_hints if str(item).strip())
        if isinstance(review_hints, list)
        else (),
    )


def _infer_build_id_from_path(path: Path) -> str:
    if path.parent.name != FACTORY_DRAFT_DIRECTORY_NAME:
        return ""
    parent = path.parent.parent
    return parent.name if parent.name else ""


def _stub_action_for_task(task_kind: str) -> str:
    if task_kind == "candidate_draft":
        return "Extract candidate knowledge statements for maintainer review."
    if task_kind == "incident_normalization":
        return "Normalize the incident narrative into structured support fields."
    if task_kind == "contradiction_cluster":
        return "Group conflicting statements and keep both sides for maintainer review."
    return "Draft downstream dataset notes and export checks for maintainer review."


def _stub_review_hints(task_kind: str) -> list[str]:
    task_specific = {
        "candidate_draft": "Confirm each candidate statement against the authoritative source before build.",
        "incident_normalization": "Check the normalized fields against the original incident wording before reuse.",
        "contradiction_cluster": "Verify each contradiction cluster against the cited sources before resolution.",
        "dataset_draft": "Confirm expected answer contract fields before exporting any downstream training asset.",
    }
    return [
        "This artifact is draft-only and cannot bypass build/review/gate/activate.",
        task_specific[task_kind],
        "Promote only maintainer-reviewed content into formal knowledge or dataset exports.",
    ]


def _build_factory_trust_boundary_provenance(source_references: list[dict[str, Any]]) -> dict[str, Any]:
    decision = TrustBoundaryDecision(
        policy_name="factory-draft-local-only",
        items=tuple(
            OutboundContextItem(
                key=str(reference.get("label", "")).strip(),
                value=reference.get("preview", ""),
                disposition=OutboundContextDisposition.LOCAL_ONLY,
                provenance={
                    "path": reference.get("path", ""),
                    "file_type": reference.get("file_type", ""),
                },
            )
            for reference in source_references
        ),
    )
    return build_trust_boundary_result(decision).summary
