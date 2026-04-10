from __future__ import annotations


def format_ollama_runtime_error(
    *,
    error_text: str,
    base_url: str,
    model: str,
) -> str:
    return "\n".join(
        [
            "【运行时模型不可用】",
            f"- 当前无法访问本地 Ollama HTTP API：{base_url}",
            f"- 当前目标模型：{model}",
            "",
            "【建议下一步】",
            "- 先执行 `sengent doctor`，确认当前机器是不是运行时主机。",
            "- 如果这台机器只做 build / review / activate，请执行 `sengent doctor --skip-ollama`。",
            "- 如果这台机器要聊天或单轮问答，请先安装并启动 Ollama。",
            f"- 如果 Ollama 已启动但模型还没准备，执行：`ollama pull {model}`。",
            "",
            "【原始错误】",
            f"- {error_text}",
        ]
    )


def doctor_guidance_lines(
    *,
    ollama: dict[str, object],
) -> list[str]:
    base_url = str(ollama.get("base_url", "")).strip() or "http://127.0.0.1:11434"
    model = str(ollama.get("model", "")).strip() or "gemma4:e4b"
    if ollama.get("skipped"):
        return [
            "当前已跳过 Ollama 探测；这适合 build-only 主机，不适合直接进入聊天运行时。",
            "如果这台机器后续要回答问题，请先安装并启动 Ollama，再重新执行 `sengent doctor`。",
            f"如需预拉取模型，可执行：`ollama pull {model}`。",
        ]
    if ollama.get("ok") and not ollama.get("model_available", True):
        return [
            f"Ollama API 已可访问，但本地还没有目标模型 `{model}`。",
            f"先执行：`ollama pull {model}`。",
            "拉取完成后重新执行 `sengent doctor`，再进入 `sengent chat`。",
        ]
    if ollama.get("ok"):
        return []
    return [
        f"当前无法连接 Ollama HTTP API：{base_url}。",
        "如果这台机器只做 build / review / activate，可改用 `sengent doctor --skip-ollama`。",
        "如果这台机器要运行聊天，请先安装并启动 Ollama。",
        f"确认服务就绪后，可执行：`ollama pull {model}`。",
    ]
