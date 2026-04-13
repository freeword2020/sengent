from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentieon_assist.factory_model import normalize_factory_task_kind, run_factory_draft


def test_normalize_factory_task_kind_accepts_hyphenated_aliases():
    assert normalize_factory_task_kind("candidate_draft") == "candidate_draft"
    assert normalize_factory_task_kind("incident-normalization") == "incident_normalization"
    assert normalize_factory_task_kind("contradiction-cluster") == "contradiction_cluster"
    assert normalize_factory_task_kind("dataset-draft") == "dataset_draft"


def test_normalize_factory_task_kind_rejects_unknown_task():
    with pytest.raises(ValueError, match="unsupported factory draft task"):
        normalize_factory_task_kind("runtime_answering")


def test_run_factory_draft_writes_review_needed_artifact_with_prompt_and_source_provenance(tmp_path: Path):
    source_path = tmp_path / "vendor-note.md"
    source_path.write_text("# FastDedup\n\nUse FastDedup before alignment.\n", encoding="utf-8")
    output_path = tmp_path / "drafts" / "candidate-draft.json"

    result = run_factory_draft(
        task_kind="candidate_draft",
        source_refs=[source_path],
        output_path=output_path,
        vendor_id="sentieon",
        instruction="Draft candidate review notes from this source.",
    )

    assert result.review_status == "needs_review"
    assert result.adapter_id == "stub"
    assert result.source_reference_count == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["task_kind"] == "candidate_draft"
    assert payload["vendor_id"] == "sentieon"
    assert payload["adapter"]["adapter_id"] == "stub"
    assert payload["adapter"]["provider"] == "local-stub"
    assert payload["adapter"]["model_name"] == "stub-factory-v1"
    assert payload["review_status"] == "needs_review"
    assert payload["review_required"] is True
    assert payload["prompt_provenance"]["template_id"] == "factory.candidate_draft.v1"
    assert payload["prompt_provenance"]["template_version"] == "v1"
    assert "Draft candidate review notes from this source." in payload["prompt_provenance"]["rendered_prompt"]
    assert payload["source_references"][0]["path"] == str(source_path.resolve())
    assert payload["source_references"][0]["label"] == source_path.name
    assert payload["source_references"][0]["file_type"] == "markdown"
    assert "FastDedup" in payload["source_references"][0]["preview"]
    assert payload["draft_payload"]["summary"]
    assert payload["draft_payload"]["draft_items"]
    assert payload["draft_payload"]["review_hints"]
