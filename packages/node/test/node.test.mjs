import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { openRepository } from "../dist/node/index.js";
import { fixtureRepository } from "./fixture-repository.mjs";

test("Node repository is index-first, immutable, and binding-local deterministic", async () => {
  const root = await fixtureRepository();
  const repository = await openRepository(root);
  const reopened = await openRepository(root);
  assert.equal(repository.modelVersion, "2.1");
  assert.equal(repository.findEntityByAliasId("EXT-0001")?.entity_type, "fixture:worker");
  assert.equal(repository.fingerprint, reopened.fingerprint);
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
