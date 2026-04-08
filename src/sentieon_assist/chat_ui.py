from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


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
        left = Group(
            Text("欢迎使用 Sengent", style="bold"),
            Text("本地 Sentieon 支持助手", style="dim"),
            Text(""),
            Text("示例提问", style="bold"),
            Text("- Sentieon 202503 license 报错"),
            Text("- install 失败，命令不可用"),
            Text("- DNAscope 是做什么的"),
        )
        right = Group(
            Text("我可以帮你做什么", style="bold"),
            Text("- 许可证排障"),
            Text("- 安装排障"),
            Text("- 模块和参数查询"),
            Text(""),
            Text("常用命令", style="bold"),
            Text("- /quit"),
            Text("- /reset"),
            Text(""),
            Text("提问建议", style="bold"),
            Text("- 优先带上版本号"),
            Text("- 报错尽量保留原文"),
        )
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(left, right)
        self.console.print(
            Panel(
                grid,
                title="Sengent",
            )
        )
        self.console.print(Rule())

    def render_user_message(self, text: str) -> None:
        self.console.print(Panel(text, title="你"))

    def render_events(self, events: list[str]) -> None:
        if not events:
            return
        body = "\n".join(f"- {event}" for event in events)
        self.console.print(Panel(body, title="事件流"))

    def render_streaming_answer_header(self) -> None:
        self.console.print(Rule("Sengent"))

    def render_answer(self, text: str) -> None:
        self.console.print(Panel(text, title="Sengent"))
