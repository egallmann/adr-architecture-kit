# ADR-Kit canonical schema taxonomy

`schema/` is the canonical repository authority for JSON contract bytes. The
family-first layout gives each contract family an independently meaningful
version namespace:

- `v1.0/` is the retained stable authoring compatibility exception.
- `authoring/v1.2/` and `authoring/v1.3/` contain ADR authoring contracts.
- `architecture-discovery/v1.1/` contains discovery indexes and the legacy
  entity registry.
- `normalized-model/v1.1/` and `normalized-model/v2.0/` contain normalized
  model contracts.
- `governance/v1.1/` contains governance ledgers and review contracts.
- `evidence-attribution/v1.1/` and `evidence-attribution/v1.5/` contain
  evidence and attribution contracts. v1.5 is semantic attribution evidence,
  not ADR authoring schema v1.5 and not a normalized model version.
- `kernel/` and `migrations/` remain special families.

The installed package namespace is intentionally asymmetric and unchanged:
`src/adr_kit/schema/v1_0/`, `v1_1/`, `v1_2/`, `v1_3/`, `v1_5/`, `v2_0/`, and
`migrations/` remain the package resource locations. The test inventory is a
non-authoritative verification snapshot, not another schema authority.
