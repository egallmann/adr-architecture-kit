"""Run the local pre-push check bundle for adr-architecture-kit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_EVIDENCE = (
    REPO_ROOT.parent
    / ".ste-workspace"
    / "state"
    / "adr-architecture-kit"
    / "attribution"
    / "implementation-attribution-evidence.yaml"
)

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
        "tests/test_retrofit_contract_guards.py",
        "tests/test_attribution_evidence_sync.py",
        "-q",
    ),
)


def run_attribution_check() -> int:
    if not WORKSPACE_EVIDENCE.is_file():
        print(
            "SKIP: workspace attribution evidence not found "
            f"({WORKSPACE_EVIDENCE}); run recon:workspace from ste-runtime first",
            flush=True,
        )
        return 0

    command = (
        sys.executable,
        "-m",
        "src.adr_kit.cli.main",
        "attribution",
        "check",
        "--scope",
        str(REPO_ROOT),
        "--evidence",
        str(WORKSPACE_EVIDENCE),
    )
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def main() -> int:
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT)
        if result.returncode != 0:
            return result.returncode

    return run_attribution_check()


if __name__ == "__main__":
    raise SystemExit(main())
