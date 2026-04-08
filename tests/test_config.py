from sentieon_assist.config import load_config


def test_load_config_uses_defaults(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_KEEP_ALIVE", raising=False)
    config = load_config()
    assert config.ollama_base_url == "http://127.0.0.1:11434"
    assert config.ollama_model == "gemma4:e4b"
    assert config.ollama_keep_alive == "30m"


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://customer-box:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:latest")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "2h")
    monkeypatch.setenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", "/tmp/sentieon-knowledge")
    monkeypatch.setenv("SENTIEON_ASSIST_SOURCE_DIR", "/tmp/sentieon-sources")
    config = load_config()
    assert config.ollama_base_url == "http://customer-box:11434"
    assert config.ollama_model == "gemma4:latest"
    assert config.ollama_keep_alive == "2h"
    assert config.knowledge_dir == "/tmp/sentieon-knowledge"
    assert config.source_dir == "/tmp/sentieon-sources"
