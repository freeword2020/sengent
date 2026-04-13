from __future__ import annotations

from sentieon_assist.vendors import get_vendor_profile


def _bullet_list(items: list[str], *, empty: str = "- 无") -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return empty
    return "\n".join(f"- {item}" for item in cleaned)


def _official_material_request(vendor_id: str, *, version_hint: str = "") -> str:
    profile = get_vendor_profile(vendor_id)
    terms = " / ".join(
        str(term).strip() for term in profile.runtime_wording.official_material_terms if str(term).strip()
    ) or "官方资料"
    resolved_version = str(version_hint).strip()
    if resolved_version:
        return f"{profile.display_name} {resolved_version} 对应的 {terms}"
    return f"{profile.display_name} 对应版本的 {terms}"


def format_boundary_contract(
    *,
    summary_lines: list[str],
    next_steps: list[str],
    needed_materials: list[str],
) -> str:
    return (
        "【资料边界】\n"
        f"{_bullet_list(summary_lines)}\n\n"
        "【建议下一步】\n"
        f"{_bullet_list(next_steps)}\n\n"
        "【需要补充的材料】\n"
        f"{_bullet_list(needed_materials)}"
    )


def format_knowledge_gap_answer(
    missing_labels: list[str],
    *,
    vendor_id: str = "sentieon",
    vendor_version: str = "",
) -> str:
    profile = get_vendor_profile(vendor_id)
    headline = f"需要补充以下信息：{', '.join(missing_labels)}"
    context_line = f"当前按 {profile.display_name} {vendor_version} 资料上下文处理。" if vendor_version else ""
    summary_lines = [
        "现有信息还不足以给出确定性建议。",
        context_line,
    ]
    next_steps = [
        "请直接补充上面列出的关键信息后再继续。",
        "如果方便，也可以同时补充原始命令、完整报错和输入文件类型。",
    ]
    return (
        f"{headline}\n\n"
        "【当前判断】\n"
        f"{_bullet_list(summary_lines)}\n\n"
        "【需要确认的信息】\n"
        f"{_bullet_list(missing_labels)}\n\n"
        "【建议下一步】\n"
        f"{_bullet_list(next_steps)}"
    )


def format_unsupported_version_boundary(
    *,
    vendor_id: str,
    requested_version: str,
) -> str:
    profile = get_vendor_profile(vendor_id)
    supported_versions = [str(item).strip() for item in profile.supported_versions if str(item).strip()]
    supported_text = "、".join(supported_versions) or "当前激活资料版本"
    return format_boundary_contract(
        summary_lines=[
            f"当前请求版本: {requested_version or '未明确提供'}",
            f"当前已激活支持版本: {supported_text}",
            f"当前本地结构化资料没有覆盖 {profile.display_name} {requested_version or '该版本'}，不能直接给出确定性建议。",
        ],
        next_steps=[
            "如果你必须处理这个版本，请先导入并激活对应版本的官方资料后再继续。",
            "如果问题允许按当前资料主版本保守参考，请先明确是否接受版本差异带来的偏差。",
        ],
        needed_materials=[
            _official_material_request(vendor_id, version_hint=requested_version or "目标版本"),
            "复现场景中的原始命令、完整报错和输入文件类型",
        ],
    )


def format_no_answer_boundary(
    *,
    vendor_id: str,
    vendor_version: str,
    missing_labels: list[str],
    reason: str,
) -> str:
    profile = get_vendor_profile(vendor_id)
    context_line = f"当前上下文: {profile.display_name} {vendor_version}" if vendor_version else f"当前上下文: {profile.display_name}"
    return format_boundary_contract(
        summary_lines=[
            reason,
            context_line,
            "在补齐这些信息之前，当前不能直接给出确定性建议。",
        ],
        next_steps=[
            "先补齐下面列出的材料，再重新提问。",
            "如果暂时拿不到全部材料，至少补充版本、完整报错和实际执行步骤。",
        ],
        needed_materials=missing_labels
        or [
            _official_material_request(vendor_id),
            "原始命令、完整报错和输入文件类型",
        ],
    )
