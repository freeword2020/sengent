from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


MODULE_INDEX_FILENAME = "sentieon-modules.json"
PARAMETER_TOKEN_PATTERN = r"-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*"
MODULE_OVERVIEW_GROUPS = (
    ("Alignment", ("alignment",)),
    ("Germline Variant Calling", ("germline-variant-calling", "copy-number", "workflow")),
    ("Somatic Variant Calling", ("somatic-variant-calling",)),
    ("RNA / Specialized Analysis", ("rna-variant-calling", "specialized-analysis")),
    ("Preprocess / QC / Support", ("family", "bam-processing", "vcf-filtering", "architecture", "fastq-generation")),
)


def module_index_path(source_directory: str | Path) -> Path:
    return Path(source_directory) / MODULE_INDEX_FILENAME


def load_module_index(source_directory: str | Path) -> dict[str, Any]:
    path = module_index_path(source_directory)
    if not path.exists():
        return {"version": "", "entries": []}
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"module index must contain a JSON object: {path}")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"module index entries must be a JSON list: {path}")
    return data


def list_module_entries(source_directory: str | Path) -> list[dict[str, Any]]:
    return [entry for entry in load_module_index(source_directory).get("entries", []) if isinstance(entry, dict)]


def _is_identifier_char(value: str) -> bool:
    return value.isascii() and (value.isalnum() or value in {"_", "-"})


def _alias_match_score(normalized_query: str, normalized_alias: str) -> int:
    if not normalized_alias or normalized_alias not in normalized_query:
        return -1
    if re.fullmatch(r"[a-z0-9][a-z0-9 _-]*", normalized_alias):
        best_score = -1
        start = normalized_query.find(normalized_alias)
        while start >= 0:
            end = start + len(normalized_alias)
            before_ok = start == 0 or not _is_identifier_char(normalized_query[start - 1])
            after_ok = end == len(normalized_query) or not _is_identifier_char(normalized_query[end])
            if before_ok and after_ok:
                score = len(normalized_alias)
                if normalized_query == normalized_alias:
                    score += 20
                elif normalized_query.startswith(normalized_alias):
                    score += 10
                if score > best_score:
                    best_score = score
            start = normalized_query.find(normalized_alias, start + 1)
        return best_score
    score = len(normalized_alias)
    if normalized_query.startswith(normalized_alias):
        score += 10
    if normalized_query == normalized_alias:
        score += 20
    return score


def match_module_entries(
    query: str,
    source_directory: str | Path,
    *,
    max_matches: int = 3,
) -> list[dict[str, Any]]:
    normalized_query = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in list_module_entries(source_directory):
        aliases = [str(value).strip() for value in entry.get("aliases", [])]
        aliases.append(str(entry.get("name", "")).strip())
        best_score = -1
        best_alias = ""
        for alias in aliases:
            normalized_alias = alias.lower()
            score = _alias_match_score(normalized_query, normalized_alias)
            if score > best_score:
                best_score = score
                best_alias = alias
        if best_score >= 0:
            enriched = dict(entry)
            enriched["matched_alias"] = best_alias
            scored.append((best_score, enriched))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return [entry for _, entry in scored[:max_matches]]


def find_related_module_mentions(module_name: str, source_directory: str | Path) -> list[dict[str, str]]:
    normalized_name = module_name.lower().strip()
    mentions: list[dict[str, str]] = []
    for entry in list_module_entries(source_directory):
        related_modules = [str(value).strip() for value in entry.get("related_modules", [])]
        if not any(value.lower() == normalized_name for value in related_modules):
            continue
        mentions.append(
            {
                "name": str(entry.get("name", "")).strip(),
                "summary": str(entry.get("summary", "")).strip(),
            }
        )
    return mentions


def format_missing_module_reference_answer(module_name: str, related_mentions: list[dict[str, str]] | None = None) -> str:
    normalized_name = module_name.strip() or "该模块"
    if related_mentions:
        names = "；".join(item["name"] for item in related_mentions if item.get("name"))
        return (
            "【模块介绍】\n"
            f"- 当前本地模块索引未收录 {normalized_name} 的独立条目，不能把它直接等同于其他模块家族。\n"
            f"- 现有资料里只把它作为相关模块提及，当前可追溯到：{names}。\n\n"
            "【常用参数】\n"
            "- 如果你现在要确认的是 QC 作用、输入输出或调用位置，建议先追问对应父模块或补充更具体的问题。"
        )
    return (
        "【模块介绍】\n"
        f"- 当前本地模块索引未收录 {normalized_name} 的独立条目，暂时不能给出确定性的模块介绍。\n\n"
        "【常用参数】\n"
        "- 请补充更完整的模块名、父流程，或你想确认的是功能、输入输出还是参考脚本。"
    )


def detect_module_query_intent(query: str) -> str:
    normalized = query.lower()
    if re.search(PARAMETER_TOKEN_PATTERN, query) or any(token in normalized for token in ("参数", "选项", "option")):
        return "parameter"
    if any(token in normalized for token in ("输入", "input", "fastq", "ubam", "ucram", "bam", "cram")):
        return "inputs"
    if any(token in normalized for token in ("输出", "产出", "结果", "文件", "output")):
        return "outputs"
    if any(token in normalized for token in ("相关", "上下游", "关联", "配合", "区别", "对比")):
        return "related"
    if any(token in normalized for token in ("适合", "适用于", "用途", "场景", "支持什么", "支持哪些")):
        return "scope"
    return "intro"


def detect_parameter_tokens(query: str) -> list[str]:
    return [match.group(0) for match in re.finditer(PARAMETER_TOKEN_PATTERN, query)]


def _parameter_alias_candidates(alias: str) -> list[str]:
    normalized_alias = alias.lower().strip()
    if not normalized_alias:
        return []
    if normalized_alias.startswith("-"):
        return [normalized_alias]
    return [f"--{normalized_alias}", normalized_alias]


def match_module_parameter(entry: dict[str, Any], query: str) -> dict[str, Any] | None:
    normalized_query = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for parameter in entry.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        aliases = [str(value).strip() for value in parameter.get("aliases", [])]
        aliases.append(str(parameter.get("name", "")).strip())
        best_score = -1
        best_alias = ""
        for alias in aliases:
            for candidate in _parameter_alias_candidates(alias):
                if candidate not in normalized_query:
                    continue
                score = len(candidate) + (20 if candidate.startswith("-") else 0)
                if score > best_score:
                    best_score = score
                    best_alias = alias
        if best_score >= 0:
            enriched = dict(parameter)
            enriched["matched_alias"] = best_alias
            scored.append((best_score, enriched))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return scored[0][1]


def match_parameter_entries(
    query: str,
    source_directory: str | Path,
    *,
    max_matches: int = 3,
) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for entry in list_module_entries(source_directory):
        parameter = match_module_parameter(entry, query)
        if parameter is None:
            continue
        parameter_name = str(parameter.get("name", "")).strip()
        matched_alias = str(parameter.get("matched_alias", "")).strip()
        score = len(parameter_name or matched_alias or "")
        if parameter_name and parameter_name in query:
            score += 20
        if matched_alias and matched_alias in query:
            score += 10
        enriched_entry = dict(entry)
        enriched_entry["matched_parameter"] = dict(parameter)
        scored.append((score, enriched_entry, dict(parameter)))
    scored.sort(
        key=lambda item: (
            -item[0],
            str(item[0]),
            str(item[1].get("name", "")).lower(),
            str(item[2].get("name", "")).lower(),
        )
    )
    return [entry for _, entry, _ in scored[:max_matches]]


def build_module_evidence(entry: dict[str, Any]) -> dict[str, str]:
    summary = str(entry.get("summary", "")).strip()
    category = str(entry.get("category", "")).strip()
    inputs = "；".join(str(value).strip() for value in entry.get("inputs", []) if str(value).strip())
    outputs = "；".join(str(value).strip() for value in entry.get("outputs", []) if str(value).strip())
    snippet_parts = [f"{entry.get('name', '模块')}：{summary}"]
    if category:
        snippet_parts.append(f"类别：{category}")
    if inputs:
        snippet_parts.append(f"输入：{inputs}")
    if outputs:
        snippet_parts.append(f"输出：{outputs}")
    return {
        "name": MODULE_INDEX_FILENAME,
        "path": MODULE_INDEX_FILENAME,
        "type": "json",
        "trust": "derived",
        "priority": "1",
        "snippet": " ".join(snippet_parts).strip(),
    }


def build_parameter_evidence(entry: dict[str, Any], parameter: dict[str, Any]) -> dict[str, str]:
    details = "；".join(str(value).strip() for value in parameter.get("details", []) if str(value).strip())
    values = "；".join(str(value).strip() for value in parameter.get("values", []) if str(value).strip())
    snippet_parts = [
        f"{entry.get('name', '模块')} {parameter.get('name', '参数')}：{str(parameter.get('summary', '')).strip()}",
    ]
    if values:
        snippet_parts.append(f"值：{values}")
    if details:
        snippet_parts.append(f"说明：{details}")
    return {
        "name": MODULE_INDEX_FILENAME,
        "path": MODULE_INDEX_FILENAME,
        "type": "json",
        "trust": "derived",
        "priority": "1",
        "snippet": " ".join(snippet_parts).strip(),
    }


def format_script_reference_answer(entry: dict[str, Any]) -> str:
    examples = [item for item in entry.get("script_examples", []) if isinstance(item, dict)]
    if not examples:
        return ""

    example = examples[0]
    name = str(entry.get("name", "")).strip() or "未知模块"
    summary = str(entry.get("summary", "")).strip()
    title = str(example.get("title", "")).strip() or "reference script"
    example_summary = str(example.get("summary", "")).strip()
    when_to_use = [str(value).strip() for value in example.get("when_to_use", []) if str(value).strip()]
    command_lines = [str(value).rstrip() for value in example.get("command_lines", []) if str(value).strip()]
    notes = [str(value).strip() for value in example.get("notes", []) if str(value).strip()]

    intro_lines = [f"{name}：{summary}"]
    if example_summary:
        intro_lines.append(f"- 脚本定位：{example_summary}")
    if when_to_use:
        intro_lines.append(f"- 适用场景：{'；'.join(when_to_use)}")

    command_section = [f"- {title}"]
    command_section.extend(f"  {line}" for line in command_lines)

    usage_lines = [f"- {note}" for note in notes] or ["- 这是参考命令骨架，样本名、路径、线程数和参考文件需要按现场替换。"]

    return (
        "【模块介绍】\n"
        + "\n".join(intro_lines)
        + "\n\n【参考命令】\n"
        + "\n".join(command_section)
        + "\n\n【使用前提】\n"
        + "\n".join(usage_lines)
    )


def _is_release_note_only_entry(entry: dict[str, Any]) -> bool:
    summary = str(entry.get("summary", "")).strip().lower()
    scope_values = [str(value).strip().lower() for value in entry.get("scope", []) if str(value).strip()]
    return "release notes" in summary or "release notes mention only" in scope_values


def format_unavailable_script_reference_answer(entry: dict[str, Any]) -> str:
    if not _is_release_note_only_entry(entry):
        return ""
    name = str(entry.get("name", "")).strip() or "未知模块"
    return (
        "【参考命令】\n"
        f"- {name}：当前本地官方资料仅见 release notes 级提及，未提供可确定性复用的参考脚本或 CLI 骨架。"
    )


def format_unavailable_parameter_reference_answer(entry: dict[str, Any]) -> str:
    if not _is_release_note_only_entry(entry):
        return ""
    name = str(entry.get("name", "")).strip() or "未知模块"
    return (
        "【常用参数】\n"
        f"- {name}：当前本地官方资料仅见 release notes 级提及，未提供可确定性索引的参数列表。"
    )


def format_parameter_followup_answer(entry: dict[str, Any]) -> str:
    name = str(entry.get("name", "")).strip() or "未知模块"
    parameter_names: list[str] = []
    for parameter in entry.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        parameter_name = str(parameter.get("name", "")).strip()
        if not parameter_name or parameter_name in parameter_names:
            continue
        parameter_names.append(parameter_name)

    if not parameter_names:
        return (
            "【常用参数】\n"
            f"- 已定位到 {name}，但你这句还没给出具体参数名。\n"
            "- 当前本地模块索引未收录可直接提示的参数示例，请直接补充完整参数名后再查询。"
        )

    examples = "；".join(f"{name} 的 {parameter_name} 是什么" for parameter_name in parameter_names[:2])
    return (
        "【常用参数】\n"
        f"- 已定位到 {name}，但你这句还没给出具体参数名。\n"
        f"- 请直接补充参数名，例如：{examples}。"
    )


def format_module_overview_answer(source_directory: str | Path) -> str:
    entries = list_module_entries(source_directory)
    if not entries:
        return ""

    intro_lines = ["Sentieon 主要模块可以先按下面几组理解："]
    placeholder_names = [
        str(entry.get("name", "")).strip()
        for entry in entries
        if "待核验占位" in str(entry.get("summary", "")).strip()
    ]
    for label, categories in MODULE_OVERVIEW_GROUPS:
        names: list[str] = []
        for category in categories:
            for entry in entries:
                entry_category = str(entry.get("category", "")).strip()
                entry_name = str(entry.get("name", "")).strip()
                if entry_category != category or not entry_name:
                    continue
                if entry_name in placeholder_names:
                    continue
                if category == "family" and label == "Preprocess / QC / Support" and entry_name != "QC":
                    continue
                names.append(entry_name)
        if names:
            intro_lines.append(f"- {label}：{'；'.join(names)}")
    if placeholder_names:
        intro_lines.append(f"- 待核验占位：{'；'.join(placeholder_names)}")

    parameter_lines = [
        "- 如果要继续收窄，可直接追问具体模块，例如：DNAscope 是什么；TNscope 和 TNseq 区别；RNAseq 参考脚本。",
    ]

    return (
        "【资料查询】\n"
        "- 命中语义意图：module_overview\n\n"
        "【模块介绍】\n"
        + "\n".join(intro_lines)
        + "\n\n【常用参数】\n"
        + "\n".join(parameter_lines)
    )


def format_module_reference_answer(entry: dict[str, Any], query: str) -> str:
    intent = detect_module_query_intent(query)
    if intent == "parameter":
        return ""

    name = str(entry.get("name", "")).strip() or "未知模块"
    category = str(entry.get("category", "")).strip()
    summary = str(entry.get("summary", "")).strip()
    if "待核验占位" in summary:
        return (
            "【模块介绍】\n"
            f"{name}：{summary}\n\n"
            "【常用参数】\n"
            "- 当前本地官方资料未提供可用于确定性回答的详细章节。"
        )
    if _is_release_note_only_entry(entry):
        return (
            "【模块介绍】\n"
            f"{name}：{summary}\n\n"
            "【常用参数】\n"
            "- 当前本地官方资料仅见 release notes 级提及，尚未提供稳定的输入、输出或参数章节。"
        )
    matched_alias = str(entry.get("matched_alias", "")).strip()
    scope = [str(value).strip() for value in entry.get("scope", []) if str(value).strip()]
    inputs = [str(value).strip() for value in entry.get("inputs", []) if str(value).strip()]
    outputs = [str(value).strip() for value in entry.get("outputs", []) if str(value).strip()]
    related = [str(value).strip() for value in entry.get("related_modules", []) if str(value).strip()]
    common_questions = [str(value).strip() for value in entry.get("common_questions", []) if str(value).strip()]

    lookup_lines = [f"- 命中模块索引：{name}"]
    if matched_alias and matched_alias.lower() != name.lower():
        lookup_lines.append(f"- 命中别名：{matched_alias}")
    if category:
        lookup_lines.append(f"- 模块类别：{category}")

    intro_lines = [f"{name}：{summary}"]
    if intent in {"intro", "scope"} and scope:
        intro_lines.append(f"- 适用范围：{'；'.join(scope)}")
    if intent in {"intro", "inputs", "scope"} and inputs:
        intro_lines.append(f"- 常见输入：{'；'.join(inputs)}")
    if intent in {"intro", "outputs"} and outputs:
        intro_lines.append(f"- 常见输出：{'；'.join(outputs)}")
    if intent in {"intro", "related"} and related:
        intro_lines.append(f"- 相关模块：{'；'.join(related)}")

    parameter_lines = [
        "- 当前模块索引优先覆盖模块定位、输入输出、适用范围和相关模块。",
    ]
    if common_questions:
        parameter_lines.append(f"- 可继续追问：{'；'.join(common_questions[:3])}")

    return (
        "【资料查询】\n"
        + "\n".join(lookup_lines)
        + "\n\n【模块介绍】\n"
        + "\n".join(intro_lines)
        + "\n\n【常用参数】\n"
        + "\n".join(parameter_lines)
    )


def format_parameter_reference_answer(entry: dict[str, Any], parameter: dict[str, Any]) -> str:
    name = str(entry.get("name", "")).strip() or "未知模块"
    parameter_name = str(parameter.get("name", "")).strip() or "未知参数"
    summary = str(parameter.get("summary", "")).strip()
    details = [str(value).strip() for value in parameter.get("details", []) if str(value).strip()]
    values = [str(value).strip() for value in parameter.get("values", []) if str(value).strip()]

    parameter_lines = [f"- {name} 的 {parameter_name}：{summary}"]
    if values:
        parameter_lines.append(f"- 可选值/关键值：{'；'.join(values)}")
    for detail in details:
        parameter_lines.append(f"- {detail}")

    return "【常用参数】\n" + "\n".join(parameter_lines)


def format_parameter_disambiguation(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "未在本地资料中找到相关参数，请补充更具体的模块名或参数名。"
    parameter_names = []
    module_names = []
    for match in matches:
        module_name = str(match.get("name", "")).strip()
        matched_parameter = match.get("matched_parameter", {})
        parameter_name = str(matched_parameter.get("name", "")).strip() if isinstance(matched_parameter, dict) else ""
        if parameter_name and parameter_name not in parameter_names:
            parameter_names.append(parameter_name)
        if module_name and module_name not in module_names:
            module_names.append(module_name)
    shown_parameter = parameter_names[0] if parameter_names else "该参数"
    shown_modules = "；".join(module_names[:4])
    example_module = module_names[0] if module_names else "模块名"
    return (
        "需要确认模块："
        f"参数 {shown_parameter} 同时出现在多个模块中（{shown_modules}）。"
        f"请补充模块名后再查询，例如：{example_module} 的 {shown_parameter} 是什么"
    )
