import pytest

from sentieon_assist.kernel.pack_contract import (
    LOGICAL_PACK_KINDS,
    PackManifestEntry,
    assert_required_pack_completeness,
)


def test_logical_pack_kinds_cover_the_sengent_2_0_contract():
    assert LOGICAL_PACK_KINDS == (
        "vendor-reference",
        "vendor-decision",
        "domain-standard",
        "playbook",
        "troubleshooting",
        "incident-memory",
    )


def test_pack_manifest_entry_exposes_required_schema_fields():
    entry = PackManifestEntry(
        required=True,
        file_name="vendor-reference.json",
        entry_schema_version="2.0",
        load_order=10,
    )

    assert entry.required is True
    assert entry.file_name == "vendor-reference.json"
    assert entry.entry_schema_version == "2.0"
    assert entry.load_order == 10


def test_required_pack_completeness_helper_raises_when_any_required_kind_is_missing():
    manifest = {
        "vendor-reference": PackManifestEntry(
            required=True,
            file_name="vendor-reference.json",
            entry_schema_version="2.0",
            load_order=10,
        ),
        "vendor-decision": PackManifestEntry(
            required=True,
            file_name="vendor-decision.json",
            entry_schema_version="2.0",
            load_order=20,
        ),
        "domain-standard": PackManifestEntry(
            required=True,
            file_name="domain-standard.json",
            entry_schema_version="2.0",
            load_order=30,
        ),
        "playbook": PackManifestEntry(
            required=True,
            file_name="playbook.json",
            entry_schema_version="2.0",
            load_order=40,
        ),
        "troubleshooting": PackManifestEntry(
            required=True,
            file_name="troubleshooting.json",
            entry_schema_version="2.0",
            load_order=50,
        ),
    }

    with pytest.raises(ValueError, match="incident-memory"):
        assert_required_pack_completeness(manifest)
