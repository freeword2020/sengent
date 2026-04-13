from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import re

from sentieon_assist.support_contracts import (
    BoundaryOutcome,
    SupportIntent,
    ToolRequirement,
    normalize_boundary_outcome,
    normalize_support_intent,
    normalize_tool_requirement,
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    normalized: list[str] = []
    for item in values:
        candidate = _normalize_text(item)
        if candidate:
            normalized.append(candidate)
    return tuple(normalized)


def _require_enum_value(value: str, enum_values: set[str], *, label: str) -> str:
    if value not in enum_values:
        raise ValueError(f"unsupported {label}: {value}")
    return value


def _parse_version(version: str) -> tuple[int, ...]:
    candidate = _normalize_text(version)
    if not candidate:
        return ()
    parts = [int(part) for part in re.findall(r"\d+", candidate)]
    return tuple(parts)


def _version_in_range(current_version: str, min_version: str, max_version: str) -> bool:
    current = _parse_version(current_version)
    if not current:
        return not min_version and not max_version
    if min_version and current < _parse_version(min_version):
        return False
    if max_version and current > _parse_version(max_version):
        return False
    return True


@dataclass(frozen=True)
class BoundaryRule:
    name: str
    outcome: str = BoundaryOutcome.SHOULD_ANSWER
    boundary_tags: tuple[str, ...] = ()
    cues: tuple[str, ...] = ()
    tool_requirement: str = ToolRequirement.NONE
    support_intents: tuple[str, ...] = ()
    min_version: str = ""
    max_version: str = ""
    priority: int = 0
    reason: str = ""

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BoundaryRule":
        name = _normalize_text(payload.get("name"))
        if not name:
            raise ValueError("boundary rule name is required")
        outcome = normalize_boundary_outcome(payload.get("outcome"))
        tool_requirement = normalize_tool_requirement(payload.get("tool_requirement"))
        return cls(
            name=name,
            outcome=_require_enum_value(
                outcome,
                {item.value for item in BoundaryOutcome},
                label="boundary outcome",
            ),
            boundary_tags=_normalize_tuple(payload.get("boundary_tags")),
            cues=_normalize_tuple(payload.get("cues")),
            tool_requirement=_require_enum_value(
                tool_requirement,
                {item.value for item in ToolRequirement},
                label="tool requirement",
            ),
            support_intents=tuple(
                normalize_support_intent(item)
                for item in _normalize_tuple(payload.get("support_intents"))
            ),
            min_version=_normalize_text(payload.get("min_version")),
            max_version=_normalize_text(payload.get("max_version")),
            priority=int(payload.get("priority") or 0),
            reason=_normalize_text(payload.get("reason")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "outcome": self.outcome,
            "boundary_tags": list(self.boundary_tags),
            "cues": list(self.cues),
            "tool_requirement": self.tool_requirement,
            "support_intents": list(self.support_intents),
            "min_version": self.min_version,
            "max_version": self.max_version,
            "priority": self.priority,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BoundaryPack:
    schema_version: str = ""
    pack_version: str = ""
    rules: tuple[BoundaryRule, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BoundaryPack":
        rules = tuple(
            BoundaryRule.from_mapping(rule)
            for rule in payload.get("rules", [])
            if isinstance(rule, Mapping)
        )
        return cls(
            schema_version=_normalize_text(payload.get("schema_version")),
            pack_version=_normalize_text(payload.get("pack_version")),
            rules=rules,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_version": self.pack_version,
            "rules": [rule.to_mapping() for rule in self.rules],
        }


def select_boundary_rule(
    query: str,
    pack: BoundaryPack,
    *,
    boundary_tags: Sequence[str] | None = None,
    info: Mapping[str, str] | None = None,
    support_intent: str | SupportIntent | None = None,
) -> BoundaryRule | None:
    normalized_query = _normalize_text(query).lower()
    normalized_tags = {str(item).strip() for item in (boundary_tags or []) if str(item).strip()}
    normalized_version = _normalize_text((info or {}).get("version", ""))
    normalized_intent = normalize_support_intent(support_intent)

    candidates: list[tuple[int, int, int, BoundaryRule]] = []
    for index, rule in enumerate(pack.rules):
        if not _version_in_range(normalized_version, rule.min_version, rule.max_version):
            continue
        matched_tag = bool(normalized_tags.intersection(rule.boundary_tags))
        matched_cue = any(cue.lower() in normalized_query for cue in rule.cues)
        matched_intent = normalized_intent in rule.support_intents if rule.support_intents else False
        if not (matched_tag or matched_cue or matched_intent):
            continue
        score = (3 if matched_tag else 0) + (2 if matched_intent else 0) + (1 if matched_cue else 0)
        candidates.append((score, rule.priority, -index, rule))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]


_DEFAULT_BOUNDARY_PACK = BoundaryPack.from_mapping(
    {
        "schema_version": "2.1",
        "pack_version": "2026-04-13",
        "rules": [
            {
                "name": "file_structure_must_tool",
                "outcome": "should_answer",
                "cues": [
                    "contig not found",
                    "tabix 建不了索引",
                    "reference mismatch",
                    "sequence dictionary mismatch",
                    "read group 不一致",
                    "bed 区间",
                    "差一位",
                    "fai 和 dict 对不上",
                    "没有 crai",
                    "随机访问",
                    "没排序",
                    "没索引",
                    "sort order",
                    "header mismatch",
                    "index is missing",
                    "missing index",
                    "header is inconsistent",
                ],
                "tool_requirement": "required",
                "reason": "文件结构一致性问题需要先跑确定性检查。",
            },
            {
                "name": "unsupported_policy_refusal",
                "outcome": "must_refuse",
                "boundary_tags": ["refuse"],
                "reason": "该请求超出当前软件支持边界。",
            },
            {
                "name": "maintainer_escalation",
                "outcome": "must_escalate",
                "boundary_tags": ["escalate"],
                "reason": "该问题需要升级给维护者处理。",
            },
        ],
    }
)


def default_boundary_pack() -> BoundaryPack:
    return _DEFAULT_BOUNDARY_PACK


__all__ = [
    "BoundaryPack",
    "BoundaryRule",
    "default_boundary_pack",
    "select_boundary_rule",
]
