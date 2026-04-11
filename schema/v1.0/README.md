# ADR Kit JSON Schema v1.0

`schema/v1.0/` is the stable public ADR encoding contract surface for `adr-architecture-kit`.

These schemas define the v1 ADR frontmatter and artifact model owned by this repository. They do not define the normative public cross-repo Architecture IR contract. That contract belongs to `ste-spec`.

## Stable v1 scope

- `types.schema.json`
- `adr-common.schema.json`
- `adr-logical.schema.json`
- `adr-physical.schema.json`
- `adr-physical-system.schema.json`
- `adr-physical-component.schema.json`
- `adr-physical-base.schema.json`
- `invariant.schema.json`
- `project-metadata.schema.json`
- `manifest.schema.json`

## What v1.0 means here

v1.0 is the stable public encoding line for:

- ADR frontmatter
- ADR type taxonomy
- canonical authoring fields
- project metadata
- manifest encoding

## Relationship to other layers

- ADR YAML defined by these schemas is canonical source authority for this repository
- repository-normalized discovery outputs are generated from those sources
- public cross-repo Architecture IR remains owned by `ste-spec`

## Consumption guidance

- Depend on these schemas when authoring or validating ADR artifacts
- Do not use these schemas as a proxy for the `ste-spec` Architecture IR contract
- Prefer `ADR-L`, `ADR-PS`, and `ADR-PC` as the main public modeling forms
- Treat legacy `ADR-P` as compatibility-oriented

## Related

- [../../docs/adr-type-model.md](../../docs/adr-type-model.md)
- [../../docs/architecture-ir-overview.md](../../docs/architecture-ir-overview.md)
