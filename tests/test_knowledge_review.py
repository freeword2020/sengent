from __future__ import annotations

import json
from pathlib import Path

from sentieon_assist.knowledge_review import build_maintainer_queue
from sentieon_assist.knowledge_review import format_maintainer_queue


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_queue_build(build_root: Path, build_id: str = "20260413T010203Z-queue1234") -> Path:
    build_dir = build_root / build_id
    candidate_dir = build_dir / "candidate-packs"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "report.md").write_text("# Knowledge Build Report\n", encoding="utf-8")
    (candidate_dir / "manifest.json").write_text(
        json.dumps(
            {
                "compile_skips": [
                    {"relative_path": "fastdedup-source.md", "reason": "factory intake pending review"},
                ],
                "pack_diffs": {
                    "sentieon-modules.json": {
                        "unchanged": False,
                        "added_ids": [],
                        "removed_ids": [],
                        "updated_ids": ["fastdedup"],
                    },
                    "workflow-guides.json": {
                        "unchanged": True,
                        "added_ids": [],
                        "removed_ids": [],
                        "updated_ids": [],
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_jsonl(
        build_dir / "parameter_review_suggestion.jsonl",
        [
            {
                "build_id": build_id,
                "relative_path": "fastdedup.md",
                "module_id": "fastdedup",
                "parameter_name": "--threads",
                "suggested_action": "review_parameter_candidate",
                "template": {"name": "--threads"},
                "detail": "Found a high-confidence parameter candidate.",
            }
        ],
    )
    _write_jsonl(
        build_dir / "gap_intake_review.jsonl",
        [
            {
                "build_id": build_id,
                "relative_path": "incident-gap.md",
                "metadata_path": str(build_dir / "incident-gap.meta.yaml"),
                "pack_target": "incident-memory.json",
                "entry_id": "license-gap-001",
                "session_id": "session-gap-001",
                "turn_id": "turn-gap-001",
                "gap_type": "clarification_open",
                "vendor_version": "202503.03",
                "user_question": "Which Sentieon version is deployed?",
                "missing_materials": ["Sentieon 202503.03"],
                "known_context": {"query_version": "202503.03"},
                "captured_at": "2026-04-13T00:00:00+00:00",
                "review_status": "pending",
                "review_decision": "pending",
                "review_scope": "last",
                "review_notes": "",
                "expected_mode": "",
                "expected_task": "",
            }
        ],
    )
    _write_jsonl(
        build_dir / "gap_eval_seed.jsonl",
        [
            {
                "record_id": "gap-eval.1",
                "source": "gap-intake-review",
                "scope": "last",
                "session_id": "session-gap-001",
                "selected_turn_ids": ["turn-gap-001"],
                "expected_mode": "boundary",
                "expected_task": "troubleshooting",
                "scorable": True,
                "entry_id": "license-gap-001",
                "gap_type": "clarification_open",
                "build_id": build_id,
            }
        ],
    )
    return build_dir


def test_build_maintainer_queue_aggregates_pending_buckets(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_dir = _write_queue_build(build_root)

    result = build_maintainer_queue(build_root=build_root, build_id=build_dir.name)

    assert result.build_id == build_dir.name
    assert result.total_items == 5
    bucket_ids = [bucket.bucket_id for bucket in result.buckets]
    assert bucket_ids == [
        "pending-gap-triage",
        "pending-source-review",
        "pending-parameter-review",
        "pending-gate-input",
        "candidate-pack-change",
    ]
    assert result.buckets[0].recommended_command.startswith("sengent knowledge triage-gap")
    assert result.buckets[1].artifact_path.endswith("candidate-packs/manifest.json")
    assert result.buckets[3].recommended_command.startswith("python scripts/pilot_closed_loop.py")


def test_format_maintainer_queue_outputs_actionable_sections(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_dir = _write_queue_build(build_root)

    result = build_maintainer_queue(build_root=build_root, build_id=build_dir.name)
    text = format_maintainer_queue(result)

    assert build_dir.name in text
    assert "Pending Gap Triage" in text
    assert "Pending Source Review" in text
    assert "Pending Parameter Review" in text
    assert "Pending Gate Input" in text
    assert "Candidate Pack Change" in text
    assert "Next action:" in text
    assert "Recommended command:" in text


def test_build_maintainer_queue_uses_latest_build_and_ignores_activation_backups(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    _write_queue_build(build_root, build_id="20260413T000100Z-older111")
    latest_dir = _write_queue_build(build_root, build_id="20260413T000200Z-latest222")
    backup_dir = build_root / "activation-backups" / "20260413T000300000000Z-backup333"
    backup_dir.mkdir(parents=True)
    (backup_dir / "report.md").write_text("# Backup Report\n", encoding="utf-8")

    result = build_maintainer_queue(build_root=build_root)

    assert result.build_id == latest_dir.name
