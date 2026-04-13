from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sentieon_assist.config import AppConfig, load_config
from sentieon_assist.external_guides import is_external_reference_query
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.reference_boundaries import detect_reference_boundary_tags
from sentieon_assist.runtime_outbound_trust import build_reference_intent_outbound_request
from sentieon_assist.support_contracts import ToolRequirement, normalize_tool_requirement


VALID_REFERENCE_INTENTS = {
    "module_overview",
    "module_intro",
    "workflow_guidance",
    "parameter_lookup",
    "script_example",
    "reference_other",
    "not_reference",
}

INTENT_ALIASES = {
    "modules_overview": "module_overview",
    "module_list": "module_overview",
    "overview": "module_overview",
    "module_detail": "module_intro",
    "workflow": "workflow_guidance",
    "workflow_guide": "workflow_guidance",
    "workflow_guidance": "workflow_guidance",
    "parameter": "parameter_lookup",
    "param_lookup": "parameter_lookup",
    "script": "script_example",
    "example_script": "script_example",
    "reference": "reference_other",
    "other_reference": "reference_other",
}

MODULE_HINTS = (
    ("geneeditevaluator", "GeneEditEvaluator"),
    ("gene edit", "GeneEditEvaluator"),
    ("geneedit", "GeneEditEvaluator"),
    ("dnascope hybrid", "DNAscope Hybrid"),
    ("hybrid", "DNAscope Hybrid"),
    ("dnascope long read", "DNAscope LongRead"),
    ("dnascope longread", "DNAscope LongRead"),
    ("joint call", "Joint Call"),
    ("gvcftyper", "GVCFtyper"),
    ("rnaseq", "RNAseq"),
    ("dnascope", "DNAscope"),
    ("tnscope", "TNscope"),
    ("sentieon-cli", "sentieon-cli"),
    ("sentieon cli", "sentieon-cli"),
    ("sentieon driver", "sentieon-cli"),
)
SCRIPT_HEURISTIC_MODULES = {
    "GeneEditEvaluator",
    "RNAseq",
    "DNAscope",
    "DNAscope LongRead",
    "DNAscope Hybrid",
    "TNscope",
    "Joint Call",
    "GVCFtyper",
    "sentieon-cli",
}
PARAMETER_TOKEN_PATTERN = re.compile(r"(?<!\w)-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*")


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class ReferenceIntent:
    intent: str = "not_reference"
    module: str = ""
    confidence: float = 0.0
    tool_requirement: str = ToolRequirement.NONE

    @property
    def is_reference(self) -> bool:
        return self.intent != "not_reference"


TOOL_REQUIRED_FILE_TERMS = (
    "vcf",
    "bam",
    "cram",
    "bed",
    "fasta",
    "fastq",
    "contig",
    "header",
    "index",
    "dictionary",
    "dict",
    "fai",
    "crai",
    "tabix",
)
TOOL_REQUIRED_DIAGNOSTIC_TERMS = (
    "报错",
    "错误",
    "not found",
    "missing",
    "mismatch",
    "inconsistent",
    "不一致",
    "sort",
    "排序",
    "header",
    "contig",
    "index",
    "read group",
    "随机访问",
    "差一位",
    "对不上",
)
TOOL_REQUIRED_STRUCTURE_TERMS = (
    "contig",
    "header",
    "index",
    "dictionary",
    "dict",
    "fai",
    "crai",
    "tabix",
    "sort",
    "sorted",
    "随机访问",
    "差一位",
    "偏一位",
    "off by one",
)
OPTION_SCOPE_ERROR_TERMS = (
    "unrecognized option",
    "unknown option",
    "invalid option",
    "不认识这个参数",
    "不支持这个参数",
    "参数无效",
)


def _normalize_intent(value: str) -> str:
    normalized = str(value).strip().lower()
    normalized = INTENT_ALIASES.get(normalized, normalized)
    if normalized in VALID_REFERENCE_INTENTS:
        return normalized
    return "not_reference"


def _normalize_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _merge_tool_requirement(primary: str | None, secondary: str | None) -> str:
    if _safe_tool_requirement(primary) == ToolRequirement.REQUIRED:
        return ToolRequirement.REQUIRED
    return _safe_tool_requirement(secondary)


def _safe_tool_requirement(value: object) -> str:
    try:
        return normalize_tool_requirement(value)
    except ValueError:
        return ToolRequirement.NONE


def _detect_tool_requirement(query: str) -> str:
    normalized = query.lower()
    if any(term in normalized for term in OPTION_SCOPE_ERROR_TERMS) and PARAMETER_TOKEN_PATTERN.search(query):
        return ToolRequirement.NONE
    if any(term in normalized for term in TOOL_REQUIRED_FILE_TERMS) and any(
        term in normalized for term in TOOL_REQUIRED_DIAGNOSTIC_TERMS
    ) and any(
        term in normalized for term in TOOL_REQUIRED_STRUCTURE_TERMS
    ):
        return ToolRequirement.REQUIRED
    return ToolRequirement.NONE


def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def detect_reference_module_hint(query: str) -> str:
    normalized = query.lower()
    collapsed = _collapse_whitespace(normalized)
    compact = re.sub(r"\s+", "", normalized)
    for needle, canonical in MODULE_HINTS:
        normalized_needle = needle.lower()
        if (
            normalized_needle in normalized
            or normalized_needle in collapsed
            or normalized_needle.replace(" ", "") in compact
        ):
            return canonical
    return ""


def _looks_like_operational_doc_reference(query: str) -> bool:
    normalized = query.lower()
    if ("核心" in query or "cpu" in normalized) and any(cue in normalized for cue in ("占用", "资源", "线程", "thread")):
        return True
    if any(cue in normalized for cue in ("gpu", "fpga", "nvidia", "arm", "graviton")):
        return True
    if "sentieon driver" in normalized and "sentieon-cli" in normalized:
        return True
    if any(cue in normalized for cue in ("joint call", "gvcftyper", ".g.vcf", "g.vcf")) and "-v" in normalized:
        return True
    if "tnscope" in normalized and "tumor-only" in normalized and any(
        cue in normalized for cue in ("tumor-normal", "tumor normal", "matched normal")
    ):
        return True
    return False


def _looks_like_license_doc_reference(query: str) -> bool:
    normalized = query.lower()
    return any(cue in normalized for cue in ("licclnt", "licsrvr")) and any(
        cue in query for cue in ("哪个", "哪条", "工具", "binary", "命令")
    )


def _has_parameter_language(normalized: str) -> bool:
    if "参数" in normalized or "flag" in normalized or "option" in normalized:
        return True
    if "选项" in normalized and "候选项" not in normalized:
        return True
    return False


def _heuristic_reference_intent(query: str) -> ReferenceIntent:
    normalized = query.lower()
    module = detect_reference_module_hint(query)
    tool_requirement = _detect_tool_requirement(query)
    has_parameter_cue = bool(PARAMETER_TOKEN_PATTERN.search(query)) or _has_parameter_language(normalized)
    strong_script_cues = ("脚本", "示例脚本", "参考脚本", "示例命令", "参考命令", "命令骨架", "skeleton")
    hybrid_followup_terms = (
        "hybrid",
        "联合分析",
        "short-read + long-read",
        "short-read+long-read",
        "short read + long read",
        "短读长 + 长读长",
        "短读长+长读长",
    )
    hybrid_parent_context_terms = (
        "wgs",
        "whole genome",
        "全基因组",
        "wes",
        "whole exome",
        "全外显子",
        "exome",
        "panel",
        "long-read",
        "long read",
        "长读长",
        "short-read",
        "short read",
        "短读长",
    )
    workflow_guidance_domains = (
        "wgs",
        "wes",
        "whole exome",
        "全外显子",
        "exome",
        "panel",
        "rna",
        "rna-seq",
        "短读长",
        "short-read",
        "short read",
        "whole genome",
        "全基因组",
        "germline",
        "胚系",
        "somatic",
        "体细胞",
        "tumor-normal",
        "tumor normal",
        "tumor-only",
        "tumor only",
        "肿瘤",
        "long-read",
        "long read",
        "长读长",
        "pacbio",
        "hifi",
        "ont",
        "nanopore",
        "pangenome",
        "graph",
        "diploid",
        "二倍体",
        "polyploid",
        "多倍体",
        "多倍",
        "non-diploid",
        "非二倍体",
    )
    workflow_guidance_cues = (
        "指导",
        "怎么做",
        "怎么选",
        "选哪个",
        "看哪个",
        "路线",
        "分流",
        "workflow",
        "pipeline",
        "流程",
        "分析",
    )
    has_strong_script_cue = any(cue in query for cue in strong_script_cues)
    has_hybrid_followup_term = any(term in normalized for term in hybrid_followup_terms)
    has_hybrid_parent_context = any(term in normalized for term in hybrid_parent_context_terms)
    if has_hybrid_followup_term and has_hybrid_parent_context:
        return ReferenceIntent(intent="workflow_guidance", module=module, confidence=0.47, tool_requirement=tool_requirement)
    has_workflow_domain = any(term in normalized for term in workflow_guidance_domains)
    has_workflow_guidance_cue = any(cue in normalized for cue in workflow_guidance_cues)
    if has_workflow_domain and not module:
        if has_workflow_guidance_cue or has_strong_script_cue:
            return ReferenceIntent(intent="workflow_guidance", confidence=0.45, tool_requirement=tool_requirement)
    if _looks_like_license_doc_reference(query) or _looks_like_operational_doc_reference(query):
        return ReferenceIntent(intent="reference_other", module=module, confidence=0.41, tool_requirement=tool_requirement)
    boundary_tags = detect_reference_boundary_tags(query)
    if boundary_tags:
        if module and has_parameter_cue:
            return ReferenceIntent(intent="parameter_lookup", module=module, confidence=0.42, tool_requirement=tool_requirement)
        return ReferenceIntent(intent="reference_other", module=module, confidence=0.41, tool_requirement=tool_requirement)
    if any(cue in query for cue in ("脚本", "示例", "命令", "workflow", "pipeline")):
        if module in SCRIPT_HEURISTIC_MODULES:
            return ReferenceIntent(intent="script_example", module=module, confidence=0.4, tool_requirement=tool_requirement)
    if has_parameter_cue:
        if module or PARAMETER_TOKEN_PATTERN.search(query):
            return ReferenceIntent(intent="parameter_lookup", module=module, confidence=0.38, tool_requirement=tool_requirement)
    if not module and is_external_reference_query(query):
        return ReferenceIntent(intent="reference_other", confidence=0.33, tool_requirement=tool_requirement)
    if "模块" in query and any(cue in query for cue in ("哪些", "有什么", "总览", "主要", "分类")):
        if "sentieon" in normalized or "sengent" in normalized or "模块" in query:
            return ReferenceIntent(intent="module_overview", confidence=0.35, tool_requirement=tool_requirement)
    return ReferenceIntent(tool_requirement=tool_requirement)


def _merge_with_heuristic(query: str, parsed: ReferenceIntent) -> ReferenceIntent:
    heuristic = _heuristic_reference_intent(query)
    if heuristic.intent == "not_reference":
        return ReferenceIntent(
            intent=parsed.intent,
            module=parsed.module,
            confidence=parsed.confidence,
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    if heuristic.intent == parsed.intent:
        return ReferenceIntent(
            intent=parsed.intent,
            module=parsed.module or heuristic.module,
            confidence=max(parsed.confidence, heuristic.confidence),
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    if heuristic.intent == "parameter_lookup" and parsed.intent in {"module_intro", "reference_other", "not_reference"}:
        return ReferenceIntent(
            intent="parameter_lookup",
            module=parsed.module or heuristic.module,
            confidence=max(parsed.confidence, heuristic.confidence),
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    if heuristic.intent == "script_example" and parsed.intent in {"module_intro", "reference_other", "not_reference"}:
        return ReferenceIntent(
            intent="script_example",
            module=parsed.module or heuristic.module,
            confidence=max(parsed.confidence, heuristic.confidence),
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    if heuristic.intent == "workflow_guidance" and parsed.intent in {
        "module_intro",
        "reference_other",
        "not_reference",
    }:
        return ReferenceIntent(
            intent="workflow_guidance",
            module=parsed.module or heuristic.module,
            confidence=max(parsed.confidence, heuristic.confidence),
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    if heuristic.intent == "module_overview" and parsed.intent in {"module_intro", "reference_other", "not_reference"}:
        return ReferenceIntent(
            intent="module_overview",
            module=parsed.module or heuristic.module,
            confidence=max(parsed.confidence, heuristic.confidence),
            tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
        )
    return ReferenceIntent(
        intent=parsed.intent,
        module=parsed.module,
        confidence=parsed.confidence,
        tool_requirement=_merge_tool_requirement(parsed.tool_requirement, heuristic.tool_requirement),
    )


def parse_reference_intent(
    query: str,
    *,
    model_generate=None,
    config: AppConfig | None = None,
) -> ReferenceIntent:
    heuristic = _heuristic_reference_intent(query)
    if heuristic.intent in {"workflow_guidance", "parameter_lookup", "reference_other"}:
        return heuristic
    if heuristic.intent == "script_example" and heuristic.module:
        return heuristic

    app_config = config or load_config()
    outbound = build_reference_intent_outbound_request(query=query)
    try:
        if model_generate is not None:
            raw = model_generate(outbound.prompt)
        else:
            raw = build_backend_router(app_config).generate(outbound)
    except RuntimeError:
        return heuristic

    payload = _extract_first_json_object(str(raw))
    if not payload:
        return heuristic
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return heuristic
    if not isinstance(parsed, dict):
        return heuristic
    parsed_intent = ReferenceIntent(
        intent=_normalize_intent(parsed.get("intent", "")),
        module=str(parsed.get("module", "")).strip(),
        confidence=_normalize_confidence(parsed.get("confidence", 0.0)),
        tool_requirement=_safe_tool_requirement(parsed.get("tool_requirement", ToolRequirement.NONE)),
    )
    return _merge_with_heuristic(query, parsed_intent)
