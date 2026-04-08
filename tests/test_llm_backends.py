from sentieon_assist.config import AppConfig
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


def test_build_backend_router_supports_optional_openai_compatible_fallback():
    config = AppConfig(
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="gemma4:e4b",
        ollama_keep_alive="30m",
        llm_fallback_backend="openai_compatible",
        llm_fallback_base_url="https://llm.example/v1",
        llm_fallback_model="gpt-5.4-mini",
        llm_fallback_api_key="secret-token",
        knowledge_dir="",
        source_dir="/tmp/sentieon-note",
    )

    router = build_backend_router(config)

    assert isinstance(router.primary, OllamaBackend)
    assert isinstance(router.fallback, OpenAICompatibleBackend)
