import pytest

from sentieon_assist.vendors import DEFAULT_VENDOR_ID, default_vendor_profile, get_vendor_profile, resolve_vendor_id


def test_sentieon_profile_exposes_minimum_vendor_contract():
    profile = get_vendor_profile("sentieon")

    assert profile.vendor_id == "sentieon"
    assert profile.display_name
    assert profile.default_version
    assert profile.supported_versions
    assert profile.pack_manifest
    assert profile.domain_dependencies
    assert profile.clarification_policy
    assert profile.support_boundaries
    assert "vendor-reference" in profile.pack_manifest


def test_sentieon_profile_pack_manifest_entries_include_required_schema_fields():
    profile = get_vendor_profile("sentieon")

    for logical_kind in (
        "vendor-reference",
        "vendor-decision",
        "domain-standard",
        "playbook",
        "troubleshooting",
        "incident-memory",
    ):
        entry = profile.pack_manifest[logical_kind]
        assert entry.required is True
        assert entry.file_name
        assert entry.entry_schema_version
        assert entry.load_order is not None


def test_sentieon_profile_maps_incident_memory_to_runtime_json_pack():
    profile = get_vendor_profile("sentieon")

    assert profile.pack_manifest["incident-memory"].file_name == "incident-memory.json"


def test_resolve_vendor_id_defaults_to_sentieon():
    assert DEFAULT_VENDOR_ID == "sentieon"
    assert resolve_vendor_id(None) == "sentieon"
    assert resolve_vendor_id(" Sentieon ") == "sentieon"
    assert default_vendor_profile().vendor_id == "sentieon"


def test_resolve_vendor_id_rejects_unknown_vendor():
    with pytest.raises(KeyError, match="unknown vendor profile"):
        resolve_vendor_id("unknown-vendor")


def test_sentieon_profile_runtime_wording_contract():
    profile = get_vendor_profile("sentieon")

    wording = profile.runtime_wording

    assert wording.field_labels["version"] == "Sentieon 版本"
    assert wording.field_labels["error"] == "完整报错信息"
    assert wording.capability_summary_lines
    assert wording.capability_example_queries
    assert wording.official_material_terms == ("manual", "release notes", "app note")
