"""Verify the frozen Phase 0 Python and CLI compatibility inventories."""

from __future__ import annotations

import argparse
import difflib
import importlib
import inspect
import json
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

import click
from click.testing import CliRunner

from adr_kit.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts" / "compatibility"
PYTHON_SNAPSHOT = CONTRACT_DIR / "python-surface.json"
CLI_SNAPSHOT = CONTRACT_DIR / "cli-surface.json"
CLI_BEHAVIOR_SNAPSHOT = CONTRACT_DIR / "cli-behavior.json"
MODULES = (
    "adr_kit.api",
    "adr_kit.repository",
    "adr_kit.parser",
    "adr_kit.validators",
    "adr_kit.generators",
    "adr_kit.models",
    "adr_kit.compiler",
)

PINNED_TIMESTAMP = "2026-01-01T00:00:00Z"


def _canonicalize_strings(value: object) -> object:
    """Canonicalize text recursively so snapshots are host-platform independent."""

    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(value, list):
        return [_canonicalize_strings(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_canonicalize_strings(item) for item in value)
    if isinstance(value, dict):
        return {key: _canonicalize_strings(item) for key, item in value.items()}
    return value


def _json_value(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return repr(value)


def collect_python_surface() -> dict[str, list[str]]:
    surface = {"adr_kit": ["__version__"]}
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        exports = getattr(module, "__all__", ())
        surface[module_name] = sorted(str(name) for name in exports)
    return surface


def _parameter_record(parameter: click.Parameter) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": parameter.name,
        "kind": type(parameter).__name__,
        "required": parameter.required,
        "nargs": parameter.nargs,
        "type": parameter.type.name,
        "default": _json_value(parameter.default),
    }
    if isinstance(parameter, click.Option):
        record.update(
            {
                "opts": list(parameter.opts),
                "secondary_opts": list(parameter.secondary_opts),
                "multiple": parameter.multiple,
                "count": parameter.count,
                "is_flag": parameter.is_flag,
            }
        )
    return record


def _walk_commands(group: click.Group, prefix: str = "") -> dict[str, Any]:
    records: dict[str, Any] = {}
    for name, command in sorted(group.commands.items()):
        path = f"{prefix} {name}".strip()
        records[path] = {
            "help": inspect.cleandoc(command.help or ""),
            "params": [_parameter_record(parameter) for parameter in command.params],
        }
        if isinstance(command, click.Group):
            records.update(_walk_commands(command, path))
    return records


def collect_cli_surface() -> dict[str, Any]:
    return {
        "entry_point": "adr_kit.cli.main:cli",
        "params": [_parameter_record(parameter) for parameter in cli.params],
        "commands": _walk_commands(cli),
    }


def _fixture(root: Path, *, recursive: bool = False) -> None:
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    if recursive:
        fixture_builder = getattr(
            importlib.import_module("tests.test_compiler_driver"),
            "_create_recursive_workspace",
        )
        fixture_builder(root)
        return

    fixture_builder = getattr(
        importlib.import_module("tests.test_architecture_index_generator"),
        "_create_fixture",
    )
    fixture_builder(root)


def _replace(root: Path, old: str, new: str) -> None:
    path = root / "adrs" / "logical" / "ADR-L-1000-discovery.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def _generated_hashes(root: Path) -> dict[str, str]:
    paths: list[Path] = []
    for scope in (root, *sorted(path.parent for path in root.rglob("PROJECT.yaml"))):
        for relative in ("adrs/manifest.yaml", "adrs/entities/registry.yaml"):
            candidate = scope / relative
            if candidate.is_file():
                paths.append(candidate)
        for directory in (scope / "adrs" / "index", scope / "adrs" / "rendered"):
            if directory.is_dir():
                paths.extend(path for path in directory.rglob("*") if path.is_file())
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }


def _normalize_output(value: bytes, fixture_root: Path) -> str:
    text = value.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    for root_text in (str(fixture_root), fixture_root.as_posix()):
        text = text.replace(root_text, "<FIXTURE_ROOT>")
    return text.replace("\\", "/")


def _invoke(argv: list[str], fixture_root: Path) -> dict[str, Any]:
    runner = CliRunner()
    result = runner.invoke(cli, argv, color=False)
    return {
        "argv": [
            item.replace(str(fixture_root), "<FIXTURE_ROOT>").replace("\\", "/") for item in argv
        ],
        "exit_code": result.exit_code,
        "stdout": _normalize_output(result.stdout_bytes, fixture_root),
        "stderr": _normalize_output(result.stderr_bytes, fixture_root),
        "generated_files": _generated_hashes(fixture_root),
    }


def _governance_failure(root: Path) -> None:
    _replace(
        root,
        "context: |\n  Discovery fixture.\n",
        "context: |\n  Discovery fixture.\n"
        "governance:\n"
        "  steelman_review_required: true\n"
        "  steelman_review_completed: false\n"
        "  implementation_authority: implementation_authoritative\n"
        "  approved_by: erik\n"
        '  approved_date: "2026-03-18T12:00:00Z"\n',
    )


def _prepare_check(root: Path, *, drift: bool) -> None:
    result = CliRunner().invoke(
        cli,
        ["compile", "--scope", str(root), "--timestamp", PINNED_TIMESTAMP],
        color=False,
    )
    if result.exit_code != 0:
        raise RuntimeError(result.output)
    if drift:
        manifest = root / "adrs" / "manifest.yaml"
        manifest.write_text("drifted\n", encoding="utf-8", newline="\n")


def collect_cli_behavior() -> dict[str, dict[str, Any]]:
    """Capture the exact Phase 1 validate/compile compatibility matrix."""

    cases: tuple[tuple[str, tuple[str, ...], str], ...] = (
        ("validate-complete", (), "basic"),
        ("validate-structural", ("--mode", "structural"), "basic"),
        ("validate-invalid-schema", (), "invalid-schema"),
        ("validate-cross-reference-success", ("--cross-references",), "basic"),
        ("validate-cross-reference-failure", ("--cross-references",), "xref-failure"),
        ("validate-recursive", ("--recursive",), "recursive"),
        ("compile-write", ("--timestamp", PINNED_TIMESTAMP), "basic"),
        ("compile-dry-run", ("--dry-run", "--timestamp", PINNED_TIMESTAMP), "basic"),
        ("compile-clean-check", ("--check",), "clean-check"),
        ("compile-drifted-check", ("--check",), "drift-check"),
        (
            "compile-strict-failure",
            ("--dry-run", "--mode", "strict", "--timestamp", PINNED_TIMESTAMP),
            "governance-failure",
        ),
        (
            "compile-lenient-diagnostic",
            ("--dry-run", "--mode", "lenient", "--timestamp", PINNED_TIMESTAMP),
            "governance-failure",
        ),
        (
            "compile-greenfield-contract",
            (
                "--dry-run",
                "--validate-contract",
                "--contract-profile",
                "greenfield",
                "--timestamp",
                PINNED_TIMESTAMP,
            ),
            "basic",
        ),
        (
            "compile-brownfield-contract",
            (
                "--dry-run",
                "--validate-contract",
                "--contract-profile",
                "brownfield",
                "--timestamp",
                PINNED_TIMESTAMP,
            ),
            "basic",
        ),
        (
            "compile-graph",
            ("--emit", "graph", "--timestamp", PINNED_TIMESTAMP),
            "basic",
        ),
        (
            "compile-recursive",
            ("--recursive", "--dry-run", "--timestamp", PINNED_TIMESTAMP),
            "recursive",
        ),
    )
    behavior: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="adr-kit-cli-behavior-") as temporary:
        temporary_root = Path(temporary)
        for name, arguments, setup in cases:
            root = temporary_root / name / "project"
            _fixture(root, recursive=setup == "recursive")
            if setup == "invalid-schema":
                _replace(root, 'title: "Discovery"\n', "")
            elif setup == "xref-failure":
                _replace(root, 'related_adrs: ["ADR-PC-1000"]', 'related_adrs: ["ADR-PC-9999"]')
            elif setup == "governance-failure":
                _governance_failure(root)
            elif setup in {"clean-check", "drift-check"}:
                _prepare_check(root, drift=setup == "drift-check")

            command = "validate" if name.startswith("validate-") else "compile"
            argv = [command, "--scope", str(root), *arguments]
            behavior[name] = _invoke(argv, root)
    return behavior


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical = _canonicalize_strings(payload)
    path.write_text(
        json.dumps(canonical, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _snapshot_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _check(path: Path, actual: object) -> bool:
    if not path.is_file():
        print(f"missing compatibility snapshot: {_snapshot_label(path)}", file=sys.stderr)
        return False
    expected: object = json.loads(path.read_text(encoding="utf-8"))
    canonical_expected = _canonicalize_strings(expected)
    if expected != canonical_expected:
        print(
            f"non-canonical newlines in compatibility snapshot: {_snapshot_label(path)}; "
            "refresh the snapshot with --write",
            file=sys.stderr,
        )
        return False
    actual = _canonicalize_strings(actual)
    if expected != actual:
        print(f"compatibility snapshot drift: {_snapshot_label(path)}", file=sys.stderr)
        expected_text = json.dumps(expected, indent=2, sort_keys=True).splitlines()
        actual_text = json.dumps(actual, indent=2, sort_keys=True).splitlines()
        print(
            "\n".join(
                difflib.unified_diff(
                    expected_text,
                    actual_text,
                    fromfile=f"committed/{_snapshot_label(path)}",
                    tofile=f"actual/{_snapshot_label(path)}",
                    lineterm="",
                )
            ),
            file=sys.stderr,
        )
        return False
    print(f"OK: {_snapshot_label(path)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="refresh the committed snapshots")
    arguments = parser.parse_args()
    python_surface = collect_python_surface()
    cli_surface = collect_cli_surface()
    cli_behavior = collect_cli_behavior()
    if arguments.write:
        _write(PYTHON_SNAPSHOT, python_surface)
        _write(CLI_SNAPSHOT, cli_surface)
        _write(CLI_BEHAVIOR_SNAPSHOT, cli_behavior)
        return 0
    checks = (
        _check(PYTHON_SNAPSHOT, python_surface),
        _check(CLI_SNAPSHOT, cli_surface),
        _check(CLI_BEHAVIOR_SNAPSHOT, cli_behavior),
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
