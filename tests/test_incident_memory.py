from sentieon_assist.incident_memory import list_incident_entries


def test_list_incident_entries_uses_incident_memory_pack_resolution(monkeypatch, tmp_path):
    resolved_path = tmp_path / "incident-memory-v2.json"
    resolved_path.write_text(
        '{"version":"","entries":[{"id":"vcf-header-mismatch","summary":"header mismatch"}]}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sentieon_assist.incident_memory.pack_path_for_kind",
        lambda source_directory, vendor_id, logical_kind: resolved_path,
        raising=False,
    )

    entries = list_incident_entries(tmp_path)

    assert [entry["id"] for entry in entries] == ["vcf-header-mismatch"]
