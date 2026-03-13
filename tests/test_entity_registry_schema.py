"""Schema validation tests for entity registry artifacts."""

from src.adr_kit.generators import EntityRegistryGenerator
from src.adr_kit.parser import ADRParser


def test_generated_entity_registry_parses_against_schema(tmp_path):
    """Generated registry output should round-trip through the parser."""
    root = tmp_path / "scope"
    root.mkdir(parents=True, exist_ok=True)

    (root / "PROJECT.yaml").write_text("project:\n  name: schema-test\n", encoding="utf-8")
    adr_dir = root / "adrs" / "logical"
    adr_dir.mkdir(parents=True, exist_ok=True)

    (adr_dir / "ADR-L-2000-schema-test.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-2000",
                'title: "Schema test"',
                "status: accepted",
                'created_date: "2026-03-13"',
                "authors: [test.author]",
                "domains: [architecture]",
                "introduces_entities: [CAP-2000]",
                "context: |",
                "  Schema validation fixture.",
                "capabilities:",
                "  - id: CAP-2000",
                '    name: "Schema capability"',
                '    description: "Used to validate entity registry schema output."',
                '    rationale: "Round-trip parser coverage."',
                "architectural_boundaries: []",
                "interaction_contracts: []",
                "constraints: []",
                "non_functional_requirements: []",
                "invariants: []",
                "decisions:",
                "  - id: DEC-2000",
                '    summary: "Schema coverage"',
                '    rationale: "Exercise parser round-trip."',
                "gaps: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    generator = EntityRegistryGenerator()
    registry = generator.generate_from_directory(root / "adrs")
    output_path = root / "adrs" / "entities" / "registry.yaml"
    generator.save_registry(registry, output_path)

    parsed = ADRParser().parse_entity_registry(output_path)

    assert parsed.type == "entity_registry"
    assert parsed.entities[0].entity_id == "CAP-2000"
