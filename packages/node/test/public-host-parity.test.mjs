import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, resolve } from "node:path";
import test from "node:test";
import { parse, stringify } from "yaml";
import { validateArchitecture, validateContract, validateProjectMetadata } from "../dist/node/governance.js";

const repoRoot = resolve("../..");

function normalizeDiagnostics(diagnostics) {
  // Field pointers are host-parser formatting details; compare the shared
  // semantic category and source path so equivalent failures remain peers.
  return diagnostics.map((item) => ({
    severity: item.severity,
    code: item.code.startsWith("contract.") ? "schema_validation" : item.code,
    ...(item.path ? { path: item.path } : {}),
  })).sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
}

function normalizeArchitecture(result) {
  return {
    success: result.success,
    validated_files: [...result.validated_files],
    error_count: result.error_count,
    warning_count: result.warning_count,
    diagnostics: normalizeDiagnostics(result.diagnostics),
  };
}

function normalizeMetadata(result) {
  return {
    success: result.success,
    diagnostics: normalizeDiagnostics(result.diagnostics),
  };
}

function normalizeContract(result) {
  return {
    success: result.success,
    profile: result.profile,
    outcome: result.outcome,
    sentinel_field_count: result.sentinel_field_count,
    non_complete_entity_count: result.non_complete_entity_count,
    completeness_counts: result.completeness_counts,
    issues: result.issues,
    diagnostics: normalizeDiagnostics(result.diagnostics),
  };
}

function pythonResult(root, operation) {
  const script = String.raw`
import json
import sys
from pathlib import Path
from tests.test_architecture_repository import _generate_bundle
from adr_kit.api import (
    ContractValidationRequest,
    ProjectMetadataValidationRequest,
    ValidationRequest,
    validate_architecture,
    validate_contract,
    validate_project_metadata,
)

root = Path(sys.argv[1])
operation = sys.argv[2]

def diagnostic(item):
    return {
        key: value
        for key, value in {
            "severity": item.severity,
            "code": item.code,
            "path": item.path,
            "field": getattr(item, "field", None),
        }.items()
        if value is not None
    }

if operation == "create":
    _generate_bundle(root)
    result = {"created": True}
elif operation.startswith("architecture:"):
    mode, cross_references = operation.split(":")[1:]
    value = validate_architecture(ValidationRequest(root, mode=mode, cross_references=cross_references == "true"))
    result = {
        "success": value.success,
        "validated_files": list(value.validated_files),
        "error_count": value.error_count,
        "warning_count": value.warning_count,
        "diagnostics": [diagnostic(item) for item in value.diagnostics],
    }
elif operation == "metadata":
    value = validate_project_metadata(ProjectMetadataValidationRequest(root))
    result = {"success": value.success, "diagnostics": [diagnostic(item) for item in value.diagnostics]}
elif operation.startswith("contract:"):
    _, profile, threshold = operation.split(":")
    value = validate_contract(ContractValidationRequest(root, profile=profile, max_sentinel_fields=int(threshold) if threshold else None))
    result = {
        "success": value.success,
        "profile": value.profile,
        "outcome": value.outcome,
        "sentinel_field_count": value.sentinel_field_count,
        "non_complete_entity_count": value.non_complete_entity_count,
        "completeness_counts": dict(value.completeness_counts),
        "issues": [{"path": item.path, "message": item.message} for item in value.issues],
        "diagnostics": [diagnostic(item) for item in value.diagnostics],
    }
else:
    raise ValueError(operation)
print(json.dumps(result, sort_keys=True))
`;
  const localPython = process.platform === "win32"
    ? resolve(repoRoot, ".venv/Scripts/python.exe")
    : resolve(repoRoot, ".venv/bin/python");
  const pythonPath = process.env.PYTHON ?? (existsSync(localPython) ? localPython : "python");
  const pythonPathEntries = [repoRoot, resolve(repoRoot, "src"), process.env.PYTHONPATH].filter(Boolean);
  const completed = spawnSync(pythonPath, ["-c", script, root, operation], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: pythonPathEntries.join(delimiter) },
  });
  assert.equal(completed.status, 0, completed.stderr || completed.stdout);
  return JSON.parse(completed.stdout);
}

async function assertPeer(root, operation, nodeValue, normalize) {
  assert.deepEqual(normalize(nodeValue), normalize(pythonResult(root, operation)), operation);
}

test("Python and Node public governance hosts produce equivalent normalized results", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "adr-kit-public-parity-"));
  await mkdir(resolve(root, "adrs/logical"), { recursive: true });
  await pythonResult(root, "create");
  await writeFile(resolve(root, "adrs/manifest.yaml"), [
    'schema_version: "1.0"',
    "type: manifest",
    'generated_date: "2026-01-01T00:00:00Z"',
    "generated_from: adrs/**/*.yaml",
    "adrs: []",
    "statistics:",
    "  total_adrs: 0",
    "  logical_adrs: 0",
    "  physical_adrs: 0",
  ].join("\n") + "\n", "utf8");
  const normalizedSource = JSON.parse(await readFile(resolve(repoRoot, "contracts/conformance/consumer-binding-v1/repository/model-v21.json"), "utf8")).input;
  const contractEntity = {
    id: normalizedSource.entities[0].id,
    alias_id: "COMP-0001",
    alias_name: "fixture-component",
    alias_ref: "COMP-0001:fixture-component",
    entity_type: "component",
    name: "Fixture Component",
    summary: "A canonical contract fixture.",
    uri: normalizedSource.entities[0].uri,
    created_at: "fixture-created",
    entity_fingerprint: normalizedSource.entities[0].entity_fingerprint,
    lifecycle_stage: "active",
    canonical_source: {
      source_type: "fixture",
      source_ref: "fixture:component/1",
      artifact_path: "adrs/logical/ADR-L-1000-discovery.yaml",
    },
    source_refs: [],
    relationships: {},
    provenance: {
      source_type: "fixture",
      source_ref: "fixture:component/1",
      extraction_phase: "fixture",
      classification: "explicit",
      generator: "public-host-parity",
    },
    metadata: {
      adr_id: "ADR-0001",
      technologies: [],
      module_path: "src/fixture",
      implements_capabilities: [],
      implements_system: "SYS-0001",
    },
    completeness: { status: "complete", missing_fields: [] },
  };
  await writeFile(resolve(root, "adrs/index/entity-registry.yaml"), stringify({
    schema_version: "2.1",
    type: "normalized_entity_registry",
    entities: [contractEntity],
  }), "utf8");
  await writeFile(resolve(root, "adrs/index/relationship-registry.yaml"), stringify({
    schema_version: "2.1",
    type: "relationship_registry",
    relationships: [],
  }), "utf8");
  await writeFile(resolve(root, "adrs/index/unresolved-registry.yaml"), stringify({
    schema_version: "2.1",
    type: "unresolved_registry",
    unresolved: [],
  }), "utf8");
  for (const name of ["decision", "capability", "invariant", "component", "system"]) {
    await writeFile(resolve(root, `adrs/index/${name}-registry.yaml`), stringify({
      schema_version: "2.1",
      type: "normalized_entity_registry",
      entities: [],
    }), "utf8");
  }
  await writeFile(resolve(root, "adrs/index/architecture-index.yaml"), [
    'schema_version: "1.1"',
    "type: architecture_index",
    "architecture_namespace: arch-test",
    'generated_at: "2026-01-01T00:00:00Z"',
    "generator: fixture",
    "entity_registry_path: adrs/index/entity-registry.yaml",
    "relationship_registry_path: adrs/index/relationship-registry.yaml",
    "unresolved_registry_path: adrs/index/unresolved-registry.yaml",
    "decision_registry_path: adrs/index/decision-registry.yaml",
    "capability_registry_path: adrs/index/capability-registry.yaml",
    "invariant_registry_path: adrs/index/invariant-registry.yaml",
    "component_registry_path: adrs/index/component-registry.yaml",
    "system_registry_path: adrs/index/system-registry.yaml",
    "validation_summary:",
    "  hard_failures: 0",
    "  warnings: 0",
    "  unresolved_entries: 0",
    "source_coverage:",
    "  logical_adrs: 0",
    "  physical_adrs: 0",
    "  physical_system_adrs: 0",
    "  physical_component_adrs: 0",
    "  standalone_invariants: 0",
  ].join("\n") + "\n", "utf8");

  const logicalPath = resolve(root, "adrs/logical/ADR-L-1000-discovery.yaml");
  const validLogical = await readFile(logicalPath, "utf8");
  await assertPeer(root, "architecture:complete:true", await validateArchitecture({ project_root: root, mode: "complete", cross_references: true }), normalizeArchitecture);
  await assertPeer(root, "architecture:structural:false", await validateArchitecture({ project_root: root, mode: "structural" }), normalizeArchitecture);
  await assertPeer(root, "metadata", await validateProjectMetadata({ project_root: root }), normalizeMetadata);
  await assertPeer(root, "contract:greenfield:", await validateContract({ project_root: root, profile: "greenfield" }), normalizeContract);

  // The shared authoring policy deliberately relaxes completeness-only
  // constraints such as minItems in structural mode. Both hosts must preserve
  // that policy while complete mode still reports the deficient source.
  const structuralLogical = validLogical.replace(
    "interaction_contracts: []",
    [
      "interaction_contracts:",
      "  - id: CONTRACT-1000",
      "    parties: [one]",
      "    protocol: documented",
      "    guarantees: The boundary is explicit.",
    ].join("\n"),
  );
  await writeFile(logicalPath, structuralLogical, "utf8");
  await assertPeer(root, "architecture:structural:false", await validateArchitecture({ project_root: root, mode: "structural" }), normalizeArchitecture);
  await assertPeer(root, "architecture:complete:false", await validateArchitecture({ project_root: root, mode: "complete" }), normalizeArchitecture);
  await writeFile(logicalPath, validLogical, "utf8");

  const entityPath = resolve(root, "adrs/index/entity-registry.yaml");
  const entityDocument = parse(await readFile(entityPath, "utf8"));
  const component = entityDocument.entities.find((item) => item.entity_type === "component");
  assert.ok(component);
  component.metadata.module_path = "__NOT_YET_MODELED__";
  await writeFile(entityPath, stringify(entityDocument), "utf8");
  await assertPeer(root, "contract:brownfield:", await validateContract({ project_root: root, profile: "brownfield" }), normalizeContract);
  await assertPeer(root, "contract:brownfield:0", await validateContract({ project_root: root, profile: "brownfield", max_sentinel_fields: 0 }), normalizeContract);

  await writeFile(logicalPath, validLogical.replace(/^title:.*\r?\n/m, ""), "utf8");
  await assertPeer(root, "architecture:complete:false", await validateArchitecture({ project_root: root, mode: "complete" }), normalizeArchitecture);
  await writeFile(logicalPath, "not: [valid", "utf8");
  await assertPeer(root, "architecture:complete:true", await validateArchitecture({ project_root: root, mode: "complete", cross_references: true }), normalizeArchitecture);

  await writeFile(resolve(root, "PROJECT.yaml"), "project: [malformed\n", "utf8");
  await assertPeer(root, "metadata", await validateProjectMetadata({ project_root: root }), normalizeMetadata);
  await writeFile(resolve(root, "PROJECT.yaml"), "project:\n  name: Bad Name\n", "utf8");
  await assertPeer(root, "metadata", await validateProjectMetadata({ project_root: root }), normalizeMetadata);
});
