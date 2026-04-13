from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentieon_assist.config import AppConfig


class FactoryBackend(Protocol):
    adapter_id: str
    provider: str
    model_name: str

    def probe(self) -> dict[str, Any]:
        ...

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class StubFactoryBackend:
    adapter_id: str = "stub"
    provider: str = "local-stub"
    model_name: str = "stub-factory-v1"

    def probe(self) -> dict[str, Any]:
        return {"ok": True, "model_available": True, "models": [self.model_name]}

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        task_label = task_kind.replace("_", " ")
        draft_items = [
            {
                "item_id": f"{task_kind}-{index}",
                "title": f"{reference['label']} review candidate",
                "proposed_action": _stub_action_for_task(task_kind),
                "source_path": reference.get("path", ""),
                "evidence_preview": reference.get("preview", ""),
            }
            for index, reference in enumerate(source_references, start=1)
        ]
        return {
            "summary": (
                f"Stub {task_label} draft for vendor `{vendor_id}` built from "
                f"{len(source_references)} reviewed source reference(s)."
            ),
            "draft_items": draft_items,
            "review_hints": _stub_review_hints(task_kind),
            "adapter_notes": {
                "execution_mode": "offline-stub",
                "prompt_preview": prompt[:240],
            },
        }


@dataclass(frozen=True)
class OpenAICompatibleFactoryBackend:
    base_url: str
    model_name: str
    api_key: str = ""
    adapter_id: str = "hosted"
    provider: str = "openai_compatible"

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
            raise RuntimeError(f"factory hosted request failed: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("factory hosted response is not a JSON object")
        return parsed

    def probe(self) -> dict[str, Any]:
        payload = self._request_json(f"{self.base_url.rstrip('/')}/models")
        models = [
            str(item.get("id", "")).strip()
            for item in payload.get("data", [])
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]
        return {
            "ok": True,
            "model_available": self.model_name in models,
            "models": models,
        }

    def draft(
        self,
        *,
        task_kind: str,
        vendor_id: str,
        prompt: str,
        source_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        del task_kind, vendor_id, source_references
        payload = self._request_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            body={
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        return _extract_factory_draft_payload(payload)


def build_factory_backend(config: AppConfig) -> FactoryBackend:
    provider = str(config.factory_hosted_provider).strip().lower()
    if not provider:
        return StubFactoryBackend()
    if provider == "openai_compatible":
        if not config.factory_hosted_base_url or not config.factory_hosted_model:
            raise ValueError("factory hosted provider requires base_url and model")
        return OpenAICompatibleFactoryBackend(
            base_url=config.factory_hosted_base_url,
            model_name=config.factory_hosted_model,
            api_key=config.factory_hosted_api_key,
        )
    raise ValueError(f"unsupported factory hosted provider: {config.factory_hosted_provider}")


def _extract_factory_draft_payload(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("factory hosted response is missing choices")
    message = choices[0].get("message", {})
    if not isinstance(message, dict):
        raise RuntimeError("factory hosted response is missing assistant message")
    content = message.get("content", "")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and str(item.get("type", "")).lower() in {"text", "output_text"}
        )
    else:
        raise RuntimeError("factory hosted response is missing assistant content")
    return {
        "summary": text,
        "draft_items": [],
        "review_hints": [],
        "adapter_notes": {"execution_mode": "hosted-review-only"},
    }


def _stub_action_for_task(task_kind: str) -> str:
    if task_kind == "candidate_draft":
        return "Extract candidate knowledge statements for maintainer review."
    if task_kind == "incident_normalization":
        return "Normalize the incident narrative into structured support fields."
    if task_kind == "contradiction_cluster":
        return "Group conflicting statements and keep both sides for maintainer review."
    return "Draft downstream dataset notes and export checks for maintainer review."


def _stub_review_hints(task_kind: str) -> list[str]:
    task_specific = {
        "candidate_draft": "Confirm each candidate statement against the authoritative source before build.",
        "incident_normalization": "Check the normalized fields against the original incident wording before reuse.",
        "contradiction_cluster": "Verify each contradiction cluster against the cited sources before resolution.",
        "dataset_draft": "Confirm expected answer contract fields before exporting any downstream training asset.",
    }
    return [
        "This artifact is draft-only and cannot bypass build/review/gate/activate.",
        task_specific[task_kind],
        "Promote only maintainer-reviewed content into formal knowledge or dataset exports.",
    ]


__all__ = [
    "FactoryBackend",
    "OpenAICompatibleFactoryBackend",
    "StubFactoryBackend",
    "build_factory_backend",
]
