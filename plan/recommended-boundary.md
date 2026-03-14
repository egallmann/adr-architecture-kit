# Recommended Boundary

## Name

Use **Architecture Repository Boundary** as the primary name.

Use **Normalized Architecture Model** for the semantic payload exposed by that
boundary.

## Boundary definition

### `ArchitectureRepository`

The repository boundary is the only supported in-process consumer entry point.
Its responsibilities are:

- load one scope's compiled bundle
- validate contract integrity and semantic consistency
- hide file paths, artifact layout, and registry schema differences
- expose typed queries
- return one stable semantic export: `NormalizedArchitectureModel`

It does **not**:

- parse raw ADRs for consumer workflows
- expose compiler pass internals as a stable contract
- execute graph logic
- perform federation
- merge implementation evidence into architecture state

### `NormalizedArchitectureModel`

The normalized model is the stable semantic view exposed by the repository.
It should contain:

- scope identity
- architecture namespace when available
- normalized entities
- normalized relationships
- unresolved records
- validation summary
- source coverage summary
- deterministic fingerprint

It preserves:

- canonical source references
- non-canonical source refs
- provenance
- unresolved state
- repo-local identifiers

It does not attempt to become:

- a graph query engine
- a runtime supergraph
- a cross-repo federation representation

## Invariants

- ADRs and invariants remain canonical authority
- compiled bundles remain derived contract artifacts
- `ArchModel` remains compiler-internal
- in-process consumers use the repository boundary, not ad hoc registry reads
- unresolveds remain first-class typed records
- provenance is preserved through the semantic boundary

## Relationship to future kernel work

Future graph compilation should consume the normalized model boundary, not
scattered YAML registry files. That lets ADR-Kit stabilize semantics now while
deferring kernel-grade graph behavior.
