"""README attribution docs must stay a single, current evidence-lineage story."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
IMPLEMENTATION_LINKAGE = README.split("## Implementation linkage", 1)[1].split(
    "## Contributing", 1
)[0]


def test_readme_has_one_default_evidence_lookup_explanation() -> None:
    assert IMPLEMENTATION_LINKAGE.count("If `--evidence` is omitted") == 1
    assert (
        IMPLEMENTATION_LINKAGE.count(
            "{scope}/state/attribution/implementation-attribution-evidence.yaml"
        )
        == 1
    )
    assert (
        IMPLEMENTATION_LINKAGE.count(
            "{scope}/.ste/state/attribution/implementation-attribution-evidence.yaml"
        )
        == 1
    )


def test_readme_documents_both_attribution_schema_lineages_once() -> None:
    assert "schema/v1.1/implementation-attribution-evidence.schema.json" in IMPLEMENTATION_LINKAGE
    assert IMPLEMENTATION_LINKAGE.count("1.0/1.2 remain") == 1
    assert IMPLEMENTATION_LINKAGE.count("Canonical 1.5 lives") == 1
    assert "schema/v1.5/" in IMPLEMENTATION_LINKAGE
    assert "semantic implementation-attribution evidence" in IMPLEMENTATION_LINKAGE
    assert "not ADR authoring schema 1.5" in IMPLEMENTATION_LINKAGE
    assert "normalize-evidence" in IMPLEMENTATION_LINKAGE
    assert "`__architecture_attribution_claims__`" in IMPLEMENTATION_LINKAGE


def test_readme_does_not_imply_cli_searches_workspace_derived_state() -> None:
    assert "do not search `.ste-workspace` automatically" in IMPLEMENTATION_LINKAGE
    assert "passes that path via `--evidence`" in IMPLEMENTATION_LINKAGE
    assert (
        "{workspace}/.ste-workspace/state/adr-architecture-kit/attribution/"
        in IMPLEMENTATION_LINKAGE
    )
