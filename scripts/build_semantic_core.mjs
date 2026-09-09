import { cp, mkdir, readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const cargo = process.env.CARGO ?? "cargo";
const args = ["build", "--manifest-path", resolve(repoRoot, "core/Cargo.toml"), "--target", "wasm32-unknown-unknown", "--release"];

await new Promise((resolvePromise, reject) => {
  const child = spawn(cargo, args, { cwd: repoRoot, stdio: "inherit", shell: process.platform === "win32" });
  child.on("error", reject);
  child.on("exit", (code) => code === 0 ? resolvePromise() : reject(new Error(`cargo exited with ${code}`)));
});

const artifact = resolve(repoRoot, "core/target/wasm32-unknown-unknown/release/adr_kit_semantic_core.wasm");
const pythonTarget = resolve(repoRoot, "src/adr_kit/core/semantic-core.wasm");
const nodeTarget = resolve(repoRoot, "packages/node/src/generated/semantic-core.wasm");
const contractSource = resolve(repoRoot, "contracts/semantic-core/v1.0/contract.json");
const pythonContractTarget = resolve(repoRoot, "src/adr_kit/core/semantic-core-contract.json");
await mkdir(resolve(repoRoot, "src/adr_kit/core"), { recursive: true });
await mkdir(resolve(repoRoot, "packages/node/src/generated"), { recursive: true });
await cp(artifact, pythonTarget, { force: true });
await cp(artifact, nodeTarget, { force: true });
await cp(contractSource, pythonContractTarget, { force: true });
const semanticContractSource = resolve(repoRoot, "contracts/semantic-contract/v1.0");
const semanticContractTarget = resolve(repoRoot, "src/adr_kit/semantic_contract/v1_0");
await cp(resolve(semanticContractSource, "semantic-contract-version.schema.json"), resolve(semanticContractTarget, "semantic-contract-version.schema.json"), { force: true });
await cp(resolve(semanticContractSource, "resource-manifest-entry.schema.json"), resolve(semanticContractTarget, "resource-manifest-entry.schema.json"), { force: true });
await cp(resolve(semanticContractSource, "definitions"), semanticContractTarget, { recursive: true, force: true });
await cp(resolve(semanticContractSource, "resources"), resolve(semanticContractTarget, "resources"), { recursive: true, force: true });
const [pythonBytes, nodeBytes] = await Promise.all([readFile(pythonTarget), readFile(nodeTarget)]);
if (!pythonBytes.equals(nodeBytes)) {
  throw new Error("Python and Node semantic-core WASM artifacts are not byte-identical");
}
