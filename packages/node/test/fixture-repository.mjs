import { mkdir, readFile, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";

const source = JSON.parse(await readFile(resolve("../../contracts/conformance/consumer-binding-v1/repository/model-v21.json"), "utf8")).input;

export async function fixtureRepository() {
  const root = await mkdtemp(resolve(tmpdir(), "adr-kit-fixture-"));
  await mkdir(resolve(root, "adrs/index"), { recursive: true });
  await writeFile(resolve(root, "PROJECT.yaml"), "name: fixture\n", "utf8");
  const dump = (value) => JSON.stringify(value, null, 2);
  await writeFile(resolve(root, "adrs/index/entity-registry.yaml"), dump({ schema_version: "2.1", type: "normalized_entity_registry", entities: source.entities }), "utf8");
  await writeFile(resolve(root, "adrs/index/relationship-registry.yaml"), dump({ schema_version: "2.1", type: "relationship_registry", relationships: source.relationships }), "utf8");
  await writeFile(resolve(root, "adrs/index/unresolved-registry.yaml"), dump({ schema_version: "2.1", type: "unresolved_registry", unresolved: source.unresolved }), "utf8");
  await writeFile(resolve(root, "adrs/index/architecture-index.yaml"), `schema_version: '1.1'\ntype: architecture_index\narchitecture_namespace: fixture\ngenerated_at: '2026-08-23T00:00:00Z'\ngenerator: fixture\nentity_registry_path: adrs/index/entity-registry.yaml\nrelationship_registry_path: adrs/index/relationship-registry.yaml\nunresolved_registry_path: adrs/index/unresolved-registry.yaml\ndecision_registry_path: adrs/index/decision-registry.yaml\ncapability_registry_path: adrs/index/capability-registry.yaml\ninvariant_registry_path: adrs/index/invariant-registry.yaml\ncomponent_registry_path: adrs/index/component-registry.yaml\nsystem_registry_path: adrs/index/system-registry.yaml\nvalidation_summary:\n  hard_failures: 0\n  warnings: 0\n  unresolved_entries: 1\nsource_coverage:\n  logical_adrs: 1\n  physical_adrs: 0\n  physical_system_adrs: 0\n  physical_component_adrs: 0\n  standalone_invariants: 0\n`, "utf8");
  await writeFile(resolve(root, "adrs/manifest.yaml"), "schema_version: '1.0'\ntype: manifest\ngenerated_date: '2026-08-23T00:00:00Z'\ngenerated_from: adrs/**/*.yaml\nadrs: []\nstatistics:\n  total_adrs: 0\n  logical_adrs: 0\n  physical_adrs: 0\n", "utf8");
  return root;
}
