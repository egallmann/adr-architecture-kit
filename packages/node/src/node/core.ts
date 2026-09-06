import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { ContractValidationError, RepositoryError } from "../errors.js";
import type { NormalizedEntityV21 } from "../model/types.js";
import { openRepository } from "./repository.js";
import { parse } from "yaml";
import { packageVersion } from "../generated/package-metadata.js";

const API_CONTRACT_VERSION = "1.0" as const;

export type ContractProfile = "greenfield" | "brownfield" | "migration";

export interface ContractValidationRequest {
  readonly project_root: string | URL;
  readonly profile?: ContractProfile;
  readonly max_sentinel_fields?: number;
  readonly max_non_complete_entities?: number;
}

export interface ContractValidationIssue { readonly path: string; readonly message: string; }
export interface ContractValidationDiagnostic { readonly severity: "error"; readonly code: string; readonly message: string; readonly path?: string; }
export interface ContractValidationResult {
  readonly success: boolean;
  readonly profile: ContractProfile;
  readonly outcome: "compliant" | "sentinel_compliant" | "non_compliant" | "invalid_request";
  readonly sentinel_field_count: number;
  readonly non_complete_entity_count: number;
  readonly completeness_counts: Readonly<Record<string, number>>;
  readonly issues: readonly ContractValidationIssue[];
  readonly diagnostics: readonly ContractValidationDiagnostic[];
  readonly package_version: string;
  readonly api_contract_version: typeof API_CONTRACT_VERSION;
}

export interface ProjectMetadataValidationRequest { readonly project_root: string | URL; }
export interface ProjectMetadataValidationDiagnostic { readonly severity: "error" | "warning" | "info"; readonly code: string; readonly message: string; readonly path?: string; readonly source_ref?: string; }
export interface ProjectMetadataValidationResult {
  readonly success: boolean;
  readonly diagnostics: readonly ProjectMetadataValidationDiagnostic[];
  readonly package_version: string;
  readonly api_contract_version: typeof API_CONTRACT_VERSION;
}
export interface ArchitectureReferenceValidationRequest {
  readonly records: readonly Record<string, unknown>[];
  readonly reviews?: readonly Record<string, unknown>[];
  readonly overrides?: readonly Record<string, unknown>[];
}
export interface ArchitectureReferenceValidationResult {
  readonly success: boolean;
  readonly error_count: number;
  readonly warning_count: number;
  readonly diagnostics: readonly ProjectMetadataValidationDiagnostic[];
}
export interface ArchitectureValidationRequest {
  readonly records: readonly Record<string, unknown>[];
  readonly mode?: "complete" | "structural";
}
export interface ArchitectureValidationResult {
  readonly success: boolean;
  readonly error_count: number;
  readonly warning_count: number;
  readonly diagnostics: readonly ProjectMetadataValidationDiagnostic[];
}
export interface ProviderBinding { readonly workspace_key: string; readonly architecture_namespace: string; readonly project_root: string; readonly repository: Awaited<ReturnType<typeof openRepository>>; }
export interface ProviderRegistry { readonly bindings: readonly ProviderBinding[]; getRepository(workspaceKey: string): ProviderBinding["repository"]; getRepositoryByNamespace(namespace: string): ProviderBinding["repository"]; }

interface CoreExports {
  readonly memory: WebAssembly.Memory;
  readonly alloc: (size: number) => number;
  readonly execute: (pointer: number, size: number) => number;
  readonly result_len: () => number;
  readonly dealloc: (pointer: number, size: number) => void;
}

let coreBytes: Promise<Buffer> | undefined;
function loadCoreBytes(): Promise<Buffer> {
  coreBytes ??= readFile(new URL("../generated/semantic-core.wasm", import.meta.url));
  return coreBytes;
}

export async function executeSemanticCoreRequest(request: Record<string, unknown>): Promise<Record<string, unknown>> {
  const instantiated = await WebAssembly.instantiate(await loadCoreBytes());
  const instance = ("instance" in instantiated ? instantiated.instance : instantiated) as WebAssembly.Instance;
  const exports = instance.exports as unknown as CoreExports;
  const payload = Buffer.from(JSON.stringify(request), "utf8");
  const input = exports.alloc(payload.length);
  new Uint8Array(exports.memory.buffer).set(payload, input);
  const output = exports.execute(input, payload.length);
  const outputLength = exports.result_len();
  try {
    const bytes = new Uint8Array(exports.memory.buffer, output, outputLength);
    const decoded = JSON.parse(Buffer.from(bytes).toString("utf8")) as unknown;
    return decoded as Record<string, unknown>;
  } catch (error) {
    throw new ContractValidationError(`Semantic core returned malformed output: ${String(error)}`);
  } finally {
    exports.dealloc(output, outputLength);
    exports.dealloc(input, payload.length);
  }
}

export async function validateContract(request: ContractValidationRequest): Promise<ContractValidationResult> {
  const profile = request.profile ?? "greenfield";
  if (!(["greenfield", "brownfield", "migration"] as const).includes(profile)) {
    throw new ContractValidationError(`Unsupported contract validation profile: ${String(profile)}`);
  }
  for (const [name, value] of [["max_sentinel_fields", request.max_sentinel_fields], ["max_non_complete_entities", request.max_non_complete_entities]] as const) {
    if (value !== undefined && (!Number.isInteger(value) || value < 0)) throw new ContractValidationError(`${name} must be a non-negative integer`);
  }
  const repository = await openRepository(request.project_root);
  const remediationLedger = await readOptionalYaml(
    resolve(repository.projectRoot, "adrs/governance/remediation-ledger.yaml"),
  );
  const coreRequest: Record<string, unknown> = {
    core_contract_version: "1.0",
    operation: "validate_contract",
    profile,
    entity_registry: { schema_version: "2.1", type: "normalized_entity_registry", entities: repository.entities() as readonly NormalizedEntityV21[] },
    remediation_ledger: remediationLedger,
  };
  if (request.max_sentinel_fields !== undefined) coreRequest.max_sentinel_fields = request.max_sentinel_fields;
  if (request.max_non_complete_entities !== undefined) coreRequest.max_non_complete_entities = request.max_non_complete_entities;
  const result = await executeSemanticCoreRequest(coreRequest);
  return Object.freeze({
    ...result,
    package_version: packageVersion,
    api_contract_version: API_CONTRACT_VERSION,
  }) as ContractValidationResult;
}

async function readOptionalYaml(path: string): Promise<unknown | null> {
  try {
    return parse(await readFile(path, "utf8"));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw new ContractValidationError(`Could not load ${path}: ${String(error)}`);
  }
}

export async function validateProjectMetadata(request: ProjectMetadataValidationRequest): Promise<ProjectMetadataValidationResult> {
  const root = String(request.project_root);
  let metadata: unknown;
  try {
    const projectPath = request.project_root instanceof URL
      ? new URL("PROJECT.yaml", request.project_root)
      : resolve(root, "PROJECT.yaml");
    metadata = parse(await readFile(projectPath, "utf8"));
  } catch (error) {
    return {
      success: false,
      diagnostics: [{ severity: "error", code: "project_metadata.parse_error", message: String(error), path: "PROJECT.yaml" }],
      package_version: packageVersion,
      api_contract_version: API_CONTRACT_VERSION,
    };
  }
  const result = await executeSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "validate_project_metadata",
    project_metadata: metadata
  });
  return Object.freeze({
    ...result,
    package_version: packageVersion,
    api_contract_version: API_CONTRACT_VERSION,
  }) as ProjectMetadataValidationResult;
}

export async function validateArchitectureReferences(
  request: ArchitectureReferenceValidationRequest,
): Promise<ArchitectureReferenceValidationResult> {
  return executeSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "validate_architecture_references",
    records: request.records,
    reviews: request.reviews ?? [],
    overrides: request.overrides ?? [],
  }) as unknown as Promise<ArchitectureReferenceValidationResult>;
}

/** Internal host seam for normalized ADR facts; not a public capability until
 * Node also owns the equivalent schema-aware source adapter. */
export async function validateArchitectureFacts(
  request: ArchitectureValidationRequest,
): Promise<ArchitectureValidationResult> {
  return executeSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "validate_architecture",
    mode: request.mode ?? "complete",
    records: request.records,
  }) as unknown as Promise<ArchitectureValidationResult>;
}

export async function openProviderRegistry(workspaceRoots: Readonly<Record<string, string | URL>>): Promise<ProviderRegistry> {
  const keys = Object.keys(workspaceRoots).sort();
  if (keys.length === 0) throw new RepositoryError("provider_registry.invalid", "workspace_roots must be a non-empty mapping");
  const bindings: ProviderBinding[] = [];
  for (const workspace_key of keys) {
    if (!workspace_key) throw new RepositoryError("provider_registry.invalid", "workspace routing keys must be non-empty strings");
    const root = workspaceRoots[workspace_key];
    if (root === undefined) throw new RepositoryError("provider_registry.invalid", `Missing workspace root: ${workspace_key}`);
    const repository = await openRepository(root);
    bindings.push({ workspace_key, architecture_namespace: repository.architectureNamespace, project_root: repository.projectRoot, repository });
  }
  const core = await executeSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "open_provider_registry",
    bindings: bindings.map(({ workspace_key, architecture_namespace, project_root }) => ({ workspace_key, architecture_namespace, project_root }))
  });
  if (!core.success) {
    const message = Array.isArray(core.diagnostics)
      ? core.diagnostics.map((item) => String((item as Record<string, unknown>).message ?? "provider registry validation failed")).join("; ")
      : "provider registry validation failed";
    throw new RepositoryError("provider_registry.invalid", message);
  }
  const byKey = new Map(bindings.map((binding) => [binding.workspace_key, binding]));
  const byNamespace = new Map(bindings.map((binding) => [binding.architecture_namespace, binding]));
  return Object.freeze({
    bindings: Object.freeze(bindings),
    getRepository(workspaceKey: string) {
      const binding = byKey.get(workspaceKey);
      if (!binding) throw new RepositoryError("provider_registry.unknown_workspace", `Unknown workspace routing key: ${workspaceKey}`);
      return binding.repository;
    },
    getRepositoryByNamespace(namespace: string) {
      const binding = byNamespace.get(namespace);
      if (!binding) throw new RepositoryError("provider_registry.unknown_namespace", `Unknown architecture_namespace: ${namespace}`);
      return binding.repository;
    }
  });
}
