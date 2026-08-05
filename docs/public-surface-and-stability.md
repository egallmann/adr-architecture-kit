# Public surface and stability

`adr-architecture-kit` is a pre-1.0 Alpha package. Production engineering quality
does not constitute a `1.0.0` compatibility declaration, and ADR schema version 1.0
does not determine the package's SemVer major version.

## Compatibility categories

### Stable

Stable surfaces have an explicit compatibility promise. In the current package these
are the ADR v1.0 encoding in `schema/v1.0/`, the supported repository consumer seam
(`ArchitectureRepository` and `NormalizedArchitectureModel`), traceability decorators,
and the documented role of the repository-normalized discovery bundle. Changes must
be backward compatible or follow the removal policy below.

### De facto public

Documented or historically imported surfaces without a formal stable declaration are
de facto public. This includes `adr_kit.__version__`, documented parser, validator,
generator, exception, and CLI behavior, existing diagnostic codes, and existing
compiler exports. Phase 0 snapshots these surfaces and prevents accidental removal or
shape drift.

`ArchModel` is the important exception: it remains importable from
`adr_kit.compiler` for compatibility, but it is compiler-internal and must not be used
as a new consumer contract.

### Provisional

Provisional surfaces are public enough for careful integration but may evolve before
promotion. They include `schema/v1.1/`, discovery/ledger/lifecycle/remediation
extensions, normalized fields outside the core consumer seam, subset registries, and
the additive architecture graph. Provisional material must identify migration impact
when it changes and is not promoted by Phase 0.

### Experimental

Experimental surfaces may change or disappear without a compatibility period. These
include vision materials, migrators, `ADR-L-9000`, workspace boot-publication examples,
and self-publication scripts. They are unsuitable as foundations for external
dependencies.

### Deprecated

A deprecated surface remains functional during its documented compatibility window.
Deprecation must include a warning where practical, a supported replacement, migration
instructions, and the earliest permitted removal version. Deprecation does not itself
authorize removal.

### Internal

Compiler passes, IR, emitters, renderers, orchestration plumbing, and other modules not
classified above are internal/reference implementation. Their behavior can evolve,
but existing de facto imports are still protected from accidental Phase 0 breakage.
No new root exports or SDK facade are created in Phase 0.

### Generated compatibility

Committed registries, manifest, architecture index, rendered ADRs, system overview,
goldens, integrity headers, fingerprints, diagnostic shapes, and package-data mirrors
are derived, not authoritative. Nevertheless, deterministic shape and freshness are
compatibility-relevant. Change canonical artifacts first and regenerate only with the
repository-owned commands; never edit a projection directly.

## Pre-1.0 SemVer policy

- Patch releases may fix defects and add controls without changing documented behavior.
- Minor releases may add backward-compatible public behavior and may revise provisional
  or experimental surfaces with migration notes.
- Breaking a stable or de facto public surface requires an explicit ADR decision,
  release notes, migration guidance, and a deprecation window unless a documented
  security or correctness emergency makes that impossible.
- Moving to `1.0.0` requires an explicit compatibility review; Phase 0 does not make
  that declaration.

The release tag must be `v<PEP 440 project version>`. Project metadata,
`adr_kit.__version__`, installed metadata, and `adr --version` must agree. Runtime
version sourcing from `importlib.metadata` is mandatory Phase 1 work; Phase 0 preserves
the literal runtime behavior at `0.1.0` and adds a drift guard.

## Surface-specific rules

- ADR v1.0 encoding is stable. ADR v1.1 discovery, ledger, graph, and attribution
  material remains provisional or draft.
- Existing CLI command names, options, defaults, exit codes, diagnostics, and
  machine-readable shapes are de facto public. Additive developer controls do not
  redefine existing commands.
- Existing diagnostic codes must not be reused for a different meaning. Removal or
  renaming follows the same migration rules as CLI behavior.
- Generated-artifact changes require canonical authority changes, regeneration,
  schema/golden/freshness validation, and a deterministic second run.
- Package schemas and templates are distribution data and must load through
  `importlib.resources` from the installed wheel.
- Migration documentation and changelog entries are required for compatibility-impacting
  changes before release.

## Practical consumption

- Depend on `schema/v1.0/` for stable ADR encoding.
- Use `ArchitectureRepository` and `NormalizedArchitectureModel` for in-process
  consumption; use the documented generated file contract only when Python is not
  available.
- Treat `ste-spec` as the normative owner of cross-repository Architecture IR.
- Avoid new dependencies on `ArchModel`, compiler internals, provisional graph shape,
  or experimental surfaces.

See the [Phase 0 public-surface inventory](production-hardening/public-surface-inventory.md)
for the frozen compatibility snapshot and [authority-boundary.md](authority-boundary.md)
for repository ownership.
