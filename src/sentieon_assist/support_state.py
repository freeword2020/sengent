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

    def to_snapshot(self) -> dict[str, object]:
        return {
            "active_task": self.active_task,
            "anchor_query": self.anchor_query,
            "confirmed_facts": dict(self.confirmed_facts),
            "open_clarification_slots": list(self.open_clarification_slots),
            "last_route_reason": self.last_route_reason,
        }
