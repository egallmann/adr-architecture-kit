<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 301df4b727cabfc666f01d4ea7905f07d6c469d37520c008ccb2235568fea729
rendered_hash: 2a5801305e1207aa41b1dc25c4d0d3e52ac3a188ba9f1e82debff2855383f6f5
-->

# ADR-L-0020: Semantic Implementation Attribution and Cross-Layer Architecture Relationships

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0020  
**Alias name:** semantic-implementation-attribution-and-cross-layer-architecture-relationships  
**Created:** 2026-08-13  
**Modified:** 2026-08-20  
**Authors:** adr-architecture-kit  
**Domains:** architecture, traceability, governance, identity  

## Architecture Position

Logical architecture authority for this subject. Neighborhood paths use structural bridges plus exactly one semantic architecture edge; they never invent ADR-to-ADR verbs.

## Architecture Neighborhood


### Semantic architecture inventory

- `implements_logical`: ADR-PC-0002 → ADR-L-0020
- `implements_logical`: ADR-PC-0007 → ADR-L-0020

## Neighbor Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0002 — Schema and Contract Validation](../physical-component/ADR-PC-0002-schema-and-contract-validation.md) | ADR-PC-0002 -[:implements_logical]-> ADR-L-0020 | `ADR-PC-0002 -[:implements_logical]-> ADR-L-0020` |
| [ADR-PC-0007 — Semantic Attribution Embodiment](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md) | ADR-PC-0007 -[:implements_logical]-> ADR-L-0020 | `ADR-PC-0007 -[:implements_logical]-> ADR-L-0020` |


### Lifecycle / association

- ADR-L-0004 -[:references]-> ADR-L-0020
- ADR-L-0020 -[:references]-> ADR-L-0004
- ADR-L-0020 -[:references]-> ADR-L-0013
- ADR-L-0020 -[:references]-> ADR-L-0019
- ADR-L-0020 -[:references]-> ADR-PC-0002
- ADR-L-0020 -[:references]-> ADR-PS-0002
- ADR-L-0020 -[:references]-> ADR-PC-0007
- ADR-L-0024 -[:references]-> ADR-L-0020

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


## Internal Structure

```mermaid
flowchart TB
  n_019ffdba_3c42_7c4a_a737_f6751a265d60["ADR-L-0020<br/>Semantic Implementation Attribution and Cross-Layer Architecture Relationships"]
  subgraph sg_capability["capability"]
    n_019ffdba_3c42_7578_b43f_ad19109d59d9["CAP-0053<br/>Semantic Implementation Attribution"]
    n_019ffdba_3c42_71ba_b81f_a2a24830abd6["CAP-0054<br/>Repository-Aware Attribution Normalization"]
    n_019ffdba_3c42_745c_9e37_85f7696cd43c["CAP-0055<br/>Unique-Link Attribution Coverage"]
  end
  subgraph sg_decision["decision"]
    n_019ffdba_3c42_700c_ac3f_8135e0139dfb["DEC-0116<br/>Canonical v1.5 claims require relationship, target UUID, and confidence"]
    n_019ffdba_3c42_73c1_b11c_d0a177cd522b["DEC-0117<br/>Raw evidence must not require target entity type"]
    n_019ffdba_3c42_7f40_b339_204a447bec81["DEC-0118<br/>Apply the attribution matrix to repository-resolved entity type"]
    n_019ffdba_3c42_7751_a81c_d738f411b299["DEC-0119<br/>Evidence claim verbs are not architecture relationship types"]
    n_019ffdba_3c42_7282_931f_92503f4079cb["DEC-0120<br/>Legacy 1.0/1.2 evidence normalizes only with architecture state"]
    n_019ffdba_3c42_705f_9935_76ed45c32cd7["DEC-0121<br/>Canonical output order is deterministic and idempotent"]
    n_019ffdba_3c42_7690_8f1b_ad8deaeed484["DEC-0122<br/>Duplicate semantic claims follow provenance-aware fail-closed rules"]
    n_019ffdba_3c42_7304_ab2f_bcd01cc6f9d3["DEC-0123<br/>Coverage distinguishes unique semantic links from evidence occurrence"]
    n_019ffdba_3c42_729a_a83f_a40c53d278fd["DEC-0124<br/>Extractors and legacy decorators must not load architecture state"]
  end
  subgraph sg_invariant["invariant"]
    n_019ffdba_3c42_7cbe_a121_06d3437129ed["INV-0103"]
    n_019ffdba_3c42_7c85_a63f_689e71c5236a["INV-0104"]
    n_019ffdba_3c42_7d33_9e1b_e22bc168fa7c["INV-0105"]
    n_019ffdba_3c42_74ea_993d_990027e528c0["INV-0106"]
    n_019ffdba_3c42_7e3a_a037_3b6c3087ef0a["INV-0107"]
    n_019ffdba_3c42_7da9_ac3e_879c2e5a88a4["INV-0108"]
    n_019ffdba_3c42_7ec4_852c_06396e99d050["INV-0109"]
    n_019ffdba_3c42_7a6d_9717_d8d96b6fa75d["INV-0110"]
    n_019ffdba_3c42_7230_8d39_ef047f583291["INV-0111"]
    n_019ffdba_3c42_72d4_982d_88224ca69e68["INV-0112"]
  end
  n_019ffdba_3c42_700c_ac3f_8135e0139dfb -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_705f_9935_76ed45c32cd7 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_71ba_b81f_a2a24830abd6 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7230_8d39_ef047f583291 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7282_931f_92503f4079cb -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_729a_a83f_a40c53d278fd -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_72d4_982d_88224ca69e68 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7304_ab2f_bcd01cc6f9d3 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_73c1_b11c_d0a177cd522b -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_745c_9e37_85f7696cd43c -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_74ea_993d_990027e528c0 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7578_b43f_ad19109d59d9 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7690_8f1b_ad8deaeed484 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7751_a81c_d738f411b299 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7a6d_9717_d8d96b6fa75d -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7c85_a63f_689e71c5236a -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7cbe_a121_06d3437129ed -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7d33_9e1b_e22bc168fa7c -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7da9_ac3e_879c2e5a88a4 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7e3a_a037_3b6c3087ef0a -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7ec4_852c_06396e99d050 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
  n_019ffdba_3c42_7f40_b339_204a447bec81 -->|"declared_in"| n_019ffdba_3c42_7c4a_a737_f6751a265d60
```

- `capability` CAP-0053 — Semantic Implementation Attribution
- `capability` CAP-0054 — Repository-Aware Attribution Normalization
- `capability` CAP-0055 — Unique-Link Attribution Coverage
- `decision` DEC-0116 — Canonical v1.5 claims require relationship, target UUID, and confidence
- `decision` DEC-0117 — Raw evidence must not require target entity type
- `decision` DEC-0118 — Apply the attribution matrix to repository-resolved entity type
- `decision` DEC-0119 — Evidence claim verbs are not architecture relationship types
- `decision` DEC-0120 — Legacy 1.0/1.2 evidence normalizes only with architecture state
- `decision` DEC-0121 — Canonical output order is deterministic and idempotent
- `decision` DEC-0122 — Duplicate semantic claims follow provenance-aware fail-closed rules
- `decision` DEC-0123 — Coverage distinguishes unique semantic links from evidence occurrence
- `decision` DEC-0124 — Extractors and legacy decorators must not load architecture state
- `invariant` INV-0103 — INV-0103
- `invariant` INV-0104 — INV-0104
- `invariant` INV-0105 — INV-0105
- `invariant` INV-0106 — INV-0106
- `invariant` INV-0107 — INV-0107
- `invariant` INV-0108 — INV-0108
- `invariant` INV-0109 — INV-0109
- `invariant` INV-0110 — INV-0110
- `invariant` INV-0111 — INV-0111
- `invariant` INV-0112 — INV-0112

## Capabilities

### CAP-0053: Semantic Implementation Attribution

UUID-canonical typed claims connecting implementation surfaces to
architecture entities plus a validated, bidirectionally queryable derived
projection without collapsing evidence into authority.


### CAP-0054: Repository-Aware Attribution Normalization

Translate supported evidence into explicitly selected canonical v1.5 or
v1.6 claims using governed architecture lookup and lossless conversion.


### CAP-0055: Unique-Link Attribution Coverage

Informational coverage and public linkage traversal that preserve ADR
catalog keys and report unique semantic links separately from occurrences.



## Decisions

### DEC-0116: Canonical v1.5 claims require relationship, target UUID, and confidence

**Rationale:**
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




### DEC-0117: Raw evidence must not require target entity type

**Rationale:**
Extractors and UUID decorators carry identity, not architecture type.
Optional `asserted_target_entity_type` is redundant evidence. If present,
architecture-aware validation compares it to the repository-resolved type
and fails on mismatch. It is never authority. Derived
`resolved_target_entity_type` belongs on validation results and coverage
reports, not on the required extractor schema.




### DEC-0118: Apply the attribution matrix to repository-resolved entity type

**Rationale:**
After `ArchitectureRepository.find_entity_by_uuid` (model 2.0), the
versioned mechanical vocabulary
admits: `implements` to adr, decision, capability, contract, interface,
implementation_decision; `enforces` to invariant only; `embodies` to
system, component, boundary. Unknown relationship, illegal resolved type,
or unresolved UUID fails closed. Version 1.6 additionally rejects inferred
or heuristic `enforces`; version 1.5 is not retroactively reinterpreted.
`superseded` and `deprecated` targets warn (INV-0028 posture).




### DEC-0119: Evidence claim verbs are not architecture relationship types

**Rationale:**
Evidence relationship names and the bidirectional linkage projection are
derived evidence. They are not
`RelationshipRecordV2.relationship_type` values and must not be written
into architecture relationship registries or Architecture IR.
`implementation_entity_id` remains extractor-owned and is not an admitted
model 2.0 architecture UUID (ADR-L-0019 DEC-0097). Shared English
(`implements`, `embodies`) does not project implementation surfaces into
the canonical graph. `build_embodiment_linkage` never persists links,
allocates graph identities, or performs graph admission.




### DEC-0120: Legacy 1.0/1.2 evidence normalizes only with architecture state

**Rationale:**
Attribution 1.0/1.2 remains readable under the v1.1 evidence schema and
normalizes through governed repository lookup. Targets 1.5 and 1.6 are
explicit; 1.5 remains the CLI default. Conversion preserves confidence
exactly and never invents claims, identities, types, pointers, or spans.
A conversion that would violate the target confidence policy or discard
v1.6-only provenance fails deterministically. The converter never rewrites
`.ste-workspace` or any supplied evidence file in place.




### DEC-0121: Canonical output order is deterministic and idempotent

**Rationale:**
Record order is `(implementation_entity_id, source_file, source_pointer,
start_line, end_line, extractor, commit or "")`. Claim order is `(relationship, target_entity_id,
asserted_target_entity_type or "")`. Unsorted raw input is valid.
Repeated canonicalization is idempotent for semantic content and
serialized canonical output.




### DEC-0122: Duplicate semantic claims follow provenance-aware fail-closed rules

**Rationale:**
The unique linkage key is `(implementation_entity_id, relationship,
target_entity_id)`. Across records with distinct provenance, occurrences
aggregate behind that link. Exact repeated claim-and-provenance occurrences
and conflicting qualifiers at the same occurrence fail closed. Provenance
participates only in occurrence ordering/fingerprinting, never semantic or
graph identity. This rule is not weakened for dogfood.




### DEC-0123: Coverage distinguishes unique semantic links from evidence occurrence

**Rationale:**
Existing coverage YAML keys remain. For v1.5/v1.6 input, ADR fields fill from
claims whose resolved type is `adr`. Additive unique-link counts use
`(implementation_entity_id, relationship, target_entity_id)` after
normalize/resolve. Occurrence counts, if present, must be named so they
cannot be mistaken for coverage. The supported `adr_kit.api` facade exposes
immutable request/result contracts, forward and reverse traversal, partial
results, and explicit non-admission fields. Neither metric proves correctness.




### DEC-0124: Extractors and legacy decorators must not load architecture state

**Rationale:**
ste-runtime and other extractors emit UUID claims without loading ADR Kit
architecture. Legacy alias decorators remain metadata producers
(`__implements_adrs__` / `__enforces_invariants__`) and must not resolve
aliases, load `ArchitectureRepository`, or synthesize
`__architecture_attribution_claims__`. Canonical UUID decorators alone
populate that claims attribute, with local UUIDv7 validation only.





## Invariants

### INV-0103

**Statement:** Raw v1.5 and v1.6 attribution claims MUST include relationship, lowercase UUIDv7
target_entity_id, and confidence
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
Extractors cannot invent architecture type; identity and declared
relationship are the required claim surface.


### INV-0104

**Statement:** Architecture-aware v1.5 validation MUST fail closed when a claim UUID is
missing, an alias or alias_ref is used as target_entity_id, or optional
asserted type mismatches the resolved type
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
Canonical identity is UUID. Aliases are presentation and 1.0/1.2
translation input only.


### INV-0105

**Statement:** A v1.5 or v1.6 claim MUST be rejected when the resolved target entity type is not
admitted for that relationship by the mechanical vocabulary; v1.6 MUST also
reject inferred or heuristic `enforces` claims without changing v1.5 behavior
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
The matrix is architecture authority, not extractor opinion.


### INV-0106

**Statement:** Attribution evidence verbs and validated linkage projections MUST NOT be
written into architecture relationship registries, treated as
RelationshipRecordV2.relationship_type, or graph-admitted
  
**Scope:** global  
**Enforcement:** must (design)

**Rationale:**
Implementation surfaces are not admitted architecture entities.


### INV-0107

**Statement:** Duplicate (relationship, target_entity_id) within one attribution record
MUST be an error
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
One record cannot independently restate the same semantic edge.


### INV-0108

**Statement:** Identical semantic triple and occurrence provenance across records MUST be
an error; distinct provenance MUST remain as independent occurrences of one link
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
Independent extractors may observe the same edge; copy-paste duplicates
must not.


### INV-0109

**Statement:** Implementation attribution declarations MUST NOT be treated as proof that
the named architecture constraint is enforced
  
**Scope:** global  
**Enforcement:** must (design)

**Rationale:**
ADR Kit does not parse implementation source to prove behavior. INV-0030
remains a declared claim, not kit-automated proof.


### INV-0110

**Statement:** Legacy alias decorators and evidence extractors MUST NOT load
ArchitectureRepository or synthesize canonical UUID claim metadata from
alias arguments
  
**Scope:** global  
**Enforcement:** must (design)

**Rationale:**
Architecture resolution is a validation/normalization concern, not a
decorator or extractor concern.


### INV-0111

**Statement:** Canonical normalized v1.5/v1.6 output MUST be sorted by its documented total
order, preserve confidence, reject lossy conversion, and be idempotent
  
**Scope:** global  
**Enforcement:** must (test)

**Rationale:**
Deterministic serialization is required for diffs and federation, but
unsorted producer input remains valid.


### INV-0112

**Statement:** Equivalent legacy-alias and UUID declarations for the same implementation
edge MUST NOT be dual-encoded on one surface
  
**Scope:** global  
**Enforcement:** must (design)

**Rationale:**
True-duplicate errors stay in force. Dogfood may keep a legacy ADR-level
edge or migrate it to UUID, not both.






---

*Generated from ADR-L-0020 by ADR Architecture Kit (projection v3)*