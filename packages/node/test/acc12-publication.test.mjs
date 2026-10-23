import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  getSemanticContract,
  listSemanticContracts,
  loadSemanticResource,
  validateSemanticResourceClosure,
  verifySemanticContract,
} from "../dist/node/semantic-contract.js";
import { semanticCoreCapabilities } from "../dist/node/protocol.js";

test("Node exposes exact ACC 1.2 authority without selecting it or advertising execution", async () => {
  const canonical = JSON.parse(await readFile("../../contracts/authoring-construction/v1.2/contract.json", "utf8"));
  const contract = getSemanticContract("authoring-construction", "1.2");
  assert.deepEqual(contract, canonical);
  assert.notEqual(contract.semanticContractFingerprint, getSemanticContract("authoring-construction", "1.1").semanticContractFingerprint);
  assert.throws(() => getSemanticContract("authoring-construction", "1.4"));
  assert.equal((await verifySemanticContract(contract)).success, true);
  const resources = contract.resourceManifest.map((item) => ({
    canonicalResourceKey: item.canonicalResourceKey,
    content: loadSemanticResource(item.canonicalResourceKey),
  }));
  assert.equal((await validateSemanticResourceClosure(contract, resources)).closure_valid, true);
  const key = "authoring-construction/1.2/composition-bindings";
  assert.deepEqual(loadSemanticResource(key), JSON.parse(await readFile("../../contracts/authoring-construction/v1.2/resources/composition-bindings.json", "utf8")));
  assert.equal((await validateSemanticResourceClosure(contract, resources.filter((item) => item.canonicalResourceKey !== key))).success, false);
  assert.equal(listSemanticContracts().some((item) => item.semanticContractFamily === "authoring-construction"), false);
  assert.equal(Object.values(semanticCoreCapabilities().operations_by_version).flat().some((operation) => operation.includes("construction") && operation.includes("1_2")), false);
});
