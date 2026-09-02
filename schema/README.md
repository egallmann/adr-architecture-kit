# ADR-Kit canonical schema taxonomy

`schema/` is the canonical repository authority for JSON contract bytes. The
family-first layout gives each contract family an independently meaningful
version namespace:

- `v1.0/` is the retained stable authoring compatibility exception.
- `authoring/v1.2/`, `authoring/v1.3/`, `authoring/v1.4/`, and `authoring/v1.5/` contain ADR authoring contracts.
- `architecture-discovery/v1.1/` contains discovery indexes and the legacy
  entity registry.
- `normalized-model/v1.1/` and `normalized-model/v2.0/` contain normalized
  model contracts.
- `governance/v1.1/` contains governance ledgers and review contracts.
- `evidence-attribution/v1.1/` and `evidence-attribution/v1.5/` contain
  evidence and attribution contracts. v1.5 is semantic attribution evidence,
  not ADR authoring schema v1.5 and not a normalized model version.
- `kernel/` and `migrations/` remain special families.

The installed package namespace is intentionally asymmetric:
`src/adr_kit/schema/v1_0/` through `v1_4/` remain authoring package mirrors;
ADR authoring v1.5 is family-qualified at `src/adr_kit/schema/authoring/v1_5/`
(`adr_kit.schema.authoring.v1_5`) so it does not collide with evidence
attribution `src/adr_kit/schema/v1_5/`. `v1_6/`, `v2_0/`, `v2_1/`, and
`migrations/` remain the other package resource locations. The test inventory is a
non-authoritative verification snapshot, not another schema authority.
