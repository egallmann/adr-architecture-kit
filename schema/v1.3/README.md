# ADR Schema v1.3 — Canonical Entity Identity

Schema v1.3 introduces the canonical entity identity model defined by
ADR-L-0019.  Key changes from v1.2:

- **UUIDv7 canonical identity** — every admitted identity-bearing record
  uses a lowercase RFC 9562 UUIDv7 in the `id` field.
- **Governed aliases** — `alias_id` (type-prefixed, e.g. `ADR-L-0001`)
  and `alias_name` (kebab-case human-friendly) are required alongside
  the UUID.
- **UUID-based references** — `related_adrs`, `supersedes`, entity
  cross-references, and relationship endpoints use UUIDs.
- **External references** — `namespace` + UUIDv7 `id` + `kind` +
  `fingerprint` (SHA-256 over RFC 8785 JCS).
- **Standalone invariants retired** — `invariant.schema.json` is not
  included in v1.3.
- **Physical-system `system` object** — an authored `system` identity
  envelope with `id`/`alias_id`/`alias_name`.

Schemas in this directory are the canonical authority; the package
mirror under `src/adr_kit/schema/v1_3/` must be kept byte-identical.
