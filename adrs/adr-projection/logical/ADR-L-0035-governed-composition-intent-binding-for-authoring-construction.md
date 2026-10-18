<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 30cc889e7e3f25424f7dc57447f05ab96853fae9a76838a814a5b36590385540
rendered_hash: 7140e0ad8ec05d266cd7f9e3cceec13251b69d5114c71b1b84715ae324a3196b
-->

# ADR-L-0035: Governed Composition-Intent Binding for Authoring Construction

## Identity / Status

**Type:** logical<br>
**Status:** proposed<br>
**Alias:** ADR-L-0035<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-10-18<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, authoring, semantic-authority, determinism, conformance<br>
**Tags:** authoring-construction, composition-intent, authoring-1.7, architecture-interpretation-1.2, proposed-authority<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0035 |
| Status | proposed |
| Decisions | 5 |
| Invariants | 6 |


## Context

ACC 1.1 accepts a composition intent of parent, child, relation, and
ordering, then fails closed. Accepted authority already requires
composition to preserve child identity, to omit an exactly embedded child
from minimal source roots, and to treat composition ownership as semantic
provenance distinct from integrity evidence. It does not select one
Authoring 1.7 property, one Architecture Interpretation 1.2 semantic field,
one endpoint resolution rule, or one owner of the embedded bytes.

ADC 1.1 permits entity/decision under adr/logical and declares that child
an identity-keyed set whose presentation order is not identity. AI 1.2
declares adr/logical#/decisions an ordered sequence of child identities.
Those statements govern different facts. Neither statement, nor schema
occurrence of a decision object, interprets composition_intent.ordering or
the relation token.

Historical ACC 1.0 uses the token contains in frozen conformance and
describes endpoints as a request key or exact reference. Its historical
execution ignores relation and rewrites some child fields. That behavior
remains historical authority for unchanged C01-C42 only. It is not ACC 1.1
construction authority, and this decision does not carry that behavior forward.

This ADR defines the minimum binding that later construction can execute
for one parent and child capability. It does not execute composition,
amend a published contract, or change semantic-core protocol 1.5. Its
status remains proposed until a separate acceptance decision.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0274 | Bind one composition intent to one governed containment row or fail closed | Related INV-0284, INV-0285 |
| DEC-0275 | Resolve composition endpoints only to same-request fragment request keys | Related INV-0285 |
| DEC-0276 | Let the compiler write the selected parent property from separate prepared children | Related INV-0286, INV-0287 |
| DEC-0277 | Treat ordering as parent membership sequence and never as child identity | Related INV-0288 |
| DEC-0278 | Require semantic, integrity, and diagnostic evidence before composition execution can be reported | Related INV-0289 |

### DEC-0274 — Bind one composition intent to one governed containment row or fail closed

**Rationale**

A composition intent is the tuple {parent, child, relation, ordering}.
Execution MAY succeed only when that tuple selects exactly one row of the
binding matrix below. The row selects exactly one Authoring 1.7 property
and exactly one AI 1.2 semantic_field_key. Schema uniqueness, a historical
renderer, and an open relation pattern are not selectors.

The closed relation vocabulary of this ADR is the single token contains.
For the initial row, contains means that the child definition is a member
of the selected parent property. It is not a normalized relationship type,
not composed_of, and not permission to embed the child in any other
property. ACC 1.0 execution that ignored relation, embedded every logical
child into decisions, rewrote aliases, or rewrote rationales is rejected
as the meaning of this token.

The initial matrix has one row and no others:

parent semantic type: adr/logical
child semantic type: entity/decision
relation: contains
Authoring 1.7 property: decisions
Authoring pointer: /decisions
AI 1.2 semantic_field_key: adr/logical#/decisions
AI ordering: ordered_sequence
AI destination: child_membership
AI identity match: child_uuid
AI multiplicity: reject_duplicate_identity
AI value semantics: child_identity_membership
child identity: canonical UUIDv7, not positional
byte owner: compiler, and only when the prepared parent lacks decisions
endpoint resolution: exactly one same-request fragment request_key

A later accepted ADR MAY add rows. It MUST NOT change this row without
superseding this decision. This ADR does not declare rows for the other
semantic types.

The selected row is consistent with published ADC 1.1 and AI 1.2, and
execution MUST re-check that consistency against the qualified resources.
The child composition policy MUST name the parent in allowed_parents,
use mode fragment_composition, and preserve child identity. The parent
composition policy MUST use mode root_fragment. The qualified AI
disposition for adr/logical#/decisions MUST remain child_membership,
ordered_sequence, child_uuid, reject_duplicate_identity, and
child_identity_membership. Disagreement is Unavailable. Execution MUST
NOT override the resource and MUST NOT choose a different field.

Fragment composition_keys do not identify a composition, a property, or
a child. They have no governed target. A non-empty composition_keys array
on any fragment makes the request Unavailable.

Outcome aggregation for one request is closed. Any Rejected composition
rejects the request. Otherwise any Unresolved composition leaves the
request Unresolved. Otherwise any Unavailable composition leaves the
request Unavailable. Otherwise every composition is bound by a matrix row.
Partial embedding is forbidden. Empty compositions remain the existing
non-composition path and are outside this binding.

Closed cases:

Unknown relation, including composed_of: Rejected,
authoring_construction.composition.relation_unknown.
Known relation with no matrix row for the resolved types: Unavailable,
authoring_construction.composition.binding_unavailable.
Qualified ADC or AI resource disagrees with the selected row: Unavailable,
authoring_construction.composition.authority_inconsistent.
Non-empty composition_keys: Unavailable,
authoring_construction.composition.key_unbound.
Endpoint matches no request_key and no request-visible reference identity:
Unresolved, authoring_construction.composition.endpoint_unresolved.
Endpoint equals a fragment reference key or target, or a reference-basis
reference_id or canonical UUID, and is not one create request_key:
Rejected, authoring_construction.composition.reference_not_definition.
That equality recognizes a reference. It does not resolve or copy it.
Endpoint matches more than one request_key: Rejected,
authoring_construction.composition.endpoint_ambiguous.
Parent or child operation is reference: Rejected,
authoring_construction.composition.reference_not_definition.
Parent or child operation is retire: Rejected,
authoring_construction.composition.operation_unsupported.
Parent or child operation is update: Unavailable,
authoring_construction.composition.update_unavailable.
Parent or child input_mode is compact: Rejected,
authoring_construction.composition.compact_input_forbidden.
Parent and child are the same fragment, or the containment edges cycle:
Rejected, authoring_construction.composition.cycle.
The same parent and child pair occurs more than once: Rejected,
authoring_construction.composition.duplicate_membership.
The same child identity is bound to more than one parent, or any fragment
canonical UUID is repeated: Rejected,
authoring_construction.composition.duplicate_identity.
Two children of one parent field share an ordering value: Rejected,
authoring_construction.composition.ordering_conflict.
The prepared parent contains the selected property, including an empty
array or null: Rejected,
authoring_construction.composition.ownership_conflict.

Diagnostics use the ACC 1.1 sort key. Until a semantic unit UUID exists,
the identity component is the stable unresolved sentinel and the request
key remains integrity payload. All applicable diagnostics are retained.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Import ACC 1.0 request-key-or-exact-reference and ignore relation | ACC 1.1 does not restate that endpoint rule, and the historical renderer is not a relation or field selector. Importing it would publish an interpreter this authority rejects. |
| Treat contains as generic containment into any child array | The token is not a property name. A generic reading would invent a second field selector beside the binding row and AI 1.2. |

**Consequences**

Positive:
- One request tuple has one auditable containment or a named failure.
- Later parent and child pairs can be added as rows without redefining contains or this row.

Negative:
- Every pair outside the initial row remains Unavailable, including pairs ADC already permits.
- Reference endpoints and update merges are not available in this capability.

**Traceability**
- Related invariants: INV-0284
- Related invariants: INV-0285

### DEC-0275 — Resolve composition endpoints only to same-request fragment request keys

**Rationale**

For this capability, parent and child MUST each equal exactly one
fragment request_key in the same construction request. The match is exact
string equality. The fragment operation MUST be create and its input_mode
MUST be prepared. The parent fragment semantic type MUST be adr/logical.
The child fragment semantic type MUST be entity/decision. Parent and child
request keys MUST differ.

The resolver MUST NOT bind an endpoint through a fragment reference, a
sealed reference-basis entry, an alias, a canonical UUID, a source path,
or a source_ref. Consulting those identities to copy bytes or to accept
the endpoint is forbidden. Recognizing that an unbound string equals one
of those reference identities is only the Rejected diagnostic in
DEC-0274. A reference never becomes a definition.

Request-array position is not an endpoint and is not precedence. There is
no fallback from an unresolved request_key to another identifier space.

**Traceability**
- Related invariants: INV-0285

### DEC-0276 — Let the compiler write the selected parent property from separate prepared children

**Rationale**

This ADR selects compiler-owned containment and rejects both verification
of a pre-written child and any combination of the two writers.

The composition intent is the sole authority for membership of the
selected property. The child definition is a separate prepared fragment.
After identity establishment, the compiler inserts the child's complete
canonical object into the parent property. The prepared parent MUST NOT
already contain that property. Absence means the key is not present.
An empty array, null, or any other value is a conflicting prepared writer
and is Rejected. Exact equality between a prepared value and the
compiler result is not acceptance and is not a second success path.

The child canonical object is the prepared child fields plus the one
established child id and no other key. Identity establishment is the
existing create rule: preserve a supplied UUIDv7, or mint one UUIDv7 when
create omits id. Composition MUST NOT mint a second id, derive an id, or
replace an id while embedding. The embedded id MUST equal the child
candidate identity.

Every other child field is preserved exactly, including alias_id,
alias_name, summary, rationale, and every optional decision field present
on the prepared child. The compiler MUST NOT add, remove, rename, retype,
default, or rewrite a child field. It MUST NOT fabricate an alias, rewrite
a rationale, or infer meaning that the child fields do not already state.
Optional fields that the author omitted stay omitted. Serialization key
order belongs to the existing adr-kit.authoring-yaml/v1 profile and is not
a semantic edit. JSON deep equality after that canonical parse is the
equality test. A loss, addition, or rewrite is Rejected,
authoring_construction.composition.child_mutation. An embedded id that
differs from the child candidate id is Rejected,
authoring_construction.composition.identity_mutation.

Parent fields other than the selected property are copied unchanged. The
only authorized parent mutations are establishment of the parent id and
insertion of the selected array. The compiler MUST NOT invent
schema_version, context, title, aliases, or any other parent field. If
those prepared fields are insufficient for Authoring 1.7, existing
authoring validation rejects them. Composition MUST NOT supply them to
force success.

The selected array contains one element per bound child and no other
elements. Its order is the order defined by DEC-0277. The parent document
is then subject to ordinary Authoring 1.7 validation. The child remains a
candidate artifact of kind authoring_fragment, validated as the Authoring
1.7 decision object. The child is omitted from candidate_source_basis
roots only after the embedded element is an exact subtree of the parent.
Omitting the child without that proof, or retaining it as a root after
that proof, is Rejected,
authoring_construction.composition.containment_accounting.

The selected semantic_field_key records parent membership. It does not
replace, summarize, or become the child's semantic fields. Child field
meaning remains on the child semantic unit, as ADR-L-0034 already requires.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Verify an already prepared exact child and do not modify the parent | The composition intent would not construct containment from a separate child fragment. The historical positive request shape omits the parent property, so verification alone cannot produce the Authoring document. It also leaves two copies without a single writer. |
| Accept either exact prepared containment or compiler insertion | The two paths are different compilers even when their bytes can be proved equal. Exact-match verification would still make prepared parent bytes an authority for membership. This capability has one writer. |

**Consequences**

Positive:
- Membership, child bytes, and source-root omission have one owner and one proof.
- Prepared parent prose and identity stay intact.

Negative:
- An author who already embedded the child must remove the parent property before this capability can bind the intent.
- Update of an existing document is outside this capability because no merge rule is defined.

**Traceability**
- Related invariants: INV-0286
- Related invariants: INV-0287

### DEC-0277 — Treat ordering as parent membership sequence and never as child identity

**Rationale**

ADC entity/decision ordering_policy identity_keyed_set with material false
and AI 1.2 ordered_sequence on adr/logical#/decisions do not contradict
each other. The ADC statement governs the child unit: canonical UUIDv7 is
the child identity, and presentation position MUST NOT identify, mint, or
replace that child. The AI statement governs the parent field: the
sequence of child identities in decisions is semantic.

composition_intent.ordering is the authored sequence key for that parent
field. It applies only because the selected AI disposition says
ordered_sequence. The compiler sorts sibling children by that integer
ascending and emits the decisions array in that order. Ordering values
need not be dense or zero-based. They MUST be unique among children of
the same parent field. An equal value is a conflict. The compositions
array index, fragment array index, mint order, and source order MUST NOT
break the tie or become the sequence.

The integer is not written onto the child and is not a child field. Child
identity remains the established UUIDv7. Reordering the compositions array
while preserving ordering values MUST NOT change the parent bytes.

The semantic value of the parent field is the induced sequence of child
canonical UUIDs. Two integer assignments that induce the same UUID
sequence produce the same parent field. The composition record still
retains each authored integer so the intent is auditable. ADR logical
source_declared_sequence is satisfied by this explicit key, not by request
order.

**Traceability**
- Related invariants: INV-0288

### DEC-0278 — Require semantic, integrity, and diagnostic evidence before composition execution can be reported

**Rationale**

A bound composition is proved only by a composition record that separates
meaning from integrity. The record is not defined by semantic-core
protocol 1.5, and this ADR does not add it there. Protocol 1.5 keeps
composition_resolution false. No implementation may report composition
resolution, seal a composed basis, or return Constructed under protocol
1.5.

An additive semantic-core protocol successor, protocol 1.6, is required
before execution. Protocol 1.6 transports this record and may set
composition_resolution true only when every composition in the request is
bound and every record is present. It MUST NOT edit protocol 1.5. It is
not the semantic authority for the binding; an accepted form of this ADR
is. If a protocol const and this ADR disagree, execution is Unavailable.
construct_authoring_set and the other currently false ACC 1.1 capability
flags stay false. No new ACC, ADC, AI, Authoring, Normalized Model, or
CEC version is required for the binding itself.

Each bound intent produces one record. Records sort by parent canonical
UUID, ordering, then child canonical UUID.

Semantic fields: parent_canonical_uuid, child_canonical_uuid,
parent_semantic_type, child_semantic_type, relation, authoring_property,
semantic_field_key, ordering, resolution_kind. For this capability
resolution_kind is request. The parent field's semantic sequence is the
ordered child UUIDs, not the compositions array index.

Integrity fields: parent_request_key, child_request_key, parent_source_ref,
child_source_ref, parent_content_digest, child_content_digest,
induced_sequence_index, identity_disposition, prepared_property_absent,
exact_subtree, child_candidate_artifact_retained, child_source_root_omitted.
induced_sequence_index is the zero-based position after the ordering sort.
The four proof flags are true on success. Qualification is the request's
existing exact ACC 1.1, ADC 1.1, Authoring 1.7, and AI 1.2 basis. The
record MUST NOT carry a different qualification.

Diagnostics are the closed codes in DEC-0274 plus child_mutation,
identity_mutation, and containment_accounting from DEC-0276. They are not
semantic values. Non-evidence, which MUST NOT establish meaning or
success, includes the compositions array index, repository paths, alias
text, generated ids other than the established canonical UUIDs, digest
equality used as a substitute for field equality, and composed_of.
composed_of remains an AI interpretation of authored system topology, not
a forward composition relation.

This ADR is proposed. Acceptance is a separate decision. Until both
acceptance and protocol 1.6 exist, composition-bearing ACC 1.1 requests
remain Unavailable under the current fail-closed gate, including the
existing authoring_construction.composition.evidence_unavailable result.
This ADR authorizes no Rust construction, no Constructed outcome, no
repository binding, and no persistence.

The future conformance matrix, and not a root-count assertion, is the
execution oracle. It is not authorized for implementation by this
proposed ADR.

Positive cases, after acceptance and protocol 1.6: one adr/logical create
parent and one entity/decision create child; relation contains; distinct
request_key endpoints; empty composition_keys; prepared parent lacks
decisions; child fields are a complete decision except an id that may be
minted; the embedded element equals the child object; the embedded id
equals the child artifact id; the child remains a candidate artifact and
is absent from source roots; the parent remains a source root; a repeated
entropy seed is byte-identical; permuting the compositions array does not
change parent bytes when ordering values are unchanged; two children emit
in ordering-sort order rather than request order.

Negative cases, after that same gate: unknown relation; parent or child
type outside the matrix; duplicate membership; duplicate ordering; missing
endpoint; ambiguous request_key; reference or reference-basis endpoint;
reference or retire operation; compact input; prepared decisions present;
self-containment; the same child under two parents; a mutated child field;
a second child id; the child both embedded and selected as a root; a
non-empty composition_keys array; direct use of composed_of as a relation.
Update remains Unavailable.

Regression that remains in force now and after implementation: frozen ACC
1.0 C01-C42, including C05 and C07 minimal-root digests; ACC 1.1
non-composition sealed bases; protocol 1.5 composition_resolution false;
no relabeling of C01-C42 as ACC 1.1 runtime coverage.

**Consequences**

Positive:
- A later protocol can transport only facts this decision already fixes.
- Reviewers can accept or reject the binding without an implementation disguised as a contract edit.

Negative:
- Composition-bearing requests stay Unavailable through this proposal.
- Execution requires a later accepted ADR plus an additive protocol before any code change.

**Traceability**
- Related invariants: INV-0289





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0284 | One ACC composition intent MUST select exactly one accepted binding row, one Authoring 1.7 property, and one AI 1.2… | MUST / design | automated |
| INV-0285 | Composition parent and child endpoints in this capability MUST resolve to exactly one same-request create fragment… | MUST / design | automated |
| INV-0286 | For a bound composition, the compiler MUST own the selected parent property, the prepared parent MUST omit that… | MUST / design | automated |
| INV-0287 | Embedding MUST preserve the child canonical UUIDv7 and every child semantic field exactly, MUST NOT mint a second… | MUST / design | automated |
| INV-0288 | composition_intent.ordering MUST determine only the semantic sequence of child identities in the selected parent… | MUST / design | automated |
| INV-0289 | This proposed binding MUST NOT amend ACC 1.0, ACC 1.1, ADC 1.1, AI 1.2, Authoring 1.7, NM 2.4, CEC 1.0, or… | MUST / design | manual |

### INV-0284

**Statement**

One ACC composition intent MUST select exactly one accepted binding row, one Authoring 1.7 property, and one AI 1.2 semantic_field_key, or the request MUST fail closed as Rejected, Unresolved, or Unavailable under the closed case table. Unknown relations MUST be Rejected. Pairs without a row MUST be Unavailable. The relation contains MUST mean membership in the selected property only.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

An open relation pattern and a historical renderer are not field selectors.

**Upheld by decisions**
- Bind one composition intent to one governed containment row or fail closed (DEC-0274)

### INV-0285

**Statement**

Composition parent and child endpoints in this capability MUST resolve to exactly one same-request create fragment request_key each, and a reference, alias, canonical UUID, or source location MUST NOT become a definition.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Endpoint resolution is explicit because ACC 1.1 does not define it and ACC 1.0 endpoint wording is not imported.

**Upheld by decisions**
- Bind one composition intent to one governed containment row or fail closed (DEC-0274)
- Resolve composition endpoints only to same-request fragment request keys (DEC-0275)

### INV-0286

**Statement**

For a bound composition, the compiler MUST own the selected parent property, the prepared parent MUST omit that property, and a prepared value MUST NOT be accepted as an alternate or verifying writer.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Prepared containment and compiler containment are different authorities, so this capability admits only one.

**Upheld by decisions**
- Let the compiler write the selected parent property from separate prepared children (DEC-0276)

### INV-0287

**Statement**

Embedding MUST preserve the child canonical UUIDv7 and every child semantic field exactly, MUST NOT mint a second identity or rewrite aliases or rationales, and MUST retain the child as a candidate artifact while omitting it from source roots only under exact-subtree proof.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Parent membership is not a projection of the child, and source-root omission is not an identity operation.

**Upheld by decisions**
- Let the compiler write the selected parent property from separate prepared children (DEC-0276)

### INV-0288

**Statement**

composition_intent.ordering MUST determine only the semantic sequence of child identities in the selected parent field. It MUST NOT identify the child, be stored as a child field, or be replaced by request array position.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

ADC identity-keyed child identity and AI ordered parent membership are both true and govern different facts.

**Upheld by decisions**
- Treat ordering as parent membership sequence and never as child identity (DEC-0277)

### INV-0289

**Statement**

This proposed binding MUST NOT amend ACC 1.0, ACC 1.1, ADC 1.1, AI 1.2, Authoring 1.7, NM 2.4, CEC 1.0, or semantic-core protocol 1.5, and MUST NOT by itself authorize composition execution, a Constructed outcome, repository binding, or persistence.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

The missing authority is a decision. Publishing it as proposed does not make composition available.

**Upheld by decisions**
- Require semantic, integrity, and diagnostic evidence before composition execution can be reported (DEC-0278)



## Decision / Intent Traceability

### Decision Traceability

```mermaid
flowchart LR
  %% Decision traceability
  n_01a1514b_805c_75ff_a7ee_e98d9d102cff["Bind one composition intent to one governed containment row or fail closed (DEC-0274)"]
  n_01a1514b_805c_75ff_a7ee_e98ef774ad1f["Resolve composition endpoints only to same-request fragment request keys (DEC-0275)"]
  n_01a1514b_805c_75ff_a7ee_e98fd08780d2["Let the compiler write the selected parent property from separate prepared children (DEC-0276)"]
  n_01a1514b_805c_75ff_a7ee_e9900b046f24["Treat ordering as parent membership sequence and never as child identity (DEC-0277)"]
  n_01a1514b_805c_75ff_a7ee_e9913dbcd63e["Require semantic, integrity, and diagnostic evidence before composition execution can be reported (DEC-0278)"]
  n_01a1514b_805c_75ff_a7ee_e992bdc5673c["INV-0284"]
  n_01a1514b_805c_75ff_a7ee_e9938eb9705e["INV-0285"]
  n_01a1514b_805d_762f_9733_a657fe39a26f["INV-0286"]
  n_01a1514b_805d_762f_9733_a658b38110fb["INV-0287"]
  n_01a1514b_805d_762f_9733_a6594aac3aa9["INV-0288"]
  n_01a1514b_805d_762f_9733_a65a91055d91["INV-0289"]
  n_01a1514b_805c_75ff_a7ee_e98d9d102cff -->|"enforces"| n_01a1514b_805c_75ff_a7ee_e992bdc5673c
  n_01a1514b_805c_75ff_a7ee_e98d9d102cff -->|"enforces"| n_01a1514b_805c_75ff_a7ee_e9938eb9705e
  n_01a1514b_805c_75ff_a7ee_e98ef774ad1f -->|"enforces"| n_01a1514b_805c_75ff_a7ee_e9938eb9705e
  n_01a1514b_805c_75ff_a7ee_e98fd08780d2 -->|"enforces"| n_01a1514b_805d_762f_9733_a657fe39a26f
  n_01a1514b_805c_75ff_a7ee_e98fd08780d2 -->|"enforces"| n_01a1514b_805d_762f_9733_a658b38110fb
  n_01a1514b_805c_75ff_a7ee_e9900b046f24 -->|"enforces"| n_01a1514b_805d_762f_9733_a6594aac3aa9
  n_01a1514b_805c_75ff_a7ee_e9913dbcd63e -->|"enforces"| n_01a1514b_805d_762f_9733_a65a91055d91
```





## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)
- [ADR-L-0033](ADR-L-0033-governed-candidate-binding-for-authoring-construction.md)
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)

**References**
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)
- [ADR-L-0033](ADR-L-0033-governed-candidate-binding-for-authoring-construction.md)
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)





## Notes

Status is proposed. This file is a review surface, not accepted authority.
Do not promote it to accepted in the change that introduces it.

The binding chosen here is compiler-owned insertion of separate prepared
children. Verification of a pre-embedded child, and any dual-writer
combination, are rejected alternatives recorded on DEC-0276.

Explicitly outside this capability, and therefore not open semantic
questions inside it: reference-basis endpoints, update and merge,
composition_keys as selectors, additional semantic-type rows, protocol 1.6
publication, Normalized Model interpretation of composed roots, ledger
derivation, and Constructed qualification. ACC 1.0 C01-C42 stay frozen.

After separate acceptance, the only authorized implementation change is
bounded as follows. Publish additive semantic-core protocol 1.6 whose
composition record contains only the fields named in DEC-0278. Leave
protocol 1.5 unchanged. Then, and only then, teach ACC 1.1 basis preparation
to bind the one matrix row or fail closed with the named diagnostics, insert
the child canonical object, and pass the resulting containment proof to the
existing minimal-root selector. Host adapters pass that result through
unchanged. Do not call the historical ACC 1.0 fragment renderer. Do not
return Constructed. Do not bind a repository or persist. Add the positive
and negative fixtures named in DEC-0278, and keep C01-C42 and current
non-composition seals unchanged. Stop there.


---

*Generated from ADR-L-0035 by ADR Architecture Kit (projection v3)*