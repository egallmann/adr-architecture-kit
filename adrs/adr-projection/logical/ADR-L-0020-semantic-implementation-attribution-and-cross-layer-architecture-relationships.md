<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 17f6d327017553f50f10cc2a18eac5b918171fd965f364ffed8dca5631b14732
rendered_hash: 1f8697670dd3248ea6435ac7603c3737e10befe7d41b3ac41d2646778bfde1e1
-->

# ADR-L-0020: Semantic Implementation Attribution and Cross-Layer Architecture Relationships

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0020  
**Authoring contract:** authoring v1.5  
**Created:** 2026-08-13  
**Modified:** 2026-08-20  
**Authors:** erik.gallmann  
**Domains:** architecture, traceability, governance, identity  
**Tags:** attribution, semantic-claims, uuid, evidence  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0020 |
| Status | accepted |
| Decisions | 9 |
| Capabilities | 3 |
| Invariants | 10 |
| Physical realizations | [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md), [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md) |


## Context

ADR-L-0004 established implementation attribution as an explicit intent
surface. ADR-L-0019 made canonical machine identity a lowercase UUIDv7.
Attribution evidence still cited human aliases (`ADR-L-*`, `INV-*`) and
could not name typed relationships to nested architecture entities.

This ADR authorizes UUID-canonical semantic attribution evidence lines
(schema_version 1.5 and provisional 1.6). Version 1.6 adds optional source
pointer/span provenance, version-aware confidence rules, deterministic
loss-aware normalization, and a validated bidirectional linkage projection.
Version 1.5 remains byte-frozen and keeps its historical validation semantics.
This does not create ADR authoring schema 1.5 or 1.6, does
not create normalized model 3.0, and does not collapse extractor evidence
into architecture authority. A declaration is evidence of intent, not proof
of enforcement or correctness.

Architecture YAML remains authority. Decorators and extracted YAML are
untrusted declarations. ste-runtime must emit claims without loading ADR Kit
architecture state. Validation never mutates ADRs, registries, evidence input,
Architecture IR, or graph state. The validated projection has an authority
ceiling of validated derived evidence and is explicitly not admitted to the graph.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0116 | Canonical v1.5 claims require relationship, target UUID, and confidence | — |
| DEC-0117 | Raw evidence must not require target entity type | — |
| DEC-0118 | Apply the attribution matrix to repository-resolved entity type | — |
| DEC-0119 | Evidence claim verbs are not architecture relationship types | — |
| DEC-0120 | Legacy 1.0/1.2 evidence normalizes only with architecture state | — |
| DEC-0121 | Canonical output order is deterministic and idempotent | — |
| DEC-0122 | Duplicate semantic claims follow provenance-aware fail-closed rules | — |
| DEC-0123 | Coverage distinguishes unique semantic links from evidence occurrence | — |
| DEC-0124 | Extractors and legacy decorators must not load architecture state | — |

### DEC-0116 — Canonical v1.5 claims require relationship, target UUID, and confidence

**Rationale**

Each raw claim requires `relationship` (`implements` | `enforces` |
`embodies`), `target_entity_id` (lowercase UUIDv7), and `confidence`
(`declared` | `inferred` | `heuristic`). Records also require
`implementation_entity_id`, `implementation_entity_type`, and
`provenance` (`source_file`, `extractor`, optional `commit`). The
document uses an admitted evidence-attribution `schema_version` and
`type: implementation_attribution_evidence`. Decorator-generated claims
always use `confidence: declared`. Under v1.6, `implements` and `embodies`
admit declared, inferred, or heuristic confidence while `enforces` admits
declared only. Version 1.5 retains its historical confidence semantics.

### DEC-0117 — Raw evidence must not require target entity type

**Rationale**

Extractors and UUID decorators carry identity, not architecture type.
Optional `asserted_target_entity_type` is redundant evidence. If present,
architecture-aware validation compares it to the repository-resolved type
and fails on mismatch. It is never authority. Derived
`resolved_target_entity_type` belongs on validation results and coverage
reports, not on the required extractor schema.

### DEC-0118 — Apply the attribution matrix to repository-resolved entity type

**Rationale**

After `ArchitectureRepository.find_entity_by_uuid` (model 2.0), the
versioned mechanical vocabulary
admits: `implements` to adr, decision, capability, contract, interface,
implementation_decision; `enforces` to invariant only; `embodies` to
system, component, boundary. Unknown relationship, illegal resolved type,
or unresolved UUID fails closed. Version 1.6 additionally rejects inferred
or heuristic `enforces`; version 1.5 is not retroactively reinterpreted.
`superseded` and `deprecated` targets warn (INV-0028 posture).

### DEC-0119 — Evidence claim verbs are not architecture relationship types

**Rationale**

Evidence relationship names and the bidirectional linkage projection are
derived evidence. They are not
`RelationshipRecordV2.relationship_type` values and must not be written
into architecture relationship registries or Architecture IR.
`implementation_entity_id` remains extractor-owned and is not an admitted
model 2.0 architecture UUID (ADR-L-0019 DEC-0097). Shared English
(`implements`, `embodies`) does not project implementation surfaces into
the canonical graph. `build_embodiment_linkage` never persists links,
allocates graph identities, or performs graph admission.

### DEC-0120 — Legacy 1.0/1.2 evidence normalizes only with architecture state

**Rationale**

Attribution 1.0/1.2 remains readable under the v1.1 evidence schema and
normalizes through governed repository lookup. Targets 1.5 and 1.6 are
explicit; 1.5 remains the CLI default. Conversion preserves confidence
exactly and never invents claims, identities, types, pointers, or spans.
A conversion that would violate the target confidence policy or discard
v1.6-only provenance fails deterministically. The converter never rewrites
`.ste-workspace` or any supplied evidence file in place.

### DEC-0121 — Canonical output order is deterministic and idempotent

**Rationale**

Record order is `(implementation_entity_id, source_file, source_pointer,
start_line, end_line, extractor, commit or "")`. Claim order is `(relationship, target_entity_id,
asserted_target_entity_type or "")`. Unsorted raw input is valid.
Repeated canonicalization is idempotent for semantic content and
serialized canonical output.

### DEC-0122 — Duplicate semantic claims follow provenance-aware fail-closed rules

**Rationale**

The unique linkage key is `(implementation_entity_id, relationship,
target_entity_id)`. Across records with distinct provenance, occurrences
aggregate behind that link. Exact repeated claim-and-provenance occurrences
and conflicting qualifiers at the same occurrence fail closed. Provenance
participates only in occurrence ordering/fingerprinting, never semantic or
graph identity. This rule is not weakened for dogfood.

### DEC-0123 — Coverage distinguishes unique semantic links from evidence occurrence

**Rationale**

Existing coverage YAML keys remain. For v1.5/v1.6 input, ADR fields fill from
claims whose resolved type is `adr`. Additive unique-link counts use
`(implementation_entity_id, relationship, target_entity_id)` after
normalize/resolve. Occurrence counts, if present, must be named so they
cannot be mistaken for coverage. The supported `adr_kit.api` facade exposes
immutable request/result contracts, forward and reverse traversal, partial
results, and explicit non-admission fields. Neither metric proves correctness.

### DEC-0124 — Extractors and legacy decorators must not load architecture state

**Rationale**

ste-runtime and other extractors emit UUID claims without loading ADR Kit
architecture. Legacy alias decorators remain metadata producers
(`__implements_adrs__` / `__enforces_invariants__`) and must not resolve
aliases, load `ArchitectureRepository`, or synthesize
`__architecture_attribution_claims__`. Canonical UUID decorators alone
populate that claims attribute, with local UUIDv7 validation only.


## Capabilities

### CAP-0053 — Semantic Implementation Attribution

UUID-canonical typed claims connecting implementation surfaces to
architecture entities plus a validated, bidirectionally queryable derived
projection without collapsing evidence into authority.

**Acceptance criteria**
- raw claims require relationship, target UUID, and confidence
- resolved type is derived after repository lookup
- matrix rejects illegal relationship/type pairs
- v1.6 rejects non-declared enforcement claims without changing v1.5 semantics
- public SDK results expose authority ceiling and graph non-admission
- declaration is not treated as proof

### CAP-0054 — Repository-Aware Attribution Normalization

Translate supported evidence into explicitly selected canonical v1.5 or
v1.6 claims using governed architecture lookup and lossless conversion.

**Acceptance criteria**
- unresolved or ambiguous aliases fail closed
- output omits required target type
- normalize(normalize(x)) equals normalize(x)
- incompatible confidence or lossy downgrade fails deterministically
- default CLI path does not write workspace evidence

### CAP-0055 — Unique-Link Attribution Coverage

Informational coverage and public linkage traversal that preserve ADR
catalog keys and report unique semantic links separately from occurrences.

**Acceptance criteria**
- existing five coverage YAML keys remain
- v1.5/v1.6 ADR keys fill from resolved type adr
- unique-link counts are distinct from occurrence counts
- forward and reverse traversal return the same ordered link objects




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0103 | Raw v1.5 and v1.6 attribution claims MUST include relationship, lowercase UUIDv7 target_entity_id, and confidence | MUST / test | automated |
| INV-0104 | Architecture-aware v1.5 validation MUST fail closed when a claim UUID is missing, an alias or alias_ref is used as… | MUST / test | automated |
| INV-0105 | A v1.5 or v1.6 claim MUST be rejected when the resolved target entity type is not admitted for that relationship by… | MUST / test | automated |
| INV-0106 | Attribution evidence verbs and validated linkage projections MUST NOT be written into architecture relationship… | MUST / design | automated |
| INV-0107 | Duplicate (relationship, target_entity_id) within one attribution record MUST be an error | MUST / test | automated |
| INV-0108 | Identical semantic triple and occurrence provenance across records MUST be an error; distinct provenance MUST remain… | MUST / test | automated |
| INV-0109 | Implementation attribution declarations MUST NOT be treated as proof that the named architecture constraint is enforced | MUST / design | manual |
| INV-0110 | Legacy alias decorators and evidence extractors MUST NOT load ArchitectureRepository or synthesize canonical UUID… | MUST / design | automated |
| INV-0111 | Canonical normalized v1.5/v1.6 output MUST be sorted by its documented total order, preserve confidence, reject… | MUST / test | automated |
| INV-0112 | Equivalent legacy-alias and UUID declarations for the same implementation edge MUST NOT be dual-encoded on one surface | MUST / design | automated |

### INV-0103

**Statement**

Raw v1.5 and v1.6 attribution claims MUST include relationship, lowercase UUIDv7
target_entity_id, and confidence

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Extractors cannot invent architecture type; identity and declared
relationship are the required claim surface.

### INV-0104

**Statement**

Architecture-aware v1.5 validation MUST fail closed when a claim UUID is
missing, an alias or alias_ref is used as target_entity_id, or optional
asserted type mismatches the resolved type

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Canonical identity is UUID. Aliases are presentation and 1.0/1.2
translation input only.

### INV-0105

**Statement**

A v1.5 or v1.6 claim MUST be rejected when the resolved target entity type is not
admitted for that relationship by the mechanical vocabulary; v1.6 MUST also
reject inferred or heuristic `enforces` claims without changing v1.5 behavior

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

The matrix is architecture authority, not extractor opinion.

### INV-0106

**Statement**

Attribution evidence verbs and validated linkage projections MUST NOT be
written into architecture relationship registries, treated as
RelationshipRecordV2.relationship_type, or graph-admitted

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Implementation surfaces are not admitted architecture entities.

### INV-0107

**Statement**

Duplicate (relationship, target_entity_id) within one attribution record
MUST be an error

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

One record cannot independently restate the same semantic edge.

### INV-0108

**Statement**

Identical semantic triple and occurrence provenance across records MUST be
an error; distinct provenance MUST remain as independent occurrences of one link

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Independent extractors may observe the same edge; copy-paste duplicates
must not.

### INV-0109

**Statement**

Implementation attribution declarations MUST NOT be treated as proof that
the named architecture constraint is enforced

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

ADR Kit does not parse implementation source to prove behavior. INV-0030
remains a declared claim, not kit-automated proof.

### INV-0110

**Statement**

Legacy alias decorators and evidence extractors MUST NOT load
ArchitectureRepository or synthesize canonical UUID claim metadata from
alias arguments

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Architecture resolution is a validation/normalization concern, not a
decorator or extractor concern.

### INV-0111

**Statement**

Canonical normalized v1.5/v1.6 output MUST be sorted by its documented total
order, preserve confidence, reject lossy conversion, and be idempotent

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Deterministic serialization is required for diffs and federation, but
unsorted producer input remains valid.

### INV-0112

**Statement**

Equivalent legacy-alias and UUID declarations for the same implementation
edge MUST NOT be dual-encoded on one surface

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

True-duplicate errors stay in force. Dogfood may keep a legacy ADR-level
edge or migrate it to UUID, not both.




## Physical Realization

**Components**
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)

**References**
- [ADR-L-0004](ADR-L-0004-adr-to-implementation-traceability-via-decorators-and-metadata-attribution.md)
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PS-0002](../physical-system/ADR-PS-0002-adr-kit-authoring-compiler-and-validation-system.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | implements this logical authority | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0020` |
| [ADR-PC-0007 — Semantic Attribution Embodiment](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md) | implements this logical authority | `ADR-PC-0007 -[:implements_logical]-> ADR-L-0020` |




## Notes

Embodiment is ADR-PC-0007. Schema authority remains this repository.
ste-spec draft hand-off prose is pre-normative. Do not add 1.5 to
supported_adr_schema_versions. Evidence versions are advertised separately as
supported_evidence_attribution_versions, with provisional 1.6 preferred for
new producers. API contract 1.0 and package versions remain independent.
v1.1 relationship-registry enum drift is quarantined and is not repaired by
this ADR.


---

*Generated from ADR-L-0020 by ADR Architecture Kit (projection v3)*