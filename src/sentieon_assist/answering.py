from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from typing import Any

from sentieon_assist.answer_contracts import (
    format_boundary_contract,
    format_knowledge_gap_answer,
    format_no_answer_boundary,
    format_unsupported_version_boundary,
)
from sentieon_assist.config import AppConfig, load_config
from sentieon_assist.gap_records import build_gap_record
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.prompts import build_reference_prompt, build_support_prompt
from sentieon_assist.reference_intents import ReferenceIntent, parse_reference_intent
from sentieon_assist.rules import match_rule
from sentieon_assist.reference_resolution import resolve_reference_answer
from sentieon_assist.runtime_outbound_trust import (
    build_reference_answer_outbound_trust,
    build_support_answer_outbound_trust,
)
from sentieon_assist.sources import collect_source_bundle_metadata, collect_source_evidence
from sentieon_assist.support_contracts import BoundaryOutcome
from sentieon_assist.trace_vocab import ResolverPath
from sentieon_assist.vendors import get_vendor_profile, resolve_vendor_id


REQUIRED_FIELDS = {
    "license": ("version", "error"),
    "install": ("version",),
}

def _join_lines(values: list[str]) -> str:
    if not values:
        return "- 无"
    return "\n".join(f"- {value}" for value in values)


def _get_vendor_profile(vendor_id: str | None = None):
    resolved_vendor_id = resolve_vendor_id(None) if vendor_id is None else str(vendor_id).strip().lower()
    return get_vendor_profile(resolved_vendor_id)


def _field_labels(vendor_id: str | None = None) -> dict[str, str]:
    return dict(_get_vendor_profile(vendor_id).runtime_wording.field_labels)


def _requirement_field_aliases(vendor_id: str | None = None) -> dict[str, str]:
    return dict(_get_vendor_profile(vendor_id).runtime_wording.requirement_field_aliases)


def _official_material_request(vendor_id: str | None = None, *, version_hint: str = "") -> str:
    profile = _get_vendor_profile(vendor_id)
    terms = " / ".join(
        str(term).strip() for term in profile.runtime_wording.official_material_terms if str(term).strip()
    ) or "官方资料"
    resolved_version = str(version_hint).strip()
    if resolved_version:
        return f"{profile.display_name} {resolved_version} 对应的 {terms}"
    return f"{profile.display_name} 对应版本的 {terms}"


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


def filter_known_requirements(rule: dict[str, Any], info: dict[str, str], *, vendor_id: str | None = None) -> dict[str, Any]:
    filtered_rule = dict(rule)
    aliases = _requirement_field_aliases(vendor_id)
    filtered_requires: list[str] = []
    for requirement in rule.get("requires", []):
        requirement_text = str(requirement).strip()
        field_name = aliases.get(requirement_text, "")
        if field_name and info.get(field_name, "").strip():
            continue
        filtered_requires.append(requirement_text)
    filtered_rule["requires"] = filtered_requires
    return filtered_rule


def missing_required_fields(issue_type: str, info: dict[str, str]) -> list[str]:
    return [field for field in REQUIRED_FIELDS.get(issue_type, ()) if not info.get(field, "").strip()]


def ask_for_missing(missing_fields: list[str], *, vendor_id: str | None = None) -> str:
    labels = [label for label in _missing_field_labels(missing_fields, vendor_id=vendor_id)]
    return f"需要补充以下信息：{', '.join(labels)}"


def _missing_field_labels(missing_fields: list[str], *, vendor_id: str | None = None) -> list[str]:
    field_labels = _field_labels(vendor_id)
    return [field_labels.get(field, field) for field in missing_fields]


def _clarification_round_limit(vendor_id: str) -> int:
    profile = get_vendor_profile(vendor_id)
    try:
        return max(0, int(profile.clarification_policy.get("max_rounds", 2)))
    except (TypeError, ValueError):
        return 2


def _extract_confirmation_materials(text: str) -> list[str]:
    lines = str(text).splitlines()
    materials: list[str] = []
    collecting = False
    for raw_line in lines:
        line = raw_line.strip()
        if line == "【需要确认的信息】":
            collecting = True
            continue
        if collecting and re.fullmatch(r"【[^】]+】", line):
            break
        if not collecting:
            continue
        if line.startswith("- "):
            materials.append(line[2:].strip())
    return [item for item in materials if item]


def format_capability_explanation_answer(vendor_id: str | None = None) -> str:
    profile = _get_vendor_profile(vendor_id)
    wording = profile.runtime_wording
    capability_lines = "\n".join(f"- {line}" for line in wording.capability_summary_lines)
    example_queries = "；".join(str(query).strip() for query in wording.capability_example_queries if str(query).strip())
    return (
        "【能力说明】\n"
        f"我可以帮你做这些 {profile.display_name} 技术支持工作：\n"
        f"{capability_lines}\n\n"
        "【建议下一步】\n"
        f"- 直接告诉我你的目标或问题，例如：{example_queries}。"
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
    outbound = build_support_answer_outbound_trust(
        issue_type=issue_type,
        query=query,
        info=info,
        source_context=source_context,
        evidence=evidence,
    )
    prompt = build_support_prompt(
        issue_type,
        outbound.query,
        outbound.info,
        source_context=outbound.source_context,
        evidence=list(outbound.evidence),
    )
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
    outbound = build_reference_answer_outbound_trust(
        query=query,
        source_context=source_context,
        evidence=evidence,
    )
    prompt = build_reference_prompt(
        outbound.query,
        source_context=outbound.source_context,
        evidence=list(outbound.evidence),
    )
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
    gap_record: dict[str, Any] | None = None
    trust_boundary_summary: dict[str, Any] | None = None


def _trace_gap_record(
    *,
    vendor_id: str,
    vendor_version: str,
    support_intent: str,
    gap_type: str,
    query: str,
    known_context: dict[str, str],
    missing_materials: list[str],
) -> dict[str, Any]:
    return build_gap_record(
        vendor_id=vendor_id,
        vendor_version=vendor_version,
        intent=support_intent,
        gap_type=gap_type,
        user_question=query,
        known_context=known_context,
        missing_materials=missing_materials,
    )


def _format_arbitration_boundary(
    *,
    action: str,
    vendor_id: str,
    vendor_version: str,
    reason: str,
    info: dict[str, str],
) -> str:
    resolved_reason = str(reason).strip()
    if action == BoundaryOutcome.MUST_TOOL:
        return format_boundary_contract(
            summary_lines=[
                resolved_reason or "这个问题属于文件结构或一致性检查。",
                "必须先跑确定性检查，再解释结果，不能只靠模型推断。",
            ],
            next_steps=[
                "先运行对应的 header / 索引 / contig / 排序一致性检查。",
                "拿到工具输出后，再继续定位。",
            ],
            needed_materials=[
                info.get("input_type", "").strip() or "相关输入文件类型",
                info.get("error", "").strip() or "完整报错或检查输出",
                info.get("step", "").strip() or "实际执行步骤",
            ],
        )
    if action == BoundaryOutcome.MUST_REFUSE:
        return format_boundary_contract(
            summary_lines=[
                resolved_reason or "该请求超出当前软件支持边界。",
                "当前不能在没有证据约束的前提下直接给出确定性结论。",
            ],
            next_steps=[
                "请改为当前软件支持边界内的问题，或补充正式证据材料。",
            ],
            needed_materials=[
                _official_material_request(vendor_id, version_hint=vendor_version or "目标版本"),
            ],
        )
    if action == BoundaryOutcome.MUST_ESCALATE:
        return format_boundary_contract(
            summary_lines=[
                resolved_reason or "该问题需要升级处理。",
                "当前不应在本地直接给出最终结论。",
            ],
            next_steps=[
                "请转给维护者或原厂支持链路，并附上当前已知证据。",
            ],
            needed_materials=[
                _official_material_request(vendor_id, version_hint=vendor_version or "目标版本"),
                info.get("error", "").strip() or "完整报错或现场证据",
            ],
        )
    return format_knowledge_gap_answer(
        [resolved_reason or "还需要先明确关键上下文"],
        vendor_id=vendor_id,
        vendor_version=vendor_version,
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
    route_decision=None,
    clarification_rounds: int = 0,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    trace_collector=None,
) -> str:
    vendor_id = resolve_vendor_id(getattr(route_decision, "vendor_id", None))
    vendor_version = str(getattr(route_decision, "vendor_version", "")).strip()
    support_intent = str(getattr(route_decision, "support_intent", "troubleshooting")).strip() or "troubleshooting"
    known_context = {key: value for key, value in info.items() if str(value).strip()}
    if route_decision is not None and str(getattr(route_decision, "fallback_mode", "")).strip() == "unsupported-version":
        text = format_unsupported_version_boundary(
            vendor_id=vendor_id,
            requested_version=vendor_version,
        )
        gap_record = _trace_gap_record(
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            support_intent=support_intent,
            gap_type="unsupported_version",
            query=query,
            known_context={"query_version": vendor_version, **known_context},
            missing_materials=[_official_material_request(vendor_id, version_hint=vendor_version or "目标版本")],
        )
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=["unsupported-version"],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_UNSUPPORTED_VERSION],
                    gap_record=gap_record,
                )
            )
        return text

    missing = missing_required_fields(issue_type, info)
    if missing:
        missing_labels = _missing_field_labels(missing, vendor_id=vendor_id)
        gap_record = _trace_gap_record(
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            support_intent=support_intent,
            gap_type="clarification_open",
            query=query,
            known_context=known_context,
            missing_materials=missing_labels,
        )
        if clarification_rounds >= _clarification_round_limit(vendor_id):
            text = format_no_answer_boundary(
                vendor_id=vendor_id,
                vendor_version=vendor_version,
                missing_labels=missing_labels,
                reason="连续补问后仍缺少关键上下文。",
            )
            if trace_collector is not None:
                trace_collector(
                    SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=["clarify-limit"],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_CLARIFY_LIMIT],
                    gap_record=gap_record,
                )
            )
            return text
        text = format_knowledge_gap_answer(
            missing_labels,
            vendor_id=vendor_id,
            vendor_version=vendor_version,
        )
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=[],
                    resolver_path=[ResolverPath.TROUBLESHOOTING_KNOWLEDGE_GAP],
                    gap_record=gap_record,
                )
            )
        return text

    arbitration_action = str(getattr(route_decision, "arbitration_action", "")).strip()
    if arbitration_action in {
        BoundaryOutcome.MUST_CLARIFY,
        BoundaryOutcome.MUST_TOOL,
        BoundaryOutcome.MUST_REFUSE,
        BoundaryOutcome.MUST_ESCALATE,
    }:
        text = _format_arbitration_boundary(
            action=arbitration_action,
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            reason=str(getattr(route_decision, "boundary_reason", "")).strip(),
            info=info,
        )
        resolver_path = {
            BoundaryOutcome.MUST_CLARIFY: ResolverPath.ARBITRATION_MUST_CLARIFY,
            BoundaryOutcome.MUST_TOOL: ResolverPath.ARBITRATION_MUST_TOOL,
            BoundaryOutcome.MUST_REFUSE: ResolverPath.ARBITRATION_MUST_REFUSE,
            BoundaryOutcome.MUST_ESCALATE: ResolverPath.ARBITRATION_MUST_ESCALATE,
        }[arbitration_action]
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=text,
                    sources=[],
                    boundary_tags=[arbitration_action.replace("_", "-")],
                    resolver_path=[resolver_path],
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
        filtered_rule = filter_known_requirements(rule, info, vendor_id=vendor_id)
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
        outbound = build_support_answer_outbound_trust(
            issue_type=issue_type,
            query=query,
            info=info,
            evidence=evidence,
        )
        text = call_model_fallback(
            model_fallback,
            issue_type,
            outbound.query,
            outbound.info,
            list(outbound.evidence),
        )
        source_names = [item["name"] for item in (list(outbound.evidence) or evidence)]
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
                    trust_boundary_summary=outbound.trust_boundary_result.summary,
                )
            )
        return rendered

    outbound = build_support_answer_outbound_trust(
        issue_type=issue_type,
        query=query,
        info=info,
        source_context=source_context,
        evidence=evidence,
    )
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
                trust_boundary_summary=outbound.trust_boundary_result.summary,
            )
        )
    return rendered


def answer_reference_query(
    query: str,
    *,
    route_decision=None,
    clarification_rounds: int = 0,
    model_fallback=None,
    source_directory: str | None = None,
    parsed_intent: ReferenceIntent | None = None,
    trace_collector=None,
) -> str:
    vendor_id = resolve_vendor_id(getattr(route_decision, "vendor_id", None))
    vendor_version = str(getattr(route_decision, "vendor_version", "")).strip()
    if route_decision is not None and str(getattr(route_decision, "fallback_mode", "")).strip() == "unsupported-version":
        support_intent = str(getattr(route_decision, "support_intent", "concept_understanding")).strip() or "concept_understanding"
        rendered = format_unsupported_version_boundary(
            vendor_id=vendor_id,
            requested_version=vendor_version,
        )
        gap_record = _trace_gap_record(
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            support_intent=support_intent,
            gap_type="unsupported_version",
            query=query,
            known_context={"query_version": vendor_version},
            missing_materials=[_official_material_request(vendor_id, version_hint=vendor_version or "目标版本")],
        )
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=rendered,
                    sources=[],
                    boundary_tags=["unsupported-version"],
                    resolver_path=[ResolverPath.REFERENCE_UNSUPPORTED_VERSION],
                    gap_record=gap_record,
                )
            )
        return rendered

    app_config = load_config()
    effective_source_directory = source_directory or app_config.source_dir
    source_context = collect_source_bundle_metadata(effective_source_directory)
    resolved_intent = parsed_intent or ReferenceIntent()
    if resolved_intent.intent == "not_reference":
        resolved_intent = parse_reference_intent(query, config=app_config)
    arbitration_action = str(getattr(route_decision, "arbitration_action", "")).strip()
    if arbitration_action in {
        BoundaryOutcome.MUST_CLARIFY,
        BoundaryOutcome.MUST_TOOL,
        BoundaryOutcome.MUST_REFUSE,
        BoundaryOutcome.MUST_ESCALATE,
    }:
        rendered = _format_arbitration_boundary(
            action=arbitration_action,
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            reason=str(getattr(route_decision, "boundary_reason", "")).strip(),
            info=getattr(route_decision, "info", {}) or {},
        )
        resolver_path = {
            BoundaryOutcome.MUST_CLARIFY: ResolverPath.ARBITRATION_MUST_CLARIFY,
            BoundaryOutcome.MUST_TOOL: ResolverPath.ARBITRATION_MUST_TOOL,
            BoundaryOutcome.MUST_REFUSE: ResolverPath.ARBITRATION_MUST_REFUSE,
            BoundaryOutcome.MUST_ESCALATE: ResolverPath.ARBITRATION_MUST_ESCALATE,
        }[arbitration_action]
        if trace_collector is not None:
            trace_collector(
                SupportAnswerTrace(
                    text=rendered,
                    sources=[],
                    boundary_tags=[arbitration_action.replace("_", "-")],
                    resolver_path=[resolver_path],
                )
            )
        return rendered
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
    support_intent = str(getattr(route_decision, "support_intent", "concept_understanding")).strip() or "concept_understanding"
    confirmation_materials = _extract_confirmation_materials(rendered)
    gap_record = None
    boundary_tags = list(resolved.boundary_tags)
    resolver_path = list(resolved.resolver_path)
    if confirmation_materials:
        gap_record = _trace_gap_record(
            vendor_id=vendor_id,
            vendor_version=vendor_version,
            support_intent=support_intent,
            gap_type="clarification_open",
            query=query,
            known_context={},
            missing_materials=confirmation_materials,
        )
        if clarification_rounds >= _clarification_round_limit(vendor_id):
            rendered = format_no_answer_boundary(
                vendor_id=vendor_id,
                vendor_version=vendor_version,
                missing_labels=confirmation_materials,
                reason="连续补问后仍缺少关键上下文。",
            )
            boundary_tags = ["clarify-limit"]
            resolver_path = [ResolverPath.BOUNDARY_REFERENCE]
    if trace_collector is not None:
        trace_collector(
            SupportAnswerTrace(
                text=rendered,
                sources=list(resolved.sources),
                boundary_tags=boundary_tags,
                resolver_path=resolver_path,
                gap_record=gap_record,
            )
        )
    return rendered
