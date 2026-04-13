from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from sentieon_assist.support_experience import format_support_answer_card

WELCOME_BORDER_STYLE = "dark_orange3"
WELCOME_ACCENT_STYLE = "bold dark_orange3"
WELCOME_SHADOW_STYLE = "bold color(94)"
WELCOME_SUBTITLE_STYLE = "dark_orange3"
USER_BORDER_STYLE = "bright_cyan"
USER_ACCENT_STYLE = "bold bright_cyan"
EVENT_BORDER_STYLE = "grey50"
EVENT_ACCENT_STYLE = "bold grey70"
ASSISTANT_BORDER_STYLE = "dark_orange3"
ASSISTANT_ACCENT_STYLE = "bold dark_orange3"
WELCOME_SUBTITLE = "Sentieon Local Support Agent 1.0"
WELCOME_LOGO_LINES = (
    "████▓ ████▓ █  █▓ ████▓ ████▓ █  █▓ ████▓",
    "█▓    █▓    ██ █▓ █▓    █▓    ██ █▓  ██▓ ",
    " ███▓ ███▓  █ ███ █ ██▓ ███▓  █ ███  ██▓ ",
    "   █▓ █▓    █  ██ █  █▓ █▓    █  ██  ██▓ ",
    "████▓ ████▓ █   █ ████▓ ████▓ █   █  ██▓ ",
    "▓▓▓▓  ▓▓▓▓  ▓   ▓ ▓▓▓▓  ▓▓▓▓  ▓   ▓  ▓▓  ",
)


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


def _render_logo_line(line: str) -> Text:
    text = Text()
    for char in line:
        if char == "█":
            text.append(char, style=WELCOME_ACCENT_STYLE)
        elif char == "▓":
            text.append(char, style=WELCOME_SHADOW_STYLE)
        else:
            text.append(char)
    return text


@dataclass
class ChatUI:
    console: Console = field(default_factory=build_console)

    def render_welcome_panel(self) -> None:
        left = Group(
            Text(""),
            *[_render_logo_line(line) for line in WELCOME_LOGO_LINES],
            Align.center(Text(WELCOME_SUBTITLE, style=WELCOME_SUBTITLE_STYLE)),
        )
        right = Group(
            Text("我可以帮你做什么", style=WELCOME_ACCENT_STYLE),
            Text("- 许可证排障"),
            Text("- 安装排障"),
            Text("- 模块、参数、参考脚本查询"),
            Text("常用命令", style=WELCOME_ACCENT_STYLE),
            Text("- /help  /quit  /reset  /feedback"),
            Text("提问建议", style=WELCOME_ACCENT_STYLE),
            Text("- 优先带版本号"),
            Text("- 报错尽量保留原文"),
        )
        grid = Table.grid(expand=False, padding=(0, 3))
        grid.add_column()
        grid.add_column()
        grid.add_row(left, right)
        self.console.print(
            Panel.fit(
                grid,
                title=Text("Sengent", style=WELCOME_ACCENT_STYLE),
                border_style=WELCOME_BORDER_STYLE,
            )
        )
        self.console.print(Rule(style=WELCOME_BORDER_STYLE))

    def render_user_message(self, text: str) -> None:
        self.console.print(
            Panel(
                text,
                title=Text("你", style=USER_ACCENT_STYLE),
                border_style=USER_BORDER_STYLE,
            )
        )

    def render_events(self, events: list[str]) -> None:
        if not events:
            return
        body = "\n".join(f"- {event}" for event in events)
        self.console.print(
            Panel(
                body,
                title=Text("事件流", style=EVENT_ACCENT_STYLE),
                border_style=EVENT_BORDER_STYLE,
            )
        )

    def _print_assistant_spacing(self) -> None:
        self.console.print("")

    def render_streaming_answer_header(self) -> None:
        self._print_assistant_spacing()
        self.console.print(
            Rule(
                Text("Sengent", style=ASSISTANT_ACCENT_STYLE),
                style=ASSISTANT_BORDER_STYLE,
            )
        )

    def render_answer(self, text: str) -> None:
        self._print_assistant_spacing()
        self.console.print(
            Panel(
                format_support_answer_card(text),
                title=Text("Sengent", style=ASSISTANT_ACCENT_STYLE),
                border_style=ASSISTANT_BORDER_STYLE,
            )
        )
