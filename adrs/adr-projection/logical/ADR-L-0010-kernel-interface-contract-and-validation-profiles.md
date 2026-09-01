<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: e86a16c3f69d75621ec9d4adac0b7d1777ab3ef186667771a9dee347701433a0
rendered_hash: 9c92c36ddb8080f036a06dd07e1dc873cc6990189b544281e91ebea8ff622fab
-->

# ADR-L-0010: Kernel Interface Contract and Validation Profiles

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0010  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-14  
**Authors:** adr-architecture-kit  
**Domains:** kernel, contract, governance, validation  
**Tags:** contract, registries, brownfield, migration, sentinel  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0010 |
| Status | accepted |
| Decisions | 7 |
| Capabilities | 2 |
| Invariants | 4 |
| Physical realizations | [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md), [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) |


## Context

adr-architecture-kit is transitioning from an implicit generator toolkit into
an explicit architecture compiler with a defined contract boundary to the STE
kernel. The plan work established that the compiler's guaranteed contract
surface is broader than the kernel's minimal load subset: the contract family
is all generated artifacts under `adrs/index/` plus `manifest.yaml`, while
individual consumers may rely on narrower subsets.

The same plan work also established that legacy onboarding must be tolerated
without collapsing schema structure. Brownfield architectures need a way to
remain structurally valid while carrying explicit machine-readable placeholders
for unavailable content. At the same time, production kernel loading must not
silently accept incomplete architecture knowledge as fully compliant.

What is needed is a formal contract ADR that defines:
1. The minimal compiler-to-kernel contract surface
2. The pre-stable versioning policy for that contract
3. Validation profiles for greenfield, brownfield, and migration use
4. The meaning of `sentinel_compliant` for compilation, CI, and kernel load
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0036 | Use the indexed compiler bundle as the contract surface, with four core artifacts as the minimal kernel load subset | — |
| DEC-0037 | Treat the compiler-kernel contract as pre-stable 0.x until intentionally frozen | — |
| DEC-0044 | Promote the contract to 1.0 only through an explicit readiness gate | — |
| DEC-0038 | Validate compiled output through explicit greenfield, brownfield, and migration profiles | — |
| DEC-0039 | Classify sentinel-backed bundles as sentinel compliant rather than compliant | — |
| DEC-0059 | Treat all `adrs/index/*` artifacts and `manifest.yaml` as the guaranteed contract family | — |
| DEC-0060 | Treat `architecture-graph.yaml` as an additive indexed artifact rather than a second architecture authority | — |

### DEC-0036 — Use the indexed compiler bundle as the contract surface, with four core artifacts as the minimal kernel load subset

**Rationale**

The full guaranteed compiler contract includes all generated artifacts in
`adrs/index/` plus `manifest.yaml`. The kernel may rely on a narrower
minimal load subset for bootstrap loading, but that subset must not be
mistaken for the entire guaranteed contract family.

**Consequences**

Positive:
- Kernel loading surface can stay small and explicit
- The broader guaranteed contract family remains available to downstream consumers
- Minimal load subset and full contract family are separated cleanly

### DEC-0037 — Treat the compiler-kernel contract as pre-stable 0.x until intentionally frozen

**Rationale**

The contract is not yet open as a stable external surface. Using 0.x avoids
pretending the boundary is already semantically frozen while still keeping a
versioned contract and explicit upgrade path.

**Consequences**

Positive:
- Breaking changes remain allowed while the boundary is still internal
- The transition to 1.0 can be made explicit and intentional
- Contract drift can still be tracked through version numbers

### DEC-0044 — Promote the contract to 1.0 only through an explicit readiness gate

**Rationale**

Stable status should reflect implemented and verified behavior, not elapsed
time or confidence. The transition from 0.x to 1.0 must therefore be tied
to concrete conditions across compiler output, schema conformance, and
actual kernel consumption.

**Consequences**

Positive:
- Stable contract status remains meaningful
- The kernel boundary is frozen intentionally rather than accidentally
- Promotion becomes auditable through governance

### DEC-0038 — Validate compiled output through explicit greenfield, brownfield, and migration profiles

**Rationale**

A single contract schema is not enough to represent the enforcement posture
across new systems, legacy imports, and active remediation states. Profiles
allow strict integrity rules to remain universal while allowing quality and
completeness expectations to vary by adoption stage.

**Consequences**

Positive:
- Brownfield import can be structurally valid without pretending to be complete
- Greenfield enforcement remains strict
- Migration can tighten policy gradually without schema forks

### DEC-0039 — Classify sentinel-backed bundles as sentinel compliant rather than compliant

**Rationale**

Sentinel-backed content is valid under the right profile, but it is not the
same as fully populated architecture knowledge. A separate validator outcome
preserves honesty while keeping the system operational.

**Consequences**

Positive:
- Compile success and contract honesty are both preserved
- CI behavior can follow the active profile explicitly
- Production kernel loads can reject sentinel-backed bundles by default

### DEC-0059 — Treat all `adrs/index/*` artifacts and `manifest.yaml` as the guaranteed contract family

**Rationale**

Downstream bridge and kernel work already depend on the wider indexed
bundle, the manifest, and the additive graph artifact. Guaranteeing the
full family prevents downstream consumers from inventing different notions
of what the compiler publishes.

### DEC-0060 — Treat `architecture-graph.yaml` as an additive indexed artifact rather than a second architecture authority

**Rationale**

The graph is consumed downstream and belongs to the generated contract
family, but it remains a projection artifact over the same architecture
authority rather than a separate source of meaning.


## Capabilities

### CAP-0034 — Profile-Aware Contract Validation

Validate compiled registry bundles against a single contract schema with
profile-specific enforcement for greenfield, brownfield, and migration.

### CAP-0035 — Production-Safe Kernel Admission

Distinguish between contract-valid bundles that are production-safe and
bundles that are inspection-safe only.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0052 | The compiler's guaranteed machine-readable contract surface MUST be defined as all generated artifacts under… | MUST / design | automated |
| INV-0053 | Contract validation MUST support profile-based enforcement for greenfield, brownfield, and migration without forking… | MUST / design | automated |
| INV-0054 | Bundles classified as sentinel compliant MUST NOT be admitted to production kernel loads by default, but MAY be… | MUST / runtime | automated |
| INV-0097 | Compiler projection from canonical architecture state to kernel-facing registry artifacts must be deterministic and… | MUST / test | automated |

### INV-0052

**Statement**

The compiler's guaranteed machine-readable contract surface MUST be defined
as all generated artifacts under `adrs/index/` plus `adrs/manifest.yaml`.
Consumers MAY define narrower minimal load subsets, but those subsets MUST
NOT be treated as the full guaranteed contract surface.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

The contract boundary must remain explicit without collapsing the broader
generated bundle into one consumer's minimal load subset.

### INV-0053

**Statement**

Contract validation MUST support profile-based enforcement for greenfield,
brownfield, and migration without forking the registry schema.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Enforcement posture changes across adoption stages, but the contract surface
must remain one schema.

### INV-0054

**Statement**

Bundles classified as sentinel compliant MUST NOT be admitted to production
kernel loads by default, but MAY be loaded by inspection-only or remediation
tooling.

**Scope:** global

**Enforcement:** MUST (runtime)
**Verification:** automated

**Rationale**

Sentinel-backed content preserves structure, not full operational readiness.

### INV-0097

**Statement**

Compiler projection from canonical architecture state to kernel-facing registry artifacts must be deterministic and contract-valid.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Equivalent canonical inputs must produce equivalent registry outputs that
continue to satisfy the explicit kernel contract.




## Physical Realization

**Systems**
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**Components**
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)

**References**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0009](ADR-L-0009-derived-architecture-discovery-surfaces.md)
- [ADR-L-0011](ADR-L-0011-metadata-schemas-and-remediation-ledger-enforcement.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | implements this logical authority | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0010` |
| [ADR-PS-0002 — ADR Kit Authoring Compiler and Validation System](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md) | implements this logical authority | `ADR-PS-0002 -[:implements_logical]-> ADR-L-0010` |





---

*Generated from ADR-L-0010 by ADR Architecture Kit (projection v3)*