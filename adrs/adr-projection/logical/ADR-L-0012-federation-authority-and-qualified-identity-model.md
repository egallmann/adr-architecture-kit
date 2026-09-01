<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 728acc72ce16ad9fb6875bfb5e97656e79bb98c004431c1103a0267b21400b5c
rendered_hash: 98edad81f36c6c69256108444500b081ddf058889dbc8b43df6c3d1e35ca71fb
-->

# ADR-L-0012: Federation Authority and Qualified Identity Model

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0012  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-14  
**Modified:** 2026-06-02  
**Authors:** adr-architecture-kit  
**Domains:** federation, identity, governance, multi-repo  
**Tags:** federation, qualified-id, namespace, authority  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0012 |
| Status | accepted |
| Decisions | 4 |
| Capabilities | 1 |
| Invariants | 1 |
| Physical realizations | [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md), [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) |


## Context

The compiler and recursive multi-scope model preserve repository-local
compilation boundaries, while STE federation spans independently compiled
repositories. Federation therefore requires global identity without weakening
provider authority or allowing the aggregation layer to rewrite canonical
repository state.

Earlier authoring treated bare local identifiers as sufficient within a
repository and introduced namespace qualification only when crossing repository
boundaries. Canonical v1.3 identity separates those concerns more precisely:
authored entity references use UUIDs, provider-authoritative external identity
is `(architecture_namespace, UUID)`, human aliases remain recognition surfaces,
and workspace repository keys are used only for registration, routing, and
attribution.

This ADR establishes federation as read-only aggregation, preserves each
provider as authority over its entities, and defines the identity boundary used
when architecture is resolved across repositories.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0045 | Treat federation as a read-only aggregation layer over per-repo canonical registries | — |
| DEC-0046 | Use provider-authoritative conflict resolution for federated entity definitions | — |
| DEC-0047 | Qualify machine identity as (architecture_namespace, UUID); keep human alias qualification derived | — |
| DEC-0077 | Emit workspace-attribution-federation.yaml as read-only cross-repo attribution index keyed by workspace routing identity that resolves to architecture_namespace | — |

### DEC-0045 — Treat federation as a read-only aggregation layer over per-repo canonical registries

**Rationale**

Per-repository registries remain the canonical architecture outputs for
their owning repository. Federation exists to read, index, merge, and query
across those outputs; it must not rewrite or mutate them.

**Consequences**

Positive:
- Repository ownership boundaries remain explicit
- Federation can be added or evolved without changing local compiler output
- Global analysis stays traceable to per-repo canonical state

### DEC-0046 — Use provider-authoritative conflict resolution for federated entity definitions

**Rationale**

When one repository references an entity defined by another repository, the
defining repository is the authority on that entity's name, status, and
metadata. Consumers may declare relationships to the entity, but they do
not redefine it.

**Consequences**

Positive:
- Entity ownership remains unambiguous across repository boundaries
- Consumer references cannot silently override provider truth
- Conflict handling remains deterministic

### DEC-0047 — Qualify machine identity as (architecture_namespace, UUID); keep human alias qualification derived

**Rationale**

V1.3 canonical external identity is the pair (architecture_namespace, UUID). Local v1.3 authored references use UUIDs. Human-recognition aliases may be namespace-qualified for display, but alias qualification remains derived and is not provider namespace identity authority.

**Consequences**

Positive:
- Pre-v1.3 local authoring remains readable and compatible
- Cross-repo references become explicit and machine-parseable
- Global identity does not require a central ID allocator

### DEC-0077 — Emit workspace-attribution-federation.yaml as read-only cross-repo attribution index keyed by workspace routing identity that resolves to architecture_namespace

**Rationale**

Workspace repository keys remain local registration/routing/attribution handles. They resolve to the provider's architecture_namespace and must not be treated as the provider identity namespace. Canonical external identity remains (architecture_namespace, UUID), not a workspace-key-qualified local ADR alias.

**Consequences**

Positive:
- Agents and workspace tools resolve ADR embodiment without bare-id collapse
- Federation remains derived and does not mutate per-repo evidence

Negative:
- Workspace manifest repo keys remain stable for routing/attribution resolution to architecture_namespace, not as UUID identity namespaces


## Capabilities

### CAP-0038 — Federated Qualified Identity Resolution

Support unambiguous multi-repository entity references using architecture_namespace and UUID identity while retaining read-only provider authority and derived human alias qualification.




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0058 | Federation and aggregation layers MUST treat each repository as authoritative over its own canonical registries and… | MUST / design | automated |

### INV-0058

**Statement**

Federation and aggregation layers MUST treat each repository as
authoritative over its own canonical registries and MUST NOT mutate those
registries during federation.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Multi-repository architecture reasoning depends on repository ownership and
read-only aggregation remaining explicit.




## Physical Realization

**Systems**
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)

**Components**
- [ADR-PC-0001](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)

**References**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0007](ADR-L-0007-deterministic-documentation-projection.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0018](ADR-L-0018-schema-v1-2-and-normalized-semantic-foundation.md)
- [ADR-PS-0001](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0001 — Entity Registry and Discovery Index](../physical-component/ADR-PC-0001-entity-registry-and-discovery-index.md) | implements this logical authority | `ADR-PC-0001 -[:implements_logical]-> ADR-L-0012` |
| [ADR-PS-0001 — ADR Architecture Kit Discovery and Indexing System](../physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.md) | implements this logical authority | `ADR-PS-0001 -[:implements_logical]-> ADR-L-0012` |





---

*Generated from ADR-L-0012 by ADR Architecture Kit (projection v3)*