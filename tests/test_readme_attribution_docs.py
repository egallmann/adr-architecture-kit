"""The package README routes specialist attribution details to deeper docs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_does_not_duplicate_attribution_inventory() -> None:
    assert "## Implementation linkage" not in README
    assert "If `--evidence` is omitted" not in README
    assert "__architecture_attribution_claims__" not in README


def test_readme_routes_specialist_sdk_details_to_public_guides() -> None:
    assert "docs/public-sdk.md" in README
    assert "docs/public-surface-and-stability.md" in README
    assert "packages/node/README.md" in README
