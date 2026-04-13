from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sentieon_assist.eval_trace_plane import project_runtime_eval_trace
from sentieon_assist.gap_review import build_gap_eval_seed_record
from sentieon_assist.gap_review import normalize_gap_maintainer_review
from sentieon_assist.gap_review import aggregate_gap_review_eval_alignments
from sentieon_assist.gap_review import project_gap_review_eval_alignment
from sentieon_assist.gap_review import update_gap_review_metadata


def _write_gap_metadata(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "pack_target": "incident-memory.json",
                "entry_type": "incident",
                "action": "upsert",
                "origin": "runtime-gap-capture",
                "id": "gap-license-001",
                "name": "Gap intake for clarification_open",
                "session_id": "session-001",
                "turn_id": "turn-001",
                "turn_index": 1,
                "gap_type": "clarification_open",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
                "user_question": "license 报错",
                "known_context": {"error": "license"},
                "missing_materials": ["Sentieon version"],
                "captured_at": "2026-04-13T00:00:00+00:00",
                "version": "202503.03",
                "date": "2026-04-13",
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def test_normalize_gap_maintainer_review_defaults_to_pending_state():
    assert normalize_gap_maintainer_review(None) == {
        "status": "pending",
        "decision": "pending",
        "scope": "last",
        "expected_mode": "",
        "expected_task": "",
        "notes": "",
    }


def test_normalize_gap_maintainer_review_preserves_hosted_learning_provenance():
    review = normalize_gap_maintainer_review(
        {
            "status": "triaged",
            "decision": "seed_eval",
            "scope": "last",
            "expected_mode": "boundary",
            "expected_task": "troubleshooting",
            "hosted_learning_provenance": {
                "draft_id": "factory-draft.dataset.001",
                "task_kind": "dataset_draft",
                "learning_track": "hosted_learning",
                "adapter_id": "hosted",
                "adapter_provider": "openai_compatible",
                "adapter_model_name": "factory-gpt",
            },
        }
    )

    assert review["hosted_learning_provenance"]["draft_id"] == "factory-draft.dataset.001"
    assert review["hosted_learning_provenance"]["adapter_provider"] == "openai_compatible"


def test_update_gap_review_metadata_writes_seed_eval_review_block_without_touching_gap_fields(tmp_path: Path):
    metadata_path = tmp_path / "gap-license.meta.yaml"
    _write_gap_metadata(metadata_path)

    updated = update_gap_review_metadata(
        metadata_path,
        status="triaged",
        decision="seed_eval",
        expected_mode="boundary",
        expected_task="troubleshooting",
        scope="last",
        note="Need a boundary regression case before gate.",
    )

    payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert payload["id"] == "gap-license-001"
    assert payload["gap_type"] == "clarification_open"
    assert payload["maintainer_review"] == {
        "status": "triaged",
        "decision": "seed_eval",
        "scope": "last",
        "expected_mode": "boundary",
        "expected_task": "troubleshooting",
        "notes": "Need a boundary regression case before gate.",
    }
    assert updated["maintainer_review"]["decision"] == "seed_eval"


def test_update_gap_review_metadata_rejects_seed_eval_without_expectations(tmp_path: Path):
    metadata_path = tmp_path / "gap-license.meta.yaml"
    _write_gap_metadata(metadata_path)

    with pytest.raises(ValueError, match="expected_mode"):
        update_gap_review_metadata(
            metadata_path,
            status="triaged",
            decision="seed_eval",
            expected_mode="",
            expected_task="troubleshooting",
            scope="last",
            note="missing expected mode",
        )


def test_update_gap_review_metadata_preserves_existing_hosted_learning_provenance(tmp_path: Path):
    metadata_path = tmp_path / "gap-license.meta.yaml"
    _write_gap_metadata(metadata_path)
    payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    payload["maintainer_review"] = {
        "status": "triaged",
        "decision": "seed_eval",
        "scope": "last",
        "expected_mode": "boundary",
        "expected_task": "troubleshooting",
        "notes": "Existing review context.",
        "hosted_learning_provenance": {
            "draft_id": "factory-draft.dataset.001",
            "task_kind": "dataset_draft",
            "learning_track": "hosted_learning",
            "adapter_id": "hosted",
            "adapter_provider": "openai_compatible",
            "adapter_model_name": "factory-gpt",
        },
    }
    metadata_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    updated = update_gap_review_metadata(
        metadata_path,
        status="triaged",
        decision="seed_eval",
        expected_mode="boundary",
        expected_task="troubleshooting",
        scope="last",
        note="Need a boundary regression case before gate.",
    )

    assert updated["maintainer_review"]["hosted_learning_provenance"]["draft_id"] == "factory-draft.dataset.001"
    assert updated["maintainer_review"]["hosted_learning_provenance"]["adapter_provider"] == "openai_compatible"


def test_project_gap_review_eval_alignment_marks_expected_review_and_eval_contract_as_aligned():
    review = {
        "entry_id": "gap-license-001",
        "review_status": "triaged",
        "review_decision": "seed_eval",
        "review_scope": "last",
        "expected_mode": "boundary",
        "expected_task": "troubleshooting",
    }
    eval_projection = project_runtime_eval_trace(
        {
            "planner": {
                "support_intent": "troubleshooting",
                "fallback_mode": "clarification_open",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
            },
            "answer": {
                "response_mode": "boundary",
                "sources": ["Sentieon202503.03.pdf"],
                "boundary_tags": [],
                "resolver_path": ["troubleshooting_knowledge_gap"],
                "gap_record": {"gap_type": "clarification_open"},
            },
            "trust_boundary_audit": [
                {
                    "key": "query",
                    "disposition": "redacted",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
                {
                    "key": "session_secret",
                    "disposition": "local_only",
                    "provenance": {"source": "runtime"},
                    "redaction_reason": "runtime-sanitizer",
                },
            ],
        }
    )

    alignment = project_gap_review_eval_alignment(review, eval_projection)

    assert alignment["entry_id"] == "gap-license-001"
    assert alignment["alignment_state"] == "aligned"
    assert alignment["expected_mode_matches"] is True
    assert alignment["expected_task_matches"] is True
    assert alignment["boundary_adherence"] == "clarify"
    assert alignment["evidence_fidelity"] == "source_grounded"
    assert alignment["trust_boundary_audit_present"] is True
    assert alignment["trust_boundary_audit_posture"] == "provenance_only"


def test_aggregate_gap_review_eval_alignments_counts_mixed_alignment_states():
    aligned = project_gap_review_eval_alignment(
        {
            "entry_id": "gap-license-001",
            "review_status": "triaged",
            "review_decision": "seed_eval",
            "review_scope": "last",
            "expected_mode": "boundary",
            "expected_task": "troubleshooting",
        },
        {
            "response_mode": "boundary",
            "support_intent": "troubleshooting",
            "boundary_adherence": "boundary",
            "evidence_fidelity": "source_grounded",
        },
    )
    mismatched = project_gap_review_eval_alignment(
        {
            "entry_id": "gap-license-002",
            "review_status": "triaged",
            "review_decision": "seed_eval",
            "review_scope": "last",
            "expected_mode": "clarify",
            "expected_task": "troubleshooting",
        },
        {
            "response_mode": "boundary",
            "support_intent": "reference_lookup",
            "boundary_adherence": "must_tool",
            "evidence_fidelity": "contract_only",
        },
    )

    summary = aggregate_gap_review_eval_alignments([aligned, mismatched])

    assert summary["alignment_state"] == "mixed"
    assert summary["aligned_count"] == 1
    assert summary["mismatched_count"] == 1


def test_build_gap_eval_seed_record_carries_hosted_learning_provenance_into_eval_alignment():
    review = normalize_gap_maintainer_review(
        {
            "status": "triaged",
            "decision": "seed_eval",
            "scope": "last",
            "expected_mode": "boundary",
            "expected_task": "troubleshooting",
            "hosted_learning_provenance": {
                "draft_id": "factory-draft.dataset.001",
                "task_kind": "dataset_draft",
                "learning_track": "hosted_learning",
                "adapter_id": "hosted",
                "adapter_provider": "openai_compatible",
                "adapter_model_name": "factory-gpt",
            },
        }
    )

    seed = build_gap_eval_seed_record(
        build_id="build-001",
        entry_id="gap-license-001",
        gap_type="clarification_open",
        session_id="session-001",
        turn_id="turn-001",
        review=review,
    )

    assert seed is not None
    assert seed["eval_alignment"]["hosted_learning_provenance_present"] is True
    assert seed["eval_alignment"]["hosted_learning_provenance"]["learning_track"] == "hosted_learning"
    assert seed["eval_alignment"]["hosted_learning_provenance"]["task_kind"] == "dataset_draft"
    assert seed["eval_alignment"]["hosted_learning_provenance"]["adapter_provider"] == "openai_compatible"
