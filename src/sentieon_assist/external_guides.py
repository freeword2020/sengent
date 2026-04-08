from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


EXTERNAL_FORMAT_GUIDE_FILENAME = "external-format-guides.json"
EXTERNAL_TOOL_GUIDE_FILENAME = "external-tool-guides.json"
EXTERNAL_ERROR_ASSOCIATION_FILENAME = "external-error-associations.json"
EXTERNAL_GUIDE_FILENAMES = (
    EXTERNAL_FORMAT_GUIDE_FILENAME,
    EXTERNAL_TOOL_GUIDE_FILENAME,
)
EXTERNAL_REFERENCE_FILENAMES = EXTERNAL_GUIDE_FILENAMES + (EXTERNAL_ERROR_ASSOCIATION_FILENAME,)
EXTERNAL_GUIDE_TERMS = (
    "vcf",
    "bcf",
    "sample column",
    "bam",
    "cram",
    "sam",
    "fasta",
    "fai",
    "dict",
    "sequence dictionary",
    "faidx",
    "bed",
    "interval",
    "off by one",
    "bgzip",
    "tabix",
    "bai",
    "csi",
    "crai",
    "header",
    "read group",
    "readgroup",
    "rg",
    "contig",
    "fastqc",
    "multiqc",
    "samtools",
    "bcftools",
    "grep",
    "sed",
    "awk",
    "shell",
    "bash",
    "quoting",
    "quote",
    "引号",
    "管道",
    "pipefail",
)
EXTERNAL_REFERENCE_CUES = (
    "是什么",
    "做什么",
    "区别",
    "格式",
    "结构",
    "字段",
    "header",
    "索引",
    "报告",
    "怎么看",
    "含义",
    "为什么",
    "说明",
    "参数",
    "命令",
    "规则",
)
EXTERNAL_ERROR_CUES = (
    "报错",
    "失败",
    "异常",
    "怎么办",
    "建不了",
    "不能",
    "无法",
    "不一致",
    "冲突",
    "对不上",
    "差一位",
    "偏一位",
    "不匹配",
    "not found",
    "mismatch",
    "missing",
    "incompatible",
    "random access",
    "region query",
    "fetch",
    "decode",
    "解码",
    "随机访问",
    "索引",
    "index",
    "排序",
    "sorted",
    "unexpected eof",
    "matching quote",
    "syntax error",
    "command not found",
    "bad substitution",
    "unknown command",
    "unterminated",
    "extra characters",
    "can't read",
    "no such file",
)
AMBIGUOUS_GUIDE_ALIASES = {
    "info",
    "format",
}


def _load_external_guide_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"external guide index must contain a JSON object: {path}")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"external guide index entries must be a JSON list: {path}")
    loaded: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        enriched = dict(entry)
        enriched["source_file"] = path.name
        loaded.append(enriched)
    return loaded


def _contains_term(normalized_text: str, term: str) -> bool:
    normalized_term = str(term).strip().lower()
    if not normalized_term:
        return False
    if all(character.isascii() and (character.isalnum() or character in {"_", "-"}) for character in normalized_term):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])"
        return re.search(pattern, normalized_text) is not None
    return normalized_term in normalized_text


def _load_external_association_file(path: Path) -> list[dict[str, Any]]:
    return _load_external_guide_file(path)


def list_external_guide_entries(source_directory: str | Path) -> list[dict[str, Any]]:
    root = Path(source_directory)
    entries: list[dict[str, Any]] = []
    for filename in EXTERNAL_GUIDE_FILENAMES:
        entries.extend(_load_external_guide_file(root / filename))
    return entries


def list_external_error_associations(source_directory: str | Path) -> list[dict[str, Any]]:
    root = Path(source_directory)
    return _load_external_association_file(root / EXTERNAL_ERROR_ASSOCIATION_FILENAME)


def is_external_reference_query(query: str, info: dict[str, str] | None = None) -> bool:
    parts = [query]
    if info:
        parts.extend([info.get("error_keywords", ""), info.get("step", ""), info.get("error", "")])
    normalized = " ".join(str(part).lower() for part in parts if str(part).strip())
    if not normalized:
        return False
    has_term = any(_contains_term(normalized, term) for term in EXTERNAL_GUIDE_TERMS)
    if not has_term:
        return False
    return any(_contains_term(normalized, cue) for cue in EXTERNAL_REFERENCE_CUES) or has_term


def is_external_error_query(query: str, info: dict[str, str] | None = None) -> bool:
    parts = [query]
    if info:
        parts.extend([info.get("error_keywords", ""), info.get("step", ""), info.get("error", "")])
    normalized = " ".join(str(part).lower() for part in parts if str(part).strip())
    if not normalized:
        return False
    if not any(_contains_term(normalized, term) for term in EXTERNAL_GUIDE_TERMS):
        return False
    return any(_contains_term(normalized, cue) for cue in EXTERNAL_ERROR_CUES)


def _matches_required_any(normalized_query: str, required: list[str]) -> bool:
    if not required:
        return True
    return any(_contains_term(normalized_query, term) for term in required)


def _matches_required_groups(normalized_query: str, groups: list[list[str]]) -> bool:
    if not groups:
        return True
    return all(any(_contains_term(normalized_query, term) for term in group) for group in groups)


def _matches_excluded(normalized_query: str, excluded: list[str]) -> bool:
    if not excluded:
        return False
    return any(_contains_term(normalized_query, term) for term in excluded)


def _alias_requires_context(alias: str) -> bool:
    return alias in AMBIGUOUS_GUIDE_ALIASES


def _alias_context_satisfied(normalized_query: str, alias: str) -> bool:
    if alias not in AMBIGUOUS_GUIDE_ALIASES:
        return True
    return any(_contains_term(normalized_query, term) for term in ("vcf", "bcf"))


def match_external_error_association(
    query: str,
    source_directory: str | Path,
) -> dict[str, Any] | None:
    if not is_external_error_query(query):
        return None
    normalized_query = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in list_external_error_associations(source_directory):
        patterns_any = [str(value).strip().lower() for value in entry.get("patterns_any", []) if str(value).strip()]
        require_any = [str(value).strip().lower() for value in entry.get("require_any", []) if str(value).strip()]
        require_groups = [
            [str(value).strip().lower() for value in group if str(value).strip()]
            for group in entry.get("require_groups", [])
            if isinstance(group, list)
        ]
        exclude_any = [str(value).strip().lower() for value in entry.get("exclude_any", []) if str(value).strip()]
        matched_terms = [term for term in patterns_any if _contains_term(normalized_query, term)]
        if not matched_terms:
            continue
        if _matches_excluded(normalized_query, exclude_any):
            continue
        if not _matches_required_any(normalized_query, require_any):
            continue
        if not _matches_required_groups(normalized_query, require_groups):
            continue
        score = sum(len(term) for term in matched_terms)
        enriched = dict(entry)
        enriched["matched_terms"] = matched_terms
        scored.append((score, enriched))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return scored[0][1]


def match_external_guide_entry(
    query: str,
    source_directory: str | Path,
) -> dict[str, Any] | None:
    normalized_query = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in list_external_guide_entries(source_directory):
        aliases = [str(value).strip() for value in entry.get("aliases", []) if str(value).strip()]
        aliases.append(str(entry.get("name", "")).strip())
        best_score = -1
        best_alias = ""
        for alias in aliases:
            normalized_alias = alias.lower()
            if not normalized_alias or not _contains_term(normalized_query, normalized_alias):
                continue
            if _alias_requires_context(normalized_alias) and not _alias_context_satisfied(normalized_query, normalized_alias):
                continue
            score = len(normalized_alias)
            if normalized_query.startswith(normalized_alias):
                score += 10
            if normalized_query == normalized_alias:
                score += 20
            if score > best_score:
                best_score = score
                best_alias = alias
        if best_score >= 0:
            enriched = dict(entry)
            enriched["matched_alias"] = best_alias
            scored.append((best_score, enriched))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
    return scored[0][1]


def format_external_guide_answer(entry: dict[str, Any]) -> str:
    name = str(entry.get("name", "")).strip() or "外部资料"
    summary = str(entry.get("summary", "")).strip()
    details = [str(value).strip() for value in entry.get("details", []) if str(value).strip()]
    troubleshooting = [str(value).strip() for value in entry.get("troubleshooting", []) if str(value).strip()]
    boundary = [str(value).strip() for value in entry.get("usage_boundary", []) if str(value).strip()]

    detail_lines = [f"{name}：{summary}"] if summary else [name]
    detail_lines.extend(f"- {value}" for value in details)
    troubleshooting_lines = [f"- {value}" for value in troubleshooting] or ["- 当前本地外部资料索引未整理出更具体的关联排查提示。"]
    boundary_lines = [f"- {value}" for value in boundary] or ["- 这层资料只用于解释外部格式或工具规则，不单独替代 Sentieon 官方 workflow 或模块结论。"]

    return (
        "【资料查询】\n"
        f"- 命中外部资料索引：{name}\n"
        f"- 资料文件：{entry.get('source_file', 'external guides')}\n\n"
        "【资料说明】\n"
        + "\n".join(detail_lines)
        + "\n\n【关联排查】\n"
        + "\n".join(troubleshooting_lines)
        + "\n\n【使用边界】\n"
        + "\n".join(boundary_lines)
    )


def format_external_error_association(entry: dict[str, Any]) -> str:
    name = str(entry.get("name", "")).strip() or "外部错误关联"
    summary = str(entry.get("summary", "")).strip()
    checks = [str(value).strip() for value in entry.get("checks", []) if str(value).strip()]
    related_guides = [str(value).strip() for value in entry.get("related_guides", []) if str(value).strip()]
    boundary = [str(value).strip() for value in entry.get("usage_boundary", []) if str(value).strip()]

    summary_line = summary or "这更像是一类外部格式/工具层问题，需要先回到对应规则层检查。"
    check_lines = [f"- {value}" for value in checks] or ["- 先回到相关格式/工具层检查输入状态。"]
    related_lines = [f"- {value}" for value in related_guides] or ["- 当前本地错误关联索引未整理出更具体的关联资料。"]
    boundary_lines = [f"- {value}" for value in boundary] or ["- 这是关联判断，不直接替代具体模块或 workflow 结论。"]

    return (
        "【资料查询】\n"
        f"- 命中外部错误关联：{name}\n"
        f"- 资料文件：{entry.get('source_file', EXTERNAL_ERROR_ASSOCIATION_FILENAME)}\n\n"
        "【关联判断】\n"
        f"- {summary_line}\n\n"
        "【优先检查】\n"
        + "\n".join(check_lines)
        + "\n\n【关联资料】\n"
        + "\n".join(related_lines)
        + "\n\n【使用边界】\n"
        + "\n".join(boundary_lines)
    )
