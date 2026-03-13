"""Shared pytest fixtures for adr_kit tests."""

import re
import shutil
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path(request):
    """Use a repo-owned temp directory to avoid OS temp permission issues."""
    repo_root = Path(__file__).resolve().parent.parent
    base_dir = repo_root / "tests" / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.node.nodeid)
    path = base_dir / f"{safe_name[:48]}-{uuid.uuid4().hex[:6]}"
    path.mkdir(parents=True, exist_ok=False)

    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
