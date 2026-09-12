import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasmPath = resolve(root, "packages/node/src/generated/semantic-core.wasm");
const core = await WebAssembly.instantiate(await readFile(wasmPath));
const instance = ("instance" in core ? core.instance : core);
const exports = instance.exports;

function execute(request) {
  const payload = Buffer.from(JSON.stringify(request), "utf8");
  const input = exports.alloc(payload.length);
  new Uint8Array(exports.memory.buffer).set(payload, input);
  const output = exports.execute(input, payload.length);
  const length = exports.result_len();
  try {
    return JSON.parse(Buffer.from(new Uint8Array(exports.memory.buffer, output, length)).toString("utf8"));
  } finally {
    exports.dealloc(output, length);
    exports.dealloc(input, payload.length);
  }
}

const contractRoot = resolve(root, "contracts/semantic-contract/v1.0");
const definitionNames = ["architecture-interpretation.json", "normative-semantics.json", "normalized-model.json"];
const definitions = await Promise.all(definitionNames.map(async (name) =>
  JSON.parse(await readFile(resolve(contractRoot, "definitions", name), "utf8"))));

function resourceName(key) {
  const parts = key.split("/");
  const candidates = [`${key.replaceAll("/", "-")}.json`];
  if (parts.length === 3) candidates.push(`${parts[0]}-${parts[2]}.json`);
  return candidates;
}

for (const definition of definitions) {
  const verified = execute({
    core_contract_version: "1.0",
    operation: "fingerprint_semantic_contract",
    mode: "verify",
    definition,
  });
  if (!verified.success || verified.semantic_contract_fingerprint !== definition.semanticContractFingerprint) {
    throw new Error(`tracked WASM failed fingerprint verification for ${definition.semanticContractFamily}`);
  }
  const resources = [];
  for (const entry of definition.resourceManifest) {
    const names = resourceName(entry.canonicalResourceKey);
    let content;
    for (const name of names) {
      try { content = JSON.parse(await readFile(resolve(contractRoot, "resources", name), "utf8")); break; }
      catch (error) { if (error.code !== "ENOENT") throw error; }
    }
    if (content === undefined) throw new Error(`missing canonical resource for ${entry.canonicalResourceKey}`);
    resources.push({ canonicalResourceKey: entry.canonicalResourceKey, content });
  }
  const closure = execute({
    core_contract_version: "1.0",
    operation: "validate_semantic_resource_closure",
    definition,
    resources,
  });
  if (!closure.success || closure.closure_valid !== true) {
    throw new Error(`tracked WASM failed resource closure for ${definition.semanticContractFamily}`);
  }
}

const canonical = execute({
  core_contract_version: "1.0",
  operation: "canonicalize_semantic_json",
  value_json: '{"small":1e-6,"tiny":1e-7,"large":1e20,"huge":1e21,"zero":-0}',
});
if (!canonical.success || !canonical.canonical_preimage_json) throw new Error("tracked WASM failed JCS smoke test");

const set = execute({
  core_contract_version: "1.0",
  operation: "compose_semantic_contract_set",
  contracts: definitions.map(({ semanticContractFamily, semanticContractVersion, semanticContractFingerprint }) => ({
    semanticContractFamily,
    semanticContractVersion,
    semanticContractFingerprint,
  })),
});
if (!set.success || !/^scs:v1:sha256:[0-9a-f]{64}$/.test(set.semantic_contract_set_id ?? "")) {
  throw new Error("tracked WASM failed semantic-contract-set smoke test");
}
console.log(`tracked semantic-core WASM passed semantic-contract smoke (${set.semantic_contract_set_id})`);
