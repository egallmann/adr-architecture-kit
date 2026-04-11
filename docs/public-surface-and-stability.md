# Public surface and stability

## Stable

The following are the intended **stable public v1** surfaces for `adr-architecture-kit`:

- ADR v1.0 schemas in `schema/v1.0/`
- ADR frontmatter model and type taxonomy
- parser and validator behavior for canonical ADR and invariant artifacts
- the existence and role of the repository-normalized discovery bundle
- `ArchitectureRepository`
- `NormalizedArchitectureModel`
- the rule that `ArchModel` is compiler-internal
- ADR-to-Architecture-IR adapter semantics, with `ste-spec` owning the normative schema

## Draft

These surfaces are public but not yet declared shape-stable:

- `schema/v1.1/`
- normalized registry field evolution beyond the core bundle identity
- additive graph and subset registry details
- logical ADR IR adapter profile version details
- lifecycle, remediation, and ledger extensions

**Draft** means:

- useful to review and consume carefully
- expected to evolve
- not yet promised as a long-term stable contract

## Experimental

These areas are intentionally outside the stable public v1 contract:

- `ADR-V-*` vision materials
- `src/adr_kit/migrators/`
- `ADR-L-9000` and workspace boot publication examples
- `scripts/publish_architecture_ir_fragments.py`
- older strategy or ecosystem-future material that depends on a shared workspace narrative

**Experimental** means:

- present for exploration or internal evolution
- not guaranteed to remain
- not appropriate as the foundation for new external dependencies

## Reference implementation surface

The following are public **reference implementation** assets rather than normative contracts:

- compiler pipeline internals
- registry and projection emitters
- manifest generation
- rendered markdown generation
- CLI orchestration
- integrity and freshness validation

These are useful and supported, but external users should depend on the **declared public surface** rather than on internal implementation details.

## Practical consumption rules

- Depend on `schema/v1.0/` for stable ADR encoding contracts.
- Use `ArchitectureRepository` or the repository-normalized bundle for repository-local consumer workflows.
- Treat `ste-spec` as the only normative owner of the cross-repo Architecture IR schema.
- Avoid taking new dependencies on experimental surfaces.

## Related

- [authority-boundary.md](authority-boundary.md)
- [architecture-ir-overview.md](architecture-ir-overview.md)
