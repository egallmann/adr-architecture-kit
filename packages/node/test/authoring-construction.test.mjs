import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { delimiter, resolve } from "node:path";
import test from "node:test";
import { constructAuthoringSet, validateAuthoring } from "../dist/node/index.js";

const repoRoot = resolve("../..");
const corpus = JSON.parse(await readFile(resolve(repoRoot, "contracts/authoring-construction/v1.0/resources/conformance.json"), "utf8"));
const accContract = JSON.parse(await readFile(resolve(repoRoot, "contracts/authoring-construction/v1.0/contract.json"), "utf8"));

function bindMarkers(value) {
  if (typeof value === "string") return value === "$enclosing_scf" ? accContract.semanticContractFingerprint : value;
  if (Array.isArray(value)) return value.map(bindMarkers);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, bindMarkers(child)]));
  return value;
}

function requestFor(caseId) {
  const source = corpus.cases.find((item) => item.id === caseId);
  assert.ok(source, caseId);
  return bindMarkers(source.input);
}

function normalize(result) {
  return {
    operation: result.operation,
    status: result.validation_status ?? result.outcome,
    diagnostics: result.diagnostics.map((item) => item.code),
    candidate_fragments: result.candidate_fragments?.length ?? 0,
    candidate_artifacts: result.candidate_artifacts?.length ?? 0,
    construction_map: result.construction_map?.length ?? 0,
    candidate_source_digest: result.candidate_source_basis?.basis_digest ?? null,
    normalized_digest: result.normalized_result?.semantic_digest ?? null,
    round_trip: result.round_trip ? {
      qualified: result.round_trip.qualified,
      comparison: result.round_trip.comparison,
    } : null,
  };
}

function pythonResult(request) {
  const script = String.raw`
import json
import sys
from adr_kit.api import AuthoringRequest, construct_authoring_set, validate_authoring

request = AuthoringRequest.from_wire(json.loads(sys.argv[1]))
value = validate_authoring(request) if request.operation == "validate_authoring" else construct_authoring_set(request)
result = {
    "operation": value.request.operation,
    "status": getattr(value, "validation_status", getattr(value, "outcome", None)),
    "diagnostics": [item.code for item in value.diagnostics],
    "candidate_fragments": len(getattr(value, "candidate_fragments", ())),
    "candidate_artifacts": len(getattr(value, "candidate_artifacts", ())),
    "construction_map": len(getattr(value, "construction_map", ())),
    "candidate_source_digest": (value.candidate_source_basis or {}).get("basis_digest") if hasattr(value, "candidate_source_basis") and value.candidate_source_basis else None,
    "normalized_digest": (value.normalized_result or {}).get("semantic_digest") if hasattr(value, "normalized_result") and value.normalized_result else None,
    "round_trip": ({"qualified": value.round_trip["qualified"], "comparison": value.round_trip["comparison"]} if hasattr(value, "round_trip") else None),
}
print(json.dumps(result))
`;
  const localPython = process.platform === "win32" ? resolve(repoRoot, ".venv/Scripts/python.exe") : resolve(repoRoot, ".venv/bin/python");
  const pythonPath = process.env.PYTHON ?? (existsSync(localPython) ? localPython : "python");
  const completed = spawnSync(pythonPath, ["-c", script, JSON.stringify(request)], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: [repoRoot, resolve(repoRoot, "src"), process.env.PYTHONPATH].filter(Boolean).join(delimiter) },
  });
  assert.equal(completed.status, 0, completed.stderr || completed.stdout);
  return JSON.parse(completed.stdout);
}

test("public Node validation uses semantic-core protocol 1.2 and returns governed status", async () => {
  const result = await validateAuthoring(requestFor("C27"));
  assert.equal(result.operation, "validate_authoring");
  assert.equal(result.validation_status, "invalid");
  assert.ok(result.diagnostics.length > 0);
});

for (const [caseId, outcome] of [["C01", "Constructed"], ["C32", "Rejected"], ["C33", "Unavailable"], ["C41", "Unresolved"]]) {
  test(`public Node construction returns ${outcome} for ${caseId}`, async () => {
    const result = await constructAuthoringSet(requestFor(caseId));
    assert.equal(result.outcome, outcome);
    assert.ok(Array.isArray(result.diagnostics));
  });
}

for (const [caseId, parentKey, childKey] of [["C05", "parent", "child"], ["C07", "adr", "decision"]]) {
  test(`public Node construction preserves minimal source roots for ${caseId}`, async () => {
    const result = await constructAuthoringSet(requestFor(caseId));
    const expected = corpus.cases.find((item) => item.id === caseId).expected.result;
    assert.equal(result.outcome, "Constructed");
    assert.deepEqual(
      result.candidate_artifacts.map((item) => item.source_ref),
      expected.candidate_artifacts.map((item) => item.source_ref),
    );
    assert.deepEqual(
      result.candidate_source_basis.artifacts.map((item) => item.source_ref),
      expected.candidate_source_basis.artifacts.map((item) => item.source_ref),
    );
    assert.deepEqual(
      result.candidate_source_basis.artifacts.map((item) => item.request_key),
      [parentKey],
    );
    assert.ok(result.candidate_artifacts.some((item) => item.request_key === childKey));
  });
}

test("Python and Node public construction results have equivalent observables", async () => {
  for (const caseId of ["C01", "C32", "C33", "C41"]) {
    const result = await constructAuthoringSet(requestFor(caseId));
    assert.deepEqual(normalize(result), pythonResult(requestFor(caseId)), caseId);
  }
});

test("constructed candidates are detached result data, not persistence", async () => {
  const result = await constructAuthoringSet(requestFor("C01"));
  assert.equal(result.outcome, "Constructed");
  assert.equal(result.round_trip.qualified, true);
  assert.ok(result.candidate_artifacts[0].bytes);
  assert.ok(Object.isFrozen(result));
  assert.ok(Object.isFrozen(result.candidate_artifacts));
});
