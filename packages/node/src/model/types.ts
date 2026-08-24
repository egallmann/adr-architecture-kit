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

export type RelationshipV21 = CanonicalRelationshipV21 | CompatibilityRelationshipV21;

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

export type RelationshipDirection = "any" | "incoming" | "outgoing";
export interface RelationshipQuery { readonly relationshipType?: string; readonly direction?: RelationshipDirection; }
