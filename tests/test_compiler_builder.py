from pathlib import Path

from src.adr_kit.compiler import ArchModelBuilder
from src.adr_kit.compiler.backend.projection import project_entity, project_relationship, project_unresolved
from src.adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from src.adr_kit.scope import ProjectScopeResolver
from tests.golden.helpers import clone_scope_sources, generate_deterministic_outputs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _projected_bundle(model):
    entities = [
        projected.model_dump(mode="json")
        for entity in model.entities.values()
        if (projected := project_entity(entity, model.relationships)) is not None
    ]
    relationships = [
        project_relationship(relationship).model_dump(mode="json")
        for relationship in model.relationships.values()
    ]
    unresolved = [
        project_unresolved(item).model_dump(mode="json")
        for item in model.unresolved.values()
    ]
    return entities, relationships, unresolved


def test_builder_discovers_same_source_files_as_current_generator(tmp_path):
    clone_scope_sources(_repo_root(), tmp_path / "workspace")
    scope = ProjectScopeResolver(explicit_scope=tmp_path / "workspace").resolve()

    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))
    generator = ArchitectureIndexGenerator(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))

    assert builder.discover_source_files(scope.adr_dir) == generator._discover_source_files(scope.adr_dir)


def test_builder_projects_current_outputs_with_golden_parity(tmp_path):
    generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    scope = ProjectScopeResolver(explicit_scope=tmp_path / "workspace").resolve()
    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))

    build_result = builder.build_from_scope(scope)
    projected_entities, projected_relationships, projected_unresolved = _projected_bundle(build_result.model)

    generator = ArchitectureIndexGenerator(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))
    bundle = generator.generate_from_scope(scope)

    assert projected_entities == [entity.model_dump(mode="json") for entity in bundle.entity_registry.entities]
    assert projected_relationships == [item.model_dump(mode="json") for item in bundle.relationship_registry.relationships]
    assert projected_unresolved == [item.model_dump(mode="json") for item in bundle.unresolved_registry.unresolved]


def test_builder_assigns_standalone_invariant_as_canonical_source():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))

    build_result = builder.build_from_scope(scope)
    invariant = build_result.model.entities.get("INV-0001")

    assert invariant is not None
    assert invariant.entity_type == "invariant"
    assert invariant.canonical_source.source_type == "standalone_invariant"
    assert invariant.canonical_source.source_ref == "INV-0001"


def test_builder_is_deterministic_across_repeated_runs():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    resolver = ProjectScopeResolver(explicit_scope=scope.root)
    builder = ArchModelBuilder(scope_resolver=resolver)

    first = builder.build_from_scope(scope)
    second = builder.build_from_scope(scope)

    assert _projected_bundle(first.model) == _projected_bundle(second.model)
