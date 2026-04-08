from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request_json(url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    method = "GET" if body is None else "POST"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"local ollama request failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("local ollama response is not a JSON object")
    return parsed


def build_generate_payload(
    model: str,
    prompt: str,
    *,
    stream: bool = False,
    keep_alive: str | None = None,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }
    if keep_alive:
        payload["keep_alive"] = keep_alive
    return payload


def probe_ollama(base_url: str, model: str) -> dict[str, Any]:
    version_data = _request_json(f"{base_url.rstrip('/')}/api/version")
    tags_data = _request_json(f"{base_url.rstrip('/')}/api/tags")
    models = [str(item.get("name", "")).strip() for item in tags_data.get("models", []) if isinstance(item, dict)]
    return {
        "ok": True,
        "version": str(version_data.get("version", "")).strip(),
        "model_available": model in models,
        "models": [name for name in models if name],
    }


def generate(
    model: str,
    prompt: str,
    base_url: str = "http://127.0.0.1:11434",
    *,
    keep_alive: str | None = None,
) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = build_generate_payload(model, prompt, stream=False, keep_alive=keep_alive)
    data = _request_json(url, payload)
    text = data.get("response")
    if not isinstance(text, str):
        raise RuntimeError("local ollama response is missing 'response' text")
    return text


def generate_stream(
    model: str,
    prompt: str,
    *,
    on_chunk,
    base_url: str = "http://127.0.0.1:11434",
    keep_alive: str | None = None,
) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = build_generate_payload(model, prompt, stream=True, keep_alive=keep_alive)
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    chunks: list[str] = []
    try:
        with urlopen(request, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                parsed = json.loads(line)
                if not isinstance(parsed, dict):
                    raise RuntimeError("local ollama stream item is not a JSON object")
                chunk = parsed.get("response", "")
                if chunk:
                    text = str(chunk)
                    chunks.append(text)
                    on_chunk(text)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"local ollama request failed: {exc}") from exc
    return "".join(chunks)


def warmup_model(
    model: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    keep_alive: str | None = None,
) -> None:
    generate(model, "", base_url=base_url, keep_alive=keep_alive)
