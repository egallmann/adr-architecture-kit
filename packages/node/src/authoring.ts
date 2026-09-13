/**
 * Browser-safe ADC discovery over the generated canonical contract mirror.
 *
 * The mirror is generated from contracts/authoring-domain/v1.0/contract.json;
 * this module contains no authoring construction, mutation, persistence,
 * filesystem, network, identity, or repository behavior.
 */
import { authoringDomainContract } from "./generated/authoring-domain.js";
import { AdrKitError, type AdrKitDiagnostic } from "./errors.js";

export type AuthoringTypeKind = "adr" | "entity" | "relationship" | "value";
export type AuthoringPolicyStatus = "defined" | "deferred" | "not_applicable";

export interface AuthoringTypeKey {
  readonly kind: AuthoringTypeKind;
  readonly name: string;
}

export interface AuthoringParentConstraint {
  readonly kind: AuthoringTypeKind;
  readonly name: string;
  readonly minOccurs: number;
  readonly maxOccurs: number | null;
}

export interface AuthoringPolicy {
  readonly status: AuthoringPolicyStatus;
  readonly mode: string | null;
  readonly values: readonly string[];
  readonly allowedParents: readonly AuthoringParentConstraint[];
  readonly owner: string | null;
}

export interface AuthoringDiscriminator {
  readonly mode: string;
  readonly field: string | null;
  readonly value: string | null;
}

export interface AuthoringTypeSummary {
  readonly key: AuthoringTypeKey;
  readonly displayName: string;
  readonly description: string;
}

export interface AuthoringTypeList {
  readonly contractVersion: string;
  readonly types: readonly AuthoringTypeSummary[];
}

export interface AuthoringContractDescription {
  readonly contractId: string;
  readonly contractVersion: string;
  readonly definedCapabilities: readonly string[];
  readonly discoveryOperations: readonly string[];
  readonly typeKinds: readonly AuthoringTypeKind[];
}

export interface AuthoringTypeDescriptor {
  readonly contractVersion: string;
  readonly key: AuthoringTypeKey;
  readonly displayName: string;
  readonly description: string;
  readonly authoringMode: "direct" | "embedded" | "template";
  readonly semanticTypeOwnership: "adr_kit" | "consumer_qualified";
  readonly discriminator: AuthoringDiscriminator;
  readonly inputContract: AuthoringPolicy;
  readonly identityPolicy: AuthoringPolicy;
  readonly compositionPolicy: AuthoringPolicy;
  readonly referencePolicy: AuthoringPolicy;
  readonly fieldOwnershipPolicy: AuthoringPolicy;
}

export class AuthoringDiscoveryError extends AdrKitError {
  readonly diagnostics: readonly AdrKitDiagnostic[];

  constructor(code: string, message: string, path: string) {
    super(code, message);
    this.diagnostics = Object.freeze([Object.freeze({
      severity: "error" as const,
      code,
      message,
      path,
    })]);
  }
}

type JsonObject = Record<string, unknown>;
const contract = authoringDomainContract as unknown as JsonObject;

function freeze<T>(value: T): T {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value as JsonObject)) freeze(child);
  return Object.freeze(value);
}

function object(value: unknown, label: string): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Malformed canonical ADC ${label}`);
  }
  return value as JsonObject;
}

function array(value: unknown, label: string): readonly unknown[] {
  if (!Array.isArray(value)) throw new Error(`Malformed canonical ADC ${label}`);
  return value;
}

function requiredString(value: unknown, label: string): string {
  if (typeof value !== "string") throw new Error(`Malformed canonical ADC ${label}`);
  return value;
}

function assertContractVersion(contractVersion: string): void {
  const expected = requiredString(contract.contract_version, "contract_version");
  if (contractVersion !== expected) {
    throw new AuthoringDiscoveryError(
      "contract.unsupported_version",
      `Unsupported authoring-domain contract version: ${contractVersion}`,
      "contract_version",
    );
  }
}

function assertKind(kind: string): asserts kind is AuthoringTypeKind {
  const kinds = array(contract.type_kinds, "type_kinds").map((item) => requiredString(item, "type_kinds[]"));
  if (!kinds.includes(kind)) {
    throw new AuthoringDiscoveryError(
      "authoring.unknown_type_kind",
      `Unknown authoring type kind: ${kind}`,
      "kind",
    );
  }
}

function projectKey(value: unknown): AuthoringTypeKey {
  const raw = object(value, "type.key");
  return freeze({
    kind: requiredString(raw.kind, "type.key.kind") as AuthoringTypeKind,
    name: requiredString(raw.name, "type.key.name"),
  });
}

function projectParent(value: unknown): AuthoringParentConstraint {
  const raw = object(value, "composition_policy.allowed_parents[]");
  const maxOccurs = raw.max_occurs;
  if (maxOccurs !== null && typeof maxOccurs !== "number") {
    throw new Error("Malformed canonical ADC max_occurs");
  }
  return freeze({
    kind: requiredString(raw.kind, "parent.kind") as AuthoringTypeKind,
    name: requiredString(raw.name, "parent.name"),
    minOccurs: Number(raw.min_occurs),
    maxOccurs,
  });
}

function projectPolicy(value: unknown): AuthoringPolicy {
  const raw = object(value, "policy");
  const status = requiredString(raw.status, "policy.status");
  if (!(status === "defined" || status === "deferred" || status === "not_applicable")) {
    throw new Error(`Malformed canonical ADC policy status: ${status}`);
  }
  return freeze({
    status,
    mode: typeof raw.mode === "string" ? raw.mode : null,
    values: freeze(array(raw.values ?? [], "policy.values").map((item) => requiredString(item, "policy.values[]"))),
    allowedParents: freeze(array(raw.allowed_parents ?? [], "policy.allowed_parents").map(projectParent)),
    owner: typeof raw.owner === "string" ? raw.owner : null,
  });
}

function projectDiscriminator(value: unknown): AuthoringDiscriminator {
  const raw = object(value, "discriminator");
  return freeze({
    mode: requiredString(raw.mode, "discriminator.mode"),
    field: typeof raw.field === "string" ? raw.field : null,
    value: typeof raw.value === "string" ? raw.value : null,
  });
}

function projectSummary(value: unknown): AuthoringTypeSummary {
  const raw = object(value, "types[]");
  return freeze({
    key: projectKey(raw.key),
    displayName: requiredString(raw.display_name, "type.display_name"),
    description: requiredString(raw.description, "type.description"),
  });
}

function projectDescriptor(value: unknown): AuthoringTypeDescriptor {
  const raw = object(value, "types[]");
  return freeze({
    contractVersion: requiredString(raw.contract_version, "type.contract_version"),
    key: projectKey(raw.key),
    displayName: requiredString(raw.display_name, "type.display_name"),
    description: requiredString(raw.description, "type.description"),
    authoringMode: requiredString(raw.authoring_mode, "type.authoring_mode") as AuthoringTypeDescriptor["authoringMode"],
    semanticTypeOwnership: requiredString(raw.semantic_type_ownership, "type.semantic_type_ownership") as AuthoringTypeDescriptor["semanticTypeOwnership"],
    discriminator: projectDiscriminator(raw.discriminator),
    inputContract: projectPolicy(raw.input_contract),
    identityPolicy: projectPolicy(raw.identity_policy),
    compositionPolicy: projectPolicy(raw.composition_policy),
    referencePolicy: projectPolicy(raw.reference_policy),
    fieldOwnershipPolicy: projectPolicy(raw.field_ownership_policy),
  });
}

function typeValues(): readonly unknown[] {
  return array(contract.types, "types");
}

export function describeContract(contractVersion: string): AuthoringContractDescription {
  /** Describe the exact ADC version supported by this binding. */
  assertContractVersion(contractVersion);
  return freeze({
    contractId: requiredString(contract.contract_id, "contract_id"),
    contractVersion: requiredString(contract.contract_version, "contract_version"),
    definedCapabilities: freeze(array(contract.defined_capabilities, "defined_capabilities").map((item) => requiredString(item, "defined_capabilities[]"))),
    discoveryOperations: freeze(array(contract.discovery_operations, "discovery_operations").map((item) => requiredString(item, "discovery_operations[]"))),
    typeKinds: freeze(array(contract.type_kinds, "type_kinds").map((item) => requiredString(item, "type_kinds[]") as AuthoringTypeKind)),
  });
}

export function listTypes(contractVersion: string, kind?: string): AuthoringTypeList {
  /** List ADC types using an optional exact, case-sensitive kind filter. */
  assertContractVersion(contractVersion);
  if (kind !== undefined) assertKind(kind);
  const values = typeValues()
    .filter((value) => kind === undefined || projectKey(object(value, "types[]").key).kind === kind)
    .map(projectSummary)
    .sort((left, right) => left.key.kind.localeCompare(right.key.kind) || left.key.name.localeCompare(right.key.name));
  return freeze({
    contractVersion: requiredString(contract.contract_version, "contract_version"),
    types: freeze(values),
  });
}

export function describeType(contractVersion: string, kind: string, name: string): AuthoringTypeDescriptor {
  /** Describe one ADC type selected by the exact (kind, name) pair. */
  assertContractVersion(contractVersion);
  assertKind(kind);
  const match = typeValues().find((value) => {
    const key = projectKey(object(value, "types[]").key);
    return key.kind === kind && key.name === name;
  });
  if (match === undefined) {
    throw new AuthoringDiscoveryError(
      "authoring.unknown_type",
      `Unknown authoring type: ${kind}/${name}`,
      "name",
    );
  }
  return projectDescriptor(match);
}
