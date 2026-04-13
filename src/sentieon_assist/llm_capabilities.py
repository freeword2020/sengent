from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMCapabilityDescriptor:
    provider: str
    supports_tools: bool
    supports_json_schema: bool
    supports_reasoning_effort: bool
    supports_streaming: bool
    max_context: int
    prompt_cache_behavior: str


_PROVIDER_DEFAULTS: dict[str, LLMCapabilityDescriptor] = {
    "ollama": LLMCapabilityDescriptor(
        provider="ollama",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="provider_managed",
    ),
    "openai_compatible": LLMCapabilityDescriptor(
        provider="openai_compatible",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="unknown",
    ),
}

_PROVIDER_ALIASES = {
    "openai-compatible": "openai_compatible",
    "openai_compatible": "openai_compatible",
    "ollama": "ollama",
}


def normalize_provider(provider: str) -> str:
    value = str(provider).strip().lower()
    return _PROVIDER_ALIASES.get(value, value)


def default_capabilities(provider: str) -> LLMCapabilityDescriptor:
    normalized = normalize_provider(provider)
    try:
        return _PROVIDER_DEFAULTS[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported llm provider: {provider}") from exc
