# Public surface and stability

`adr-architecture-kit` is a pre-1.0 Alpha package. Production engineering quality
does not constitute a `1.0.0` compatibility declaration, and ADR schema version 1.0
does not determine the package's SemVer major version. Python and TypeScript/Node
share one release lineage, while each host advertises its qualified operations
through `capabilities()`.

## Compatibility categories

### Stable

Stable surfaces have an explicit compatibility promise. The retained ADR v1.0
encoding in `schema/v1.0/`, the supported repository consumer seam
(`ArchitectureRepository` and `NormalizedArchitectureModel`), traceability
decorators, and the documented role of the repository-normalized discovery bundle
are stable. Changes must be backward compatible or follow the removal policy below.

### De facto public

Documented or historically imported surfaces without a formal stable declaration are
de facto public. This includes `adr_kit.__version__`, documented parser, validator,
generator, exception, and CLI behavior, existing diagnostic codes, and existing
compiler exports. Compatibility snapshots and tests protect these surfaces from
accidental removal or shape drift.

`ArchModel` is the important exception: it remains importable from
`adr_kit.compiler` for compatibility, but it is compiler-internal and must not be used
as a new consumer contract.

### Provisional

Provisional surfaces are public enough for careful integration but may evolve before
promotion. They include family-scoped authoring and discovery contracts, governance,
evidence-attribution, normalized-model, external-binding, topology, subset-registry,
architecture-graph, and semantic-linkage surfaces that are advertised by the
installed host. Evidence-attribution v1.5/v1.6 are semantic evidence lines, not ADR
authoring versions. ADC 1.0 discovery is descriptive and does not authorize
semantic construction or mutation.
Provisional material must identify migration impact when it changes and is not promoted
merely by implementation.

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
but existing de facto imports remain compatibility-protected. The supported facade is
the separate `adr_kit.api` module; the package root exposes only `__version__` for
new consumers.

### Supported SDK

`adr_kit.api` is the recommended boundary for new Python integrations.
`adr_kit.api` has an explicit compatibility-tested symbol inventory recorded in
`contracts/compatibility/python-surface.json` and documented in
[Public Python SDK](public-sdk.md). Its API contract version is `1.0`. Public
annotations and returned object graphs exclude compiler internals. Use
`capabilities()` for the current operation and contract surface; the compatibility
contract remains the exact source for symbol inventory and shape.

### TypeScript consumer binding

`@system-of-thought/adr-kit` is the official TypeScript host/browser binding.
It is governed by Consumer Binding Contract 1.0 and ADR-L-0027. The Node host
profile is a peer to Python for supported filesystem-backed capabilities; the
browser-safe entry points are a deliberately constrained framework-neutral ESM
profile, not a third filesystem host. TypeScript and Python fingerprints are
binding-local and are not required to match.

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
- Moving to `1.0.0` requires an explicit compatibility review; this policy does not
  make that declaration.

The release tag must be `v<PEP 440 project version>`. `pyproject.toml` is the only
manually edited package-version authority. Installed metadata, `adr_kit.__version__`,
`adr --version`, SDK capabilities, and SDK results must agree. Direct-source execution
falls back to validated project metadata; an invalid or unavailable source reports the
explicit non-release sentinel `0+unknown`.

## Surface-specific rules

- ADR v1.0 encoding is stable. Family-scoped authoring, discovery, governance,
  normalized-model, and attribution materials remain provisional unless the
  installed host and its compatibility contract qualify them otherwise. Attribution
  evidence v1.5/v1.6 are semantic-claim lines; neither is an ADR authoring schema.
  ADC 1.0 is a descriptive discovery contract and does not imply construction.
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
- Use `adr_kit.api` or the qualified Node host entry points for new integrations.
  Ask `capabilities()` before selecting a versioned operation.
- Existing direct
  `ArchitectureRepository` and `NormalizedArchitectureModel` consumers remain
  supported; use the documented generated file contract only when Python is not
  available.
- Treat `ste-spec` as the normative owner of cross-repository Architecture IR.
- Avoid new dependencies on `ArchModel`, compiler internals, provisional graph shape,
  or experimental surfaces.

See the [public-surface inventory](production-hardening/public-surface-inventory.md)
for the frozen compatibility snapshot and [authority-boundary.md](authority-boundary.md)
for repository ownership.
