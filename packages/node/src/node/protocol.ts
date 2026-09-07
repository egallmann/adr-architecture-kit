import AjvModule, { type ErrorObject } from "ajv/dist/2020.js";
import { semanticCoreContract } from "../generated/semantic-core-contract.js";

type Validator = ((value: unknown) => boolean) & { errors?: ErrorObject[] | null };
interface AjvLike { compile(schema: unknown): Validator; }
const AjvConstructor = AjvModule as unknown as new (options: Record<string, unknown>) => AjvLike;
const validator = new AjvConstructor({ allErrors: true, strict: false }).compile(semanticCoreContract);

/** Enforce the versioned request/result transport contract in the Node host. */
export function validateSemanticCoreProtocol(value: unknown): void {
  if (validator(value)) return;
  const details = (validator.errors ?? []).slice(0, 3).map((error) => {
    const path = error.instancePath || "/";
    return `${path}: ${error.message ?? "protocol validation failed"}`;
  }).join("; ");
  throw new Error(`semantic-core protocol violation: ${details}`);
}
