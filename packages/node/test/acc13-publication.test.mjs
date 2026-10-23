import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { getSemanticContract, loadSemanticResource, listSemanticContracts, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

test("ACC 1.3 is an exact immutable publication without runtime construction selection", async () => {
  const d = getSemanticContract("authoring-construction", "1.3");
  assert.equal(d.semanticContractFingerprint, "scf:v1:sha256:e809df8b4c13da7db8afd5513af31329222b488fcbd1590d1a25246aaf64f96a");
  assert.equal(d.resourceManifest.length, 94);
  assert.deepEqual(d.frozenNormativeConformanceResources, ["authoring-construction/1.3/conformance"]);
  assert.equal((await verifySemanticContract(d)).success, true);
  const bundle = [];
  for (const e of d.resourceManifest) {
    const key = e.canonicalResourceKey;
    let bytes;
    try {
      bytes = await readFile(resolve("../../contracts/semantic-contract/v1.0/resources", key.replaceAll("/", "-") + ".json"), "utf8");
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      const [family, , ...name] = key.split("/");
      bytes = await readFile(resolve("../../contracts/semantic-contract/v1.0/resources", family + "-" + name.join("-") + ".json"), "utf8");
    }
    const content = loadSemanticResource(key);
    assert.deepEqual(content, JSON.parse(bytes), key);
    bundle.push({ canonicalResourceKey: key, content });
  }
  assert.equal((await validateSemanticResourceClosure(d, bundle)).closure_valid, true);
  assert.equal(loadSemanticResource("authoring-construction/1.3/composition-bindings").rows.length, 1);
  assert.equal(loadSemanticResource("authoring-construction/1.3/conformance").cases.length, 159);
  assert.deepEqual(loadSemanticResource("architecture-interpretation/1.3/contract"), getSemanticContract("architecture-interpretation", "1.3"));
  assert.equal(listSemanticContracts().some((x) => x.semanticContractVersion === "1.3"), false);
  assert.throws(() => getSemanticContract("authoring-construction", "1.4"), /Unsupported semantic contract/);
  for (const key of ["authoring-construction/1.4/rules", "authoring-construction/1.3/contract", "authoring-construction/1.3/composition/bindings", "authoring-construction/1.3/conformance-not-published"]) {
    assert.throws(() => loadSemanticResource(key), /Unsupported semantic resource|Missing bundled semantic resource/);
  }
});
