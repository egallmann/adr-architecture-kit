import AjvModule, { type ErrorObject, type ValidateFunction } from "ajv";
import addFormats from "ajv-formats";
import { ContractValidationError, UnsupportedContractVersionError, type AdrKitDiagnostic } from "../errors.js";
import { canonicalSchemas } from "../schemas/index.js";

export type SupportedCapability = "normalized-model:2.1" | "evidence-attribution:1.5" | "evidence-attribution:1.6" | "architecture-discovery:1.1" | "manifest:1.0" | "normalized-entity-registry:2.1" | "relationship-registry:2.1" | "unresolved-registry:2.1";
export interface ValidationResult { readonly valid: boolean; readonly diagnostics: readonly AdrKitDiagnostic[]; }

interface AjvInstance {
  getSchema(id: string): ValidateFunction | undefined;
  addSchema(schema: unknown, id?: string): void;
}
const AjvConstructor = AjvModule as unknown as new (options: Record<string, unknown>) => AjvInstance;
const ajv = new AjvConstructor({ allErrors: true, strict: false, validateFormats: true });
(addFormats as unknown as (instance: object) => void)(ajv);
for (const schema of Object.values(canonicalSchemas)) {
  const id = (schema as { $id?: string }).$id;
  if (id && !ajv.getSchema(id)) ajv.addSchema(schema, id);
}

const schemaFor: Record<SupportedCapability, string> = {
  "normalized-model:2.1": "https://adr-kit.ste.systems/schema/normalized-model/v2.1/normalized-architecture-model.schema.json",
  "evidence-attribution:1.5": "https://adr-kit.ste.systems/schema/v1.5/implementation-attribution-evidence.schema.json",
  "evidence-attribution:1.6": "https://adr-kit.ste.systems/schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json",
  "architecture-discovery:1.1": "https://adr-kit.ste.systems/schema/v1.1/architecture-index.schema.json",
  "manifest:1.0": "https://adr-kit.ste.systems/schema/v1.0/manifest.schema.json",
  "normalized-entity-registry:2.1": "https://adr-kit.ste.systems/schema/normalized-model/v2.1/normalized-entity-registry.schema.json",
  "relationship-registry:2.1": "https://adr-kit.ste.systems/schema/normalized-model/v2.1/relationship-registry.schema.json",
  "unresolved-registry:2.1": "https://adr-kit.ste.systems/schema/normalized-model/v2.1/unresolved-registry.schema.json"
};

function validator(capability: SupportedCapability): ValidateFunction {
  const value = ajv.getSchema(schemaFor[capability]);
  if (!value) throw new Error(`Canonical schema is not packaged: ${capability}`);
  return value;
}

export function validateContract(input: unknown, capability: string): ValidationResult {
  if (!(capability in schemaFor)) throw new UnsupportedContractVersionError(capability);
  const check = validator(capability as SupportedCapability);
  const valid = Boolean(check(input));
  return Object.freeze({ valid, diagnostics: Object.freeze(valid ? [] : (check.errors ?? []).map(diagnostic)) });
}

export function assertValidContract(input: unknown, capability: string): void {
  const result = validateContract(input, capability);
  if (!result.valid) throw new ContractValidationError(`Invalid ${capability} contract`, result.diagnostics);
}

function diagnostic(error: ErrorObject): AdrKitDiagnostic {
  const path = error.instancePath;
  return path
    ? { code: `contract.${error.keyword}`, message: error.message ?? "contract validation failed", severity: "error", path }
    : { code: `contract.${error.keyword}`, message: error.message ?? "contract validation failed", severity: "error" };
}
