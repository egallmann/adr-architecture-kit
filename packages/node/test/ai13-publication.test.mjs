import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { getSemanticContract, listSemanticContracts, loadSemanticResource, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

test("AI 1.3 exact publication is available without selection or execution", async () => {
  const definition = getSemanticContract("architecture-interpretation", "1.3");
  assert.equal(definition.semanticContractFingerprint, "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167");
  assert.equal(definition.resourceManifest.length, 52);
  assert.deepEqual(definition.frozenNormativeConformanceResources, ["architecture-interpretation/1.3/conformance"]);
  const keys = definition.resourceManifest.map((entry) => entry.canonicalResourceKey);
  assert.equal(new Set(keys).size, 52);
  assert.equal(keys.filter((key) => key.startsWith("architecture-interpretation/1.3/")).length, 12);
  assert.equal((await verifySemanticContract(definition)).success, true);
  for (const key of keys) {
    let bytes;
    try {
      bytes = await readFile(resolve("../../contracts/semantic-contract/v1.0/resources", key.replaceAll("/", "-") + ".json"), "utf8");
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      const [family, , ...name] = key.split("/");
      bytes = await readFile(resolve(`../../contracts/semantic-contract/v1.0/resources/${family}-${name.join("-")}.json`), "utf8");
    }
    assert.deepEqual(loadSemanticResource(key), JSON.parse(bytes), key);
  }
  assert.equal((await validateSemanticResourceClosure(definition, keys.map((key) => ({ canonicalResourceKey: key, content: loadSemanticResource(key) })))).closure_valid, true);
  assert.equal(loadSemanticResource("architecture-interpretation/1.3/lifecycle-ownership").rows.length, 17);
  assert.equal(loadSemanticResource("architecture-interpretation/1.3/conformance").cases.length, 137);
  assert.equal(listSemanticContracts().some((item) => item.semanticContractVersion === "1.3"), false);
  assert.throws(() => getSemanticContract("architecture-interpretation", "1.4"), /Unsupported semantic contract/);
  assert.throws(() => getSemanticContract("authoring-construction", "1.3"), /Unsupported semantic contract/);
  assert.throws(() => loadSemanticResource("architecture-interpretation/1.4/rules"), /Unsupported semantic resource/);
  assert.throws(() => loadSemanticResource("architecture-interpretation/1.3/missing"), /Missing bundled semantic resource/);
});
