ANSWER_TEMPLATE = """
你是 Sentieon 技术支持助手。

必须按以下格式回答：

【问题判断】
【可能原因】
【建议步骤】
【需要补充的信息】

不要编造命令。
""".strip()

REFERENCE_TEMPLATE = """
你是 Sentieon 技术资料助手。

必须按以下格式回答：

【资料查询】
【模块介绍】
【常用参数】
【参考资料】

只允许基于提供的本地资料片段整理，不要脱离资料自由发挥。
""".strip()

REFERENCE_INTENT_TEMPLATE = """
你是 Sentieon 问句意图解析器。

只输出一个 JSON 对象，不要输出解释、Markdown 或代码块。

允许的 intent:
- module_overview: 用户在问 Sentieon 有哪些模块、主要模块、模块总览
- module_intro: 用户在问某个模块是什么、做什么、适合什么
- workflow_guidance: 用户在问 WGS/WES/胚系/体细胞/长读长 这类流程该怎么分流、该看哪个官方 workflow
- parameter_lookup: 用户在问参数、选项、flag 的含义，包括 `-t`、`-r` 这类全局参数
- script_example: 用户在要参考脚本、示例命令、workflow skeleton，或在问某模块当前是否有稳定参考命令
- reference_other: 明显是资料查询，但不属于以上几类
- not_reference: 不是资料查询

JSON schema:
{"intent":"module_overview|module_intro|workflow_guidance|parameter_lookup|script_example|reference_other|not_reference","module":"","confidence":0.0}
""".strip()


def build_chat_missing_info_prompt(query: str, raw_response: str) -> str:
    return (
        "你是 Sentieon 中文技术支持助手。\n"
        "请把下面这条生硬的缺失信息提示改写成自然、简短、礼貌的中文追问。\n"
        "要求：\n"
        "1. 保留原始缺失字段要求，不要新增字段\n"
        "2. 结合用户原话来追问\n"
        "3. 只输出一段中文追问，不要解释\n\n"
        f"用户原话：{query}\n"
        f"原始提示：{raw_response}"
    )


def build_chat_polish_prompt(query: str, raw_response: str) -> str:
    return (
        "你是 Sentieon 中文技术支持助手。\n"
        "请在不改变结论、步骤、版本信息和资料引用的前提下，把下面答案润色得更自然。\n"
        "要求：\n"
        "1. 保留所有已有事实\n"
        "2. 保留现有分段和标题\n"
        "3. 不要新增未经提供的命令、参数或结论\n"
        "4. 只输出润色后的最终答案\n\n"
        f"用户原话：{query}\n"
        f"待润色答案：\n{raw_response}"
    )


def build_reference_prompt(
    query: str,
    *,
    source_context: dict[str, str] | None = None,
    evidence: list[dict[str, str]] | None = None,
) -> str:
    prompt = f"{REFERENCE_TEMPLATE}\n\n用户问题：{query}"
    if source_context and any(source_context.values()):
        context_lines = []
        if source_context.get("primary_release"):
            context_lines.append(f"- 主参考版本: {source_context['primary_release']}")
        if source_context.get("primary_date"):
            context_lines.append(f"- 主参考日期: {source_context['primary_date']}")
        if source_context.get("primary_reference"):
            context_lines.append(f"- 主参考文件: {source_context['primary_reference']}")
        if context_lines:
            prompt += f"\n\n资料版本上下文：\n" + "\n".join(context_lines)
    if evidence:
        evidence_lines = "\n".join(
            f"- {item['name']} [{item.get('trust', 'other')}]: {item['snippet']}"
            for item in evidence
        )
        prompt += f"\n\n本地资料片段：\n{evidence_lines}"
    return prompt


def build_reference_intent_prompt(query: str) -> str:
    return f"{REFERENCE_INTENT_TEMPLATE}\n\n用户问题：{query}"


def build_support_prompt(
    issue_type: str,
    query: str,
    info: dict[str, str],
    source_context: dict[str, str] | None = None,
    evidence: list[dict[str, str]] | None = None,
) -> str:
    info_lines = "\n".join(f"- {key}: {value or '未知'}" for key, value in info.items())
    prompt = (
        f"{ANSWER_TEMPLATE}\n\n"
        f"问题类型：{issue_type}\n"
        f"用户问题：{query}\n"
        "已提取信息：\n"
        f"{info_lines}"
    )
    if source_context and any(source_context.values()):
        context_lines = []
        if source_context.get("primary_release"):
            context_lines.append(f"- 主参考版本: {source_context['primary_release']}")
        if source_context.get("primary_date"):
            context_lines.append(f"- 主参考日期: {source_context['primary_date']}")
        if source_context.get("primary_reference"):
            context_lines.append(f"- 主参考文件: {source_context['primary_reference']}")
        if context_lines:
            prompt += f"\n\n资料版本上下文：\n" + "\n".join(context_lines)
    if evidence:
        evidence_lines = "\n".join(
            f"- {item['name']} [{item.get('trust', 'other')}]: {item['snippet']}"
            for item in evidence
        )
        prompt += f"\n\n参考资料片段：\n{evidence_lines}"
    return prompt
