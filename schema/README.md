# ADR-Kit canonical schema taxonomy

`schema/` contains the canonical JSON contract bytes shipped or mirrored by
ADR-Kit. Each family has its own version namespace; a number in one family does
not imply the same version in another.

- `v1.0/` is the retained stable ADR authoring compatibility line.
- `authoring/v1.2/` through `authoring/v1.6/` are family-scoped ADR authoring
  contracts. They are separate from the stable v1.0 line.
- `architecture-discovery/` contains repository discovery contracts.
- `normalized-model/` contains normalized semantic output contracts.
- `governance/` contains governance and review contracts.
- `evidence-attribution/` contains implementation-linkage evidence contracts.
  Evidence attribution v1.5 and v1.6 are not ADR authoring versions.
- `kernel/` and `migrations/` are specialist contract families.

The independent language-neutral Authoring Domain Contract (ADC) describes
authoring concepts and discovery operations. It is not another persistence
schema line. The installed Python and TypeScript/Node bindings report their
qualified schema and contract support through `capabilities()`; use that
manifest instead of treating this taxonomy as a release capability inventory.

Package resource paths are intentionally asymmetric where authoring and evidence
versions would otherwise collide. The bundled mirrors are checked for parity;
the canonical files in this directory remain the schema authority.
