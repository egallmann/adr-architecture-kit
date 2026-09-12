/**
 * Public Node binding for the architecture-materialization capability.
 *
 * The host owns acquisition and DTO adaptation only. The packaged WASM core
 * remains the authority for qualification, source interpretation, exact
 * resource resolution, normalization, and deterministic diagnostics.
 */
import { packageVersion } from "../generated/package-metadata.js";
import { semanticContractAssets } from "../generated/semantic-contract-assets.js";
import { executeValidatedSemanticCoreRequest } from "./core.js";
import { getSemanticContractProfile, listSemanticContractSets, listSemanticContracts, loadSemanticResource } from "./semantic-contract.js";
import type { AdrKitDiagnostic } from "../errors.js";

const API_CONTRACT_VERSION = "1.0" as const;
const assets = semanticContractAssets as Record<string, unknown>;

export interface MaterializationAuthorityProvider {
  readonly kind: string;
  readonly architecture_namespace: string;
}

export interface MaterializationSourceContract {
  readonly version: "1.5" | "1.6";
  readonly schema_resource: { readonly canonical_resource_key: string; readonly content_digest: string };
  readonly resource_closure: readonly { readonly canonical_resource_key: string; readonly content_digest: string }[];
  readonly family?: "authoring";
}

export interface MaterializationSourceArtifact {
  readonly source_ref: string;
  readonly artifact_path: string;
  readonly content_digest: string;
  readonly source_contract: MaterializationSourceContract;
  readonly document: Readonly<Record<string, unknown>>;
}

export interface MaterializationSourceBasis {
  readonly provider_source_identity: string;
  readonly source_revision: string;
  readonly artifacts: readonly MaterializationSourceArtifact[];
  readonly sealed?: true;
  readonly legacy_identity_map?: Readonly<Record<string, unknown>> | null;
}

export interface MaterializationProviderProvenance {
  readonly semanticCoreContractVersion: string;
  readonly packageVersion: string;
  readonly hostBinding: string;
}

export interface ArchitectureMaterializationRequest {
  readonly semantic_contract_set_id: string;
  readonly authority_provider: MaterializationAuthorityProvider;
  readonly source_basis: MaterializationSourceBasis | null;
  readonly direction: "none" | "forward" | "reverse";
  readonly use_mode: "new" | "historical";
  readonly profile_id: "architecture-materialization@1.0";
}

export interface MaterializationSemanticBasis {
  readonly semanticContractSetId: string | null;
  readonly authorityStateFingerprint: string | null;
}

export interface MaterializationCapabilityLimitation {
  readonly sourceContractRef: MaterializationSourceContract;
  readonly semanticCapability: string;
  readonly classification: "not_expressible_by_source_contract";
}

export interface ArchitectureMaterializationResult {
  readonly request: ArchitectureMaterializationRequest;
  readonly success: boolean;
  readonly outcome: "Materialized" | "Rejected" | "Unavailable";
  readonly authorityProvider: MaterializationAuthorityProvider | null;
  readonly sourceBasis: MaterializationSourceBasis | null;
  readonly sourceContractClosure: readonly MaterializationSourceContract[];
  readonly semanticBasis: MaterializationSemanticBasis;
  readonly normalizedModel: Readonly<Record<string, unknown>> | null;
  readonly sourceCapabilityLimitations: readonly MaterializationCapabilityLimitation[];
  readonly providerProvenance: MaterializationProviderProvenance;
  readonly diagnostics: readonly AdrKitDiagnostic[];
  readonly package_version: string;
  readonly api_contract_version: typeof API_CONTRACT_VERSION;
}

function deepFreeze<T>(value: T): T {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
  return Object.freeze(value);
}

function sourceContract(value: MaterializationSourceContract): Record<string, unknown> {
  return {
    family: value.family ?? "authoring",
    version: value.version,
    schemaResource: {
      canonicalResourceKey: value.schema_resource.canonical_resource_key,
      contentDigest: value.schema_resource.content_digest,
    },
    resourceClosure: value.resource_closure.map((item) => ({
      canonicalResourceKey: item.canonical_resource_key,
      contentDigest: item.content_digest,
    })),
  };
}

function sourceBasis(value: MaterializationSourceBasis | null): Record<string, unknown> | null {
  if (value === null) return null;
  return {
    sealed: true,
    providerSourceIdentity: value.provider_source_identity,
    sourceRevision: value.source_revision,
    artifacts: value.artifacts.map((item) => ({
      sourceRef: item.source_ref,
      artifactPath: item.artifact_path,
      contentDigest: item.content_digest,
      sourceContract: sourceContract(item.source_contract),
      document: item.document,
    })),
    ...(value.legacy_identity_map === undefined || value.legacy_identity_map === null
      ? {}
      : { legacyIdentityMap: value.legacy_identity_map }),
  };
}

function sourceContractFromWire(value: Record<string, unknown>): MaterializationSourceContract {
  const schema = value.schemaResource as Record<string, string>;
  const closure = Array.isArray(value.resourceClosure) ? value.resourceClosure : [];
  return {
    version: value.version as "1.5" | "1.6",
    family: "authoring",
    schema_resource: {
      canonical_resource_key: String(schema.canonicalResourceKey ?? ""),
      content_digest: String(schema.contentDigest ?? ""),
    },
    resource_closure: closure.map((item) => {
      const resource = item as Record<string, string>;
      return { canonical_resource_key: String(resource.canonicalResourceKey ?? ""), content_digest: String(resource.contentDigest ?? "") };
    }),
  };
}

function sourceBasisFromWire(value: unknown): MaterializationSourceBasis | null {
  if (!value || typeof value !== "object") return null;
  const basis = value as Record<string, unknown>;
  const artifacts = Array.isArray(basis.artifacts) ? basis.artifacts : [];
  return {
    sealed: true,
    provider_source_identity: String(basis.providerSourceIdentity ?? ""),
    source_revision: String(basis.sourceRevision ?? ""),
    artifacts: artifacts.map((item) => {
      const artifact = item as Record<string, unknown>;
      return {
        source_ref: String(artifact.sourceRef ?? ""),
        artifact_path: String(artifact.artifactPath ?? ""),
        content_digest: String(artifact.contentDigest ?? ""),
        source_contract: sourceContractFromWire(artifact.sourceContract as Record<string, unknown>),
        document: artifact.document as Readonly<Record<string, unknown>>,
      };
    }),
    legacy_identity_map: (basis.legacyIdentityMap as Readonly<Record<string, unknown>> | undefined) ?? null,
  };
}

function authorityDefinitions(): Record<string, unknown>[] {
  return listSemanticContracts().map((definition) => ({
    definition,
    resources: definition.resourceManifest.map((entry) => ({
      canonicalResourceKey: entry.canonicalResourceKey,
      content: loadSemanticResource(entry.canonicalResourceKey),
    })),
  }));
}

function authorityInputs(profileId: string): Record<string, unknown> {
  return {
    profile: getSemanticContractProfile(profileId),
    definitions: authorityDefinitions(),
    sets: listSemanticContractSets().map((value) => ({ ...value })),
    qualifications: assets["qualifications/architecture-materialization-1.0.json"],
    catalog: assets["catalog/semantic-contract-catalog-1.0.json"],
    policy: assets["policy/semantic-contract-policy-1.0.json"],
  };
}

function result(
  request: ArchitectureMaterializationRequest,
  value: Record<string, unknown>,
): ArchitectureMaterializationResult {
  const outcome = value.outcome === "Materialized" || value.outcome === "Unavailable"
    ? value.outcome
    : "Rejected";
  const semanticBasis = value.semanticBasis as Record<string, unknown> | undefined;
  return deepFreeze({
    request,
    success: value.success === true,
    outcome,
    authorityProvider: (value.authorityProvider as MaterializationAuthorityProvider | null | undefined) ?? null,
    sourceBasis: sourceBasisFromWire(value.sourceBasis),
    sourceContractClosure: Array.isArray(value.sourceContractClosure)
      ? value.sourceContractClosure.map((item) => sourceContractFromWire(item as Record<string, unknown>))
      : [],
    semanticBasis: {
      semanticContractSetId: typeof semanticBasis?.semanticContractSetId === "string" ? semanticBasis.semanticContractSetId : null,
      authorityStateFingerprint: typeof semanticBasis?.authorityStateFingerprint === "string" ? semanticBasis.authorityStateFingerprint : null,
    },
    normalizedModel: (value.normalizedModel as Readonly<Record<string, unknown>> | null | undefined) ?? null,
    sourceCapabilityLimitations: Array.isArray(value.sourceCapabilityLimitations)
      ? value.sourceCapabilityLimitations.map((item) => {
        const limitation = item as Record<string, unknown>;
        return {
          sourceContractRef: sourceContractFromWire(limitation.sourceContractRef as Record<string, unknown>),
          semanticCapability: String(limitation.semanticCapability ?? ""),
          classification: "not_expressible_by_source_contract" as const,
        };
      })
      : [],
    providerProvenance: (value.providerProvenance as MaterializationProviderProvenance | undefined) ?? {
      semanticCoreContractVersion: "1.1",
      packageVersion,
      hostBinding: "public-host",
    },
    diagnostics: Array.isArray(value.diagnostics) ? value.diagnostics : [],
    package_version: packageVersion,
    api_contract_version: API_CONTRACT_VERSION,
  }) as ArchitectureMaterializationResult;
}

export async function materializeArchitecture(
  request: ArchitectureMaterializationRequest,
): Promise<ArchitectureMaterializationResult> {
  const profileId = request.profile_id;
  const wire: Record<string, unknown> = {
    core_contract_version: "1.1",
    operation: "materialize_architecture",
    materializationContractVersion: "1.0",
    semanticContractSetId: request.semantic_contract_set_id,
    authorityProvider: {
      kind: request.authority_provider.kind,
      architectureNamespace: request.authority_provider.architecture_namespace,
    },
    sourceBasis: sourceBasis(request.source_basis),
    providerProvenance: {
      semanticCoreContractVersion: "1.1",
      packageVersion,
      hostBinding: "public-host",
    },
    targetOperation: "materialize_architecture",
    direction: request.direction,
    useMode: request.use_mode,
    ...authorityInputs(profileId),
  };
  return result(request, await executeValidatedSemanticCoreRequest(wire));
}
