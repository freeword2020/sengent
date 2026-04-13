from __future__ import annotations

import os
from dataclasses import dataclass

from sentieon_assist.app_paths import default_source_dir
from sentieon_assist.llm_capabilities import default_capabilities, normalize_provider


@dataclass(frozen=True)
class AppConfig:
    runtime_llm_provider: str
    runtime_llm_base_url: str
    runtime_llm_model: str
    runtime_llm_api_key: str
    runtime_llm_keep_alive: str
    runtime_llm_supports_tools: bool
    runtime_llm_supports_json_schema: bool
    runtime_llm_supports_reasoning_effort: bool
    runtime_llm_supports_streaming: bool
    runtime_llm_max_context: int
    runtime_llm_prompt_cache_behavior: str
    llm_fallback_backend: str
    llm_fallback_base_url: str
    llm_fallback_model: str
    llm_fallback_api_key: str
    knowledge_dir: str
    source_dir: str
    factory_hosted_provider: str = ""
    factory_hosted_base_url: str = ""
    factory_hosted_model: str = ""
    factory_hosted_api_key: str = ""

    @property
    def ollama_base_url(self) -> str:
        return self.runtime_llm_base_url

    @property
    def ollama_model(self) -> str:
        return self.runtime_llm_model

    @property
    def ollama_keep_alive(self) -> str:
        return self.runtime_llm_keep_alive


def _parse_strict_bool(value: str, *, env_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{env_name} must be one of 1/true/yes/on or 0/false/no/off: {value!r}")


def _parse_non_negative_int(value: str, *, env_name: str) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{env_name} must be a non-negative integer: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{env_name} must be a non-negative integer: {value!r}")
    return parsed


def _read_env(name: str, *, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_config() -> AppConfig:
    runtime_provider_raw = _read_env("SENGENT_RUNTIME_LLM_PROVIDER")
    runtime_provider = normalize_provider(runtime_provider_raw or "ollama")
    factory_provider_raw = _read_env("SENGENT_FACTORY_HOSTED_PROVIDER")
    factory_provider = normalize_provider(factory_provider_raw) if factory_provider_raw else ""
    provider_defaults = default_capabilities(runtime_provider)

    runtime_base_url = _read_env("SENGENT_RUNTIME_LLM_BASE_URL")
    runtime_model = _read_env("SENGENT_RUNTIME_LLM_MODEL")
    runtime_api_key = _read_env("SENGENT_RUNTIME_LLM_API_KEY")
    runtime_keep_alive = _read_env("SENGENT_RUNTIME_LLM_KEEP_ALIVE")
    if runtime_provider == "ollama":
        runtime_base_url = runtime_base_url or _read_env("OLLAMA_BASE_URL", default="http://127.0.0.1:11434")
        runtime_model = runtime_model or _read_env("OLLAMA_MODEL", default="gemma4:e4b")
        runtime_keep_alive = runtime_keep_alive or _read_env("OLLAMA_KEEP_ALIVE", default="30m")

    supports_tools_raw = _read_env("SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS")
    supports_json_schema_raw = _read_env("SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA")
    supports_reasoning_effort_raw = _read_env("SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT")
    supports_streaming_raw = _read_env("SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING")
    max_context_raw = _read_env("SENGENT_RUNTIME_LLM_MAX_CONTEXT")
    prompt_cache_behavior = _read_env("SENGENT_RUNTIME_LLM_PROMPT_CACHE_BEHAVIOR") or provider_defaults.prompt_cache_behavior
    return AppConfig(
        runtime_llm_provider=runtime_provider,
        runtime_llm_base_url=runtime_base_url,
        runtime_llm_model=runtime_model,
        runtime_llm_api_key=runtime_api_key,
        runtime_llm_keep_alive=runtime_keep_alive,
        runtime_llm_supports_tools=_parse_strict_bool(supports_tools_raw, env_name="SENGENT_RUNTIME_LLM_SUPPORTS_TOOLS")
        if supports_tools_raw
        else provider_defaults.supports_tools,
        runtime_llm_supports_json_schema=_parse_strict_bool(
            supports_json_schema_raw, env_name="SENGENT_RUNTIME_LLM_SUPPORTS_JSON_SCHEMA"
        )
        if supports_json_schema_raw
        else provider_defaults.supports_json_schema,
        runtime_llm_supports_reasoning_effort=_parse_strict_bool(
            supports_reasoning_effort_raw, env_name="SENGENT_RUNTIME_LLM_SUPPORTS_REASONING_EFFORT"
        )
        if supports_reasoning_effort_raw
        else provider_defaults.supports_reasoning_effort,
        runtime_llm_supports_streaming=_parse_strict_bool(
            supports_streaming_raw, env_name="SENGENT_RUNTIME_LLM_SUPPORTS_STREAMING"
        )
        if supports_streaming_raw
        else provider_defaults.supports_streaming,
        runtime_llm_max_context=_parse_non_negative_int(max_context_raw, env_name="SENGENT_RUNTIME_LLM_MAX_CONTEXT")
        if max_context_raw
        else provider_defaults.max_context,
        runtime_llm_prompt_cache_behavior=prompt_cache_behavior,
        llm_fallback_backend=os.getenv("SENGENT_LLM_FALLBACK_BACKEND", "").strip(),
        llm_fallback_base_url=os.getenv("SENGENT_LLM_FALLBACK_BASE_URL", "").strip(),
        llm_fallback_model=os.getenv("SENGENT_LLM_FALLBACK_MODEL", "").strip(),
        llm_fallback_api_key=os.getenv("SENGENT_LLM_FALLBACK_API_KEY", "").strip(),
        knowledge_dir=os.getenv("SENTIEON_ASSIST_KNOWLEDGE_DIR", ""),
        source_dir=os.getenv("SENTIEON_ASSIST_SOURCE_DIR", str(default_source_dir())),
        factory_hosted_provider=factory_provider,
        factory_hosted_base_url=_read_env("SENGENT_FACTORY_HOSTED_BASE_URL"),
        factory_hosted_model=_read_env("SENGENT_FACTORY_HOSTED_MODEL"),
        factory_hosted_api_key=_read_env("SENGENT_FACTORY_HOSTED_API_KEY"),
    )
