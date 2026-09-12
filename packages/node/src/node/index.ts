export { openRepository, type ArchitectureRepository } from "./repository.js";
export { materializeArchitecture, type ArchitectureMaterializationRequest, type ArchitectureMaterializationResult, type MaterializationAuthorityProvider, type MaterializationCapabilityLimitation, type MaterializationProviderProvenance, type MaterializationSemanticBasis, type MaterializationSourceArtifact, type MaterializationSourceBasis, type MaterializationSourceContract } from "./materialization.js";
export { executeSemanticCoreRequest, openProviderRegistry, validateContract, validateProjectMetadata, type ContractProfile, type ContractValidationDiagnostic, type ContractValidationIssue, type ContractValidationRequest, type ContractValidationResult, type ProjectMetadataValidationDiagnostic, type ProjectMetadataValidationRequest, type ProjectMetadataValidationResult, type ProviderBinding, type ProviderRegistry } from "./core.js";
export { AdrKitError, AmbiguousAliasError, AttributionShimError, ContractValidationError, RepositoryError, RepositoryPathError, UnsupportedContractVersionError } from "../errors.js";
export {
  calculateSemanticContractFingerprint,
  canonicalizeSemanticJson,
  composeSemanticContractSet,
  listSemanticContractProfiles,
  getSemanticContractProfile,
  validateSemanticContractProfile,
  validateSemanticContractQualification,
  previewSemanticContractSetAssembly,
  applySemanticContractSetAssembly,
  validateSemanticContractCorpus,
  listSemanticContractSets,
  resolveCurrentSemanticContractSet,
  getSemanticContract,
  listSemanticContracts,
  loadSemanticResource,
  validateSemanticResourceClosure,
  verifySemanticContract,
  SCF_SCHEME,
  SCS_SCHEME,
  type SemanticContractVersion,
  type SemanticContractProfile,
  type SemanticOperationResult,
  type SemanticResourceDependency,
  type SemanticResourceManifestEntry,
} from "./semantic-contract.js";
