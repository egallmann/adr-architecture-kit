"""Narrow supported Python SDK for ADR Kit authoring consumers."""

from ..models import NormalizedArchitectureModel
from ..models.v2_0 import NormalizedArchitectureModelV2
from ..repository import ArchitectureRepository, ProviderRegistry
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
    apply_promotion,
    capabilities,
    check_promotion,
    compile_architecture,
    open_provider_registry,
    open_repository,
    prepare_promotion,
    validate_architecture,
)
from ._promotion_contracts import (
    PromotionApplyRequest,
    PromotionApplyResult,
    PromotionBaselineDescriptor,
    PromotionBindingDescriptor,
    PromotionBlockerDescriptor,
    PromotionCheckRequest,
    PromotionCheckResult,
    PromotionExecutionEvidenceDescriptor,
    PromotionMutationDescriptor,
    PromotionPrepareRequest,
    PromotionPrepareResult,
    PromotionValidationEvidenceDescriptor,
)

__all__ = [
    "ArchitectureRepository",
    "NormalizedArchitectureModel",
    "NormalizedArchitectureModelV2",
    "ProviderRegistry",
    "ArtifactDescriptor",
    "CapabilityManifest",
    "ValidationRequest",
    "ValidationResult",
    "CompilationRequest",
    "CompilationResult",
    "PromotionPrepareRequest",
    "PromotionPrepareResult",
    "PromotionCheckRequest",
    "PromotionCheckResult",
    "PromotionApplyRequest",
    "PromotionApplyResult",
    "PromotionMutationDescriptor",
    "PromotionBindingDescriptor",
    "PromotionValidationEvidenceDescriptor",
    "PromotionBlockerDescriptor",
    "PromotionBaselineDescriptor",
    "PromotionExecutionEvidenceDescriptor",
    "Diagnostic",
    "SDKError",
    "InvalidRequestError",
    "OperationError",
    "RepositoryError",
    "capabilities",
    "validate_architecture",
    "compile_architecture",
    "open_repository",
    "open_provider_registry",
    "prepare_promotion",
    "check_promotion",
    "apply_promotion",
]
