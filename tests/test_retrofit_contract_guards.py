"""Attribution retrofit contract guards — ADR-scoped boundary assertions."""

from __future__ import annotations

import pytest

from src.adr_kit.cli.main import cli
from src.adr_kit.compiler.backend.adr_ir_fragment_emitter import compile_logical_adr_ir_fragments
from src.adr_kit.compiler.backend.graph_emitter import emit_graph_artifact
from src.adr_kit.compiler.backend.manifest_emitter import emit_manifest_artifact
from src.adr_kit.compiler.backend.markdown_emitter import emit_markdown_artifacts
from src.adr_kit.compiler.backend.registry_emitter import emit_registry_artifacts
from src.adr_kit.compiler.driver import ArchitectureCompiler
from src.adr_kit.compiler.pipeline import CompilerPipeline, run_frontend_pipeline
from src.adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from src.adr_kit.generators.entity_registry_generator import EntityRegistryGenerator
from src.adr_kit.generators.manifest_generator import ManifestGenerator
from src.adr_kit.generators.scaffold_generator import ScaffoldGenerator
from src.adr_kit.generators.system_overview_generator import SystemOverviewGenerator
from src.adr_kit.integrity.validation import GeneratedArtifactValidator
from src.adr_kit.models.normalized_architecture_model import NormalizedArchitectureModel
from src.adr_kit.parser.yaml_parser import ADRParser
from src.adr_kit.projection import ProjectionInspector
from src.adr_kit.repository.architecture_repository import ArchitectureRepository
from src.adr_kit.repository.registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_legacy_entity_registry,
    load_normalized_entity_registry,
    load_relationship_registry,
    load_remediation_ledger,
    load_unresolved_registry,
    model_payload,
)
from src.adr_kit.repository.semantic_adapter import (
    coerce_to_normalized_model,
    legacy_entity_to_normalized,
    legacy_relationships,
)
from src.adr_kit.schema.contract_validation import validate_adr_contract_bundle
from src.adr_kit.schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)
from src.adr_kit.schema.repository_schema_generator import generate_repository_schema_documents
from src.adr_kit.validators import ADRValidator, EntityValidator, SystemOverviewValidator

from tests.provenance_test_helpers import (
    class_adr_metadata,
    expect_adr_claims,
    expect_adr_source_exists,
    function_adr_metadata,
)


class TestAdrL0001MachineVerifiableAdrSystem:
    def test_adr_parser(self) -> None:
        assert class_adr_metadata(ADRParser) == ("ADR-L-0001",)

    def test_adr_validator_validate_file(self) -> None:
        expect_adr_claims(ADRValidator.validate_file, "ADR-L-0001")


class TestAdrL0002MultiScopeArchitecture:
    def test_cli_group(self) -> None:
        assert class_adr_metadata(cli) == ("ADR-L-0002", "ADR-L-0013")


class TestAdrL0004ImplementationTraceability:
    def test_validate_implementation_attribution_evidence(self) -> None:
        expect_adr_claims(
            validate_implementation_attribution_evidence,
            "ADR-L-0004",
            ("INV-0027", "INV-0028", "INV-0029"),
        )


class TestAdrL0007DocumentationProjection:
    def test_projection_inspector(self) -> None:
        assert class_adr_metadata(ProjectionInspector) == ("ADR-L-0007",)

    def test_system_overview_generator(self) -> None:
        assert class_adr_metadata(SystemOverviewGenerator) == ("ADR-L-0007",)

    def test_emit_markdown_artifacts(self) -> None:
        expect_adr_claims(emit_markdown_artifacts, "ADR-L-0007")


class TestAdrL0009DiscoverySurfaces:
    def test_architecture_compiler(self) -> None:
        assert class_adr_metadata(ArchitectureCompiler) == ("ADR-L-0009", "ADR-L-0013")

    def test_compiler_pipeline(self) -> None:
        assert class_adr_metadata(CompilerPipeline) == ("ADR-L-0009", "ADR-L-0013")

    def test_run_frontend_pipeline(self) -> None:
        expect_adr_claims(run_frontend_pipeline, "ADR-L-0009")

    def test_architecture_index_generator(self) -> None:
        expect_adr_claims(ArchitectureIndexGenerator, "ADR-L-0009")


class TestAdrL0010KernelInterfaceContract:
    def test_validate_adr_contract_bundle(self) -> None:
        expect_adr_claims(validate_adr_contract_bundle, "ADR-L-0010")

    def test_manifest_generator(self) -> None:
        expect_adr_claims(ManifestGenerator, "ADR-L-0010")


class TestAdrL0011MetadataSchemas:
    def test_validate_adr_contract_bundle(self) -> None:
        adr_ids = function_adr_metadata(validate_adr_contract_bundle)
        assert "ADR-L-0011" in adr_ids

    def test_generate_repository_schema_documents(self) -> None:
        expect_adr_claims(generate_repository_schema_documents, "ADR-L-0011")


class TestAdrL0013RepositoryBoundary:
    def test_architecture_repository(self) -> None:
        assert class_adr_metadata(ArchitectureRepository) == ("ADR-L-0013",)

    def test_normalized_architecture_model_entity_ids(self) -> None:
        expect_adr_claims(NormalizedArchitectureModel.entity_ids, "ADR-L-0013")

    def test_registry_loaders(self) -> None:
        expect_adr_claims(load_architecture_index, "ADR-L-0013")
        expect_adr_claims(load_normalized_entity_registry, "ADR-L-0013")

    def test_semantic_adapter(self) -> None:
        expect_adr_claims(coerce_to_normalized_model, "ADR-L-0013")


class TestAdrL0015GovernanceState:
    def test_adr_validator_class(self) -> None:
        adr_ids = class_adr_metadata(ADRValidator)
        assert "ADR-L-0015" in adr_ids
        assert "ADR-L-0001" in adr_ids


class TestAdrL9000KernelBootPublication:
    def test_compile_logical_adr_ir_fragments(self) -> None:
        adr_ids = function_adr_metadata(compile_logical_adr_ir_fragments)
        assert "ADR-L-9000" in adr_ids
        assert "ADR-L-0013" in adr_ids


class TestAdrPcPhysicalComponents:
    def test_entity_registry_generator(self) -> None:
        expect_adr_claims(EntityRegistryGenerator, "ADR-PC-0001")

    def test_emit_registry_artifacts(self) -> None:
        expect_adr_claims(emit_registry_artifacts, "ADR-PC-0003")

    def test_generated_artifact_validator(self) -> None:
        adr_ids = class_adr_metadata(GeneratedArtifactValidator)
        assert "ADR-PC-0005" in adr_ids


class TestNegativeSpace:
    def test_scaffold_generator_has_no_direct_adr_claims(self) -> None:
        assert function_adr_metadata(ScaffoldGenerator.scaffold) == ()
        assert class_adr_metadata(ScaffoldGenerator) == ()

    def test_scaffold_generator_class_has_no_class_level_claims(self) -> None:
        assert class_adr_metadata(ScaffoldGenerator) == ()


class TestAdrSourceAnchors:
    @pytest.mark.parametrize(
        ("adr_id", "relative_path"),
        [
            ("ADR-L-0004", "adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml"),
            (
                "ADR-L-0013",
                "adrs/logical/ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.yaml",
            ),
            ("ADR-L-0009", "adrs/logical/ADR-L-0009-derived-architecture-discovery-surfaces.yaml"),
        ],
    )
    def test_wave_sample_adrs_exist_on_disk(self, adr_id: str, relative_path: str) -> None:
        expect_adr_source_exists(adr_id, relative_path)
