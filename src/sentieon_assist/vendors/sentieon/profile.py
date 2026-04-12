from __future__ import annotations

from sentieon_assist.kernel.pack_contract import PackManifestEntry
from sentieon_assist.vendors.base import VendorProfile


SENTIEON_PROFILE = VendorProfile(
    vendor_id="sentieon",
    display_name="Sentieon",
    default_version="202503.03",
    supported_versions=("202503.03",),
    pack_manifest={
        "vendor-reference": PackManifestEntry(
            required=True,
            file_name="sentieon-modules.json",
            entry_schema_version="2.0",
            load_order=10,
        ),
        "vendor-decision": PackManifestEntry(
            required=True,
            file_name="workflow-guides.json",
            entry_schema_version="2.0",
            load_order=20,
        ),
        "domain-standard": PackManifestEntry(
            required=True,
            file_name="external-format-guides.json",
            entry_schema_version="2.0",
            load_order=30,
        ),
        "playbook": PackManifestEntry(
            required=True,
            file_name="external-tool-guides.json",
            entry_schema_version="2.0",
            load_order=40,
        ),
        "troubleshooting": PackManifestEntry(
            required=True,
            file_name="external-error-associations.json",
            entry_schema_version="2.0",
            load_order=50,
        ),
        "incident-memory": PackManifestEntry(
            required=True,
            file_name="sentieon-module-index.md",
            entry_schema_version="2.0",
            load_order=60,
        ),
    },
    domain_dependencies=(
        "VCF",
        "BAM",
        "CRAM",
        "FASTA",
        "BED",
        "sequence-dictionary",
    ),
    clarification_policy={
        "default_slots": ("vendor", "version", "workflow", "inputs", "error"),
        "max_rounds": 2,
    },
    support_boundaries=(
        "unsupported-version",
        "benchmarking",
        "roadmap",
        "deep-mechanism",
    ),
)
