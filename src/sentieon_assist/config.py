from __future__ import annotations

import os
from dataclasses import dataclass

from sentieon_assist.app_paths import default_source_dir


@dataclass(frozen=True)
class AppConfig:
    ollama_base_url: str
    ollama_model: str
    ollama_keep_alive: str
    llm_fallback_backend: str
    llm_fallback_base_url: str
    llm_fallback_model: str
    llm_fallback_api_key: str
    knowledge_dir: str
    source_dir: str


def load_config() -> AppConfig:
    return AppConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        llm_fallback_backend=os.getenv("SENGENT_LLM_FALLBACK_BACKEND", "").strip(),
        llm_fallback_base_url=os.getenv("SENGENT_LLM_FALLBACK_BASE_URL", "").strip(),
        llm_fallback_model=os.getenv("SENGENT_LLM_FALLBACK_MODEL", "").strip(),
        llm_fallback_api_key=os.getenv("SENGENT_LLM_FALLBACK_API_KEY", "").strip(),
        knowledge_dir=os.getenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", ""),
        source_dir=os.getenv("SENTIEON_ASSIST_SOURCE_DIR", str(default_source_dir())),
    )
