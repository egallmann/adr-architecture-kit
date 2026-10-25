import assert from "node:assert/strict";
import test from "node:test";
import { getSemanticContract, loadSemanticResource, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

const prefix = "architecture-interpretation/1.5/";
test("AI 1.5 exact packaged publication qualifies identity recipe definitions without instance execution", async () => {
  const contract = getSemanticContract("architecture-interpretation", "1.5");
  assert.equal(contract.semanticContractFingerprint, "scf:v1:sha256:e3d52d9e863cfb6008f55bbff5c7ea4e676ac6a021d9eb52126284636d0329af");
  assert.equal(contract.resourceManifest.length, 69);
  assert.deepEqual(contract.frozenNormativeConformanceResources, [prefix + "conformance"]);
  assert.equal((await verifySemanticContract(contract)).success, true);
  const bundle = contract.resourceManifest.map((m) => ({ canonicalResourceKey: m.canonicalResourceKey, content: loadSemanticResource(m.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(contract, bundle)).closure_valid, true);
  assert.equal((await validateSemanticResourceClosure(contract, [...bundle].reverse())).closure_valid, true);
  const catalog = loadSemanticResource(prefix + "required-output-derivations");
  assert.equal(catalog.types.length, 27);
  const statuses = catalog.types.flatMap((t) => t.outputs).reduce((counts, e) => { counts[e.status] = (counts[e.status] ?? 0) + 1; return counts; }, {});
  assert.deepEqual(statuses, { QUALIFIED: 240, BLOCKED: 215 });
  assert.equal(catalog.inherited_output_authority.local_rule_bindings.literal_string_copy.canonical_resource_key, "architecture-interpretation/1.4/required-output-derivations");
  const recipes = loadSemanticResource(prefix + "identity-representation-recipes");
  assert.equal(recipes.applicability.instance_applicability, "Unknown");
  assert.equal(recipes.scope.complete_interpretation, "Unavailable");
  assert.equal(recipes.scope.instance_values_produced, false);
  assert.equal(recipes.context_authority.governing_version, "1.3");
  assert.equal(loadSemanticResource(prefix + "conformance").cases.length, 132);
  assert.equal(loadSemanticResource("architecture-interpretation/1.4/required-output-derivations").types.flatMap((t) => t.outputs).filter((e) => e.status === "BLOCKED").length, 269);
});

test("AI 1.5 missing versions, malformed keys and corrupted bundles fail closed", async () => {
  assert.throws(() => getSemanticContract("architecture-interpretation", "99.99"), /Unsupported semantic contract/);
  for (const key of [prefix + "missing", prefix + "../1.4/rules", prefix + "required/output"]) assert.throws(() => loadSemanticResource(key), /Missing bundled semantic resource/);
  const c = getSemanticContract("architecture-interpretation", "1.5");
  const bundle = c.resourceManifest.map((m) => ({ canonicalResourceKey: m.canonicalResourceKey, content: loadSemanticResource(m.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(c, bundle.slice(1))).closure_valid, false);
  const altered = structuredClone(bundle); altered[0].content = { tampered: true };
  assert.equal((await validateSemanticResourceClosure(c, altered)).closure_valid, false);
});
