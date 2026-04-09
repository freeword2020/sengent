#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sentieon_assist.adversarial_sessions import run_support_session  # noqa: E402


@dataclass(frozen=True)
class SessionTurnCase:
    prompt: str
    expected: tuple[str, ...]
    forbidden: tuple[str, ...] = ("当前 MVP 仅支持 license 和 install 问题",)
    reused_anchor: bool | None = None


@dataclass(frozen=True)
class SessionCase:
    name: str
    turns: tuple[SessionTurnCase, ...]


def load_cases(repo_root: Path) -> tuple[SessionCase, ...]:
    payload = json.loads((repo_root / "tests" / "data" / "high_intensity_adversarial_sessions.json").read_text())
    cases: list[SessionCase] = []
    for item in payload:
        turns = []
        for turn in item.get("turns", []):
            turns.append(
                SessionTurnCase(
                    prompt=str(turn["prompt"]),
                    expected=tuple(turn.get("expected", [])),
                    forbidden=tuple(turn.get("forbidden", [])) or ("当前 MVP 仅支持 license 和 install 问题",),
                    reused_anchor=turn.get("reused_anchor"),
                )
            )
        cases.append(SessionCase(name=str(item.get("name", item.get("id", "session"))), turns=tuple(turns)))
    return tuple(cases)


def validate_session(repo_root: Path, case: SessionCase) -> tuple[bool, str]:
    results = run_support_session(
        [turn.prompt for turn in case.turns],
        source_directory=str(repo_root / "sentieon-note"),
    )
    if len(results) != len(case.turns):
        return False, f"turn_count_mismatch expected={len(case.turns)} actual={len(results)}"

    failures: list[str] = []
    for index, (turn, result) in enumerate(zip(case.turns, results, strict=True), start=1):
        missing = [value for value in turn.expected if value not in result.response]
        present_forbidden = [value for value in turn.forbidden if value in result.response]
        anchor_mismatch = turn.reused_anchor is not None and result.reused_anchor != turn.reused_anchor
        if not missing and not present_forbidden and not anchor_mismatch:
            continue
        details = [
            f"turn={index}",
            f"prompt={turn.prompt}",
            f"effective={result.effective_query}",
            f"reused_anchor={result.reused_anchor}",
            result.response,
        ]
        if missing:
            details.append(f"missing={missing}")
        if present_forbidden:
            details.append(f"forbidden={present_forbidden}")
        if anchor_mismatch:
            details.append(f"expected_reused_anchor={turn.reused_anchor}")
        failures.append("\n".join(details))
    if failures:
        return False, "\n\n".join(failures)
    return True, ""


def main() -> int:
    cases = load_cases(REPO_ROOT)
    failures = 0
    print(f"Running high-intensity support drill from {REPO_ROOT}")
    for case in cases:
        ok, details = validate_session(REPO_ROOT, case)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case.name}")
        if not ok:
            failures += 1
            print(details)
    if failures:
        print(f"{failures} high-intensity session(s) failed.")
        return 1
    print(f"All {len(cases)} high-intensity sessions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
