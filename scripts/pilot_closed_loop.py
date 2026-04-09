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
    parser.add_argument("--baseline", type=Path, help="Optional path to a previous pilot-closed-loop JSON report.")
    args = parser.parse_args(argv)

    report = run_pilot_closed_loop(
        REPO_ROOT,
        baseline_path=args.baseline,
        json_out=args.json_out,
    )
    print(format_pilot_closed_loop_summary(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
