# Consumer semantic extensions

Authoring schema v1.4 admits `extension_entities` and
`extension_relationships`. Every consumer type is qualified as
`<architecture_namespace>:<local_type>` and carries bounded scalar properties
plus required rationale. ADR-Kit validates the envelope and preserves the
consumer payload; it does not interpret the type or infer graph edges.

Consumers own their alias-prefix allocation state. ADR-Kit reuses the canonical
allocation contract and validates a consumer-supplied registration, but the
ADR-Kit repository ledger is not a registry for external consumers.

Normalized model v2.1 represents extension payloads explicitly:

```yaml
extension:
  properties: { ... }
  rationale: ...
```

Canonical relationships have persisted UUIDv7 `id` values. Legacy hash
`relationship_id`/`assertion_id` values are available only on the named
compatibility projection and cannot enter canonical graph state.
