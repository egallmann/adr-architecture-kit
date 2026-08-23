<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 2
hash_algorithm: sha256
source_hash: bf6f95bc7db14f54296af83d8c115d031fd2b0b7b75ed1bf8a5c7efd74c88f18
rendered_hash: 51be6bfe8a0e0198a435b745296e57101bf8dce5a4e3537da13f2cc147404c40
-->

# ADR-L-0013: Architecture Repository Boundary and Normalized Semantic Model

**Status:** accepted  
**Created:** 2026-03-14  
**Modified:** 2026-08-06  
**Authors:** adr-architecture-kit  
**Domains:** repository, discovery, compiler, kernel  
**Tags:** repository-boundary, semantic-model, archmodel, registries  
**Alias name:** architecture-repository-boundary-and-normalized-semantic-model  

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


## Relationship graph

```mermaid
flowchart LR
  n_019fee89_e615_7b9c_8e3f_32ceeda01491["ADR-L-0007"]
  n_019fee89_e616_7018_982f_d3d703f29db7["DEC-0079"]
  n_019fee89_e616_7140_bb3f_8b78ab40d018["CAP-0039"]
  n_019fee89_e616_7153_930f_595ce3d9f96d["DEC-0061"]
  n_019fee89_e616_7174_bc0f_0812c51d1d0c["INV-0076"]
  n_019fee89_e616_71e8_8619_6d6dde59a698["INV-0067"]
  n_019fee89_e616_72be_b22f_784bf7f19434["INV-0059"]
  n_019fee89_e616_7340_a61b_57b9c79eca96["DEC-0062"]
  n_019fee89_e616_73a1_9d27_96afd11520ad["CAP-0047"]
  n_019fee89_e616_744f_b63e_5ecddf344faa["ADR-L-0012"]
  n_019fee89_e616_755b_843e_689f9ffa2091["DEC-0067"]
  n_019fee89_e616_7628_913b_a059c1057c36["ADR-L-0014"]
  n_019fee89_e616_765f_a51d_a19f2cfa383b["INV-0074"]
  n_019fee89_e616_770c_a025_2c241a720730["ADR-L-0009"]
  n_019fee89_e616_77c3_9137_1750a4d9bca5["DEC-0068"]
  n_019fee89_e616_7a7c_883f_b36edf94a1d8["DEC-0082"]
  n_019fee89_e616_7b02_9c1e_5028e84c85e1["DEC-0052"]
  n_019fee89_e616_7c36_b43f_6e4c45a4faf4["DEC-0080"]
  n_019fee89_e616_7c4e_953c_b7349412a784["ADR-L-0013"]
  n_019fee89_e616_7c74_922b_f871dc663b59["DEC-0050"]
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712["CAP-0044"]
  n_019fee89_e616_7d61_8e35_f11ba2ddd75d["ADR-L-0010"]
  n_019fee89_e616_7da4_9e1f_eb49b97c42ca["DEC-0051"]
  n_019fee89_e617_7270_ab2f_58a756d2530e["ADR-PC-0001"]
  n_019fee89_e617_76d8_a333_e21361cd6602["COMP-0010"]
  n_019fee89_e617_7e69_861a_f3040f70c2d9["ADR-L-0015"]
  n_019fee89_e617_7f4d_811d_4862645a55c5["ADR-L-0018"]
  n_019fee89_e617_7fe1_8d2c_cc2745c31674["ADR-L-0016"]
  n_019fee89_e618_73ce_aa2d_101276d64e33["ADR-PC-0004"]
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37["ADR-PC-0005"]
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6["ADR-PC-0003"]
  n_019fee89_e618_7d04_9337_4aa2d3258507["ADR-PS-0002"]
  n_019ffdba_3c42_7c4a_a737_f6751a265d60["ADR-L-0020"]
  n_01a02d38_7cf3_7b3c_87ec_1c5f08490c6e["ADR-L-0024"]
  n_019fee89_e616_7018_982f_d3d703f29db7 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7140_bb3f_8b78ab40d018 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7153_930f_595ce3d9f96d -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7174_bc0f_0812c51d1d0c -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_71e8_8619_6d6dde59a698 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_72be_b22f_784bf7f19434 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7340_a61b_57b9c79eca96 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_73a1_9d27_96afd11520ad -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_755b_843e_689f9ffa2091 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_765f_a51d_a19f2cfa383b -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_77c3_9137_1750a4d9bca5 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7a7c_883f_b36edf94a1d8 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7b02_9c1e_5028e84c85e1 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7c36_b43f_6e4c45a4faf4 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7c74_922b_f871dc663b59 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7da4_9e1f_eb49b97c42ca -->|"declared_in"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7d30_ae2e_6fee1dbb2712 -->|"implemented_by"| n_019fee89_e617_76d8_a333_e21361cd6602
  n_019fee89_e618_73ce_aa2d_101276d64e33 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e618_74b2_a83e_e41c7d8c9f37 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e618_7b76_843f_cfe21ceb2ea6 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e618_7d04_9337_4aa2d3258507 -->|"implements_logical"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e615_7b9c_8e3f_32ceeda01491 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_744f_b63e_5ecddf344faa -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7628_913b_a059c1057c36 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_770c_a025_2c241a720730 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e616_744f_b63e_5ecddf344faa
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e616_770c_a025_2c241a720730
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e616_7d61_8e35_f11ba2ddd75d
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e617_7270_ab2f_58a756d2530e
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e617_7f4d_811d_4862645a55c5
  n_019fee89_e616_7c4e_953c_b7349412a784 -->|"references"| n_019fee89_e618_74b2_a83e_e41c7d8c9f37
  n_019fee89_e616_7d61_8e35_f11ba2ddd75d -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e617_7e69_861a_f3040f70c2d9 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e617_7f4d_811d_4862645a55c5 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019fee89_e617_7fe1_8d2c_cc2745c31674 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_019ffdba_3c42_7c4a_a737_f6751a265d60 -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
  n_01a02d38_7cf3_7b3c_87ec_1c5f08490c6e -->|"references"| n_019fee89_e616_7c4e_953c_b7349412a784
```

## Related ADRs

### ADR-L-0007 — Deterministic Documentation Projection

**Relationships:**
- 019fee89-e615-7b9c-8e3f-32ceeda01491 -[:references]-> this ADR

**Context:** The repository already treats several human-readable artifacts as derived state:
ADR human projections under adrs/adr-projection/, manifest summaries, and the AI-first SYSTEM-OVERVIEW
are generated from structured or code-defined sources. That behavior now needs
explicit architectural authority so future contributors do not reintroduce
manually maintained documentation that drifts from canonical artifacts.

[Open projection](ADR-L-0007-deterministic-documentation-projection.md)
### ADR-L-0009 — Derived Architecture Discovery Surfaces

**Relationships:**
- 019fee89-e616-770c-a025-2c241a720730 -[:references]-> this ADR
- this ADR -[:references]-> 019fee89-e616-770c-a025-2c241a720730

**Context:** adr-architecture-kit is primarily machine-facing tooling used by agents to
reason over canonical architecture artifacts. Relying on agents to scan raw
ADR bodies for discovery is inconsistent with the toolkit's AI-first design
theory: discovery surfaces should be explicit, deterministic, cheap to query,
and derived from canonical authority.

[Open projection](ADR-L-0009-derived-architecture-discovery-surfaces.md)
### ADR-L-0010 — Kernel Interface Contract and Validation Profiles

**Relationships:**
- 019fee89-e616-7d61-8e35-f11ba2ddd75d -[:references]-> this ADR
- this ADR -[:references]-> 019fee89-e616-7d61-8e35-f11ba2ddd75d

**Context:** adr-architecture-kit is transitioning from an implicit generator toolkit into
an explicit architecture compiler with a defined contract boundary to the STE
kernel. The plan work established that the compiler's guaranteed contract
surface is broader than the kernel's minimal load subset: the contract family
is all generated artifacts under `adrs/index/` plus `manifest.yaml`, while
individual consumers may rely on narrower subsets.

[Open projection](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
### ADR-L-0012 — Federation Authority and Qualified Identity Model

**Relationships:**
- 019fee89-e616-744f-b63e-5ecddf344faa -[:references]-> this ADR
- this ADR -[:references]-> 019fee89-e616-744f-b63e-5ecddf344faa

**Context:** The compiler and recursive multi-scope model preserve repository-local
compilation boundaries, while STE federation spans independently compiled
repositories. Federation therefore requires global identity without weakening
provider authority or allowing the aggregation layer to rewrite canonical
repository state.

[Open projection](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
### ADR-L-0014 — Brownfield Onboarding and Canonicalization Workflow

**Relationships:**
- 019fee89-e616-7628-913b-a059c1057c36 -[:references]-> this ADR

**Context:** STE adoption often begins after meaningful architecture and implementation
decisions already exist. In that stage, the problem is not blank-slate design;
it is brownfield onboarding: discover current architecture state, normalize
legacy identifiers and metadata, formalize already-made decisions into
canonical ADRs, and regenerate deterministic derived artifacts without
treating derived state as authority.

[Open projection](ADR-L-0014-brownfield-onboarding-and-canonicalization-workflow.md)
### ADR-L-0015 — ADR Governance State and Override Semantics

**Relationships:**
- 019fee89-e617-7e69-861a-f3040f70c2d9 -[:references]-> this ADR

**Context:** The repository now has a first-pass governance block on ADRs and a canonical
objection override artifact. That initial implementation made the metadata
available, but it left several important questions under-specified:

[Open projection](ADR-L-0015-adr-governance-state-and-override-semantics.md)
### ADR-L-0016 — Deterministic Corpus Query and Authoring Orientation APIs

**Relationships:**
- 019fee89-e617-7fe1-8d2c-cc2745c31674 -[:references]-> this ADR

**Context:** Upstream authoring workflows need deterministic ways to inspect the compiled
corpus, orient themselves within a scope, and allocate governed human-facing
ADR aliases without reparsing registry YAML or hand-implementing directory
scans.

[Open projection](ADR-L-0016-deterministic-corpus-query-and-authoring-orientation-apis.md)
### ADR-L-0018 — Schema v1.2 and Normalized Semantic Foundation

**Relationships:**
- 019fee89-e617-7f4d-811d-4862645a55c5 -[:references]-> this ADR
- this ADR -[:references]-> 019fee89-e617-7f4d-811d-4862645a55c5

**Context:** Phase 1 established a narrow supported authoring SDK while explicitly deferring
schema expansion, normalized-model expansion, assertion identity, bindings, and
topology identity. The repository now needs those contracts as an additive
semantic foundation for future consumers, without implementing the Phase 3 graph
bundle or absorbing authority owned by runtime, rules, substrate, or admission
systems.

[Open projection](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
### ADR-L-0020 — Semantic Implementation Attribution and Cross-Layer Architecture Relationships

**Relationships:**
- 019ffdba-3c42-7c4a-a737-f6751a265d60 -[:references]-> this ADR

**Context:** ADR-L-0004 established implementation attribution as an explicit intent
surface. ADR-L-0019 made canonical machine identity a lowercase UUIDv7.
Attribution evidence still cited human aliases (`ADR-L-*`, `INV-*`) and
could not name typed relationships to nested architecture entities.

[Open projection](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
### ADR-L-0024 — Cross-Language Consumer Bindings and TypeScript Distribution

**Relationships:**
- 01a02d38-7cf3-7b3c-87ec-1c5f08490c6e -[:references]-> this ADR

**Context:** ADR-Kit already owns accepted ADR authority, canonical schema bytes, semantic
vocabularies, the repository discovery contract, the normalized model, and
validated derived embodiment evidence. Python is the existing implementation
of those contracts, but it is not their semantic owner. Node services,
engineering-agent integrations, and browser applications need a supported
read-only consumer binding without reparsing ADR source YAML, depending on
compiler internals, or importing Node authority…

[Open projection](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)
### ADR-PC-0001 — Entity Registry and Discovery Index

**Relationships:**
- this ADR -[:references]-> 019fee89-e617-7270-ab2f-58a756d2530e

**Context:** The discovery/indexing component now centers on the unified compiler path. It
generates the normalized discovery bundle under `adrs/index/`, emits the
legacy compatibility registry at `adrs/entities/registry.yaml`, generates
manifest and rendered ADR markdown outputs through the same compiler-owned
path for single-scope use, and exposes exact-ID and filtered CLI query
operations over generated registry state.

[Open projection](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
### ADR-PC-0003 — Compiler Pipeline and Driver

**Relationships:**
- 019fee89-e618-7b76-843f-cfe21ceb2ea6 -[:implements_logical]-> this ADR

**Context:** The compiler driver and explicit pipeline now own deterministic architecture
compilation across parse, analysis, emission, and recursive scope
orchestration. The command-line behavior is compatibility-relevant, while the
Python compiler pipeline, passes, `ArchModel`, emitters, and result plumbing are
internal reference implementation and are not a supported SDK facade.

[Open projection](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)
### ADR-PC-0004 — Repository Boundary and Normalized Semantic Model

**Relationships:**
- 019fee89-e618-73ce-aa2d-101276d64e33 -[:implements_logical]-> this ADR

**Context:** ArchitectureRepository and NormalizedArchitectureModel are the stable
in-process semantic boundary for consumers. Phase 1 adds a narrow supported
authoring facade that reuses those contracts without wrapping or changing the
normalized model and without making registry loaders or path helpers public.

[Open projection](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md)
### ADR-PC-0005 — Generated Artifact Integrity Validation

**Relationships:**
- 019fee89-e618-74b2-a83e-e41c7d8c9f37 -[:implements_logical]-> this ADR
- this ADR -[:references]-> 019fee89-e618-74b2-a83e-e41c7d8c9f37

**Context:** Generated artifact integrity validation verifies freshness, tamper status,
integrity headers, and scope-local generated outputs. It is a distinct public
subsystem used by validator and governance flows.

[Open projection](../physical-component/ADR-PC-0005-generated-artifact-integrity-validation.md)
### ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System

**Relationships:**
- 019fee89-e618-7d04-9337-4aa2d3258507 -[:implements_logical]-> this ADR

**Context:** adr-architecture-kit operates as an authoring-time compiler and validation system rather
than a collection of unrelated generators. The implementation includes an
explicit compiler pipeline, contract validation, normalized repository/model
access, integrity verification, and CLI orchestration over those surfaces.

[Open projection](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

## Capabilities

### CAP-0039: Stable Repository Semantic Boundary

Provide one scope-safe, deterministic in-process interface that loads
compiled architecture bundles and exposes the authorized
NormalizedArchitectureModel 2.0 semantic payload with UUID, alias, and
logical URI resolution.


### CAP-0044: Cross-Language Runtime Ingestion Contract

Provide one explicit file-format ingestion posture for cross-language or
out-of-process runtime consumers so they can consume compiler-owned
Architecture IR without redefining architecture semantics locally.


### CAP-0047: Narrow Supported Authoring SDK

Provide a deterministic Python facade for explicit-root validation,
authoring compilation of registries, manifest, and markdown, repository
loading, normalized-model consumption, and local capability discovery. The facade remains a narrow supported authoring SDK and admits only explicitly authorized public symbols for the current API contract, including additive promotion-provider operations once separately authorized. Bounded model 2.0 compatibility adapters may be exposed without exposing compiler internals and without advertising schema/model embodiment as complete.






## Invariants

### INV-0059

**Statement:** In-process architecture consumers MUST use the ArchitectureRepository
boundary instead of inventing ad hoc compiled-registry interpretation when
a repository boundary is available. Cross-language or out-of-process
consumers MAY consume generated `adrs/index/*` artifacts directly when the
repository boundary is not available to them.
  
**Scope:** global  
**Enforcement:** must (design)  
**Verification:** automated

**Rationale:**
Centralized loading and semantic adaptation are required to prevent
consumer fragmentation and long-term registry drift.




### INV-0067

**Statement:** Cross-language or out-of-process architecture consumers that rely on the
file-format contract MUST bootstrap from `adrs/index/architecture-index.yaml`,
MUST require the minimal ingestion subset of `entity-registry.yaml`,
`relationship-registry.yaml`, `unresolved-registry.yaml`, and
`adrs/manifest.yaml`, and MUST NOT recreate architecture authority by
reparsing ADR source YAML when the generated contract bundle is expected.
Subset registries and `architecture-graph.yaml` MAY be consumed only as
additive artifacts, and `adrs/entities/registry.yaml` MUST remain
compatibility-only.
  
**Scope:** global  
**Enforcement:** must (design)  
**Verification:** automated

**Rationale:**
Cross-language consumers need an explicit ingestion posture that preserves
compiler authority, keeps required versus additive surfaces distinct, and
prevents fallback drift into source-level reinterpretation.




### INV-0074

**Statement:** The supported `adr_kit.api` facade MUST NOT expose `ArchModel`, compiler
configuration, compiler passes, frontend or backend objects, emitters,
internal output artifacts, mutable diagnostic logs, compiler caches, or
other compiler-internal types through public annotations or runtime result
object graphs.
  
**Scope:** global  
**Enforcement:** must (test)  
**Verification:** automated

**Rationale:**
The facade is a stable consumer contract, while compiler orchestration and
intermediate representation remain implementation details that must be able
to evolve independently.




### INV-0076

**Statement:** Only ADR Kit tooling MAY create or modify canonical artifacts, authoring
projections, compatibility outputs, or other files inside the
`adr-architecture-kit` repository. External runtime or workspace tooling MAY
read supported repository contracts but MUST NOT write anywhere inside any
repository tree. All runtime-derived and workspace-derived state MUST be
written beneath the workspace-root `.ste-workspace` directory.
  
**Scope:** global  
**Enforcement:** must (design)  
**Verification:** automated

**Rationale:**
Separate write domains prevent derived runtime state from corrupting
canonical authoring state, compatibility bytes, integrity metadata, and
repository-local governance evidence.






## Decisions

### DEC-0050: Use ArchitectureRepository as the supported in-process semantic entry point with UUID, governed alias, and logical URI lookup

**Rationale:**
The repository boundary centralizes scope-safe loading, contract
validation, path hiding, and registry compatibility adaptation. This keeps
consumers from binding directly to registry files and current layout.

Repository lookup/resolution supports UUID, governed aliases, and logical URI forms while canonical machine operations resolve to UUID.



**Consequences:**

**Positive:**
- Consumer logic stops duplicating bundle loading behavior
- Registry schema and layout evolution can be absorbed behind one boundary
- Future kernel consumers can target one trusted seam



### DEC-0051: Adopt NormalizedArchitectureModel 2.0 as the v1.3 repository semantic payload

**Rationale:**
A semantic model is needed so consumers depend on architecture meaning
rather than current registry document shapes. The model must preserve
entities, relationships, unresolved records, provenance, scope identity,
and deterministic fingerprinting.

V1.3 authority advances normalized semantics to model 2.0 with UUID
identities and endpoints, explicit UUID/alias lookup, and versioned
compatibility adapters. Embodiment of that contract is subsequent v1.3
implementation work.



**Consequences:**

**Positive:**
- Consumers use one typed semantic contract
- Future graph compilation has a stable landing zone
- Unresolved and provenance semantics remain explicit



### DEC-0052: Keep ArchModel compiler-internal and do not promote it to the public consumer API

**Rationale:**
The current `ArchModel` is the compiler IR. It reflects pass orchestration
and extraction concerns and may evolve as compiler internals change. Making
it the public consumer contract would freeze the wrong abstraction too
early.



**Consequences:**

**Positive:**
- Compiler internals remain evolvable
- Consumer semantics stay narrower and more stable
- ADR-Kit avoids becoming an accidental proto-kernel



### DEC-0061: Permit direct `adrs/index/*` consumption for cross-language or out-of-process consumers

**Rationale:**
Cross-language consumers such as `ste-runtime` cannot call a Python
repository API directly. They still consume the same generated authority
surface, but through the file-format contract rather than the in-process
repository seam.





### DEC-0062: Treat repository-backed graph access as the intended Python graph seam

**Rationale:**
Python consumers should not hardcode the graph artifact path once the
repository boundary can expose it as part of the indexed contract family.
This preserves a coherent semantic seam for in-process consumers.





### DEC-0067: Define an index-first minimal runtime ingestion subset for cross-language architecture consumers

**Rationale:**
Cross-language consumers such as `ste-runtime` need an explicit baseline
ingestion contract so they do not guess which generated artifacts are
required for architecture-aware operation. The baseline subset is
`architecture-index.yaml`, `entity-registry.yaml`,
`relationship-registry.yaml`, `unresolved-registry.yaml`, and
`manifest.yaml`.



**Consequences:**

**Positive:**
- Cross-language runtime ingestion starts from one named bundle contract
- Required bundle failure becomes explicit instead of implicit drift
- Downstream runtime implementation can remain smaller and more deterministic



### DEC-0068: Require cross-language runtime ingestion to remain index-first, manifest-aware, and additive-safe

**Rationale:**
The runtime bridge must preserve compiler authority even when a consumer
uses file-format contracts directly. Cross-language consumers should
bootstrap from the architecture index, treat manifest as a discovery and
freshness aid, treat subset registries and `architecture-graph.yaml` as
additive, and refuse to reconstruct authority by reparsing source ADR YAML.



**Consequences:**

**Positive:**
- Compiler authority remains upstream of runtime projection behavior
- Additive graph or subset-registry failures can degrade safely without redefining the baseline contract
- The legacy compatibility registry does not silently regain authority



### DEC-0079: Preserve the present repository seam and defer any narrow consumer facade

**Rationale:**
Phase 0 production hardening does not authorize a new SDK, root export,
replacement compilation result, normalized-model revision, or graph API.
`ArchitectureRepository` and `NormalizedArchitectureModel` remain the
supported in-process seam. The historical `ArchModel` export is retained
for compatibility but remains compiler-internal and unsuitable as a new
consumer dependency.

A later phase may introduce a narrow facade over supported interfaces only.
Any future Assembler must call that supported boundary and must not bind to
`ArchModel`, compiler passes, raw source ADR parsing, or generated-file layout.



**Consequences:**

**Positive:**
- Production controls land without freezing a premature SDK abstraction
- Existing imports remain compatible during pre-1.0 hardening
- Later facade and Assembler work starts from an explicit dependency boundary



### DEC-0080: Establish adr_kit.api as the narrow supported authoring SDK facade

**Rationale:**
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



**Consequences:**

**Positive:**
- New Python consumers have one explicit supported authoring boundary
- Existing repository and normalized-model contracts remain unchanged
- Compiler implementation types remain free to evolve behind translation
- Historical deep imports remain compatible without becoming recommended



### DEC-0082: Keep repository-local authoring projections separate from workspace runtime state

**Rationale:**
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



**Consequences:**

**Positive:**
- ADR Kit remains the sole writer of files committed in its repository
- Runtime and workspace state cannot invalidate authoring integrity controls
- Cross-repository consumers retain read access without sharing write authority
- SDK implementation remains independent of runtime graph production





---

*Generated from ADR-L-0013 by ADR Architecture Kit*