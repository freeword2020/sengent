import pytest

from sentieon_assist.config import AppConfig
from sentieon_assist.llm_capabilities import LLMCapabilityDescriptor
from sentieon_assist.llm_backends import BackendRouter, OllamaBackend, OpenAICompatibleBackend, build_backend_router


class FakeBackend:
    def __init__(self, name: str, *, generate_error: Exception | None = None, stream_error: Exception | None = None):
        self.name = name
        self.generate_error = generate_error
        self.stream_error = stream_error
        self.calls: list[tuple[str, str]] = []

    def probe(self):
        self.calls.append(("probe", ""))
        return {"ok": True, "model_available": True}

    def warmup(self):
        self.calls.append(("warmup", ""))

    def generate(self, prompt: str) -> str:
        self.calls.append(("generate", prompt))
        if self.generate_error is not None:
            raise self.generate_error
        return f"{self.name}:{prompt}"

    def generate_stream(self, prompt: str, *, on_chunk):
        self.calls.append(("generate_stream", prompt))
        if self.stream_error is not None:
            raise self.stream_error
        chunk = f"{self.name}:{prompt}"
        on_chunk(chunk)
        return chunk


def test_backend_router_prefers_primary_backend():
    primary = FakeBackend("primary")
    fallback = FakeBackend("fallback")
    router = BackendRouter(primary=primary, fallback=fallback)

    assert router.generate("hello") == "primary:hello"

    streamed: list[str] = []
    assert router.generate_stream("stream", on_chunk=streamed.append) == "primary:stream"

    assert primary.calls == [("generate", "hello"), ("generate_stream", "stream")]
    assert fallback.calls == []


def test_backend_router_uses_fallback_when_primary_generation_fails():
    primary = FakeBackend("primary", generate_error=RuntimeError("primary unavailable"))
    fallback = FakeBackend("fallback")
    router = BackendRouter(primary=primary, fallback=fallback)

    assert router.generate("hello") == "fallback:hello"

    assert primary.calls == [("generate", "hello")]
    assert fallback.calls == [("generate", "hello")]


def test_build_backend_router_exposes_primary_capabilities():
    config = AppConfig(
        runtime_llm_provider="ollama",
        runtime_llm_base_url="http://127.0.0.1:11434",
        runtime_llm_model="gemma4:e4b",
        runtime_llm_api_key="",
        runtime_llm_keep_alive="30m",
        llm_fallback_backend="",
        llm_fallback_base_url="",
        llm_fallback_model="",
        llm_fallback_api_key="",
        runtime_llm_supports_tools=False,
        runtime_llm_supports_json_schema=False,
        runtime_llm_supports_reasoning_effort=False,
        runtime_llm_supports_streaming=True,
        runtime_llm_max_context=0,
        runtime_llm_prompt_cache_behavior="provider_managed",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    router = build_backend_router(config)

    assert isinstance(router.primary, OllamaBackend)
    assert router.primary_capabilities == LLMCapabilityDescriptor(
        provider="ollama",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="provider_managed",
    )


def test_build_backend_router_uses_openai_primary_with_conservative_capabilities():
    config = AppConfig(
        runtime_llm_provider="openai_compatible",
        runtime_llm_base_url="https://llm.example/v1",
        runtime_llm_model="gpt-5.4-mini",
        runtime_llm_api_key="secret-token",
        runtime_llm_keep_alive="30m",
        llm_fallback_backend="",
        llm_fallback_base_url="",
        llm_fallback_model="",
        llm_fallback_api_key="",
        runtime_llm_supports_tools=False,
        runtime_llm_supports_json_schema=False,
        runtime_llm_supports_reasoning_effort=False,
        runtime_llm_supports_streaming=True,
        runtime_llm_max_context=0,
        runtime_llm_prompt_cache_behavior="unknown",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    router = build_backend_router(config)

    assert isinstance(router.primary, OpenAICompatibleBackend)
    assert router.primary_capabilities == LLMCapabilityDescriptor(
        provider="openai_compatible",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="unknown",
    )


def test_build_backend_router_reflects_primary_capability_override():
    config = AppConfig(
        runtime_llm_provider="openai_compatible",
        runtime_llm_base_url="https://llm.example/v1",
        runtime_llm_model="gpt-5.4-mini",
        runtime_llm_api_key="secret-token",
        runtime_llm_keep_alive="30m",
        llm_fallback_backend="",
        llm_fallback_base_url="",
        llm_fallback_model="",
        llm_fallback_api_key="",
        runtime_llm_supports_tools=True,
        runtime_llm_supports_json_schema=True,
        runtime_llm_supports_reasoning_effort=True,
        runtime_llm_supports_streaming=False,
        runtime_llm_max_context=4096,
        runtime_llm_prompt_cache_behavior="provider_managed",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    router = build_backend_router(config)

    assert isinstance(router.primary, OpenAICompatibleBackend)
    assert router.primary_capabilities == LLMCapabilityDescriptor(
        provider="openai_compatible",
        supports_tools=True,
        supports_json_schema=True,
        supports_reasoning_effort=True,
        supports_streaming=False,
        max_context=4096,
        prompt_cache_behavior="provider_managed",
    )


def test_openai_compatible_backend_uses_conservative_default_capabilities():
    backend = OpenAICompatibleBackend(base_url="https://llm.example/v1", model="gpt-5.4-mini", api_key="secret-token")

    assert backend.capabilities == LLMCapabilityDescriptor(
        provider="openai_compatible",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="unknown",
    )


def test_build_backend_router_uses_provider_capabilities_for_fallback():
    config = AppConfig(
        runtime_llm_provider="ollama",
        runtime_llm_base_url="http://127.0.0.1:11434",
        runtime_llm_model="gemma4:e4b",
        runtime_llm_api_key="",
        runtime_llm_keep_alive="30m",
        llm_fallback_backend="openai_compatible",
        llm_fallback_base_url="https://llm.example/v1",
        llm_fallback_model="gpt-5.4-mini",
        llm_fallback_api_key="secret-token",
        runtime_llm_supports_tools=False,
        runtime_llm_supports_json_schema=False,
        runtime_llm_supports_reasoning_effort=False,
        runtime_llm_supports_streaming=True,
        runtime_llm_max_context=0,
        runtime_llm_prompt_cache_behavior="unknown",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    router = build_backend_router(config)

    assert isinstance(router.primary, OllamaBackend)
    assert isinstance(router.fallback, OpenAICompatibleBackend)
    assert router.fallback_capabilities == LLMCapabilityDescriptor(
        provider="openai_compatible",
        supports_tools=False,
        supports_json_schema=False,
        supports_reasoning_effort=False,
        supports_streaming=True,
        max_context=0,
        prompt_cache_behavior="unknown",
    )


def test_build_backend_router_rejects_unknown_primary_provider():
    config = AppConfig(
        runtime_llm_provider="anthropic",
        runtime_llm_base_url="https://llm.example/v1",
        runtime_llm_model="claude-3.7",
        runtime_llm_api_key="secret-token",
        runtime_llm_keep_alive="30m",
        llm_fallback_backend="",
        llm_fallback_base_url="",
        llm_fallback_model="",
        llm_fallback_api_key="",
        runtime_llm_supports_tools=False,
        runtime_llm_supports_json_schema=False,
        runtime_llm_supports_reasoning_effort=False,
        runtime_llm_supports_streaming=True,
        runtime_llm_max_context=0,
        runtime_llm_prompt_cache_behavior="unknown",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    with pytest.raises(ValueError, match="unsupported llm provider"):
        build_backend_router(config)
