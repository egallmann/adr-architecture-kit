# ADR placement convention

Placement is scoped by `PROJECT.yaml` and resolved by
`ProjectScopeResolver`. A scope owns its `adrs/` directory, manifest, source
records, and generated projections.

## Current source paths

```text
<scope>/adrs/logical/             ADR-L sources
<scope>/adrs/physical-system/     ADR-PS sources
<scope>/adrs/physical-component/  ADR-PC sources
<scope>/adrs/manifest.yaml        generated scope manifest
<scope>/adrs/index/               generated discovery registries and indexes
```

Legacy `adrs/physical/` remains a compatibility input path for readers and
migrators. It is not the recommended placement for new physical-system or
physical-component records.

## Scope configuration

When `PROJECT.yaml` declares `architecture_documentation.adr_directory` or
`manifest_path`, resolve those paths relative to the scope root. Do not derive
paths from the caller's current working directory or write into a parent
workspace.

Use the resolver and repository-owned commands when creating or regenerating
artifacts:

```bash
adr generate-manifest --scope .
adr generate-architecture-index --scope .
```

Generated files are derived projections. Canonical ADR source and contract
inputs must be changed first; projections must be regenerated and validated.
