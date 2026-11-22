import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { getSemanticContract, loadSemanticResource } from "../dist/node/semantic-contract.js";

const repositoryRoot = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const lifecycle = JSON.parse(
  await readFile(
    resolve(repositoryRoot, "adrs/migrations/semantic-contract-lifecycle-classification.json"),
    "utf8",
  ),
);

test("installed Node authority loaders expose released definitions and fail closed for candidates", async () => {
  for (const entry of lifecycle.released_contracts) {
    assert.equal(getSemanticContract(entry.family, entry.version).semanticContractFingerprint, entry.scf);
  }
  const released = new Set(
    lifecycle.released_contracts.map((entry) => `${entry.family}/${entry.version}`),
  );
  const definitionsDirectory = resolve(repositoryRoot, "contracts/semantic-contract/v1.0/definitions");
  for (const filename of await readdir(definitionsDirectory)) {
    if (!filename.endsWith(".json")) continue;
    const source = JSON.parse(await readFile(resolve(definitionsDirectory, filename), "utf8"));
    const identity = `${source.semanticContractFamily}/${source.semanticContractVersion}`;
    if (released.has(identity)) continue;
    assert.throws(
      () => getSemanticContract(source.semanticContractFamily, source.semanticContractVersion),
      /Unsupported semantic contract/,
    );
    assert.throws(
      () => loadSemanticResource(`${identity}/contract`),
    );
  }
});
