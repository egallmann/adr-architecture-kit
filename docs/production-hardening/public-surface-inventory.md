# Phase 0 public-surface inventory

Snapshot date: 2026-08-05  
Package: `adr-architecture-kit==0.1.0`

This inventory records the surface that Phase 0 must preserve. “Stable” below refers
to the compatibility category in `public-surface-and-stability.md`; it does not imply
that the pre-1.0 package has declared SemVer 1.0 compatibility.

## Python surface

| Surface | Category | Phase 0 obligation |
| --- | --- | --- |
| `adr_kit.__version__` | De facto public | Preserve `0.1.0`; enforce metadata/CLI equality |
| `adr_kit.repository.ArchitectureRepository` | Stable | Preserve import and behavior |
| `adr_kit.repository.ArchitectureRegistryError` | Stable exception | Preserve type and failure role |
| `adr_kit.repository.ContractBundleView` | Stable supporting type | Preserve import and fields |
| `adr_kit.models.NormalizedArchitectureModel` | Stable | Preserve shape, queries, and fingerprint semantics |
| `adr_kit.parser.ADRParser`, `ADRParseError`, `ADRSchemaValidationError` | De facto public | Preserve documented imports and diagnostic behavior |
| `adr_kit.validators.*` exported validators/results | De facto public | Preserve imports and validation behavior |
| `adr_kit.generators.*` exported generators | De facto public | Preserve imports; generated compatibility rules apply |
| `adr_kit.decorators.implements_adr`, `implements_adrs`, `enforces_invariant`, `enforces_invariants` | Stable traceability surface | Preserve call signatures and no-op metadata semantics |
| `adr_kit.compiler.ArchModel` and other compiler exports | Compatibility-preserved internal/deep imports | Do not remove in Phase 0; do not recommend for new consumers |
| `adr_kit.compiler.*`, backend/frontend/pass/IR modules | Internal/reference implementation | No new stability promise; existing tests protect accidental breakage |
| `adr_kit.migrators.*` | Experimental | No compatibility promise |

The package root intentionally exports no new facade, compiler result, repository
type, or normalized-model type in Phase 0.

## CLI surface

The console entry point is `adr = adr_kit.cli.main:cli`. Global options are
`--help` and `--version`. Existing command names are:

| Command family | Commands | Output and exit contract |
| --- | --- | --- |
| Validation/governance | `validate`, `validate-contract`, `validate-generated-docs`, `validate-project-metadata`, `validate-system-overview`, `governance-checks`, `audit-runtime` | Human-readable diagnostics; machine-readable YAML where already provided; zero on success, nonzero on validation/control failure |
| Compilation/projection | `compile`, `compile-ir-fragments`, `build-ir-fragments` | Preserve options, default emission, artifact shape, diagnostics, and exit behavior |
| Generation | `generate-architecture-index`, `generate-entity-registry`, `generate-manifest`, `generate-rendered-docs`, `generate-system-overview` | Preserve paths, output shapes, integrity headers, and success/failure behavior |
| Authoring helpers | `generate-logical`, `generate-physical-component`, `generate-physical-system`, `generate-vision`, `scaffold`, `next-id`, `normalize-canonical-ids` | Preserve names, prompts/options, generated ADR v1.0 shape, and exit behavior |
| Discovery | `entities`, `scope` | Preserve subcommands, default human-readable output, machine-readable shapes, and exit behavior |
| Attribution | `attribution check`, `coverage`, `workspace-report`, `generate-shim` | Preserve YAML shapes and validation exit behavior |

Phase 0 adds developer commands/scripts for ratchets, release manifests,
installed-wheel verification, and benchmarks only. It does not rename or reinterpret
the CLI above. Compatibility snapshots cover command/option identity and representative
output/exit contracts.

## Compiler, repository, exceptions, and diagnostics

| Kind | Current contract |
| --- | --- |
| Consumer seam | `ArchitectureRepository` returning `NormalizedArchitectureModel` |
| Compiler IR | `ArchModel`; internal despite historical export from `adr_kit.compiler` |
| Compiler result types | Existing `CompilationResult`, statistics, artifacts, scoped/workspace results; compatibility preserved, no replacement introduced |
| Diagnostics | Existing `Diagnostic`, `DiagnosticLevel`, `DiagnosticLog` and current CLI diagnostic codes/messages |
| Repository failures | Missing/malformed/out-of-scope bundles fail closed through existing repository exceptions and validation results |

Diagnostic codes already emitted in structured or machine-readable output are de facto
public. Phase 0 may add codes for new developer controls but does not rename or reuse an
existing code with different meaning.

## Schemas and package data

| Path/resource | Category | Obligation |
| --- | --- | --- |
| `schema/v1.0/*.json` | Stable ADR encoding | Backward-compatible changes only; canonical source |
| `adr_kit.schema.v1_0/*.json` | Generated/package mirror | Byte parity with canonical v1.0 files |
| `schema/architecture-discovery/v1.1/`, `schema/governance/v1.1/`, `schema/evidence-attribution/v1.1/`, `schema/normalized-model/v1.1/*.json` | Provisional/draft | No promotion during Phase 0 |
| `adr_kit.schema.v1_1/*.json` | Generated/package mirror | Byte parity with canonical v1.1 files |
| `adr_kit.templates/*.jinja2` | Package data, de facto public | Must exist and load through `importlib.resources` in a clean wheel |
| `contracts/architecture-ir/*` | Mirrored sibling contract | Guarded mirror; `ste-spec` remains authoritative |

## Generated artifacts and graph shape

| Artifact | Compatibility posture |
| --- | --- |
| `adrs/manifest.yaml` | Generated compatibility surface; deterministic content and integrity metadata |
| `adrs/index/architecture-index.yaml` | Cross-language bootstrap/discovery surface |
| entity, relationship, unresolved, decision, capability, component, invariant, and system registries | Generated compatibility surfaces; required/additive status remains as already documented |
| `adrs/index/architecture-graph.yaml` | Additive draft graph projection; no redesign or promotion in Phase 0 |
| `adrs/rendered/*.md` and `SYSTEM-OVERVIEW.md` | Derived documentation with integrity/freshness validation |
| golden fixtures | Regression evidence generated only by the approved refresh script |

Existing graph node/edge identity, ordering, optionality, and serialization are frozen
for Phase 0. Integrity headers, timestamps/fixed time behavior, source references,
fingerprints, and manifest metadata are compatibility-relevant.

## Version and distribution metadata

| Source | Current value | Phase 0 rule |
| --- | --- | --- |
| `pyproject.toml` project version | `0.1.0` | Packaging authority for release/tag comparison |
| `adr_kit.__version__` | `0.1.0` | Preserve runtime behavior; compare automatically |
| installed metadata | `0.1.0` | Must equal project/runtime/CLI values |
| `adr --version` | `0.1.0` | Must equal the other three sources |
| Release tag | none in current workflow | Phase 0 requires `v<PEP 440 project version>` |
| Distribution set | one wheel and one sdist | Exact cardinality required by manifest verification |

## Deprecated, provisional, experimental, and internal surfaces

- No surface is removed in Phase 0.
- family-scoped v1.1 discovery, ledger/lifecycle/remediation extensions, subset registries, and the
  additive graph remain provisional.
- migrators, vision ADRs, boot-publication examples, and self-publication scripts
  remain experimental.
- compiler pipeline, pass, IR, emitter, and renderer modules remain internal/reference
  implementation even where historical imports are compatibility-preserved.
- `ArchModel` is the central documented contradiction: import compatibility is
  retained, but it is not the supported consumer model.
- No deprecation clock starts without documentation, migration guidance, and the
  pre-1.0 removal rules defined by policy.
