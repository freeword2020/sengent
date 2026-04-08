from __future__ import annotations

from sentieon_assist.models import SUPPORTED_ISSUE_TYPES

LICENSE_TERMS = (
    "license",
    "licence",
    "许可证",
    "授权",
    "激活",
    "license 文件",
)

INSTALL_TERMS = (
    "install",
    "安装",
    "部署",
    "解压",
    "找不到 sentieon",
    "找不到 sentieon 命令",
)

REFERENCE_TERMS = (
    "alignment",
    "bwa",
    "star",
    "minimap2",
    "dnaseq",
    "dnascope",
    "dnascope longread",
    "dnascope hybrid",
    "pangenome",
    "cnvscope",
    "joint call",
    "tnscope",
    "tnseq",
    "tnsnv",
    "tnhaplotyper",
    "tnhaplotyper2",
    "gvcftyper",
    "dedup",
    "locuscollector",
    "qualcal",
    "varcal",
    "applyvarcal",
    "rnaseq",
    "geneedit",
    "umi",
    "readwriter",
    "python api",
    "distributed mode",
    "bcl-fastq",
    "realigner",
    "sentieon-cli",
)

REFERENCE_CUES = (
    "是什么",
    "做什么",
    "介绍",
    "参数",
    "选项",
    "区别",
    "有哪些",
    "--",
)


def normalize_issue_type(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized in SUPPORTED_ISSUE_TYPES:
        return normalized
    return "other"


def classify_query(query: str) -> str:
    normalized_query = query.lower()
    if any(term in normalized_query for term in LICENSE_TERMS):
        return "license"
    if any(term in normalized_query for term in INSTALL_TERMS):
        return "install"
    return "other"


def is_reference_query(query: str) -> bool:
    normalized_query = query.lower()
    has_reference_cue = any(cue in normalized_query for cue in REFERENCE_CUES)
    has_reference_term = any(term in normalized_query for term in REFERENCE_TERMS)
    has_parameter_only_cue = "--" in normalized_query and any(
        cue in normalized_query for cue in ("参数", "选项", "是什么", "含义", "作用", "意思")
    )
    return (has_reference_term and has_reference_cue) or has_parameter_only_cue
