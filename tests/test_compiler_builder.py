from pathlib import Path

from adr_kit.compiler import ArchModelBuilder
from adr_kit.compiler.backend.projection import (
    project_entity,
    project_entity_v2,
    project_relationship,
    project_relationship_v2,
    project_unresolved,
)
from adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from adr_kit.scope import ProjectScopeResolver
from tests.golden.helpers import clone_scope_sources, generate_deterministic_outputs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _projected_bundle(model, *, model_version: str = "1.1", namespace: str = ""):
    if model_version == "2.0":
        entities = [
            projected.model_dump(mode="json")
            for entity in model.entities.values()
            if (projected := project_entity_v2(entity, model.relationships, namespace)) is not None
        ]
        relationships = [
            projected.model_dump(mode="json")
            for relationship in model.relationships.values()
            if (projected := project_relationship_v2(relationship)) is not None
        ]
    else:
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
    projected_entities, projected_relationships, projected_unresolved = _projected_bundle(
        build_result.model,
        model_version=build_result.model_version,
        namespace=build_result.namespace,
    )

    generator = ArchitectureIndexGenerator(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))
    bundle = generator.generate_from_scope(scope)

    assert projected_entities == [entity.model_dump(mode="json") for entity in bundle.entity_registry.entities]
    assert projected_relationships == [item.model_dump(mode="json") for item in bundle.relationship_registry.relationships]
    assert projected_unresolved == [item.model_dump(mode="json") for item in bundle.unresolved_registry.unresolved]


def test_builder_assigns_logical_adr_as_canonical_invariant_source():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))

    build_result = builder.build_from_scope(scope)
    invariant = build_result.model.entities.get("019fee89-e615-713e-b627-2ee4bf985295")

    assert invariant is not None
    assert invariant.entity_type == "invariant"
    assert invariant.canonical_source.source_type == "logical_adr"
    assert invariant.canonical_source.source_ref == (
        "019fee89-e615-70a5-861b-b2dde147e5af#019fee89-e615-713e-b627-2ee4bf985295"
    )
    assert invariant.metadata.get("alias_id") == "INV-0001"


def test_builder_is_deterministic_across_repeated_runs():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    resolver = ProjectScopeResolver(explicit_scope=scope.root)
    builder = ArchModelBuilder(scope_resolver=resolver)

    first = builder.build_from_scope(scope)
    second = builder.build_from_scope(scope)

    assert _projected_bundle(
        first.model, model_version=first.model_version, namespace=first.namespace
    ) == _projected_bundle(
        second.model, model_version=second.model_version, namespace=second.namespace
    )
