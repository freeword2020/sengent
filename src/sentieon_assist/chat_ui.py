from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule


class ConsoleCallbackWriter:
    encoding = "utf-8"

    def __init__(self, output_fn: Callable[[str], None]) -> None:
        self._output_fn = output_fn
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        return len(text)

    def flush(self) -> None:
        if not self._buffer:
            return
        text = self._buffer.rstrip("\n")
        self._buffer = ""
        if text:
            self._output_fn(text)

    def isatty(self) -> bool:
        return False


def build_console(*, output_fn: Callable[[str], None] | None = None) -> Console:
    if output_fn is None:
        return Console()
    return Console(file=ConsoleCallbackWriter(output_fn), force_terminal=False, color_system=None)


@dataclass
class ChatUI:
    console: Console = field(default_factory=build_console)

    def render_welcome_panel(self) -> None:
        self.console.print(
            Panel.fit(
                "欢迎使用 Sengent\n\n"
                "示例提问：\n"
                "- Sentieon 202503 license 报错\n"
                "- install 失败，命令不可用\n"
                "- DNAscope 是做什么的\n\n"
                "我可以帮你做什么：\n"
                "- 许可证排障\n"
                "- 安装排障\n"
                "- 模块和参数查询\n\n"
                "常用命令：\n"
                "- /quit\n"
                "- /reset",
                title="Sengent",
            )
        )
        self.console.print(Rule())

    def render_user_message(self, text: str) -> None:
        self.console.print(f"你\n{text}")

    def render_events(self, events: list[str]) -> None:
        if not events:
            return
        body = "\n".join(f"- {event}" for event in events)
        self.console.print(Panel(body, title="事件流"))

    def render_streaming_answer_header(self) -> None:
        self.console.print(Rule("Sengent"))

    def render_answer(self, text: str) -> None:
        self.console.print(Panel(text, title="Sengent"))
