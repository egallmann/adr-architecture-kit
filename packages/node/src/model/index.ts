import { AmbiguousAliasError, UnsupportedContractVersionError } from "../errors.js";
import type { NormalizedArchitectureModel, Relationship, RelationshipQuery } from "./types.js";

type ModelEntity<TModel extends NormalizedArchitectureModel> = TModel["entities"][number];
type ModelRelationship<TModel extends NormalizedArchitectureModel> = TModel["relationships"][number];

function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T; }
function freeze<T>(value: T): T {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const item of Object.values(value as Record<string, unknown>)) freeze(item);
  }
  return value;
}

export interface ArchitectureModelView<TModel extends NormalizedArchitectureModel = NormalizedArchitectureModel> {
  readonly model: Readonly<TModel>;
  entities(): readonly ModelEntity<TModel>[];
  relationships(): readonly ModelRelationship<TModel>[];
  unresolved(): readonly Record<string, unknown>[];
  findEntityByUuid(uuid: string): ModelEntity<TModel> | undefined;
  findEntityByAliasId(aliasId: string): ModelEntity<TModel> | undefined;
  findEntityByAliasRef(aliasRef: string): ModelEntity<TModel> | undefined;
  resolveUri(uri: string): ModelEntity<TModel> | undefined;
  entitiesByType(entityType: string): readonly ModelEntity<TModel>[];
  relationshipsForEntity(entityId: string, options?: RelationshipQuery): readonly ModelRelationship<TModel>[];
  extensionEntities(): readonly ModelEntity<TModel>[];
  extensionRelationships(): readonly ModelRelationship<TModel>[];
  unresolvedForEntity(entityId: string): readonly Record<string, unknown>[];
}

export function createArchitectureModel<TModel extends NormalizedArchitectureModel>(input: TModel): ArchitectureModelView<TModel> {
  const version = (input as { schema_version?: unknown } | null)?.schema_version;
  if (!input || (version !== "2.1" && version !== "2.2")) throw new UnsupportedContractVersionError(String(version ?? "missing"));
  const model = freeze(clone(input));
  const entities = [...model.entities].sort((a, b) => a.id.localeCompare(b.id)) as ModelEntity<TModel>[];
  const relationships = [...model.relationships].sort((a, b) => relationshipKey(a).localeCompare(relationshipKey(b))) as ModelRelationship<TModel>[];
  const unresolved = model.unresolved as readonly Record<string, unknown>[];
  const alias = (value: string, field: "alias_id" | "alias_ref"): ModelEntity<TModel> | undefined => {
    const found = entities.filter((entity) => entity[field] === value);
    if (found.length > 1) throw new AmbiguousAliasError(value);
    return found[0];
  };
  const view: ArchitectureModelView<TModel> = {
    model,
    entities: () => Object.freeze([...entities]),
    relationships: () => Object.freeze([...relationships]),
    unresolved: () => Object.freeze([...unresolved]),
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
    unresolvedForEntity: (entityId) => Object.freeze(unresolved.filter((item) => Object.values(item).some((value) => value === entityId))),
  };
  return Object.freeze(view);
}

function relationshipKey(value: Relationship): string {
  return `${value.relationship_type}\u0000${value.from_entity_id}\u0000${value.to_entity_id}\u0000${value.record_kind === "canonical" ? value.id : value.assertion_id}`;
}

export type * from "./types.js";
