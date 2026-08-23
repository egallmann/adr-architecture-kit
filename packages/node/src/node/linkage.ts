import { readFile } from "node:fs/promises";
import { parse } from "yaml";
import { openRepository } from "./repository.js";
import { LinkageError, type AdrKitDiagnostic } from "../errors.js";
import { getSemanticAttributionVocabulary } from "../schemas/index.js";
import { validateContract } from "../validation/index.js";

export type LinkageProfile = "greenfield" | "brownfield" | "migration";
export interface BuildEmbodimentLinkageRequest { readonly project_root: string; readonly evidence_path: string; readonly profile?: LinkageProfile; }
export interface LinkageProvenance { readonly source_file: string; readonly extractor: string; readonly commit?: string | null; readonly source_pointer?: string | null; readonly start_line?: number | null; readonly end_line?: number | null; }
export interface LinkageOccurrence { readonly confidence: string; readonly provenance: LinkageProvenance; readonly source_language?: string; }
export interface EmbodimentIntentLink { readonly implementation_entity_id: string; readonly implementation_entity_type: string; readonly relationship: string; readonly target_entity_id: string; readonly target_entity_type: string; readonly target_alias_id: string; readonly target_alias_name: string; readonly target_lifecycle: string; readonly occurrences: readonly LinkageOccurrence[]; readonly validation_status: "valid" | "warning"; readonly diagnostics: readonly AdrKitDiagnostic[]; readonly authority_ceiling: "validated_derived_evidence"; readonly graph_admission_status: "not_admitted"; }
export interface RejectedEmbodimentClaim { readonly implementation_entity_id: string; readonly implementation_entity_type: string; readonly relationship: string; readonly target_entity_id: string; readonly confidence: string; readonly provenance: LinkageProvenance; readonly diagnostics: readonly AdrKitDiagnostic[]; }
export interface EmbodimentLinkageResult { readonly success: boolean; readonly evidence_schema_version: string; readonly architecture_fingerprint: string; readonly links: readonly EmbodimentIntentLink[]; readonly rejected_claims: readonly RejectedEmbodimentClaim[]; readonly diagnostics: readonly AdrKitDiagnostic[]; readonly error_count: number; readonly warning_count: number; readonly authority_ceiling: "validated_derived_evidence"; readonly graph_admission_status: "not_admitted"; }

const relationshipOrder: Record<string, number> = { implements: 0, enforces: 1, embodies: 2 };

export async function buildEmbodimentLinkage(request: BuildEmbodimentLinkageRequest): Promise<EmbodimentLinkageResult> {
  const profile = request.profile ?? "greenfield";
  if (!["greenfield", "brownfield", "migration"].includes(profile)) throw new LinkageError("linkage.profile", `Unsupported linkage profile: ${String(profile)}`);
  const repository = await openRepository(request.project_root);
  const raw = parse(await readFile(request.evidence_path, "utf8")) as Record<string, any>;
  const version = raw.schema_version;
  if (version !== "1.5" && version !== "1.6") throw new LinkageError("contract.unsupported_version", `Unsupported evidence schema version: ${String(version)}`);
  const capability = `evidence-attribution:${version}` as "evidence-attribution:1.5" | "evidence-attribution:1.6";
  const structural = validateContract(raw, capability);
  const diagnostics: AdrKitDiagnostic[] = structural.diagnostics.slice();
  const rejected: RejectedEmbodimentClaim[] = [];
  const grouped = new Map<string, EmbodimentIntentLink>();
  const seenClaims = new Set<string>();
  const implementationTypes = new Map<string, string>();
  const vocabulary = getSemanticAttributionVocabulary(version);
  const relationships = vocabulary.relationships as Record<string, Record<string, unknown>>;
  const records = Array.isArray(raw.records) ? raw.records : [];
  for (const [recordIndexValue, record] of records.entries()) {
    const implementationId = String(record.implementation_entity_id ?? "");
    const implementationType = String(record.implementation_entity_type ?? "");
    const priorType = implementationTypes.get(implementationId);
    if (priorType && priorType !== implementationType) {
      rejectRecordClaims(record, `attribution.implementation_type_conflict`, `implementation entity type conflicts with prior occurrence`, rejected, diagnostics);
      continue;
    }
    implementationTypes.set(implementationId, implementationType);
    const provenance = record.provenance as LinkageProvenance;
    const claims = Array.isArray(record.claims) ? record.claims : [];
    for (const claim of claims) {
      const relationship = String(claim.relationship ?? "");
      const targetId = String(claim.target_entity_id ?? "");
      const confidence = String(claim.confidence ?? "");
      const claimKey = `${implementationId}\u0000${relationship}\u0000${targetId}`;
      const claimDiagnostics: AdrKitDiagnostic[] = [];
      if (seenClaims.has(`${recordIndexValue}\u0000${claimKey}`)) claimDiagnostics.push(diagnostic("attribution.duplicate_claim", "duplicate relationship/target claim within one record"));
      seenClaims.add(`${recordIndexValue}\u0000${claimKey}`);
      if (version === "1.6" && relationship === "enforces" && confidence !== "declared") claimDiagnostics.push(diagnostic("attribution.v16_enforces_confidence", "v1.6 enforces requires confidence declared"));
      const entity = repository.findEntityByUuid(targetId);
      if (!entity) claimDiagnostics.push(diagnostic("attribution.unresolved_target", `referenced architecture entity does not exist: ${targetId}`));
      const spec = relationships[relationship];
      if (entity && spec && !(spec.allowed_target_entity_types as string[]).includes(entity.entity_type)) claimDiagnostics.push(diagnostic("attribution.illegal_target_type", `${relationship} does not admit target type ${entity.entity_type}`));
      if (entity && claim.asserted_target_entity_type && claim.asserted_target_entity_type !== entity.entity_type) claimDiagnostics.push(diagnostic("attribution.asserted_type_mismatch", `asserted target type ${claim.asserted_target_entity_type} does not match ${entity.entity_type}`));
      if (claimDiagnostics.some((item) => item.severity === "error") || !entity) {
        rejected.push({ implementation_entity_id: implementationId, implementation_entity_type: implementationType, relationship, target_entity_id: targetId, confidence, provenance, diagnostics: Object.freeze(claimDiagnostics) });
        diagnostics.push(...claimDiagnostics);
        continue;
      }
      const occurrence: LinkageOccurrence = { confidence, provenance, ...(record.attribution_source_language ? { source_language: record.attribution_source_language } : {}) };
      const existing = grouped.get(claimKey);
      if (existing) {
        const duplicate = existing.occurrences.some((item) => JSON.stringify(item) === JSON.stringify(occurrence));
        if (duplicate) { const d = diagnostic("attribution.duplicate_occurrence", "duplicate evidence occurrence"); rejected.push({ implementation_entity_id: implementationId, implementation_entity_type: implementationType, relationship, target_entity_id: targetId, confidence, provenance, diagnostics: [d] }); diagnostics.push(d); continue; }
        grouped.set(claimKey, { ...existing, occurrences: Object.freeze([...existing.occurrences, occurrence].sort(occurrenceOrder)) });
        continue;
      }
      const warning = entity.lifecycle_stage === "deprecated" || entity.lifecycle_stage === "superseded" ? diagnostic("attribution.lifecycle_warning", `referenced architecture entity is ${entity.lifecycle_stage}` , "warning") : undefined;
      const link: EmbodimentIntentLink = { implementation_entity_id: implementationId, implementation_entity_type: implementationType, relationship, target_entity_id: targetId, target_entity_type: entity.entity_type, target_alias_id: entity.alias_id, target_alias_name: entity.alias_name, target_lifecycle: entity.lifecycle_stage, occurrences: Object.freeze([occurrence]), validation_status: warning ? "warning" : "valid", diagnostics: Object.freeze(warning ? [warning] : []), authority_ceiling: "validated_derived_evidence", graph_admission_status: "not_admitted" };
      grouped.set(claimKey, link);
      if (warning) diagnostics.push(warning);
    }
  }
  const links = [...grouped.values()].sort((a, b) => a.implementation_entity_id.localeCompare(b.implementation_entity_id) || (relationshipOrder[a.relationship] ?? 99) - (relationshipOrder[b.relationship] ?? 99) || a.target_entity_id.localeCompare(b.target_entity_id));
  const errorCount = diagnostics.filter((item) => item.severity === "error").length;
  return Object.freeze({ success: errorCount === 0, evidence_schema_version: version, architecture_fingerprint: repository.fingerprint, links: Object.freeze(links), rejected_claims: Object.freeze(rejected), diagnostics: Object.freeze(diagnostics), error_count: errorCount, warning_count: diagnostics.filter((item) => item.severity === "warning").length, authority_ceiling: "validated_derived_evidence", graph_admission_status: "not_admitted" });
}

function diagnostic(code: string, message: string, severity: "error" | "warning" = "error"): AdrKitDiagnostic { return { code, message, severity }; }
function occurrenceOrder(a: LinkageOccurrence, b: LinkageOccurrence): number { return `${a.provenance.source_file}\u0000${a.provenance.source_pointer ?? ""}`.localeCompare(`${b.provenance.source_file}\u0000${b.provenance.source_pointer ?? ""}`); }
function rejectRecordClaims(record: Record<string, any>, code: string, message: string, rejected: RejectedEmbodimentClaim[], diagnostics: AdrKitDiagnostic[]): void { const d = diagnostic(code, message); for (const claim of Array.isArray(record.claims) ? record.claims : []) { rejected.push({ implementation_entity_id: String(record.implementation_entity_id), implementation_entity_type: String(record.implementation_entity_type), relationship: String(claim.relationship), target_entity_id: String(claim.target_entity_id), confidence: String(claim.confidence), provenance: record.provenance, diagnostics: [d] }); } diagnostics.push(d); }
