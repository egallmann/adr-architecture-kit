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
    result = api.materialize_architecture(_request())

    assert result.success is True
    assert result.outcome == "Materialized"
    assert result.semantic_basis.semantic_contract_set_id == _request().semantic_contract_set_id
    assert result.normalized_model is not None
    assert result.normalized_model["schema_version"] == "2.3"
    with pytest.raises(TypeError):
        result.normalized_model["schema_version"] = "2.2"  # type: ignore[index]


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
