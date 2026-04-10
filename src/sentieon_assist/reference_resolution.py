from __future__ import annotations

import re
from dataclasses import dataclass

from sentieon_assist.external_guides import (
    format_external_error_association,
    format_external_guide_answer,
)
from sentieon_assist.module_index import (
    build_module_evidence,
    find_related_module_mentions,
    format_missing_module_reference_answer,
    format_module_overview_answer,
    format_module_reference_answer,
    format_parameter_disambiguation,
    format_parameter_followup_answer,
    format_parameter_reference_answer,
    format_script_reference_answer,
    format_unavailable_parameter_reference_answer,
    format_unavailable_script_reference_answer,
    match_module_entries,
    match_module_parameter,
)
from sentieon_assist.reference_boundaries import detect_reference_boundary_tags
from sentieon_assist.reference_intents import ReferenceIntent
from sentieon_assist.reference_retrieval import collect_reference_fallback_evidence, retrieve_reference_candidates
from sentieon_assist.trace_vocab import ResolverPath
from sentieon_assist.workflow_index import (
    format_workflow_guidance_answer,
    format_workflow_uncovered_answer,
    workflow_allows_direct_script_handoff,
    workflow_script_module,
)


@dataclass(frozen=True)
class ResolvedReferenceAnswer:
    text: str
    sources: list[str]
    boundary_tags: list[str]
    resolver_path: list[str]


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


def _has_explicit_script_request(query: str) -> bool:
    normalized = query.lower()
    return any(
        cue in normalized
        for cue in ("脚本", "示例脚本", "参考脚本", "示例命令", "参考命令", "命令骨架", "skeleton")
    )

def format_reference_boundary_answer(query: str, tags: list[str]) -> str:
    reasons: list[str] = []
    if "benchmark" in tags:
        reasons.append("benchmark / 精确数值")
    if "comparison" in tags:
        reasons.append("竞品或方案比较")
    if "roadmap" in tags:
        reasons.append("roadmap / 未来规划")
    if "deep_mechanism" in tags:
        reasons.append("深度机制拆解")
    reason_text = "、".join(reasons) or "当前结构化支持边界之外的资料型问题"
    return (
        "【资料边界】\n"
        f"- 这个问题属于 {reason_text}；当前本地支持资料没有足够的结构化证据，不能直接给出确定性结论。\n"
        "- 现阶段系统稳定支持的是：模块定位、参数语义、输入输出、流程导航和常见排障。\n\n"
        "【建议下一步】\n"
        "- 如果你要继续推进，建议把问题收窄到模块是什么、参数怎么用、输入输出是什么、该走哪条流程。\n"
        "- 如果你需要精确 benchmark、竞品比较、路线图或论文级机制说明，请补充对应 app note、release note、benchmark 文档或官方链接。"
    )


def _contains_all(normalized: str, cues: tuple[str, ...]) -> bool:
    return all(cue in normalized for cue in cues)


def format_doc_reference_answer(query: str) -> tuple[str, list[str]] | None:
    normalized = query.lower()
    if "too many open files" in normalized or "ulimit" in normalized:
        return (
            "【资料说明】\n"
            "- `Too many open files` 更像是运行环境的文件句柄上限不足，不一定是 Sentieon 自身 bug。\n"
            "- 这类问题的第一步通常不是改变调用算法，而是先检查当前 shell / 作业环境的 open files limit，并按需提高 `ulimit -n`。\n"
            "- 如果你在集群或调度器环境里运行，还要同时确认节点级 limits 或 job wrapper 没有把新的上限覆盖掉。\n\n"
            "【使用边界】\n"
            "- 当前回答只覆盖排障方向；具体永久化配置方式仍取决于你的 Linux 发行版、shell 和调度器。",
            [],
        )
    if any(cue in normalized for cue in ("samtools collate", "samtofastq")) and any(
        cue in normalized for cue in ("picard", "bwa", "重比对")
    ):
        return (
            "【资料说明】\n"
            "- 这类场景更稳的思路通常是先按 read name 近邻整理 BAM，再通过管道把 reads 直接送进 BWA，而不是先落地成一大批 FASTQ 中间文件。\n"
            "- `samtools collate` 的价值在于把同一 read name 的记录整理到一起，便于流式恢复 read 对并直接重比对。\n"
            "- 相比先用 `Picard SamToFastq` 拆出中间 FASTQ，这条路径通常更省磁盘和中间文件，也更不容易在尾部未配对 reads 堆积时放大内存压力。\n\n"
            "【使用边界】\n"
            "- 当前回答强调的是工程上的资源管理与重比对组织方式，不把它表述成所有场景下唯一正确路径。",
            [],
        )
    if ("核心" in query or "cpu" in normalized) and any(
        cue in normalized for cue in ("占用", "资源", "线程", "thread")
    ):
        return (
            "【资料说明】\n"
            "- 当前本地资料里，`sentieon-cli` 和很多 `sentieon driver` 命令都把 `-t` 作为共享参数，用来设置线程数。\n"
            "- `-t` 的稳定语义是：控制命令运行时可用的并行 worker 数；如果没有按命令显式设置，CPU 利用率不一定会贴近机器总核心数。\n"
            "- 现场可先回看你实际运行的命令里是否传了 `-t NUMBER_THREADS`，再结合 I/O 和调度策略判断线程利用情况。\n\n"
            "【使用边界】\n"
            "- 当前回答只确认 `-t` 的文档语义；如果你要继续定位具体命令为什么没吃满 CPU，还需要补充实际命令和运行步骤。",
            ["sentieon-modules.json", "Sentieon202503.03.pdf", "sentieon-doc-map.md"],
        )
    if any(cue in normalized for cue in ("gpu", "fpga", "nvidia", "arm", "graviton")):
        return (
            "【资料说明】\n"
            "- 当前本地 Quick Start 和常见 `sentieon-cli` / `sentieon driver` 资料，主线都是围绕 Linux、参考文件和 `-t` 线程参数展开，并没有把 GPU/FPGA 列为运行前提。\n"
            "- release notes 摘要里还能追溯到：`202308.03` 提到 ARM CPU 对 STAR 和 minimap2 的支持。\n"
            "- 基于当前本地资料可做的保守推断是：常见主线并不要求额外购买 GPU/FPGA；如果你关心某个特定二进制在 ARM 上的覆盖范围，仍要按版本回看 release notes。\n\n"
            "【使用边界】\n"
            "- 当前回答是基于本地资料的保守归纳，不替代逐版本的硬件兼容矩阵。",
            ["sentieon-doc-map.md", "Sentieon202503.03.pdf"],
        )
    if _contains_all(normalized, ("sentieon driver", "sentieon-cli")):
        return (
            "【资料说明】\n"
            "- `sentieon driver --algo ...` 属于更底层的二进制/算法入口，适合自定义脚本、GATK 风格迁移、分片运行和细粒度调参。\n"
            "- `sentieon-cli` 是官方单命令 pipeline CLI，当前本地资料明确覆盖 DNAscope、DNAscope LongRead、DNAscope Hybrid 和 Pangenome 等入口。\n"
            "- 可以把它理解成：`sentieon-cli` 负责把典型多步流程包装成单命令入口，而 `driver --algo` 保留底层拼装能力。\n\n"
            "【使用边界】\n"
            "- 当前回答只解释工具层级和定位；如果你要继续追到参数一一对应关系，建议再看 app note 的 Arguments Correspondence。",
            ["sentieon-doc-map.md", "sentieon-github-map.md", "Sentieon202503.03.pdf"],
        )
    if (
        any(cue in normalized for cue in (".model", "model 文件", "模型文件", "model bundle"))
        and any(cue in normalized for cue in ("illumina", "mgi", "华大", "ultima", "element"))
    ):
        return (
            "【资料说明】\n"
            "- 当前本地 GitHub 资料明确有官方 `sentieon-models` 仓库，用于维护 model bundle 清单。\n"
            "- 资料摘要里已列出短读长 DNAscope 的平台覆盖包含 Illumina、MGI / Complete Genomics、Element、Ultima 等。\n"
            "- 按这个资料边界，不能把不同平台直接当成同一个通用 bundle；更稳妥的做法是回到 `sentieon-models` 选择对应测序平台的 model bundle。\n\n"
            "【使用边界】\n"
            "- 当前回答只确认模型入口和平台分流；如果你要继续到具体 bundle 文件名，还要补充目标版本或对应仓库链接。",
            ["sentieon-github-map.md"],
        )
    if (
        any(cue in normalized for cue in ("joint call", "gvcftyper", ".g.vcf", "g.vcf"))
        and "-v" in normalized
        and any(cue in normalized for cue in ("500", "合并", "大文件"))
    ):
        return (
            "【资料说明】\n"
            "- 当前本地 `Joint Call` 参考骨架直接展示了 `sentieon driver --algo GVCFtyper -v s1_GVCF -v s2_GVCF ...` 这种多 gVCF 输入方式。\n"
            "- 同一批资料还把 large cohort 的重点放在 distributed mode 的 shard / merge 顺序和 `--split_by_sample` 等设计上，而不是先手工并成一个超大 gVCF 文件。\n"
            "- 按当前本地资料能稳定确认的范围，`GVCFtyper` 本身就是承接多 gVCF 输入的联合分型入口。\n\n"
            "【使用边界】\n"
            "- 当前回答只确认多输入骨架和分布式方向；如果你要继续到 500 样本的分片策略，需要再结合 distributed mode 章节。",
            ["sentieon-modules.json", "sentieon-doc-map.md", "Sentieon202503.03.pdf"],
        )
    if _contains_all(normalized, ("tnscope", "tumor-only")) and any(
        cue in normalized for cue in ("tumor-normal", "tumor normal", "matched normal")
    ):
        return (
            "【资料说明】\n"
            "- 当前本地资料明确写到：`TNscope` 覆盖 `tumor-only` 和 `tumor-normal` 的体细胞变异与结构变异检测。\n"
            "- workflow guidance 还明确提醒：`tumor-only` 输出里会包含 `germline variants`；`tumor-normal` 主线则要求同时准备 Tumor 和 Normal 输入，并先完成各自预处理。\n"
            "- 所以就当前资料边界，`tumor-only` 是可行入口，但它和 `tumor-normal` 在输入前提和胚系背景控制上并不相同。\n\n"
            "【使用边界】\n"
            "- 当前本地资料没有给出低频突变灵敏度或假阳性过滤效果的定量比较；如果你要比较性能，需要补充专门 benchmark 或 app note。",
            ["sentieon-modules.json", "workflow-guides.json", "Sentieon202503.03.pdf"],
        )
    if _contains_all(normalized, ("locuscollector", "dedup")):
        return (
            "【资料说明】\n"
            "- 当前本地模块索引把 `LocusCollector` 定义为 `Dedup` 上游的统计步骤，用于收集重复打分相关信息。\n"
            "- `Dedup` 则负责实际的 duplicate marking / dedup 处理，并可承接常规重复标记、consensus-based deduplication 和部分 UMI-aware 场景。\n"
            "- 按当前资料可稳定理解为：`LocusCollector` 先产出重复打分所需信息，`Dedup` 再消费这些信息完成后续处理。\n\n"
            "【使用边界】\n"
            "- 当前回答主要解释两步分工；如果你要继续追到“只标记不删除”的具体开关，仍要回到对应 workflow 或官方手册（manual）示例确认。",
            ["sentieon-modules.json", "Sentieon202503.03.pdf"],
        )
    if _contains_all(normalized, ("gvcftyper", "--emit_mode")) and any(cue in normalized for cue in ("体积", "几百")):
        return (
            "【资料说明】\n"
            "- 当前本地资料可稳定确认：`GVCFtyper` 的 `--emit_mode` 用于控制参考位点和非变异位点的输出范围。\n"
            "- release notes 摘要里明确记过 `--emit_mode all`；如果输出范围扩大到更多参考/非变异位点，VCF 体积也会随之显著增加。\n"
            "- 对 `variant / confident / all` 的完整逐项差异，当前本地资料仍建议回看 manual 对应章节。\n\n"
            "【使用边界】\n"
            "- 当前回答只确认输出范围和体积变化方向，不替代完整的模式差异说明。",
            ["sentieon-modules.json", "Sentieon202503.03.pdf"],
        )
    lines: list[str] = []
    sources: list[str] = []
    if "licsrvr" in normalized or "licclnt" in normalized:
        lines.append("- LICSRVR：当前本地官方资料把它列为 license server 相关二进制；LICCLNT 用于 ping/query 服务器状态。")
        lines.append("- 如果你现在关注的是 license server 健康检查，常见入口是 `sentieon licclnt ping/query` 这类命令。")
        sources.extend(["Sentieon202503.03.pdf", "sentieon-doc-map.md"])
    if "poetry" in normalized or "sdist" in normalized:
        lines.append("- Poetry：当前本地资料只稳定确认 `sentieon-cli` 仓库支持用 Poetry 安装开发环境。")
        lines.append("- 目前本地资料没有收录可确定性复用的完整 Poetry 配置手册，只能先确认它属于受支持的开发环境安装方式。")
        sources.extend(["sentieon-github-map.md"])
    if not lines:
        return None
    return (
        "【资料说明】\n"
        + "\n".join(lines)
        + "\n\n【使用边界】\n"
        + "- 当前回答只确认工具定位和文档入口；如果你要继续到集群配置或逐步安装，请再补充具体目标。",
        sources,
    )


def _resolved(
    text: str,
    sources: list[str],
    *,
    boundary_tags: list[str] | None = None,
    resolver_path: list[str] | None = None,
) -> ResolvedReferenceAnswer:
    return ResolvedReferenceAnswer(
        text=text,
        sources=sources,
        boundary_tags=list(boundary_tags or []),
        resolver_path=list(resolver_path or []),
    )


def resolve_reference_answer(
    query: str,
    *,
    source_directory: str,
    resolved_intent: ReferenceIntent,
) -> ResolvedReferenceAnswer:
    doc_answer = format_doc_reference_answer(query)
    if doc_answer is not None:
        doc_text, doc_sources = doc_answer
        return _resolved(doc_text, doc_sources, resolver_path=[ResolverPath.DOC_REFERENCE])

    boundary_tags = detect_reference_boundary_tags(query, resolved_intent)
    if boundary_tags:
        return _resolved(
            format_reference_boundary_answer(query, boundary_tags),
            [],
            boundary_tags=boundary_tags,
            resolver_path=[ResolverPath.BOUNDARY_REFERENCE],
        )

    retrieval = retrieve_reference_candidates(
        query,
        source_directory=source_directory,
        resolved_intent=resolved_intent,
    )

    if resolved_intent.intent == "workflow_guidance":
        workflow_entry = retrieval.workflow_entry
        if workflow_entry is None:
            return _resolved(
                format_workflow_uncovered_answer(),
                ["workflow-guides.json"],
                resolver_path=[ResolverPath.WORKFLOW_UNCOVERED],
            )
        if _is_terse_script_followup(query) or (
            _has_explicit_script_request(query) and workflow_allows_direct_script_handoff(workflow_entry)
        ):
            script_entry = retrieval.script_workflow_entry or workflow_entry
            script_module = workflow_script_module(script_entry)
            if script_module:
                module_matches = match_module_entries(script_module, source_directory, max_matches=1)
                if module_matches:
                    module_entry = module_matches[0]
                    direct_answer = format_script_reference_answer(module_entry, query=query) or format_unavailable_script_reference_answer(
                        module_entry
                    )
                    if direct_answer:
                        script_source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                        return _resolved(
                            direct_answer,
                            script_source_names,
                            resolver_path=[ResolverPath.WORKFLOW_DIRECT_SCRIPT],
                        )
        source_names = ["workflow-guides.json", *[str(item) for item in workflow_entry.get("sources", [])]]
        return _resolved(
            format_workflow_guidance_answer(workflow_entry),
            source_names,
            resolver_path=[ResolverPath.WORKFLOW_GUIDANCE],
        )

    external_entry = retrieval.external_entry
    external_error_association = retrieval.external_error_association
    if external_error_association is not None:
        source_names = [
            str(external_error_association.get("source_file", "")).strip(),
            *[str(item) for item in external_error_association.get("source_notes", [])],
        ]
        return _resolved(
            format_external_error_association(external_error_association),
            [name for name in source_names if name],
            resolver_path=[ResolverPath.EXTERNAL_ERROR_ASSOCIATION],
        )

    module_matches = retrieval.module_matches
    module_candidate = str(resolved_intent.module or "").strip()
    if not module_matches and module_candidate and resolved_intent.intent in {"module_intro", "parameter_lookup", "script_example"}:
        related_mentions = find_related_module_mentions(module_candidate, source_directory)
        if not related_mentions:
            return _resolved(
                format_reference_boundary_answer(query, ["deep_mechanism"]),
                ["sentieon-modules.json"],
                boundary_tags=["deep_mechanism"],
                resolver_path=[ResolverPath.MISSING_MODULE_BOUNDARY],
            )
        return _resolved(
            format_missing_module_reference_answer(module_candidate, related_mentions),
            ["sentieon-modules.json"],
            resolver_path=[ResolverPath.MISSING_MODULE_REFERENCE],
        )

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
            return _resolved(
                format_external_guide_answer(external_entry),
                [name for name in source_names if name],
                resolver_path=[ResolverPath.EXTERNAL_GUIDE],
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
                return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_PLACEHOLDER_REFERENCE])
        module_parameter = match_module_parameter(module_entry, query)
        if module_parameter is not None:
            direct_answer = format_parameter_reference_answer(module_entry, module_parameter)
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_PARAMETER])
        if resolved_intent.intent == "script_example":
            direct_answer = format_script_reference_answer(module_entry, query=query) or format_unavailable_script_reference_answer(
                module_entry
            )
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_SCRIPT])
        if resolved_intent.intent == "parameter_lookup":
            direct_answer = format_unavailable_parameter_reference_answer(module_entry)
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_PARAMETER_UNAVAILABLE])
            direct_answer = format_parameter_followup_answer(module_entry)
            if direct_answer:
                source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
                return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_PARAMETER_FOLLOWUP])
        direct_answer = format_module_reference_answer(module_entry, query)
        module_evidence.append(build_module_evidence(module_entry))
        if direct_answer:
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.MODULE_REFERENCE])

    global_parameter_matches = retrieval.global_parameter_matches
    all_parameter_matches = retrieval.all_parameter_matches
    if len(all_parameter_matches) > 1:
        return _resolved(
            format_parameter_disambiguation(all_parameter_matches),
            [],
            resolver_path=[ResolverPath.GLOBAL_PARAMETER_DISAMBIGUATION],
        )
    if global_parameter_matches:
        module_entry = global_parameter_matches[0]
        module_parameter = module_entry.get("matched_parameter")
        if isinstance(module_parameter, dict):
            direct_answer = format_parameter_reference_answer(module_entry, module_parameter)
            source_names = ["sentieon-modules.json", *[str(item) for item in module_entry.get("sources", [])]]
            return _resolved(direct_answer, source_names, resolver_path=[ResolverPath.GLOBAL_PARAMETER])

    if resolved_intent.intent == "module_overview":
        direct_answer = format_module_overview_answer(source_directory)
        if direct_answer:
            return _resolved(
                direct_answer,
                ["sentieon-modules.json", "sentieon-module-index.md"],
                resolver_path=[ResolverPath.MODULE_OVERVIEW],
            )

    evidence = collect_reference_fallback_evidence(
        query,
        source_directory=source_directory,
        preferred_evidence=module_evidence,
    )
    return _resolved(
        format_reference_boundary_answer(query, ["deep_mechanism"]),
        [item["name"] for item in evidence],
        boundary_tags=["deep_mechanism"],
        resolver_path=[ResolverPath.FALLBACK_BOUNDARY],
    )
