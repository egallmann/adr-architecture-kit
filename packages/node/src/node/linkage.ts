import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { parse } from "yaml";
import { openRepository } from "./repository.js";
import { AttributionShimError, LinkageError, type AdrKitDiagnostic } from "../errors.js";
import { executeValidatedSemanticCoreRequest } from "./core.js";
import { getSemanticAttributionVocabulary } from "../schemas/index.js";
import { packageVersion } from "../generated/package-metadata.js";

export { AttributionShimError, LinkageError } from "../errors.js";

export type LinkageProfile = "greenfield" | "brownfield" | "migration";

export interface BuildEmbodimentLinkageRequest {
  readonly project_root: string;
  readonly evidence_path: string;
  readonly profile?: LinkageProfile;
}

export interface LinkageProvenance {
  readonly source_file: string;
  readonly extractor: string;
  readonly commit?: string | null;
  readonly source_pointer?: string | null;
  readonly start_line?: number | null;
  readonly end_line?: number | null;
}

export interface LinkageOccurrence {
  readonly confidence: string;
  readonly provenance: LinkageProvenance;
  readonly source_language?: string;
}

export interface EmbodimentIntentLink {
  readonly implementation_entity_id: string;
  readonly implementation_entity_type: string;
  readonly relationship: string;
  readonly target_entity_id: string;
  readonly target_entity_type: string;
  readonly target_alias_id: string;
  readonly target_alias_name: string;
  readonly target_lifecycle: string;
  readonly occurrences: readonly LinkageOccurrence[];
  readonly validation_status: "valid" | "warning";
  readonly diagnostics: readonly AdrKitDiagnostic[];
  readonly authority_ceiling: "validated_derived_evidence";
  readonly graph_admission_status: "not_admitted";
}

export interface RejectedEmbodimentClaim {
  readonly implementation_entity_id: string;
  readonly implementation_entity_type: string;
  readonly relationship: string;
  readonly target_entity_id: string;
  readonly confidence: string;
  readonly provenance: LinkageProvenance;
  readonly diagnostics: readonly AdrKitDiagnostic[];
}

export interface EmbodimentLinkageResult {
  readonly success: boolean;
  readonly evidence_schema_version: string;
  readonly architecture_fingerprint: string;
  readonly links: readonly EmbodimentIntentLink[];
  readonly rejected_claims: readonly RejectedEmbodimentClaim[];
  readonly diagnostics: readonly AdrKitDiagnostic[];
  readonly error_count: number;
  readonly warning_count: number;
  readonly authority_ceiling: "validated_derived_evidence";
  readonly graph_admission_status: "not_admitted";
}

export type AttributionShimLanguage = "python" | "typescript";

export interface AttributionShimRequest {
  readonly language: AttributionShimLanguage;
}

export interface AttributionShimResult {
  readonly success: true;
  readonly language: AttributionShimLanguage;
  readonly content: string;
  readonly sha256: string;
  readonly diagnostics: readonly AdrKitDiagnostic[];
  readonly package_version: string;
  readonly api_contract_version: "1.0";
}

function shimVocabulary(): Record<string, unknown> {
  const source = getSemanticAttributionVocabulary("1.5");
  const legacy = source.legacy_decorators;
  const relationships = source.relationships;
  if (!source.canonical_claims_attribute || !legacy || typeof legacy !== "object" || !relationships || typeof relationships !== "object") {
    throw new AttributionShimError("attribution_shim.invalid_request", "Canonical attribution vocabulary is malformed");
  }
  return {
    canonical_claims_attribute: source.canonical_claims_attribute,
    legacy_decorators: Object.entries(legacy as Record<string, Record<string, unknown>>).map(([name, value]) => ({
      name,
      attribute: value.attribute,
      label: value.label,
      variadic: Boolean(value.variadic),
    })),
    relationships: Object.entries(relationships as Record<string, Record<string, unknown>>).map(([name, value]) => ({
      name,
      uuid_decorator: value.uuid_decorator,
      uuid_sequence_decorator: value.uuid_sequence_decorator,
    })),
  };
}

export async function generateAttributionShim(
  request: AttributionShimRequest,
): Promise<AttributionShimResult> {
  const language = typeof request.language === "string" ? request.language.trim().toLowerCase() : "";
  if (language !== "python" && language !== "typescript") {
    throw new AttributionShimError(
      "attribution_shim.invalid_request",
      `Unsupported shim language: ${String(request.language)} (supported: python, typescript)`,
    );
  }
  const result = await executeValidatedSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "generate_attribution_shim",
    language,
    vocabulary: shimVocabulary(),
  });
  if (!result.success || typeof result.content !== "string" || result.language !== language) {
    const message = Array.isArray(result.diagnostics)
      ? result.diagnostics.map((item) => String((item as Record<string, unknown>).message ?? "attribution shim generation failed")).join("; ")
      : "attribution shim generation failed";
    throw new AttributionShimError("attribution_shim.generation", message);
  }
  const content = result.content;
  const sha256 = createHash("sha256").update(Buffer.from(content, "utf8")).digest("hex");
  return Object.freeze({
    success: true,
    language,
    content,
    sha256,
    diagnostics: Object.freeze((result.diagnostics ?? []) as readonly AdrKitDiagnostic[]),
    package_version: packageVersion,
    api_contract_version: "1.0" as const,
  });
}

export async function buildEmbodimentLinkage(
  request: BuildEmbodimentLinkageRequest,
): Promise<EmbodimentLinkageResult> {
  const profile = request.profile ?? "greenfield";
  if (!["greenfield", "brownfield", "migration"].includes(profile)) {
    throw new LinkageError("linkage.profile", `Unsupported linkage profile: ${String(profile)}`);
  }

  const repository = await openRepository(request.project_root);
  const raw = parse(await readFile(request.evidence_path, "utf8")) as Record<string, unknown>;
  const version = raw.schema_version;
  if (version !== "1.5" && version !== "1.6") {
    throw new LinkageError(
      "contract.unsupported_version",
      `Unsupported evidence schema version: ${String(version)}`,
    );
  }

  const result = await executeValidatedSemanticCoreRequest({
    core_contract_version: "1.0",
    operation: "build_embodiment_linkage",
    profile,
    evidence_schema_version: version,
    architecture_fingerprint: repository.fingerprint,
    records: Array.isArray(raw.records) ? raw.records : [],
    entities: repository.entities(),
  });
  return result as unknown as EmbodimentLinkageResult;
}
