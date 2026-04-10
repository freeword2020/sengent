#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sentieon_assist.pilot_closed_loop import format_pilot_closed_loop_summary, run_pilot_closed_loop  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the pilot closed-loop evaluation for Sengent.")
    parser.add_argument("--json-out", type=Path, help="Optional path for machine-readable JSON output.")
    parser.add_argument("--source-dir", type=Path, help="Optional source pack directory to evaluate instead of sentieon-note/.")
    parser.add_argument("--baseline", type=Path, help="Optional path to a previous pilot-closed-loop JSON report.")
    parser.add_argument("--feedback-path", type=Path, help="Optional path to runtime feedback JSONL.")
    parser.add_argument("--runtime-root", type=Path, help="Optional runtime root to resolve pointer-style runtime feedback records.")
    parser.add_argument(
        "--focus-limit",
        type=int,
        default=3,
        help="Number of optimization buckets to surface in the top-N tightening queue.",
    )
    args = parser.parse_args(argv)

    report = run_pilot_closed_loop(
        REPO_ROOT,
        source_directory=args.source_dir,
        baseline_path=args.baseline,
        json_out=args.json_out,
        runtime_feedback_path=args.feedback_path,
        runtime_root=args.runtime_root,
        focus_limit=args.focus_limit,
    )
    print(format_pilot_closed_loop_summary(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
