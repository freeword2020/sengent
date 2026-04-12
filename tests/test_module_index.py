from types import SimpleNamespace

from sentieon_assist.module_index import (
    build_module_evidence,
    build_parameter_evidence,
    match_module_entries,
)


def test_match_module_entries_uses_vendor_reference_pack_resolution(monkeypatch, tmp_path):
    resolved_path = tmp_path / "vendor-reference-v2.json"
    resolved_path.write_text(
        '{"version":"","entries":[{"id":"dnascope","name":"DNAscope","summary":"short-read germline"}]}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sentieon_assist.module_index.pack_path_for_kind",
        lambda source_directory, vendor_id, logical_kind: resolved_path,
        raising=False,
    )

    matches = match_module_entries("DNAscope 是做什么的", tmp_path)

    assert matches
    assert matches[0]["name"] == "DNAscope"


def test_module_evidence_uses_resolved_vendor_reference_name(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.module_index.resolve_pack_entry",
        lambda vendor_id, logical_kind: SimpleNamespace(file_name="vendor-reference-v2.json"),
        raising=False,
    )

    evidence = build_module_evidence({"name": "DNAscope", "summary": "short-read germline"})

    assert evidence["name"] == "vendor-reference-v2.json"
    assert evidence["path"] == "vendor-reference-v2.json"


def test_parameter_evidence_uses_resolved_vendor_reference_name(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.module_index.resolve_pack_entry",
        lambda vendor_id, logical_kind: SimpleNamespace(file_name="vendor-reference-v2.json"),
        raising=False,
    )

    evidence = build_parameter_evidence(
        {"name": "DNAscope"},
        {"name": "--emit_mode", "summary": "controls output", "details": ["variant", "all"]},
    )

    assert evidence["name"] == "vendor-reference-v2.json"
    assert evidence["path"] == "vendor-reference-v2.json"
