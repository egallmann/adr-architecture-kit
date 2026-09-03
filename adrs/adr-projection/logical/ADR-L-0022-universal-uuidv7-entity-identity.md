<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: b7d013039c6d1cb6d82aff8240634edf81a81a34dc0e45ef0f1236c23ad90823
rendered_hash: dc2076e894f6552ab32cde3cacd62f4c8b67d96dd82b007cb5225d6bb2f2315b
-->

# ADR-L-0022: Universal UUIDv7 Entity Identity

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0022  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-15  
**Authors:** erik.gallmann  
**Domains:** architecture, identity, schema-governance  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0022 |
| Status | accepted |
| Decisions | 17 |
| Invariants | 11 |


## Context

ADR-L-0019 correctly separated immutable UUIDv7 machine identity from human-oriented aliases, but DEC-0097 admitted that identity envelope for only a selected set of entity kinds. Other durable ADR-domain records still expose alias-shaped values as `id`, use alias references across artifacts, or omit identity entirely. Requirements snapshots, requirement items, decision ledgers, ledger decisions, reviews, overrides, constraints, non-functional requirements, gaps, system boundaries, data flows, and evidence expectations are examples.
That split creates an accumulating identity tax. A consumer cannot determine from the name `id` whether a field is immutable canonical identity, a human alias, a content-derived projection key, or an owner-local structural handle. New schema families such as rules could repeat the ambiguity unless schema admission is bound to one universal entity-identity invariant.
This ADR extends ADR-L-0019 rather than replacing its successful UUID, alias, reference, namespace, collision, and migration semantics. It supersedes the narrow entity-kind boundary in DEC-0097, establishes a structural test for entityhood, distinguishes canonical entities from local value objects and derived projections, and requires future schema contracts to make that classification explicit. Semantic schema versions, package namespaces, corpus migration, and removal of old compatibility surfaces remain implementation decisions that must be reviewed before destructive application.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0130 | Require the ADR-L-0019 identity envelope for every canonical independently addressable ADR-domain entity | Supersedes Admit UUID identity only for independently addressable durable entity kinds (DEC-0097) |
| DEC-0131 | Define entityhood by actual or potential participation in the system graph | — |
| DEC-0132 | Require canonical entity references to use UUIDs while aliases remain orientation | — |
| DEC-0133 | Keep owner-local value objects free of entity identity | — |
| DEC-0134 | Require stable UUIDv7 identity for every graph node and edge projection | — |
| DEC-0135 | Promote current durable alias-identified authoring and governance records to entities | — |
| DEC-0136 | Bind future rule evidence and other entity schemas to the same invariant | — |
| DEC-0137 | Require semantic version boundaries and explicit package mappings for identity migration | — |
| DEC-0138 | Migrate identity with a sealed reviewable map and semantic parity proof | — |
| DEC-0139 | Remove obsolete compatibility surfaces only through an explicit reviewed gate | — |
| DEC-0140 | Treat effective relationships and relationship assertions as distinct entities | — |
| DEC-0141 | Model generated inverse traversal as a derived projection unless independently authored | — |
| DEC-0142 | Govern aliases for newly promoted entity families as an explicit namespace contract | — |
| DEC-0143 | Bind identity changes to family-scoped semantic versions and explicit package mappings | — |
| DEC-0144 | Preserve a graph-vNext compatibility posture while identity contracts advance | — |
| DEC-0145 | Define the universal allocation map as a sealed, reviewable lifecycle artifact | — |
| DEC-0146 | Keep universal identity migration blocked until every human gate is explicit | — |

### DEC-0130 — Require the ADR-L-0019 identity envelope for every canonical independently addressable ADR-domain entity

**Rationale**

Every canonical independently addressable ADR-domain entity authors an immutable lowercase RFC 9562 UUIDv7 in `id`, a governed type-prefixed `alias_id`, and a stable-by-default human-oriented `alias_name`. This supersedes DEC-0097's closed entity-kind allowlist without weakening the existing identity, alias, namespace, collision, or migration rules.

**Traceability**
- Supersedes: Admit UUID identity only for independently addressable durable entity kinds (DEC-0097)

### DEC-0131 — Define entityhood by actual or potential participation in the system graph

**Rationale**

Any record that participates, or may later participate, as a node or edge in the system graph is an entity and must have the universal identity envelope before graph admission. Independent addressability, cross-artifact references, lifecycle, provenance, admission, governance meaning, and durable semantic continuity are evidence of graph eligibility. Uncertainty resolves toward entity identity; only records explicitly prohibited from graph participation may be classified as value objects.

### DEC-0132 — Require canonical entity references to use UUIDs while aliases remain orientation

**Rationale**

Canonical local references and relationship endpoints use the target entity UUID. Cross-namespace references use provider namespace, UUID, kind, and fingerprint. `alias_id`, `alias_name`, and derived `alias_ref` are human orientation and lookup presentation only and never foreign keys or retargetable identity.

### DEC-0133 — Keep owner-local value objects free of entity identity

**Rationale**

A record may remain a value object only when its contract explicitly excludes it from present and future graph participation and it has no independent lifecycle, authority, cross-owner reference, or durable semantic continuity. It has no `id`, `alias_id`, or `alias_name`. An owner-local structural handle is named `key` or `<role>_key`, is scoped to its owner, and cannot enter graph output. Any later graph eligibility requires promotion to an entity through a schema version and migration before graph admission.

### DEC-0134 — Require stable UUIDv7 identity for every graph node and edge projection

**Rationale**

A graph projection reuses the persisted UUID and aliases of its canonical node or edge entity. Relationship assertions, topology nodes and edges, unresolved findings, bindings, evidence claims, or other derived candidates cannot enter the system graph until canonical authority has allocated and persisted their UUIDv7 identity. Content hashes remain fingerprints or deduplication keys, never identity. Purely non-graph diagnostics may use deterministic keys, and generators never mint authoritative UUIDs opportunistically during regeneration.

### DEC-0135 — Promote current durable alias-identified authoring and governance records to entities

**Rationale**

Constraints, non-functional requirements, authored gaps, system boundaries, data flows, evidence expectations, requirements snapshots and their referencable requirement items, decision ledgers and ledger decisions, steelman reviews and referencable objections, objection overrides, remediation ledgers, and independently governed remediation entries are graph-eligible records and therefore receive the universal identity envelope in their next semantic contract version. Topology nodes and edges, relationship assertions, unresolved findings, bindings, and evidence claims also require the envelope whenever they can participate in the graph.

### DEC-0136 — Bind future rule evidence and other entity schemas to the same invariant

**Rationale**

Every new schema that models records eligible for graph participation, including rule, evidence, governance, authoring, and normalized-model contracts, must require the universal identity envelope. Rule instances, evidence entities, and graph-participating binding or assertion records use UUID identity; external references add provider namespace, kind, and fingerprint. A JSON Schema `$id` is contract URI identity and does not substitute for instance entity identity.

### DEC-0137 — Require semantic version boundaries and explicit package mappings for identity migration

**Rationale**

Changing alias-only identity, adding required UUID and alias fields, changing canonical references, or reclassifying `id` as `key` is a semantic contract change and must occur in a new family-scoped schema version. Canonical repository and installed-package resource paths are explicit mappings rather than inferred from an unqualified version label. Existing contract bytes are not silently rewritten in place.

### DEC-0138 — Migrate identity with a sealed reviewable map and semantic parity proof

**Rationale**

Migration inventories every promoted entity and reference before minting, records owner path and structural pointer, preserves the human alias, proposes an alias name deterministically, mints each UUID once into a sealed map, rewrites canonical references atomically, validates the entire write set, and proves idempotence and semantic parity. Counts alone are not proof and a migration cannot silently remint or retarget an entity.

### DEC-0139 — Remove obsolete compatibility surfaces only through an explicit reviewed gate

**Rationale**

Being the sole current external consumer permits a clean break but does not make deletion implicit. Exact schema versions, parser modes, package namespaces, public API shims, migration inputs, and corpus formats proposed for removal must be enumerated with dependency evidence and approved before deletion. Identity admission does not create a release tag or publication authority.

### DEC-0140 — Treat effective relationships and relationship assertions as distinct entities

**Rationale**

An effective relationship is an ENTITY and graph-eligible record with its own UUIDv7 identity and stable alias envelope. A relationship assertion is also a graph-eligible ENTITY with its own UUIDv7 identity and assertion alias; one effective relationship may therefore have multiple assertions that are independently governed. A content fingerprint such as `relationship_id` or `assertion_id` is a deduplication and provenance key, never a substitute for canonical entity identity. A VALUE_OBJECT is excluded from graph participation and a DERIVED_PROJECTION reuses canonical identity.

### DEC-0141 — Model generated inverse traversal as a derived projection unless independently authored

**Rationale**

An inverse edge generated from an effective relationship reuses the persisted relationship UUID and is a DERIVED_PROJECTION, not a second canonical entity. An independently authored or governed inverse relationship is a separate ENTITY only when its own lifecycle, authority, or provenance warrants it. Generators do not mint UUIDs to materialize a traversal view. Any exception requires explicit human approval.

### DEC-0142 — Govern aliases for newly promoted entity families as an explicit namespace contract

**Rationale**

Every newly promoted entity kind receives a unique governed type-prefixed alias namespace before migration. Namespace allocation, high-water marks, collision dispositions, and retired aliases are recorded in the migration contract; aliases remain human orientation and never become canonical references. Unknown or colliding legacy aliases block sealing rather than being silently reassigned.

### DEC-0143 — Bind identity changes to family-scoped semantic versions and explicit package mappings

**Rationale**

The vNext identity contract is family-scoped: authoring, architecture-discovery, normalized-model, governance, and evidence-attribution versions advance independently when their identity semantics change. Canonical repository paths and installed package resource paths are explicit mappings, not labels inferred from a version number; existing schema bytes and the stable authoring compatibility surface remain intact until a reviewed version admission changes them.

### DEC-0144 — Preserve a graph-vNext compatibility posture while identity contracts advance

**Rationale**

Graph-vNext may expose canonical UUID identity, relationship/assertion distinction, and derived inverse projections while retaining a deterministic compatibility projection for existing graph consumers. A graph projection is derived state; graph-vNext admission requires semantic parity evidence and does not authorize corpus migration, package behavior changes, or opportunistic UUID minting.

### DEC-0145 — Define the universal allocation map as a sealed, reviewable lifecycle artifact

**Rationale**

The allocation map records canonical owner path, structural pointer, entity kind, legacy alias, proposed UUIDv7, final alias, disposition, and provenance. It progresses through draft, collision-review, approved, and SEALED states; sealing is one-way for a migration pass and requires exact inventory, collision dispositions, vNext contract approval, graph posture approval, and semantic-parity evidence.

### DEC-0146 — Keep universal identity migration blocked until every human gate is explicit

**Rationale**

No universal corpus migration may mint UUIDs, rewrite references, or remove compatibility surfaces while alias collisions, family-scoped vNext contracts, graph-vNext posture, allocation-map contract, or map sealing remain unapproved. Working review packets are evidence for human decisions only and are not durable architecture authority; each gate requires explicit human approval before migration.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0130 | Every record that participates or may participate as a node or edge in the system graph has an immutable lowercase… | MUST / design | automated |
| INV-0131 | Canonical entity references and relationship endpoints use UUIDs rather than aliases or owner-local keys. | MUST / design | automated |
| INV-0132 | Human aliases orient and resolve for presentation but never define canonical identity or retarget a reference. | MUST / design | automated |
| INV-0133 | Owner-local value objects are explicitly ineligible for graph participation, have no entity identity, and name any… | MUST / design | automated |
| INV-0134 | Every graph projection reuses a persisted canonical node or edge UUID; only explicitly non-graph diagnostics may use… | MUST / design | automated |
| INV-0135 | Every new or revised schema declares graph eligibility and entity value-object and projection boundaries and… | MUST / policy | automated |
| INV-0136 | Identity migration mints each entity UUID once from a reviewed sealed map and proves reference and semantic parity… | MUST / policy | automated |
| INV-0137 | No legacy schema package namespace parser mode public compatibility shim or corpus format is removed without… | MUST / policy | automated |
| INV-0138 | Effective relationships and relationship assertions are distinct graph-eligible entities, each with its own UUIDv7… | MUST / design | automated |
| INV-0139 | Generated inverse traversal reuses the effective relationship UUID and is a DERIVED_PROJECTION unless an… | MUST / design | automated |
| INV-0140 | Universal identity migration remains blocked until collision, vNext, graph, allocation-contract, and allocation-map… | MUST / policy | automated |

### INV-0130

**Statement**

Every record that participates or may participate as a node or edge in the system graph has an immutable lowercase RFC 9562 UUIDv7 `id`, a governed `alias_id`, and a human-oriented `alias_name` before graph admission.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Universal canonical identity prevents new alias-only identity debt.

### INV-0131

**Statement**

Canonical entity references and relationship endpoints use UUIDs rather than aliases or owner-local keys.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Reference stability must not depend on presentation or local structure.

### INV-0132

**Statement**

Human aliases orient and resolve for presentation but never define canonical identity or retarget a reference.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Alias evolution must remain independent from identity.

### INV-0133

**Statement**

Owner-local value objects are explicitly ineligible for graph participation, have no entity identity, and name any local structural handle as a key rather than an id.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Field vocabulary must reveal whether a value is canonical identity.

### INV-0134

**Statement**

Every graph projection reuses a persisted canonical node or edge UUID; only explicitly non-graph diagnostics may use deterministic keys, and generators do not mint canonical identity without canonical authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Derived state cannot become an accidental authority source.

### INV-0135

**Statement**

Every new or revised schema declares graph eligibility and entity value-object and projection boundaries and mechanically enforces the universal identity invariant.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

The invariant applies to rules and future schema families as well as ADR authoring.

### INV-0136

**Statement**

Identity migration mints each entity UUID once from a reviewed sealed map and proves reference and semantic parity after atomic application.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

A migration must not remint retarget or partially apply canonical identity.

### INV-0137

**Statement**

No legacy schema package namespace parser mode public compatibility shim or corpus format is removed without explicit reviewed disposition.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Clean-break authority must be precise rather than inferred.

### INV-0138

**Statement**

Effective relationships and relationship assertions are distinct graph-eligible entities, each with its own UUIDv7 identity and alias envelope; fingerprints are not identity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Multiple assertions may explain one effective relationship without collapsing their independent provenance or governance lifecycle.

### INV-0139

**Statement**

Generated inverse traversal reuses the effective relationship UUID and is a DERIVED_PROJECTION unless an independently authored inverse is governed as a separate entity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Traversal views must not create duplicate canonical identity.

### INV-0140

**Statement**

Universal identity migration remains blocked until collision, vNext, graph, allocation-contract, and allocation-map seal gates are explicitly approved and evidence is sealed.

**Scope:** global

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Architectural closure and implementation readiness are separate states.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)

**References**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)





## Notes

Accepted from the 2026-08-15 human lock that every record which participates or may participate in the system graph requires stable UUIDv7 identity. This ADR is the durable authority for the identity doctrine and its admission gates. Exact semantic-version, package-namespace, corpus-migration, and obsolete-surface dispositions must be promoted through governed contracts and explicit human approval; local design journals and review packets are non-authoritative working state.


---

*Generated from ADR-L-0022 by ADR Architecture Kit (projection v3)*