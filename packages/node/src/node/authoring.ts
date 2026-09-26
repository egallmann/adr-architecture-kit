/** Thin public Authoring Construction adapters over semantic-core protocol 1.2. */

import { ContractValidationError } from "../errors.js";
import { packageVersion } from "../generated/package-metadata.js";
import { executeValidatedSemanticCoreRequest } from "./core.js";
import { supportsSemanticCoreOperation } from "./protocol.js";

const SEMANTIC_CORE_PROTOCOL_VERSION = "1.2" as const;
const CONTRACT_FAMILY = "authoring_construction" as const;
const CONTRACT_VERSION = "1.0" as const;

export type AuthoringOperation = "validate_authoring" | "construct_authoring_set";
export type AuthoringValidationStatus = "valid" | "invalid" | "unavailable" | "unresolved";
export type AuthoringConstructionOutcome = "Constructed" | "Rejected" | "Unavailable" | "Unresolved";
export type AuthoringJsonObject = Readonly<Record<string, unknown>>;

export interface AuthoringRequest {
  readonly contract_family: typeof CONTRACT_FAMILY;
  readonly contract_version: typeof CONTRACT_VERSION;
  readonly operation: AuthoringOperation;
  readonly request: AuthoringJsonObject;
  readonly basis: AuthoringJsonObject;
}

export interface AuthoringDiagnostic {
  readonly code: string;
  readonly severity: "info" | "warning" | "error";
  readonly status: "violation" | "blocked" | "unresolved" | "unavailable";
  readonly request_key: string | null;
  readonly location: string;
  readonly semantic_type: string | null;
  readonly rule: string;
  readonly expected: unknown;
  readonly observed: unknown;
  readonly remediation: string;
  readonly blocked_by?: readonly string[];
}

export interface AuthoringValidationResult {
  readonly request: AuthoringRequest;
  readonly contract_family: typeof CONTRACT_FAMILY;
  readonly contract_version: typeof CONTRACT_VERSION;
  readonly operation: "validate_authoring";
  readonly validation_status: AuthoringValidationStatus;
  readonly basis_qualification: AuthoringJsonObject;
  readonly diagnostics: readonly AuthoringDiagnostic[];
  readonly provenance: AuthoringJsonObject;
  readonly package_version: string;
  readonly api_contract_version: string;
}

export interface AuthoringConstructionResult {
  readonly request: AuthoringRequest;
  readonly contract_family: typeof CONTRACT_FAMILY;
  readonly contract_version: typeof CONTRACT_VERSION;
  readonly operation: "construct_authoring_set";
  readonly outcome: AuthoringConstructionOutcome;
  readonly basis_qualification: AuthoringJsonObject;
  readonly diagnostics: readonly AuthoringDiagnostic[];
  readonly candidate_fragments: readonly AuthoringJsonObject[];
  readonly candidate_artifacts: readonly AuthoringJsonObject[];
  readonly candidate_source_basis: AuthoringJsonObject | null;
  readonly construction_map: readonly AuthoringJsonObject[];
  readonly normalized_result: AuthoringJsonObject | null;
  readonly round_trip: AuthoringJsonObject;
  readonly provenance: AuthoringJsonObject;
  readonly package_version: string;
  readonly api_contract_version: string;
}

function cloneAndFreeze(value: unknown): unknown {
  if (Array.isArray(value)) return Object.freeze(value.map(cloneAndFreeze));
  if (value !== null && typeof value === "object") {
    return Object.freeze(Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, child]) => [key, cloneAndFreeze(child)]),
    ));
  }
  return value;
}

function object(value: unknown, field: string): AuthoringJsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new ContractValidationError(`Malformed authoring ${field}`);
  }
  return cloneAndFreeze(value) as AuthoringJsonObject;
}

function objectList(value: unknown, field: string): readonly AuthoringJsonObject[] {
  if (!Array.isArray(value)) throw new ContractValidationError(`Malformed authoring ${field}`);
  return Object.freeze(value.map((item) => object(item, field)));
}

function text(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new ContractValidationError(`Malformed authoring ${field}`);
  }
  return value;
}

function diagnostics(value: unknown): readonly AuthoringDiagnostic[] {
  if (!Array.isArray(value)) throw new ContractValidationError("Malformed authoring diagnostics");
  return Object.freeze(value.map((item) => {
    const raw = item as Record<string, unknown>;
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      throw new ContractValidationError("Malformed authoring diagnostic");
    }
    const severity = raw.severity;
    const status = raw.status;
    if (!(severity === "info" || severity === "warning" || severity === "error")) {
      throw new ContractValidationError("Malformed authoring diagnostic severity");
    }
    if (!(status === "violation" || status === "blocked" || status === "unresolved" || status === "unavailable")) {
      throw new ContractValidationError("Malformed authoring diagnostic status");
    }
    const blockedBy = raw.blocked_by;
    if (blockedBy !== undefined && !Array.isArray(blockedBy)) {
      throw new ContractValidationError("Malformed authoring diagnostic blocked_by");
    }
    const diagnostic: AuthoringDiagnostic = {
      code: text(raw.code, "diagnostic.code"),
      severity,
      status,
      request_key: typeof raw.request_key === "string" ? raw.request_key : null,
      location: text(raw.location, "diagnostic.location"),
      semantic_type: typeof raw.semantic_type === "string" ? raw.semantic_type : null,
      rule: text(raw.rule, "diagnostic.rule"),
      expected: cloneAndFreeze(raw.expected),
      observed: cloneAndFreeze(raw.observed),
      remediation: text(raw.remediation, "diagnostic.remediation"),
      ...(Array.isArray(blockedBy) ? { blocked_by: Object.freeze(blockedBy.map((item) => text(item, "diagnostic.blocked_by"))) } : {}),
    };
    return Object.freeze(diagnostic);
  }));
}

function assertRequest(value: AuthoringRequest): void {
  if (value === null || typeof value !== "object") throw new TypeError("request must be an AuthoringRequest");
  if (value.contract_family !== CONTRACT_FAMILY || value.contract_version !== CONTRACT_VERSION) {
    throw new TypeError("request must be an ACC 1.0 authoring_construction request");
  }
  if (value.operation !== "validate_authoring" && value.operation !== "construct_authoring_set") {
    throw new TypeError(`Unsupported authoring operation: ${String(value.operation)}`);
  }
  object(value.request, "request");
  object(value.basis, "basis");
}

function execute(request: AuthoringRequest): Promise<AuthoringJsonObject> {
  assertRequest(request);
  if (!supportsSemanticCoreOperation(SEMANTIC_CORE_PROTOCOL_VERSION, request.operation)) {
    throw new ContractValidationError(
      `Loaded semantic core does not advertise protocol ${SEMANTIC_CORE_PROTOCOL_VERSION} operation ${request.operation}`,
    );
  }
  return executeValidatedSemanticCoreRequest({
    core_contract_version: SEMANTIC_CORE_PROTOCOL_VERSION,
    operation: request.operation,
    request: {
      contract_family: request.contract_family,
      contract_version: request.contract_version,
      operation: request.operation,
      request: request.request,
      basis: request.basis,
    },
  }).then((envelope) => object(envelope.result, "result"), (error: unknown) => {
    if (error instanceof ContractValidationError) throw error;
    throw new ContractValidationError(`Authoring operation ${request.operation} could not complete: ${String(error)}`);
  });
}

function baseResult(value: AuthoringJsonObject, operation: AuthoringOperation): void {
  if (value.contract_family !== CONTRACT_FAMILY || value.contract_version !== CONTRACT_VERSION || value.operation !== operation) {
    throw new ContractValidationError("Semantic core returned an unexpected authoring result");
  }
  object(value.basis_qualification, "basis_qualification");
  object(value.provenance, "provenance");
  diagnostics(value.diagnostics);
}

export async function validateAuthoring(request: AuthoringRequest): Promise<AuthoringValidationResult> {
  assertRequest(request);
  if (request.operation !== "validate_authoring") throw new TypeError("validateAuthoring requires operation='validate_authoring'");
  const value = await execute(request);
  baseResult(value, "validate_authoring");
  const status = value.validation_status;
  if (!(status === "valid" || status === "invalid" || status === "unavailable" || status === "unresolved")) {
    throw new ContractValidationError("Semantic core returned an invalid validation_status");
  }
  return Object.freeze({
    request: Object.freeze({ ...request, request: object(request.request, "request"), basis: object(request.basis, "basis") }),
    contract_family: CONTRACT_FAMILY,
    contract_version: CONTRACT_VERSION,
    operation: "validate_authoring",
    validation_status: status,
    basis_qualification: object(value.basis_qualification, "basis_qualification"),
    diagnostics: diagnostics(value.diagnostics),
    provenance: object(value.provenance, "provenance"),
    package_version: packageVersion,
    api_contract_version: "1.0",
  });
}

export async function constructAuthoringSet(request: AuthoringRequest): Promise<AuthoringConstructionResult> {
  assertRequest(request);
  if (request.operation !== "construct_authoring_set") throw new TypeError("constructAuthoringSet requires operation='construct_authoring_set'");
  const value = await execute(request);
  baseResult(value, "construct_authoring_set");
  const outcome = value.outcome;
  if (!(outcome === "Constructed" || outcome === "Rejected" || outcome === "Unavailable" || outcome === "Unresolved")) {
    throw new ContractValidationError("Semantic core returned an invalid construction outcome");
  }
  return Object.freeze({
    request: Object.freeze({ ...request, request: object(request.request, "request"), basis: object(request.basis, "basis") }),
    contract_family: CONTRACT_FAMILY,
    contract_version: CONTRACT_VERSION,
    operation: "construct_authoring_set",
    outcome,
    basis_qualification: object(value.basis_qualification, "basis_qualification"),
    diagnostics: diagnostics(value.diagnostics),
    candidate_fragments: objectList(value.candidate_fragments, "candidate_fragments"),
    candidate_artifacts: objectList(value.candidate_artifacts, "candidate_artifacts"),
    candidate_source_basis: value.candidate_source_basis === null ? null : object(value.candidate_source_basis, "candidate_source_basis"),
    construction_map: objectList(value.construction_map, "construction_map"),
    normalized_result: value.normalized_result === null ? null : object(value.normalized_result, "normalized_result"),
    round_trip: object(value.round_trip, "round_trip"),
    provenance: object(value.provenance, "provenance"),
    package_version: packageVersion,
    api_contract_version: "1.0",
  });
}
