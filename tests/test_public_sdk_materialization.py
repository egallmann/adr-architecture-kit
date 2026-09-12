"""Cross-host public architecture-materialization contract checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import adr_kit.api as api

VECTOR = Path("contracts/semantic-core/v1.1/vectors/architecture-materialization.json")


def _request() -> api.ArchitectureMaterializationRequest:
    request = json.loads(VECTOR.read_text(encoding="utf-8"))["cases"][0]["request"]
    source = request["sourceBasis"]
    artifacts = tuple(
        api.MaterializationSourceArtifact(
            source_ref=item["sourceRef"],
            artifact_path=item["artifactPath"],
            content_digest=item["contentDigest"],
            source_contract=api.MaterializationSourceContract(
                version=item["sourceContract"]["version"],
                schema_resource=api.SemanticResourceDependency(
                    item["sourceContract"]["schemaResource"]["canonicalResourceKey"],
                    item["sourceContract"]["schemaResource"]["contentDigest"],
                ),
                resource_closure=tuple(
                    api.SemanticResourceDependency(
                        value["canonicalResourceKey"], value["contentDigest"]
                    )
                    for value in item["sourceContract"]["resourceClosure"]
                ),
            ),
            document=item["document"],
        )
        for item in source["artifacts"]
    )
    return api.ArchitectureMaterializationRequest(
        semantic_contract_set_id=request["semanticContractSetId"],
        authority_provider=api.MaterializationAuthorityProvider(
            kind=request["authorityProvider"]["kind"],
            architecture_namespace=request["authorityProvider"]["architectureNamespace"],
        ),
        source_basis=api.MaterializationSourceBasis(
            provider_source_identity=source["providerSourceIdentity"],
            source_revision=source["sourceRevision"],
            artifacts=artifacts,
        ),
        direction="none",
        use_mode="new",
        profile_id="architecture-materialization@1.0",
    )


def test_public_materialization_uses_exact_authority_and_immutable_result() -> None:
    request = _request()
    result = api.materialize_architecture(request)

    assert result.success is True
    assert result.outcome == "Materialized"
    assert result.authority_provider == request.authority_provider
    assert result.source_basis is not None
    assert isinstance(result.source_basis, api.MaterializationSourceBasis)
    assert result.source_basis.sealed is True
    assert result.source_basis.provider_source_identity == "fixture-provider:example"
    assert result.source_basis.source_revision == "revision-1"
    assert len(result.source_basis.artifacts) == 1
    artifact = result.source_basis.artifacts[0]
    assert artifact.source_ref == "logical-16"
    assert artifact.artifact_path == "architecture/logical-16.yaml"
    assert artifact.content_digest.startswith("sha256:")
    assert artifact.source_contract.family == "authoring"
    assert artifact.source_contract.version == "1.6"
    assert artifact.source_contract.schema_resource.canonical_resource_key == (
        "authoring/1.6/schema/adr-logical.schema"
    )
    assert len(artifact.source_contract.resource_closure) == 3
    assert result.source_contract_closure == (artifact.source_contract,)
    assert result.semantic_basis.semantic_contract_set_id == request.semantic_contract_set_id
    assert result.semantic_basis.authority_state_fingerprint is not None
    assert result.normalized_model is not None
    assert result.normalized_model["schema_version"] == "2.3"
    assert result.source_capability_limitations == ()
    assert result.provider_provenance == api.MaterializationProviderProvenance(
        semantic_core_contract_version="1.1",
        package_version="0.10.1",
        host_binding="public-host",
    )
    assert result.diagnostics == ()
    assert result.package_version == "0.10.1"
    assert result.api_contract_version == "1.0"
    with pytest.raises(TypeError):
        result.normalized_model["schema_version"] = "2.2"  # type: ignore[index]
    with pytest.raises(TypeError):
        artifact.document["title"] = "mutated"  # type: ignore[index]


def test_public_materialization_round_trips_legacy_identity_map() -> None:
    request = _request()
    assert request.source_basis is not None
    source_basis = api.MaterializationSourceBasis(
        provider_source_identity=request.source_basis.provider_source_identity,
        source_revision=request.source_basis.source_revision,
        artifacts=request.source_basis.artifacts,
        legacy_identity_map={
            "sealed": True,
            "provider": "fixture-provider:example",
            "entries": [{"sourceId": "legacy:boundary", "canonicalId": "canonical:boundary"}],
        },
    )
    result = api.materialize_architecture(
        api.ArchitectureMaterializationRequest(
            semantic_contract_set_id=request.semantic_contract_set_id,
            authority_provider=request.authority_provider,
            source_basis=source_basis,
            direction=request.direction,
            use_mode=request.use_mode,
            profile_id=request.profile_id,
        )
    )

    assert result.source_basis is not None
    legacy_identity_map = result.source_basis.legacy_identity_map
    assert legacy_identity_map is not None
    assert legacy_identity_map["sealed"] is True
    assert legacy_identity_map["provider"] == "fixture-provider:example"
    assert legacy_identity_map["entries"] == (
        {"sourceId": "legacy:boundary", "canonicalId": "canonical:boundary"},
    )


def test_public_materialization_has_bounded_unavailable_outcome() -> None:
    request = _request()
    result = api.materialize_architecture(
        api.ArchitectureMaterializationRequest(
            semantic_contract_set_id=request.semantic_contract_set_id,
            authority_provider=request.authority_provider,
            source_basis=None,
            direction=request.direction,
            use_mode=request.use_mode,
            profile_id=request.profile_id,
        )
    )

    assert result.success is False
    assert result.outcome == "Unavailable"
    assert result.normalized_model is None


def test_public_materialization_rejects_unknown_exact_scs() -> None:
    request = _request()
    result = api.materialize_architecture(
        api.ArchitectureMaterializationRequest(
            semantic_contract_set_id="scs:v1:sha256:" + "0" * 64,
            authority_provider=request.authority_provider,
            source_basis=request.source_basis,
            direction=request.direction,
            use_mode=request.use_mode,
            profile_id=request.profile_id,
        )
    )

    assert result.success is False
    assert result.outcome == "Rejected"
    assert result.diagnostics
