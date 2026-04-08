from sentieon_assist.config import load_config


def test_load_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_BACKEND", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_BASE_URL", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_MODEL", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_API_KEY", raising=False)
    config = load_config()
    assert config.ollama_base_url == "http://127.0.0.1:11434"
    assert config.ollama_model == "gemma4:e4b"
    assert config.ollama_keep_alive == "30m"
    assert config.llm_fallback_backend == ""
    assert config.llm_fallback_base_url == ""
    assert config.llm_fallback_model == ""
    assert config.llm_fallback_api_key == ""


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://customer-box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:latest")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "2h")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_BACKEND", "openai_compatible")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_API_KEY", "secret-token")
    monkeypatch.setenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", "/tmp/sentieon-knowledge")
    monkeypatch.setenv("SENTIEON_ASSIST_SOURCE_DIR", "/tmp/sentieon-sources")
    config = load_config()
    assert config.ollama_base_url == "http://customer-box:11434"
    assert config.ollama_model == "gemma4:latest"
    assert config.ollama_keep_alive == "2h"
    assert config.llm_fallback_backend == "openai_compatible"
    assert config.llm_fallback_base_url == "https://llm.example/v1"
    assert config.llm_fallback_model == "gpt-5.4-mini"
    assert config.llm_fallback_api_key == "secret-token"
    assert config.knowledge_dir == "/tmp/sentieon-knowledge"
    assert config.source_dir == "/tmp/sentieon-sources"
