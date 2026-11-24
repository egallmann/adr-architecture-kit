import { cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const canonicalSchemaTarget = resolve(packageRoot, "dist/schemas/canonical");
const semanticContractTarget = resolve(packageRoot, "dist/generated/semantic-contract");
await rm(canonicalSchemaTarget, { recursive: true, force: true });
await rm(semanticContractTarget, { recursive: true, force: true });
await mkdir(canonicalSchemaTarget, { recursive: true });
await cp(resolve(packageRoot, "src/generated/schemas"), resolve(packageRoot, "dist/schemas/canonical"), { recursive: true, force: true });
await cp(resolve(packageRoot, "src/generated/semantic-core.wasm"), resolve(packageRoot, "dist/generated/semantic-core.wasm"), { force: true });
await cp(resolve(packageRoot, "src/generated/semantic-contract"), semanticContractTarget, { recursive: true, force: true });
