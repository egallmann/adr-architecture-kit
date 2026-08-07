"""Phase 2 RED/GREEN contracts for normalized entity promotion."""

from __future__ import annotations

import shutil
from pathlib import Path

from adr_kit.generators import ArchitectureIndexGenerator
from adr_kit.repository import ArchitectureRepository
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "v1_2"


def _create_v12_scope(root: Path) -> None:
    shutil.copy2(ROOT / "PROJECT.yaml", root / "PROJECT.yaml")
    destinations = {
        "logical-bindings.yaml": root / "adrs" / "logical" / "ADR-L-9801-bindings.yaml",
        "physical-system-topology.yaml": (
            root / "adrs" / "physical-system" / "ADR-PS-9801-topology.yaml"
        ),
        "physical-component-semantics.yaml": (
            root / "adrs" / "physical-component" / "ADR-PC-9801-semantics.yaml"
        ),
    }
    for source_name, destination in destinations.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES / source_name, destination)


def _generate(root: Path):
    resolver = ProjectScopeResolver(explicit_scope=root)
    generator = ArchitectureIndexGenerator(scope_resolver=resolver)
    scope = resolver.resolve()
    bundle = generator.generate_from_scope(scope)
    paths = generator.save_bundle(bundle, scope)
    return bundle, paths


def test_phase2_promotes_exact_authorized_entity_types(tmp_path: Path) -> None:
    _create_v12_scope(tmp_path)
    bundle, _ = _generate(tmp_path)
    by_id = {entity.id: entity for entity in bundle.entity_registry.entities}

    assert by_id["BOUND-9801"].entity_type == "boundary"
    assert by_id["CONTRACT-9801"].entity_type == "contract"
    assert by_id["IFACE-9801"].entity_type == "interface"
    assert by_id["IMPL-9801"].entity_type == "implementation_decision"
    assert by_id["BOUND-9801"].canonical_source.source_ref == "ADR-L-9801#BOUND-9801"
    assert by_id["IFACE-9801"].canonical_source.source_ref == "ADR-PC-9801#IFACE-9801"

    projected_types = {entity.entity_type for entity in bundle.entity_registry.entities}
    assert projected_types == {
        "adr",
        "system",
        "component",
        "decision",
        "boundary",
        "contract",
        "interface",
        "implementation_decision",
    }
    assert not projected_types.intersection({"constraint", "nfr", "gap", "integration"})


def test_promoted_entities_have_declarations_and_typed_relationships(tmp_path: Path) -> None:
    _create_v12_scope(tmp_path)
    bundle, _ = _generate(tmp_path)
    relationships = {
        (item.relationship_type, item.from_entity_id, item.to_entity_id)
        for item in bundle.relationship_registry.relationships
    }

    assert ("declared_in", "BOUND-9801", "ADR-L-9801") in relationships
    assert ("declared_in", "CONTRACT-9801", "ADR-L-9801") in relationships
    assert ("declared_in", "IFACE-9801", "ADR-PC-9801") in relationships
    assert ("declared_in", "IMPL-9801", "ADR-PC-9801") in relationships
    assert ("provides_interface", "COMP-9801", "IFACE-9801") in relationships
    assert ("composed_of", "SYS-9801", "TOPO-0001") in relationships


def test_repository_queries_promoted_types_without_changing_decision_query(tmp_path: Path) -> None:
    _create_v12_scope(tmp_path)
    _generate(tmp_path)
    repository = ArchitectureRepository(project_root=tmp_path)
    model = repository.get_model()

    assert model.schema_version == "1.1"
    assert [item.id for item in repository.get_boundaries()] == ["BOUND-9801"]
    assert [item.id for item in repository.get_contracts()] == ["CONTRACT-9801"]
    assert [item.id for item in repository.get_interfaces()] == ["IFACE-9801"]
    assert [item.id for item in repository.get_implementation_decisions()] == ["IMPL-9801"]
    assert [item.id for item in repository.get_decisions()] == ["DEC-9801"]


def test_entity_projection_order_and_payload_are_deterministic(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _create_v12_scope(first_root)
    _create_v12_scope(second_root)
    first_bundle, _ = _generate(first_root)
    second_bundle, _ = _generate(second_root)

    first_keys = [(item.entity_type, item.id) for item in first_bundle.entity_registry.entities]
    second_keys = [(item.entity_type, item.id) for item in second_bundle.entity_registry.entities]
    assert [item_id for _, item_id in first_keys] == sorted(item_id for _, item_id in first_keys)
    assert first_keys == second_keys
    assert first_bundle.entity_registry.model_dump(
        mode="json"
    ) == second_bundle.entity_registry.model_dump(mode="json")
