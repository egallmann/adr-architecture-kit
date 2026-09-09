import { createHash } from "node:crypto";
import { access, readFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { parse } from "yaml";
import { fileURLToPath } from "node:url";
import { createArchitectureModel, type ArchitectureModelView } from "../model/index.js";
import type { NormalizedArchitectureModel, NormalizedEntity, Relationship, RelationshipQuery } from "../model/types.js";
import { RepositoryError, RepositoryPathError } from "../internal.js";
import { assertValidContract } from "../validation/index.js";

const REQUIRED_INDEX_FIELDS = ["entity_registry_path", "relationship_registry_path", "unresolved_registry_path"] as const;
const OPTIONAL_INDEX_FIELDS: Record<string, string> = {
  decision_registry_path: "decisions",
  capability_registry_path: "capabilities",
  invariant_registry_path: "invariants",
  component_registry_path: "components",
  system_registry_path: "systems"
};

export interface RepositoryOptions { readonly project_root: string; }

export interface ArchitectureRepository extends ArchitectureModelView {
  readonly projectRoot: string;
  readonly project_root: string;
  readonly modelVersion: SupportedNormalizedModelVersion;
  readonly architectureNamespace: string;
  readonly architectureIndex: Readonly<Record<string, unknown>>;
  readonly manifest: Readonly<Record<string, unknown>>;
  readonly fingerprint: string;
  readonly subsets: Readonly<Record<string, readonly NormalizedEntity[]>>;
}

export type SupportedNormalizedModelVersion = "2.1" | "2.2" | "2.3";

export async function openRepository(projectRoot: string | URL): Promise<ArchitectureRepository> {
  const root = resolve(projectRoot instanceof URL ? fileURLToPath(projectRoot) : projectRoot);
  await requireFile(root, "PROJECT.yaml", "repository.orientation");
  await requireDirectory(root, "adrs", "repository.orientation");
  const indexPath = resolve(root, "adrs", "index", "architecture-index.yaml");
  const manifestPath = resolve(root, "adrs", "manifest.yaml");
  const architectureIndex = await loadYaml(indexPath, "repository.discovery");
  const manifest = await loadYaml(manifestPath, "repository.discovery");
  try { assertValidContract(architectureIndex, "architecture-discovery:1.1"); } catch (error) { throw repositoryFailure(error); }
  try { assertValidContract(manifest, "manifest:1.0"); } catch (error) { throw repositoryFailure(error); }

  for (const field of REQUIRED_INDEX_FIELDS) {
    if (typeof architectureIndex[field] !== "string") throw new RepositoryError("repository.missing_artifact", `Architecture index missing ${field}`);
  }
  const required = await Promise.all(REQUIRED_INDEX_FIELDS.map(async (field) => {
    const path = safeIndexPath(root, architectureIndex[field] as string);
    return [field, await loadYaml(path, `repository.${field}`)] as const;
  }));
  const documents = Object.fromEntries(required);
  const entityRegistry = documents.entity_registry_path as { schema_version?: unknown; entities: NormalizedEntity[] };
  const modelVersion = normalizedModelVersion(entityRegistry.schema_version);
  try {
    assertRegistryVersion(documents.relationship_registry_path, modelVersion, "relationship registry");
    assertRegistryVersion(documents.unresolved_registry_path, modelVersion, "unresolved registry");
    assertValidContract(documents.entity_registry_path, capability("normalized-entity-registry", modelVersion));
    assertValidContract(documents.relationship_registry_path, capability("relationship-registry", modelVersion));
    assertValidContract(documents.unresolved_registry_path, capability("unresolved-registry", modelVersion));
  } catch (error) { throw repositoryFailure(error); }

  const subsets: Record<string, readonly NormalizedEntity[]> = {};
  for (const [field, name] of Object.entries(OPTIONAL_INDEX_FIELDS)) {
    const reference = architectureIndex[field];
    if (typeof reference !== "string") continue;
    const path = safeIndexPath(root, reference);
    if (!(await exists(path))) continue;
    const subset = await loadYaml(path, `repository.${name}`);
    try {
      assertRegistryVersion(subset, modelVersion, `${name} registry`);
      assertValidContract(subset, capability("normalized-entity-registry", modelVersion));
    } catch (error) { throw repositoryFailure(error); }
    subsets[name] = Object.freeze([...(subset.entities as NormalizedEntity[])]);
  }

  const relationshipRegistry = documents.relationship_registry_path as { relationships: Relationship[] };
  const unresolvedRegistry = documents.unresolved_registry_path as { unresolved: Record<string, unknown>[] };
  const model = {
    schema_version: modelVersion,
    type: "normalized_architecture_model" as const,
    mode: "normalized" as const,
    scope_root: root,
    architecture_namespace: String(architectureIndex.architecture_namespace),
    fingerprint: bindingFingerprint({ architectureIndex, entityRegistry, relationshipRegistry, unresolvedRegistry, subsets }),
    entities: entityRegistry.entities,
    relationships: relationshipRegistry.relationships,
    unresolved: unresolvedRegistry.unresolved,
    ...(architectureIndex.validation_summary !== undefined ? { validation_summary: architectureIndex.validation_summary } : {}),
    ...(architectureIndex.source_coverage !== undefined ? { source_coverage: architectureIndex.source_coverage } : {})
  } as NormalizedArchitectureModel;
  try { assertValidContract(model, capability("normalized-model", modelVersion)); } catch (error) { throw repositoryFailure(error); }
  const { executeValidatedSemanticCoreRequest } = await import("./core.js");
  const semantic = await executeValidatedSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "open_repository",
    model_version: modelVersion,
    architecture_namespace: model.architecture_namespace,
    entities: model.entities,
  });
  if (!semantic.success) {
    const message = Array.isArray(semantic.diagnostics)
      ? semantic.diagnostics
          .map((item) => String((item as Record<string, unknown>).message ?? "repository identity validation failed"))
          .join("; ")
      : "repository identity validation failed";
    throw new RepositoryError("repository.contract", message);
  }
  const view = createArchitectureModel(model);
  return Object.freeze({
    ...view,
    projectRoot: root,
    project_root: root,
    modelVersion,
    architectureNamespace: String(architectureIndex.architecture_namespace),
    architectureIndex: deepFreeze(architectureIndex),
    manifest: deepFreeze(manifest),
    fingerprint: model.fingerprint,
    subsets: deepFreeze(subsets)
  });
}

async function loadYaml(path: string, code: string): Promise<Record<string, any>> {
  try {
    const value = parse(await readFile(path, "utf8"));
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("expected an object");
    return value as Record<string, any>;
  } catch (error) { throw new RepositoryError(code, `Could not load ${path}: ${String(error)}`); }
}

function safeIndexPath(root: string, reference: string): string {
  if (isAbsolute(reference)) throw new RepositoryPathError(`Index reference must be relative: ${reference}`);
  const candidate = resolve(root, reference);
  const escaped = relative(root, candidate) === ".." || relative(root, candidate).startsWith(`..${sep}`) || isAbsolute(relative(root, candidate));
  if (escaped) throw new RepositoryPathError(`Index reference escapes project root: ${reference}`);
  return candidate;
}

async function requireFile(root: string, name: string, code: string): Promise<void> {
  const path = resolve(root, name);
  if (!(await exists(path))) throw new RepositoryError(code, `Required repository file is missing: ${name}`);
}
async function requireDirectory(root: string, name: string, code: string): Promise<void> {
  const path = resolve(root, name);
  try { await access(path); } catch { throw new RepositoryError(code, `Required repository directory is missing: ${name}`); }
}
async function exists(path: string): Promise<boolean> { try { await access(path); return true; } catch { return false; } }
function bindingFingerprint(value: unknown): string { return `sha256:${createHash("sha256").update(stableJson(value)).digest("hex")}`; }
function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(",")}}`;
  return JSON.stringify(value);
}
function deepFreeze<T>(value: T): T { if (value && typeof value === "object" && !Object.isFrozen(value)) { Object.freeze(value); for (const item of Object.values(value as Record<string, unknown>)) deepFreeze(item); } return value; }
function repositoryFailure(error: unknown): RepositoryError { return error instanceof RepositoryError ? error : new RepositoryError("repository.contract", error instanceof Error ? error.message : String(error)); }

function normalizedModelVersion(value: unknown): SupportedNormalizedModelVersion {
  if (value === "2.1" || value === "2.2" || value === "2.3") return value;
  throw new RepositoryError("contract.unsupported_version", `Normalized model ${String(value)} is not supported`);
}

function capability(family: "normalized-model" | "normalized-entity-registry" | "relationship-registry" | "unresolved-registry", version: SupportedNormalizedModelVersion): `${typeof family}:${SupportedNormalizedModelVersion}` {
  return `${family}:${version}`;
}

function assertRegistryVersion(value: unknown, expected: SupportedNormalizedModelVersion, label: string): void {
  const actual = (value as { schema_version?: unknown } | null)?.schema_version;
  if (actual !== expected) throw new RepositoryError("contract.version_mismatch", `${label} schema version ${String(actual)} does not match normalized model ${expected}`);
}
