import { readFile } from "node:fs/promises";
import { parse } from "yaml";
import { openRepository } from "./repository.js";
import { LinkageError, type AdrKitDiagnostic } from "../errors.js";
import { executeValidatedSemanticCoreRequest } from "./core.js";

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
