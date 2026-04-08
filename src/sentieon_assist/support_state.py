from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SupportTask = Literal[
    "idle",
    "troubleshooting",
    "onboarding_guidance",
    "reference_lookup",
    "capability_explanation",
]


@dataclass
class SupportSessionState:
    active_task: SupportTask = "idle"
    anchor_query: str = ""
    confirmed_facts: dict[str, str] = field(default_factory=dict)
    open_clarification_slots: tuple[str, ...] = ()
    last_route_reason: str = ""

    def cleared(self) -> "SupportSessionState":
        return SupportSessionState()
