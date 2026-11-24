"""Shared pytest fixtures for adr_kit tests."""

import re
import shutil
import uuid
from pathlib import Path

import pytest

_ASSURANCE_LAYERS = {"fast", "integration", "governance", "crosshost", "benchmark"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Give every test one lifecycle layer; new tests default to full integration."""

    for item in items:
        selected = {
            marker.name for marker in item.iter_markers() if marker.name in _ASSURANCE_LAYERS
        }
        if not selected:
            item.add_marker(pytest.mark.integration)
        elif len(selected) != 1:
            raise pytest.UsageError(
                f"test must have exactly one assurance-layer marker, found {sorted(selected)}: {item.nodeid}"
            )


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
