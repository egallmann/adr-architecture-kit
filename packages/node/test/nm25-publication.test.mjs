import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import {
  getSemanticContract,
  listSemanticContracts,
  loadSemanticResource,
} from "../dist/node/semantic-contract.js";

test("NM 2.5 is exactly discoverable without runtime support or current selection", async () => {
  const definition = getSemanticContract("normalized-model", "2.5");
  assert.equal(definition.semanticContractFingerprint, "scf:v1:sha256:bb48720502668e434d378445004aec7783346a0e74254c9e0d3cb01a8798d9d7");
  assert.equal(definition.resourceManifest.length, 7);
  assert.deepEqual(
    definition.frozenNormativeConformanceResources,
    ["normalized-model/2.5/conformance"],
  );
  const keys = definition.resourceManifest.map((entry) => entry.canonicalResourceKey);
  assert.equal(new Set(keys).size, 7);
  for (const key of keys) {
    const loaded = loadSemanticResource(key);
    const filename = key.replaceAll("/", "-") + ".json";
    const bytes = await readFile(resolve("../../contracts/semantic-contract/v1.0/resources", filename), "utf8");
    assert.deepEqual(loaded, JSON.parse(bytes), key);
  }
  assert.equal(
    listSemanticContracts().find((item) => item.semanticContractFamily === "normalized-model").semanticContractVersion,
    "2.3",
  );
  assert.equal(getSemanticContract("normalized-model", "2.4").semanticContractVersion, "2.4");
  assert.throws(() => getSemanticContract("normalized-model", "2.6"), /Unsupported semantic contract/);
  assert.throws(() => loadSemanticResource("normalized-model/2.6/conformance"), /Unsupported semantic resource/);
  assert.throws(() => loadSemanticResource("normalized-model/2.5/schema/not-published"), /Missing bundled semantic resource/);
});
