"""Verify the frozen Phase 0 Python and CLI compatibility inventories."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import click

from adr_kit.cli.main import cli

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts" / "compatibility"
PYTHON_SNAPSHOT = CONTRACT_DIR / "python-surface.json"
CLI_SNAPSHOT = CONTRACT_DIR / "cli-surface.json"
MODULES = (
    "adr_kit.repository",
    "adr_kit.parser",
    "adr_kit.validators",
    "adr_kit.generators",
    "adr_kit.models",
    "adr_kit.compiler",
)


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
            "help": command.help or "",
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


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _check(path: Path, actual: object) -> bool:
    if not path.is_file():
        print(f"missing compatibility snapshot: {path.relative_to(ROOT)}", file=sys.stderr)
        return False
    expected: object = json.loads(path.read_text(encoding="utf-8"))
    if expected != actual:
        print(f"compatibility snapshot drift: {path.relative_to(ROOT)}", file=sys.stderr)
        return False
    print(f"OK: {path.relative_to(ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="refresh the committed snapshots")
    arguments = parser.parse_args()
    python_surface = collect_python_surface()
    cli_surface = collect_cli_surface()
    if arguments.write:
        _write(PYTHON_SNAPSHOT, python_surface)
        _write(CLI_SNAPSHOT, cli_surface)
        return 0
    return 0 if _check(PYTHON_SNAPSHOT, python_surface) and _check(CLI_SNAPSHOT, cli_surface) else 1


if __name__ == "__main__":
    raise SystemExit(main())
