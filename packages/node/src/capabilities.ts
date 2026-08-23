import { packageVersion } from "./generated/package-metadata.js";

export interface CapabilityManifest {
  readonly package_version: string;
  readonly binding: "typescript";
  readonly consumer_binding_contract_version: "1.0";
  readonly execution_environments: readonly ["browser", "node"];
  readonly supported_architecture_discovery_versions: readonly ["1.1"];
  readonly supported_normalized_model_versions: readonly ["2.1"];
  readonly supported_evidence_attribution_versions: readonly ["1.5", "1.6"];
  readonly preferred_evidence_attribution_version: "1.6";
  readonly browser_safe_entrypoints: readonly [".", "./model", "./schemas", "./validation"];
  readonly node_entrypoints: readonly ["./node", "./node/linkage"];
}

export function capabilities(): CapabilityManifest {
  return Object.freeze({
    package_version: packageVersion,
    binding: "typescript",
    consumer_binding_contract_version: "1.0",
    execution_environments: ["browser", "node"] as const,
    supported_architecture_discovery_versions: ["1.1"] as const,
    supported_normalized_model_versions: ["2.1"] as const,
    supported_evidence_attribution_versions: ["1.5", "1.6"] as const,
    preferred_evidence_attribution_version: "1.6",
    browser_safe_entrypoints: [".", "./model", "./schemas", "./validation"] as const,
    node_entrypoints: ["./node", "./node/linkage"] as const
  });
}
