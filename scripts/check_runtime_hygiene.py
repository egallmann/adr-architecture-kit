"""Check runtime hygiene for adr_kit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adr_kit.validators.runtime_hygiene import (
    find_import_deprecations,
    format_findings,
    format_outdated_packages,
    list_outdated_packages,
    load_direct_dependency_names,
    run_pip_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime hygiene for adr_kit.")
    parser.add_argument(
        "--requirements",
        type=Path,
        default=Path("requirements.txt"),
        help="Requirements file used for dependency security audit.",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="pyproject.toml used to determine direct dependencies.",
    )
    parser.add_argument(
        "--fail-on-outdated",
        action="store_true",
        help="Fail if any direct dependency is outdated.",
    )
    args = parser.parse_args()

    failures = 0

    print("Checking deprecated runtime APIs...")
    deprecations = find_import_deprecations("adr_kit")
    if deprecations:
        failures += 1
        print("Deprecated API usage detected:")
        for line in format_findings(deprecations):
            print(f"  - {line}")
    else:
        print("  OK: no deprecation warnings during adr_kit import scan")

    print("\nChecking dependency security...")
    audit_result = run_pip_audit(args.requirements)
    if audit_result.returncode != 0:
        failures += 1
        stderr = audit_result.stderr.strip()
        stdout = audit_result.stdout.strip()
        print("Dependency security audit failed:")
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
    else:
        print("  OK: no known vulnerabilities in audited dependencies")

    print("\nChecking direct dependency freshness...")
    direct_dependencies = load_direct_dependency_names(args.requirements, args.pyproject)
    outdated = list_outdated_packages(direct_dependencies)
    if outdated:
        print("Outdated direct dependencies detected:")
        for line in format_outdated_packages(outdated):
            print(f"  - {line}")
        if args.fail_on_outdated:
            failures += 1
    else:
        print("  OK: direct dependencies are current")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
