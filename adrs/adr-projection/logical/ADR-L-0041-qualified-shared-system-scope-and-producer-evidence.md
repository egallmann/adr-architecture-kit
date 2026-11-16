<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 56ce61a9870ae15f6cee63e1bc226746877db0879f7d932398dfcea8534734c5
rendered_hash: 147c28fbc3206a357b94b0ea9e45913b85bc913ebce8ac4fd045632fe46b252d
-->

# ADR-L-0041: Qualified Shared-System Scope and Producer Evidence

## Identity / Status

**Type:** logical<br>
**Status:** accepted<br>
**Alias:** ADR-L-0041<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-11-08<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, semantic-authority, conformance<br>
**Tags:** shared-system, provider-scope, source-evidence, v0.13<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0041 |
| Status | accepted |
| Decisions | 6 |
| Invariants | 6 |


## Context

PR #194 is merged at develop 37a91de52602af54bc184ec7278b470d6277360a and independently
qualified. Private execution covers Physical System Data Flow/Boundary and 20 of 26
labels. System direct-object containment qualifies, while semantic execution remains
Unavailable. AI 1.5 recipes require unique_unit_and_producer_before_applicability;
ACC 1.5 shared_descriptor requires independently qualified existing unit type and
shared identity. Neither a minimal sealed basis nor the fixed inherited detached
context proves a complete relevant provider claim universe or an existing producer.
Existing provider registry lookup implements historical model versions, not this
forward evidence handoff. This ADR adds the minimum scope and existing-unit
qualification rule, preserving accepted semantic meaning and conditional reuse.
It establishes no actual provider capability or executed output.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-9029 | Qualify the complete authoritative provider source snapshot before System applicability | Refines Treat federation as a read-only aggregation layer over per-repo canonical registries (DEC-0045), Use provider-authoritative conflict resolution for federated entity definitions (DEC-0046) |
| DEC-9030 | Reuse only an existing provider-qualified System unit with one authorized defining occurrence | Refines Authorize explicit scoped declaring-ADR lifecycle propagation (DEC-9003), Account for all 27 types while selecting only applicable entity destinations (DEC-9021) |
| DEC-9031 | Account for every descriptor and preserve literal lifecycle and contextual meaning | Refines Carry qualified inherited-lifecycle facts in existing open NM metadata (DEC-9004), Compare inherited lifecycle meaning and independently verify its authority (DEC-9005) |
| DEC-9032 | Separate provider authority, complete membership, unit binding and independent replay | Refines Distinguish authored summaries, literal representation copies and absent narrative (DEC-9011), Account for all 27 types while selecting only applicable entity destinations (DEC-9021) |
| DEC-9033 | Revise current candidate qualification later without changing semantic recipes or historical authority | Refines Freeze exact snapshots; promote compatibility explicitly (DEC-9023) |
| DEC-9034 | Require executable conformance before admitting System facts | Refines Bind each output producer to exact branch, selectors, operation and evidence (DEC-9012) |

### DEC-9029 — Qualify the complete authoritative provider source snapshot before System applicability

**Rationale**

ADR-L-0012 DEC-0045 through DEC-0047 makes the owning provider authoritative for
its namespace and canonical registry; it does not make a caller's source list complete.
Extend that provider responsibility narrowly: a System-capable provider MUST expose
one immutable revision of its entire authoritative architecture source collection for
the qualified namespace, together with its canonical unit bindings at that revision.
Scope is that provider-owned architecture collection, including all subordinate source
collections using the same namespace. It is not an arbitrary directory, requested UUID
subset, selected ADR status, or the whole external world. Different namespaces remain
separate authorities. Existing independently governed provider/namespace binding must
authorize the collection boundary and the provider's snapshot publication channel;
neither can be selected or replaced by the System producer or its request.

Select a complete content-addressed source object graph as the completeness mechanism.
Its immutable root commits every collection node and child membership, every source
object's original bytes and exact source-schema qualification, and the canonical unit
bindings. The provider's authenticated publication binds namespace, scope identity,
revision and root. A hash or signed caller inventory alone is insufficient. The
verifier MUST obtain that root independently through the authorized provider binding,
retrieve and expand every committed child edge to terminal objects, verify every object
commitment, and reconstruct membership itself. Missing children, truncated enumeration,
hidden pages, cycles or unverifiable external edges cannot establish completeness.
A provider whose backend cannot expose a complete immutable collection is unsupported.
This defines an evidence obligation, not a new source registry, filesystem scan
convention, persistence system or public API. Wire encoding is subsequently selected
by closed AI candidate schemas using existing canonical JSON/digest primitives.

Every original source object must be accounted for under its qualified schema. Locate
every Authoring 1.7 Physical System root and its /system object; no status, filename,
alias, UUID, request-order or caller-supplied relevance filter may hide a claim.
Unknown source kinds or unsupported schema classification make completeness Unavailable;
known invalid or substituted source/schema evidence is Rejected. Relevant claims are
ALL such occurrences in that complete namespace collection, not only selected outputs.
The snapshot root is independently authoritative because the namespace owner has
designated the complete collection and publication channel outside this operation;
a descriptor producer cannot create that authorization. Provider honesty beyond that
authority boundary is not inferred from cryptography. Unregistered external material
is not silently included or asserted absent from the world.

ADR-L-0032 DEC-0254 through DEC-0257 and ACC 1.5 distinguish retained returned
candidate artifacts from the request's minimal non-overlapping interpretation roots.
That candidate source basis is not the provider's complete source collection. A
minimal-root digest proves retained integrity, not provider completeness. No synthetic
complete=true proof is allowed. Missing authorized publication, full provider membership
or exact revision is Unavailable.

The selected complete provider snapshot and reuse-only binding cost full relevant-source
enumeration and leave providers without that capability Unavailable. They preserve a
small independently testable trust boundary; they do not promise provider-independent
global uniqueness or require full normalized architecture assembly.

Every collection node must expose its complete child membership within its committed
content. Verify node commitments using the exact candidate-selected canonical JSON/digest
rules and original source commitments over the complete bytes. A revision label is not
a root commitment. Source identities occur exactly once in authoritative membership;
duplicate membership or conflicting objects under one source identity are Rejected.
Repeated transport retrieval of the same object is not another semantic occurrence.
Exact set equality applies between the independently expanded provider graph and its
authenticated committed provider inventory, not unconditionally between that inventory
and the request basis. Unrelated non-architecture files are outside the already
authorized collection boundary, never excluded through a new filename scan rule.


Complete claim accounting also includes every native typed System fragment and every
other entity/system definition occurrence selected by the exact source-schema/mapping
authority. Missing declaring context does not erase a claim or prove producer uniqueness.
A standalone fragment cannot become this boundary's authorized defining /system producer
without the independently established original declaring containment; no synthetic ADR
wrapper is allowed. For a relevant same-identity fragment, missing contextual evidence is
Unavailable and independently established canonical-value contradictions are Rejected.
Reference-only fields and relationship endpoints are not defining occurrences. Determine
that distinction from actual qualified source rules, not a field spelling or locator.
An unsupported source classification cannot silently hide a potentially relevant claim.


Distinguish these source roles. P is the complete authenticated provider snapshot at
one qualified revision; E is the selection of already-published provider source objects
relevant to a request; C is newly constructed detached candidate source, not yet in P.
Here published means provider snapshot membership, not contract release or promotion.
E may be a strict subset of P. B contains the minimal roots required by its governing
operation. For ACC these cover ALL returned candidate artifacts using exact containment
proofs, not a convenient subset of those artifacts and not a copy of all of P.
Retained child artifacts may be covered by parent roots without becoming extra roots.
Do not require P = B or add unselected provider roots to the interpretation, output
model or ledgers merely to prove scope completeness. Whole-inventory equality is
required only if the exact governing operation independently requires that scope;
this ADR introduces no such whole-provider interpretation operation.

For every selected existing member E, independently bind its logical request source_ref
to the actual P member's qualified source identity, exact schema/selector, provider
revision and original bytes, verifying commitments rather than trusting supplied hashes.
A logical source_ref need not be a provider storage path and is not membership proof.
Every relevant System claim in P, including unselected claims outside B, remains part
of unique-producer/context qualification. Selection does not make those claims absent.

Artifacts in C are sealed and schema-qualified under the existing candidate rules.
Their legitimate absence from the prior snapshot is not by itself a violation and
MUST NOT be represented as existing membership or provider publication. Identical bytes
or a copied existing child do not prove that a newly composed parent or changed declaring
context was in P. Source origin must qualify from membership or retained construction
evidence, not a caller-supplied existing/new flag. A purported existing source missing
at the requested revision cannot be relabelled C to bypass missing or stale evidence.
Existing exact-subtree/byte-preservation evidence remains necessary
and is not a substitute for provider membership or declaring-context qualification.

System claims in C would need a separately governed, independently qualified
candidate-to-provider comparison/qualification relation binding complete P, all relevant
candidate claims (including children represented by minimal roots), exact namespace,
revisions, source commitments and existing unit/producer authority. ACC's minimal basis
and detached context do not currently supply that relation. This ADR does not
authorize an overlay, publication, producer designation or membership-conversion
operation. Without that selected comparison authority and evidence, candidate System
reuse remains Unavailable; known identity/value/context violations remain Rejected
with their independent diagnostics. No caller declaration or finite candidate basis
can supply the missing relation. Defining that relation, if needed, is a remaining
authority prerequisite, not an implementation detail to invent in the later revision.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Treat the retained finite basis as complete | Integrity of supplied roots cannot expose omitted authoritative claims. |
| Discover a winner through a repository scan or matching fields | Discovery and equal values cannot establish authorized producer or contextual equivalence. |
| Create a new global System registry or coalescence service | Existing owning-provider authority can supply snapshot and prior unit evidence without another registry. |
| Create the first System from a lone descriptor | This would add initial establishment and producer-election semantics to an inherited reuse boundary. |

**Traceability**
- Refines: Treat federation as a read-only aggregation layer over per-repo canonical registries (DEC-0045)
- Refines: Use provider-authoritative conflict resolution for federated entity definitions (DEC-0046)

### DEC-9030 — Reuse only an existing provider-qualified System unit with one authorized defining occurrence

**Rationale**

This boundary is strictly reuse-only. Reading a descriptor MUST NOT establish a new
System unit or elect its initial producer. The owning provider's canonical unit binding,
established outside this execution and included in the independently authenticated
snapshot, must already bind (exact architecture_namespace, canonical lowercase UUIDv7)
to semantic_type entity/system and exactly one authorized defining source occurrence.
The provider's existing canonical-unit authority explicitly designates the defining
occurrence; discovery order never does. Initial establishment/admission and its
authorization remain outside this slice. Without a preexisting qualified binding the
result is Unavailable, even when only one descriptor is visible.

The binding must identify its establishment authority/evidence, immutable revision,
defining original source identity and digest, /system occurrence, source/child schema
identities, declaring Physical System ADR UUID, original canonical fields and qualified
semantic/contextual provenance. A source pointer locates the occurrence; namespace
plus UUID remains canonical identity. The independent verifier authenticates the owning
provider binding, verifies the typed unit record and its prior establishment evidence,
and reconstructs those facts from the exact defining original. A historical record is
not forward-qualified by changing its version/SCF. It must prove compatible meaning
under the actual selected authority; otherwise it is Unavailable.

Exactly one provider-authorized defining occurrence is required. Multiple independently
authorized defining occurrences for the same unit are Rejected, even if their values
match. A supplied preferred producer or an unqualified existing-unit receipt is not
authorization. Every other descriptor of the same canonical identity is a reuse claim
to be checked, not a candidate from which an implementation may choose a winner.
No first/last occurrence, filename, lexical order, alias, content-digest rank, request
order, matching UUID or identical values may designate a producer.

The exact selected source mapping and semantic-unit accounting still govern coincident
ADR/descriptor UUID roles. A provider type assertion cannot override an adr mapping or
fabricate another unit. Unsupported or ambiguous role coincidence remains Unavailable;
independently established contradictory canonical type/identity evidence is Rejected.
The first executable cases may use a qualified descriptor whose UUID is distinct from
its declaring ADR. This ADR does not redesign root/System role coalescence.

A generated registry, graph or normalized index is an evidentiary projection, not the
authority that establishes the unit. Its binding must trace to the exact canonical
defining original and independently verifiable prior establishment authorization under
the owning provider's existing governance. The verifier must authenticate that prior
authorization and replay the source/type/context qualification. An index entry, runtime
graph node or same UUID alone is insufficient. This ADR authorizes no new admission
procedure and cannot turn reading a generated record into initial unit establishment.

**Traceability**
- Refines: Authorize explicit scoped declaring-ADR lifecycle propagation (DEC-9003)
- Refines: Account for all 27 types while selecting only applicable entity destinations (DEC-9021)

### DEC-9031 — Account for every descriptor and preserve literal lifecycle and contextual meaning

**Rationale**

Preserve architecture-interpretation/1.3/lifecycle-ownership and the actual rule
declaring-lifecycle.adr-physical-system.system with its governing qualification and
reuse_existing_semantic_unit_if_same_canonical_identity meaning. Direct /system
containment, one declaring Physical System ADR, exact source/parent/child schemas,
ownership_schema_path and identity selectors must qualify from original sources.
Do not relabel inherited resources or assign lifecycle to a synthetic System owner.

Independently compare every same-identity descriptor in the complete scope against
the authorized defining occurrence and existing typed unit. Require equality of every
governed authored semantic value, typed value, presence/absence, multiplicity and
applicable collection semantics under the actual field dispositions. Independently
qualify original semantic destinations; matching generated labels are insufficient.
Compare literal declaring lifecycle and the complete applicable contextual-fact meaning:
declaring_adr_id, declaring_adr_semantic_type, status_semantic_field_key and qualified
ownership_rule.rule_id/meaning. Validate the full lifecycle carrier under its actual
AI 1.3 schema. Digests, source locations and rule receipts are qualification evidence,
not contextual equality or semantic identity. No implicit cross-version equivalence.

Compatible reuse retains the existing unit/producer and lifecycle exactly once; it
creates no second semantic owner, unit, lifecycle slot or label owner. Compatibility
is a necessary equality criterion, not evidence that a second descriptor can reach
a successful case under the actual schema and declaring-context rules.

Authoring 1.7 Physical System requires one direct /system object, not an array of
descriptors. The inherited ownership rule selects that occurrence and the declaring
ADR's /id. Two distinct Physical System ADR identities in the same provider namespace
necessarily have different declaring_adr_id values. They cannot satisfy the exact
contextual equality selected above for one shared System identity, even when authored
fields, labels and literal status are identical. Once both declaring contexts are
independently established, this is Rejected. When required owner evidence is absent,
it is Unavailable; unknown context must not be treated as either equality or an
established contradiction. This decision admits no cross-ADR descriptor coalescence.

Positive reuse is repeated qualified reference, lookup or independent reverification
of the same already-established source occurrence and typed unit at the qualified
snapshot revision, without introducing another semantic definition or producer. A
reference-only occurrence must qualify as a reference under its actual source contract;
it preserves the defining unit's established context and does not acquire a new
declaring lifecycle or duplicate that context on a newly invented System unit.
Repeated transport retrieval is not another source occurrence. Another request can
reference the same established binding only after its own applicable evidence qualifies.
These are normative positive cases, not claims of currently available provider support.

The single /system property supplies no positive example of two different descriptors
inside one unchanged ADR. Copies of an ADR carrying the same canonical ADR UUID are
not two distinct declaring ADRs; duplicate-source and semantic-unit identity constraints
remain in force. Repeated reads must not be misreported as additional compatible
definitions. A compatible_additional_descriptor outcome is conditional on all these
constraints; it is not an advertised reachable cross-ADR execution capability.

If v0.13 requires meaningful shared-System descriptor reuse across distinct declaring
ADRs, whether to require that capability and how its ownership/lifecycle/context and
definition-versus-reference semantics should work remain an unresolved human
architectural decision. Do not weaken contextual equality, choose a preferred ADR,
introduce multi-declarer lifecycle or coalesce contextual facts here. This is not a
runtime Unresolved outcome and does not authorize another ADR automatically.

Distinct canonical UUIDs remain distinct; equal aliases do not merge them. Equal UUIDs
under different independently qualified namespaces also remain distinct identities.
System summary remains literal alias_name duplication, without narrative meaning.

**Traceability**
- Refines: Carry qualified inherited-lifecycle facts in existing open NM metadata (DEC-9004)
- Refines: Compare inherited lifecycle meaning and independently verify its authority (DEC-9005)

### DEC-9032 — Separate provider authority, complete membership, unit binding and independent replay

**Rationale**

Evidence responsibilities are closed and separate. Existing governed namespace/provider
configuration supplies authority and scope/publication binding. The authorized provider
supplies immutable source-collection and canonical-unit snapshot objects. Original ADR
sources supply typed values and declaring containment. The existing selected candidate
definitions supply schema, field, context, representation and equality authority. An
independent qualifier retrieves the authoritative root, exhaustively reconstructs the
source graph and all claims, authenticates prior unit/producer establishment and replays
source/identity/context proofs. A System producer supplies outputs only; its success,
scope and preferred-producer receipts cannot establish any of these evidence facts.

Bind provider, namespace, scope authorization, exact snapshot revision/root, complete
provider membership and separately qualified selected/candidate source commitments, original bytes/digests/schema identities, existing typed
unit, defining occurrence, all reuse claims and exact NM/AI/ACC definitions/resources/
SCFs in a single qualification. Do not mix source or registry revisions. No latest or
ambient lookup during replay. Independent verification reconstructs membership, source
values, unique authorized producer, identity, literal lifecycle and contextual equality
from original evidence, without invoking output producers or trusting replay receipts.
Source/resource order cannot affect the result. A changed legitimate snapshot requires
requalification, not a mutation of old immutable evidence. Replay against changed
qualified inputs rejects stale results. Historical evidence remains reproducible.

The following closed decision summary is the accepted normative authority for this
boundary. Its tests audit the requirements, not signatures, provider completeness or
successful System execution:

Provider completeness and minimal request-basis integrity are separate qualifications.
The former accounts for all relevant P claims; the latter qualifies the exact bounded
roots consumed by the operation. Do not merge them into one equality or count check.
New candidate source commitments must remain distinguishable from existing P membership.

```yaml
boundary: reuse_only_no_unit_creation
scope:
  owner: independently_authorized_namespace_provider
  extent: entire_authoritative_architecture_source_collection_for_namespace
  snapshot: immutable_complete_content_addressed_object_graph
  root_authority: independently_authenticated_provider_publication_binding
  enumeration: independent_exhaustive_expansion_of_every_committed_child_edge
  claims: all_selected_system_definition_occurrences_including_native_fragments
  filters: none_by_status_path_alias_uuid_or_requested_selection
  partial_or_unavailable: Unavailable
unit:
  identity:
  - architecture_namespace
  - canonical_uuidv7
  semantic_type: entity/system
  establishment: preexisting_owning_provider_canonical_unit_binding
  designation: exactly_one_provider_authorized_defining_source_occurrence
  defining_pointer: /system
  creation_during_qualification: false
  election: false
reuse:
  rule: reuse_existing_semantic_unit_if_same_canonical_identity
  ownership_resource: architecture-interpretation/1.3/lifecycle-ownership
  ownership_rule: declaring-lifecycle.adr-physical-system.system
  comparison: all_governed_semantic_values_and_applicable_contextual_facts
  second_unit_or_owner: false
  context_qualification: actual_selected_resource_identity_digest_and_rule_meaning
  reachability:
    descriptor_shape: one_required_direct_system_object_per_physical_system_ADR
    distinct_declaring_ADRs_equal_context: false
    positive_case: repeat_reference_or_reverification_same_qualified_unit_no_new_definition
    duplicate_definitions_permitted: false
    cross_ADR_capability: human_decision_if_required_not_admitted_here
outcomes:
  unique_qualified_definition: eligible_for_bounded_execution
  compatible_additional_descriptor: reuse_existing_unit_only
  conflicting_canonical_values: Rejected
  conflicting_lifecycle_or_context: Rejected
  competing_authorized_definitions: Rejected
  missing_or_stale_scope: Unavailable
  unqualified_existing_unit: Unavailable
  distinct_canonical_uuids: distinct_units
  partial_or_unsupported_provider: Unavailable
  forged_or_substituted_evidence: Rejected
  stale_result_against_changed_qualified_snapshot: Rejected
evidence_bindings:
- provider_namespace_and_scope_authorization
- authenticated_snapshot_root_and_revision
- complete_source_object_membership
- original_bytes_digests_and_source_schema_identities
- preexisting_typed_unit_and_authorized_defining_occurrence
- all_descriptor_claims_and_literal_declaring_context
- exact_nm_ai_acc_definitions_resources_and_scfs
exclusions:
- initial_unit_creation
- producer_election
- current_scs_change
- complete_interpretation
- normalized_materialization
- whole_ledger_equivalence
- Constructed
- authority_promotion
source_sets:
  provider_inventory: complete_authenticated_P_independent_of_request_selection
  selected_existing: E_is_a_qualified_subset_of_P_not_required_equal_P
  request_basis: B_is_operation_selected_minimal_nonoverlapping_roots_not_all_P
  existing_member_checks:
  - source_identity
  - schema_and_selector
  - snapshot_revision
  - exact_original_bytes
  unselected_system_claims: account_in_complete_P_even_when_outside_B
  new_candidates: C_is_sealed_detached_source_not_prior_provider_membership
  new_candidate_comparison: Unavailable_without_selected_candidate_to_provider_authority_and_evidence
  implicit_publication_or_overlay: false
execution_prerequisites:
- accepted_decision_and_independently_qualified_candidate_authority
- implemented_authenticated_complete_provider_snapshot_capability
- independently_qualified_prior_System_unit_and_defining_producer
- implemented_private_scope_unit_and_output_verifiers
- selected_candidate_to_provider_comparison_when_new_candidate_claims_are_involved
```

**Traceability**
- Refines: Distinguish authored summaries, literal representation copies and absent narrative (DEC-9011)
- Refines: Account for all 27 types while selecting only applicable entity destinations (DEC-9021)

### DEC-9033 — Revise current candidate qualification later without changing semantic recipes or historical authority

**Rationale**

ADR-L-0037 through ADR-L-0040 remain accepted and unaffected. This ADR refines only
the shared_identity instance prerequisites of DEC-9011/DEC-9021 and the existing-unit
evidence requirement; it replaces no accepted MUST clause, field rule or equality rule.
The additional proof must satisfy, not override, all existing independent qualifications.

Dependency analysis at develop 37a91de52602af54bc184ec7278b470d6277360a selects AI 1.5
rules, required-output-derivations and identity-representation-recipes; the last resource
currently selects only architecture-interpretation/1.3/detached-context. That fixed
detached context commits supplied roots and cannot attest to this provider snapshot.
It stays unchanged and unsupported for System completeness on its own. After acceptance,
add the smallest AI 1.5-owned closed System scope/unit evidence resource and companion
schema, plus an exactly qualified provider-context branch for these System operations.
That branch must bind the actual owning-provider namespace to the snapshot. It must not
masquerade as, rewrite or silently substitute the historical detached provider.

Update AI 1.5 rules, System applicability/context references in the catalog, the recipe
context qualification and their closed companion schemas only as required by the new
evidence branch; qualify name/summary and the three existing identity operations using
those exact inputs. The recipe operations and original semantic destinations do not
change. Preserve all non-System catalog rows and all 215 static BLOCKED statuses,
including shared_identity entries: this supplies instance prerequisites, not a default
producer or blanket blocker removal. Full source-envelope, fingerprint and completeness
output recipes are not supplied by a source-scope witness.

ACC 1.5 rules/qualification evidence and closed contract schema must require the same
snapshot/unit proof wherever shared-System semantics are claimed; compatibility/exact
interpretation selection, conformance and generated manifests/definitions must select
the revised AI closure. Inspect current ACC schema references, not only version labels.
No new composition binding or ledger algorithm. Retain the normative ACC 1.3 ledger
schema and independent expected/observed whole-ledger obligations. Exact inherited
AI 1.3 rule keys, digests and qualification identities stay intact.

AI 1.5 and ACC 1.5 candidate SCFs will change from qualified authoritative bytes without
increasing versions under ADR-L-0040. NM 2.5, Authoring 1.7, ADC/CEC and released or
historical authority bytes remain unchanged. Generate mirrors/closures deterministically
and requalify co-dependent consumers. This decision PR changes none of those resources,
current SCS, public capabilities or execution. This ADR's acceptance and merge are
prerequisites to the bounded candidate revision; neither constitutes candidate
promotion.

The follow-up evidence/context revision must preserve the P/E/C/B distinction above.
It does not, by itself, supply an unpublished-candidate comparison rule or make any
provider operational. Keep the unqualified C-to-P System handoff Unavailable. Neither
that revision nor this ADR admits cross-ADR declaring-context coalescence.

**Traceability**
- Refines: Freeze exact snapshots; promote compatibility explicitly (DEC-9023)

### DEC-9034 — Require executable conformance before admitting System facts

**Rationale**

Following this ADR's acceptance, first revise and independently qualify the AI/ACC
candidate evidence/context authority and conformance. Then implement a bounded private
Rust verifier and reuse the existing candidate_authority, original-source, ownership,
identity-representation, semantic-field and label inverses. Never construct another
System to satisfy reuse. No new interpretation engine or public route is authorized.

Future executable tests must obtain complete authenticated snapshot evidence and prior
typed-unit/producer evidence independently of the System producer. Exercise a unique
defining occurrence, actually compatible reuse, all literal statuses, same UUID with
conflicting values/context, two authorized defining producers, distinct UUIDs/equal
aliases, distinct namespaces, partial/truncated enumeration, omitted/transitively hidden
sources, wrong scope/provider/revision, missing objects, changed bytes, unsupported
schemas, forged establishment and replay, invalid identity, altered rule qualifiers,
unauthorized consistently rehashed candidates and stale outputs after legitimate source
changes. A synthetic accepted fixture or self-declared signature is not live evidence.

Preserve Rejected > Unavailable > Unresolved. Known structural, semantic, identity,
authority or integrity violations are Rejected. Authentic but missing/stale/incomplete
required evidence or unsupported capability is Unavailable. Unresolved requires an
actual separately governed dependency and is never a label for an implementation gap.
Retain independent diagnostics and clear partial qualified outputs on failure.
Repeated compatible claims must pass every existing contextual and duplicate-identity
obligation; do not fabricate a positive fixture when that evidence cannot be established.

System failure cannot poison independently qualified Data Flow/Boundary siblings unless
the requested atomic scope depends on System. Physical System root execution is a
separate applicability question, not automatically complete after System qualification.
All 27 types/six branches, 240 producer definitions, 215 BLOCKED entries, 26 labels,
54 identity representations, three identity operations, five evidence checks and one
composition binding remain regression guards rather than proof. No complete NM entity
or model, complete interpretation, semantic_equivalent, Constructed, persistence,
admission, package publication or authority promotion follows from this bounded proof.

Execution-path assessment at reviewed head 3534500be75b7d001b1fc6b7a6ad06f1a15b5273:
ProviderRegistry routes namespaces to loaded repositories and resolves legacy normalized
entities; _normalized_bundle supports model versions through 2.3. It does not supply
authenticated complete source snapshots, immutable enumeration or the forward-qualified
prior System producer binding required here. The selected AI 1.3 detached context
commits only the retained basis. Rust SealedSources retains originals, authorities,
basis and context; system_claims checks retained claims and returns Unavailable for
missing complete scope/unique binding, while preserving known violations as Rejected.
No existing provider path inspected supplies the complete handoff. This is a baseline
observation, not a permanent prohibition on later qualified provider implementations.

Keep four milestones separate: a normative evidence shape, an actual supported provider
capability, prior independently authorized System unit/producer establishment outside
this reuse-only boundary, and implemented private Rust qualification/execution/replay.
AI/ACC candidate revision alone cannot make System executable. Real provider snapshot
acquisition/authentication, complete enumeration, prior establishment evidence and the
private verifier are external/engineering prerequisites. New candidate System claims
additionally need the separately governed comparison relation described above.

Conformance tests must cover a strict E subset of P, unselected relevant System claims,
exact membership/schema/revision/bytes, C absent from prior P without false publication,
missing authorized candidate comparison, distinct declaring ADR contextual conflict and
repeated reference to the same qualified unit with no new definition. These are design
audits, not evidence of a live provider or operational System execution. Known context
contradictions remain Rejected; missing authorized evidence remains Unavailable.

**Traceability**
- Refines: Bind each output producer to exact branch, selectors, operation and evidence (DEC-9012)





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0321 | System applicability MUST require independently reconstructed complete membership of the externally authorized… | MUST / design | automated |
| INV-0322 | System reuse MUST bind an already-established namespace-qualified entity/system UUID to exactly one independently… | MUST / design | automated |
| INV-0323 | Every relevant same-identity descriptor MUST preserve all governed semantic values and literal declaring-context… | MUST / design | automated |
| INV-0324 | Independent verification MUST bind exact scope, snapshot, sources, existing unit, defining producer, every reuse… | MUST / design | automated |
| INV-0325 | System applicability refinement MUST preserve historical rule identities, existing operations, all static BLOCKED… | MUST / design | automated |
| INV-0326 | Qualification MUST retain Rejected over Unavailable over governed Unresolved, clear partial outputs on failure and… | MUST / design | automated |

### INV-0321

**Statement**

System applicability MUST require independently reconstructed complete membership of the externally authorized immutable provider source collection; retained input integrity alone MUST NOT prove completeness.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Qualify the complete authoritative provider source snapshot before System applicability

**Upheld by decisions**
- Qualify the complete authoritative provider source snapshot before System applicability (DEC-9029)

### INV-0322

**Statement**

System reuse MUST bind an already-established namespace-qualified entity/system UUID to exactly one independently authenticated provider-authorized defining occurrence; qualification MUST NOT create a unit or elect a producer.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Reuse only an existing provider-qualified System unit with one authorized defining occurrence

**Upheld by decisions**
- Reuse only an existing provider-qualified System unit with one authorized defining occurrence (DEC-9030)

### INV-0323

**Statement**

Every relevant same-identity descriptor MUST preserve all governed semantic values and literal declaring-context meaning; compatible reuse MUST NOT duplicate a unit, lifecycle or semantic owner.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Account for every descriptor and preserve literal lifecycle and contextual meaning

**Upheld by decisions**
- Account for every descriptor and preserve literal lifecycle and contextual meaning (DEC-9031)

### INV-0324

**Statement**

Independent verification MUST bind exact scope, snapshot, sources, existing unit, defining producer, every reuse claim and selected candidate authority; producer receipts MUST NOT establish those facts.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Separate provider authority, complete membership, unit binding and independent replay

**Upheld by decisions**
- Separate provider authority, complete membership, unit binding and independent replay (DEC-9032)

### INV-0325

**Statement**

System applicability refinement MUST preserve historical rule identities, existing operations, all static BLOCKED statuses, independent ledger obligations and candidate-only lifecycle without public capability activation.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Revise current candidate qualification later without changing semantic recipes or historical authority

**Upheld by decisions**
- Revise current candidate qualification later without changing semantic recipes or historical authority (DEC-9033)

### INV-0326

**Statement**

Qualification MUST retain Rejected over Unavailable over governed Unresolved, clear partial outputs on failure and preserve independent sibling execution; accepted governance alone MUST NOT activate System execution.

**Scope:** architecture

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Require executable conformance before admitting System facts

**Upheld by decisions**
- Require executable conformance before admitting System facts (DEC-9034)






## Governance / Bindings / Evidence

### Governance

**Approved by:** egallmann
**Approved date:** 2026-11-11 01:52:28+00:00


## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)
- [ADR-L-0040](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)

**References**
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)
- [ADR-L-0040](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-L-0012 — Federation Authority and Qualified Identity Model](ADR-L-0012-federation-authority-and-qualified-identity-model.md) | refines | `DEC-9029 -[:refines]-> DEC-0046` |
| [ADR-L-0037 — Lossless Authored Lifecycle and Declaring-ADR Provenance](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md) | refines | `DEC-9030 -[:refines]-> DEC-9003` |
| [ADR-L-0038 — Explicit Required-Output Authority Across the AI Catalog](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md) | refines | `DEC-9032 -[:refines]-> DEC-9011` |
| [ADR-L-0039 — Forward Identity Representation Recipes](ADR-L-0039-forward-identity-representation-recipes.md) | refines | `DEC-9030 -[:refines]-> DEC-9021` |
| [ADR-L-0040 — Enforceable Semantic Contract Candidate and Promotion Lifecycle](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md) | refines | `DEC-9033 -[:refines]-> DEC-9023` |




## Notes

Accepted following explicit human architectural approval of ADR-L-0041 at reviewed
PR #195 head 3d9bab9728bb572c3029d61dc6267a1ba6793fce, covering DEC-9029–9034 and
INV-0321–0326. Approval source: the authenticated Codex conversation for this
repository task; thread 01a10569-766b-7991-b9c5-3952eff35bcb; message
01a1c84e-797b-7651-81da-385a1a7aea67; timestamp 2026-11-11T01:52:28Z. The linked
GitHub identity verified for the required approver is egallmann, matching PROJECT.yaml.
The approving human stated: "I am that person, I am approving." In this task context,
that is explicit authorization for acceptance and merge of this exact reviewed PR
revision after qualification gates pass. This records architectural authorization;
it does not claim a GitHub APPROVED review or independent branch-protection review.

All six decisions, six invariants, canonical UUIDs, aliases, source-role distinctions,
reuse-only establishment, strict declaring-context equality, outcome precedence and
execution/publication exclusions are unchanged. Acceptance activates this normative
boundary only; it does not qualify a live provider, execute System interpretation,
revise AI/ACC candidates or promote any candidate authority.


---

*Generated from ADR-L-0041 by ADR Architecture Kit (projection v3)*