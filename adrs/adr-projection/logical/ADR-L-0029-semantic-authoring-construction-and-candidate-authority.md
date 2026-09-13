<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: c22e18e8abca2b05bae09bff62791f2005d618735a8f0c6c73bc705f80a12dd7
rendered_hash: 61b80aa8d804de0d224c7c743b325167db61b74f73b4d8a71413380124bd4038
-->

# ADR-L-0029: Semantic Authoring Construction and Candidate Authority

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0029  
**Authoring contract:** authoring v1.5  
**Created:** 2026-09-13  
**Authors:** erik.gallmann  
**Domains:** architecture, authoring, semantic-authority, schema-governance, extensibility, identity, topology, consumer-bindings  
**Tags:** semantic-authoring, construction, detached-candidate, authority-boundary, successor-contracts, r1-design-lock  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0029 |
| Status | accepted |
| Decisions | 16 |
| Invariants | 19 |


## Context

ADC 1.0, accepted by ADR-L-0026 and qualified by ADR-L-0027, established
read-only authoring-domain discovery. ADR-Kit now needs deterministic
semantic construction, but construction is distinct from persistence,
repository admission, governance promotion, Runtime admission, Runtime
Snapshot mutation, and implementation conformance.

The primitive construction unit is a schema-governed Semantic Fragment, not
an ADR document. Canonical and consumer-qualified semantics require one
governed compiler mechanism without erasing semantic ownership. ADR-Kit owns
canonical meaning; consumers own the meaning of qualified custom types.

The exact successor contracts authorized below do not yet exist. This ADR
authorizes their bounded definition and preserves the current supported ADR
representation for this promotion. It creates no release, package,
persistence, or implementation capability claim.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0128 | Make a schema-governed Semantic Fragment the primitive constructible authoring unit | — |
| DEC-0129 | Make successful construction produce detached candidate semantic state or artifacts | — |
| DEC-0184 | Permit UUIDv7 identity establishment during create-construction without implying admission | — |
| DEC-0185 | Use one contract-driven construction mechanism for canonical and consumer-qualified fragments | — |
| DEC-0186 | Require exact contracts to close the semantics of every constructible type | — |
| DEC-0187 | Authorize the set-oriented construct_authoring_set capability concept | — |
| DEC-0188 | Converge prepared fragments and compact contract-oriented input into one semantic compiler | — |
| DEC-0189 | Make validation and construction use one canonical semantic validation authority | — |
| DEC-0190 | Require complete graph or set conformance before classifying a result Constructed | — |
| DEC-0191 | Require exact forward interpretation and normalized equivalence for Constructed results | — |
| DEC-0192 | Authorize bounded successor contract definition after this authority promotion | — |
| DEC-0193 | Preserve owner-local topology vocabulary for future authoring 1.7 | — |
| DEC-0194 | Preserve NormativeProposition as an explicit peer semantic type to Invariant | — |
| DEC-0195 | Require Python and TypeScript/Node to expose peer host capabilities over one semantic authority | — |
| DEC-0196 | Keep persistence and transaction semantics outside construction authority | — |
| DEC-0197 | Limit this promotion to accepted architectural authority | — |

### DEC-0128 — Make a schema-governed Semantic Fragment the primitive constructible authoring unit

**Rationale**

Decision, Invariant, NormativeProposition, Component, Interface, System,
SystemBoundary, DataFlow, EvidenceExpectation, and other contract-governed
constructs may each be fragments and may compose other fragments. An ADR is
a higher-order composition or synthesis, not the primitive create operation.

### DEC-0129 — Make successful construction produce detached candidate semantic state or artifacts

**Rationale**

Construction does not persist repository source, reserve aliases, perform
governance acceptance or promotion, admit architecture into a Runtime graph,
mutate a Runtime Snapshot, or establish implementation conformance. Those
authorities remain separately governed.

### DEC-0184 — Permit UUIDv7 identity establishment during create-construction without implying admission

**Rationale**

A valid caller-supplied UUIDv7 is validated and preserved; when absent,
ADR-Kit MAY mint UUIDv7 for an independently identity-bearing canonical or
custom fragment. Update preserves the UUID and reference does not recreate
it. Identity is never derived from alias, prose, path, hash, ordering,
source location, or composition position. Alias reservation remains separate.
Determinism begins after identity establishment over exact request, contract,
custom registry, reference basis, and target authoring contract.

### DEC-0185 — Use one contract-driven construction mechanism for canonical and consumer-qualified fragments

**Rationale**

Canonical type meaning remains ADR-Kit-owned while custom type meaning
remains consumer-owned. ADR-Kit may validate custom structural and relational
semantics only where the exact custom contract declares them. Custom means
extensible, not ungoverned.

### DEC-0186 — Require exact contracts to close the semantics of every constructible type

**Rationale**

Contracts must describe applicable input shape, identity, create/update/
reference/retire posture, field ownership and field presence, composition,
allowed parents, references, inbound and outbound relationships, endpoint
constraints, relationship identity posture, cardinality, and ordering.
Relationship validity is contract-declared wherever the contract model can
express it rather than hidden in host-language branching.

### DEC-0187 — Authorize the set-oriented construct_authoring_set capability concept

**Rationale**

One request may create, update, reference, retire where permitted, relate,
and compose multiple fragments. ADR synthesis is composition over fragments.
One-fragment and one-ADR operations are trivial subsets of the same semantic
operation, not separate compilers.

### DEC-0188 — Converge prepared fragments and compact contract-oriented input into one semantic compiler

**Rationale**

Compact input is semantic compression, not semantic inference. ADR-Kit may
supply declared structural or default ceremony but must not invent decisions,
rationales, relationships, NormativePropositions, applicability, materiality,
or other missing intent. AI or agent reasoning crosses the boundary as
explicit typed semantic intent.

### DEC-0189 — Make validation and construction use one canonical semantic validation authority

**Rationale**

The future validate_authoring capability is diagnostic-oriented and shares
the construction validator. Validation fails closed while aggregating every
independently discoverable violation. A dependent check made impossible by
an earlier violation is reported blocked or unresolved, not silently omitted.
Diagnostics are governed semantic output.

### DEC-0190 — Require complete graph or set conformance before classifying a result Constructed

**Rationale**

Individually schema-valid fragments do not guarantee a valid construction.
The complete supplied result must conform to exact canonical and custom
contracts across shape, identity, composition, references, relationships,
cardinality, cross-fragment constraints, and whole-result invariants. The
bounded outcomes are Constructed, Rejected, Unavailable, and Unresolved;
there is no empty-success fallback.

### DEC-0191 — Require exact forward interpretation and normalized equivalence for Constructed results

**Rationale**

Successful construction proves explicit intent to candidate artifacts, exact
forward interpretation, normalized semantic result, and equivalence to the
compiler's intended projection. The proof is bounded by available canonical
and custom authority; structural round-trip does not claim undeclared custom
domain meaning.

### DEC-0192 — Authorize bounded successor contract definition after this authority promotion

**Rationale**

Later exact definitions may establish Authoring Domain Contract 1.1, Custom
Entity Contract 1.0, Authoring Construction Contract 1.0, authoring 1.7,
normalized-model 2.4, architecture-interpretation 1.1, semantic-core 1.2,
and the whole-qualified architecture-authoring@1.0 contract set/profile.
Authorization does not claim any resource is implemented, qualified, or
released.

### DEC-0193 — Preserve owner-local topology vocabulary for future authoring 1.7

**Rationale**

Forward topology construction uses topology_key, from_key, and to_key.
Historical authoring 1.5 and 1.6 remain immutable and readable. The admitted
verbs are calls, depends_on, publishes_to, subscribes_to, reads_from, and
writes_to. composed_of remains derived, and consumes_interface remains
deferred pending authority and endpoint reconciliation. Topology values do
not acquire canonical UUID identity.

### DEC-0194 — Preserve NormativeProposition as an explicit peer semantic type to Invariant

**Rationale**

Future construction requires explicit semantic content and exactly one of
MUST, MUST NOT, SHOULD, SHOULD NOT, or MAY. It must not infer propositions,
materiality, applicability, competence, or effectivity from prose, add an
independent NP lifecycle, or add NP implementation attribution under the
current attribution contract.

### DEC-0195 — Require Python and TypeScript/Node to expose peer host capabilities over one semantic authority

**Rationale**

Future construction semantics execute through the canonical Rust/WASM
semantic core. Python and TypeScript/Node remain peer public host adapters.
No second TypeScript compiler, host-specific semantic defaults, or Python
subprocess semantic implementation is authorized. Browser publication may
advertise a narrower execution-profile capability.

### DEC-0196 — Keep persistence and transaction semantics outside construction authority

**Rationale**

Later authority must separately design alias reservation, base-revision
locking, conflicts, atomic writes, rollback, Git mutation, governance
promotion, and durable authoring transaction history. Construction does not
absorb those semantics.

### DEC-0197 — Limit this promotion to accepted architectural authority

**Rationale**

This ADR is sufficient authority for later contract-definition and
implementation slices, but it adds no successor contract resource, SDK
operation, persistence behavior, package capability, release claim, or
implementation conformance evidence.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0113 | Construction MUST NOT be treated as persistence, repository admission, governance promotion, Runtime admission or… | MUST / design | manual |
| INV-0114 | Valid supplied UUIDv7 identity MUST be preserved, update MUST preserve UUID identity, and ADR-Kit MUST NOT silently… | MUST / design | automated |
| INV-0115 | Composing an independently identity-bearing fragment into another fragment or ADR MUST NOT create, replace, or… | MUST / design | automated |
| INV-0116 | Every meaning-affecting construction or interpretation contract or source input MUST be explicitly qualified;… | MUST / design | automated |
| INV-0117 | Compact input MUST NOT authorize ADR-Kit to invent semantically material architectural intent. | MUST / design | manual |
| INV-0118 | ADR-Kit MUST NOT claim custom semantic meaning, fields, relationship semantics, composition semantics, or domain… | MUST / design | automated |
| INV-0119 | Custom contract migration MUST be explicit; retirement MUST preserve UUID identity and sufficient provenance and… | MUST / design | automated |
| INV-0120 | Every relationship admitted into a successful result MUST be authorized by an exact qualified canonical or custom… | MUST / design | automated |
| INV-0121 | ADR-Kit MUST NOT classify construction as successful unless the complete requested semantic result conforms to all… | MUST / design | automated |
| INV-0122 | Validation MUST report all independently discoverable violations, and a dependent check blocked by a prior violation… | MUST / design | automated |
| INV-0123 | A contract violation MUST identify, where deterministically available, a stable typed code, affected semantic… | MUST / design | automated |
| INV-0124 | Public validation and construction MUST derive findings from the same canonical semantic validation authority. | MUST / design | automated |
| INV-0125 | ADR-Kit MUST NOT claim to validate semantic properties that are not machine-evaluable under exact qualified… | MUST / design | manual |
| INV-0126 | A candidate MUST NOT be classified Constructed unless exact target validation and canonical rematerialization… | MUST / design | automated |
| INV-0127 | Construction MUST preserve Constructed, Rejected, Unavailable, and Unresolved as distinct outcomes and MUST NOT use… | MUST / design | automated |
| INV-0165 | NormativeProposition force MUST use the exact closed vocabulary, and construction MUST NOT infer NP existence,… | MUST / design | manual |
| INV-0166 | Topology keys and topology-local relationship endpoints MUST remain distinct from canonical UUID identity, and… | MUST / design | automated |
| INV-0167 | Public Python and TypeScript/Node capabilities MUST obtain equivalent semantics from the same canonical execution… | MUST / design | automated |
| INV-0168 | Runtime or another downstream system MAY retain an exact custom contract for historical reproducibility, but… | MUST / design | manual |

### INV-0113

**Statement**

Construction MUST NOT be treated as persistence, repository admission, governance promotion, Runtime admission or Snapshot mutation, alias reservation, or implementation-conformance authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Detached candidate construction remains responsibility-scoped.

### INV-0114

**Statement**

Valid supplied UUIDv7 identity MUST be preserved, update MUST preserve UUID identity, and ADR-Kit MUST NOT silently replace supplied identity or derive canonical identity from presentation or source-location properties; create MAY mint UUIDv7 without implying admission.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Canonical identity is independent of aliases, prose, paths, hashes, ordering, and composition position.

### INV-0115

**Statement**

Composing an independently identity-bearing fragment into another fragment or ADR MUST NOT create, replace, or derive that child's canonical identity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Parent policy governs legal assembly, not whether a child can exist before its parent.

### INV-0116

**Statement**

Every meaning-affecting construction or interpretation contract or source input MUST be explicitly qualified; mutable latest, repository HEAD, installed-current custom contract, host default, UI state, filesystem order, and undocumented behavior MUST NOT substitute for exact authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Construction reproducibility requires an explicit semantic basis.

### INV-0117

**Statement**

Compact input MUST NOT authorize ADR-Kit to invent semantically material architectural intent.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Compression may omit ceremony, but it cannot create missing intent.

### INV-0118

**Statement**

ADR-Kit MUST NOT claim custom semantic meaning, fields, relationship semantics, composition semantics, or domain correctness beyond the exact qualified custom contract; a custom entity MUST still conform to the governed identity and construction envelope.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Custom extensibility remains qualified semantic authority.

### INV-0119

**Statement**

Custom contract migration MUST be explicit; retirement MUST preserve UUID identity and sufficient provenance and contract qualification for historical reconstruction; canonical promotion of the same architectural referent MUST preserve UUID identity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Version changes cannot become ambient reinterpretation or identity replacement.

### INV-0120

**Statement**

Every relationship admitted into a successful result MUST be authorized by an exact qualified canonical or custom contract and satisfy its endpoint and field constraints.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Relationship semantics cannot be hidden in host-language branching.

### INV-0121

**Statement**

ADR-Kit MUST NOT classify construction as successful unless the complete requested semantic result conforms to all applicable exact contracts.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Local schema validity is insufficient for graph or set conformance.

### INV-0122

**Statement**

Validation MUST report all independently discoverable violations, and a dependent check blocked by a prior violation MUST be represented as blocked or unresolved rather than successful.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Failure-closed diagnostics must preserve reachable accountability.

### INV-0123

**Statement**

A contract violation MUST identify, where deterministically available, a stable typed code, affected semantic location or request key, violated rule, observed and expected state, and safe remediation guidance.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Diagnostics are governed semantic output rather than arbitrary strings.

### INV-0124

**Statement**

Public validation and construction MUST derive findings from the same canonical semantic validation authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Divergent validator and compiler interpretations are semantic drift.

### INV-0125

**Statement**

ADR-Kit MUST NOT claim to validate semantic properties that are not machine-evaluable under exact qualified contracts, including prose materiality, architectural quality, or meaning-preserving identity continuity without such authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Structural determinism cannot certify natural-language meaning or architectural judgment.

### INV-0126

**Statement**

A candidate MUST NOT be classified Constructed unless exact target validation and canonical rematerialization equivalence both succeed.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Forward schema validity alone does not prove semantic equivalence.

### INV-0127

**Statement**

Construction MUST preserve Constructed, Rejected, Unavailable, and Unresolved as distinct outcomes and MUST NOT use empty or partial success to conceal missing authority or unresolved references.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Epistemic uncertainty must remain observable.

### INV-0165

**Statement**

NormativeProposition force MUST use the exact closed vocabulary, and construction MUST NOT infer NP existence, materiality, applicability, authority, effectivity, governance lifecycle, or implementation attribution from prose or outside the current attribution contract.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

NP remains a peer semantic type to Invariant with explicit content and authority dimensions.

### INV-0166

**Statement**

Topology keys and topology-local relationship endpoints MUST remain distinct from canonical UUID identity, and consumes_interface MUST remain deferred until separately reconciled.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Forward topology vocabulary is owner-local and does not create canonical entity identity.

### INV-0167

**Statement**

Public Python and TypeScript/Node capabilities MUST obtain equivalent semantics from the same canonical execution authority and MUST NOT maintain independent semantic implementations for the promoted capability.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Host adapters expose authority; they do not own construction meaning.

### INV-0168

**Statement**

Runtime or another downstream system MAY retain an exact custom contract for historical reproducibility, but retention MUST NOT make that downstream system the defining semantic authority for the contract.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Retained evidence supports reconstruction without moving contract ownership.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0027](ADR-L-0027-public-binding-construction-and-release-parity.md)
- [ADR-L-0028](ADR-L-0028-normative-semantic-authority-and-materialization-foundation.md)

**References**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0015](ADR-L-0015-adr-governance-state-and-override-semantics.md)
- [ADR-L-0017](ADR-L-0017-forward-authoring-ergonomics-for-split-physical-adr-types.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0023](ADR-L-0023-consumer-semantic-extension-contract.md)
- [ADR-L-0024](ADR-L-0024-cross-language-consumer-bindings-and-typescript-distribution.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0027](ADR-L-0027-public-binding-construction-and-release-parity.md)
- [ADR-L-0028](ADR-L-0028-normative-semantic-authority-and-materialization-foundation.md)





## Notes

This promotion is based on the human-reviewed source `ADR-Kit Semantic
Authoring Construction — Candidate Design Lock R1.0`, reviewed 2026-09-13,
on the basis of `69d1bdca6ab536cd18cc777d7d209bfaff990abe`. The design source
is evidence for this promotion, not a second normative authority. This ADR is
self-sufficient accepted authority after promotion.

Explicitly deferred successor work includes the exact ADC 1.1 27-type matrix;
Custom Entity Contract 1.0 JSON Schema and property vocabulary; Authoring
Construction Contract 1.0 request and response DTOs; the authoring 1.6 to 1.7
source delta; normalized-model 2.3 to 2.4 delta; architecture-interpretation
1.0 to 1.1 delta; relationship-mode and endpoint matrices; diagnostic
enumeration and transport; contract and fingerprint domain prefixes; private
Rust compiler IR; Runtime retained-custom-contract paths; browser capability
advertisement; persistence and transaction design; and consumes_interface
reconciliation. None is implemented, advertised, or released by this ADR.

The current supported authoring representation is used intentionally. No
unsupported normative_propositions field is introduced, and no schema
validation is weakened. No successor contract directory or resource is
created by this promotion.


---

*Generated from ADR-L-0029 by ADR Architecture Kit (projection v3)*