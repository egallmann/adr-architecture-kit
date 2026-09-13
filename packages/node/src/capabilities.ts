import { packageVersion } from "./generated/package-metadata.js";
import { hostCapabilities } from "./generated/host-capabilities.js";

export interface CapabilityManifest {
  readonly package_version: string;
  readonly binding: "typescript";
  readonly consumer_binding_contract_version: "1.0";
  readonly execution_environments: readonly ["browser", "node"];
  readonly supported_architecture_discovery_versions: readonly ["1.1"];
  readonly supported_normalized_model_versions: readonly ["2.1", "2.2", "2.3"];
  readonly supported_evidence_attribution_versions: readonly ["1.5", "1.6"];
  readonly preferred_evidence_attribution_version: "1.6";
  readonly supported_authoring_domain_versions: readonly ["1.0"];
  readonly preferred_authoring_domain_version: "1.0";
  readonly authoring_capabilities: readonly ["authoring.discovery"];
  readonly browser_safe_entrypoints: readonly [".", "./model", "./schemas", "./validation", "./authoring"];
  readonly node_entrypoints: readonly ["./node", "./node/linkage", "./node/governance", "./node/materialization", "./node/semantic-contract"];
  readonly host_operations: readonly string[];
  readonly pending_host_operations: readonly string[];
  readonly browser_operations: readonly string[];
}

export function capabilities(): CapabilityManifest {
  return Object.freeze({
    package_version: packageVersion,
    binding: "typescript",
    consumer_binding_contract_version: "1.0",
    execution_environments: ["browser", "node"] as const,
    supported_architecture_discovery_versions: ["1.1"] as const,
    supported_normalized_model_versions: ["2.1", "2.2", "2.3"] as const,
    supported_evidence_attribution_versions: ["1.5", "1.6"] as const,
    preferred_evidence_attribution_version: "1.6",
    supported_authoring_domain_versions: hostCapabilities.authoring_domain.supported_versions as readonly ["1.0"],
    preferred_authoring_domain_version: hostCapabilities.authoring_domain.preferred_version as "1.0",
    authoring_capabilities: hostCapabilities.authoring_domain.capabilities as readonly ["authoring.discovery"],
    browser_safe_entrypoints: [".", "./model", "./schemas", "./validation", "./authoring"] as const,
    node_entrypoints: ["./node", "./node/linkage", "./node/governance", "./node/materialization", "./node/semantic-contract"] as const,
    host_operations: hostCapabilities.peer_host_operations,
    pending_host_operations: hostCapabilities.pending_host_operations,
    browser_operations: hostCapabilities.browser_operations
  });
}
