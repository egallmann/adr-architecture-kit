export type JsonValue = null | boolean | number | string | JsonValue[] | { readonly [key: string]: JsonValue };

export interface NormalizedEntityV21 {
  readonly id: string;
  readonly alias_id: string;
  readonly alias_name: string;
  readonly alias_ref: string;
  readonly entity_type: string;
  readonly name: string;
  readonly summary: string;
  readonly uri: string;
  readonly created_at: string;
  readonly entity_fingerprint: string;
  readonly lifecycle_stage: "proposed" | "active" | "deprecated" | "superseded";
  readonly canonical_source: Record<string, unknown>;
  readonly source_refs?: readonly unknown[];
  readonly metadata?: Record<string, unknown>;
  readonly relationships?: Record<string, unknown>;
  readonly completeness: Record<string, unknown>;
  readonly provenance: Record<string, unknown>;
  readonly extension?: { readonly properties: Record<string, JsonValue>; readonly rationale: string };
}

/**
 * Normalized model 2.2 keeps the v2.1 entity identity and payload shape.  The
 * versioned name is intentional: it lets the binding preserve the accepted
 * contract version without creating a second semantic entity model.
 */
export interface NormalizedEntityV22 extends NormalizedEntityV21 {}

export interface NormativePropositionEntityV23 {
  readonly id: string;
  readonly alias_id: `NP-${number}` | string;
  readonly alias_name: string;
  readonly alias_ref: string;
  readonly entity_type: "normative_proposition";
  readonly name: string;
  readonly summary: string;
  readonly uri: string;
  readonly created_at: string;
  readonly entity_fingerprint: string;
  readonly statement: string;
  readonly normative_force: "MUST" | "MUST NOT" | "SHOULD" | "SHOULD NOT" | "MAY";
  readonly scope: string;
  readonly rationale?: string | null;
  readonly declaring_adr: Record<string, unknown>;
  readonly source_artifact: Record<string, unknown>;
  readonly source_contract: Record<string, unknown>;
  readonly canonical_source: Record<string, unknown>;
  readonly source_refs?: readonly unknown[];
  readonly metadata?: Record<string, unknown>;
  readonly relationships?: Record<string, unknown>;
  readonly completeness: Record<string, unknown>;
  readonly provenance: Record<string, unknown>;
}

export interface NormalizedEntityV23 extends NormalizedEntityV22 {}

export interface CanonicalRelationshipV21 {
  readonly record_kind: "canonical";
  readonly id: string;
  readonly alias_id: string;
  readonly alias_name: string;
  readonly relationship_type: string;
  readonly from_entity_id: string;
  readonly to_entity_id: string;
  readonly [key: string]: unknown;
}

export interface CompatibilityRelationshipV21 {
  readonly record_kind: "compatibility";
  readonly relationship_id: string;
  readonly assertion_id: string;
  readonly relationship_type: string;
  readonly from_entity_id: string;
  readonly to_entity_id: string;
  readonly [key: string]: unknown;
}

/**
 * v2.2 keeps relationship identity but makes normalized provenance explicit.
 * Topology vocabulary and endpoint rules remain owned by the canonical schema
 * and semantic core; these fields only preserve that contract at the boundary.
 */
export interface CanonicalRelationshipV22 extends CanonicalRelationshipV21 {
  readonly source_owner_id?: string | null;
  readonly source_pointer?: string | null;
  readonly provenance_classification?: "explicit" | "derived" | "heuristic";
  readonly evidence?: readonly string[];
  readonly canonical_source_ref: string;
  readonly confidence?: number;
  readonly extension?: { readonly properties: Record<string, JsonValue>; readonly rationale: string };
}

export interface CompatibilityRelationshipV22 extends CompatibilityRelationshipV21 {
  readonly source_owner_id?: string | null;
  readonly source_pointer?: string | null;
  readonly provenance_classification: "explicit" | "derived" | "heuristic";
  readonly evidence?: readonly string[];
  readonly canonical_source_ref: string;
  readonly confidence?: number;
  readonly metadata?: Record<string, unknown>;
}

export type RelationshipV21 = CanonicalRelationshipV21 | CompatibilityRelationshipV21;
export type RelationshipV22 = CanonicalRelationshipV22 | CompatibilityRelationshipV22;

export interface NormalizedArchitectureModelV21 {
  readonly schema_version: "2.1";
  readonly type: "normalized_architecture_model";
  readonly mode: "normalized" | "legacy";
  readonly scope_root: string;
  readonly architecture_namespace?: string | null;
  readonly fingerprint: string;
  readonly entities: readonly NormalizedEntityV21[];
  readonly relationships: readonly RelationshipV21[];
  readonly unresolved: readonly Record<string, unknown>[];
  readonly [key: string]: unknown;
}

export interface NormalizedArchitectureModelV22
  extends Pick<NormalizedArchitectureModelV21, "type" | "mode" | "scope_root" | "architecture_namespace" | "fingerprint" | "unresolved"> {
  readonly schema_version: "2.2";
  readonly entities: readonly NormalizedEntityV22[];
  readonly relationships: readonly RelationshipV22[];
  readonly validation_summary?: Record<string, unknown> | null;
  readonly source_coverage?: Record<string, unknown> | null;
}

export interface NormalizedArchitectureModelV23
  extends Pick<NormalizedArchitectureModelV22, "type" | "mode" | "scope_root" | "architecture_namespace" | "fingerprint" | "unresolved" | "validation_summary" | "source_coverage"> {
  readonly schema_version: "2.3";
  readonly entities: readonly (NormalizedEntityV23 | NormativePropositionEntityV23)[];
  readonly relationships: readonly RelationshipV22[];
}

export type NormalizedEntity = NormalizedEntityV21 | NormalizedEntityV22 | NormalizedEntityV23 | NormativePropositionEntityV23;
export type Relationship = RelationshipV21 | RelationshipV22;
export type NormalizedArchitectureModel = NormalizedArchitectureModelV21 | NormalizedArchitectureModelV22 | NormalizedArchitectureModelV23;

export type RelationshipDirection = "any" | "incoming" | "outgoing";
export interface RelationshipQuery { readonly relationshipType?: string; readonly direction?: RelationshipDirection; }
