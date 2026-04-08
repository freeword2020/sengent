from __future__ import annotations


FIELD_LABELS = {
    "version": "Sentieon 版本",
    "error": "完整报错信息",
    "input_type": "输入文件类型",
    "data_type": "数据类型",
    "step": "执行步骤",
}

ISSUE_TYPE_LABELS = {
    "license": "许可证问题",
    "install": "安装问题",
    "reference": "资料查询",
    "other": "其他问题",
}


def event_detect_issue_type(issue_type: str) -> str:
    label = ISSUE_TYPE_LABELS.get(issue_type, issue_type)
    return f"已识别问题类型：{label}"


def event_check_missing_info(missing_fields: list[str]) -> str:
    if not missing_fields:
        return "已检查必要信息"
    labels = [FIELD_LABELS.get(field, field) for field in missing_fields]
    return f"发现需要补充的信息：{', '.join(labels)}"


def event_search_sources() -> str:
    return "正在检索本地资料"


def event_prepare_reference_answer() -> str:
    return "正在整理参考答案"


def event_generate_reply() -> str:
    return "正在生成回复"
