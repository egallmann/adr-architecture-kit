import { AmbiguousAliasError, UnsupportedContractVersionError } from "../errors.js";
import type { NormalizedArchitectureModelV21, NormalizedEntityV21, RelationshipQuery, RelationshipV21 } from "./types.js";

function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T; }
function freeze<T>(value: T): T {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const item of Object.values(value as Record<string, unknown>)) freeze(item);
  }
  return value;
}

export interface ArchitectureModelView {
  readonly model: Readonly<NormalizedArchitectureModelV21>;
  entities(): readonly NormalizedEntityV21[];
  relationships(): readonly RelationshipV21[];
  unresolved(): readonly Record<string, unknown>[];
  findEntityByUuid(uuid: string): NormalizedEntityV21 | undefined;
  findEntityByAliasId(aliasId: string): NormalizedEntityV21 | undefined;
  findEntityByAliasRef(aliasRef: string): NormalizedEntityV21 | undefined;
  resolveUri(uri: string): NormalizedEntityV21 | undefined;
  entitiesByType(entityType: string): readonly NormalizedEntityV21[];
  relationshipsForEntity(entityId: string, options?: RelationshipQuery): readonly RelationshipV21[];
  extensionEntities(): readonly NormalizedEntityV21[];
  extensionRelationships(): readonly RelationshipV21[];
  unresolvedForEntity(entityId: string): readonly Record<string, unknown>[];
}

export function createArchitectureModel(input: NormalizedArchitectureModelV21): ArchitectureModelView {
  if (!input || input.schema_version !== "2.1") throw new UnsupportedContractVersionError(String((input as { schema_version?: unknown } | null)?.schema_version ?? "missing"));
  const model = freeze(clone(input));
  const entities = [...model.entities].sort((a, b) => a.id.localeCompare(b.id));
  const relationships = [...model.relationships].sort((a, b) => relationshipKey(a).localeCompare(relationshipKey(b)));
  const alias = (value: string, field: "alias_id" | "alias_ref"): NormalizedEntityV21 | undefined => {
    const found = entities.filter((entity) => entity[field] === value);
    if (found.length > 1) throw new AmbiguousAliasError(value);
    return found[0];
  };
  const view: ArchitectureModelView = {
    model,
    entities: () => Object.freeze([...entities]),
    relationships: () => Object.freeze([...relationships]),
    unresolved: () => Object.freeze([...model.unresolved]),
    findEntityByUuid: (uuid) => entities.find((entity) => entity.id === uuid),
    findEntityByAliasId: (aliasId) => alias(aliasId, "alias_id"),
    findEntityByAliasRef: (aliasRef) => alias(aliasRef, "alias_ref"),
    resolveUri: (uri) => entities.find((entity) => entity.uri === uri),
    entitiesByType: (entityType) => Object.freeze(entities.filter((entity) => entity.entity_type === entityType)),
    relationshipsForEntity: (entityId, options = {}) => Object.freeze(relationships.filter((relationship) => {
      const outgoing = relationship.from_entity_id === entityId;
      const incoming = relationship.to_entity_id === entityId;
      const direction = options.direction ?? "any";
      return (direction === "any" ? outgoing || incoming : direction === "outgoing" ? outgoing : incoming)
        && (!options.relationshipType || relationship.relationship_type === options.relationshipType);
    })),
    extensionEntities: () => Object.freeze(entities.filter((entity) => entity.entity_type.includes(":"))),
    extensionRelationships: () => Object.freeze(relationships.filter((relationship) => relationship.relationship_type.includes(":"))),
    unresolvedForEntity: (entityId) => Object.freeze(model.unresolved.filter((item) => Object.values(item).some((value) => value === entityId))),
  };
  return Object.freeze(view);
}

function relationshipKey(value: RelationshipV21): string {
  return `${value.relationship_type}\u0000${value.from_entity_id}\u0000${value.to_entity_id}\u0000${value.record_kind === "canonical" ? value.id : value.assertion_id}`;
}

export type * from "./types.js";
