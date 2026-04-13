from __future__ import annotations

from sentieon_assist.vendors import get_vendor_profile, resolve_vendor_id

ISSUE_TYPE_LABELS = {
    "license": "许可证问题",
    "install": "安装问题",
    "reference": "资料查询",
    "other": "其他问题",
}


def event_detect_issue_type(issue_type: str) -> str:
    label = ISSUE_TYPE_LABELS.get(issue_type, issue_type)
    return f"已识别问题类型：{label}"


def _field_labels(vendor_id: str | None = None) -> dict[str, str]:
    resolved_vendor_id = resolve_vendor_id(vendor_id)
    profile = get_vendor_profile(resolved_vendor_id)
    return dict(profile.runtime_wording.field_labels)


def event_check_missing_info(missing_fields: list[str], *, vendor_id: str | None = None) -> str:
    if not missing_fields:
        return "已检查必要信息"
    field_labels = _field_labels(vendor_id)
    labels = [field_labels.get(field, field) for field in missing_fields]
    return f"发现需要补充的信息：{', '.join(labels)}"


def event_search_sources() -> str:
    return "正在检索本地资料"


def event_prepare_reference_answer() -> str:
    return "正在整理参考答案"


def event_generate_reply() -> str:
    return "正在生成回复"
