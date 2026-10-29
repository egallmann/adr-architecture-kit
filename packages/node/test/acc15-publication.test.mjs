import assert from "node:assert/strict";
import test from "node:test";
import { getSemanticContract, loadSemanticResource, verifySemanticContract, validateSemanticResourceClosure } from "../dist/node/semantic-contract.js";

const p = "authoring-construction/1.5/";

test("ACC 1.5 exact packaged authority preserves actual inherited rules and unavailable execution", async () => {
  const contract = getSemanticContract("authoring-construction", "1.5");
  assert.equal(contract.resourceManifest.length, 125);
  assert.deepEqual(contract.frozenNormativeConformanceResources, [p + "conformance"]);
  assert.equal((await verifySemanticContract(contract)).success, true);
  const bundle = contract.resourceManifest.map(m => ({ canonicalResourceKey: m.canonicalResourceKey, content: loadSemanticResource(m.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(contract, bundle)).closure_valid, true);
  assert.equal((await validateSemanticResourceClosure(contract, [...bundle].reverse())).closure_valid, true);
  const rules = loadSemanticResource(p + "rules");
  assert.equal(rules.authority.architecture_interpretation.version, "1.5");
  assert.equal(rules.authority.architecture_interpretation.fingerprint, getSemanticContract("architecture-interpretation", "1.5").semanticContractFingerprint);
  assert.deepEqual(rules.required_output.catalog_counts, { semantic_types: 27, output_branches: 6, qualified_producer_definitions: 240, BLOCKED_destination_entries: 215, literal_copy_label_rules: 26, identity_representation_definitions: 54 });
  assert.deepEqual(rules.required_output.identity_recipe_operations, ["literal_alias_join", "literal_entity_uri", "uuidv7_unix_milliseconds_to_rfc3339_utc"]);
  assert.equal(rules.required_output.schema_valid_is_instance_proof, false);
  assert.equal(rules.publication_posture.execution_capability_advertised, false);
  const table = loadSemanticResource(p + "composition-bindings");
  assert.equal(table.rows.length, 1);
  assert.deepEqual(table.rows, loadSemanticResource("authoring-construction/1.4/composition-bindings").rows);
  assert.equal(table.rows[0].ai_ownership_authority.version, "1.3");
  assert.deepEqual(table.semanticDependencies.filter(k => k.endsWith("composition-bindings.schema")), [p + "composition-bindings.schema"]);
  const cases = loadSemanticResource(p + "conformance");
  assert.equal(cases.cases.length, 555);
  assert.equal(cases.inherited_cases.length, 263);
  assert.equal(cases.authority_only, true);
  assert.equal(cases.runtime_execution_coverage, false);
});

test("ACC 1.5 missing, malformed and corrupted packaged authority fails closed", async () => {
  assert.throws(() => getSemanticContract("authoring-construction", "missing-version"));
  for (const key of [p + "missing", p + "../1.4/rules", p + "composition/bindings"]) assert.throws(() => loadSemanticResource(key));
  const contract = getSemanticContract("authoring-construction", "1.5");
  const bundle = contract.resourceManifest.map(m => ({ canonicalResourceKey: m.canonicalResourceKey, content: loadSemanticResource(m.canonicalResourceKey) }));
  assert.equal((await validateSemanticResourceClosure(contract, bundle.slice(1))).closure_valid, false);
  const altered = structuredClone(bundle); altered[0].content = { tampered: true };
  assert.equal((await validateSemanticResourceClosure(contract, altered)).closure_valid, false);
});
