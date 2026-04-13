from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentieon_assist.kernel.pack_contract import PackManifestEntry, assert_required_pack_completeness


@dataclass(frozen=True)
class VendorRuntimeWording:
    field_labels: dict[str, str]
    capability_summary_lines: tuple[str, ...]
    capability_example_queries: tuple[str, ...]
    official_material_terms: tuple[str, ...]

    @property
    def requirement_field_aliases(self) -> dict[str, str]:
        return {label: field for field, label in self.field_labels.items() if str(label).strip()}

    def field_label(self, field_name: str) -> str:
        return self.field_labels.get(field_name, field_name)

    def official_material_request(self, display_name: str, version_hint: str = "") -> str:
        terms = " / ".join(str(term).strip() for term in self.official_material_terms if str(term).strip()) or "官方资料"
        resolved_version = str(version_hint).strip()
        if resolved_version:
            return f"{display_name} {resolved_version} 对应的 {terms}"
        return f"{display_name} 对应版本的 {terms}"


@dataclass(frozen=True)
class VendorProfile:
    vendor_id: str
    display_name: str
    default_version: str
    supported_versions: tuple[str, ...]
    pack_manifest: dict[str, PackManifestEntry]
    domain_dependencies: tuple[str, ...]
    clarification_policy: dict[str, Any]
    support_boundaries: tuple[str, ...]
    runtime_wording: VendorRuntimeWording

    def __post_init__(self) -> None:
        assert_required_pack_completeness(self.pack_manifest)
