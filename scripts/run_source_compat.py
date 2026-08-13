"""Cross-platform source/SDK compatibility orchestration (stdlib only)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> None:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed "
            f"{command!r}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def _prepare_fixture(repo_root: Path, fixture_root: Path) -> Path:
    project_root = fixture_root / "fixture"
    logical = project_root / "adrs" / "logical"
    logical.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "PROJECT.yaml", project_root / "PROJECT.yaml")
    shutil.copy2(
        repo_root / "tests" / "fixtures" / "valid" / "logical-minimal.yaml",
        logical / "ADR-L-9999-minimal.yaml",
    )
    return project_root


def run_source_compat(repo_root: Path, python_executable: str | None = None) -> None:
    """Exercise installed, direct-source, and editable SDK consumers outside the checkout."""

    repo_root = repo_root.resolve()
    python = python_executable or sys.executable
    consumer = repo_root / "scripts" / "test_sdk_consumer.py"
    base_env = os.environ.copy()
    base_env.pop("PYTHONPATH", None)

    with tempfile.TemporaryDirectory(prefix="adr-source-compat-") as temporary:
        fixture_root = Path(temporary)
        project_root = _prepare_fixture(repo_root, fixture_root)

        _run(
            [
                python,
                str(consumer),
                "--project-root",
                str(project_root),
                "--version-source",
                "metadata",
            ],
            cwd=fixture_root,
            env=base_env,
        )

        source_env = base_env.copy()
        source_env["PYTHONPATH"] = str(repo_root / "src")
        _run(
            [
                python,
                str(consumer),
                "--project-root",
                str(project_root),
                "--version-source",
                "source",
            ],
            cwd=fixture_root,
            env=source_env,
        )

        _run([python, "-m", "pip", "install", "-e", str(repo_root)], cwd=repo_root, env=base_env)
        _run(
            [
                python,
                str(consumer),
                "--project-root",
                str(project_root),
                "--version-source",
                "metadata",
            ],
            cwd=fixture_root,
            env=base_env,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--python", default=sys.executable)
    arguments = parser.parse_args(argv)
    try:
        run_source_compat(arguments.repo_root, arguments.python)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
