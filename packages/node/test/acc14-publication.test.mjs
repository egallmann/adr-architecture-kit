import assert from "node:assert/strict";
import test from "node:test";
import { getSemanticContract, loadSemanticResource, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

test("ACC 1.4 exact immutable publication qualifies its complete packaged authority", async () => {
  const definition = getSemanticContract("authoring-construction", "1.4");
  assert.equal(definition.semanticContractFingerprint, "scf:v1:sha256:19e267c5c77477a594414168bde9f733b1b9e547c06fc6836ad09392a248ea6d");
  assert.equal(definition.resourceManifest.length, 108);
  assert.deepEqual(definition.frozenNormativeConformanceResources, ["authoring-construction/1.4/conformance"]);
  assert.equal((await verifySemanticContract(definition)).success, true);
  const resources = definition.resourceManifest.map((entry) => ({ canonicalResourceKey: entry.canonicalResourceKey, content: loadSemanticResource(entry.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(definition, resources)).closure_valid, true);
  const rules = loadSemanticResource("authoring-construction/1.4/rules");
  assert.equal(rules.authority.architecture_interpretation.version, "1.4");
  assert.equal(rules.required_output.BLOCKED_is_producer, false);
  assert.equal(rules.required_output.definition_is_instance_proof, false);
  assert.equal(rules.publication_posture.execution_capability_advertised, false);
  assert.deepEqual(rules.required_output.catalog_counts, { semantic_types: 27, qualified_producer_definitions: 186, BLOCKED_destination_entries: 269, literal_copy_label_rules: 26 });
  const table = loadSemanticResource("authoring-construction/1.4/composition-bindings");
  assert.deepEqual(table.rows, loadSemanticResource("authoring-construction/1.3/composition-bindings").rows);
  assert.equal(table.rows.length, 1);
  assert.equal(table.rows[0].ai_ownership_authority.version, "1.3");
  assert.equal(table.rows[0].ai_ownership_authority.rule_id, "declaring-lifecycle.adr-logical.decisions");
  assert.equal(loadSemanticResource("authoring-construction/1.4/conformance").cases.length, 263);
  assert.deepEqual(loadSemanticResource("architecture-interpretation/1.4/contract"), getSemanticContract("architecture-interpretation", "1.4"));
  assert.deepEqual(loadSemanticResource("authoring-construction/1.3/contract"), getSemanticContract("authoring-construction", "1.3"));
});

test("ACC exact discovery rejects missing versions and malformed resources without predecessor fallback", () => {
  assert.throws(() => getSemanticContract("authoring-construction", "99.99"), /Unsupported semantic contract/);
  for (const key of ["authoring-construction/1.4/../1.3/rules", "authoring-construction/1.4/missing", "authoring-construction/1.4/composition/bindings", "authoring-construction/99.99/rules"]) {
    assert.throws(() => loadSemanticResource(key), /Unsupported semantic resource|Missing bundled semantic resource/);
  }
  assert.equal(getSemanticContract("authoring-construction", "1.3").semanticContractFingerprint, "scf:v1:sha256:5828fe0c3b1692240726152f57ca6de037a1e07f38bb8f9ecda223af105d1b49");
});
