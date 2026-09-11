"""Reject delivery-stage names in active repository paths and identifiers."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

# These are intentionally exact historical filenames.  They are design-journal
# provenance, not active implementation or release-stage surfaces.
HISTORICAL_PATH_EXCEPTIONS: dict[str, str] = {
    "docs/design-journal/2026-phase-1-public-sdk.md": "historical public-SDK decision journal",
    "docs/design-journal/2026-phase-2-schema-v12.md": "historical schema decision journal",
}

CONTENT_SCAN_EXCEPTIONS: dict[str, str] = {
    "scripts/check_repository_naming.py": "the policy test contains forbidden examples",
    "tests/test_repository_naming.py": "the policy test contains forbidden examples",
}

DELIVERY_PATH_RE = re.compile(
    r"(?:^|[/_-])(?:slice|hsg|tranche|phase|wave)(?:[-_]?(?:[a-z]|\d+))(?=$|[-_.])",
    re.IGNORECASE,
)
DELIVERY_CONTRACT_IDENTIFIER_RE = re.compile(
    r"\b(?:slice|hsg|tranche|phase|wave)[_-]?(?:[a-z]|\d+)\b",
    re.IGNORECASE,
)
DELIVERY_CODE_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:slice|hsg|tranche|phase|wave)(?:\d+|_(?:[a-z]|\d+))(?=$|[^A-Za-z0-9])",
    re.IGNORECASE,
)
ACTIVE_CONTENT_SUFFIXES = {
    ".json",
    ".js",
    ".mjs",
    ".py",
    ".rs",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}


def tracked_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def path_violations(paths: Iterable[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in HISTORICAL_PATH_EXCEPTIONS:
            continue
        match = DELIVERY_PATH_RE.search(normalized)
        if match:
            violations.append(
                f"path {normalized}: delivery-stage name {match.group(0)!r}; "
                "rename it to describe domain capability, responsibility, or behavior"
            )
    return violations


def _is_generated_or_historical(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized in HISTORICAL_PATH_EXCEPTIONS
        or normalized in CONTENT_SCAN_EXCEPTIONS
    )


def content_violations(root: Path, paths: Iterable[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if _is_generated_or_historical(normalized):
            continue
        if Path(normalized).suffix.lower() not in ACTIVE_CONTENT_SUFFIXES:
            continue
        if Path(normalized).suffix.lower() in {".yaml", ".yml"} and not normalized.startswith(
            ("contracts/", "src/adr_kit/semantic_contract/", "tests/fixtures/")
        ):
            continue
        file_path = root / Path(normalized)
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            matches: list[re.Match[str]] = []
            if normalized.startswith(("contracts/", "src/adr_kit/semantic_contract/", "tests/fixtures/")):
                matches.extend(DELIVERY_CONTRACT_IDENTIFIER_RE.finditer(line))
            else:
                matches.extend(DELIVERY_CODE_IDENTIFIER_RE.finditer(line))
            for match in matches:
                violations.append(
                    f"identifier {normalized}:{line_number}: {match.group(0)!r}; "
                    "active identifiers must describe domain capability, responsibility, or behavior"
                )
    return violations


def find_violations(root: Path = ROOT) -> list[str]:
    paths = tracked_paths(root)
    return path_violations(paths) + content_violations(root, paths)


def main() -> int:
    try:
        violations = find_violations()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"repository naming check failed to inspect tracked files: {exc}", file=sys.stderr)
        return 2
    if violations:
        print("repository naming policy violations:", file=sys.stderr)
        print("\n".join(f"- {violation}" for violation in violations), file=sys.stderr)
        return 1
    print("repository naming policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
