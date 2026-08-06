"""Tests for canonical entity ID normalization."""

from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner

from adr_kit.cli.main import cli
from adr_kit.migrators.canonical_id_normalizer import CanonicalIdNormalizer
from adr_kit.parser import ADRParser


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def _fixture(root: Path) -> Path:
    _write(
        root / "PROJECT.yaml",
        """
        schema_version: "1.0"
        type: project_metadata
        project:
          name: collision-test
          description: collision fixture
          type: library
        ownership:
          team: architecture
        repository:
          url: local
          primary_branch: main
        architecture_documentation:
          adr_directory: adrs/
          manifest_path: adrs/manifest.yaml
          architecture_namespace: collision-test
        """,
    )
    adr_dir = root / "adrs"
    _write(
        adr_dir / "logical" / "ADR-L-1000-a.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-1000
        title: "A"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        introduces_entities: ["CAP-0001", "DEC-0001"]
        context: |
          First ADR.
        capabilities:
          - id: CAP-0001
            name: "A capability"
            description: "First capability."
        decisions:
          - id: DEC-0001
            summary: "A decision"
            rationale: "First decision."
            enables_capabilities: ["CAP-0001"]
        architectural_boundaries: []
        interaction_contracts: []
        constraints: []
        non_functional_requirements: []
        invariants: []
        gaps: []
        """,
    )
    _write(
        adr_dir / "logical" / "ADR-L-1001-b.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-1001
        title: "B"
        status: accepted
        created_date: "2026-03-13"
        authors: ["test.author"]
        domains: ["architecture"]
        introduces_entities: ["CAP-0001", "DEC-0001"]
        context: |
          Second ADR.
        capabilities:
          - id: CAP-0001
            name: "B capability"
            description: "Second capability."
            enabled_by_decisions: ["DEC-0001"]
        decisions:
          - id: DEC-0001
            summary: "B decision"
            rationale: "Second decision."
            enables_capabilities: ["CAP-0001"]
        architectural_boundaries: []
        interaction_contracts: []
        constraints: []
        non_functional_requirements: []
        invariants: []
        gaps: []
        """,
    )
    return adr_dir


def test_normalizer_remaps_collisions_deterministically(tmp_path):
    adr_dir = _fixture(tmp_path)
    normalizer = CanonicalIdNormalizer()

    remaps = normalizer.normalize(normalizer.scope_resolver.resolve(tmp_path))

    assert [(item.entity_type, item.adr_id, item.old_id, item.new_id) for item in remaps] == [
        ("capability", "ADR-L-1001", "CAP-0001", "CAP-0002"),
        ("decision", "ADR-L-1001", "DEC-0001", "DEC-0002"),
    ]

    data = ADRParser().parse_yaml(adr_dir / "logical" / "ADR-L-1001-b.yaml")
    assert data["introduces_entities"] == ["CAP-0002", "DEC-0002"]
    assert data["capabilities"][0]["id"] == "CAP-0002"
    assert data["capabilities"][0]["enabled_by_decisions"] == ["DEC-0002"]
    assert data["decisions"][0]["id"] == "DEC-0002"
    assert data["decisions"][0]["enables_capabilities"] == ["CAP-0002"]
    assert data["migration_origin"]["original_capability_id"] == "CAP-0001"
    assert len(data["migration_origin"]["remapped_entities"]) == 2

    ledger = ADRParser().parse_yaml(adr_dir / "migrations" / "canonical-id-remap.yaml")
    assert ledger["type"] == "canonical_id_remap"
    assert len(ledger["entries"]) == 2


def test_normalizer_is_idempotent(tmp_path):
    adr_dir = _fixture(tmp_path)
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)

    first = normalizer.normalize(scope)
    second = normalizer.normalize(scope)

    assert len(first) == 2
    assert second == []


def test_normalize_canonical_ids_cli(tmp_path):
    _fixture(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["normalize-canonical-ids", "--scope", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Normalized 2 canonical ID collisions." in result.output
    assert "adr generate-architecture-index --scope ." in result.output
