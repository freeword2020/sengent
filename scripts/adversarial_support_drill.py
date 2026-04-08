#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DrillCase:
    name: str
    prompt: str
    expected: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


LEGACY_CASES = (
    DrillCase(
        name="capability-broad",
        prompt="你能做什么",
        expected=("【能力说明】", "Sentieon 技术支持工作"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="capability-sentieon",
        prompt="你不是可以提供sentieon的功能吗",
        expected=("【能力说明】", "Sentieon 技术支持工作"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="module-overview",
        prompt="sentieon有哪些模块",
        expected=("【模块介绍】", "Sentieon 主要模块可以先按下面几组理解"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="unindexed-submodule-boundary",
        prompt="介绍下AlignmentStat",
        expected=("AlignmentStat", "未收录", "QC"),
        forbidden=("Alignment：Sentieon 的比对能力",),
    ),
    DrillCase(
        name="external-explanation",
        prompt="FastQC 是做什么的",
        expected=("【资料说明】", "FastQC"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="external-error",
        prompt="BAM 报错说 read group 不一致怎么办",
        expected=("【关联判断】", "Read Group"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="workflow-clarification",
        prompt="能提供个wes参考脚本吗",
        expected=("【流程指导】", "【需要确认的信息】"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
    DrillCase(
        name="parameter-lookup",
        prompt="DNAscope 的 --pcr_free 是什么",
        expected=("DNAscope 的 --pcr_free", "【常用参数】"),
        forbidden=("当前 MVP 仅支持 license 和 install 问题",),
    ),
)


def load_notebooklm_cases(repo_root: Path) -> tuple[DrillCase, ...]:
    payload = json.loads((repo_root / "tests" / "data" / "notebooklm_adversarial_cases.json").read_text())
    cases: list[DrillCase] = []
    for item in payload:
        case_id = int(item["id"])
        expected_mode = str(item.get("expected_mode", "")).strip()
        if expected_mode == "boundary":
            expected = ("【资料边界】",)
        elif expected_mode == "clarify":
            expected = ("【需要确认的信息】",)
        else:
            expected = tuple(item.get("expected", [])) or ("【资料说明】",)
        forbidden = ("当前 MVP 仅支持 license 和 install 问题",)
        cases.append(
            DrillCase(
                name=f"notebooklm-{case_id:02d}",
                prompt=str(item["prompt"]),
                expected=expected,
                forbidden=forbidden,
            )
        )
    return tuple(cases)


def run_case(repo_root: Path, case: DrillCase) -> tuple[bool, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    command = [sys.executable, "-m", "sentieon_assist.cli", case.prompt]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        return False, f"exit={completed.returncode}\nSTDOUT:\n{output}\nSTDERR:\n{stderr}"

    missing = [value for value in case.expected if value not in output]
    present_forbidden = [value for value in case.forbidden if value in output]
    if not missing and not present_forbidden:
        return True, output

    details: list[str] = [output]
    if missing:
        details.append(f"missing={missing}")
    if present_forbidden:
        details.append(f"forbidden={present_forbidden}")
    return False, "\n".join(details)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    cases = (*LEGACY_CASES, *load_notebooklm_cases(repo_root))
    failures = 0
    print(f"Running adversarial support drill from {repo_root}")
    for case in cases:
        ok, details = run_case(repo_root, case)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case.name}: {case.prompt}")
        if not ok:
            failures += 1
            print(details)
    if failures:
        print(f"{failures} adversarial drill case(s) failed.")
        return 1
    print(f"All {len(cases)} adversarial drill cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
