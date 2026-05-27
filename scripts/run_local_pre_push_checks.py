"""Run the local pre-push check bundle for adr-architecture-kit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

COMMANDS: tuple[tuple[str, ...], ...] = (
    (
        sys.executable,
        "-m",
        "src.adr_kit.cli.main",
        "validate-generated-docs",
        "--scope",
        str(REPO_ROOT),
    ),
    (
        sys.executable,
        "-m",
        "pytest",
        "tests/golden/test_current_outputs.py",
        "tests/test_generated_docs_integrity.py",
        "tests/test_kernel_schema_fixture_sync.py",
        "tests/test_package_schema_parity.py",
        "tests/test_adr_ir_fragment_compiler.py",
        "tests/test_architecture_ir_publication.py",
        "-q",
    ),
)


def main() -> int:
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
