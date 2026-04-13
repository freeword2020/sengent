from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol
from uuid import uuid4


FACTORY_MODEL_INTERFACE_VERSION = "factory-model-interface-v1"
FACTORY_DRAFT_ORIGIN = "knowledge-factory-model-interface"
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
    output_path: str | Path,
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
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        "draft_id": f"factory-draft.{normalized_task}.{uuid4().hex[:12]}",
        "artifact_class": "factory_model_draft",
        "origin": FACTORY_DRAFT_ORIGIN,
        "interface_version": FACTORY_MODEL_INTERFACE_VERSION,
        "task_kind": normalized_task,
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
        "source_references": normalized_sources,
        "draft_payload": draft_payload,
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
    )


def format_factory_draft_summary(result: FactoryDraftResult) -> str:
    return "\n".join(
        [
            f"Factory draft artifact: {result.output_path}",
            f"Task: {result.task_kind}",
            f"Adapter: {result.adapter_id}",
            f"Review status: {result.review_status}",
            f"Source references: {result.source_reference_count}",
        ]
    )


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
