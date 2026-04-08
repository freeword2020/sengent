from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule


def build_console() -> Console:
    return Console()


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

    def render_answer(self, text: str) -> None:
        self.console.print(Panel(text, title="Sengent"))
