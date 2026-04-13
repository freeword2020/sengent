from __future__ import annotations

import re
from dataclasses import dataclass

from sentieon_assist.session_events import classify_response_mode


SECTION_HEADER_PATTERN = re.compile(r"^【[^】]+】$")
REPLY_HINT_PLACEHOLDERS = {
    "Sentieon 版本": "Sentieon 版本：<请填写>",
    "完整报错信息": "完整报错信息：<请填写>",
    "输入文件类型": "输入文件类型：<请填写>",
    "数据类型": "数据类型：<请填写>",
    "执行步骤": "执行步骤：<请填写>",
}
META_SECTION_TITLES = {"【资料查询】", "【资料版本】", "【版本提示】", "【参考资料】"}
FOLLOWUP_CUES = (
    "可继续追问：",
    "请直接补充参数名",
    "请补充更完整的模块名",
    "请补充更具体的问题",
    "当前模块索引优先覆盖",
    "还没给出具体参数名",
    "未收录可直接提示",
)


@dataclass(frozen=True)
class SupportAnswerSection:
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class SupportAnswerCard:
    response_mode: str
    sections: tuple[SupportAnswerSection, ...]


def _normalize_lines(lines: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_line in lines:
        line = str(raw_line).rstrip()
        if not line.strip():
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue
        normalized.append(line.strip())
    while normalized and normalized[0] == "":
        normalized.pop(0)
    while normalized and normalized[-1] == "":
        normalized.pop()
    return tuple(normalized)


def _split_sections(text: str) -> tuple[tuple[str, ...], list[SupportAnswerSection]]:
    preamble: list[str] = []
    sections: list[SupportAnswerSection] = []
    current_title = ""
    current_lines: list[str] = []
    for raw_line in str(text).splitlines():
        stripped = raw_line.strip()
        if SECTION_HEADER_PATTERN.fullmatch(stripped):
            if current_title:
                sections.append(SupportAnswerSection(current_title, _normalize_lines(current_lines)))
            elif current_lines:
                preamble.extend(_normalize_lines(current_lines))
            current_title = stripped
            current_lines = []
            continue
        current_lines.append(raw_line)
    if current_title:
        sections.append(SupportAnswerSection(current_title, _normalize_lines(current_lines)))
    elif current_lines:
        preamble.extend(_normalize_lines(current_lines))
    return _normalize_lines(preamble), sections


def _as_bullet(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return stripped
    if stripped.startswith("- "):
        return stripped
    return f"- {stripped}"


def _split_followup_lines(lines: tuple[str, ...]) -> tuple[list[str], list[str]]:
    primary: list[str] = []
    followups: list[str] = []
    for line in lines:
        if any(cue in line for cue in FOLLOWUP_CUES):
            followups.append(line)
            continue
        primary.append(line)
    return primary, followups


def _extract_example(lines: list[str] | tuple[str, ...] | str) -> str:
    candidates = [lines] if isinstance(lines, str) else [str(line) for line in lines]
    for line in candidates:
        match = re.search(r"例如[:：]\s*(.+)$", line)
        if match:
            return match.group(1).strip().rstrip("。")
    return ""


def _reply_hint_lines(requirements: list[str], example: str = "") -> list[str]:
    hints: list[str] = []
    for requirement in requirements:
        label = str(requirement).strip().removeprefix("-").strip()
        placeholder = REPLY_HINT_PLACEHOLDERS.get(label)
        if placeholder and placeholder not in hints:
            hints.append(f"- {placeholder}")
    if example:
        example_line = f"- {example}"
        if example_line not in hints:
            hints.append(example_line)
    return hints


def _default_next_steps(response_mode: str) -> list[str]:
    if response_mode == "module_intro":
        return ["- 如果你要继续落到实际命令，可继续问这个模块的输入输出、关键参数或参考脚本。"]
    if response_mode == "parameter":
        return ["- 如果你要继续落到现场命令，可继续贴当前命令，或继续比较另一个参数。"]
    if response_mode == "workflow_guidance":
        return ["- 如果你要继续收敛流程，请补充数据类型、输入形态和分析目标。"]
    if response_mode in {"doc", "external_error"}:
        return ["- 如果你要继续定位现场问题，请补充实际命令、完整报错和版本。"]
    if response_mode == "capability":
        return ["- 直接告诉我你的目标或具体问题，我会继续收窄到模块、参数、流程或排障步骤。"]
    return []


def _build_module_disambiguation_card(text: str) -> SupportAnswerCard | None:
    stripped = str(text).strip()
    if not stripped.startswith("需要确认模块："):
        return None
    payload = stripped.split("：", 1)[1].strip()
    next_step = ""
    if "请补充模块名后再查询" in payload:
        next_step = "请补充模块名后再查询。"
        requirement = payload.split("请补充模块名后再查询", 1)[0].strip().rstrip("。")
    else:
        requirement = payload
    example = _extract_example(payload)
    sections = [SupportAnswerSection("【需要确认的信息】", (_as_bullet(f"需要确认模块：{requirement}"),))]
    if next_step:
        sections.append(SupportAnswerSection("【建议下一步】", (_as_bullet(next_step),)))
    hint_lines = _reply_hint_lines([], example=example)
    if hint_lines:
        sections.append(SupportAnswerSection("【下一条可直接回复】", tuple(hint_lines)))
    return SupportAnswerCard(response_mode="clarify", sections=tuple(sections))


def build_support_answer_card(text: str) -> SupportAnswerCard:
    special = _build_module_disambiguation_card(text)
    if special is not None:
        return special

    stripped = str(text).strip()
    response_mode = classify_response_mode(stripped)
    preamble, raw_sections = _split_sections(stripped)
    if not raw_sections:
        if preamble:
            return SupportAnswerCard(response_mode=response_mode, sections=(SupportAnswerSection("", preamble),))
        return SupportAnswerCard(response_mode=response_mode, sections=())

    display_sections: list[SupportAnswerSection] = []
    evidence_lines: list[str] = []
    explicit_next_sections: list[SupportAnswerSection] = []
    clarify_section: SupportAnswerSection | None = None
    boundary_sections: list[SupportAnswerSection] = []
    followup_lines: list[str] = []
    reply_example = ""

    for section in raw_sections:
        title = section.title
        if title in META_SECTION_TITLES:
            evidence_lines.extend(_normalize_lines(list(section.lines)))
            continue
        if title in {"【建议步骤】", "【建议下一步】"}:
            explicit_next_sections.append(section)
            continue
        if title in {"【需要确认的信息】", "【需要补充的信息】", "【需要补充的材料】"}:
            clarify_section = section
            continue
        if title == "【使用边界】":
            boundary_sections.append(section)
            continue
        if title == "【常用参数】":
            primary_lines, section_followups = _split_followup_lines(section.lines)
            if primary_lines:
                display_sections.append(SupportAnswerSection(title, tuple(primary_lines)))
            if section_followups:
                followup_lines.extend(_normalize_lines(section_followups))
                reply_example = reply_example or _extract_example(section_followups)
            continue
        display_sections.append(section)

    if preamble and not clarify_section and not stripped.startswith("需要补充以下信息："):
        display_sections.insert(0, SupportAnswerSection("【当前判断】", preamble))

    if clarify_section is not None:
        display_sections.append(clarify_section)
    elif stripped.startswith("需要补充以下信息："):
        requirement_text = stripped.split("：", 1)[1].splitlines()[0].strip()
        requirements = [item.strip() for item in re.split(r"[，,、]\s*", requirement_text) if item.strip()]
        if requirements:
            display_sections.append(
                SupportAnswerSection("【需要确认的信息】", tuple(_as_bullet(item) for item in requirements))
            )

    if explicit_next_sections:
        display_sections.extend(explicit_next_sections)
    else:
        derived_next_steps = _normalize_lines(followup_lines) or tuple(_default_next_steps(response_mode))
        if derived_next_steps:
            display_sections.append(SupportAnswerSection("【建议下一步】", derived_next_steps))

    requirement_lines: list[str] = []
    for section in display_sections:
        if section.title in {"【需要确认的信息】", "【需要补充的信息】", "【需要补充的材料】"}:
            requirement_lines = [
                line[2:].strip() if line.startswith("- ") else line.strip()
                for line in section.lines
                if line.strip()
            ]
            break
    reply_hint_lines = _reply_hint_lines(requirement_lines, example=reply_example)
    if reply_hint_lines:
        display_sections.append(SupportAnswerSection("【下一条可直接回复】", tuple(reply_hint_lines)))

    if evidence_lines:
        display_sections.append(SupportAnswerSection("【证据依据】", tuple(evidence_lines)))
    display_sections.extend(boundary_sections)

    return SupportAnswerCard(response_mode=response_mode, sections=tuple(display_sections))


def format_support_answer_card(text: str) -> str:
    card = build_support_answer_card(text)
    if not card.sections:
        return str(text).strip()
    if len(card.sections) == 1 and not card.sections[0].title:
        return "\n".join(card.sections[0].lines).strip()

    chunks: list[str] = []
    for section in card.sections:
        if section.title:
            chunks.append(section.title)
        chunks.extend(section.lines)
        chunks.append("")
    return "\n".join(chunks[:-1]).strip()
