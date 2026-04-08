from __future__ import annotations


def next_state(current_state: str, has_missing_info: bool) -> str:
    if current_state == "CLASSIFIED":
        return "EXTRACTED"
    if current_state == "EXTRACTED":
        return "NEED_INFO" if has_missing_info else "READY"
    if current_state == "READY":
        return "ANSWERED"
    if current_state == "NEED_INFO":
        return "NEED_INFO"
    raise ValueError(f"unsupported state: {current_state}")
