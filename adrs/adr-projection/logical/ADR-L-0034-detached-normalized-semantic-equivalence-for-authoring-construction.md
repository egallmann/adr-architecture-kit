<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 12b9e793788ca6568f019ca2d54282981706f1daa35e8cb86e98e1827a17c445
rendered_hash: ee6b93823dd853bcfeb0274ae04f7784753957a68a7dbd45138ac2bee1b82477
-->

# ADR-L-0034: Detached Normalized Semantic Equivalence for Authoring Construction

## Identity / Status

**Type:** logical<br>
**Status:** accepted<br>
**Alias:** ADR-L-0034<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-10-04<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, authoring, semantic-authority, normalized-model, determinism, conformance<br>
**Tags:** authoring-construction, whole-result-equivalence, architecture-interpretation, normalized-model-2.4, detached-context, semantic-preservation<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0034 |
| Status | accepted |
| Decisions | 6 |
| Invariants | 8 |


## Context

ADR-L-0029 through ADR-L-0033 establish detached semantic construction,
exact candidate source representation, whole-result equivalence as a
construction gate, and downstream governed candidate binding. ADR-L-0032
requires candidate source roots to pass through exact Authoring 1.7
validation, Architecture Interpretation 1.1, and a complete Normalized
Model 2.4 result before semantic equivalence may qualify construction.

The current executable path has minimal source-root selection but its
comparison is a narrow entity/gap.context check and its normalized_result
is transitional request metadata rather than a complete Normalized Model.
The complete document interpreter requires materialization context absent
from detached construction, and standalone fragments do not yet participate
in its whole-model assembler. This authority defines the expected and
observed comparison inputs, a detached output context, closed field
dispositions, whole-result aggregation, and evidence boundaries needed for
a deterministic implementation.

This ADR is design authority only. It does not implement the comparator,
candidate binding, Promotion Contract preparation, repository placement,
persistence, Git mutation, Runtime admission, or consumer admission.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0268 | Compare complete expected and observed semantic ledgers for construction round trips | — |
| DEC-0269 | Require exact Architecture Interpretation dispositions for all supported Authoring 1.7 fields | — |
| DEC-0270 | Produce complete Normalized Model results using a deterministic detached context | — |
| DEC-0271 | Define the only authorized differences in construction semantic comparison | — |
| DEC-0272 | Distinguish semantic provenance from candidate integrity and representation ceremony | — |
| DEC-0273 | Define whole-result aggregation for documents, fragments, relationships, and unresolved semantics | — |

### DEC-0268 — Compare complete expected and observed semantic ledgers for construction round trips

**Rationale**

The expected side is the complete semantic state after construction has
established identity, resolved references, selected exact custom
qualification, and validated composition, but before serialization
ceremony. It is derived from canonical construction state, not the original
request DTO and not candidate bytes.

The observed side is extracted from the complete schema-valid Normalized
Model 2.4 produced by validating and interpreting only the sealed minimal
candidate source roots through exact Authoring 1.7 and Architecture
Interpretation 1.2 authority. The observed projection uses the same
contract-owned field disposition map to produce the same ledger shape.

Complete whole-result qualification is governed by immutable Authoring
Construction 1.1, the successor to ACC 1.0. ACC 1.0 and its frozen
conformance remain unchanged historical authority. ACC 1.1 consumes AI
1.2 and retains Normalized Model 2.4 under the qualified open-metadata
preservation rule defined below.

A ledger contains every entity, semantic relation, owner-local topology
value, compatibility occurrence, composition-derived relation, and
unresolved semantic record exactly once. Entities match by canonical
UUIDv7, relationships by canonical UUIDv7, topology components by owner
UUID plus topology_key, and noncanonical compatibility records as a
multiset keyed by relationship type, owner scope, resolved endpoints,
and authored semantic properties. Multiplicity is significant. A
source-occurrence discriminator participates only when exact AI authority
declares a semantic owner-local key; source pointers, array positions,
and generated record IDs are not occurrence identity by default.
Duplicate canonical identities or ambiguous semantic occurrences fail
closed.

Canonical comparison is over every semantic ledger member and its
multiplicity. Outer record collections sort by governed identity;
source arrays retain order whenever exact source authority makes order
semantic. Request order, root traversal order, source filename, and
incidental normalized-array order do not become semantic identity.

Byte equality, digest equality, fingerprint equality, count equality,
per-fragment success, and selected field spot checks are not equivalence.
semantic_equivalent is permitted only after every expected value and
observed value has one governed counterpart and all four authorized
difference rules have been applied. Unclassified, missing, additional,
or nondeterministically comparable semantics prevent success.

### DEC-0269 — Require exact Architecture Interpretation dispositions for all supported Authoring 1.7 fields

**Rationale**

Architecture Interpretation owns source-to-Normalized-Model meaning.
ACC orchestrates the expected ledger, sealed-source interpretation,
normalized-result assembly, comparison, and diagnostics; ACC does not
define a second interpretation map.

This capability MUST use the immutable Architecture Interpretation 1.2
successor to AI 1.1. AI 1.1, including its fixed semantic-contract
fingerprint and frozen normative conformance, remains historical authority
and MUST NOT be edited. AI 1.2 owns the new machine-evaluable disposition
resource and native detached interpretation defined here.

The selected exact AI authority MUST provide a machine-evaluable
disposition for every semantic field reachable through ACC's supported
Authoring Construction types. Each field has a stable AI-owned
semantic-field key formed from its semantic type and schema-relative field
selector, encoded as `<semantic-type>#<schema-relative-JSON-Pointer>` (for
example, `entity/gap#/context`). The selector is relative to the field's
schema, uses RFC 6901 token escaping, and is not relative to a particular
source instance. AI 1.2 MUST guarantee key uniqueness within each semantic
unit; duplicate or ambiguous keys fail closed. It excludes runtime array
indexes, root traversal positions, embedded positions, candidate
filenames, and incidental container placement unless exact source
authority makes that order or location semantic. Each field has exactly
one disposition: direct_semantic_value at an exact normalized path;
canonical_field_placement with a named stable source field key and
normalized semantic destination;
compatibility_projection with a closed semantic matching tuple and
multiplicity rule;
declared_absence naming the exact source field and omitted normalized
location; or deterministic_ceremony naming an exactly derivable
representation value. No sixth implicit class exists. An unclassified
field, unsupported projection, or unknown selected schema member fails
closed.

The source-field inventory at design time covers all three Authoring 1.7
ADR roots; decision, capability, boundary, contract, gap, invariant,
interface, component, implementation_decision, system, system_boundary,
data_flow, evidence_expectation, normative_proposition, custom_entity,
custom_relationship, topology component/relationship, relationship
fragments, alternatives, technology choices, consequences, and every
recursively schema-governed root object and array. Every field with no
first-class normalized destination MUST receive an explicit
direct_semantic_value disposition to the reserved
metadata.semantic_extensions object. Its entries are keyed by the stable
AI-owned semantic-field key within the independently identified semantic
unit, and store the complete typed JSON value without coercion; the key
and value participate in semantic equality. Runtime source-instance
pointers remain available for integrity, diagnostics, provenance, and
replay, but are not equality keys merely because they locate a value.
This ADR defines
the preservation destination, but the selected AI resource MUST enumerate
each exact field key and destination and MUST be checked against the closed
schema closure. There is no runtime default for a missing mapping: any
field absent from the selected resource fails closed. Structured source
containers that compose child units MUST map their membership and any
governed order without duplicating child payload semantics; child fields
are compared on the child semantic unit. An ordered array remains an
ordered typed value under its stable field key; runtime array indices do
not enter field or semantic-unit identity. Reordering a collection whose
order is not governed changes neither identity nor equality.

Existing metadata.source_semantics is source replay/provenance evidence;
it cannot substitute for semantic output or make a dropped value equal.
A source value has exactly one semantic destination in the ledger: a
first-class normalized path, an explicitly mapped semantic extension, or
a compatibility occurrence. Replay copies do not create a second semantic
value. In particular,
entity/gap.context is semantic and its loss is semantic_mismatch (C32).
No unclassified field may disappear, and implementation limitations
cannot be labeled declared_absence.

Authoring Construction 1.1 is the immutable successor to ACC 1.0 for
complete whole-result qualification. ACC 1.1 consumes exact AI 1.2
authority and owns ledger construction, comparison, diagnostics, and the
closed meaning of normalized_result.model. ACC 1.0, including its fixed
fingerprint and frozen C01-C42 conformance, remains historical authority
and MUST NOT be edited. Normalized Model 2.4 remains unchanged: its open
metadata object is only a schema-valid carrier here; semantic-extension
meaning is conferred by exact AI 1.2 qualification and does not give
generic NM 2.4 consumers intrinsic semantics for arbitrary metadata.

### DEC-0270 — Produce complete Normalized Model results using a deterministic detached context

**Rationale**

Complete Normalized Model 2.4 output for detached construction uses the
explicit DetachedCandidateContext, not repository materialization
context. Its domain is
adr-kit.detached-candidate-normalization/v1. The fixed provider_kind is
adr-kit-detached-candidate and the fixed architecture_namespace is
urn:adr-kit:detached-candidate:v1.

scope_root is
urn:adr-kit:detached-candidate:v1:source-basis:sha256:<lowercase basis digest hex>.
For each root, artifact_path is
urn:adr-kit:detached-candidate:v1:source-basis:sha256:<lowercase basis digest hex>/root:sha256:<SHA-256 of UTF-8 source_ref>.
canonical_source_ref remains the candidate's logical source identity and
source_pointer remains its exact interpreted pointer. The artifact_path
value is a domain-separated opaque locator, not a filesystem path or
repository destination. All digests use lowercase hexadecimal.

Derived provider, namespace, URI, scope, and root locator values have no
independent authoring choice and are deterministic_ceremony. Their domain
and derivation are nevertheless part of integrity and reproducibility
evidence. The context is derived only from the sealed source-basis
digest, candidate source identity, exact contract identity, and these
fixed constants. It cannot imply filename allocation, alias reservation,
repository placement, persistence, or admission. Repository materializers
use a separate context variant. Candidate binding cannot reinterpret a
detached locator as a repository target.

### DEC-0271 — Define the only authorized differences in construction semantic comparison

**Rationale**

deterministic_ceremony is a field fully and uniquely derivable from
established identity, exact selected authority, sealed basis identity,
or the fixed detached context, and contains no independent semantic
choice. Examples are the normalized-model schema envelope, canonical
fingerprints, alias_ref derived from aliases, UUID-derived created_at,
and detached context identifiers. A generated lifecycle, alias, date,
UUID, qualification, or relationship meaning is never ceremony merely
because an implementation produced it.

canonical_field_placement is an exact lossless mapping from an AI-owned
stable semantic-field key (semantic type plus schema-relative field
selector) to a normalized semantic destination declared by Architecture
Interpretation. Runtime source-instance pointers may locate the value but
do not define its semantic field identity. The source and destination
values must be the same canonical semantic value. Examples include
title to name, status to lifecycle_stage, evidence kind to evidence_kind,
and related_entities to related_entity_ids where the selected exact
mapping declares those paths. Truncation, fallback, value-changing
normalization, or field loss is mismatch.

compatibility_projection is permitted only for an Architecture
Interpretation mapping explicitly marked compatibility_projection.
Equality uses relationship type, resolved endpoint identities, owning
document or owner-local scope, authored semantic properties, and
multiplicity. Exact AI authority may add a semantic owner-local key when
the source contract defines one. Source pointers, array positions, and
generated noncanonical assertion IDs are not semantic identity by
default. Generated assertion IDs, display pointers, or digests are
ceremony and cannot identify or equal the relation. Missing, additional,
redirected, or semantically changed projections fail.

declared_absence is permitted only when the exact selected authority names
the exact source type and field, normalized target location, and absence
rule. The existing normative-proposition lifecycle absence is the
specific current example. A field omitted by an incomplete mapping or
implementation is never declared absent. An unmentioned field is not
classified.

### DEC-0272 — Distinguish semantic provenance from candidate integrity and representation ceremony

**Rationale**

Semantic equality includes provenance facts that distinguish or qualify
meaning: canonical UUIDs and aliases; resolved reference identities;
exact custom type qualification/version/fingerprint; relationship
endpoints; owner-local topology keys and scope; composition ownership;
and compatibility relation type, owner scope, endpoints, semantic
properties, and multiplicity.

Candidate/source integrity evidence is independently verified and retained
even when not compared as semantic meaning. It includes source_ref and
pointers, complete candidate artifact and root membership, exact schema
selector, serialization profile, exact bytes and content digests, source
contract/resource closure, basis descriptor/digest, identity-establishment
evidence, and construction/composition map. Integrity evidence cannot be
erased because the semantic ledger compares equal.

metadata.source_semantics is a source replay/provenance copy, not by itself
an equality claim. metadata.semantic_extensions carries semantic values
and participates in equality. Source-contract qualification is
integrity/qualification evidence; custom semantic qualification is both
semantic meaning and qualification. Candidate-local source_ref becomes
semantic only when the AI mapping declares it as owner/occurrence
identity; otherwise it is integrity evidence. Runtime source-instance
pointers are locators for integrity, diagnostics, provenance, and replay,
not semantic equality keys by default. Detached provider/context,
generated URI, generated fingerprints, validation summaries, and outer
storage ordering are representation provenance and may be normalized only
by the deterministic_ceremony rules.

Repository artifact paths, provider instances, admission state, and Git
state do not enter detached equivalence. Later candidate binding verifies
them under ADR-L-0033 without changing construction's comparison result.

### DEC-0273 — Define whole-result aggregation for documents, fragments, relationships, and unresolved semantics

**Rationale**

The expected ledger is built from the complete post-construction semantic
state after explicit composition and identity resolution. The observed
normalized model is interpreted from the minimal sealed root basis. A
selected authoring_document contributes its document entity, embedded
child entities, relations, topology values, and derived records once.
Its separately retained child candidate_artifacts stay first-class output
evidence but are not interpreted or counted again as roots. A standalone
authoring_fragment is interpreted as a native semantic unit and is never
wrapped in a synthetic ADR. Mixed document and standalone roots contribute
the canonical union. Reference-only dependencies are not definitions.
For a nested collection that composes child units, AI authority maps the
collection's semantic membership and any governed order to an explicit
identity sequence or composition relation, while each child's authored
fields map to that child unit. The complete nested child object is not
copied again into the parent semantic extension. This prevents both
omission and double counting.

Semantic-extension entries match by (semantic-unit identity, stable
AI-owned semantic-field key), never by runtime instance JSON Pointer
unless exact authority independently makes that location semantic. The
complete typed JSON value participates in equality without coercion;
values already mapped to first-class normalized properties are not
duplicated. Embedded child values remain with the child semantic unit
rather than being copied into a parent extension.

Canonical UUIDv7 identifies ADRs, canonical entities, custom entities,
normative propositions, and canonical relationships. Topology components
use (owner UUID, topology_key). Noncanonical compatibility occurrences use a semantic multiset keyed by
(owner UUID or owner-local scope, relationship type, resolved from UUID,
resolved to UUID, and all authored semantic properties), preserving
multiplicity. A source occurrence key is included only when exact source
authority defines a semantic owner-local key; a JSON Pointer or array
index is not such a key merely because it locates the source value.
Composition-derived relations use their declared owner and endpoints.
Duplicate canonical identities or semantically ambiguous projections
fail closed.

Exact source authority defines which value arrays are ordered. Such arrays
are preserved, including owner-local data-flow paths and authored ordered
collections. Result collections and source roots are canonicalized by
governed identity; request order and incidental root traversal order do
not affect semantic equality. Unresolved records remain explicit and
follow ACC's outcome rules.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0276 | A Constructed Authoring Construction result MUST contain a schema-valid complete Normalized Model 2.4 derived from… | MUST / design | automated |
| INV-0277 | Every machine-evaluable Authoring 1.7 semantic field reachable through supported construction MUST have exactly one… | MUST / design | automated |
| INV-0278 | Detached normalized-output context MUST be deterministic under adr-kit.detached-candidate-normalization/v1 and MUST… | MUST / design | automated |
| INV-0279 | Candidate source interpretation MUST consume only the minimal non-overlapping source roots; every embedded child… | MUST / design | automated |
| INV-0280 | Semantic equality MUST include provenance facts that disambiguate meaning, while candidate source integrity and… | MUST / design | automated |
| INV-0281 | Noncanonical compatibility records MUST compare by declared relation type, resolved endpoints, owner scope, semantic… | MUST / design | automated |
| INV-0282 | Candidate, basis, entity, and normalized-model digests or fingerprints MUST NOT substitute for complete structural… | MUST / design | automated |
| INV-0283 | Construction equivalence evidence MUST remain detached and MUST NOT authorize candidate binding, repository… | MUST / design | manual |

### INV-0276

**Statement**

A Constructed Authoring Construction result MUST contain a schema-valid complete Normalized Model 2.4 derived from the minimal sealed candidate source roots and MUST report semantic_equivalent only after whole-ledger equality succeeds.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

A partial model, source validation, or fragment-level interpretation cannot qualify the complete round trip.

### INV-0277

**Statement**

Every machine-evaluable Authoring 1.7 semantic field reachable through supported construction MUST have exactly one exact Architecture Interpretation 1.2 disposition; unclassified fields MUST fail closed and semantic values without a first-class Normalized Model field MUST be preserved in metadata.semantic_extensions and compared by (semantic-unit identity, stable AI-owned semantic-field key), independent of runtime source-instance location unless exact authority declares that location semantic.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Explicit lossless extension preserves semantic data without inventing new graph concepts or treating provenance copies as semantic output.

### INV-0278

**Statement**

Detached normalized-output context MUST be deterministic under adr-kit.detached-candidate-normalization/v1 and MUST NOT imply or be reinterpreted as repository placement, persistence, or admission.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

A complete detached model needs generated materialization fields without claiming a repository destination.

### INV-0279

**Statement**

Candidate source interpretation MUST consume only the minimal non-overlapping source roots; every embedded child MUST contribute its semantic identity and values exactly once, and standalone fragments MUST remain native roots without synthetic ADR wrappers.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

This preserves ADR-L-0032 and PR

### INV-0280

**Statement**

Semantic equality MUST include provenance facts that disambiguate meaning, while candidate source integrity and representation provenance MUST be independently verified and MUST NOT be conflated with semantic equivalence.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Equal meaning does not authenticate source evidence, and intact bytes do not establish semantic equality.

### INV-0281

**Statement**

Noncanonical compatibility records MUST compare by declared relation type, resolved endpoints, owner scope, semantic properties, and multiplicity; a source occurrence key participates only when exact source authority defines it as semantic, and generated noncanonical identifiers MUST NOT substitute for semantic equality.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Compatibility record identity is generated and cannot establish that a semantic relationship is preserved.

### INV-0282

**Statement**

Candidate, basis, entity, and normalized-model digests or fingerprints MUST NOT substitute for complete structural semantic comparison unless their exact governed preimage is proven complete for that claim.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Existing entity fingerprints omit semantic fields and model fingerprints include representation provenance.

### INV-0283

**Statement**

Construction equivalence evidence MUST remain detached and MUST NOT authorize candidate binding, repository mutation, Promotion Contract execution, Git operations, Runtime admission, or consumer admission.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

ADR-L-0033 remains downstream and independently verifies construction qualification.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)
- [ADR-L-0033](ADR-L-0033-governed-candidate-binding-for-authoring-construction.md)

**References**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)
- [ADR-L-0033](ADR-L-0033-governed-candidate-binding-for-authoring-construction.md)





## Notes

The complete field-disposition inventory and option analysis were recorded
in the local ignored Design Journal at
.adr-kit/design-journal/normalized-model-24-whole-result-equivalence.md.
That journal is exploratory evidence, not durable authority; this ADR's
decisions and invariants are the promoted design surface.

With this ADR accepted, the next authority sequence is fixed: publish
immutable Architecture Interpretation 1.2 with exact field-disposition and
detached interpretation authority; publish immutable Authoring Construction
1.1 consuming AI 1.2; retain Normalized Model 2.4 unchanged under the
AI-qualified metadata extension rule; then implement native fragment and
mixed-root Normalized Model 2.4 assembly, define and validate the detached
context, close ACC normalized_result.model around the complete model, and
provide deterministic whole-ledger diagnostics and reproducible
qualification evidence. Architecture Interpretation retains all
source-to-normalized meaning. ACC owns orchestration and comparison only.

Existing ACC metadata.source_semantics is source provenance and does not by
itself preserve semantic meaning for equality. Semantic values without a
dedicated Normalized Model property are losslessly carried in the
AI 1.2-qualified metadata.semantic_extensions object and compared by
(semantic-unit identity, stable AI-owned semantic-field key), not runtime
source-instance pointer. C32 remains the generalized semantic-loss negative
case: gap.context is an authored semantic value and its absence from the
semantic extension is a mismatch, even if raw source/provenance still
records it. The conformance vector should exercise an observed-side omission
without any gap-specific production comparator.

Architecture Interpretation 1.2 authority owns direct values, canonical
placements, compatibility projections, declared absence, stable
semantic-field keys, and the complete field-disposition inventory. ACC 1.1
consumes the exact selected AI 1.2 resource closure. AI 1.1 and ACC 1.0
remain immutable historical contract identities; neither may be amended in
place. Normalized Model 2.4 remains unchanged because its schema permits the
metadata carrier and AI 1.2 alone qualifies the extension's meaning.

The follow-on conformance set must cover simple, composed, standalone and
mixed roots; C05/C07 minimal roots; C32 field loss; custom properties and
qualification; canonical/custom relationships; topology compatibility and
composition-derived records; unresolved results; ordered values; root
ordering; UUID/endpoint changes; unclassified source fields; detached-context
determinism; and exact Python/Node observation of the Rust result.


---

*Generated from ADR-L-0034 by ADR Architecture Kit (projection v3)*