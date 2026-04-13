from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentieon_assist.config import AppConfig
from sentieon_assist.llm_capabilities import LLMCapabilityDescriptor, default_capabilities, normalize_provider
from sentieon_assist.llm_requests import LLMOutboundRequest, coerce_llm_outbound_request
from sentieon_assist.ollama_client import generate, generate_stream, probe_ollama, warmup_model


class LLMBackend(Protocol):
    capabilities: LLMCapabilityDescriptor

    def probe(self) -> dict[str, Any]:
        ...

    def generate(self, request: LLMOutboundRequest | str) -> str:
        ...

    def generate_stream(self, request: LLMOutboundRequest | str, *, on_chunk: Callable[[str], None]) -> str:
        ...

    def warmup(self) -> None:
        ...


@dataclass
class OllamaBackend:
    base_url: str
    model: str
    keep_alive: str | None = None
    capabilities: LLMCapabilityDescriptor = default_capabilities("ollama")

    def probe(self) -> dict[str, Any]:
        return probe_ollama(self.base_url, self.model)

    def generate(self, request: LLMOutboundRequest | str) -> str:
        outbound = coerce_llm_outbound_request(request)
        return generate(
            self.model,
            outbound.prompt,
            base_url=self.base_url,
            keep_alive=self.keep_alive,
        )

    def generate_stream(self, request: LLMOutboundRequest | str, *, on_chunk: Callable[[str], None]) -> str:
        outbound = coerce_llm_outbound_request(request, stream=True)
        return generate_stream(
            self.model,
            outbound.prompt,
            on_chunk=on_chunk,
            base_url=self.base_url,
            keep_alive=self.keep_alive,
        )

    def warmup(self) -> None:
        warmup_model(self.model, base_url=self.base_url, keep_alive=self.keep_alive)


@dataclass
class OpenAICompatibleBackend:
    base_url: str
    model: str
    api_key: str = ""
    capabilities: LLMCapabilityDescriptor = default_capabilities("openai_compatible")

    def _request_json(self, url: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"} if body is not None else {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
        try:
            with urlopen(request, timeout=120) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"openai-compatible request failed: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("openai-compatible response is not a JSON object")
        return parsed

    def _extract_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise RuntimeError("openai-compatible response is missing choices")
        message = choices[0].get("message", {})
        if not isinstance(message, dict):
            raise RuntimeError("openai-compatible response is missing assistant message")
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and str(item.get("type", "")).lower() in {"text", "output_text"}
            ]
            return "".join(parts)
        raise RuntimeError("openai-compatible response is missing assistant content")

    def probe(self) -> dict[str, Any]:
        payload = self._request_json(f"{self.base_url.rstrip('/')}/models")
        models = [
            str(item.get("id", "")).strip()
            for item in payload.get("data", [])
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]
        return {
            "ok": True,
            "model_available": self.model in models,
            "models": models,
        }

    def generate(self, request: LLMOutboundRequest | str) -> str:
        outbound = coerce_llm_outbound_request(request)
        payload = self._request_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            body={
                "model": self.model,
                "messages": [{"role": "user", "content": outbound.prompt}],
                "stream": False,
            },
        )
        return self._extract_text(payload)

    def generate_stream(self, request: LLMOutboundRequest | str, *, on_chunk: Callable[[str], None]) -> str:
        outbound = coerce_llm_outbound_request(request, stream=True)
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": outbound.prompt}],
                    "stream": True,
                }
            ).encode("utf-8"),
            headers={
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        chunks: list[str] = []
        try:
            with urlopen(request, timeout=120) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    parsed = json.loads(payload)
                    if not isinstance(parsed, dict):
                        raise RuntimeError("openai-compatible stream item is not a JSON object")
                    choices = parsed.get("choices", [])
                    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                        continue
                    delta = choices[0].get("delta", {})
                    if not isinstance(delta, dict):
                        continue
                    chunk = delta.get("content", "")
                    if isinstance(chunk, str) and chunk:
                        chunks.append(chunk)
                        on_chunk(chunk)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"openai-compatible request failed: {exc}") from exc
        return "".join(chunks)

    def warmup(self) -> None:
        return None


@dataclass
class BackendRouter:
    primary: LLMBackend
    fallback: LLMBackend | None = None
    primary_capabilities: LLMCapabilityDescriptor | None = None
    fallback_capabilities: LLMCapabilityDescriptor | None = None

    def __post_init__(self) -> None:
        if self.primary_capabilities is None:
            self.primary_capabilities = getattr(self.primary, "capabilities", None)
        if self.fallback is not None and self.fallback_capabilities is None:
            self.fallback_capabilities = getattr(self.fallback, "capabilities", None)

    def probe_primary(self) -> dict[str, Any]:
        return self.primary.probe()

    def warmup_primary(self) -> None:
        self.primary.warmup()

    def generate(self, request: LLMOutboundRequest | str) -> str:
        try:
            return self.primary.generate(request)
        except RuntimeError:
            if self.fallback is None:
                raise
            return self.fallback.generate(request)

    def generate_stream(self, request: LLMOutboundRequest | str, *, on_chunk: Callable[[str], None]) -> str:
        try:
            return self.primary.generate_stream(request, on_chunk=on_chunk)
        except RuntimeError:
            if self.fallback is None:
                raise
            return self.fallback.generate_stream(request, on_chunk=on_chunk)


def _build_capability_descriptor(config: AppConfig) -> LLMCapabilityDescriptor:
    default_capabilities(config.runtime_llm_provider)
    return LLMCapabilityDescriptor(
        provider=normalize_provider(config.runtime_llm_provider),
        supports_tools=config.runtime_llm_supports_tools,
        supports_json_schema=config.runtime_llm_supports_json_schema,
        supports_reasoning_effort=config.runtime_llm_supports_reasoning_effort,
        supports_streaming=config.runtime_llm_supports_streaming,
        max_context=config.runtime_llm_max_context,
        prompt_cache_behavior=config.runtime_llm_prompt_cache_behavior,
    )


def build_backend_router(config: AppConfig) -> BackendRouter:
    primary_capabilities = _build_capability_descriptor(config)
    provider = normalize_provider(config.runtime_llm_provider)
    if provider == "ollama":
        primary = OllamaBackend(
            base_url=config.runtime_llm_base_url,
            model=config.runtime_llm_model,
            keep_alive=config.runtime_llm_keep_alive,
            capabilities=primary_capabilities,
        )
    elif provider == "openai_compatible":
        primary = OpenAICompatibleBackend(
            base_url=config.runtime_llm_base_url,
            model=config.runtime_llm_model,
            api_key=config.runtime_llm_api_key,
            capabilities=primary_capabilities,
        )
    else:
        raise ValueError(f"unsupported llm provider: {config.runtime_llm_provider}")

    fallback: LLMBackend | None = None
    fallback_backend = normalize_provider(config.llm_fallback_backend)
    if fallback_backend == "ollama" and config.llm_fallback_base_url and config.llm_fallback_model:
        fallback = OllamaBackend(
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
            capabilities=default_capabilities("ollama"),
        )
    elif (
        fallback_backend == "openai_compatible"
        and config.llm_fallback_base_url
        and config.llm_fallback_model
    ):
        fallback = OpenAICompatibleBackend(
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
            api_key=config.llm_fallback_api_key,
            capabilities=default_capabilities("openai_compatible"),
        )
    elif config.llm_fallback_backend.strip():
        raise ValueError(f"unsupported llm provider: {config.llm_fallback_backend}")
    return BackendRouter(
        primary=primary,
        fallback=fallback,
        primary_capabilities=primary_capabilities,
        fallback_capabilities=getattr(fallback, "capabilities", None) if fallback is not None else None,
    )
