from __future__ import annotations

from typing import Any


REFERENCE_BOUNDARY_TAG_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "benchmark",
        (
            "benchmark",
            "基准测试",
            "加速",
            "多少倍",
            "快多少倍",
            "成本",
            "美元",
            "1~5",
            "1-5",
            "f1",
            "检出率",
            "召回率",
            "假阳性",
            "假阴性",
            "误差率",
            "准确率",
            "0.1%",
            "0.3%",
            "94.77",
            "100 万",
            "100万",
            "60 分钟",
            "60分钟",
            "压缩至",
            "击败",
            "最敏感",
        ),
    ),
    (
        "comparison",
        (
            "相比",
            "优劣",
            "一致性如何",
            "拉开差距",
            "bwa-mem",
            "starsolo",
            "cellranger",
            "clair3",
            "truvari",
            "vardict",
            "fgbio",
        ),
    ),
    (
        "roadmap",
        (
            "即将发布",
            "未来",
            "如何应对",
            "多少个样本网络",
            "400 样本",
            "400样本",
            "目前发布",
        ),
    ),
    (
        "deep_mechanism",
        (
            "软件架构",
            "硬件兼容",
            "gpu",
            "fpga",
            "arm",
            "graviton",
            "bwa-turbo",
            "sdist",
            "poetry",
            "licsrvr",
            "licclnt",
            "too many open files",
            "ulimit",
            ".model",
            "从哪里下载",
            "省略",
            "替代",
            "一次性调用",
            "同时完成",
            "质量打分",
            "加成",
            "ffpe",
            "target capture",
            "杂交捕获",
            "伪影",
            "多大尺寸",
            "bwa-meth",
            "methyldackel",
            "bedgraph",
            "variantphaser",
            "longreadutil",
            "crispr-detector",
            "本质差异",
            "本质区别",
            "参数传递",
            "应用场景",
            "原理",
            "机制",
            "底层",
            "共享内存",
            "picard",
            "samtofastq",
            "动态分配",
            "活跃区域",
            "从头组装",
            "纠错",
            "重比对",
            "单倍型",
            "k-mer",
            "逆向映射",
            "segmentation",
            "break-end",
            "假基因",
            "同聚物",
            "homopolymer",
        ),
    ),
)
BOUNDARY_SAFE_INTENTS = {"parameter_lookup", "script_example", "module_overview"}


def detect_reference_boundary_tags(query: str, resolved_intent: Any | None = None) -> list[str]:
    intent = str(getattr(resolved_intent, "intent", "") or "")
    if intent in BOUNDARY_SAFE_INTENTS:
        return []

    normalized = query.lower()
    tags: list[str] = []
    for tag, cues in REFERENCE_BOUNDARY_TAG_RULES:
        if any(cue in normalized for cue in cues):
            tags.append(tag)
    return tags


def looks_like_reference_boundary_query(query: str) -> bool:
    return bool(detect_reference_boundary_tags(query))
