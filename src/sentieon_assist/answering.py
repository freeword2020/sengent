from __future__ import annotations

import inspect
import re
from typing import Any

from sentieon_assist.config import AppConfig, load_config
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.module_index import (
    build_module_evidence,
    format_module_reference_answer,
    format_parameter_disambiguation,
    format_parameter_reference_answer,
    match_module_entries,
    match_module_parameter,
    match_parameter_entries,
)
from sentieon_assist.prompts import build_reference_prompt, build_support_prompt
from sentieon_assist.rules import match_rule
from sentieon_assist.sources import collect_source_bundle_metadata, collect_source_evidence


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
    source_context_block = _format_source_context(source_context)
    if source_context_block:
        normalized = f"{normalized}\n\n{source_context_block}"
    version_warning_block = _format_version_warning(query_version, source_context)
    if version_warning_block:
        normalized = f"{normalized}\n\n{version_warning_block}"
    if sources and "【参考资料】" not in normalized:
        source_lines = "\n".join(f"- {source}" for source in sources)
        normalized = f"{normalized}\n\n【参考资料】\n{source_lines}"
    return normalized


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
) -> str:
    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)
    module_matches = match_module_entries(query, effective_source_directory, max_matches=1)
    module_evidence: list[dict[str, str]] = []
    if module_matches:
        module_entry = module_matches[0]
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
