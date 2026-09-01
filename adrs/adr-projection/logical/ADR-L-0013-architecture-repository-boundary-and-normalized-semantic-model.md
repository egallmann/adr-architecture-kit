<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: c7c2d22657d60d0ce69bffc1a9e5f81d8967921c513f4de8904d8fed2572c216
rendered_hash: 85565b4169893700aa5a31a60b0e81c5df0f28cee87c9967d5322ed6b0222e76
-->

# ADR-L-0013: Architecture Repository Boundary and Normalized Semantic Model

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0013  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-14  
**Modified:** 2026-08-06  
**Authors:** adr-architecture-kit  
**Domains:** repository, discovery, compiler, kernel  
**Tags:** repository-boundary, semantic-model, archmodel, registries  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0013 |
| Status | accepted |
| Decisions | 10 |
| Capabilities | 3 |
| Invariants | 4 |
| Physical realizations | [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0004](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md), [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md), [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) |


## Context

adr-architecture-kit now has an explicit compiler pipeline, a compiler IR
(`ArchModel`), compiled registry bundles, and an additive architecture graph.
Those pieces are sufficient to produce deterministic machine-facing artifacts,
and ArchitectureRepository already defines the semantic in-process boundary.
Phase 1 adds a narrow supported authoring facade that reuses that seam without
expanding the normalized model or exposing compiler internals.

Without that boundary, in-process tools can drift into reading raw registries
directly, interpreting relationships independently, and coupling future
kernel or graph consumers to current file layouts and registry schemas. That
would undermine determinism, make schema evolution expensive, and allow
semantic drift between canonical ADR authority and downstream machine
consumers.

A stabilizing move is needed now while the system is still small enough to
evolve safely: one repository boundary that loads compiled artifacts and
exposes one stable semantic model to in-process consumers, while still making
the cross-language file-format contract explicit for consumers that cannot
call Python repository APIs.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0050 | Use ArchitectureRepository as the supported in-process semantic entry point with UUID, governed alias, and logical URI lookup | — |
| DEC-0051 | Adopt NormalizedArchitectureModel 2.0 as the v1.3 repository semantic payload | — |
| DEC-0052 | Keep ArchModel compiler-internal and do not promote it to the public consumer API | — |
| DEC-0061 | Permit direct `adrs/index/*` consumption for cross-language or out-of-process consumers | — |
| DEC-0062 | Treat repository-backed graph access as the intended Python graph seam | — |
| DEC-0067 | Define an index-first minimal runtime ingestion subset for cross-language architecture consumers | — |
| DEC-0068 | Require cross-language runtime ingestion to remain index-first, manifest-aware, and additive-safe | — |
| DEC-0079 | Preserve the present repository seam and defer any narrow consumer facade | — |
| DEC-0080 | Establish adr_kit.api as the narrow supported authoring SDK facade | — |
| DEC-0082 | Keep repository-local authoring projections separate from workspace runtime state | — |

### DEC-0050 — Use ArchitectureRepository as the supported in-process semantic entry point with UUID, governed alias, and logical URI lookup

**Rationale**

The repository boundary centralizes scope-safe loading, contract
validation, path hiding, and registry compatibility adaptation. This keeps
consumers from binding directly to registry files and current layout.

Repository lookup/resolution supports UUID, governed aliases, and logical URI forms while canonical machine operations resolve to UUID.

**Consequences**

Positive:
- Consumer logic stops duplicating bundle loading behavior
- Registry schema and layout evolution can be absorbed behind one boundary
- Future kernel consumers can target one trusted seam

### DEC-0051 — Adopt NormalizedArchitectureModel 2.0 as the v1.3 repository semantic payload

**Rationale**

A semantic model is needed so consumers depend on architecture meaning
rather than current registry document shapes. The model must preserve
entities, relationships, unresolved records, provenance, scope identity,
and deterministic fingerprinting.

V1.3 authority advances normalized semantics to model 2.0 with UUID
identities and endpoints, explicit UUID/alias lookup, and versioned
compatibility adapters. Embodiment of that contract is subsequent v1.3
implementation work.

**Consequences**

Positive:
- Consumers use one typed semantic contract
- Future graph compilation has a stable landing zone
- Unresolved and provenance semantics remain explicit

### DEC-0052 — Keep ArchModel compiler-internal and do not promote it to the public consumer API

**Rationale**

The current `ArchModel` is the compiler IR. It reflects pass orchestration
and extraction concerns and may evolve as compiler internals change. Making
it the public consumer contract would freeze the wrong abstraction too
early.

**Consequences**

Positive:
- Compiler internals remain evolvable
- Consumer semantics stay narrower and more stable
- ADR-Kit avoids becoming an accidental proto-kernel

### DEC-0061 — Permit direct `adrs/index/*` consumption for cross-language or out-of-process consumers

**Rationale**

Cross-language consumers such as `ste-runtime` cannot call a Python
repository API directly. They still consume the same generated authority
surface, but through the file-format contract rather than the in-process
repository seam.

### DEC-0062 — Treat repository-backed graph access as the intended Python graph seam

**Rationale**

Python consumers should not hardcode the graph artifact path once the
repository boundary can expose it as part of the indexed contract family.
This preserves a coherent semantic seam for in-process consumers.

### DEC-0067 — Define an index-first minimal runtime ingestion subset for cross-language architecture consumers

**Rationale**

Cross-language consumers such as `ste-runtime` need an explicit baseline
ingestion contract so they do not guess which generated artifacts are
required for architecture-aware operation. The baseline subset is
`architecture-index.yaml`, `entity-registry.yaml`,
`relationship-registry.yaml`, `unresolved-registry.yaml`, and
`manifest.yaml`.

**Consequences**

Positive:
- Cross-language runtime ingestion starts from one named bundle contract
- Required bundle failure becomes explicit instead of implicit drift
- Downstream runtime implementation can remain smaller and more deterministic

### DEC-0068 — Require cross-language runtime ingestion to remain index-first, manifest-aware, and additive-safe

**Rationale**

The runtime bridge must preserve compiler authority even when a consumer
uses file-format contracts directly. Cross-language consumers should
bootstrap from the architecture index, treat manifest as a discovery and
freshness aid, treat subset registries and `architecture-graph.yaml` as
additive, and refuse to reconstruct authority by reparsing source ADR YAML.

**Consequences**

Positive:
- Compiler authority remains upstream of runtime projection behavior
- Additive graph or subset-registry failures can degrade safely without redefining the baseline contract
- The legacy compatibility registry does not silently regain authority

### DEC-0079 — Preserve the present repository seam and defer any narrow consumer facade

**Rationale**

Phase 0 production hardening does not authorize a new SDK, root export,
replacement compilation result, normalized-model revision, or graph API.
`ArchitectureRepository` and `NormalizedArchitectureModel` remain the
supported in-process seam. The historical `ArchModel` export is retained
for compatibility but remains compiler-internal and unsuitable as a new
consumer dependency.

A later phase may introduce a narrow facade over supported interfaces only.
Any future Assembler must call that supported boundary and must not bind to
`ArchModel`, compiler passes, raw source ADR parsing, or generated-file layout.

**Consequences**

Positive:
- Production controls land without freezing a premature SDK abstraction
- Existing imports remain compatible during pre-1.0 hardening
- Later facade and Assembler work starts from an explicit dependency boundary

### DEC-0080 — Establish adr_kit.api as the narrow supported authoring SDK facade

**Rationale**

Phase 1 now has sufficient compatibility, packaging, and release controls to
add a deliberately bounded facade. The facade supports single-scope
validation, authoring compilation for registries, manifest, and markdown,
repository opening, normalized-model consumption, and deterministic local
capability discovery. It reuses the existing repository and normalized model
contracts while translating compiler results into independent immutable
public contracts.

The Phase 0 deferral in DEC-0079 is therefore complete for this exact facade.
Root re-exports, graph or Architecture IR operations, recursive workspaces,
runtime evidence, rules, substrate, admission, Assembler, MCP, and LLM
capabilities remain unauthorized.

The supported facade evolves repository/model consumption for model 2.0 compatibility adapters without exposing compiler internals or ArchModel.

**Consequences**

Positive:
- New Python consumers have one explicit supported authoring boundary
- Existing repository and normalized-model contracts remain unchanged
- Compiler implementation types remain free to evolve behind translation
- Historical deep imports remain compatible without becoming recommended

### DEC-0082 — Keep repository-local authoring projections separate from workspace runtime state

**Rationale**

Every artifact stored inside the `adr-architecture-kit` repository is owned
and written by ADR Kit. External systems may read its canonical ADRs and
supported authoring projections, but they must not target the repository as
an output location. Runtime-derived graphs, evidence, registries, manifests,
and other workspace state belong under the workspace-root `.ste-workspace`
directory, which is outside every repository.

Phase 1 therefore validates only ADR Kit's own deterministic authoring
outputs. A repository-targeted runtime refresh is not part of the SDK
authority gate. Any runtime command that writes into this repository violates
the workspace state boundary and is an external implementation defect rather
than authoring output to accept or baseline.

**Consequences**

Positive:
- ADR Kit remains the sole writer of files committed in its repository
- Runtime and workspace state cannot invalidate authoring integrity controls
- Cross-repository consumers retain read access without sharing write authority
- SDK implementation remains independent of runtime graph production


## Capabilities

### CAP-0039 — Stable Repository Semantic Boundary

Provide one scope-safe, deterministic in-process interface that loads
compiled architecture bundles and exposes the authorized
NormalizedArchitectureModel 2.0 semantic payload with UUID, alias, and
logical URI resolution.

### CAP-0044 — Cross-Language Runtime Ingestion Contract

Provide one explicit file-format ingestion posture for cross-language or
out-of-process runtime consumers so they can consume compiler-owned
Architecture IR without redefining architecture semantics locally.

### CAP-0047 — Narrow Supported Authoring SDK

Provide a deterministic Python facade for explicit-root validation,
authoring compilation of registries, manifest, and markdown, repository
loading, normalized-model consumption, and local capability discovery. The facade remains a narrow supported authoring SDK and admits only explicitly authorized public symbols for the current API contract, including additive promotion-provider operations once separately authorized. Bounded model 2.0 compatibility adapters may be exposed without exposing compiler internals and without advertising schema/model embodiment as complete.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0059 | In-process architecture consumers MUST use the ArchitectureRepository boundary instead of inventing ad hoc… | MUST / design | automated |
| INV-0067 | Cross-language or out-of-process architecture consumers that rely on the file-format contract MUST bootstrap from… | MUST / design | automated |
| INV-0074 | The supported `adr_kit.api` facade MUST NOT expose `ArchModel`, compiler configuration, compiler passes, frontend or… | MUST / test | automated |
| INV-0076 | Only ADR Kit tooling MAY create or modify canonical artifacts, authoring projections, compatibility outputs, or… | MUST / design | automated |

### INV-0059

**Statement**

In-process architecture consumers MUST use the ArchitectureRepository
boundary instead of inventing ad hoc compiled-registry interpretation when
a repository boundary is available. Cross-language or out-of-process
consumers MAY consume generated `adrs/index/*` artifacts directly when the
repository boundary is not available to them.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Centralized loading and semantic adaptation are required to prevent
consumer fragmentation and long-term registry drift.

### INV-0067

**Statement**

Cross-language or out-of-process architecture consumers that rely on the
file-format contract MUST bootstrap from `adrs/index/architecture-index.yaml`,
MUST require the minimal ingestion subset of `entity-registry.yaml`,
`relationship-registry.yaml`, `unresolved-registry.yaml`, and
`adrs/manifest.yaml`, and MUST NOT recreate architecture authority by
reparsing ADR source YAML when the generated contract bundle is expected.
Subset registries and `architecture-graph.yaml` MAY be consumed only as
additive artifacts, and `adrs/entities/registry.yaml` MUST remain
compatibility-only.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Cross-language consumers need an explicit ingestion posture that preserves
compiler authority, keeps required versus additive surfaces distinct, and
prevents fallback drift into source-level reinterpretation.

### INV-0074

**Statement**

The supported `adr_kit.api` facade MUST NOT expose `ArchModel`, compiler
configuration, compiler passes, frontend or backend objects, emitters,
internal output artifacts, mutable diagnostic logs, compiler caches, or
other compiler-internal types through public annotations or runtime result
object graphs.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

The facade is a stable consumer contract, while compiler orchestration and
intermediate representation remain implementation details that must be able
to evolve independently.

### INV-0076

**Statement**

Only ADR Kit tooling MAY create or modify canonical artifacts, authoring
projections, compatibility outputs, or other files inside the
`adr-architecture-kit` repository. External runtime or workspace tooling MAY
read supported repository contracts but MUST NOT write anywhere inside any
repository tree. All runtime-derived and workspace-derived state MUST be
written beneath the workspace-root `.ste-workspace` directory.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Separate write domains prevent derived runtime state from corrupting
canonical authoring state, compatibility bytes, integrity metadata, and
repository-local governance evidence.




## Physical Realization

**Systems**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0004](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)

**Capability realization**
- Cross-Language Runtime Ingestion Contract (CAP-0044) → Entity Registry Generator and Query Surface (COMP-0010)

  `CAP-0044 -[:implemented_by]-> COMP-0010`




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)

**References**
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0014](ADR-L-0014-brownfield-onboarding-and-canonicalization-workflow.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
- [ADR-PC-0005](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)
- [ADR-L-0016](ADR-L-0016-deterministic-corpus-query-and-authoring-orientation-apis.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0001 — Entity Registry and Discovery Index](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) | implemented by | `CAP-0044 -[:implemented_by]-> COMP-0010` |
| [ADR-PC-0003 — Compiler Pipeline and Driver](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) | implements this logical authority | `ADR-PC-0003 -[:implements_logical]-> ADR-L-0013` |
| [ADR-PC-0004 — Repository Boundary and Normalized Semantic Model](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md) | implements this logical authority | `ADR-PC-0004 -[:implements_logical]-> ADR-L-0013` |
| [ADR-PC-0005 — Generated Artifact Integrity Validation](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md) | implements this logical authority | `ADR-PC-0005 -[:implements_logical]-> ADR-L-0013` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0013` |




## Notes

Explicitly deferred beyond Phase 2 / into Phase 3 or later: graph bundles,
transactional authoring, Assembler implementation, MCP, runtime extraction,
rules, substrate, and admission capability. Topology remains
structural-ID-only; intrinsic UUID identity for topology records remains
deferred.

Phase 2 completed assertion identity, entity/schema expansion, bindings, and
normalized-model expansion to model 1.1. ADR-L-0019 subsequently authorizes
model 2.0 as the v1.3 UUID/alias compatibility event; its embodiment remains
v1.3 implementation work.


---

*Generated from ADR-L-0013 by ADR Architecture Kit (projection v3)*