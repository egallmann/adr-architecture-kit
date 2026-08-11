"""Deterministic documentation projection integrity utilities."""

from .artifacts import ArtifactKind, GeneratedArtifact, ScopeProjectionArtifacts
from .core import (
    HASH_ALGORITHM,
    HEADER_FIELD_ORDER,
    INTEGRITY_SCHEMA_VERSION,
    GENERATED_MARKER,
    GeneratorIdentity,
    HashInput,
    build_markdown_header,
    build_yaml_header,
    compute_rendered_hash,
    compute_source_hash,
    extract_body_without_header,
    parse_integrity_header,
)
from .legacy_registry import LEGACY_ENTITY_REGISTRY_GENERATOR, legacy_entity_registry_source_inputs
from .transaction import (
    PlannedWrite,
    TransactionAborted,
    commit_all_or_none,
    recover_interrupted_commit,
)
from .validation import (
    GeneratedArtifactStatus,
    GeneratedArtifactValidationResult,
    GeneratedArtifactValidator,
)

__all__ = [
    "ArtifactKind",
    "GeneratedArtifact",
    "ScopeProjectionArtifacts",
    "HASH_ALGORITHM",
    "HEADER_FIELD_ORDER",
    "INTEGRITY_SCHEMA_VERSION",
    "GENERATED_MARKER",
    "GeneratorIdentity",
    "HashInput",
    "build_markdown_header",
    "build_yaml_header",
    "compute_rendered_hash",
    "compute_source_hash",
    "extract_body_without_header",
    "parse_integrity_header",
    "LEGACY_ENTITY_REGISTRY_GENERATOR",
    "legacy_entity_registry_source_inputs",
    "GeneratedArtifactStatus",
    "GeneratedArtifactValidationResult",
    "GeneratedArtifactValidator",
    "PlannedWrite",
    "TransactionAborted",
    "commit_all_or_none",
    "recover_interrupted_commit",
]
