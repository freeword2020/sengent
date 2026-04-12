from __future__ import annotations

from sentieon_assist.vendors.base import VendorProfile
from sentieon_assist.vendors.sentieon import SENTIEON_PROFILE


_VENDOR_REGISTRY: dict[str, VendorProfile] = {
    SENTIEON_PROFILE.vendor_id: SENTIEON_PROFILE,
}


def get_vendor_profile(vendor_id: str) -> VendorProfile:
    normalized_vendor_id = str(vendor_id).strip().lower()
    try:
        return _VENDOR_REGISTRY[normalized_vendor_id]
    except KeyError as exc:
        raise KeyError(f"unknown vendor profile: {vendor_id}") from exc


def available_vendor_profiles() -> tuple[VendorProfile, ...]:
    return tuple(_VENDOR_REGISTRY.values())


__all__ = ["VendorProfile", "available_vendor_profiles", "get_vendor_profile"]
