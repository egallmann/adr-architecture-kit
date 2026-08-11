# Schema v1.3 — Canonical Entity Identity

Schema v1.3 is the provisional ADR authoring line for UUID canonical identity.

## Identity envelope

Admitted identity-bearing records author:

- `id` — lowercase RFC 9562 UUIDv7 (canonical machine identity)
- `alias_id` — governed type-prefixed identifier (for example `ADR-L-0019`, `INV-0094`)
- `alias_name` — stable mnemonic matching `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$` (3–96)

Do not author `alias_ref`, logical URI, identity `created_at`, or `updated_at`.

## Provider namespace

`architecture_namespace` is declared once by the provider through `PROJECT.yaml`
(`architecture_documentation.architecture_namespace`). ADR documents consume that
context; they do not author a second namespace-authority field.

Derived URI shape:

`adr://<architecture_namespace>/entities/<uuid>`

## References

Local canonical references are UUIDv7 strings. External references carry
provider namespace, UUID, kind, and `sha256:<64 hex>` fingerprint.

## Physical-system records

Physical-system ADRs require exactly one authored `system` object with UUID
identity and a preserved `SYS-####` alias.

## Compatibility

- v1.0 remains byte-frozen and readable
- v1.2 remains readable and migratable
- Normalized model 2.0 is emitted for all-v1.3 scopes
- Mixed legacy/v1.3 scopes fail closed

See also [identity-v13-migration.md](identity-v13-migration.md) and
[public-sdk.md](public-sdk.md).
