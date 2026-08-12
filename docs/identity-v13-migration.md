# Identity v1.3 Migration

Migrate legacy ADR authoring (v1.0 / v1.2) to schema v1.3 UUID identity.

## Lifecycle

```text
preflight
  → plan (mint once into a complete candidate map)
  → review/seal (close judgment queues; fingerprint the map)
  → apply exactly the sealed map
  → check / recover (never remint)
```

UUIDv7 minting is a state-creation event. Deterministic replay begins after the
map is sealed. A fresh `--plan` before seal may mint a new candidate; that is
not sealed-map replay.

## CLI

```bash
adr migrate-identity-v13 --scope . --plan-out /tmp/identity-plan.yaml
# review/seal the plan (programmatic IdentityV13Migrator.seal or reviewed YAML)
adr migrate-identity-v13 --scope . --identity-map /tmp/identity-sealed.yaml --apply
adr migrate-identity-v13 --scope . --identity-map adrs/migrations/canonical-identity-v13-map.yaml --check
```

Apply consumes the sealed map fingerprint and rejects open judgment queues,
baseline drift, or fingerprint mismatch. Failed preflight never mints.

## Map evidence

The identity map records architecture namespace, baseline fingerprint, complete
occurrence inventory, UUID/alias assignments, source-owner mappings, review
disposition, and the sealed map fingerprint. Canonical persistence path:

`adrs/migrations/canonical-identity-v13-map.yaml`

## ADR Kit dogfood

ADR Kit’s own corpus was migrated from 31×v1.0 + ADR-L-0019@v1.2 to uniform
v1.3. Semantic parity preserves 326 projected entities and 404 relationships
under model 2.0 after inverse UUID substitution. Authored systems preserve
`SYS-0001` / `SYS-0002` aliases.

## External providers

External references require provider-authoritative v1.3 maps and comparable
fingerprints; otherwise migration reports blockers rather than guessing.
