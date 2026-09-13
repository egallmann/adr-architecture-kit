export { capabilities, type CapabilityManifest } from "./capabilities.js";
export { AdrKitError, ContractValidationError, UnsupportedContractVersionError, type AdrKitDiagnostic } from "./errors.js";
export { createArchitectureModel, type ArchitectureModelView } from "./model/index.js";
export type * from "./model/types.js";
export {
  describeContract,
  listTypes,
  describeType,
  AuthoringDiscoveryError,
  type AuthoringContractDescription,
  type AuthoringDiscriminator,
  type AuthoringParentConstraint,
  type AuthoringPolicy,
  type AuthoringPolicyStatus,
  type AuthoringTypeDescriptor,
  type AuthoringTypeKey,
  type AuthoringTypeKind,
  type AuthoringTypeList,
  type AuthoringTypeSummary,
} from "./authoring.js";
