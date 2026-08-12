# Schema v2.0 — Normalized Semantic Model with UUID Identity

Model 2.0 schemas describe the normalized semantic output produced by the
compiler when all source ADRs use schema v1.3 with canonical UUID identity.

- `normalized-entity.schema.json` — entity with UUIDv7 `id`, alias, URI, fingerprint
- `relationship-record.schema.json` — relationship with UUID endpoints and `source_owner_id`
- `normalized-entity-registry.schema.json` — entity registry wrapper
- `relationship-registry.schema.json` — relationship registry wrapper
- `normalized-architecture-model.schema.json` — top-level model envelope

Model 1.1 registries remain unchanged for v1.0/v1.2 scopes.
