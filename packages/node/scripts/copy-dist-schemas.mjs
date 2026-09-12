import { cp, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
await mkdir(resolve(packageRoot, "dist/schemas/canonical"), { recursive: true });
await cp(resolve(packageRoot, "src/generated/schemas"), resolve(packageRoot, "dist/schemas/canonical"), { recursive: true, force: true });
await cp(resolve(packageRoot, "src/generated/semantic-core.wasm"), resolve(packageRoot, "dist/generated/semantic-core.wasm"), { force: true });
await cp(resolve(packageRoot, "src/generated/semantic-contract"), resolve(packageRoot, "dist/generated/semantic-contract"), { recursive: true, force: true });
