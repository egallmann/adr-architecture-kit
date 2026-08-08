"""Tests for canonical entity ID normalization."""

from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner
import yaml

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
    _fixture(tmp_path)
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


def _promoted_collision_fixture(root: Path) -> Path:
    _write(
        root / "PROJECT.yaml",
        """
        schema_version: "1.0"
        type: project_metadata
        project:
          name: promoted-collision-test
          description: promoted collision fixture
          type: library
        ownership:
          team: architecture
        repository:
          url: local
          primary_branch: main
        architecture_documentation:
          adr_directory: adrs/
          manifest_path: adrs/manifest.yaml
          architecture_namespace: promoted-collision-test
        """,
    )
    adr_dir = root / "adrs"
    _write(
        adr_dir / "logical" / "ADR-L-2000-a.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-2000
        title: First logical definition
        status: accepted
        created_date: "2026-01-01"
        authors: [test.author]
        domains: [architecture]
        context: First definition.
        architectural_boundaries:
          - id: BOUND-0001
            name: First boundary
            description: First boundary.
            rationale: First owner retains the historical ID.
        interaction_contracts:
          - id: CONTRACT-0001
            parties: [COMP-2000, COMP-2001]
            protocol: test
            guarantees: First contract.
        """,
    )
    _write(
        adr_dir / "logical" / "ADR-L-2001-b.yaml",
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-2001
        title: Second logical definition
        status: accepted
        created_date: "2026-01-02"
        authors: [test.author]
        domains: [architecture]
        context: Second definition.
        architectural_boundaries:
          - id: BOUND-0001
            name: Second boundary
            description: Second boundary.
            rationale: This occurrence is remapped.
        interaction_contracts:
          - id: CONTRACT-0001
            parties: [COMP-2000, COMP-2001]
            protocol: test
            guarantees: Second contract.
        """,
    )
    for number, created_date in ((2000, "2026-01-01"), (2001, "2026-01-02")):
        _write(
            adr_dir / "physical-component" / f"ADR-PC-{number}-component.yaml",
            f"""
            schema_version: "1.0"
            adr_type: physical-component
            id: ADR-PC-{number}
            title: Component {number}
            status: accepted
            created_date: "{created_date}"
            authors: [test.author]
            domains: [architecture]
            implements_system: [ADR-PS-2000]
            implements_logical: [ADR-L-2000]
            context: Component definition.
            technology_stack: []
            component_specifications:
              - id: COMP-{number}
                name: Component {number}
                type: service
                responsibilities: Test component.
                generation_context:
                  purpose: Test component.
                  key_responsibilities: [test]
                interfaces:
                  - id: IFACE-0001
                    type: library_api
                    specification: Interface {number}.
                implementation_identifiers:
                  module_path: src/component_{number}.py
                implementation_requirements: {{}}
            implementation_decisions:
              - id: IMPL-0001
                summary: Implementation decision {number}
                rationale: Test decision.
            """,
        )
    _write(
        adr_dir / "migrations" / "canonical-id-allocation.yaml",
        """
        schema_version: "1.0"
        type: canonical_id_allocation
        high_water_marks:
          BOUND: 10
          CONTRACT: 5
          IFACE: 20
          IMPL: 12
        allocations: []
        """,
    )
    return adr_dir


def test_repair_plan_covers_promoted_types_and_uses_historical_high_water(tmp_path):
    _promoted_collision_fixture(tmp_path)
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)

    plan = normalizer.plan(scope)

    assert plan.ambiguities == []
    assert [
        (item.entity_type, item.adr_id, item.old_id, item.new_id, item.source_pointer)
        for item in plan.remaps
    ] == [
        ("boundary", "ADR-L-2001", "BOUND-0001", "BOUND-0011", "/architectural_boundaries/0/id"),
        ("contract", "ADR-L-2001", "CONTRACT-0001", "CONTRACT-0006", "/interaction_contracts/0/id"),
        (
            "implementation_decision",
            "ADR-PC-2001",
            "IMPL-0001",
            "IMPL-0013",
            "/implementation_decisions/0/id",
        ),
        (
            "interface",
            "ADR-PC-2001",
            "IFACE-0001",
            "IFACE-0021",
            "/component_specifications/0/interfaces/0/id",
        ),
    ]


def test_repair_apply_writes_definitions_ledgers_and_is_idempotent(tmp_path):
    adr_dir = _promoted_collision_fixture(tmp_path)
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)

    first = normalizer.repair(scope, apply=True)
    second = normalizer.repair(scope, apply=True)

    assert len(first.remaps) == 4
    assert second.remaps == []
    logical = ADRParser().parse_yaml(adr_dir / "logical" / "ADR-L-2001-b.yaml")
    physical = ADRParser().parse_yaml(adr_dir / "physical-component" / "ADR-PC-2001-component.yaml")
    assert logical["architectural_boundaries"][0]["id"] == "BOUND-0011"
    assert logical["interaction_contracts"][0]["id"] == "CONTRACT-0006"
    assert physical["component_specifications"][0]["interfaces"][0]["id"] == "IFACE-0021"
    assert physical["implementation_decisions"][0]["id"] == "IMPL-0013"

    allocation = ADRParser().parse_yaml(adr_dir / "migrations" / "canonical-id-allocation.yaml")
    assert {
        prefix: allocation["high_water_marks"][prefix]
        for prefix in ("BOUND", "CONTRACT", "IFACE", "IMPL")
    } == {"BOUND": 11, "CONTRACT": 6, "IFACE": 21, "IMPL": 13}
    assert any(item["id"] == "IFACE-0001" for item in allocation["allocations"])
    assert any(item["id"] == "IFACE-0021" for item in allocation["allocations"])

    remap = ADRParser().parse_yaml(adr_dir / "migrations" / "canonical-id-remap.yaml")
    assert any(
        item["from"] == "IFACE-0001"
        and item["to"] == "IFACE-0021"
        and item["source_pointer"] == "/component_specifications/0/interfaces/0/id"
        for item in remap["entries"]
    )


def test_repair_fails_closed_for_ambiguous_typed_reference(tmp_path):
    adr_dir = _promoted_collision_fixture(tmp_path)
    target = adr_dir / "logical" / "ADR-L-2002-reference.yaml"
    _write(
        target,
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-2002
        title: Ambiguous reference
        status: accepted
        created_date: "2026-01-03"
        authors: [test.author]
        domains: [architecture]
        introduces_entities: [BOUND-0001]
        context: This reference cannot identify which boundary it means.
        """,
    )
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)

    plan = normalizer.plan(scope)

    assert len(plan.ambiguities) == 1
    assert plan.ambiguities[0].source_pointer == "/introduces_entities/0"
    assert plan.ambiguities[0].entity_id == "BOUND-0001"
    try:
        normalizer.repair(scope, apply=True)
    except ValueError as exc:
        assert "Ambiguous canonical entity references require a resolution map" in str(exc)
    else:
        raise AssertionError("repair must fail closed for an ambiguous reference")
    assert ADRParser().parse_yaml(target)["introduces_entities"] == ["BOUND-0001"]


def test_occurrence_scoped_resolution_map_allows_adr_kit_to_apply_ambiguous_rewrite(
    tmp_path,
):
    adr_dir = _promoted_collision_fixture(tmp_path)
    target = adr_dir / "logical" / "ADR-L-2002-reference.yaml"
    _write(
        target,
        """
        schema_version: "1.0"
        adr_type: logical
        id: ADR-L-2002
        title: Reviewed reference
        status: accepted
        created_date: "2026-01-03"
        authors: [test.author]
        domains: [architecture]
        introduces_entities: [BOUND-0001]
        context: The reviewed mapping selects the second boundary.
        """,
    )
    resolution = adr_dir / "migrations" / "canonical-id-resolution.yaml"
    _write(
        resolution,
        """
        schema_version: "1.0"
        type: canonical_id_resolution
        references:
          - file_path: adrs/logical/ADR-L-2002-reference.yaml
            source_pointer: /introduces_entities/0
            target: adrs/logical/ADR-L-2001-b.yaml#/architectural_boundaries/0/id
        """,
    )
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)

    plan = normalizer.repair(scope, apply=True, resolution_map=resolution)

    assert plan.ambiguities == []
    assert ADRParser().parse_yaml(target)["introduces_entities"] == ["BOUND-0011"]


def test_repair_cli_is_dry_run_by_default_and_check_fails_on_collisions(tmp_path):
    adr_dir = _promoted_collision_fixture(tmp_path)
    runner = CliRunner()

    preview = runner.invoke(cli, ["repair-canonical-ids", "--scope", str(tmp_path)])
    check = runner.invoke(cli, ["repair-canonical-ids", "--scope", str(tmp_path), "--check"])

    assert preview.exit_code == 0, preview.output
    assert "Planned 4 canonical ID repairs; no files changed." in preview.output
    assert check.exit_code == 1
    assert "Canonical ID repair required" in check.output
    logical = ADRParser().parse_yaml(adr_dir / "logical" / "ADR-L-2001-b.yaml")
    assert logical["architectural_boundaries"][0]["id"] == "BOUND-0001"


def test_allocation_validation_passes_after_repair_and_detects_high_water_drift(
    tmp_path,
):
    adr_dir = _promoted_collision_fixture(tmp_path)
    normalizer = CanonicalIdNormalizer()
    scope = normalizer.scope_resolver.resolve(tmp_path)
    normalizer.repair(scope, apply=True)

    assert normalizer.validate_allocations(scope) == []

    ledger_path = adr_dir / "migrations" / "canonical-id-allocation.yaml"
    ledger = ADRParser().parse_yaml(ledger_path)
    ledger["high_water_marks"]["IFACE"] = 1
    ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

    assert any(
        "high-water mark IFACE must be at least 21" in finding
        for finding in normalizer.validate_allocations(scope)
    )
