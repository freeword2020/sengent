from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from types import SimpleNamespace

from sentieon_assist.chat_events import (
    event_check_missing_info,
    event_detect_issue_type,
    event_prepare_reference_answer,
)
from sentieon_assist.chat_ui import (
    ASSISTANT_ACCENT_STYLE,
    ASSISTANT_BORDER_STYLE,
    EVENT_ACCENT_STYLE,
    EVENT_BORDER_STYLE,
    USER_ACCENT_STYLE,
    USER_BORDER_STYLE,
    WELCOME_ACCENT_STYLE,
    WELCOME_BORDER_STYLE,
    WELCOME_LOGO_LINES,
    WELCOME_SUBTITLE,
    ChatUI,
)


class CapturingConsole:
    def __init__(self) -> None:
        self.renderables: list[object] = []

    def print(self, renderable: object) -> None:
        self.renderables.append(renderable)


def test_render_welcome_panel_contains_brand_poster_and_summary():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    text = console.export_text()
    assert WELCOME_LOGO_LINES[0] in text
    assert WELCOME_SUBTITLE in text
    assert "我可以帮你做什么" in text
    assert "模块、参数、参考脚本查询" in text
    assert "提问建议" in text
    assert "/quit" in text
    assert "/help" in text
    assert "/feedback" in text
    assert "/help  /quit  /reset  /feedback" in text
    assert "示例提问" not in text
    assert "样本 -> 数据流" not in text
    assert "o==x" not in text


def test_render_welcome_panel_stays_compact_on_wide_terminal():
    console = Console(record=True, width=180)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    lines = [
        line.rstrip()
        for line in console.export_text().splitlines()
        if line.strip() and set(line.strip()) != {"─"}
    ]
    assert max(len(line) for line in lines) < 140


def test_render_welcome_panel_uses_tight_vertical_layout():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    panel_lines = [
        line
        for line in console.export_text().splitlines()
        if line.strip() and set(line.strip()) != {"─"}
    ]
    assert len(panel_lines) <= 16


def test_render_welcome_panel_uses_brand_palette():
    console = CapturingConsole()
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    panel, rule = console.renderables
    assert isinstance(panel, Panel)
    assert panel.border_style == WELCOME_BORDER_STYLE
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "Sengent"
    assert panel.title.style == WELCOME_ACCENT_STYLE
    assert isinstance(rule, Rule)
    assert rule.style == WELCOME_BORDER_STYLE


def test_render_user_message_marks_user_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_user_message("DNAscope 是做什么的")

    text = console.export_text()
    assert "你" in text
    assert "DNAscope 是做什么的" in text


def test_render_user_message_uses_user_palette():
    console = CapturingConsole()
    ui = ChatUI(console=console)

    ui.render_user_message("DNAscope 是做什么的")

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.border_style == USER_BORDER_STYLE
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "你"
    assert panel.title.style == USER_ACCENT_STYLE


def test_render_answer_marks_sengent_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_answer(
        "【资料查询】\n- 命中模块索引：DNAscope\n\n【模块介绍】\nDNAscope：用于 germline variant calling"
    )

    text = console.export_text()
    assert "Sengent" in text
    assert "【模块介绍】" in text
    assert "DNAscope：用于 germline variant calling" in text
    assert "【证据依据】" in text
    assert "【资料查询】" not in text


def test_render_answer_uses_sengent_palette():
    console = CapturingConsole()
    ui = ChatUI(console=console)

    ui.render_answer("【模块介绍】\nDNAscope：用于 germline variant calling")

    assert console.renderables[0] == ""
    panel = console.renderables[1]
    assert isinstance(panel, Panel)
    assert panel.border_style == ASSISTANT_BORDER_STYLE
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "Sengent"
    assert panel.title.style == ASSISTANT_ACCENT_STYLE


def test_render_event_stream_prints_all_events():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_events(
        [
            "已识别问题类型：资料查询",
            "正在检索本地资料",
            "正在整理参考答案",
        ]
    )

    text = console.export_text()
    assert "事件流" in text
    assert "已识别问题类型：资料查询" in text
    assert "正在整理参考答案" in text


def test_render_events_uses_event_palette():
    console = CapturingConsole()
    ui = ChatUI(console=console)

    ui.render_events(["已识别问题类型：资料查询"])

    panel = console.renderables[0]
    assert isinstance(panel, Panel)
    assert panel.border_style == EVENT_BORDER_STYLE
    assert isinstance(panel.title, Text)
    assert panel.title.plain == "事件流"
    assert panel.title.style == EVENT_ACCENT_STYLE


def test_render_streaming_answer_header_uses_sengent_palette():
    console = CapturingConsole()
    ui = ChatUI(console=console)

    ui.render_streaming_answer_header()

    assert console.renderables[0] == ""
    rule = console.renderables[1]
    assert isinstance(rule, Rule)
    assert isinstance(rule.title, Text)
    assert rule.title.plain == "Sengent"
    assert rule.title.style == ASSISTANT_ACCENT_STYLE
    assert rule.style == ASSISTANT_BORDER_STYLE


def test_render_streaming_answer_header_adds_leading_spacing():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_streaming_answer_header()

    lines = console.export_text().splitlines()
    assert lines[0] == ""


def test_render_answer_adds_leading_spacing():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_answer("【模块介绍】\nDNAscope：用于 germline variant calling")

    lines = console.export_text().splitlines()
    assert lines[0] == ""


def test_render_answer_shows_reply_hint_for_clarify_answer():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_answer(
        "需要补充以下信息：Sentieon 版本\n\n"
        "【当前判断】\n"
        "- 现有信息还不足以给出确定性建议。\n\n"
        "【需要确认的信息】\n"
        "- Sentieon 版本\n\n"
        "【建议下一步】\n"
        "- 请直接补充上面列出的关键信息后再继续。"
    )

    text = console.export_text()
    assert "【下一条可直接回复】" in text
    assert "Sentieon 版本：<请填写>" in text


def test_missing_info_event_text_is_deterministic():
    assert event_detect_issue_type("license") == "已识别问题类型：许可证问题"
    assert event_detect_issue_type("install") == "已识别问题类型：安装问题"
    assert event_check_missing_info(["version"]) == "发现需要补充的信息：Sentieon 版本"


def test_event_check_missing_info_uses_profile_owned_field_labels(monkeypatch):
    import sentieon_assist.chat_events as chat_events

    monkeypatch.setattr(
        chat_events,
        "get_vendor_profile",
        lambda vendor_id: SimpleNamespace(
            runtime_wording=SimpleNamespace(
                field_labels={
                    "version": "产品版本",
                    "error": "完整报错信息",
                    "input_type": "输入文件类型",
                    "data_type": "数据类型",
                    "step": "执行步骤",
                }
            )
        ),
    )
    monkeypatch.setattr(chat_events, "resolve_vendor_id", lambda vendor_id=None: "acme")

    assert (
        event_check_missing_info(["version", "step"], vendor_id="acme")
        == "发现需要补充的信息：产品版本, 执行步骤"
    )


def test_reference_path_event_text_is_deterministic():
    assert event_prepare_reference_answer() == "正在整理参考答案"
