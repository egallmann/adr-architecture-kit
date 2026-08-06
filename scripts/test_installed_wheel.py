"""Exercise a selected wheel as an isolated external consumer using only stdlib."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
PROBES = ("imports", "cli", "external-fixture", "schemas", "templates", "source-isolation")
PROBE = """
from importlib import resources
from pathlib import Path
import adr_kit
from adr_kit.decorators import enforces_invariant, implements_adr
from adr_kit.models import NormalizedArchitectureModel
from adr_kit.parser import ADRParser
from adr_kit.repository import ArchitectureRepository

package_path = Path(adr_kit.__file__).resolve()
assert 'site-packages' in package_path.as_posix().lower(), package_path
assert resources.files('adr_kit.schema.v1_0').joinpath('adr-logical.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_1').joinpath('architecture-index.schema.json').is_file()
assert resources.files('adr_kit.templates').joinpath('adr-logical.md.jinja2').is_file()
print(adr_kit.__version__)
"""


def _venv_paths(environment: Path) -> tuple[Path, Path, Path]:
    if os.name == "nt":
        scripts = environment / "Scripts"
        return scripts / "python.exe", scripts / "pip.exe", scripts / "adr.exe"
    scripts = environment / "bin"
    return scripts / "python", scripts / "pip", scripts / "adr"


def _run(command: list[str], cwd: Path, environment: dict[str, str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def run_harness(wheel: Path, python: Path) -> None:
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError(f"wheel not found: {wheel}")
    with tempfile.TemporaryDirectory(prefix="adr-kit-wheel-") as temporary:
        root = Path(temporary)
        environment_path = root / "venv"
        isolated_environment = os.environ.copy()
        isolated_environment.pop("PYTHONPATH", None)
        isolated_environment["PYTHONNOUSERSITE"] = "1"
        _run([str(python), "-m", "venv", str(environment_path)], root, isolated_environment)
        venv_python, pip, adr = _venv_paths(environment_path)

        _run([str(pip), "install", str(wheel)], root, isolated_environment)
        consumer = root / "consumer"
        fixture = consumer / "fixture"
        (fixture / "adrs" / "logical").mkdir(parents=True)
        shutil.copy2(ROOT / "PROJECT.yaml", fixture / "PROJECT.yaml")
        shutil.copy2(
            ROOT / "tests" / "fixtures" / "valid" / "logical-minimal.yaml",
            fixture / "adrs" / "logical" / "ADR-L-9999-minimal.yaml",
        )
        _run([str(venv_python), "-c", PROBE], consumer, isolated_environment)
        _run([str(adr), "--version"], consumer, isolated_environment)
        _run([str(adr), "validate", "--scope", str(fixture)], consumer, isolated_environment)
        _run(
            [
                str(adr),
                "compile",
                "--scope",
                str(fixture),
                "--emit",
                "registries,manifest",
                "--timestamp",
                "2026-01-01T00:00:00Z",
            ],
            consumer,
            isolated_environment,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--describe", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.describe:
        print("\n".join(PROBES))
        return 0
    if arguments.wheel is None:
        parser.error("--wheel is required unless --describe is used")
    try:
        run_harness(arguments.wheel, arguments.python)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"installed-wheel harness failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
