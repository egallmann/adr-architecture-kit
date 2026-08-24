import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { createArchitectureModel } from "../dist/model/index.js";

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
