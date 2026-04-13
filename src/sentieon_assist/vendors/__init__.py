from __future__ import annotations

from sentieon_assist.vendors.base import VendorProfile
from sentieon_assist.vendors.sentieon import SENTIEON_PROFILE


_VENDOR_REGISTRY: dict[str, VendorProfile] = {
    SENTIEON_PROFILE.vendor_id: SENTIEON_PROFILE,
}
DEFAULT_VENDOR_ID = SENTIEON_PROFILE.vendor_id


def resolve_vendor_id(vendor_id: str | None) -> str:
    normalized_vendor_id = str(vendor_id or "").strip().lower() or DEFAULT_VENDOR_ID
    get_vendor_profile(normalized_vendor_id)
    return normalized_vendor_id


def default_vendor_profile() -> VendorProfile:
    return get_vendor_profile(DEFAULT_VENDOR_ID)


def get_vendor_profile(vendor_id: str) -> VendorProfile:
    normalized_vendor_id = str(vendor_id).strip().lower()
    try:
        return _VENDOR_REGISTRY[normalized_vendor_id]
    except KeyError as exc:
        raise KeyError(f"unknown vendor profile: {vendor_id}") from exc


def available_vendor_profiles() -> tuple[VendorProfile, ...]:
    return tuple(_VENDOR_REGISTRY.values())


__all__ = [
    "DEFAULT_VENDOR_ID",
    "VendorProfile",
    "available_vendor_profiles",
    "default_vendor_profile",
    "get_vendor_profile",
    "resolve_vendor_id",
]
