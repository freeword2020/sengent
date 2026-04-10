#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sentieon_assist.pilot_readiness import format_pilot_readiness_summary, run_pilot_readiness_evaluation  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pilot-readiness gates for Sengent support flows.")
    parser.add_argument("--json-out", type=Path, help="Optional path for machine-readable JSON output.")
    parser.add_argument("--source-dir", type=Path, help="Optional source pack directory to evaluate instead of sentieon-note/.")
    args = parser.parse_args(argv)

    report = run_pilot_readiness_evaluation(REPO_ROOT, source_directory=args.source_dir, json_out=args.json_out)
    print(format_pilot_readiness_summary(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
