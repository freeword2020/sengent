from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.external_guides import is_external_error_query, is_external_reference_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.reference_intents import ReferenceIntent, detect_reference_module_hint, parse_reference_intent
from sentieon_assist.support_state import SupportSessionState, SupportTask

FIELD_SLOT_LABELS = {
    "version": "Sentieon 版本",
    "error": "完整报错信息",
    "input_type": "输入文件类型",
    "data_type": "数据类型",
    "step": "执行步骤",
}
CAPABILITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"你(?:能|可以)做什么"),
    re.compile(r"你有(?:什么|哪些)功能"),
    re.compile(r"你有(?:什么|哪些)能力"),
    re.compile(r"可以帮我做什么"),
    re.compile(r"能帮我做什么"),
    re.compile(r"你(?:能|可以)为我做些说明"),
    re.compile(r"你不是可以提供.*功能"),
    re.compile(r"你(?:能|可以)提供.*功能"),
    re.compile(r"你支持什么"),
    re.compile(r"你支持哪些"),
)
GENERIC_MODULE_INTRO_CUES = ("介绍", "是什么", "做什么", "功能", "作用")
GENERAL_MODULE_QUERY_CUES = GENERIC_MODULE_INTRO_CUES + (
    "如何",
    "怎么",
    "为什么",
    "区别",
    "差异",
    "是否",
    "能否",
    "支持",
    "兼容",
    "哪些",
    "哪几类",
    "从哪里下载",
)
OPERATIONAL_REFERENCE_CUES = (
    "licsrvr",
    "licclnt",
    "sdist",
    "poetry",
    "sentieon-cli",
    "sentieon cli",
    "sentieon driver",
    "driver",
    "graviton",
    "arm",
    "gpu",
    "fpga",
)
ERROR_REPORT_CUES = (
    "报错",
    "错误",
    "失败",
    "异常",
    "无法",
    "不能",
    "不行",
    "killed",
    "too many open files",
    "permission denied",
    "not found",
    "找不到",
)
NON_MODULE_ASCII_TOKENS = {
    "agilent",
    "arm",
    "cpu",
    "fpga",
    "sentieon",
    "gpu",
    "graviton",
    "illumina",
    "license",
    "install",
    "fastq",
    "bam",
    "cram",
    "mgi",
    "nvidia",
    "pcr",
    "pcr-free",
    "vcf",
    "sureselect",
    "wes",
    "wgs",
    "panel",
    "rna",
    "workflow",
    "pipeline",
    "shell",
    "bash",
}
DEICTIC_REFERENCE_FOLLOWUP_PATTERN = re.compile(
    r"^(?:这个|那个|那这个|这条|那条|这一条|那一条)(?:模块|流程|方向|方案)?(?:呢|怎么样|咋样|如何)?$"
)
TERSE_REFERENCE_FOLLOWUP_CUES = (
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
    "示例脚本也可以",
    "脚本呢",
    "参数呢",
    "输入呢",
    "输出呢",
)
WORKFLOW_FACT_FRAGMENT_TOKENS = (
    "短读长",
    "长读长",
    "胚系",
    "体细胞",
    "二倍体",
    "非二倍体",
    "多倍体",
    "多倍",
    "polyploid",
    "non-diploid",
    "hifi",
    "ont",
    "pacbio",
    "nanopore",
    "fastq",
    "bam",
    "cram",
    "tumor-only",
    "tumor only",
    "tumor-normal",
    "tumor normal",
    "joint call",
    "wes",
    "wgs",
    "panel",
)
STANDALONE_REQUEST_CUES = (
    "能提供",
    "提供个",
    "给个",
    "介绍",
    "是什么",
    "做什么",
    "参数",
    "脚本",
    "命令",
    "为什么",
    "如何",
    "怎么",
    "支持",
    "区别",
    "分析",
)
REFERENCE_FOLLOWUP_CANONICAL_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:配对|有对照|有matchednormal|matchednormal|tumor[- ]normal|肿瘤配对|肿瘤对照)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 tumor-normal 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:无对照|没对照|没有对照|无matchednormal|tumor[- ]only|单肿瘤|单样本肿瘤)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 tumor-only 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:体细胞(?:的)?|somatic|肿瘤(?:的)?)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 somatic 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:胚系(?:的)?|germline)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 germline 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:hybrid|联合分析|short[- ]read\s*\+\s*long[- ]read|short\s+read\s*\+\s*long\s+read|短读长\s*\+\s*长读长)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 hybrid 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:短读长|short[- ]read)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 short-read 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:长读长|long[- ]read)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 long-read 呢",
    ),
)
REFERENCE_RESPONSE_PREFIXES = (
    "【资料查询】",
    "【模块介绍】",
    "【常用参数】",
    "【流程指导】",
    "【资料说明】",
    "【参考命令】",
)
WORKFLOW_SLOT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("analysis_mode", ("胚系还是体细胞", "胚系还是体细胞？")),
    ("ploidy", ("二倍体", "diploid organism")),
    ("input_type", ("FASTQ、uBAM/uCRAM", "已对齐 BAM/CRAM", "FASTQ、uBAM/uCRAM，还是已对齐 BAM/CRAM")),
    ("request_kind", ("流程分流", "参考命令骨架")),
)


@dataclass(frozen=True)
class SupportRouteDecision:
    task: SupportTask
    issue_type: str
    parsed_intent: ReferenceIntent
    info: dict[str, str]
    reason: str
    explicit: bool = False


@dataclass(frozen=True)
class PlannedSupportTurn:
    raw_query: str
    effective_query: str
    route: SupportRouteDecision
    reused_anchor: bool = False


def is_capability_question(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    if any(pattern.search(normalized) for pattern in CAPABILITY_PATTERNS):
        if extract_explicit_module_candidate(query):
            return False
        return True
    return normalized in {"介绍一下你自己", "介绍下你自己", "你是谁", "能做哪些支持"}


def extract_explicit_module_candidate(query: str) -> str:
    hinted_module = detect_reference_module_hint(query)
    if hinted_module:
        return hinted_module
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query):
        lowered = token.lower()
        if lowered in NON_MODULE_ASCII_TOKENS:
            continue
        if any(char.isupper() for char in token[1:]) or token[0].isupper():
            return token
    return ""


def normalize_reference_followup_fragment(query: str) -> str:
    stripped = query.strip()
    normalized_compact = re.sub(r"\s+", "", stripped.lower())
    for pattern, replacement in REFERENCE_FOLLOWUP_CANONICAL_RULES:
        if pattern.search(normalized_compact):
            return replacement
    return stripped


def _looks_like_error_report(query: str) -> bool:
    normalized = query.lower()
    return any(cue in normalized for cue in ERROR_REPORT_CUES)


def _looks_like_operational_reference_query(query: str) -> bool:
    normalized = query.lower()
    return any(cue in normalized for cue in OPERATIONAL_REFERENCE_CUES)


def looks_like_reference_followup(
    query: str,
    *,
    model_generate: Callable[..., str] | None = None,
    parse_reference_intent_fn: Callable[..., ReferenceIntent] = parse_reference_intent,
) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    normalized_compact = re.sub(r"\s+", "", normalized)
    if is_capability_question(query):
        return False
    if DEICTIC_REFERENCE_FOLLOWUP_PATTERN.fullmatch(normalized_compact):
        return False
    if any(pattern.search(normalized_compact) for pattern, _replacement in REFERENCE_FOLLOWUP_CANONICAL_RULES):
        return True
    if any(normalized_compact.endswith(cue) for cue in TERSE_REFERENCE_FOLLOWUP_CUES):
        return True
    if "--" in normalized and not any(cue in normalized for cue in STANDALONE_REQUEST_CUES):
        return True
    if (
        len(normalized_compact) <= 20
        and any(token in normalized for token in WORKFLOW_FACT_FRAGMENT_TOKENS)
        and not any(cue in normalized for cue in STANDALONE_REQUEST_CUES)
    ):
        return True
    return False


def looks_like_clarification_answer_fragment(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    normalized_compact = re.sub(r"\s+", "", normalized)
    if any(cue in normalized for cue in STANDALONE_REQUEST_CUES):
        return False
    if len(normalized_compact) <= 20 and any(token in normalized for token in WORKFLOW_FACT_FRAGMENT_TOKENS):
        return True
    return False


def looks_like_module_disambiguation_fragment(query: str) -> bool:
    stripped = query.strip()
    normalized = stripped.lower()
    if not stripped:
        return False
    if any(separator in stripped for separator in ("、", ",", "，", "/")):
        return False
    if any(cue in normalized for cue in STANDALONE_REQUEST_CUES):
        return False
    if extract_explicit_module_candidate(stripped):
        return True
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9 _+.-]{1,40}", stripped))


def response_requires_followup(response: str) -> bool:
    return response.startswith("需要补充以下信息") or response.startswith("需要确认模块")


def response_supports_reference_context(response: str) -> bool:
    return response.startswith(REFERENCE_RESPONSE_PREFIXES)


def select_support_route(
    query: str,
    *,
    model_generate: Callable[..., str] | None = None,
    classify_query_fn: Callable[[str], str] = classify_query,
    parse_reference_intent_fn: Callable[..., ReferenceIntent] = parse_reference_intent,
    is_reference_query_fn: Callable[[str], bool] = is_reference_query,
    extract_info_fn: Callable[[str], dict[str, str]] = extract_info_from_query,
    is_external_error_query_fn: Callable[[str, dict[str, str] | None], bool] = is_external_error_query,
) -> SupportRouteDecision:
    info = extract_info_fn(query)
    issue_type = classify_query_fn(query)
    explicit_module = extract_explicit_module_candidate(query)
    parsed_intent = parse_reference_intent_fn(query, model_generate=model_generate)
    if is_capability_question(query):
        return SupportRouteDecision(
            task="capability_explanation",
            issue_type=issue_type,
            parsed_intent=ReferenceIntent(),
            info=info,
            reason="capability_question",
            explicit=True,
        )
    if issue_type in {"license", "install"} and (
        parsed_intent.is_reference or (_looks_like_operational_reference_query(query) and not _looks_like_error_report(query))
    ):
        if explicit_module and any(cue in query.lower() for cue in GENERAL_MODULE_QUERY_CUES):
            parsed_intent = ReferenceIntent(intent="module_intro", module=explicit_module, confidence=max(parsed_intent.confidence, 0.44))
        elif not parsed_intent.is_reference:
            parsed_intent = ReferenceIntent(intent="reference_other", confidence=0.41)
        return SupportRouteDecision(
            task="reference_lookup",
            issue_type=issue_type,
            parsed_intent=parsed_intent,
            info=info,
            reason=parsed_intent.intent or f"{issue_type}_reference_lookup",
            explicit=True,
        )
    if issue_type != "other":
        return SupportRouteDecision(
            task="troubleshooting",
            issue_type=issue_type,
            parsed_intent=ReferenceIntent(),
            info=info,
            reason=f"issue_type:{issue_type}",
            explicit=True,
        )
    if explicit_module and any(cue in query.lower() for cue in GENERAL_MODULE_QUERY_CUES) and not is_external_reference_query(query):
        if parsed_intent.intent == "reference_other":
            return SupportRouteDecision(
                task="reference_lookup",
                issue_type=issue_type,
                parsed_intent=parsed_intent,
                info=info,
                reason=parsed_intent.intent,
                explicit=True,
            )
        explicit_intent = "module_intro"
        if re.search(r"(?<!\w)-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*", query) or any(
            cue in query.lower() for cue in ("参数", "选项", "flag", "option")
        ):
            explicit_intent = "parameter_lookup"
        elif any(cue in query.lower() for cue in ("脚本", "示例", "命令", "workflow", "pipeline")):
            explicit_intent = "script_example"
        return SupportRouteDecision(
            task="reference_lookup",
            issue_type=issue_type,
            parsed_intent=ReferenceIntent(intent=explicit_intent, module=explicit_module, confidence=0.42),
            info=info,
            reason=explicit_intent,
            explicit=True,
        )
    if is_external_error_query_fn(query, info):
        if not parsed_intent.is_reference:
            parsed_intent = ReferenceIntent(intent="reference_other", confidence=0.5)
        return SupportRouteDecision(
            task="troubleshooting",
            issue_type=issue_type,
            parsed_intent=parsed_intent,
            info=info,
            reason="external_error_query",
            explicit=True,
        )
    if parsed_intent.intent == "workflow_guidance":
        return SupportRouteDecision(
            task="onboarding_guidance",
            issue_type=issue_type,
            parsed_intent=parsed_intent,
            info=info,
            reason="workflow_guidance",
            explicit=True,
        )
    if parsed_intent.is_reference or is_reference_query_fn(query):
        return SupportRouteDecision(
            task="reference_lookup",
            issue_type=issue_type,
            parsed_intent=parsed_intent,
            info=info,
            reason=parsed_intent.intent or "reference_query",
            explicit=True,
        )
    return SupportRouteDecision(
        task="capability_explanation",
        issue_type=issue_type,
        parsed_intent=ReferenceIntent(),
        info=info,
        reason="ambiguous_support_request",
        explicit=False,
    )


def plan_support_turn(
    query: str,
    state: SupportSessionState,
    *,
    model_generate: Callable[..., str] | None = None,
    classify_query_fn: Callable[[str], str] = classify_query,
    parse_reference_intent_fn: Callable[..., ReferenceIntent] = parse_reference_intent,
    is_reference_query_fn: Callable[[str], bool] = is_reference_query,
    extract_info_fn: Callable[[str], dict[str, str]] = extract_info_from_query,
    is_external_error_query_fn: Callable[[str, dict[str, str] | None], bool] = is_external_error_query,
) -> PlannedSupportTurn:
    raw_query = query.strip()
    route = select_support_route(
        raw_query,
        model_generate=model_generate,
        classify_query_fn=classify_query_fn,
        parse_reference_intent_fn=parse_reference_intent_fn,
        is_reference_query_fn=is_reference_query_fn,
        extract_info_fn=extract_info_fn,
        is_external_error_query_fn=is_external_error_query_fn,
    )
    if not state.anchor_query or state.active_task == "idle":
        return PlannedSupportTurn(raw_query=raw_query, effective_query=raw_query, route=route)

    if state.active_task in {"reference_lookup", "onboarding_guidance"}:
        should_reuse_reference_anchor = False
        if looks_like_reference_followup(
            raw_query,
            model_generate=model_generate,
            parse_reference_intent_fn=parse_reference_intent_fn,
        ):
            should_reuse_reference_anchor = True
        elif state.open_clarification_slots:
            if "module" in state.open_clarification_slots and looks_like_module_disambiguation_fragment(raw_query):
                should_reuse_reference_anchor = True
            elif looks_like_clarification_answer_fragment(raw_query):
                should_reuse_reference_anchor = True
        if route.task != "troubleshooting" and should_reuse_reference_anchor:
            effective_query = f"{state.anchor_query} {normalize_reference_followup_fragment(raw_query)}".strip()
            followup_route = select_support_route(
                effective_query,
                model_generate=model_generate,
                classify_query_fn=classify_query_fn,
                parse_reference_intent_fn=parse_reference_intent_fn,
                is_reference_query_fn=is_reference_query_fn,
                extract_info_fn=extract_info_fn,
                is_external_error_query_fn=is_external_error_query_fn,
            )
            return PlannedSupportTurn(
                raw_query=raw_query,
                effective_query=effective_query,
                route=followup_route,
                reused_anchor=True,
            )
    if state.active_task == "troubleshooting" and state.open_clarification_slots and route.task != "troubleshooting":
        effective_query = f"{state.anchor_query} {raw_query}".strip()
        followup_route = select_support_route(
            effective_query,
            model_generate=model_generate,
            classify_query_fn=classify_query_fn,
            parse_reference_intent_fn=parse_reference_intent_fn,
            is_reference_query_fn=is_reference_query_fn,
            extract_info_fn=extract_info_fn,
            is_external_error_query_fn=is_external_error_query_fn,
        )
        return PlannedSupportTurn(
            raw_query=raw_query,
            effective_query=effective_query,
            route=followup_route,
            reused_anchor=True,
        )
    return PlannedSupportTurn(raw_query=raw_query, effective_query=raw_query, route=route)


def update_support_state(
    state: SupportSessionState,
    *,
    planned_turn: PlannedSupportTurn,
    response: str,
) -> SupportSessionState:
    if planned_turn.route.task == "capability_explanation":
        return state.cleared()

    facts = dict(state.confirmed_facts)
    facts.update({key: value for key, value in planned_turn.route.info.items() if value})
    facts.update(_extract_guidance_facts(planned_turn.effective_query))
    slots = infer_open_clarification_slots(response)

    if planned_turn.route.task == "troubleshooting":
        if response_requires_followup(response) or slots:
            return SupportSessionState(
                active_task="troubleshooting",
                anchor_query=planned_turn.effective_query,
                confirmed_facts=facts,
                open_clarification_slots=slots,
                last_route_reason=planned_turn.route.reason,
            )
        return state.cleared()

    if response_requires_followup(response) or slots:
        return SupportSessionState(
            active_task=planned_turn.route.task,
            anchor_query=planned_turn.effective_query,
            confirmed_facts=facts,
            open_clarification_slots=slots,
            last_route_reason=planned_turn.route.reason,
        )
    if response_supports_reference_context(response):
        return SupportSessionState(
            active_task=planned_turn.route.task,
            anchor_query=planned_turn.effective_query,
            confirmed_facts=facts,
            open_clarification_slots=slots,
            last_route_reason=planned_turn.route.reason,
        )
    return state.cleared()


def infer_open_clarification_slots(response: str) -> tuple[str, ...]:
    slots: list[str] = []
    if response.startswith("需要补充以下信息"):
        for field, label in FIELD_SLOT_LABELS.items():
            if label in response:
                slots.append(field)
    if response.startswith("需要确认模块"):
        slots.append("module")
    if "【需要确认的信息】" in response:
        for slot, patterns in WORKFLOW_SLOT_PATTERNS:
            if any(pattern in response for pattern in patterns):
                slots.append(slot)
    seen: set[str] = set()
    ordered = [slot for slot in slots if not (slot in seen or seen.add(slot))]
    return tuple(ordered)


def _extract_guidance_facts(query: str) -> dict[str, str]:
    normalized = query.lower()
    facts: dict[str, str] = {}
    for token, value in (
        (("wgs", "全基因组"), "wgs"),
        (("wes", "全外显子"), "wes"),
        (("panel",), "panel"),
        (("rna", "rna-seq", "rnaseq"), "rna"),
        (("long-read", "long read", "长读长"), "long-read"),
        (("short-read", "short read", "短读长"), "short-read"),
        (("germline", "胚系"), "germline"),
        (("somatic", "体细胞"), "somatic"),
        (("diploid", "二倍体"), "diploid"),
        (("polyploid", "non-diploid", "非二倍体", "多倍体", "多倍"), "non-diploid"),
        (("fastq",), "fastq"),
        (("ubam", "ucram"), "ubam-ucram"),
        (("bam", "cram"), "bam-cram"),
    ):
        if any(term in normalized for term in token):
            facts.setdefault(token[0], value)
    return facts
