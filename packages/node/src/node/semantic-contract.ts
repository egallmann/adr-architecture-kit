/**
 * Public Node bindings for the immutable semantic-contract boundary.
 *
 * This file intentionally has no canonicalization or fingerprint logic. It
 * adapts JavaScript values to the versioned WASM transport and freezes the
 * returned views; the Rust semantic core remains the sole meaning authority.
 */
import { semanticContractAssets } from "../generated/semantic-contract-assets.js";
import { executeValidatedSemanticCoreRequest } from "./core.js";
import type { AdrKitDiagnostic } from "../errors.js";

const assets = semanticContractAssets as Record<string, unknown>;

export const SCF_SCHEME = "scf:v1:sha256" as const;
export const SCS_SCHEME = "scs:v1:sha256" as const;

export interface SemanticResourceDependency {
  readonly canonicalResourceKey: string;
  readonly contentDigest: string;
}

export interface SemanticResourceManifestEntry {
  readonly canonicalResourceKey: string;
  readonly contentDigest: string;
  readonly role: string;
  readonly dependencies: readonly SemanticResourceDependency[];
}

export interface SemanticContractVersion {
  readonly semanticContractFamily: string;
  readonly semanticContractVersion: string;
  readonly fingerprintScheme: typeof SCF_SCHEME;
  readonly resourceManifest: readonly SemanticResourceManifestEntry[];
  readonly frozenNormativeConformanceResources: readonly string[];
  readonly semanticContractFingerprint: string;
}

export interface SemanticOperationResult {
  readonly success: boolean;
  readonly diagnostics: readonly AdrKitDiagnostic[];
  readonly canonical_preimage_json?: string | null;
  readonly canonical_preimage_hex?: string | null;
  readonly fingerprint?: string | null;
  readonly semantic_contract_fingerprint?: string | null;
  readonly semantic_contract_set_id?: string | null;
  readonly mode?: "calculate" | "verify" | null;
  readonly closure_valid?: boolean;
}

function deepFreeze<T>(value: T): T {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
  return Object.freeze(value);
}

function freezeResult(result: Record<string, unknown>): SemanticOperationResult {
  const normalized = { ...result, diagnostics: Array.isArray(result.diagnostics) ? result.diagnostics : [] };
  return deepFreeze(normalized) as unknown as SemanticOperationResult;
}

async function execute(operation: string, fields: Record<string, unknown>): Promise<SemanticOperationResult> {
  return freezeResult(await executeValidatedSemanticCoreRequest({
    core_contract_version: "1.0",
    operation,
    ...fields,
  }));
}

export function canonicalizeSemanticJson(value: unknown): Promise<SemanticOperationResult> {
  return typeof value === "string"
    ? execute("canonicalize_semantic_json", { value_json: value })
    : execute("canonicalize_semantic_json", { value });
}

export function calculateSemanticContractFingerprint(
  definition: SemanticContractVersion | Record<string, unknown>,
): Promise<SemanticOperationResult> {
  return execute("fingerprint_semantic_contract", { definition, mode: "calculate" });
}

export function verifySemanticContract(
  definition: SemanticContractVersion | Record<string, unknown>,
): Promise<SemanticOperationResult> {
  return execute("fingerprint_semantic_contract", { definition, mode: "verify" });
}

export function validateSemanticResourceClosure(
  definition: SemanticContractVersion | Record<string, unknown>,
  resources: readonly Record<string, unknown>[],
): Promise<SemanticOperationResult> {
  return execute("validate_semantic_resource_closure", {
    definition,
    resources,
  });
}

export function composeSemanticContractSet(
  contracts: readonly (SemanticContractVersion | Record<string, unknown>)[],
): Promise<SemanticOperationResult> {
  const members = contracts.map((item) => {
    const value = item as Record<string, unknown>;
    return {
      semanticContractFamily: value.semanticContractFamily,
      semanticContractVersion: value.semanticContractVersion,
      semanticContractFingerprint: value.semanticContractFingerprint,
    };
  });
  return execute("compose_semantic_contract_set", { contracts: members });
}

function definition(name: "normative-semantics.json" | "architecture-interpretation.json" | "normalized-model.json"): SemanticContractVersion {
  return deepFreeze(structuredClone(assets[`definitions/${name}`])) as SemanticContractVersion;
}

export function listSemanticContracts(): readonly SemanticContractVersion[] {
  return Object.freeze([
    definition("architecture-interpretation.json"),
    definition("normalized-model.json"),
    definition("normative-semantics.json"),
  ]);
}

export function getSemanticContract(family: string, version = "1.0"): SemanticContractVersion {
  const contract = listSemanticContracts().find(
    (item) => item.semanticContractFamily === family && item.semanticContractVersion === version,
  );
  if (!contract) throw new Error(`Unsupported semantic contract: ${family}:${version}`);
  return contract;
}

export function loadSemanticResource(key: string): unknown {
  const parts = key.split("/");
  if (parts.length < 3 || !["1.0", "1.5", "1.6", "2.3"].includes(parts[1] ?? "")) throw new Error(`Unsupported semantic resource: ${key}`);
  const names = [`${key.replaceAll("/", "-")}.json`];
  if (parts.length === 3) names.push(`${parts[0]}-${parts[2]}.json`);
  for (const name of names) {
    const resource = assets[`resources/${name}`];
    if (resource) return deepFreeze(structuredClone(resource));
  }
  throw new Error(`Missing bundled semantic resource: ${key}`);
}
