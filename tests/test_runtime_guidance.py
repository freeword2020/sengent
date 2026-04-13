from sentieon_assist.runtime_guidance import format_ollama_runtime_error, format_runtime_provider_error


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


def test_format_runtime_provider_error_for_hosted_provider_connectivity_failure():
    text = format_runtime_provider_error(
        provider="openai_compatible",
        error_text="openai-compatible request failed: connection refused",
        base_url="https://api.example.com/v1",
        model="gpt-4.1",
        issue_kind="connectivity",
    )

    assert "openai_compatible" in text
    assert "https://api.example.com/v1" in text
    assert "gpt-4.1" in text
    assert "ollama pull" not in text
    assert "API key" in text or "api_key" in text


def test_format_runtime_provider_error_for_ollama_compatibility():
    text = format_runtime_provider_error(
        provider="ollama",
        error_text="local ollama request failed: connection refused",
        base_url="http://127.0.0.1:11434",
        model="gemma4:e4b",
        issue_kind="connectivity",
    )

    assert "Ollama" in text
    assert "ollama pull gemma4:e4b" in text
