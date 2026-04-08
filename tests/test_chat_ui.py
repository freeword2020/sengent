from rich.console import Console

from sentieon_assist.chat_ui import ChatUI


def test_render_welcome_panel_contains_brand_and_examples():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    text = console.export_text()
    assert "Sengent" in text
    assert "我可以帮你做什么" in text
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
