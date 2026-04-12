from __future__ import annotations

from pathlib import Path

from sentieon_assist.kernel.pack_runtime import (
    pack_path_for_kind,
    required_pack_status,
    resolve_pack_entry,
)


def test_resolve_pack_entry_uses_vendor_profile_metadata():
    resolved = resolve_pack_entry("sentieon", "incident-memory")

    assert resolved.vendor_id == "sentieon"
    assert resolved.logical_kind == "incident-memory"
    assert resolved.file_name == "incident-memory.json"
    assert resolved.required is True
    assert resolved.entry_schema_version == "2.0"
    assert resolved.load_order == 60


def test_required_pack_status_uses_logical_kinds_against_disk(tmp_path: Path):
    for file_name in (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (tmp_path / file_name).write_text("{}", encoding="utf-8")

    status = required_pack_status(tmp_path, "sentieon")

    assert tuple(item.logical_kind for item in status) == (
        "vendor-reference",
        "vendor-decision",
        "domain-standard",
        "playbook",
        "troubleshooting",
        "incident-memory",
    )
    assert tuple(item.file_name for item in status) == (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    )
    assert all(item.exists for item in status)

    (tmp_path / "incident-memory.json").unlink()
    status = required_pack_status(tmp_path, "sentieon")

    assert [item.logical_kind for item in status if not item.exists] == ["incident-memory"]
    assert pack_path_for_kind(tmp_path, "sentieon", "incident-memory") == tmp_path / "incident-memory.json"


def test_required_pack_status_marks_malformed_required_pack_invalid(tmp_path: Path):
    for file_name in (
        "sentieon-modules.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (tmp_path / file_name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (tmp_path / "workflow-guides.json").write_text('{"version": ""}\n', encoding="utf-8")

    status = required_pack_status(tmp_path, "sentieon")
    workflow_status = next(item for item in status if item.logical_kind == "vendor-decision")

    assert workflow_status.exists is True
    assert workflow_status.valid is False
    assert workflow_status.error == "entries-list-required"


def test_required_pack_status_marks_non_utf8_pack_invalid(tmp_path: Path):
    for file_name in (
        "sentieon-modules.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (tmp_path / file_name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (tmp_path / "workflow-guides.json").write_bytes(b"\xff\xfe\x00\x00")

    status = required_pack_status(tmp_path, "sentieon")
    workflow_status = next(item for item in status if item.logical_kind == "vendor-decision")

    assert workflow_status.valid is False
    assert workflow_status.error == "invalid-json"


def test_required_pack_status_marks_missing_version_or_invalid_entries_invalid(tmp_path: Path):
    valid_payload = '{"version":"","entries":[]}\n'
    for file_name in (
        "sentieon-modules.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (tmp_path / file_name).write_text(valid_payload, encoding="utf-8")

    (tmp_path / "workflow-guides.json").write_text('{"entries":[{"id":"wes-qc"}]}\n', encoding="utf-8")
    status = required_pack_status(tmp_path, "sentieon")
    workflow_status = next(item for item in status if item.logical_kind == "vendor-decision")
    assert workflow_status.valid is False
    assert workflow_status.error == "version-string-required"

    (tmp_path / "workflow-guides.json").write_text('{"version":"","entries":["bad-entry"]}\n', encoding="utf-8")
    status = required_pack_status(tmp_path, "sentieon")
    workflow_status = next(item for item in status if item.logical_kind == "vendor-decision")
    assert workflow_status.valid is False
    assert workflow_status.error == "entries-dict-items-required"
