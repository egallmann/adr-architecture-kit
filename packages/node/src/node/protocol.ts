import AjvModule, { type ErrorObject } from "ajv/dist/2020.js";
import { semanticCoreContract } from "../generated/semantic-core-contract.js";
import { semanticCoreContractV11 } from "../generated/semantic-core-contract-v1.1.js";
import { semanticCoreContractV12 } from "../generated/semantic-core-contract-v1.2.js";
import { semanticCoreContractV13 } from "../generated/semantic-core-contract-v1.3.js";
import { semanticCoreContractV14 } from "../generated/semantic-core-contract-v1.4.js";
import { semanticCoreContractV15 } from "../generated/semantic-core-contract-v1.5.js";

type Validator = ((value: unknown) => boolean) & { errors?: ErrorObject[] | null };
interface AjvLike { compile(schema: unknown): Validator; }
const AjvConstructor = AjvModule as unknown as new (options: Record<string, unknown>) => AjvLike;
const ajv = new AjvConstructor({ allErrors: true, strict: false });

export const SEMANTIC_CORE_PROTOCOL_VERSIONS = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5"] as const;
export const SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS = [
  "validate_authoring",
  "construct_authoring_set",
] as const;
export const SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS = ["materialize_architecture"] as const;
export const SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS = ["qualify_authoring_construction_1_1"] as const;
export const SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS = ["prepare_authoring_construction_basis_1_1"] as const;

export function semanticCoreCapabilities(): {
  readonly supported_versions: readonly string[];
  readonly operations_by_version: Readonly<Record<string, readonly string[]>>;
} {
  return Object.freeze({
    supported_versions: SEMANTIC_CORE_PROTOCOL_VERSIONS,
    operations_by_version: Object.freeze({ "1.2": SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS, "1.3": SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS, "1.4": SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS, "1.5": SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS }),
  });
}

export function supportsSemanticCoreOperation(version: string, operation: string): boolean {
  return (version === "1.2" && (SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS as readonly string[]).includes(operation))
    || (version === "1.3" && (SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS as readonly string[]).includes(operation))
    || (version === "1.4" && (SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS as readonly string[]).includes(operation))
    || (version === "1.5" && (SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS as readonly string[]).includes(operation));
}

const validators = new Map<string, Validator>([
  ["1.0", ajv.compile(semanticCoreContract)],
  ["1.1", ajv.compile(semanticCoreContractV11)],
  ["1.2", ajv.compile(semanticCoreContractV12)],
  ["1.3", ajv.compile(semanticCoreContractV13)],
  ["1.4", ajv.compile(semanticCoreContractV14)],
  ["1.5", ajv.compile(semanticCoreContractV15)],
]);

/** Enforce the versioned request/result transport contract in the Node host. */
export function validateSemanticCoreProtocol(value: unknown): void {
  const version = typeof value === "object" && value !== null && "core_contract_version" in value
    ? String((value as Record<string, unknown>).core_contract_version)
    : "1.0";
  const validator = validators.get(version) ?? validators.get("1.0")!;
  if (validator(value)) return;
  const details = (validator.errors ?? []).slice(0, 3).map((error) => {
    const path = error.instancePath || "/";
    return `${path}: ${error.message ?? "protocol validation failed"}`;
  }).join("; ");
  throw new Error(`semantic-core protocol violation: ${details}`);
}
