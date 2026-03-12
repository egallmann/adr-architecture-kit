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
    "GeneratedArtifactStatus",
    "GeneratedArtifactValidationResult",
    "GeneratedArtifactValidator",
]
