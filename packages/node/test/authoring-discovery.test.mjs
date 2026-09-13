import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import {
  AuthoringDiscoveryError,
  describeContract,
  describeType,
  listTypes,
} from "../dist/authoring.js";

const root = resolve("../..");
const canonical = JSON.parse(await readFile(resolve(root, "contracts/authoring-domain/v1.0/contract.json"), "utf8"));
const corpus = JSON.parse(await readFile(resolve(root, "contracts/conformance/consumer-binding-v1/authoring-discovery/authoring-discovery-v1.json"), "utf8"));

function descriptorWire(value) {
  const result = {
    contract_version: value.contractVersion,
    key: value.key,
    display_name: value.displayName,
    description: value.description,
    authoring_mode: value.authoringMode,
    semantic_type_ownership: value.semanticTypeOwnership,
    discriminator: value.discriminator,
    input_contract: value.inputContract,
    identity_policy: value.identityPolicy,
    composition_policy: value.compositionPolicy,
    reference_policy: value.referencePolicy,
    field_ownership_policy: value.fieldOwnershipPolicy,
  };
  for (const policy of ["input_contract", "identity_policy", "composition_policy", "reference_policy", "field_ownership_policy"]) {
    const current = result[policy];
    const mapped = { status: current.status };
    if (current.mode !== null) mapped.mode = current.mode;
    if (current.values.length > 0) mapped.values = current.values;
    if (current.allowedParents.length > 0 || (policy === "composition_policy" && current.status === "defined")) mapped.allowed_parents = current.allowedParents.map((parent) => ({
      kind: parent.kind,
      name: parent.name,
      min_occurs: parent.minOccurs,
      max_occurs: parent.maxOccurs,
    }));
    if (current.owner !== null) mapped.owner = current.owner;
    result[policy] = mapped;
  }
  const discriminator = { mode: result.discriminator.mode };
  if (result.discriminator.field !== null) discriminator.field = result.discriminator.field;
  if (result.discriminator.value !== null) discriminator.value = result.discriminator.value;
  result.discriminator = discriminator;
  return result;
}

test("TypeScript ADC discovery matches the canonical shared corpus", () => {
  const expected = corpus.expected_observable_semantic_results;
  assert.deepEqual(describeContract("1.0"), {
    contractId: expected.describe_contract.contract_id,
    contractVersion: expected.describe_contract.contract_version,
    definedCapabilities: expected.describe_contract.defined_capabilities,
    discoveryOperations: expected.describe_contract.discovery_operations,
    typeKinds: expected.describe_contract.type_kinds,
  });
  const all = listTypes("1.0");
  assert.equal(all.types.length, 27);
  assert.deepEqual(all.types.map((item) => ({
    key: item.key,
    display_name: item.displayName,
    description: item.description,
  })), expected.list_types.types);
  assert.deepEqual(all.types.map((item) => `${item.key.kind}/${item.key.name}`),
    [...all.types].map((item) => `${item.key.kind}/${item.key.name}`).sort());
});

test("TypeScript ADC discovery filters entity types exactly", () => {
  const result = listTypes("1.0", "entity");
  assert.equal(result.contractVersion, "1.0");
  assert.equal(result.types.length, 15);
  assert.ok(result.types.every((item) => item.key.kind === "entity"));
  assert.deepEqual(result.types.map((item) => item.key.name), canonical.types
    .filter((item) => item.key.kind === "entity")
    .map((item) => item.key.name)
    .sort());
});

for (const [kind, name] of [
  ["adr", "logical"],
  ["entity", "decision"],
  ["entity", "normative_proposition"],
  ["entity", "invariant"],
  ["entity", "extension"],
  ["relationship", "calls"],
  ["relationship", "extension"],
  ["value", "normative_force"],
  ["value", "topology_component"],
]) {
  test(`TypeScript preserves the complete ${kind}/${name} descriptor`, () => {
    const expected = canonical.types.find((item) => item.key.kind === kind && item.key.name === name);
    assert.ok(expected);
    assert.deepEqual(descriptorWire(describeType("1.0", kind, name)), expected);
  });
}

for (const [operation, code, path] of [
  [() => describeContract("2.0"), "contract.unsupported_version", "contract_version"],
  [() => listTypes("1.0", "Entity"), "authoring.unknown_type_kind", "kind"],
  [() => describeType("1.0", "entity", "missing"), "authoring.unknown_type", "name"],
  [() => describeType("1.0", "entity", "Decision"), "authoring.unknown_type", "name"],
  [() => describeType("1.0", "entity", "logical"), "authoring.unknown_type", "name"],
]) {
  test(`TypeScript preserves diagnostic ${code}`, () => {
    assert.throws(operation, (error) => {
      assert.ok(error instanceof AuthoringDiscoveryError);
      assert.equal(error.code, code);
      assert.deepEqual(error.diagnostics.map((item) => ({ code: item.code, path: item.path })), [{ code, path }]);
      return true;
    });
  });
}

test("TypeScript ADC results are immutable and the browser entrypoint is a read-only surface", async () => {
  const descriptor = describeType("1.0", "value", "normative_force");
  assert.equal(Object.isFrozen(descriptor), true);
  assert.equal(Object.isFrozen(descriptor.inputContract), true);
  assert.equal(Object.isFrozen(descriptor.inputContract.values), true);
  const packageAuthoring = await import("@system-of-thought/adr-kit/authoring");
  assert.equal(typeof packageAuthoring.describeContract, "function");
});
