from rich.console import Console

from sentieon_assist.chat_events import (
    event_check_missing_info,
    event_detect_issue_type,
    event_prepare_reference_answer,
)
from sentieon_assist.chat_ui import ChatUI


def test_render_welcome_panel_contains_brand_and_examples():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    text = console.export_text()
    assert "Sengent" in text
    assert "我可以帮你做什么" in text
    assert "示例提问" in text
    assert "提问建议" in text
    assert "/quit" in text


def test_render_user_message_marks_user_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_user_message("DNAscope 是做什么的")

    text = console.export_text()
    assert "你" in text
    assert "DNAscope 是做什么的" in text


def test_render_answer_marks_sengent_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_answer("【模块介绍】\nDNAscope：用于 germline variant calling")

    text = console.export_text()
    assert "Sengent" in text
    assert "【模块介绍】" in text


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


def test_missing_info_event_text_is_deterministic():
    assert event_detect_issue_type("license") == "已识别问题类型：许可证问题"
    assert event_detect_issue_type("install") == "已识别问题类型：安装问题"
    assert event_check_missing_info(["version"]) == "发现需要补充的信息：Sentieon 版本"


def test_reference_path_event_text_is_deterministic():
    assert event_prepare_reference_answer() == "正在整理参考答案"
