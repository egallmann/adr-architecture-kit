"""Enforce normalized no-regression baselines for Ruff, strict mypy, and Black."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "quality-baselines"
FORMAT_TARGETS = ("src", "tests")
MYPY_TARGETS = ("src/adr_kit", "scripts")
PHASE0_FILES = (
    "scripts/check_compatibility_snapshots.py",
    "scripts/check_version_consistency.py",
    "scripts/check_quality_ratchets.py",
    "scripts/release_manifest.py",
    "scripts/test_installed_wheel.py",
    "benchmarks/phase0.py",
    "tests/test_import_namespace.py",
    "tests/test_phase0_compatibility.py",
    "tests/test_quality_ratchets.py",
    "tests/test_release_controls.py",
    "tests/test_benchmark_phase0.py",
)
PHASE1_FILES = (
    "src/adr_kit/_version.py",
    "src/adr_kit/api/__init__.py",
    "src/adr_kit/api/_contracts.py",
    "src/adr_kit/api/_errors.py",
    "src/adr_kit/api/_operations.py",
    "src/adr_kit/repository/_normalized_bundle.py",
    "scripts/test_sdk_consumer.py",
    "tests/test_public_sdk_contract.py",
    "tests/test_public_sdk_operations.py",
    "tests/test_cli_application_delegation.py",
    "tests/test_version_authority.py",
)
PHASE0_MYPY_ARGS = (
    "-m",
    "mypy",
    "--strict",
    *PHASE0_FILES,
    "--follow-imports=silent",
    "--no-incremental",
    "--no-color-output",
    "--no-pretty",
)
PHASE1_MYPY_ARGS = (
    "-m",
    "mypy",
    "--strict",
    *PHASE1_FILES,
    "--follow-imports=silent",
    "--no-incremental",
    "--no-color-output",
    "--no-pretty",
)
MYPY_PATTERN = re.compile(r"^(.*?):\d+(?::\d+)?: error: (.*?)\s+\[([^]]+)]$")
BLACK_PATTERN = re.compile(r"would reformat (.+)$")


def _run(
    arguments: Sequence[str], environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _relative(path_text: str) -> str:
    path = Path(path_text)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _records(counter: Counter[tuple[str, str, str]]) -> list[dict[str, object]]:
    return [
        {"path": path, "code": code, "message": message, "count": count}
        for (path, code, message), count in sorted(counter.items())
    ]


def collect_ruff() -> dict[str, object]:
    result = _run(["-m", "ruff", "check", *FORMAT_TARGETS, "--output-format", "json"])
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout + result.stderr)
    payload: list[dict[str, Any]] = json.loads(result.stdout or "[]")
    findings: Counter[tuple[str, str, str]] = Counter()
    for item in payload:
        findings[(_relative(str(item["filename"])), str(item["code"]), str(item["message"]))] += 1
    return {"tool": "ruff", "finding_count": sum(findings.values()), "findings": _records(findings)}


def collect_mypy() -> dict[str, object]:
    environment = os.environ.copy()
    environment["MYPYPATH"] = "src"
    result = _run(
        [
            "-m",
            "mypy",
            "--explicit-package-bases",
            *MYPY_TARGETS,
            "--no-incremental",
            "--show-error-codes",
            "--no-color-output",
            "--no-pretty",
        ],
        environment,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout + result.stderr)
    phase0 = _run(PHASE0_MYPY_ARGS, environment)
    if phase0.returncode != 0:
        raise RuntimeError(
            "new Phase 0 files are not strict-mypy clean:\n" + phase0.stdout + phase0.stderr
        )
    findings: Counter[tuple[str, str, str]] = Counter()
    for line in result.stdout.splitlines():
        match = MYPY_PATTERN.match(line)
        if match:
            path, message, code = match.groups()
            findings[(_relative(path), code, message)] += 1
    return {"tool": "mypy", "finding_count": sum(findings.values()), "findings": _records(findings)}


def collect_black() -> dict[str, object]:
    result = _run(["-m", "black", "--no-cache", "--check", *FORMAT_TARGETS])
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stdout + result.stderr)
    files = []
    for line in (result.stdout + result.stderr).splitlines():
        match = BLACK_PATTERN.search(line)
        if match:
            files.append(_relative(match.group(1)))
    return {"tool": "black", "finding_count": len(files), "files": sorted(files)}


def _write(name: str, payload: object) -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    (BASELINE_DIR / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _finding_counter(payload: dict[str, Any]) -> Counter[tuple[str, str, str]]:
    findings: Counter[tuple[str, str, str]] = Counter()
    for item in payload.get("findings", []):
        findings[(str(item["path"]), str(item["code"]), str(item["message"]))] = int(item["count"])
    return findings


def _check_findings(name: str, current: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    current_count = int(current["finding_count"])
    baseline_count = int(baseline["finding_count"])
    if current_count > baseline_count:
        errors.append(f"{name} count increased: {current_count} > {baseline_count}")
    new = _finding_counter(current) - _finding_counter(baseline)
    for (path, code, message), count in sorted(new.items()):
        errors.append(f"{name} new finding x{count}: {path}: {code}: {message}")
    return errors


def _load(name: str) -> dict[str, Any]:
    path = BASELINE_DIR / name
    if not path.is_file():
        raise RuntimeError(f"missing quality baseline: {path.relative_to(ROOT)}")
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def check_new_phase_files() -> None:
    environment = os.environ.copy()
    environment["MYPYPATH"] = "src"
    commands = (
        ["-m", "ruff", "check", *PHASE0_FILES, *PHASE1_FILES],
        ["-m", "black", "--no-cache", "--check", *PHASE0_FILES, *PHASE1_FILES],
        PHASE0_MYPY_ARGS,
        PHASE1_MYPY_ARGS,
    )
    for command in commands:
        result = _run(command, environment)
        if result.returncode != 0:
            raise RuntimeError(
                "new Phase 0/1 files are not clean:\n" + result.stdout + result.stderr
            )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        check_new_phase_files()
        current = {
            "ruff.json": collect_ruff(),
            "mypy.json": collect_mypy(),
            "black.json": collect_black(),
        }
        if arguments.write_baseline:
            for name, payload in current.items():
                _write(name, payload)
            for payload in current.values():
                print(f"{payload['tool']}: {payload['finding_count']}")
            return 0

        errors: list[str] = []
        errors.extend(_check_findings("ruff", current["ruff.json"], _load("ruff.json")))
        errors.extend(_check_findings("mypy", current["mypy.json"], _load("mypy.json")))
        current_black = set(cast(list[str], current["black.json"]["files"]))
        baseline_black = set(cast(list[str], _load("black.json")["files"]))
        if len(current_black) > len(baseline_black):
            errors.append(f"black count increased: {len(current_black)} > {len(baseline_black)}")
        for path in sorted(current_black - baseline_black):
            errors.append(f"black new unformatted file: {path}")
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        for payload in current.values():
            print(f"{payload['tool']}: {payload['finding_count']} (ratchet passed)")
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"quality ratchet error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
