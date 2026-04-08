from __future__ import annotations

import inspect
import re
from typing import Any

from sentieon_assist.config import AppConfig, load_config
from sentieon_assist.external_guides import (
    format_external_error_association,
    format_external_guide_answer,
    match_external_error_association,
    match_external_guide_entry,
)
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.module_index import (
    build_module_evidence,
    format_module_overview_answer,
    format_parameter_followup_answer,
    format_module_reference_answer,
    format_parameter_disambiguation,
    format_parameter_reference_answer,
    format_script_reference_answer,
    format_unavailable_parameter_reference_answer,
    format_unavailable_script_reference_answer,
    match_module_entries,
    match_module_parameter,
    match_parameter_entries,
)
from sentieon_assist.prompts import build_reference_prompt, build_support_prompt
from sentieon_assist.reference_intents import ReferenceIntent, parse_reference_intent
from sentieon_assist.rules import match_rule
from sentieon_assist.sources import collect_source_bundle_metadata, collect_source_evidence
from sentieon_assist.workflow_index import (
    format_workflow_guidance_answer,
    format_workflow_uncovered_answer,
    match_workflow_entry,
)


REQUIRED_FIELDS = {
    "license": ("version", "error"),
    "install": ("version",),
}

FIELD_LABELS = {
    "version": "Sentieon 版本",
    "error": "完整报错信息",
    "input_type": "输入文件类型",
    "data_type": "数据类型",
    "step": "执行步骤",
}

REQUIREMENT_FIELD_ALIASES = {
    "Sentieon 版本": "version",
    "完整报错信息": "error",
    "输入文件类型": "input_type",
    "数据类型": "data_type",
    "执行步骤": "step",
}


def _join_lines(values: list[str]) -> str:
    if not values:
        return "- 无"
    return "\n".join(f"- {value}" for value in values)


def format_rule_answer(rule: dict[str, Any]) -> str:
    summary = str(rule.get("summary", "")).strip() or "这是一个待排查的支持问题。"
    causes = [str(value) for value in rule.get("causes", [])]
    steps = [str(value) for value in rule.get("steps", [])]
    requires = [str(value) for value in rule.get("requires", [])]
    return (
        "【问题判断】\n"
        f"{summary}\n\n"
        "【可能原因】\n"
        f"{_join_lines(causes)}\n\n"
        "【建议步骤】\n"
        f"{_join_lines(steps)}\n\n"
        "【需要补充的信息】\n"
        f"{_join_lines(requires)}"
    )


def filter_known_requirements(rule: dict[str, Any], info: dict[str, str]) -> dict[str, Any]:
    filtered_rule = dict(rule)
    filtered_requires: list[str] = []
    for requirement in rule.get("requires", []):
        requirement_text = str(requirement).strip()
        field_name = REQUIREMENT_FIELD_ALIASES.get(requirement_text, "")
        if field_name and info.get(field_name, "").strip():
            continue
        filtered_requires.append(requirement_text)
    filtered_rule["requires"] = filtered_requires
    return filtered_rule


def missing_required_fields(issue_type: str, info: dict[str, str]) -> list[str]:
    return [field for field in REQUIRED_FIELDS.get(issue_type, ()) if not info.get(field, "").strip()]


def ask_for_missing(missing_fields: list[str]) -> str:
    labels = [FIELD_LABELS.get(field, field) for field in missing_fields]
    return f"需要补充以下信息：{', '.join(labels)}"


def _format_source_context(source_context: dict[str, str] | None = None) -> str:
    if not source_context:
        return ""
    lines: list[str] = []
    if source_context.get("primary_release"):
        lines.append(f"- 主参考版本: {source_context['primary_release']}")
    if source_context.get("primary_date"):
        lines.append(f"- 主参考日期: {source_context['primary_date']}")
    if source_context.get("primary_reference"):
        lines.append(f"- 主参考文件: {source_context['primary_reference']}")
    if not lines:
        return ""
    return "【资料版本】\n" + "\n".join(lines)


def _version_family(version: str) -> str:
    match = re.search(r"(20\d{4})", version or "")
    return match.group(1) if match else ""


def _format_version_warning(query_version: str, source_context: dict[str, str] | None = None) -> str:
    if not query_version or not source_context:
        return ""
    primary_release = source_context.get("primary_release", "").strip()
    if not primary_release:
        return ""
    query_version = query_version.strip()
    query_family = _version_family(query_version)
    primary_family = _version_family(primary_release)
    if not query_family or not primary_family:
        return ""

    has_patch_query = "." in query_version
    has_patch_primary = "." in primary_release
    mismatch = False
    if has_patch_query and has_patch_primary:
        mismatch = query_version != primary_release
    else:
        mismatch = query_family != primary_family
    if not mismatch:
        return ""
    return (
        "【版本提示】\n"
        f"- 用户问题版本: {query_version}\n"
        f"- 当前资料主版本: {primary_release}\n"
        "- 当前回答基于资料包主版本，请确认是否需要切换对应版本资料后再执行。"
    )


BIOINFORMATICS_TERMINOLOGY_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?<![（(])somatic variant\s+(?:and|和)\s+structural variant detection(?![）)])",
            re.IGNORECASE,
        ),
        "体细胞变异与结构变异检测（somatic variant and structural variant detection）",
    ),
    (
        re.compile(r"(?<![（(])germline variant calling pipeline(?![）)])", re.IGNORECASE),
        "胚系变异检测流程（germline variant calling pipeline）",
    ),
    (
        re.compile(r"(?<![（(])germline variant calling(?![）)])", re.IGNORECASE),
        "胚系变异检测（germline variant calling）",
    ),
    (
        re.compile(r"(?<![（(])structural variant detection(?![）)])", re.IGNORECASE),
        "结构变异检测（structural variant detection）",
    ),
    (
        re.compile(r"(?<![（(])germline variants(?![）)])", re.IGNORECASE),
        "胚系变异（germline variants）",
    ),
    (
        re.compile(r"(?<![（(])long-read sequence data(?![）)])", re.IGNORECASE),
        "长读长测序数据（long-read sequence data）",
    ),
    (
        re.compile(r"(?<![（(])diploid organism(?![）)])", re.IGNORECASE),
        "二倍体生物（diploid organism）",
    ),
    (
        re.compile(r"(?<![（(])short-read germline(?![）)])", re.IGNORECASE),
        "短读长胚系（short-read germline）",
    ),
    (
        re.compile(r"(?<![（(])long-read germline(?![）)])", re.IGNORECASE),
        "长读长胚系（long-read germline）",
    ),
    (
        re.compile(r"(?<![（(])short-read\s+\+\s+long-read(?![）)])", re.IGNORECASE),
        "短读长 + 长读长（short-read + long-read）",
    ),
    (
        re.compile(r"(?<![（(])tumor[- ]normal(?![）)])", re.IGNORECASE),
        "肿瘤-正常配对（tumor-normal）",
    ),
    (
        re.compile(r"(?<![（(])tumor[- ]only(?![）)])", re.IGNORECASE),
        "单肿瘤（tumor-only）",
    ),
    (
        re.compile(r"(?<![（(])matched normal(?![）)])", re.IGNORECASE),
        "配对正常样本（matched normal）",
    ),
    (
        re.compile(r"(?<![（(])manual(?![）)])", re.IGNORECASE),
        "官方手册（manual）",
    ),
)


def _normalize_bioinformatics_terminology(text: str) -> str:
    normalized = text
    for pattern, replacement in BIOINFORMATICS_TERMINOLOGY_RULES:
        normalized = pattern.sub(replacement, normalized)
    normalized = re.sub(
        r"([\u4e00-\u9fff])\s+(?=(?:配对正常样本|单肿瘤|肿瘤-正常配对|胚系变异|胚系变异检测流程|胚系变异检测|结构变异检测|体细胞变异与结构变异检测|长读长测序数据|长读长胚系|短读长胚系|短读长 \+ 长读长|二倍体生物|官方手册))",
        r"\1",
        normalized,
    )
    normalized = re.sub(r"((?:[A-Za-z0-9 .+\-/]+)）)\s+(?=[\u4e00-\u9fff])", r"\1", normalized)
    return normalized


TERSE_SCRIPT_FOLLOWUP_CUES = (
    "我就要个示例",
    "我只要个示例",
    "给个示例",
    "来个示例",
    "示例也行",
    "示例就行",
    "来个脚本",
    "脚本也行",
    "就要脚本",
    "给我个脚本",
)


def _is_terse_script_followup(query: str) -> bool:
    normalized = re.sub(r"\s+", "", query.strip().lower())
    return any(normalized.endswith(cue) for cue in TERSE_SCRIPT_FOLLOWUP_CUES)


def _workflow_script_module(entry: dict[str, Any]) -> str:
    return str(entry.get("script_module", "")).strip()


def normalize_model_answer(
    text: str,
    query_version: str = "",
    source_context: dict[str, str] | None = None,
    sources: list[str] | None = None,
) -> str:
    normalized = str(text)
    for header in ("【问题判断】", "【可能原因】", "【建议步骤】", "【需要补充的信息】"):
        normalized = normalized.replace(f"**{header}**", header)
    normalized = re.sub(
        r"```[\s\S]*?```",
        "命令细节需要结合官方文档确认。",
        normalized,
    )
    normalized = re.sub(r"\*\*(.*?)\*\*", r"\1", normalized)
    normalized = re.sub(r"`([^`]+)`", r"\1", normalized)
    normalized = re.sub(r"(?m)^\*\s+", "- ", normalized)
    normalized = _normalize_bioinformatics_terminology(normalized)
    source_context_block = _format_source_context(source_context)
    if source_context_block:
        normalized = f"{normalized}\n\n{source_context_block}"
    version_warning_block = _format_version_warning(query_version, source_context)
    if version_warning_block:
        normalized = f"{normalized}\n\n{version_warning_block}"
    filtered_sources = _filter_display_sources(sources or [])
    if filtered_sources and "【参考资料】" not in normalized:
        source_lines = "\n".join(f"- {source}" for source in filtered_sources)
        normalized = f"{normalized}\n\n【参考资料】\n{source_lines}"
    return normalized


def _filter_display_sources(sources: list[str]) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for source in sources:
        name = str(source).strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered == "sentieon-chinese-reference.md":
            continue
        if lowered.startswith("thread-") and lowered.endswith("-summary.md"):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        filtered.append(name)
    return filtered


def format_reference_display(text: str) -> str:
    hidden_headers = {"【资料查询】", "【资料版本】", "【参考资料】"}
    lines = str(text).splitlines()
    visible_lines: list[str] = []
    skip_section = False
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"【[^】]+】", stripped):
            skip_section = stripped in hidden_headers
            if not skip_section:
                visible_lines.append(stripped)
            continue
        if skip_section:
            continue
        visible_lines.append(line)

    compacted = "\n".join(visible_lines)
    compacted = re.sub(r"\n{3,}", "\n\n", compacted)
    return compacted.strip()


def generate_model_fallback(
    issue_type: str,
    query: str,
    info: dict[str, str],
    source_context: dict[str, str] | None = None,
    evidence: list[dict[str, str]] | None = None,
    config: AppConfig | None = None,
) -> str:
    app_config = config or load_config()
    prompt = build_support_prompt(issue_type, query, info, source_context=source_context, evidence=evidence)
    text = build_backend_router(app_config).generate(prompt)
    source_names = [item["name"] for item in evidence or []]
    return normalize_model_answer(
        text,
        query_version=info.get("version", ""),
        source_context=source_context,
        sources=source_names,
    )


def generate_reference_fallback(
    query: str,
    *,
    source_context: dict[str, str] | None = None,
    evidence: list[dict[str, str]] | None = None,
    config: AppConfig | None = None,
) -> str:
    app_config = config or load_config()
    prompt = build_reference_prompt(query, source_context=source_context, evidence=evidence)
    text = build_backend_router(app_config).generate(prompt)
    source_names = [item["name"] for item in evidence or []]
    return normalize_model_answer(
        text,
        source_context=source_context,
        sources=source_names,
    )


def call_model_fallback(model_fallback, issue_type: str, query: str, info: dict[str, str], evidence: list[dict[str, str]]) -> str:
    parameters = inspect.signature(model_fallback).parameters.values()
    positional_params = [
        parameter
        for parameter in parameters
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    accepts_varargs = any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters)
    if accepts_varargs or len(positional_params) >= 4:
        return model_fallback(issue_type, query, info, evidence)
    return model_fallback(issue_type, query, info)


def answer_query(
    issue_type: str,
    query: str,
    info: dict[str, str],
    *,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
) -> str:
    missing = missing_required_fields(issue_type, info)
    if missing:
        return ask_for_missing(missing)

    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)

    if knowledge_directory is None:
        rule = match_rule(query)
    else:
        rule = match_rule(query, knowledge_directory)
    if rule:
        filtered_rule = filter_known_requirements(rule, info)
        return normalize_model_answer(
            format_rule_answer(filtered_rule),
            query_version=info.get("version", ""),
            source_context=source_context,
        )

    if issue_type == "other":
        return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"

    evidence = collect_source_evidence(
        effective_source_directory,
        issue_type=issue_type,
        query=query,
        info=info,
    )

    if model_fallback is not None:
        text = call_model_fallback(model_fallback, issue_type, query, info, evidence)
        source_names = [item["name"] for item in evidence]
        return normalize_model_answer(
            text,
            query_version=info.get("version", ""),
            source_context=source_context,
            sources=source_names,
        )

    return generate_model_fallback(
        issue_type,
        query,
        info,
        source_context=source_context,
        evidence=evidence,
        config=app_config,
    )


def answer_reference_query(
    query: str,
    *,
    model_fallback=None,
    source_directory: str | None = None,
    parsed_intent: ReferenceIntent | None = None,
) -> str:
    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)
    resolved_intent = parsed_intent or ReferenceIntent()
    if resolved_intent.intent == "not_reference":
        resolved_intent = parse_reference_intent(query, config=app_config)
    if resolved_intent.intent == "workflow_guidance":
        workflow_entry = match_workflow_entry(query, effective_source_directory)
        if workflow_entry is None:
            return format_reference_display(
                normalize_model_answer(
                    format_workflow_uncovered_answer(),
                    source_context=source_context,
                    sources=["workflow-guides.json"],
                )
            )
        if _is_terse_script_followup(query):
            script_entry = workflow_entry
            script_module = _workflow_script_module(script_entry)
            if not script_module:
                script_entry = match_workflow_entry(
                    query,
                    effective_source_directory,
                    require_script_module=True,
                )
                script_module = _workflow_script_module(script_entry or {})
            if script_module:
                module_matches = match_module_entries(script_module, effective_source_directory, max_matches=1)
                if module_matches:
                    module_entry = module_matches[0]
                    direct_answer = format_script_reference_answer(module_entry) or format_unavailable_script_reference_answer(
                        module_entry
                    )
                    if direct_answer:
                        script_source_names = [
                            "sentieon-modules.json",
                            *[str(item) for item in module_entry.get("sources", [])],
                        ]
                        return format_reference_display(
                            normalize_model_answer(
                                direct_answer,
                                source_context=source_context,
                                sources=script_source_names,
                            )
                        )
        source_names = ["workflow-guides.json", *[str(item) for item in workflow_entry.get("sources", [])]]
        return format_reference_display(
            normalize_model_answer(
                format_workflow_guidance_answer(workflow_entry),
                source_context=source_context,
                sources=source_names,
            )
        )
    external_entry = None
    external_error_association = None
    if resolved_intent.intent == "reference_other":
        external_error_association = match_external_error_association(query, effective_source_directory)
        external_entry = match_external_guide_entry(query, effective_source_directory)
    if external_error_association is not None:
        source_names = [
            str(external_error_association.get("source_file", "")).strip(),
            *[str(item) for item in external_error_association.get("source_notes", [])],
        ]
        source_names = [name for name in source_names if name]
        return format_reference_display(
            normalize_model_answer(
                format_external_error_association(external_error_association),
                source_context=source_context,
                sources=source_names,
            )
        )
    module_matches = match_module_entries(query, effective_source_directory, max_matches=1)
    matched_module = ""
    explicit_module_focus = False
    if module_matches:
        matched_module = str(module_matches[0].get("matched_alias", "")).strip()
        normalized_query = query.lower()
        normalized_module = matched_module.lower()
        if normalized_module:
            explicit_module_focus = (
                normalized_query.startswith(normalized_module)
                or f"{normalized_module} 的" in normalized_query
                or f"{normalized_module}的" in normalized_query
            )
    if external_entry is not None:
        matched_external = str(external_entry.get("matched_alias", "")).strip()
        if not explicit_module_focus and (not matched_module or len(matched_external) >= len(matched_module) + 2):
            source_names = [
                str(external_entry.get("source_file", "")).strip(),
                *[str(item) for item in external_entry.get("source_notes", [])],
            ]
            source_names = [name for name in source_names if name]
            return format_reference_display(
                normalize_model_answer(
                    format_external_guide_answer(external_entry),
                    source_context=source_context,
                    sources=source_names,
                )
            )
    module_evidence: list[dict[str, str]] = []
    if module_matches:
        module_entry = module_matches[0]
        module_summary = str(module_entry.get("summary", "")).strip()
        if "待核验占位" in module_summary:
            direct_answer = format_module_reference_answer(module_entry, query)
            module_evidence.append(build_module_evidence(module_entry))
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return format_reference_display(
                    normalize_model_answer(
                        direct_answer,
                        source_context=source_context,
                        sources=source_names,
                    )
                )
        if resolved_intent.intent == "script_example":
            direct_answer = format_script_reference_answer(module_entry) or format_unavailable_script_reference_answer(
                module_entry
            )
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return format_reference_display(
                    normalize_model_answer(
                        direct_answer,
                        source_context=source_context,
                        sources=source_names,
                    )
                )
        module_parameter = match_module_parameter(module_entry, query)
        if module_parameter is not None:
            direct_answer = format_parameter_reference_answer(module_entry, module_parameter)
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return format_reference_display(
                normalize_model_answer(
                    direct_answer,
                    source_context=source_context,
                    sources=source_names,
                )
            )
        if resolved_intent.intent == "parameter_lookup":
            direct_answer = format_unavailable_parameter_reference_answer(module_entry)
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return format_reference_display(
                    normalize_model_answer(
                        direct_answer,
                        source_context=source_context,
                        sources=source_names,
                    )
                )
            direct_answer = format_parameter_followup_answer(module_entry)
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return format_reference_display(
                    normalize_model_answer(
                        direct_answer,
                        source_context=source_context,
                        sources=source_names,
                    )
                )
        direct_answer = format_module_reference_answer(module_entry, query)
        module_evidence.append(build_module_evidence(module_entry))
        if direct_answer:
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return format_reference_display(
                normalize_model_answer(
                    direct_answer,
                    source_context=source_context,
                    sources=source_names,
                )
            )
    global_parameter_matches = match_parameter_entries(query, effective_source_directory, max_matches=1)
    all_parameter_matches = match_parameter_entries(query, effective_source_directory)
    if len(all_parameter_matches) > 1:
        return format_parameter_disambiguation(all_parameter_matches)
    if global_parameter_matches:
        module_entry = global_parameter_matches[0]
        module_parameter = module_entry.get("matched_parameter")
        if isinstance(module_parameter, dict):
            direct_answer = format_parameter_reference_answer(module_entry, module_parameter)
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return format_reference_display(
                normalize_model_answer(
                    direct_answer,
                    source_context=source_context,
                    sources=source_names,
                )
            )
    if resolved_intent.intent == "module_overview":
        direct_answer = format_module_overview_answer(effective_source_directory)
        if direct_answer:
            source_names = ["sentieon-modules.json", "sentieon-module-index.md"]
            return format_reference_display(
                normalize_model_answer(
                    direct_answer,
                    source_context=source_context,
                    sources=source_names,
                )
            )
    evidence = collect_source_evidence(
        effective_source_directory,
        issue_type="reference",
        query=query,
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )
    if module_evidence:
        evidence = [
            *module_evidence,
            *[item for item in evidence if item.get("name") != "sentieon-modules.json"],
        ]
    if not evidence:
        return "未在本地资料中找到相关模块或参数，请补充更具体的模块名或参数名。"
    if model_fallback is not None:
        text = call_model_fallback(model_fallback, "reference", query, {}, evidence)
        source_names = [item["name"] for item in evidence]
        return format_reference_display(
            normalize_model_answer(
                text,
                source_context=source_context,
                sources=source_names,
            )
        )
    return format_reference_display(
        generate_reference_fallback(
            query,
            source_context=source_context,
            evidence=evidence,
            config=app_config,
        )
    )
