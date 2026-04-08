from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


WORKFLOW_GUIDE_FILENAME = "workflow-guides.json"
WORKFLOW_QUERY_NOISE_PATTERN = re.compile(r"示例脚本|参考脚本|示例命令|参考命令|脚本|命令|示例")


def workflow_index_path(source_directory: str | Path) -> Path:
    return Path(source_directory) / WORKFLOW_GUIDE_FILENAME


def load_workflow_index(source_directory: str | Path) -> dict[str, Any]:
    path = workflow_index_path(source_directory)
    if not path.exists():
        return {"version": "", "entries": []}
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"workflow index must contain a JSON object: {path}")
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"workflow index entries must be a JSON list: {path}")
    return data


def list_workflow_entries(source_directory: str | Path) -> list[dict[str, Any]]:
    return [entry for entry in load_workflow_index(source_directory).get("entries", []) if isinstance(entry, dict)]


def _contains_any(normalized_query: str, values: list[str]) -> bool:
    return any(value and value in normalized_query for value in values)


def _normalize_workflow_query(query: str) -> str:
    return WORKFLOW_QUERY_NOISE_PATTERN.sub(" ", query.lower())


def match_workflow_entry(
    query: str,
    source_directory: str | Path,
    *,
    require_script_module: bool = False,
) -> dict[str, Any] | None:
    normalized_query = _normalize_workflow_query(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in list_workflow_entries(source_directory):
        if require_script_module and not str(entry.get("script_module", "")).strip():
            continue
        exclude_any = [str(value).strip().lower() for value in entry.get("exclude_any", []) if str(value).strip()]
        if _contains_any(normalized_query, exclude_any):
            continue

        require_any_groups = entry.get("require_any_groups", [])
        if not isinstance(require_any_groups, list):
            continue
        if require_any_groups:
            matched_groups = 0
            group_score = 0
            for group in require_any_groups:
                if not isinstance(group, list):
                    continue
                normalized_group = [str(value).strip().lower() for value in group if str(value).strip()]
                matched_terms = [value for value in normalized_group if value in normalized_query]
                if not matched_terms:
                    matched_groups = -1
                    break
                matched_groups += 1
                group_score += max(len(value) for value in matched_terms)
            if matched_groups < 0:
                continue
        else:
            group_score = 0

        prefer_any = [str(value).strip().lower() for value in entry.get("prefer_any", []) if str(value).strip()]
        score = int(entry.get("priority", 0)) + group_score
        score += sum(len(value) for value in prefer_any if value in normalized_query)
        scored.append((score, entry))

    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id", "")).lower()))
    return scored[0][1]


def format_workflow_guidance_answer(entry: dict[str, Any]) -> str:
    lookup_name = str(entry.get("name", "")).strip() or str(entry.get("id", "")).strip() or "workflow guidance"
    summary = str(entry.get("summary", "")).strip()
    guidance = [str(value).strip() for value in entry.get("guidance", []) if str(value).strip()]
    prerequisites = [str(value).strip() for value in entry.get("prerequisites", []) if str(value).strip()]
    follow_up = [str(value).strip() for value in entry.get("follow_up", []) if str(value).strip()]

    guidance_lines: list[str] = []
    if summary:
        guidance_lines.append(f"- {summary}")
    guidance_lines.extend(f"- {value}" for value in guidance)
    if not guidance_lines:
        guidance_lines.append("- 当前本地官方资料未覆盖可确定回答的流程指导。")

    sections = [
        "【资料查询】\n"
        f"- 命中语义意图：workflow_guidance\n"
        f"- 命中流程索引：{lookup_name}",
        "【流程指导】\n" + "\n".join(guidance_lines),
    ]
    if prerequisites:
        sections.append("【关键前提】\n" + "\n".join(f"- {value}" for value in prerequisites))
    if follow_up:
        sections.append("【需要确认的信息】\n" + "\n".join(f"- {value}" for value in follow_up))
    return "\n\n".join(sections)


def format_workflow_uncovered_answer() -> str:
    return (
        "【流程指导】\n"
        "- 当前本地官方资料未覆盖可用于确定性回答的 workflow guidance；我不能直接替你指定流程。\n\n"
        "【需要确认的信息】\n"
        "- 是胚系还是体细胞？\n"
        "- 是短读长还是 PacBio HiFi / ONT 长读长？\n"
        "- 如果是短读长胚系，样本是否来自 diploid organism？"
    )
