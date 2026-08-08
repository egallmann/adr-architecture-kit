from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from adr_kit.compiler import ArchModelBuilder
from adr_kit.compiler.registry_bundle import assemble_registry_bundle
from adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from adr_kit.scope import ProjectScopeResolver
from tests.golden.helpers import FIXED_TIMESTAMP, generate_deterministic_outputs, pinned_generation_time


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_compiler_owned_registry_bundle_matches_generator_bundle(tmp_path):
    generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    scope = ProjectScopeResolver(explicit_scope=tmp_path / "workspace").resolve()

    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))
    build_result = builder.build_from_scope(scope)
    build_result.model.metadata.generated_at = FIXED_TIMESTAMP

    compiled = assemble_registry_bundle(
        build_result.model,
        coverage=build_result.coverage,
        namespace=build_result.namespace,
        generated_at=FIXED_TIMESTAMP,
    )
    with pinned_generation_time():
        generated = ArchitectureIndexGenerator(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root)).generate_from_scope(scope)

    assert compiled.architecture_index.model_dump(mode="json") == generated.architecture_index.model_dump(mode="json")
    assert compiled.entity_registry.model_dump(mode="json") == generated.entity_registry.model_dump(mode="json")
    assert compiled.relationship_registry.model_dump(mode="json") == generated.relationship_registry.model_dump(mode="json")
    assert compiled.unresolved_registry.model_dump(mode="json") == generated.unresolved_registry.model_dump(mode="json")
    assert compiled.decision_registry.model_dump(mode="json") == generated.decision_registry.model_dump(mode="json")
    assert compiled.capability_registry.model_dump(mode="json") == generated.capability_registry.model_dump(mode="json")
    assert compiled.invariant_registry.model_dump(mode="json") == generated.invariant_registry.model_dump(mode="json")
    assert compiled.component_registry.model_dump(mode="json") == generated.component_registry.model_dump(mode="json")
    assert compiled.system_registry.model_dump(mode="json") == generated.system_registry.model_dump(mode="json")
    assert compiled.legacy_entity_registry.model_dump(mode="json") == generated.legacy_entity_registry.model_dump(mode="json")


def test_compiler_owned_registry_bundle_is_deterministic(tmp_path):
    generate_deterministic_outputs(_repo_root(), tmp_path / "workspace")
    scope = ProjectScopeResolver(explicit_scope=tmp_path / "workspace").resolve()
    builder = ArchModelBuilder(scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))

    first = builder.build_from_scope(scope)
    first.model.metadata.generated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second = builder.build_from_scope(scope)
    second.model.metadata.generated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first_bundle = assemble_registry_bundle(
        first.model,
        coverage=first.coverage,
        namespace=first.namespace,
        generated_at=first.model.metadata.generated_at,
    )
    second_bundle = assemble_registry_bundle(
        second.model,
        coverage=second.coverage,
        namespace=second.namespace,
        generated_at=second.model.metadata.generated_at,
    )

    assert first_bundle.entity_registry.model_dump(mode="json") == second_bundle.entity_registry.model_dump(mode="json")
    assert first_bundle.relationship_registry.model_dump(mode="json") == second_bundle.relationship_registry.model_dump(mode="json")
    assert first_bundle.unresolved_registry.model_dump(mode="json") == second_bundle.unresolved_registry.model_dump(mode="json")
