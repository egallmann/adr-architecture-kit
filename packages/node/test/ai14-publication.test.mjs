import assert from "node:assert/strict";
import test from "node:test";
import { getSemanticContract, loadSemanticResource, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

test("AI 1.4 exact authority and complete packaged closure qualify without execution", async () => {
  const contract = getSemanticContract("architecture-interpretation", "1.4");
  assert.equal(contract.semanticContractFingerprint, "scf:v1:sha256:5c338d24961946d7f7d4350d5bfbbfb9e3882c56c8be09ba4d242169163acdd7");
  assert.equal(contract.resourceManifest.length, 60);
  assert.deepEqual(contract.frozenNormativeConformanceResources, ["architecture-interpretation/1.4/conformance"]);
  assert.equal((await verifySemanticContract(contract)).success, true);
  const bundle = contract.resourceManifest.map((entry) => ({ canonicalResourceKey: entry.canonicalResourceKey, content: loadSemanticResource(entry.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(contract, bundle)).closure_valid, true);
  const catalog = loadSemanticResource("architecture-interpretation/1.4/required-output-derivations");
  assert.equal(catalog.types.length, 27);
  assert.equal(catalog.operation.id, "literal_string_copy");
  assert.equal(catalog.coverage.complete_interpretation, "Unavailable");
  assert.equal(loadSemanticResource("architecture-interpretation/1.4/conformance").cases.length, 85);
  assert.equal(loadSemanticResource("architecture-interpretation/1.4/rules").public_boundary.advertised, false);
  assert.equal(getSemanticContract("architecture-interpretation", "1.3").semanticContractFingerprint, "scf:v1:sha256:d4a60e843c3069cfd7eb869a4d924d3a70bf900079d3a2ad86ae28884c6ac167");
});

test("AI successor exact lookup never falls back or accepts malformed resources", () => {
  assert.throws(() => getSemanticContract("architecture-interpretation", "99.99"), /Unsupported semantic contract/);
  for (const key of ["architecture-interpretation/1.4/missing", "architecture-interpretation/1.4/../1.3/rules", "architecture-interpretation/1.4/required/output"]) {
    assert.throws(() => loadSemanticResource(key), /Missing bundled semantic resource/);
  }
  assert.throws(() => loadSemanticResource("architecture-interpretation/99.99/rules"), /Unsupported semantic resource/);
});
