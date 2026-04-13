from __future__ import annotations

import json
from pathlib import Path

import yaml

from sentieon_assist.dataset_export import export_reviewed_gap_dataset
from sentieon_assist.factory_model import run_factory_draft
from sentieon_assist.session_events import (
    SupportSessionRecord,
    append_session_record,
    append_turn_event,
    build_turn_event,
    session_log_path,
)
from sentieon_assist.trust_boundary import (
    OutboundContextDisposition,
    OutboundContextItem,
    TrustBoundaryDecision,
    build_trust_boundary_result,
)


class FakeHostedFactoryAdapter:
    adapter_id = "hosted"
    provider = "openai_compatible"
    model_name = "factory-gpt"

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "summary": f"hosted draft summary for {task_kind}",
            "draft_items": [],
            "review_hints": ["keep review required"],
            "adapter_notes": {"execution_mode": "hosted-review-only"},
        }


def _write_reviewed_gap_fixture(tmp_path: Path, *, include_trace: bool = True) -> tuple[Path, str, Path, Path, str, str]:
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_id = "20260413T120000Z-dataset"
    build_dir = build_root / build_id
    candidate_dir = build_dir / "candidate-packs"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "report.md").write_text("# Build report\n", encoding="utf-8")

    metadata_path = tmp_path / "inbox" / "license-gap.meta.yaml"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "pack_target": "incident-memory.json",
                "entry_type": "incident",
                "origin": "runtime-gap-capture",
                "id": "license-gap-001",
                "vendor_id": "sentieon",
                "vendor_version": "202503.03",
                "gap_type": "clarification_open",
                "user_question": "Which Sentieon version is deployed?",
                "missing_materials": ["Sentieon 版本"],
                "known_context": {"error": "license error"},
                "captured_at": "2026-04-13T00:00:00+00:00",
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    runtime_root = tmp_path / "runtime"
    session = SupportSessionRecord.new(
        repo_root=str(tmp_path),
        git_sha="abc123",
        source_directory="/tmp/source-packs",
        knowledge_directory="/tmp/knowledge",
        mode="interactive",
    )
    append_session_record(session, runtime_root=runtime_root)
    turn = build_turn_event(
        session_id=session.session_id,
        turn_index=1,
        raw_query="license 报错",
        effective_query="license 报错",
        reused_anchor=False,
        task="troubleshooting",
        issue_type="license",
        route_reason="issue_type:license",
        parsed_intent_intent="",
        parsed_intent_module="",
        response_text="【当前判断】\n- 现有信息还不足以给出确定性建议。\n\n【需要确认的信息】\n- Sentieon 版本",
        response_mode="clarify",
        state_before={"clarification_rounds": 0},
        state_after={"clarification_rounds": 1},
        support_intent="troubleshooting",
        fallback_mode="clarification_open",
        vendor_id="sentieon",
        vendor_version="202503.03",
        sources=["Sentieon202503.03.pdf"],
        boundary_tags=[],
        resolver_path=["troubleshooting_knowledge_gap"],
        gap_record={
            "vendor_id": "sentieon",
            "vendor_version": "202503.03",
            "intent": "troubleshooting",
            "gap_type": "clarification_open",
            "user_question": "Which Sentieon version is deployed?",
            "known_context": {"error": "license error"},
            "missing_materials": ["Sentieon 版本"],
            "captured_at": "2026-04-13T00:00:00+00:00",
        },
        trust_boundary_result=build_trust_boundary_result(
            TrustBoundaryDecision(
                policy_name="support-answer-outbound-v1",
                items=(
                    OutboundContextItem(
                        key="query",
                        value="license 报错 /Users/zhuge/Documents/codex/harness/private.txt alice@example.com token=super-secret",
                        disposition=OutboundContextDisposition.REDACTED,
                        provenance={
                            "source": "runtime",
                            "sanitized_value": "license 报错 [PATH] [EMAIL] token=[REDACTED]",
                        },
                    ),
                    OutboundContextItem(
                        key="session_secret",
                        value="super-secret",
                        disposition=OutboundContextDisposition.LOCAL_ONLY,
                        provenance={
                            "source": "runtime",
                            "path": "/Users/zhuge/Documents/codex/harness/private.txt",
                        },
                    ),
                ),
            )
        ),
    )
    if include_trace:
        append_turn_event(turn, runtime_root=runtime_root)

    (candidate_dir / "incident-memory.json").write_text(
        json.dumps(
            {
                "version": "",
                "entries": [
                    {
                        "id": "license-gap-001",
                        "vendor_id": "sentieon",
                        "vendor_version": "202503.03",
                        "gap_type": "clarification_open",
                        "user_question": "Which Sentieon version is deployed?",
                        "missing_materials": ["Sentieon 版本"],
                        "known_context": {"error": "license error"},
                        "captured_at": "2026-04-13T00:00:00+00:00",
                        "origin": "runtime-gap-capture",
                        "sources": ["license-gap.md"],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    (build_dir / "gap_intake_review.jsonl").write_text(
        json.dumps(
            {
                "build_id": build_id,
                "doc_id": "doc-gap-001",
                "relative_path": "license-gap.md",
                "metadata_path": str(metadata_path),
                "pack_target": "incident-memory.json",
                "entry_id": "license-gap-001",
                "session_id": session.session_id,
                "turn_id": turn.turn_id,
                "gap_type": "clarification_open",
                "vendor_version": "202503.03",
                "user_question": "Which Sentieon version is deployed?",
                "missing_materials": ["Sentieon 版本"],
                "known_context": {"error": "license error"},
                "captured_at": "2026-04-13T00:00:00+00:00",
                "review_status": "triaged",
                "review_decision": "seed_eval",
                "review_scope": "last",
                "review_notes": "Turn this into a boundary/support-behavior sample.",
                "expected_mode": "boundary",
                "expected_task": "troubleshooting",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (build_dir / "gap_eval_seed.jsonl").write_text(
        json.dumps(
            {
                "record_id": f"gap-eval.{build_id}.license-gap-001",
                "source": "gap-intake-review",
                "scope": "last",
                "session_id": session.session_id,
                "selected_turn_ids": [turn.turn_id],
                "expected_mode": "boundary",
                "expected_task": "troubleshooting",
                "scorable": True,
                "entry_id": "license-gap-001",
                "gap_type": "clarification_open",
                "build_id": build_id,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return build_root, build_id, runtime_root, metadata_path, session.session_id, turn.turn_id


def test_export_reviewed_gap_dataset_writes_audited_gap_support_sample(tmp_path: Path):
    build_root, build_id, runtime_root, metadata_path, session_id, turn_id = _write_reviewed_gap_fixture(tmp_path)
    output_path = tmp_path / "exports" / "reviewed-gap-dataset.jsonl"

    result = export_reviewed_gap_dataset(
        build_root=build_root,
        build_id=build_id,
        runtime_root=runtime_root,
        output_path=output_path,
    )

    assert result.build_id == build_id
    assert result.exported_count == 1
    assert result.skipped_count == 0
    lines = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    sample = lines[0]
    assert sample["sample_id"] == f"reviewed-gap-support.{build_id}.license-gap-001"
    assert sample["sample_type"] == "reviewed_gap_support_sample"
    assert sample["build_id"] == build_id
    assert sample["vendor_id"] == "sentieon"
    assert sample["vendor_version"] == "202503.03"
    assert sample["review_status"] == "triaged"
    assert sample["review_decision"] == "seed_eval"
    assert sample["review_scope"] == "last"
    assert sample["expected_answer_contract"] == {
        "expected_mode": "boundary",
        "expected_task": "troubleshooting",
    }
    assert sample["eval_trace"]["boundary_adherence"] == "clarify"
    assert sample["eval_trace"]["evidence_fidelity"] == "source_grounded"
    assert sample["support_trace"]["eval_trace_summary"]["turn_count"] == 1
    assert sample["support_trace"]["turns"][0]["eval_trace"]["boundary_adherence"] == "clarify"
    assert sample["incident"]["entry_id"] == "license-gap-001"
    assert sample["incident"]["origin"] == "runtime-gap-capture"
    assert sample["support_trace"]["session_id"] == session_id
    assert sample["support_trace"]["selected_turn_ids"] == [turn_id]
    assert sample["support_trace"]["turns"][0]["turn_id"] == turn_id
    assert sample["support_trace"]["turns"][0]["response_mode"] == "clarify"
    assert sample["support_trace"]["turns"][0]["trust_boundary_audit"][0]["key"] == "query"
    assert sample["support_trace"]["turns"][0]["trust_boundary_audit"][1]["disposition"] == "local_only"
    assert sample["support_trace"]["turns"][0]["eval_trace"]["trust_boundary_audit_present"] is True
    assert sample["support_trace"]["turns"][0]["eval_trace"]["trust_boundary_audit_posture"] == "mixed"
    assert sample["eval_trace"]["trust_boundary_audit_turn_count"] == 1
    assert sample["eval_trace"]["trust_boundary_audit_posture"] == "mixed"
    assert "super-secret" not in json.dumps(sample["support_trace"], ensure_ascii=False)
    assert "/Users/zhuge/Documents/codex/harness/private.txt" not in json.dumps(sample["support_trace"], ensure_ascii=False)
    assert str(metadata_path) in sample["source_artifacts"]


def test_export_reviewed_gap_dataset_includes_hosted_learning_provenance_from_attached_factory_draft(tmp_path: Path):
    build_root, build_id, runtime_root, metadata_path, session_id, turn_id = _write_reviewed_gap_fixture(tmp_path)
    source_path = tmp_path / "factory-learning-source.md"
    source_path.write_text("# Draft\n\nUse this for hosted-learning provenance.\n", encoding="utf-8")
    draft_result = run_factory_draft(
        task_kind="dataset_draft",
        source_refs=[source_path],
        build_root=build_root,
        build_id=build_id,
        adapter="hosted",
        adapter_impl=FakeHostedFactoryAdapter(),
    )
    output_path = tmp_path / "exports" / "reviewed-gap-dataset.jsonl"

    result = export_reviewed_gap_dataset(
        build_root=build_root,
        build_id=build_id,
        runtime_root=runtime_root,
        output_path=output_path,
    )

    assert result.exported_count == 1
    sample = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    assert sample["hosted_learning_provenance"]["learning_track"] == "hosted_learning"
    assert sample["hosted_learning_provenance"]["task_kind"] == "dataset_draft"
    assert sample["hosted_learning_provenance"]["adapter_provider"] == "openai_compatible"
    assert sample["hosted_learning_provenance"]["adapter_id"] == "hosted"
    assert sample["hosted_learning_provenance"]["review_status"] == "needs_review"
    assert draft_result.output_path.as_posix() in sample["source_artifacts"]
    assert sample["incident"]["entry_id"] == "license-gap-001"


def test_export_reviewed_gap_dataset_aggregates_multiple_hosted_learning_drafts(tmp_path: Path):
    build_root, build_id, runtime_root, _metadata_path, _session_id, _turn_id = _write_reviewed_gap_fixture(tmp_path)
    first_source = tmp_path / "factory-learning-source-1.md"
    second_source = tmp_path / "factory-learning-source-2.md"
    first_source.write_text("# Draft\n\nHosted learning 1.\n", encoding="utf-8")
    second_source.write_text("# Draft\n\nHosted learning 2.\n", encoding="utf-8")
    first_result = run_factory_draft(
        task_kind="dataset_draft",
        source_refs=[first_source],
        build_root=build_root,
        build_id=build_id,
        adapter="hosted",
        adapter_impl=FakeHostedFactoryAdapter(),
    )
    second_result = run_factory_draft(
        task_kind="candidate_draft",
        source_refs=[second_source],
        build_root=build_root,
        build_id=build_id,
        adapter="hosted",
        adapter_impl=FakeHostedFactoryAdapter(),
    )
    output_path = tmp_path / "exports" / "reviewed-gap-dataset.jsonl"

    result = export_reviewed_gap_dataset(
        build_root=build_root,
        build_id=build_id,
        runtime_root=runtime_root,
        output_path=output_path,
    )

    assert result.exported_count == 1
    sample = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    provenance = sample["hosted_learning_provenance"]
    assert provenance["draft_count"] == 2
    assert sorted(provenance["task_kinds"]) == ["candidate_draft", "dataset_draft"]
    assert provenance["learning_track"] == "hosted_learning"
    assert provenance["adapter_provider"] == "openai_compatible"
    assert len(provenance["artifact_paths"]) == 2
    assert first_result.output_path.as_posix() in sample["source_artifacts"]
    assert second_result.output_path.as_posix() in sample["source_artifacts"]


def test_export_reviewed_gap_dataset_resanitizes_legacy_audit_provenance(tmp_path: Path):
    build_root, build_id, runtime_root, _metadata_path, session_id, _turn_id = _write_reviewed_gap_fixture(tmp_path)
    output_path = tmp_path / "exports" / "reviewed-gap-dataset.jsonl"
    log_path = session_log_path(session_id, runtime_root=runtime_root)
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    turn_event = next(event for event in events if event.get("event_type") == "turn_resolved")
    turn_event["trust_boundary_audit"] = [
        {
            "key": "query",
            "disposition": "redacted",
            "provenance": {
                "source": "runtime",
                "path": "/Users/zhuge/Documents/codex/harness/private.txt",
                "contact": "alice@example.com",
                "payload": "token=super-secret",
            },
            "redaction_reason": "legacy-runtime-sanitizer",
        }
    ]
    log_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )

    result = export_reviewed_gap_dataset(
        build_root=build_root,
        build_id=build_id,
        runtime_root=runtime_root,
        output_path=output_path,
    )

    assert result.exported_count == 1
    sample = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
    audit_json = json.dumps(sample["support_trace"]["turns"][0]["trust_boundary_audit"], ensure_ascii=False)
    assert "alice@example.com" not in audit_json
    assert "/Users/zhuge/Documents/codex/harness/private.txt" not in audit_json
    assert "super-secret" not in audit_json
    assert "\"payload\"" not in audit_json
    assert "[EMAIL]" in audit_json
    assert "[PATH]" in audit_json


def test_export_reviewed_gap_dataset_skips_seed_when_selected_trace_is_missing(tmp_path: Path):
    build_root, build_id, runtime_root, _metadata_path, _session_id, _turn_id = _write_reviewed_gap_fixture(
        tmp_path,
        include_trace=False,
    )
    output_path = tmp_path / "exports" / "reviewed-gap-dataset.jsonl"

    result = export_reviewed_gap_dataset(
        build_root=build_root,
        build_id=build_id,
        runtime_root=runtime_root,
        output_path=output_path,
    )

    assert result.exported_count == 0
    assert result.skipped_count == 1
    assert output_path.read_text(encoding="utf-8") == ""
