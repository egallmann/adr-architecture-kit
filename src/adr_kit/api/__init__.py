"""Narrow supported Python SDK for ADR Kit authoring consumers."""

from ..models import NormalizedArchitectureModel
from ..repository import ArchitectureRepository
from ._contracts import (
    ArtifactDescriptor,
    CapabilityManifest,
    CompilationRequest,
    CompilationResult,
    Diagnostic,
    ValidationRequest,
    ValidationResult,
)
from ._errors import InvalidRequestError, OperationError, RepositoryError, SDKError
from ._operations import (
    capabilities,
    compile_architecture,
    open_repository,
    validate_architecture,
)

__all__ = [
    "ArchitectureRepository",
    "NormalizedArchitectureModel",
    "ArtifactDescriptor",
    "CapabilityManifest",
    "ValidationRequest",
    "ValidationResult",
    "CompilationRequest",
    "CompilationResult",
    "Diagnostic",
    "SDKError",
    "InvalidRequestError",
    "OperationError",
    "RepositoryError",
    "capabilities",
    "validate_architecture",
    "compile_architecture",
    "open_repository",
]
