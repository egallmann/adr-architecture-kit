<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 4353a3a1bfc1ff43fad422b6d0d7e86d59bd3c7e3d952098c91ad088c2993908
rendered_hash: fb8ed49453caae30665e54a8197d9fffde23cc04f855a14f490712803c48e208
-->

# ADR-L-0014: Brownfield Onboarding and Canonicalization Workflow

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0014  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-15  
**Authors:** erik.gallmann  
**Domains:** migration, onboarding, governance, brownfield  
**Tags:** onboarding, migration, canonicalization, cleanup  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0014 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 2 |
| Invariants | 2 |
| Physical realizations | [ADR-PC-0006](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md) |


## Context

STE adoption often begins after meaningful architecture and implementation
decisions already exist. In that stage, the problem is not blank-slate design;
it is brownfield onboarding: discover current architecture state, normalize
legacy identifiers and metadata, formalize already-made decisions into
canonical ADRs, and regenerate deterministic derived artifacts without
treating derived state as authority.

adr-architecture-kit already contains pieces of this workflow:
- canonical ID normalization with migration ledgers
- remediation-ledger and metadata enforcement
- compiler-owned derived artifact regeneration
- repository and discovery surfaces for post-onboarding use

What is missing is one explicit logical decision that defines onboarding and
migration as a first-class STE workflow rather than an ad hoc repair pass.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0053 | Treat brownfield onboarding as a first-class canonicalization workflow | — |
| DEC-0054 | Separate onboarding into discovery, normalization, canonization, regeneration, and validation phases | — |
| DEC-0055 | Record deterministic brownfield remaps and cleanup transitions in canonical migration artifacts | — |
| DEC-0056 | Keep rendered artifacts as disposable human projections and forbid them as semantic authority when canonical YAML exists | — |

### DEC-0053 — Treat brownfield onboarding as a first-class canonicalization workflow

**Rationale**

Existing architecture can be informally decided but not yet canonicalized.
STE needs an explicit workflow for converting that state into canonical ADR
authority without pretending the implementation invented the architecture.

**Consequences**

Positive:
- Legacy-to-canonical onboarding gains a governed path
- Architecture capture can proceed without redesigning already-made decisions
- Cleanup work becomes auditable rather than ad hoc

### DEC-0054 — Separate onboarding into discovery, normalization, canonization, regeneration, and validation phases

**Rationale**

Brownfield onboarding mixes several concerns that should not be collapsed:
discovery identifies what exists, normalization resolves collisions and
missing metadata, canonization creates or updates canonical ADRs,
regeneration rebuilds derived artifacts, and validation verifies the result.

**Consequences**

Positive:
- Automation can be applied safely to the normalization phase
- Human review remains focused on architectural classification decisions
- Migration evidence can be attached to the correct stage

### DEC-0055 — Record deterministic brownfield remaps and cleanup transitions in canonical migration artifacts

**Rationale**

Canonical ID remaps, onboarding normalization, and controlled cleanup
transitions should produce durable evidence so future consumers can explain
how legacy identifiers and structures map into current canonical state.

**Consequences**

Positive:
- Historical continuity is preserved
- Query surfaces can explain old-to-new mappings
- Cleanup automation gains an auditable output

### DEC-0056 — Keep rendered artifacts as disposable human projections and forbid them as semantic authority when canonical YAML exists

**Rationale**

Rendered markdown is useful for review and browsing, but it is structurally
weaker than canonical YAML and should never become the semantic source of
truth when canonical ADR artifacts are available.

**Consequences**

Positive:
- Human-friendly projections remain useful without weakening authority
- Discovery and graphing stay grounded in canonical YAML and controlled registries
- Agents are less likely to reintroduce narrative ambiguity through markdown parsing


## Capabilities

### CAP-0040 — Brownfield Onboarding Workflow

Provide an explicit workflow for migrating existing repositories into STE
canonical architecture authority through phased discovery, normalization,
canonization, regeneration, and validation.

**Acceptance criteria**
- The workflow distinguishes discovery from canonization
- Canonical migration evidence is produced for deterministic cleanup steps
- Derived artifacts are regenerated only after canonical updates

### CAP-0041 — Canonical Migration Evidence

Record deterministic remaps, onboarding cleanup results, and legacy-to-
canonical transitions in machine-readable migration artifacts.

**Acceptance criteria**
- Canonical ID remaps are written to migration artifacts
- Migration artifacts explain old-to-new mappings
- Derived discovery can surface migration provenance where useful




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0060 | STE onboarding workflows MUST treat discovery, normalization, canonization, regeneration, and validation as distinct… | MUST / design | automated |
| INV-0061 | Rendered markdown artifacts MUST be treated as derived human-facing projections and MUST NOT be used as semantic… | MUST / policy | automated |

### INV-0060

**Statement**

STE onboarding workflows MUST treat discovery, normalization, canonization,
regeneration, and validation as distinct phases with canonical artifacts
updated before derived artifacts are refreshed.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Canonical artifacts must remain the source of truth throughout brownfield
onboarding and cleanup.

### INV-0061

**Statement**

Rendered markdown artifacts MUST be treated as derived human-facing
projections and MUST NOT be used as semantic authority when canonical YAML
source artifacts are available.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Rendered markdown is a convenience surface, not a trustworthy semantic
contract when canonical structured artifacts exist.




## Physical Realization

**Components**
- [ADR-PC-0006](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)

**References**
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0006 — Brownfield Onboarding and Canonical Normalization](../physical-component/ADR-PC-0006-brownfield-onboarding-and-canonical-normalization.md) | implements this logical authority | `ADR-PC-0006 -[:implements_logical]-> ADR-L-0014` |





---

*Generated from ADR-L-0014 by ADR Architecture Kit (projection v3)*