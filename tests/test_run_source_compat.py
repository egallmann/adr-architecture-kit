"""Portable source/SDK compatibility helper contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

from scripts import run_source_compat as compat


def test_source_compat_helper_uses_pathlib_shutil_and_argv_subprocess() -> None:
    source = Path(compat.__file__).read_text(encoding="utf-8")
    assert "pathlib" in source
    assert "shutil" in source
    assert "external-consumer-sdk" in source
    assert "shell=True" not in source
    assert "env -u" not in source
    signature = inspect.signature(compat.run_source_compat)
    assert "repo_root" in signature.parameters
