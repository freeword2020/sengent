from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentieon_assist.kernel.pack_contract import PackManifestEntry, assert_required_pack_completeness


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

    def __post_init__(self) -> None:
        assert_required_pack_completeness(self.pack_manifest)
