import { readFile, readdir } from "node:fs/promises";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";
import {
  validateAuthoringDocument,
  type AuthoringAdrType,
  type AuthoringValidationMode,
} from "../validation/index.js";
import {
  validateArchitectureFacts,
  validateArchitectureReferences,
} from "./core.js";
import { packageVersion } from "../generated/package-metadata.js";

const API_CONTRACT_VERSION = "1.0" as const;
const ADR_DIRECTORIES = ["logical", "physical", "physical-system", "physical-component"] as const;

export interface ArchitectureValidationRequest {
  readonly project_root: string | URL;
  readonly mode?: AuthoringValidationMode;
  readonly cross_references?: boolean;
}

export interface ArchitectureDiagnostic {
  readonly severity: "error" | "warning" | "info";
  readonly code: string;
  readonly message: string;
  readonly path?: string;
  readonly field?: string;
}

export interface ArchitectureValidationResult {
  readonly success: boolean;
  readonly validated_files: readonly string[];
  readonly diagnostics: readonly ArchitectureDiagnostic[];
  readonly error_count: number;
  readonly warning_count: number;
  readonly package_version: string;
  readonly api_contract_version: typeof API_CONTRACT_VERSION;
}

type Document = Record<string, unknown>;

function projectRoot(value: string | URL): string {
  return resolve(value instanceof URL ? fileURLToPath(value) : value);
}

function displayPath(root: string, path: string): string {
  return relative(root, path).replaceAll("\\", "/");
}

function diagnostic(
  severity: ArchitectureDiagnostic["severity"],
  code: string,
  message: string,
  path?: string,
  field?: string,
): ArchitectureDiagnostic {
  return { severity, code, message, ...(path ? { path } : {}), ...(field ? { field } : {}) };
}

function listStrings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((item): item is string => typeof item === "string"))].sort();
}

function adrType(value: unknown): AuthoringAdrType | undefined {
  return value === "logical" || value === "physical" || value === "physical-system" || value === "physical-component"
    ? value
    : undefined;
}

async function sourceFiles(root: string): Promise<string[]> {
  const files: string[] = [];
  for (const directory of ADR_DIRECTORIES) {
    const path = resolve(root, "adrs", directory);
    let entries;
    try {
      entries = await readdir(path, { withFileTypes: true });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") continue;
      throw error;
    }
    for (const entry of entries) {
      if (entry.isFile() && entry.name.endsWith(".yaml")) files.push(resolve(path, entry.name));
    }
  }
  return files.sort();
}

async function exists(root: string, identifier: string): Promise<boolean> {
  try {
    await readdir(resolve(root, identifier));
    return true;
  } catch {
    try {
      await readFile(resolve(root, identifier));
      return true;
    } catch {
      return false;
    }
  }
}

function referenceRecord(document: Document): Document | undefined {
  const id = document.id;
  const kind = document.adr_type;
  if (typeof id !== "string" || typeof kind !== "string") return undefined;
  const governance = document.governance && typeof document.governance === "object"
    ? document.governance as Document
    : {};
  const record: Document = {
    id,
    kind,
    schema_version: String(document.schema_version ?? ""),
    implements_logical: listStrings(document.implements_logical),
    implements_system: listStrings(document.implements_system),
    references_components: listStrings(document.references_components),
    related_adrs: listStrings(document.related_adrs),
    related_reviews: listStrings(governance.related_reviews),
    related_overrides: listStrings(governance.related_overrides),
  };
  if (kind === "physical-system" && document.system && typeof document.system === "object") {
    const system = document.system as Document;
    if (typeof system.id === "string") record.system_id = system.id;
    if (Array.isArray(document.component_topology)) {
      record.topology_components = document.component_topology
        .filter((item): item is Document => Boolean(item && typeof item === "object"))
        .map((item) => item.component_ref)
        .filter((item): item is string => typeof item === "string")
        .sort();
    }
  }
  if (kind === "physical-component" && Array.isArray(document.component_specifications)) {
    record.component_specifications = document.component_specifications.filter(
      (item): item is Document => Boolean(item && typeof item === "object"),
    );
  }
  return record;
}

async function governanceArtifacts(root: string, directory: string, target: string): Promise<Document[]> {
  const path = resolve(root, "adrs", "decisions", directory);
  let entries;
  try {
    entries = await readdir(path, { withFileTypes: true });
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  }
  const result: Document[] = [];
  for (const entry of entries.filter((item) => item.isFile() && item.name.endsWith(".yaml")).sort((a, b) => a.name.localeCompare(b.name))) {
    const payload = parse(await readFile(resolve(path, entry.name), "utf8"));
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      const item = payload as Document;
      if (typeof item.id === "string" && typeof item[target] === "string") {
        result.push({ id: item.id, [target]: item[target], related_adr_version: item.related_adr_version });
      }
    }
  }
  return result;
}

export async function validateArchitecture(
  request: ArchitectureValidationRequest,
): Promise<ArchitectureValidationResult> {
  const root = projectRoot(request.project_root);
  const mode = request.mode ?? "complete";
  const files = await sourceFiles(root);
  const diagnostics: ArchitectureDiagnostic[] = [];
  const records: Document[] = [];
  const referenceRecords: Document[] = [];
  let referenceNormalizationFailed = false;

  for (const path of files) {
    const display = displayPath(root, path);
    let document: Document;
    try {
      const parsed = parse(await readFile(path, "utf8"));
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("expected YAML object");
      document = parsed as Document;
    } catch (error) {
      diagnostics.push(diagnostic("error", "parse_error", String(error), display));
      referenceNormalizationFailed = true;
      continue;
    }
    if (typeof document.id !== "string" || typeof document.adr_type !== "string") {
      // The reference protocol requires identity even when the authoring
      // validator will report a separate schema diagnostic for this source.
      referenceNormalizationFailed = true;
    } else {
      const reference = referenceRecord(document);
      if (reference) referenceRecords.push(reference);
    }
    const kind = adrType(document.adr_type);
    if (!kind) {
      diagnostics.push(diagnostic("error", "schema_validation", "adr_type must identify a supported ADR kind", display));
      continue;
    }
    const schemaVersion = typeof document.schema_version === "string" || typeof document.schema_version === "number"
      ? document.schema_version
      : undefined;
    const schema = validateAuthoringDocument(document, kind, schemaVersion, mode);
    if (!schema.valid) {
      diagnostics.push(...schema.diagnostics.map((item) => diagnostic(item.severity, item.code, item.message, display, item.path)));
      continue;
    }
    const normalized: Document = { ...document, missing_implementation_identifiers: [] };
    const missing: string[] = [];
    const specifications = Array.isArray(document.component_specifications) ? document.component_specifications : [];
    for (const specification of specifications) {
      if (!specification || typeof specification !== "object") continue;
      const identifiers = (specification as Document).implementation_identifiers;
      if (!Array.isArray(identifiers)) continue;
      for (const identifier of identifiers) {
        if (typeof identifier !== "string" || (!identifier.includes("/") && !identifier.includes("\\"))) continue;
        if (!(await exists(root, identifier))) missing.push(identifier);
      }
    }
    normalized.missing_implementation_identifiers = [...new Set(missing)].sort();
    records.push({ path: display, document: normalized });
  }

  if (records.length > 0) {
    const core = await validateArchitectureFacts({ records, mode });
    for (const item of core.diagnostics) {
      diagnostics.push(diagnostic(item.severity, item.code, item.message, item.source_ref, item.path));
    }
  }
  if (request.cross_references) {
    if (referenceNormalizationFailed) {
      // Host normalization is a prerequisite for the shared reference
      // evaluator. Do not infer partial references or fall back to a host
      // implementation when any source cannot be normalized.
      diagnostics.push(diagnostic("error", "parse_error", "Cross-reference source normalization failed"));
    } else {
      try {
        const reviews = await governanceArtifacts(root, "reviews", "target_adr");
        const overrides = await governanceArtifacts(root, "overrides", "related_adr");
        const core = await validateArchitectureReferences({ records: referenceRecords, reviews, overrides });
        for (const item of core.diagnostics) {
          diagnostics.push(diagnostic(item.severity, item.code, item.message, item.path));
        }
      } catch (error) {
        // Discovery/YAML failures stay host-owned diagnostics; the old host
        // evaluator is never used as a semantic fallback.
        diagnostics.push(diagnostic("error", "parse_error", `Cross-reference source normalization failed: ${String(error)}`));
      }
    }
  }
  diagnostics.sort((left, right) => `${left.path ?? ""}\u0000${left.field ?? ""}\u0000${left.code}`.localeCompare(`${right.path ?? ""}\u0000${right.field ?? ""}\u0000${right.code}`));
  const errorCount = diagnostics.filter((item) => item.severity === "error").length;
  const warningCount = diagnostics.filter((item) => item.severity === "warning").length;
  return Object.freeze({
    success: errorCount === 0,
    validated_files: Object.freeze(files.map((path) => displayPath(root, path))),
    diagnostics: Object.freeze(diagnostics),
    error_count: errorCount,
    warning_count: warningCount,
    package_version: packageVersion,
    api_contract_version: API_CONTRACT_VERSION,
  });
}
