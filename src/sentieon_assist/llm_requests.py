from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class LLMOutboundRequest:
    purpose: str
    prompt: str
    trust_boundary_summary: dict[str, Any] = field(default_factory=dict)
    transport_mode: str = "chat_completions"
    stream: bool = False

    def with_stream(self, stream: bool = True) -> "LLMOutboundRequest":
        return replace(self, stream=stream)


def build_llm_outbound_request(
    *,
    purpose: str,
    prompt: str,
    trust_boundary_summary: Mapping[str, Any] | None = None,
    transport_mode: str = "chat_completions",
    stream: bool = False,
) -> LLMOutboundRequest:
    return LLMOutboundRequest(
        purpose=str(purpose).strip(),
        prompt=str(prompt),
        trust_boundary_summary=dict(trust_boundary_summary or {}),
        transport_mode=str(transport_mode).strip() or "chat_completions",
        stream=bool(stream),
    )


def coerce_llm_outbound_request(
    value: LLMOutboundRequest | str,
    *,
    purpose: str = "",
    trust_boundary_summary: Mapping[str, Any] | None = None,
    transport_mode: str = "chat_completions",
    stream: bool = False,
) -> LLMOutboundRequest:
    if isinstance(value, LLMOutboundRequest):
        return value
    return build_llm_outbound_request(
        purpose=purpose,
        prompt=value,
        trust_boundary_summary=trust_boundary_summary,
        transport_mode=transport_mode,
        stream=stream,
    )


__all__ = [
    "LLMOutboundRequest",
    "build_llm_outbound_request",
    "coerce_llm_outbound_request",
]
