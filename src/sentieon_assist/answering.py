from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

from sentieon_assist.config import AppConfig, load_config
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.prompts import build_reference_prompt, build_support_prompt
from sentieon_assist.reference_intents import ReferenceIntent, parse_reference_intent
from sentieon_assist.rules import match_rule
from sentieon_assist.reference_resolution import resolve_reference_answer
from sentieon_assist.sources import collect_source_bundle_metadata, collect_source_evidence
from sentieon_assist.trace_vocab import ResolverPath


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


def format_capability_explanation_answer() -> str:
    return (
        "【能力说明】\n"
        "我可以帮你做这些 Sentieon 技术支持工作：\n"
        "- 入门导航：帮你判断 WGS/WES/panel、胚系/体细胞、短读长/长读长 该先看哪条流程。\n"
        "- 排障：帮你定位 license、安装、运行报错和常见格式/文件问题。\n"
        "- 资料/脚本查询：帮你查模块介绍、参数含义、输入输出和参考命令骨架。\n\n"
        "【建议下一步】\n"
        "- 直接告诉我你的目标或问题，例如：我要做 WES 分析该怎么选；license 报错原文是什么；DNAscope 是什么。"
    )


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


@dataclass(frozen=True)
class SupportAnswerTrace:
    text: str
    sources: list[str]
    boundary_tags: list[str]
    resolver_path: list[str]


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
    trace_collector=None,
) -> str:
    missing = missing_required_fields(issue_type, info)
    if missing:
        text = ask_for_missing(missing)
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=[],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_MISSING_INFO],
                )
            )
        return text

    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)

    if knowledge_directory is None:
        rule = match_rule(query)
    else:
        rule = match_rule(query, knowledge_directory)
    if rule:
        filtered_rule = filter_known_requirements(rule, info)
        rendered = normalize_model_answer(
            format_rule_answer(filtered_rule),
            query_version=info.get("version", ""),
            source_context=source_context,
        )
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=rendered,
                    sources=[],
                    boundary_tags=[],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_RULE],
                )
            )
        return rendered

    if issue_type == "other":
        text = "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=[],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_OTHER_UNSUPPORTED],
                )
            )
        return text

    evidence = collect_source_evidence(
        effective_source_directory,
        issue_type=issue_type,
        query=query,
        info=info,
    )

    if model_fallback is not None:
        text = call_model_fallback(model_fallback, issue_type, query, info, evidence)
        source_names = [item["name"] for item in evidence]
        rendered = normalize_model_answer(
            text,
            query_version=info.get("version", ""),
            source_context=source_context,
            sources=source_names,
        )
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=rendered,
                    sources=source_names,
                    boundary_tags=[],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_MODEL_FALLBACK],
                )
            )
        return rendered

    rendered = generate_model_fallback(
        issue_type,
        query,
        info,
        source_context=source_context,
        evidence=evidence,
        config=app_config,
    )
    if trace_collector is not None:
        trace_collector(
            SupportAnswerTrace(
                text=rendered,
                sources=[item["name"] for item in evidence],
                boundary_tags=[],
                resolver_path=[ResolverPath.TROUBLESHOOTING_GENERATED_FALLBACK],
            )
        )
    return rendered


def answer_reference_query(
    query: str,
    *,
    model_fallback=None,
    source_directory: str | None = None,
    parsed_intent: ReferenceIntent | None = None,
    trace_collector=None,
) -> str:
    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)
    resolved_intent = parsed_intent or ReferenceIntent()
    if resolved_intent.intent == "not_reference":
        resolved_intent = parse_reference_intent(query, config=app_config)
    resolved = resolve_reference_answer(
        query,
        source_directory=effective_source_directory,
        resolved_intent=resolved_intent,
    )
    rendered = format_reference_display(
        normalize_model_answer(
            resolved.text,
            source_context=source_context,
            sources=resolved.sources,
        )
    )
    if trace_collector is not None:
        trace_collector(
            SupportAnswerTrace(
                text=rendered,
                sources=list(resolved.sources),
                boundary_tags=list(resolved.boundary_tags),
                resolver_path=list(resolved.resolver_path),
            )
        )
    return rendered
