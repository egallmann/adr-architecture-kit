"""Run the standard local governance checks for adr_kit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adr_kit.cli.main import cli

def main() -> int:
    parser = argparse.ArgumentParser(description="Run standard local governance checks.")
    parser.add_argument(
        "--scope",
        type=Path,
        default=Path("."),
        help="Project scope root to validate.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the full pytest run.",
    )
    args = parser.parse_args()

    command = [
        "governance-checks",
        "--scope",
        str(args.scope.resolve()),
    ]
    if args.skip_tests:
        command.append("--skip-tests")

    try:
        cli.main(args=command, prog_name="adr", standalone_mode=False)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


if __name__ == "__main__":
    raise SystemExit(main())
