import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createArchitectureModel } from "../dist/model/index.js";
import { validateContract } from "../dist/validation/index.js";

const fixturePath = resolve("../../contracts/conformance/consumer-binding-v1/repository/model-v21.json");
const fixture = JSON.parse(await readFile(fixturePath, "utf8"));

test("model view preserves UUID identity, extensions, unresolved state, and relationship kinds", () => {
  const view = createArchitectureModel(fixture.input);
  assert.equal(view.findEntityByAliasId("ADR-0001")?.id, "018f2c9a-5f2a-7e11-8b3c-1234567890ab");
  assert.deepEqual(view.extensionEntities()[0].extension.properties.flags, [true, false]);
  assert.equal(view.relationships().filter((item) => item.record_kind === "compatibility").length, 1);
  assert.equal(view.unresolved().length, 1);
  assert.equal(view.relationshipsForEntity("018f2c9a-5f2a-7e12-8b3c-1234567890ac", { direction: "outgoing" }).length, 2);
  assert.equal(Object.isFrozen(view.model), true);
});

test("model view preserves the accepted normalized model 2.2 contract", () => {
  const modelV22 = { ...fixture.input, schema_version: "2.2" };
  assert.equal(validateContract(modelV22, "normalized-model:2.2").valid, true);
  const view = createArchitectureModel(modelV22);
  assert.equal(view.model.schema_version, "2.2");
  assert.deepEqual(view.extensionEntities()[0].extension.properties.flags, [true, false]);
  assert.equal(view.relationships().length, fixture.input.relationships.length);
});

test("v2.2 canonical schema rejects topology-local relationship endpoints", () => {
  const modelV22 = { ...fixture.input, schema_version: "2.2" };
  const invalid = {
    ...modelV22,
    relationships: modelV22.relationships.map((relationship, index) =>
      index === 0 ? { ...relationship, from_entity_id: "TOPO-0001" } : relationship),
  };
  assert.equal(validateContract(invalid, "normalized-model:2.2").valid, false);
});
