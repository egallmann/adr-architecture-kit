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
  readonly semantic_contract_set_fingerprint?: string | null;
  readonly closure_valid?: boolean;
}

function freezeResult(result: Record<string, unknown>): SemanticOperationResult {
  const diagnostics = Array.isArray(result.diagnostics)
    ? Object.freeze(result.diagnostics as AdrKitDiagnostic[])
    : Object.freeze([] as AdrKitDiagnostic[]);
  return Object.freeze({ ...result, diagnostics }) as SemanticOperationResult;
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
  return execute("fingerprint_semantic_contract", { definition });
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
  return execute("compose_semantic_contract_set", { contracts });
}

function definition(name: "normative-semantics.json" | "architecture-interpretation.json"): SemanticContractVersion {
  return structuredClone(assets[`definitions/${name}`]) as SemanticContractVersion;
}

export function listSemanticContracts(): readonly SemanticContractVersion[] {
  return Object.freeze([
    definition("architecture-interpretation.json"),
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
  if (parts.length !== 3 || parts[1] !== "1.0") throw new Error(`Unsupported semantic resource: ${key}`);
  const name = `${parts[0]}-${parts[2]}.json`;
  const resource = assets[`resources/${name}`];
  if (!resource) throw new Error(`Missing bundled semantic resource: ${key}`);
  return structuredClone(resource);
}
