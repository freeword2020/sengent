from sentieon_assist.runtime_guidance import format_ollama_runtime_error


def test_format_ollama_runtime_error_for_connectivity_failure():
    text = format_ollama_runtime_error(
        error_text="local ollama request failed: connection refused",
        base_url="http://127.0.0.1:11434",
        model="gemma4:e4b",
        issue_kind="connectivity",
    )

    assert "无法访问本地 Ollama HTTP API" in text
    assert "ollama pull gemma4:e4b" in text


def test_format_ollama_runtime_error_for_missing_model():
    text = format_ollama_runtime_error(
        error_text="target model is not available: gemma4:e4b",
        base_url="http://127.0.0.1:11434",
        model="gemma4:e4b",
        issue_kind="model_missing",
    )

    assert "当前可以访问本地 Ollama HTTP API" in text
    assert "还没有目标模型" in text
    assert "ollama pull gemma4:e4b" in text
