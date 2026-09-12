import AjvModule, { type ErrorObject } from "ajv/dist/2020.js";
import { semanticCoreContract } from "../generated/semantic-core-contract.js";
import { semanticCoreContractV11 } from "../generated/semantic-core-contract-v1.1.js";

type Validator = ((value: unknown) => boolean) & { errors?: ErrorObject[] | null };
interface AjvLike { compile(schema: unknown): Validator; }
const AjvConstructor = AjvModule as unknown as new (options: Record<string, unknown>) => AjvLike;
const ajv = new AjvConstructor({ allErrors: true, strict: false });
const validators = new Map<string, Validator>([
  ["1.0", ajv.compile(semanticCoreContract)],
  ["1.1", ajv.compile(semanticCoreContractV11)],
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
