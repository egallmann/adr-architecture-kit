from pathlib import Path

from adr_kit.compiler import (
    ArchModelBuilder,
    CompilerConfig,
    CompilerPipelineState,
    DiagnosticLog,
    build_default_frontend_pipeline,
)
from adr_kit.compiler.frontend import CachedADRParser
from adr_kit.compiler.pipeline import run_frontend_pipeline
from adr_kit.compiler.backend.projection import project_entity, project_relationship, project_unresolved
from adr_kit.scope import ProjectScopeResolver


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


def test_default_frontend_pipeline_pass_order():
    pipeline = build_default_frontend_pipeline()

    assert [pipeline_pass.name for pipeline_pass in pipeline.passes] == [
        "adr_parse",
        "version_detection",
        "adr_normalization",
        "logical_entity_extraction",
        "invariant_extraction",
        "physical_entity_extraction",
        "relationship_inference",
        "unresolved_detection",
        "validation",
    ]


def test_pipeline_state_matches_builder_output():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    resolver = ProjectScopeResolver(explicit_scope=scope.root)
    diagnostics = DiagnosticLog()
    config = CompilerConfig()

    pipeline_result = run_frontend_pipeline(
        scope=scope,
        parser=CachedADRParser(),
        config=config,
        diagnostics=diagnostics,
    )
    builder_result = ArchModelBuilder(
        parser=CachedADRParser(),
        scope_resolver=resolver,
        config=config,
        diagnostics=DiagnosticLog(),
    ).build_from_scope(scope)

    assert pipeline_result.coverage == builder_result.coverage
    assert pipeline_result.namespace == builder_result.namespace
    assert _projected_bundle(pipeline_result.model) == _projected_bundle(builder_result.model)


def test_pipeline_state_initializes_from_scope():
    scope = ProjectScopeResolver(explicit_scope=_repo_root()).resolve()
    state = CompilerPipelineState(
        scope=scope,
        parser=CachedADRParser(),
        config=CompilerConfig(),
        diagnostics=DiagnosticLog(),
    )

    assert state.scope.root == scope.root
    assert state.model.metadata.scope_root is None
    assert state.namespace == ""
