from sentieon_assist.vendors import get_vendor_profile


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
