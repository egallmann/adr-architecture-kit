import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { openRepository } from "../dist/node/index.js";
import { fixtureRepository } from "./fixture-repository.mjs";

test("Node repository is index-first, immutable, and binding-local deterministic", async () => {
  const root = await fixtureRepository();
  const repository = await openRepository(root);
  const reopened = await openRepository(root);
  const urlRepository = await openRepository(pathToFileURL(root));
  assert.equal(repository.modelVersion, "2.1");
  assert.equal(repository.findEntityByAliasId("EXT-0001")?.entity_type, "fixture:worker");
  assert.equal(repository.fingerprint, reopened.fingerprint);
  assert.equal(repository.fingerprint, urlRepository.fingerprint);
  assert.equal(repository.subsets.components?.length ?? 0, 0);
  assert.equal(repository.project_root, root);
});

test("Node repository rejects an index escape", async () => {
  const root = await fixtureRepository();
  const index = resolve(root, "adrs/index/architecture-index.yaml");
  const text = await readFile(index, "utf8");
  await writeFile(index, text.replace("adrs/index/entity-registry.yaml", "../../outside.yaml"), "utf8");
  await assert.rejects(() => openRepository(root), /escapes project root/);
});

test("Node repository rejects mixed normalized registry versions", async () => {
  const root = await fixtureRepository();
  const relationshipPath = resolve(root, "adrs/index/relationship-registry.yaml");
  const text = await readFile(relationshipPath, "utf8");
  await writeFile(relationshipPath, text.replace('"schema_version": "2.1"', '"schema_version": "2.2"'), "utf8");
  await assert.rejects(() => openRepository(root), /does not match normalized model 2.1/);
});

test("Node repository opens the current normalized model 2.2 bundle", async () => {
  const repository = await openRepository(resolve("../.."));
  assert.equal(repository.modelVersion, "2.2");
  assert.equal(repository.model.schema_version, "2.2");
  assert.ok(repository.model.validation_summary);
  assert.ok(repository.model.source_coverage);
  const composed = repository.relationships().find((relationship) => relationship.relationship_type === "composed_of");
  assert.ok(composed);
  assert.equal(repository.findEntityByUuid(composed.from_entity_id)?.entity_type, "system");
  assert.equal(repository.findEntityByUuid(composed.to_entity_id)?.entity_type, "component");
  const dependsOn = repository.relationships().find((relationship) => relationship.relationship_type === "depends_on");
  assert.ok(dependsOn);
  assert.ok(repository.relationshipsForEntity(dependsOn.from_entity_id, { direction: "outgoing" }).some((relationship) => relationship.relationship_type === "depends_on"));
});
