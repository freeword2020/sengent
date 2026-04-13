import pytest

from sentieon_assist.config import load_config


def test_load_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_BACKEND", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_BASE_URL", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_MODEL", raising=False)
    monkeypatch.delenv("SENGENT_LLM_FALLBACK_API_KEY", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_MODEL", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_API_KEY", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_KEEP_ALIVE", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_MAX_CONTEXT", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR", raising=False)
    config = load_config()
    assert config.runtime_llm_provider == "ollama"
    assert config.runtime_llm_base_url == "http://127.0.0.1:11434"
    assert config.runtime_llm_model == "gemma4:e4b"
    assert config.runtime_llm_api_key == ""
    assert config.runtime_llm_keep_alive == "30m"
    assert config.llm_fallback_backend == ""
    assert config.llm_fallback_base_url == ""
    assert config.llm_fallback_model == ""
    assert config.llm_fallback_api_key == ""
    assert config.runtime_llm_supports_tools is False
    assert config.runtime_llm_supports_json_schema is False
    assert config.runtime_llm_supports_reasoning_effort is False
    assert config.runtime_llm_supports_streaming is True
    assert config.runtime_llm_max_context == 0
    assert config.runtime_llm_prompt_cache_behavior == "provider_managed"


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_API_KEY", "runtime-secret")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_KEEP_ALIVE", "2h")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_BACKEND", "openai_compatible")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("SENGENT_LLM_FALLBACK_API_KEY", "secret-token")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS", "yes")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA", "no")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT", "1")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING", "0")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_MAX_CONTEXT", "8192")
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR", "provider_managed")
    monkeypatch.setenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", "/tmp/sentieon-knowledge")
    monkeypatch.setenv("SENTIEON_ASSIST_SOURCE_DIR", "/tmp/sentieon-sources")
    config = load_config()
    assert config.runtime_llm_provider == "openai_compatible"
    assert config.runtime_llm_base_url == "https://llm.example/v1"
    assert config.runtime_llm_model == "gpt-5.4-mini"
    assert config.runtime_llm_api_key == "runtime-secret"
    assert config.runtime_llm_keep_alive == "2h"
    assert config.llm_fallback_backend == "openai_compatible"
    assert config.llm_fallback_base_url == "https://llm.example/v1"
    assert config.llm_fallback_model == "gpt-5.4-mini"
    assert config.llm_fallback_api_key == "secret-token"
    assert config.runtime_llm_supports_tools is True
    assert config.runtime_llm_supports_json_schema is False
    assert config.runtime_llm_supports_reasoning_effort is True
    assert config.runtime_llm_supports_streaming is False
    assert config.runtime_llm_max_context == 8192
    assert config.runtime_llm_prompt_cache_behavior == "provider_managed"
    assert config.knowledge_dir == "/tmp/sentieon-knowledge"
    assert config.source_dir == "/tmp/sentieon-sources"


def test_load_config_maps_legacy_ollama_env_to_canonical_runtime_contract(monkeypatch):
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_MODEL", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_API_KEY", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_KEEP_ALIVE", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://customer-box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:latest")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "2h")
    config = load_config()

    assert config.runtime_llm_provider == "ollama"
    assert config.runtime_llm_base_url == "http://customer-box:11434"
    assert config.runtime_llm_model == "gemma4:latest"
    assert config.runtime_llm_api_key == ""
    assert config.runtime_llm_keep_alive == "2h"
    assert config.runtime_llm_supports_streaming is True
    assert config.runtime_llm_prompt_cache_behavior == "provider_managed"


def test_load_config_defaults_follow_selected_provider(monkeypatch):
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_MAX_CONTEXT", raising=False)
    monkeypatch.delenv("SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR", raising=False)

    config = load_config()

    assert config.runtime_llm_provider == "openai_compatible"
    assert config.runtime_llm_supports_tools is False
    assert config.runtime_llm_supports_json_schema is False
    assert config.runtime_llm_supports_reasoning_effort is False
    assert config.runtime_llm_supports_streaming is True
    assert config.runtime_llm_max_context == 0
    assert config.runtime_llm_prompt_cache_behavior == "unknown"


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS", "maybe"),
        ("SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA", "2"),
        ("SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT", "truthy"),
        ("SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING", "enabled"),
    ],
)
def test_load_config_rejects_invalid_runtime_capability_bool(monkeypatch, env_name, value):
    monkeypatch.setenv(env_name, value)
    with pytest.raises(ValueError, match=env_name):
        load_config()


@pytest.mark.parametrize("value", ["-1", "not-an-int"])
def test_load_config_rejects_invalid_runtime_capability_max_context(monkeypatch, value):
    monkeypatch.setenv("SENGENT_RUNTIME_LLM_MAX_CONTEXT", value)
    with pytest.raises(ValueError, match="SENGENT_RUNTIME_LLM_MAX_CONTEXT"):
        load_config()
