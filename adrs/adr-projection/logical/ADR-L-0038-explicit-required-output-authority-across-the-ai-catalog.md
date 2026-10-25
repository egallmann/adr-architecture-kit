<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 66fc93c102a2ad26832852614aec1cd02ad034dae30ae23ce8fe056d6b76df0a
rendered_hash: 6ff954a51f915463013cb94505b6761da6fd34e1de245dba5d6e7ecf7002ed82
-->

# ADR-L-0038: Explicit Required-Output Authority Across the AI Catalog

## Identity / Status

**Type:** logical<br>
**Status:** accepted<br>
**Alias:** ADR-L-0038<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-10-23<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, semantic-authority, authoring, conformance<br>
**Tags:** required-output-coverage, architecture-interpretation, normalized-model-2.5, v0.13<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0038 |
| Status | accepted |
| Decisions | 8 |
| Invariants | 8 |


## Context

At develop e262b86745c7c9e23536c81e768da1fec2c710b9, exact ACC 1.3,
AI 1.3 and NM 2.5 closures validate. NM 2.5 requires name and summary for
regular entities. Among the 17 regular semantic types, 9 have no direct name
placement, 15 no direct summary placement, and 7 lack both. The lifecycle-free
normative-proposition branch also requires both labels without direct placements.
Historical fallback chains and schema-valid arbitrary strings do not establish
forward semantic authority. This is a systemic required-output authority gap,
not a reason to narrow v0.13 to the currently executed Logical ADR/Decision pair.

The 27 catalog types include 17 regular types, one normative proposition,
one canonical relationship, six compatibility relationships and two value types.
They are not 27 independent roots. DEC-0271 authorizes only uniquely governed
ceremony and exact semantic preservation; ADR-L-0037 establishes literal
lifecycle and explicit ownership but does not choose all output recipes.
This accepted successor decision closes label policy and coverage governance,
while recording missing semantic and representation prerequisites explicitly.
It does not publish or execute successor authority.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-9009 | Require exactly one qualified producer for every applicable normalized output | Refines Require exact Architecture Interpretation dispositions for all supported Authoring 1.7 fields (DEC-0269), Define the only authorized differences in construction semantic comparison (DEC-0271) |
| DEC-9010 | Use exact authored names or explicit type-scoped alias labels | — |
| DEC-9011 | Distinguish authored summaries, literal representation copies and absent narrative | — |
| DEC-9012 | Bind each output producer to exact branch, selectors, operation and evidence | Refines Produce complete Normalized Model results using a deterministic detached context (DEC-0270), Distinguish semantic provenance from candidate integrity and representation ceremony (DEC-0272) |
| DEC-9013 | Keep independent representation verification separate from semantic equality | Refines Define the only authorized differences in construction semantic comparison (DEC-0271), Distinguish semantic provenance from candidate integrity and representation ceremony (DEC-0272), Compare inherited lifecycle meaning and independently verify its authority (DEC-9005) |
| DEC-9014 | Account for every required destination across entity, relationship and value branches | Refines Separate native standalone representation from qualified complete interpretation (DEC-9002), Authorize explicit scoped declaring-ADR lifecycle propagation (DEC-9003), Carry qualified inherited-lifecycle facts in existing open NM metadata (DEC-9004) |
| DEC-9015 | Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance | Refines Replace only version-selection clauses for successor construction (DEC-9006), Require human acceptance before publication and separately authorized execution (DEC-9008) |
| DEC-9016 | Require publication conformance, explicit blockers and separate human acceptance | Refines Compare complete expected and observed semantic ledgers for construction round trips (DEC-0268), Require human acceptance before publication and separately authorized execution (DEC-9008) |

### DEC-9009 — Require exactly one qualified producer for every applicable normalized output

**Rationale**

The v0.13 objective remains complete end-to-end semantic execution for all 27
published semantic types, not permanent support for only Logical ADR/Decision.
Keep the five closed authored-field dispositions unchanged. A separate closed
AI-owned required-output-derivations catalog and companion schema shall account
for every schema-required normalized destination. This is output authority, not
a sixth authored-field disposition or a manufactured authored child field.

Exactly one applicable qualified producer may establish a destination: an
existing qualified field placement, an independently qualified contextual rule,
or an explicit output derivation. BLOCKED denotes a missing prerequisite and
is not a producer, not output coverage and not an authorized default. Two
competing producers also block complete materialization. Resolve applicability
after governed canonical-identity accounting; coalesced units must not activate
competing producers. A catalog type is not necessarily an independent root.

Reuse unchanged immutable field dispositions, ownership semantics and pure
operations by exact resource qualification. Do not publish unchanged semantics
as new independent rules. Existing Rust/Python fallback chains are historical
implementation evidence only, not forward authority.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Reuse historical fallback chains | Historical implementation is not forward meaning authority and implicit alternatives prevent unique producer qualification. |
| Make NM required fields optional in a new NM version | No schema contradiction prevents explicit literal representations; dropping fields does not resolve derivation authority. |
| Narrow the execution objective to Logical ADR and Decision | The same output gap affects the wider catalog and v0.13 retains all 27 semantic types. |

**Traceability**
- Refines: Require exact Architecture Interpretation dispositions for all supported Authoring 1.7 fields (DEC-0269)
- Refines: Define the only authorized differences in construction semantic comparison (DEC-0271)

### DEC-9010 — Use exact authored names or explicit type-scoped alias labels

**Rationale**

Keep the existing adr/logical, adr/physical-system and adr/physical-component
title-to-name placement and the existing name placements for boundary,
capability, component, data_flow and system_boundary. For each remaining
entity type, explicitly select required alias_name as a representation-only
human-recognition label. Each type has its own applicability row and rationale,
all referencing one literal-string-copy operation. Aliases do not become UUIDs.

Decision and Implementation Decision summaries can be long substantive prose;
their required alias_name supplies a bounded label without truncating summary.
Contract guarantees and Interface specifications describe obligations or a
technical surface, not a short heading; use their own required alias_name.
Invariant and Normative Proposition statements carry assertions, not invented
titles; use alias_name and preserve each statement at its semantic destination.
Extension rationale does not define a custom display name; its own alias_name
labels the instance without consulting or inventing registry definitions.
Gap question and Evidence Expectation description carry substantive content;
their alias_name labels the question/expectation without rewriting that content.
System has only identity/alias fields and no authored substantive name; its
alias_name is the explicit label, not a borrowed declaring-ADR title.

Copy the complete string exactly: no hyphen replacement, title casing,
whitespace trimming, truncation, prose generation or fallback to another field.
Missing or invalid selected inputs block qualification. A source-valid value
must also satisfy the exact selected output schema. This decision does not
retroactively authorize any of these generated names under AI 1.3.
Consequences: these labels retain the authored lower-kebab spelling and change
when that semantic alias changes; they are not prose titles or new canonical
identities. Consumers may display labels, but presentation convenience does
not authorize changing normalized strings. Long substantive content remains
complete at its own destination and is never shortened to fit a name.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Use substantive prose as every generated name | Statements, summaries and technical specifications can be unsuitable human-facing labels; do not truncate them to manufacture headings. |
| Transform alias_name into a formatted title | Formatting introduces an additional representation policy; the selected label is an exact bounded copy. |

### DEC-9011 — Distinguish authored summaries, literal representation copies and absent narrative

**Rationale**

Preserve the existing Decision and Implementation Decision summary placements.
For other types select exactly the required authored string in the matrix.
These representation-only copies do not add independent substantive meaning.
Preserve the original field under its existing semantic disposition, including
typed semantic extensions; the copied output does not replace that obligation.
Optional rationale or description fields never become fallback alternatives.

For entity/system, Authoring 1.7 defines only id, alias_id and alias_name and
forbids additional properties. Select summary = alias_name as explicit label
duplication only. No substantive system description is authored, reconstructed
or inferred. This satisfies a representation requirement, not an obligation to
invent behavior, responsibilities, implementation or deployment meaning. Do not
borrow parent context/title. The existing shared-system identity rule may reuse
an existing unit; it never creates another unit or overrides that unit's
qualified producer. A conflicting coalesced representation remains BLOCKED
unless the exact selected authority uniquely determines its producer.

A string-valued required source may legitimately be long or empty where its
source schema allows it. Copy it literally, without coercion, invented empty
defaults, summaries of prose or formatting transformations.

Complete 27-type label/output-branch matrix follows. A means existing authored
placement; R means selected successor representation-only copy; not-applicable means the
selected nonentity branch has no regular name/summary requirement, not that
the type is excluded from execution. Source selectors are relative to the
exact Authoring 1.7 schema namespace, never runtime instance positions.

```yaml
- semantic_type: adr/logical
  category: regular
  source_schema: adr-logical.schema.json#
  name: A:title
  summary: R:context
- semantic_type: adr/physical-component
  category: regular
  source_schema: adr-physical-component.schema.json#
  name: A:title
  summary: R:context
- semantic_type: adr/physical-system
  category: regular
  source_schema: adr-physical-system.schema.json#
  name: A:title
  summary: R:context
- semantic_type: entity/boundary
  category: regular
  source_schema: adr-common.schema.json#/definitions/boundary
  name: A:name
  summary: R:description
- semantic_type: entity/capability
  category: regular
  source_schema: adr-common.schema.json#/definitions/capability
  name: A:name
  summary: R:description
- semantic_type: entity/component
  category: regular
  source_schema: adr-common.schema.json#/definitions/component
  name: A:name
  summary: R:responsibilities
- semantic_type: entity/contract
  category: regular
  source_schema: adr-common.schema.json#/definitions/contract
  name: R:alias_name
  summary: R:guarantees
- semantic_type: entity/data_flow
  category: regular
  source_schema: adr-common.schema.json#/definitions/data_flow
  name: A:name
  summary: R:description
- semantic_type: entity/decision
  category: regular
  source_schema: adr-common.schema.json#/definitions/decision
  name: R:alias_name
  summary: A:summary
- semantic_type: entity/evidence_expectation
  category: regular
  source_schema: adr-common.schema.json#/definitions/evidence_expectation
  name: R:alias_name
  summary: R:description
- semantic_type: entity/extension
  category: regular
  source_schema: adr-common.schema.json#/definitions/custom_entity
  name: R:alias_name
  summary: R:rationale
- semantic_type: entity/gap
  category: regular
  source_schema: adr-common.schema.json#/definitions/gap
  name: R:alias_name
  summary: R:question
- semantic_type: entity/implementation_decision
  category: regular
  source_schema: adr-common.schema.json#/definitions/implementation_decision
  name: R:alias_name
  summary: A:summary
- semantic_type: entity/interface
  category: regular
  source_schema: adr-common.schema.json#/definitions/interface
  name: R:alias_name
  summary: R:specification
- semantic_type: entity/invariant
  category: regular
  source_schema: adr-common.schema.json#/definitions/invariant
  name: R:alias_name
  summary: R:statement
- semantic_type: entity/normative_proposition
  category: normative-proposition
  source_schema: adr-common.schema.json#/definitions/normative_proposition
  name: R:alias_name
  summary: R:statement
- semantic_type: entity/system
  category: regular
  source_schema: adr-common.schema.json#/definitions/system
  name: R:alias_name
  summary: R:alias_name
- semantic_type: entity/system_boundary
  category: regular
  source_schema: adr-common.schema.json#/definitions/system_boundary
  name: A:name
  summary: R:description
- semantic_type: relationship/calls
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/depends_on
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/extension
  category: canonical-relationship
  source_schema: adr-common.schema.json#/definitions/custom_relationship
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/publishes_to
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/reads_from
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/subscribes_to
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: relationship/writes_to
  category: compatibility-relationship
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/relationships/items
  name: not-applicable
  summary: not-applicable
- semantic_type: value/normative_force
  category: proposition-value
  source_schema: types.schema.json#/definitions/normative_force
  name: not-applicable
  summary: not-applicable
- semantic_type: value/topology_component
  category: owner-local-value
  source_schema: adr-physical-system.schema.json#/properties/component_topology/properties/components/items
  name: not-applicable
  summary: not-applicable
```

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Invent a substantive system description from its parent | The System schema authors only identity and aliases; parent narrative is not child-owned meaning. |
| Block system summary until Authoring adds a description | The selected representation-only label duplicate requires no invented substantive assertion and is permitted by NM 2.5. |

### DEC-9012 — Bind each output producer to exact branch, selectors, operation and evidence

**Rationale**

For every semantic unit independently qualify the exact output schema branch,
all local/relative references, allOf/oneOf/if/then requirements and applicable
custom-type conditions. Enumerating only the root required array is inadequate.
Every applicable destination must bind exact source selectors and destination
paths, source/destination resource identities and digests, derivation-rule
identity, input types and presence, exact operation, semantic/representation
classification, independent output comparison, equality obligations and all
contextual provenance dependencies. Missing references or unsupported schema
conditions block qualification; they are not silently ignored.

The successor catalog is closed, type-scoped and schema-valid. Each new label
row selects literal_string_copy(input); direct placements and contextual facts
reference their existing authority, not duplicate definitions. Its schema must
reject unknown operations, undeclared destinations and incomplete rows.
Publication must prove no two rules can establish the same applicable output.
Do not embed the enclosing successor SCF into its own resource closure;
instance evidence binds the independently verified family/version/SCF and exact
rule key, digest and ID only after publication.

Independent verification reconstructs the representation from the original
sealed sources, established identities and exact selected rule. It may not
trust caller flags, asserted provenance, replay copies, counts or recalculated
digests. Validate the actual complete entity/record against its exact output
schema in addition to coverage and semantic checks. Fail atomically; do not
release an apparently complete representation when any destination is BLOCKED.
The proposed resource identities are architecture-interpretation/1.4/required-output-derivations
and architecture-interpretation/1.4/required-output-derivations.schema. Their
publication is a later slice after human acceptance, not an artifact of this PR.

**Traceability**
- Refines: Produce complete Normalized Model results using a deterministic detached context (DEC-0270)
- Refines: Distinguish semantic provenance from candidate integrity and representation ceremony (DEC-0272)

### DEC-9013 — Keep independent representation verification separate from semantic equality

**Rationale**

Retain DEC-0271 exact canonical-field value preservation. An R row is an
output representation derivation, not another canonical-field placement and
not a reclassification of its authored input as ceremony. The authored input
remains semantically significant exactly once under its existing disposition.
In particular, keep context, description, statement, rationale, guarantees,
specification and responsibilities at their selected semantic destinations.
The generated label/summary adds no independent semantic value or owner.

Clarify the successor use of AI 1.3 rules.semantic_extensions.duplication:
an explicitly verified representation copy is not a second first-class owned
semantic value. No semantic extension may be removed merely because its input
also appears in a generated label. Whole-ledger comparison must distinguish
direct A destinations from R destinations by exact selected authority, never
by guessing from equal strings or normalized property names.

Representation verification must reject a changed derived value even when the
source extension is intact. Semantic equality must independently detect a
changed/missing authored value even when a generated label is intact. Neither
successful schema validation nor an entity fingerprint proves either claim.
Record source/rule/identity evidence independently. Source pointers, paths,
request order, traversal positions and digests are not semantic owner identity.
Inherited lifecycle and its qualified contextual provenance remain semantic;
no lifecycle is duplicated into a carrier or treated as generated ceremony.

**Traceability**
- Refines: Define the only authorized differences in construction semantic comparison (DEC-0271)
- Refines: Distinguish semantic provenance from candidate integrity and representation ceremony (DEC-0272)
- Refines: Compare inherited lifecycle meaning and independently verify its authority (DEC-9005)

### DEC-9014 — Account for every required destination across entity, relationship and value branches

**Rationale**

The complete required-output audit uses these authority/evidence obligations.
Status refers to authority for a producer, never to runtime implementation.

| Required destination | Producer or explicit prerequisite | Classification and proof |
| --- | --- | --- |
| id, alias_id, alias_name | Established canonical identity and exact authored placements | Semantic; exact source/identity commitment; aliases never canonical UUIDs |
| entity_type | Exact selected type mapping; custom type requires CEC qualification | Semantic; custom registry/qualification must be independently selected |
| name, summary | Exact A/R matrix and successor label rules | A semantic; R representation; verify source and copy separately |
| lifecycle_stage | Exact literal root status or qualified AI declaring-ownership rule | Semantic/contextual; custom and unqualified standalone lifecycle remain BLOCKED |
| alias_ref | Explicit qualified alias-composition operation | Representation; exact inputs/format must be published; no historical fallback |
| created_at | Explicit UUIDv7 timestamp representation | Representation; exact conversion/encoding must be qualified; not authored created_date or wall clock |
| uri | Explicit qualified detached namespace and established UUID operation | Representation; exact format/profile; no repository destination |
| entity_fingerprint | Explicit qualified canonical preimage/digest profile | Representation integrity; not whole-ledger equality; never recursive |
| canonical_source, provenance | Verified source/context/authority envelope operation | Integrity evidence; preserve source refs, selectors, exact bytes/digests and contract qualification |
| completeness | Verified entity-specific schema/field/output/context coverage | Representation evidence; never complete-model interpretation or construction |
| metadata.semantic_extensions | Existing exact field dispositions, when present | Semantic typed JSON; no source replay substitution or loss |
| metadata.ai_lifecycle_provenance | Existing independently qualified AI lifecycle/context authority, when applicable | Semantic contextual facts plus independent integrity qualification |
| extension and its conditional members | Exact selected CEC source qualification/properties/rationale | Semantic; registry closure is not registry selection; absent custom lifecycle authority stays BLOCKED |

The 17 regular entity types have 14 unconditional required envelope fields.
Audit all conditional schema requirements as well. The lifecycle-free normative
proposition branch instead requires statement, normative_force, scope,
declaring_adr, source_artifact and source_contract in addition to its common
envelope; it must not acquire lifecycle_stage or independent approval.
Its A identity aliases, semantic assertion fields and qualified declaration
evidence remain significant independently of its R labels.

Canonical relationship/extension requires record_kind, canonical id/aliases,
relationship_type, resolved endpoint UUIDs and canonical_source_ref; its custom
qualification, properties and rationale are conditionally required. Bind the
actual relationship branch/destinations explicitly; entity-named catalog
references alone do not prove correct record placement. No synthetic entity
envelope is added. Compatibility branches for calls, depends_on, publishes_to,
reads_from, subscribes_to and writes_to require record_kind, relationship_id,
assertion_id, type, resolved endpoints, provenance_classification and
canonical_source_ref. Exact generated-identifier recipes, source context and
multiplicity evidence must be qualified; generated IDs never replace governed
semantic tuple equality or identify semantic occurrences by source position.

value/normative_force remains a proposition-owned enum value.
value/topology_component remains typed owner-local semantic extension content
under owner UUID plus topology_key, retaining component_ref and fields.
Neither value receives a regular entity envelope or an independently minted ID.

BLOCKED prerequisites are explicit: custom-entity lifecycle beyond published
ownership exclusions; missing/ambiguous declaring context for native fragments;
conflicting shared-identity producer selection; any unqualified envelope
operation/preimage; and incomplete relationship/nonentity output recipes or
endpoint evidence. This ADR does not invent the semantic rules needed to close
them. Give each an explicit successor publication or separate accepted-decision
obligation. They are prerequisites to the v0.13 all-27-type objective, not
permanent exclusions, output producers or grounds to claim completeness.

**Traceability**
- Refines: Separate native standalone representation from qualified complete interpretation (DEC-9002)
- Refines: Authorize explicit scoped declaring-ADR lifecycle propagation (DEC-9003)
- Refines: Carry qualified inherited-lifecycle facts in existing open NM metadata (DEC-9004)

### DEC-9015 — Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance

**Rationale**

Selected sequence: human acceptance of this reviewed ADR;
independent immutable AI 1.4 publication/qualification; independent ACC 1.4
publication selecting exact AI 1.4 and unchanged NM 2.5; then separately scoped
Rust execution. Retain Authoring 1.7, ADC/CEC and unchanged semantic resources
by exact qualifications where sufficient. Publish only new/changed authority;
reuse genuinely unchanged resource identities rather than new independent
copies of field, ownership, detached-context or representation semantics.

AI 1.4's new closed catalog/schema and frozen conformance must establish every
selected operation and required-output coverage proof. If an operation remains
unqualified its destination remains BLOCKED. This proposal does not arbitrarily
select a historical fingerprint preimage, URI template or timestamp format as
forward authority. Publication must qualify the exact recipe under accepted
authority, or obtain a narrow accepted refinement before claiming coverage.

ACC 1.4 is required because ACC 1.3 selects AI 1.3 exactly and cannot silently
inherit the successor output/equality rules. Its profile/closure must qualify
AI 1.4/NM 2.5 and distinguish schema completeness, representation verification,
semantic equality and final construction qualification. Cross-version evidence
cannot be promoted by rewriting fields or by implicit predecessor execution.
NM 2.5 has no demonstrated schema contradiction for these literal labels, so
no new NM version is justified. Preserve all historical authorities, SCFs,
frozen conformance acceptance, current SCS/catalog/policy, public APIs,
protocol 1.5 and capability flags. No migration/conversion is authorized.

For successor construction only, refine the AI 1.3 / ACC 1.3 selection clauses
of DEC-9006 and INV-0298 to AI 1.4 / ACC 1.4 after publication; retain NM 2.5
and all unrelated lifecycle, ownership, minimal-root, compiler-containment,
identity and semantic equality obligations. Do not retire DEC-0271.
Consequences: successor publication and later Rust execution add qualification
work and cannot unlock existing ACC 1.3 requests. Explicitly blocked semantic
prerequisites remain work for separate accepted decisions; this ADR does not
assert that the complete v0.13 execution objective has already been met.

**Traceability**
- Refines: Replace only version-selection clauses for successor construction (DEC-9006)
- Refines: Require human acceptance before publication and separately authorized execution (DEC-9008)

### DEC-9016 — Require publication conformance, explicit blockers and separate human acceptance

**Rationale**

This accepted ADR and its generated projections are governance artifacts only.
No AI 1.4/ACC 1.4 contract, runtime materializer, public capability or Constructed
result is published or enabled. Human architectural acceptance must identify
the reviewed ADR/commit before successor publication. Do not fabricate approval
or steelman metadata. Explicit human authorization now permits ADR acceptance
and merging PR #180 after every required qualification gate passes; it does
not authorize successor publication or runtime execution.

Successor frozen conformance must cover all 27 categories/branches, each exact
A/R producer, long and source-permitted empty strings, absent/invalid inputs,
unknown/competing producer rows, broken references, conditional requirements,
wrong operations/types/destinations, forged receipts and contextual evidence,
shared-identity conflicts, literal lifecycle, native standalone blocking,
normative-proposition lifecycle absence, custom exclusions, source/resource
permutations, missing semantic extensions and independent representation versus
semantic mismatches. Missing required output blocks complete materialization;
unsupported capability is Unavailable, established violation Rejected, and
Unresolved requires an actually established governed unresolved dependency.
Retain independent diagnostics and Rejected > Unavailable > Unresolved.

Validate whole actual entities/records and independent replay in future Rust
execution tests; publication/design tests do not execute interpretation or
prove Constructed. Require historical fingerprint/selection preservation and
deterministic resource generation. Whole-result semantic ledgers, equality,
complete NM assembly and construction remain separately required after bounded
entity materialization. No digest/count/replay-copy shortcut is permitted.

**Traceability**
- Refines: Compare complete expected and observed semantic ledgers for construction round trips (DEC-0268)
- Refines: Require human acceptance before publication and separately authorized execution (DEC-9008)





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0301 | Every applicable required output MUST have exactly one qualified producer; a BLOCKED prerequisite MUST NOT count as… | MUST / design | automated |
| INV-0302 | Generated names and summaries MUST use exactly the selected type-scoped input and literal operation, without… | MUST / design | automated |
| INV-0303 | The entity/system summary MUST be explicit alias_name label duplication only; it MUST NOT infer substantive… | MUST / design | automated |
| INV-0304 | Output qualification MUST independently resolve applicable branches/conditions and bind selectors, rule identity,… | MUST / design | automated |
| INV-0305 | A representation copy MUST NOT add independent semantic ownership, remove its authored semantic destination, or… | MUST / design | automated |
| INV-0306 | Missing lifecycle, ownership, endpoint or output-recipe authority MUST remain BLOCKED and MUST prevent complete… | MUST / design | automated |
| INV-0307 | Successor output authority MUST select exact AI 1.4 and ACC 1.4 after publication, reuse unchanged NM 2.5, and MUST… | MUST / design | automated |
| INV-0308 | This ADR MUST NOT imply human acceptance without explicit recorded approval; its acceptance MUST NOT imply successor… | MUST / design | automated |

### INV-0301

**Statement**

Every applicable required output MUST have exactly one qualified producer; a BLOCKED prerequisite MUST NOT count as a producer or complete coverage.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Require exactly one qualified producer for every applicable normalized output

**Upheld by decisions**
- Require exactly one qualified producer for every applicable normalized output (DEC-9009)

### INV-0302

**Statement**

Generated names and summaries MUST use exactly the selected type-scoped input and literal operation, without implicit fallback, prose generation, truncation or formatting.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Use exact authored names or explicit type-scoped alias labels

**Upheld by decisions**
- Use exact authored names or explicit type-scoped alias labels (DEC-9010)

### INV-0303

**Statement**

The entity/system summary MUST be explicit alias_name label duplication only; it MUST NOT infer substantive description or borrow declaring-ADR content.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Distinguish authored summaries, literal representation copies and absent narrative

**Upheld by decisions**
- Distinguish authored summaries, literal representation copies and absent narrative (DEC-9011)

### INV-0304

**Statement**

Output qualification MUST independently resolve applicable branches/conditions and bind selectors, rule identity, inputs, operation, classification, equality and contextual dependencies.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Bind each output producer to exact branch, selectors, operation and evidence

**Upheld by decisions**
- Bind each output producer to exact branch, selectors, operation and evidence (DEC-9012)

### INV-0305

**Statement**

A representation copy MUST NOT add independent semantic ownership, remove its authored semantic destination, or substitute representation verification for whole-ledger equality.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Keep independent representation verification separate from semantic equality

**Upheld by decisions**
- Keep independent representation verification separate from semantic equality (DEC-9013)

### INV-0306

**Statement**

Missing lifecycle, ownership, endpoint or output-recipe authority MUST remain BLOCKED and MUST prevent complete materialization without invented semantics or synthetic roots.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Account for every required destination across entity, relationship and value branches

**Upheld by decisions**
- Account for every required destination across entity, relationship and value branches (DEC-9014)

### INV-0307

**Statement**

Successor output authority MUST select exact AI 1.4 and ACC 1.4 after publication, reuse unchanged NM 2.5, and MUST NOT mutate historical resources or current selection.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance

**Upheld by decisions**
- Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance (DEC-9015)

### INV-0308

**Statement**

This ADR MUST NOT imply human acceptance without explicit recorded approval; its acceptance MUST NOT imply successor publication, materialization execution, public capability, semantic_equivalent or Constructed.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Require publication conformance, explicit blockers and separate human acceptance

**Upheld by decisions**
- Require publication conformance, explicit blockers and separate human acceptance (DEC-9016)






## Governance / Bindings / Evidence

### Governance

**Approved by:** egallmann
**Approved date:** 2026-10-24 17:47:27+00:00


## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)
- [ADR-L-0035](ADR-L-0035-governed-composition-intent-binding-for-authoring-construction.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)

**References**
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)
- [ADR-L-0035](ADR-L-0035-governed-composition-intent-binding-for-authoring-construction.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-L-0034 — Detached Normalized Semantic Equivalence for Authoring Construction](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md) | refines | `DEC-9009 -[:refines]-> DEC-0269` |
| [ADR-L-0037 — Lossless Authored Lifecycle and Declaring-ADR Provenance](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md) | refines | `DEC-9013 -[:refines]-> DEC-9005` |
| [ADR-L-0039 — Forward Identity Representation Recipes](ADR-L-0039-forward-identity-representation-recipes.md) | refines | `DEC-9017 -[:refines]-> DEC-9015` |




## Notes

Accepted following explicit human approval in this task of the architecture
reviewed at PR #180 head 349eb73a94d24691b9f11303fec0607b417dfa0c,
including DEC-9009 through DEC-9016 and INV-0301 through INV-0308.
After the approval precondition was explicitly requested, the human confirmed:
"I am providing the approval for this task". That authorization covers this
ADR acceptance and merging PR #180 only after all required gates pass.
Governance metadata records that authorization, not a fabricated hosted review
or steelman assessment. All canonical identities and architectural choices
are retained. The ignored Design Journal is convergence state, not authority.
AI 1.4 and ACC 1.4 publication, Rust materialization and all runtime successor
capabilities remain separate prerequisites. NM 2.5, frozen authorities, current
SCS, protocol and public/runtime boundaries remain unchanged. Derived artifacts
are repository-generated evidence, never independent semantic authority.


---

*Generated from ADR-L-0038 by ADR Architecture Kit (projection v3)*