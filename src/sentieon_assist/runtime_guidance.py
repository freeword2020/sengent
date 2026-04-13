from __future__ import annotations


def format_runtime_provider_error(
    *,
    provider: str,
    error_text: str,
    base_url: str,
    model: str,
    issue_kind: str = "connectivity",
) -> str:
    normalized_provider = provider.strip().lower() or "ollama"
    is_ollama = normalized_provider == "ollama"

    if issue_kind == "model_missing":
        if is_ollama:
            headline = f"- 当前可以访问本地 Ollama HTTP API：{base_url}"
            detail = f"- 但本地还没有目标模型：{model}"
        else:
            headline = f"- 当前可以访问 hosted runtime：{base_url}"
            detail = f"- 但当前配置的模型不可用：{model}"
    else:
        if is_ollama:
            headline = f"- 当前无法访问本地 Ollama HTTP API：{base_url}"
            detail = f"- 当前目标模型：{model}"
        else:
            headline = f"- 当前无法访问 hosted runtime：{base_url}"
            detail = f"- 当前目标模型：{model}"

    if is_ollama:
        next_steps = [
            "- 先执行 `sengent doctor`，确认当前机器是不是运行时主机。",
            "- 如果这台机器只做 build / review / activate，请执行 `sengent doctor --skip-ollama`。",
            (
                f"- 如果这台机器要聊天或单轮问答，请执行：`ollama pull {model}`。"
                if issue_kind == "model_missing"
                else "- 如果这台机器要聊天或单轮问答，请先安装并启动 Ollama。"
            ),
            (
                "- 拉取完成后，再重新执行 `sengent doctor`。"
                if issue_kind == "model_missing"
                else f"- 如果 Ollama 已启动但模型还没准备，执行：`ollama pull {model}`。"
            ),
        ]
        provider_label = "Ollama"
    else:
        next_steps = [
            "- 先执行 `sengent doctor`，确认当前机器的 hosted runtime 配置。",
            "- 检查 `SENGENT_RUNTIME_LLM_BASE_URL` 是否指向正确的 OpenAI-compatible endpoint。",
            "- 检查 `SENGENT_RUNTIME_LLM_API_KEY` 是否已设置且可用。",
            "- 检查 `SENGENT_RUNTIME_LLM_MODEL` 是否与服务端可用模型一致。",
        ]
        if issue_kind == "model_missing":
            next_steps.append(
                f"- 如果服务端使用不同模型，请更新 `SENGENT_RUNTIME_LLM_MODEL`，而不是执行 `ollama pull {model}`。"
            )
        else:
            next_steps.append("- 如果这是临时网络或鉴权问题，修复后重新执行 `sengent doctor`。")
        provider_label = normalized_provider

    body = [
        "【运行时模型不可用】",
        f"provider: {provider_label}",
        headline,
        detail,
        "",
        "【建议下一步】",
        *next_steps,
        "",
        "【原始错误】",
        f"- {error_text}",
    ]
    if not is_ollama:
        body.append(
            "- Hosted runtime guidance: verify the base URL, API key, and model via `SENGENT_RUNTIME_LLM_BASE_URL`, `SENGENT_RUNTIME_LLM_API_KEY`, and `SENGENT_RUNTIME_LLM_MODEL`."
        )
    return "\n".join(body)


def format_ollama_runtime_error(
    *,
    error_text: str,
    base_url: str,
    model: str,
    issue_kind: str = "connectivity",
) -> str:
    return format_runtime_provider_error(
        provider="ollama",
        error_text=error_text,
        base_url=base_url,
        model=model,
        issue_kind=issue_kind,
    )


def doctor_guidance_lines(
    *,
    runtime_llm: dict[str, object],
) -> list[str]:
    provider = str(runtime_llm.get("provider", "")).strip().lower() or "ollama"
    base_url = str(runtime_llm.get("base_url", "")).strip() or "http://127.0.0.1:11434"
    model = str(runtime_llm.get("model", "")).strip() or "gemma4:e4b"
    if runtime_llm.get("skipped"):
        if provider == "ollama":
            return [
                "当前已跳过 Ollama 探测；这适合 build-only 主机，不适合直接进入聊天运行时。",
                "如果这台机器后续要回答问题，请先安装并启动 Ollama，再重新执行 `sengent doctor`。",
                f"如需预拉取模型，可执行：`ollama pull {model}`。",
            ]
        return [
            "当前已跳过 hosted runtime 探测；这适合 build-only 主机，不适合直接进入聊天运行时。",
            "如果这台机器后续要回答问题，请先确认 hosted runtime 配置，再重新执行 `sengent doctor`。",
            "检查 `SENGENT_RUNTIME_LLM_BASE_URL` / `SENGENT_RUNTIME_LLM_API_KEY` / `SENGENT_RUNTIME_LLM_MODEL`。",
        ]
    if runtime_llm.get("ok") and not runtime_llm.get("model_available", True):
        if provider == "ollama":
            return [
                f"Ollama API 已可访问，但本地还没有目标模型 `{model}`。",
                f"先执行：`ollama pull {model}`。",
                "拉取完成后重新执行 `sengent doctor`，再进入 `sengent chat`。",
            ]
        return [
            f"Hosted runtime API 已可访问，但当前配置的模型 `{model}` 不可用。",
            "检查 `SENGENT_RUNTIME_LLM_MODEL` 是否与服务端可用模型一致。",
            "确认配置后重新执行 `sengent doctor`，再进入 `sengent chat`。",
        ]
    if runtime_llm.get("ok"):
        return []
    if provider == "ollama":
        return [
            f"当前无法连接 Ollama HTTP API：{base_url}。",
            "如果这台机器只做 build / review / activate，可改用 `sengent doctor --skip-ollama`。",
            "如果这台机器要运行聊天，请先安装并启动 Ollama。",
            f"确认服务就绪后，可执行：`ollama pull {model}`。",
        ]
    return [
        f"当前无法连接 hosted runtime：{base_url}。",
        "如果这台机器只做 build / review / activate，可改用 `sengent doctor --skip-ollama`。",
        "如果这台机器要运行聊天，请先确认 hosted runtime endpoint 与 API key。",
        "检查 `SENGENT_RUNTIME_LLM_BASE_URL` / `SENGENT_RUNTIME_LLM_API_KEY` / `SENGENT_RUNTIME_LLM_MODEL`。",
    ]
