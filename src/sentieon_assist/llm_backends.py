from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentieon_assist.config import AppConfig
from sentieon_assist.ollama_client import generate, generate_stream, probe_ollama, warmup_model


class LLMBackend(Protocol):
    def probe(self) -> dict[str, Any]:
        ...

    def generate(self, prompt: str) -> str:
        ...

    def generate_stream(self, prompt: str, *, on_chunk: Callable[[str], None]) -> str:
        ...

    def warmup(self) -> None:
        ...


@dataclass
class OllamaBackend:
    base_url: str
    model: str
    keep_alive: str | None = None

    def probe(self) -> dict[str, Any]:
        return probe_ollama(self.base_url, self.model)

    def generate(self, prompt: str) -> str:
        return generate(
            self.model,
            prompt,
            base_url=self.base_url,
            keep_alive=self.keep_alive,
        )

    def generate_stream(self, prompt: str, *, on_chunk: Callable[[str], None]) -> str:
        return generate_stream(
            self.model,
            prompt,
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

    def generate(self, prompt: str) -> str:
        payload = self._request_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            body={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        return self._extract_text(payload)

    def generate_stream(self, prompt: str, *, on_chunk: Callable[[str], None]) -> str:
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
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

    def probe_primary(self) -> dict[str, Any]:
        return self.primary.probe()

    def warmup_primary(self) -> None:
        self.primary.warmup()

    def generate(self, prompt: str) -> str:
        try:
            return self.primary.generate(prompt)
        except RuntimeError:
            if self.fallback is None:
                raise
            return self.fallback.generate(prompt)

    def generate_stream(self, prompt: str, *, on_chunk: Callable[[str], None]) -> str:
        try:
            return self.primary.generate_stream(prompt, on_chunk=on_chunk)
        except RuntimeError:
            if self.fallback is None:
                raise
            return self.fallback.generate_stream(prompt, on_chunk=on_chunk)


def build_backend_router(config: AppConfig) -> BackendRouter:
    primary = OllamaBackend(
        base_url=config.ollama_base_url,
        model=config.ollama_model,
        keep_alive=config.ollama_keep_alive,
    )
    fallback: LLMBackend | None = None
    if config.llm_fallback_backend == "ollama" and config.llm_fallback_base_url and config.llm_fallback_model:
        fallback = OllamaBackend(
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
        )
    elif (
        config.llm_fallback_backend == "openai_compatible"
        and config.llm_fallback_base_url
        and config.llm_fallback_model
    ):
        fallback = OpenAICompatibleBackend(
            base_url=config.llm_fallback_base_url,
            model=config.llm_fallback_model,
            api_key=config.llm_fallback_api_key,
        )
    return BackendRouter(primary=primary, fallback=fallback)
