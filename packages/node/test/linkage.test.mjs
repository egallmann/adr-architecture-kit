import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { buildEmbodimentLinkage } from "../dist/node/linkage.js";
import { fixtureRepository } from "./fixture-repository.mjs";

test("linkage preserves non-admission and groups valid evidence", async () => {
  const root = await fixtureRepository();
  const evidence = resolve(root, "evidence.json");
  const sourceRoot = resolve("../../contracts/conformance/consumer-binding-v1/embodiment-linkage/evidence-v15.json");
  const fixture = JSON.parse(await readFile(sourceRoot, "utf8"));
  await writeFile(evidence, JSON.stringify(fixture.input), "utf8");
  const result = await buildEmbodimentLinkage({ project_root: root, evidence_path: evidence });
  assert.equal(result.success, true);
  assert.equal(result.links.length, 1);
  assert.equal(result.links[0].relationship, "implements");
  assert.equal(result.links[0].occurrences.length, 1);
  assert.equal(result.authority_ceiling, "validated_derived_evidence");
  assert.equal(result.graph_admission_status, "not_admitted");
});
