<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 358f9a279080f4138a70e783e28f5d95f1c135d0e9a3a1034f859c63e93aed5f
rendered_hash: 5c68b885894b97c66b70fdc0ccbd5fd7998e89c1870ecab42e4eb861769b0811
-->

# ADR-L-0009: Derived Architecture Discovery Surfaces

## Identity / Status

**Type:** logical<br>
**Status:** accepted<br>
**Alias:** ADR-L-0009<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-03-13<br>
**Authors:** erik.gallmann<br>
**Domains:** discovery, indexing, governance, ai-first<br>
**Tags:** entity-registry, manifest, discovery, agent-tooling<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0009 |
| Status | accepted |
| Decisions | 6 |
| Capabilities | 2 |
| Invariants | 4 |
| Physical realizations | [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md), [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md), [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) |


## Context

adr-architecture-kit is primarily machine-facing tooling used by agents to
reason over canonical architecture artifacts. Relying on agents to scan raw
ADR bodies for discovery is inconsistent with the toolkit's AI-first design
theory: discovery surfaces should be explicit, deterministic, cheap to query,
and derived from canonical authority.

The kit already provides `manifest.yaml`, the normalized index family under
`adrs/index/`, and a legacy compatibility registry. What was missing was an
explicit architectural decision that separates broad discovery, normalized
lookup, guaranteed contract outputs, and compatibility-only projections so
downstream consumers do not guess which generated surfaces are authoritative.
When ADR-Kit semantic execution is available, semantic results become the
preferred machine/AI surface for interpreted ADR-domain meaning, while
manifests and indexes retain inventory and navigation roles.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0014 | Use derived discovery artifacts for agent-facing architecture inventory lookup | — |
| DEC-0021 | Treat manifest as a guaranteed discovery surface within the compiler contract family | — |
| DEC-0028 | Use `adrs/index/entity-registry.yaml` as the normalized lookup surface and keep legacy registry as compatibility-only | — |
| DEC-0057 | Classify compiler discovery outputs by guaranteed, optional, and deprecated stability tiers | — |
| DEC-0058 | Deprecate `adrs/entities/registry.yaml` as a legacy compatibility projection | — |
| DEC-0234 | Prefer semantic results for machine/AI semantic orientation when ADR-Kit execution is available | — |

### DEC-0014 — Use derived discovery artifacts for agent-facing architecture inventory lookup

**Rationale**

Canonical authority remains in ADR artifacts (including ADR-established
invariant entities). Derived discovery artifacts remain the preferred machine
inventory, navigation, interoperability, integrity, and offline inspection
surfaces. Standalone invariant files are not authority. When canonical ADR-Kit
semantic execution is available, interpreted architecture meaning should be
obtained from semantic results rather than reconstructed from these indexes.

### DEC-0021 — Treat manifest as a guaranteed discovery surface within the compiler contract family

**Rationale**

The manifest is the first discovery surface used by humans and agents for
scope inventory, freshness checks, and lifecycle summaries. It remains a
discovery artifact rather than a normalized semantic payload, but its
presence and format are guaranteed within the compiler contract family.

### DEC-0028 — Use `adrs/index/entity-registry.yaml` as the normalized lookup surface and keep legacy registry as compatibility-only

**Rationale**

The normalized entity registry in `adrs/index/` is the current machine
lookup surface for deterministic entity access. The legacy
`adrs/entities/registry.yaml` path remains compatibility-only and should
not gain new consumers.

### DEC-0057 — Classify compiler discovery outputs by guaranteed, optional, and deprecated stability tiers

**Rationale**

Downstream consumers need to know which generated surfaces are guaranteed
contract outputs, which are optional human conveniences, and which remain
transitional compatibility artifacts.

### DEC-0058 — Deprecate `adrs/entities/registry.yaml` as a legacy compatibility projection

**Rationale**

The normalized index family supersedes the legacy registry for new
consumers. Keeping the legacy path for compatibility is acceptable, but it
must be explicitly marked deprecated to prevent contract ambiguity.

### DEC-0234 — Prefer semantic results for machine/AI semantic orientation when ADR-Kit execution is available

**Rationale**

Manifest, index, and registry artifacts remain derived persisted projections
with narrower inventory, navigation, interchange, integrity, and offline
inspection roles. They are not durable semantic authority. When ADR-Kit
canonical semantic execution is available, machine and AI consumers should
prefer the semantic-result surface for interpreted architecture meaning.


## Capabilities

### CAP-0017 — Summary Discovery Surface

Provide a broad summary-oriented discovery artifact for ADR and scope
metadata through `manifest.yaml`.

### CAP-0018 — Normalized Entity Lookup Surface

Provide deterministic lookup for normalized architecture entities through
`adrs/index/entity-registry.yaml`.

**Acceptance criteria**
- normalized entity lookup is served from the indexed contract family
- the legacy entity registry is treated as compatibility-only




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0043 | Canonical architectural authority MUST remain in ADR artifacts (including invariants established in logical ADRs).… | MUST / design | automated |
| INV-0044 | Derived architecture discovery artifacts MUST be deterministic, reproducible, and disposable. | MUST / design | automated |
| INV-0045 | Agent-facing ADR toolkit workflows MUST prefer indexed lookup surfaces over raw ADR body traversal for inventory and… | MUST / design | automated |
| INV-0238 | Semantic-result outputs MUST remain derived execution results for a supplied Exact Source Basis and MUST NOT be… | MUST / design | manual |

### INV-0043

**Statement**

Canonical architectural authority MUST remain in ADR artifacts (including
invariants established in logical ADRs). Derived discovery artifacts
including adrs/index/invariant-registry.yaml MUST NOT independently define
or redefine invariants. The adrs/invariants/ authoring directory is retired.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Derived discovery surfaces are indexes of canonical architecture state,
not the source of truth. The invariant-registry is a complete derived
projection of ADR-L invariants only.

### INV-0044

**Statement**

Derived architecture discovery artifacts MUST be deterministic,
reproducible, and disposable.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Deterministic regeneration is required for machine trust, CI validation,
and drift detection.

### INV-0045

**Statement**

Agent-facing ADR toolkit workflows MUST prefer indexed lookup surfaces
over raw ADR body traversal for inventory and navigation by default. When
canonical ADR-Kit semantic execution is available, workflows MUST prefer
semantic results over reconstructing interpreted architecture meaning from
manifest, index, registry, or Markdown projections.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Indexes remain cheap inventory surfaces; semantic results are the
machine-oriented evolution for interpreted ADR-domain meaning.

### INV-0238

**Statement**

Semantic-result outputs MUST remain derived execution results for a supplied
Exact Source Basis and MUST NOT be treated as durable architecture authority
replacing canonical ADR YAML.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Preferring semantic results for orientation must not invent a second durable
authority layer beside authored ADRs.




## Physical Realization

**Systems**
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)

**Components**
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)
- [ADR-PC-0003](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md)

**Capability realization**
- Normalized Entity Lookup Surface (CAP-0018) → Entity Registry Generator and Query Surface (COMP-0010)

  `CAP-0018 -[:implemented_by]-> COMP-0010`




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)

**References**
- [ADR-L-0014](ADR-L-0014-brownfield-onboarding-and-canonicalization-workflow.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0008](ADR-L-0008-validation-modes-for-draft-and-complete-adrs.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0001 — Entity Registry and Discovery Index](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) | implemented by | `CAP-0018 -[:implemented_by]-> COMP-0010` |
| [ADR-PC-0003 — Compiler Pipeline and Driver](../physical-component/ADR-PC-0003-compiler-pipeline-and-driver.md) | implements this logical authority | `ADR-PC-0003 -[:implements_logical]-> ADR-L-0009` |
| [ADR-PS-0001 — ADR Architecture Kit Discovery and Indexing System](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md) | implements this logical authority | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0009` |





---

*Generated from ADR-L-0009 by ADR Architecture Kit (projection v3)*