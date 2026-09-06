import test from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { access, mkdtemp, readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { parse } from "yaml";
import { openRepository } from "../dist/node/index.js";
import { validateContract } from "../dist/validation/index.js";

const run = promisify(execFile);
const repositoryRoot = resolve("../..");
const generator = resolve(repositoryRoot, "tests/conformance/generate_python_repository.py");

async function pythonCommand() {
  const candidates = [
    process.env.ADR_KIT_PYTHON,
    resolve(repositoryRoot, ".venv/Scripts/python.exe"),
    resolve(repositoryRoot, ".venv/bin/python"),
    "python",
    "python3",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      if (candidate === "python" || candidate === "python3") return candidate;
    }
  }
  throw new Error("No Python interpreter available for cross-language conformance");
}

test("Python-generated v2.1 registry passes TypeScript validation and Node loading", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "adr-kit-python-v21-"));
  await run(await pythonCommand(), [generator, "1.4", root], { cwd: repositoryRoot });

  const registry = parse(await readFile(resolve(root, "adrs/index/entity-registry.yaml"), "utf8"));
  assert.equal(registry.schema_version, "2.1");
  assert.ok(registry.entities.length > 0);
  assert.ok(registry.entities.every((entity) => !("schema_version" in entity)));
  assert.equal(validateContract(registry, "normalized-entity-registry:2.1").valid, true);

  const repository = await openRepository(root);
  assert.equal(repository.modelVersion, "2.1");
  assert.equal(repository.entities().length, registry.entities.length);
});
