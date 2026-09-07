"""Host adapter for the versioned ADR-Kit semantic execution boundary."""

from .semantic_core import (
    execute_architecture_validation,
    execute_architecture_reference_validation,
    execute_contract_validation,
    execute_generated_artifact_classification,
    execute_project_metadata_validation,
    execute_provider_registry,
    execute_repository_validation,
    execute_semantic_core_request,
    execute_validated_semantic_core_request,
    validate_semantic_core_protocol,
)

__all__ = [
    "execute_architecture_validation",
    "execute_architecture_reference_validation",
    "execute_contract_validation",
    "execute_generated_artifact_classification",
    "execute_project_metadata_validation",
    "execute_provider_registry",
    "execute_repository_validation",
    "execute_semantic_core_request",
    "execute_validated_semantic_core_request",
    "validate_semantic_core_protocol",
]
