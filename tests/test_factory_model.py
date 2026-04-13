from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentieon_assist.config import AppConfig
from sentieon_assist.factory_backends import OpenAICompatibleFactoryBackend, StubFactoryBackend, build_factory_backend
from sentieon_assist.factory_model import normalize_factory_task_kind, review_factory_drafts, run_factory_draft


class FakeHostedFactoryAdapter:
    adapter_id = "hosted"
    provider = "openai_compatible"
    model_name = "factory-gpt"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, object]],
    ) -> dict[str, object]:
        self.calls.append(
            {
                "task_kind": task_kind,
                "vendor_id": vendor_id,
                "prompt": prompt,
                "source_references": source_references,
            }
        )
        return {
            "summary": "hosted draft summary",
            "draft_items": [],
            "review_hints": ["keep review required"],
            "adapter_notes": {"execution_mode": "hosted-review-only"},
        }


def _factory_config(**overrides: str) -> AppConfig:
    return AppConfig(
        runtime_llm_provider="ollama",
        runtime_llm_base_url="http://127.0.0.1:11434",
        runtime_llm_model="gemma4:e4b",
        runtime_llm_api_key="",
        runtime_llm_keep_alive="30m",
        runtime_llm_supports_tools=False,
        runtime_llm_supports_json_schema=False,
        runtime_llm_supports_reasoning_effort=False,
        runtime_llm_supports_streaming=True,
        runtime_llm_max_context=0,
        runtime_llm_prompt_cache_behavior="provider_managed",
        llm_fallback_backend="",
        llm_fallback_base_url="",
        llm_fallback_model="",
        llm_fallback_api_key="",
        knowledge_dir="",
        source_dir="/tmp/sentieon-sources",
        factory_hosted_provider=overrides.get("factory_hosted_provider", ""),
        factory_hosted_base_url=overrides.get("factory_hosted_base_url", ""),
        factory_hosted_model=overrides.get("factory_hosted_model", ""),
        factory_hosted_api_key=overrides.get("factory_hosted_api_key", ""),
    )


def test_normalize_factory_task_kind_accepts_hyphenated_aliases():
    assert normalize_factory_task_kind("candidate_draft") == "candidate_draft"
    assert normalize_factory_task_kind("incident-normalization") == "incident_normalization"
    assert normalize_factory_task_kind("contradiction-cluster") == "contradiction_cluster"
    assert normalize_factory_task_kind("dataset-draft") == "dataset_draft"


def test_normalize_factory_task_kind_rejects_unknown_task():
    with pytest.raises(ValueError, match="unsupported factory draft task"):
        normalize_factory_task_kind("runtime_answering")


def test_build_factory_backend_uses_stub_when_hosted_factory_is_disabled():
    backend = build_factory_backend(_factory_config())

    assert isinstance(backend, StubFactoryBackend)


def test_build_factory_backend_uses_hosted_provider_when_enabled():
    backend = build_factory_backend(
        _factory_config(
            factory_hosted_provider="openai_compatible",
            factory_hosted_base_url="https://factory.example/v1",
            factory_hosted_model="factory-gpt",
            factory_hosted_api_key="factory-secret",
        )
    )

    assert isinstance(backend, OpenAICompatibleFactoryBackend)


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
    assert payload["lifecycle_state"] == "review_needed"
    assert payload["eval_trace"]["lifecycle_state"] == "review_needed"
    assert payload["eval_trace"]["evidence_fidelity"] == "draft_only"
    assert payload["trust_boundary_provenance"]["policy_name"] == "factory-draft-local-only"
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


def test_run_factory_draft_uses_hosted_adapter_with_factory_trust_boundary_preflight(tmp_path: Path):
    source_path = tmp_path / "vendor-note.md"
    source_path.write_text(
        "# FastDedup\n\nUse /Users/zhuge/Documents/private/path.txt alice@example.com token=super-secret\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "drafts" / "candidate-draft.json"
    adapter = FakeHostedFactoryAdapter()

    result = run_factory_draft(
        task_kind="candidate_draft",
        source_refs=[source_path],
        output_path=output_path,
        vendor_id="sentieon",
        instruction="Draft candidate review notes from this source.",
        adapter="hosted",
        adapter_impl=adapter,
    )

    assert result.review_status == "needs_review"
    assert result.adapter_id == "hosted"
    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    assert str(source_path.resolve()) not in str(call["prompt"])
    assert source_path.name in str(call["prompt"])
    assert "alice@example.com" not in str(call["prompt"])
    assert "super-secret" not in str(call["prompt"])
    hosted_source = call["source_references"][0]
    assert hosted_source["label"] == source_path.name
    assert hosted_source["file_type"] == "markdown"
    assert "path" not in hosted_source
    assert "alice@example.com" not in str(hosted_source["preview"])
    assert "super-secret" not in str(hosted_source["preview"])
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["review_status"] == "needs_review"
    assert payload["review_required"] is True
    assert payload["lifecycle_state"] == "review_needed"
    assert payload["activation_eligibility"]["eligible"] is False
    assert payload["adapter"]["provider"] == "openai_compatible"
    assert payload["draft_payload"]["adapter_notes"]["execution_mode"] == "hosted-review-only"
    assert payload["trust_boundary_provenance"]["policy_name"] == "factory-hosted-draft-outbound-v1"
    assert payload["trust_boundary_provenance"]["local_only_count"] == 1
    assert payload["trust_boundary_provenance"]["redacted_count"] == 1
    assert payload["source_references"][0]["path"] == str(source_path.resolve())


def test_run_factory_draft_marks_hosted_learning_pilot_artifact_without_changing_artifact_class(tmp_path: Path):
    source_path = tmp_path / "hosted-learning-source.md"
    source_path.write_text("# Incident\n\nDraft hosted-learning review notes.\n", encoding="utf-8")
    output_path = tmp_path / "drafts" / "hosted-learning.json"
    adapter = FakeHostedFactoryAdapter()

    result = run_factory_draft(
        task_kind="incident_normalization",
        source_refs=[source_path],
        output_path=output_path,
        vendor_id="sentieon",
        instruction="Draft hosted-learning review notes from this source.",
        adapter="hosted",
        adapter_impl=adapter,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result.review_status == "needs_review"
    assert payload["artifact_class"] == "factory_model_draft"
    assert payload["learning_pilot"]["track"] == "hosted_learning"
    assert payload["learning_pilot"]["task_kind"] == "incident_normalization"
    assert payload["learning_pilot"]["adapter_id"] == "hosted"
    assert payload["learning_pilot"]["adapter_provider"] == "openai_compatible"
    assert payload["learning_pilot"]["review_only"] is True
    assert payload["learning_pilot"]["status"] == "review_needed"


def test_run_factory_draft_marks_stub_drafts_as_stub_draft_pilot(tmp_path: Path):
    source_path = tmp_path / "stub-source.md"
    source_path.write_text("# Dataset\n\nDraft stub review notes.\n", encoding="utf-8")
    output_path = tmp_path / "drafts" / "stub-learning.json"

    result = run_factory_draft(
        task_kind="dataset_draft",
        source_refs=[source_path],
        output_path=output_path,
        vendor_id="sentieon",
        instruction="Draft stub review notes from this source.",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result.review_status == "needs_review"
    assert payload["artifact_class"] == "factory_model_draft"
    assert payload["learning_pilot"]["track"] == "stub_draft"
    assert payload["learning_pilot"]["task_kind"] == "dataset_draft"
    assert payload["learning_pilot"]["adapter_provider"] == "local-stub"
    assert payload["learning_pilot"]["adapter_id"] == "stub"
    assert payload["learning_pilot"]["review_only"] is True


def test_run_factory_draft_can_attach_artifact_to_build_review_flow(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_dir = build_root / "20260413T010203Z-build1234"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "report.md").write_text("# Knowledge Build Report\n", encoding="utf-8")
    source_path = tmp_path / "incident-note.md"
    source_path.write_text("# Incident\n\nNormalize this incident for review.\n", encoding="utf-8")

    result = run_factory_draft(
        task_kind="incident_normalization",
        source_refs=[source_path],
        build_root=build_root,
        build_id=build_dir.name,
    )

    assert result.output_path.parent == build_dir / "factory-drafts"
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["build_id"] == build_dir.name
    assert payload["review_guidance"]["queue_bucket_id"] == "pending-factory-draft-review"
    assert payload["review_guidance"]["recommended_command"].startswith(
        "sengent knowledge review-factory-draft"
    )


def test_review_factory_drafts_exposes_eval_trace_for_lifecycle_review(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_dir = build_root / "20260413T010203Z-build1234"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "report.md").write_text("# Knowledge Build Report\n", encoding="utf-8")
    source_path = tmp_path / "vendor-note.md"
    source_path.write_text("# FastDedup\n\nUse FastDedup before alignment.\n", encoding="utf-8")

    result = run_factory_draft(
        task_kind="candidate_draft",
        source_refs=[source_path],
        build_root=build_root,
        build_id=build_dir.name,
    )

    review = review_factory_drafts(build_root=build_root, build_id=build_dir.name)

    assert review.drafts[0].artifact_path == result.output_path
    assert review.drafts[0].eval_trace["lifecycle_state"] == "review_needed"
    assert review.drafts[0].eval_trace["trust_boundary_policy_name"] == "factory-draft-local-only"
