from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    ollama_base_url: str
    ollama_model: str
    ollama_keep_alive: str
    knowledge_dir: str
    source_dir: str


def load_config() -> AppConfig:
    return AppConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
        knowledge_dir=os.getenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", ""),
        source_dir=os.getenv(
            "SENTIEON_ASSIST_SOURCE_DIR",
            str((__import__("pathlib").Path(__file__).resolve().parents[2] / "sentieon-note")),
        ),
    )
