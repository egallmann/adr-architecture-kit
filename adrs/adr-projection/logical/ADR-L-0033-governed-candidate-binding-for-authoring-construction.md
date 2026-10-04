<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 17c13b540d1955e1efc347ee7618f8a86929eb4ad7f13c64889fbfb696687564
rendered_hash: effbf70024136883cca1314cdbed62c80969f8a5675676b005748b059b9690dd
-->

# ADR-L-0033: Governed Candidate Binding for Authoring Construction

## Identity / Status

**Type:** logical<br>
**Status:** proposed<br>
**Alias:** ADR-L-0033<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-10-03<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, authoring, semantic-authority, governance, repository-boundaries<br>
**Tags:** candidate-binding, detached-construction, promotion-contract, repository-admission, self-hosting<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0033 |
| Status | proposed |
| Decisions | 7 |
| Invariants | 8 |


## Context

ADR-L-0029 through ADR-L-0032 establish detached semantic construction,
exact candidate source representation, and canonical qualification
boundaries. They deliberately do not admit candidate bytes into repository
authority. ADR-Kit therefore needs a governed handoff from a complete,
qualified construction result to the existing Design Journal Promotion
Contract (PC), without moving semantic interpretation into promotion or
introducing a second durable intent lifecycle.

This decision defines the provider-owned binding boundary and the conditions
under which that handoff may become promotable. It does not claim that
ADR-Kit 0.12.1 implements or qualifies candidate binding. The known C05/C07
minimal-root discrepancy and incomplete whole-result normalized-equivalence
proof remain implementation and self-hosting prerequisites under the
existing construction authority; they do not weaken that authority or block
promotion of this design decision.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0261 | Assign candidate-to-repository binding to the ADR-Kit promotion provider | — |
| DEC-0262 | Require canonical verification of construction evidence before preparation | — |
| DEC-0263 | Restrict initial candidate persistence to complete qualified ADR documents | — |
| DEC-0264 | Require explicit alias intent and preserve aliases and paths for existing records | — |
| DEC-0265 | Bind complete mutation accounting and resolved repository targets to approved intent | — |
| DEC-0266 | Use genuine journal outcomes with the existing STE Promotion Contract v0.1 | — |
| DEC-0267 | Bound application by a single governance writer and stale-state rejection | — |

### DEC-0261 — Assign candidate-to-repository binding to the ADR-Kit promotion provider

**Rationale**

A caller presents a qualified detached construction result, explicit
repository mutation intent, genuine design-journal outcome associations,
and repository context with an expected baseline. The ADR-Kit provider
verifies the candidate and binds its exact document-root payloads to
explicit repository targets while preparing the existing Promotion
Contract. Construction remains the owner of semantic meaning, UUID
establishment, candidate bytes, source qualification, and complete
normalized equivalence. Binding does not reinterpret or rewrite those
semantics. The existing prepared Promotion Contract is the sole governed
handoff; this capability creates no separate Authoring Transaction or
Mutation Proposal lifecycle artifact. It is a provider-qualified input
variant behind the existing preparation lifecycle, with peer Python and
Node behavior required before parity is claimed.

### DEC-0262 — Require canonical verification of construction evidence before preparation

**Rationale**

A DTO type, Constructed outcome, sealed flag, or caller-provided
qualification claim is not proof. Preparation MUST independently
re-establish construction qualification through canonical semantic
authority before producing a promotable contract. Verification MUST cover
exact candidate bytes and digests, source selectors and serialization
profile, qualified authority and resource closure, sealed source-basis
integrity, artifact/root consistency, identity continuity, and complete
whole-result normalized equivalence. Deterministic construction replay
using established identities is an acceptable implementation strategy;
another canonical verification operation is also acceptable if it proves
the same governed facts without altering candidate meaning. Byte
integrity, semantic qualification, and provenance are verified distinctly.
Missing or unresolved authority cannot become readiness. This verification
reuses canonical semantic authority; it does not add a second compiler or
interpreter in promotion.

### DEC-0263 — Restrict initial candidate persistence to complete qualified ADR documents

**Rationale**

Initial binding admits only complete qualified authoring_document roots in
the supported ADR families. A standalone authoring_fragment remains a
valid detached construction product but cannot independently become a
repository payload under this capability. Embedded fragments are
accounted for through their document root, and reference-only artifacts
remain dependencies without writes. Binding does not wrap fragments in
synthetic ADRs, assemble fragments, or reinterpret source references as
repository destinations.

### DEC-0264 — Require explicit alias intent and preserve aliases and paths for existing records

**Rationale**

Create intent supplies every required alias before construction. Binding
checks the proposed aliases against active, historical, and reserved
repository authority, including conflicts within the mutation set; it
rejects an incomplete occupancy basis. A conflict requires revised intent
and reconstruction. No allocator, reservation, high-water mutation, or
preparation-time alias rewrite is introduced. Amend and supersede preserve
existing aliases and repository paths in the initial scope. Any change to
those values requires a separately constructed and prepared result under
later authority.

### DEC-0265 — Bind complete mutation accounting and resolved repository targets to approved intent

**Rationale**

Explicit caller intent associates each mutable construction root with one
requested repository operation and placement. Binding observes the
repository, establishes the expected previous state and baseline, resolves
the destination, checks conflicts, and records the complete mutation
ledger. Every destination receives one complete constructed post-image.
The repository instance, resolved path, semantic identity, operation,
source-root association, payload digest, previous-state commitment, and
whole-set accounting are material execution intent and participate in the
Promotion Contract's locked provider evidence. Apply derives execution
only from that approved evidence and verifies it again. Sidecar state may
cache a resolution but cannot redirect it. Create, amend, and explicit
supersede are eligible under this authority only when every affected
complete post-image and destination is covered by the same lock.

### DEC-0266 — Use genuine journal outcomes with the existing STE Promotion Contract v0.1

**Rationale**

A genuine Design Journal with actual stable outcomes exists before
construction. The Promotion Contract continues to reference those actual
outcomes using its existing provider, baseline, mutation, payload, schema,
validation, and human-lock semantics. Candidate qualification and
repository-binding evidence supplement outcome anchoring; they do not
fabricate a journal, outcome, disposition, or convergence state. ADR-Kit
mirrors the STE-owned contract and adds only provider-specific evidence
and enforcement. Candidate-backed preparation fits the existing PC
semantics; no generic STE contract change is required for this scope.

### DEC-0267 — Bound application by a single governance writer and stale-state rejection

**Rationale**

The initial guarantee assumes one governance writer throughout final
verification, replacement, regeneration, validation, and recovery. The
provider establishes an exact expected repository revision and protected
authority scope, verifies the clean protected state during preparation,
before lock, and immediately before replacement, and rejects stale or
conflicting state without automatic rebase or merge. Interrupted
sequential replacements use verified pre-images and approved destinations
for bounded recovery. This is not filesystem compare-and-swap, writer
exclusion, or global atomicity; unexpected recovery state stops for
intervention. Git branch, commit, pull request, merge, and release remain
external governance operations.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0268 | Candidate binding MUST preserve the exact qualified construction result and MUST NOT change candidate bytes, UUID… | MUST / design | automated |
| INV-0269 | Every mutable candidate source root MUST have exactly one explicit disposition and every writable root MUST map to… | MUST / design | automated |
| INV-0270 | For every mutation, the freshly verified repository instance, destination, operation, semantic identity, source-root… | MUST / design | automated |
| INV-0271 | Every fact that can change payload bytes, semantic identity, operation, target, repository scope, baseline,… | MUST / design | automated |
| INV-0272 | Candidate application MUST reject any change to the expected baseline, protected authority scope, destination… | MUST / design | automated |
| INV-0273 | Binding and promotion MUST NOT infer aliases, lifecycle state, relationships, supersession, target identity,… | MUST / design | manual |
| INV-0274 | Candidate binding and repository application MUST NOT claim Runtime admission or perform external Git branch,… | MUST / design | manual |
| INV-0275 | A prepared Promotion Contract MUST NOT be mechanically ready unless exact candidate integrity, canonical semantic… | MUST / design | automated |

### INV-0268

**Statement**

Candidate binding MUST preserve the exact qualified construction result and MUST NOT change candidate bytes, UUID identity, source selectors, serialization profile, source-basis commitment, semantic content, or construction qualification; any content change requires new construction.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Repository placement and preparation cannot become semantic-authoring authority.

### INV-0269

**Statement**

Every mutable candidate source root MUST have exactly one explicit disposition and every writable root MUST map to one explicit mutation; binding MUST NOT silently subset a whole-qualified construction result, and a smaller mutation scope requires an independently qualified construction result.

**Scope:** promotion

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Root membership and mutation accounting must agree with the original qualified request and construction evidence.

### INV-0270

**Statement**

For every mutation, the freshly verified repository instance, destination, operation, semantic identity, source-root association, previous-state condition, and payload MUST equal the values covered by the human-approved locked intent; any mismatch MUST prevent execution under that lock.

**Scope:** promotion

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Mutable resolution sidecars cannot redirect approved candidate bytes.

### INV-0271

**Statement**

Every fact that can change payload bytes, semantic identity, operation, target, repository scope, baseline, qualification, conflict condition, or mutation-set completeness MUST participate in the Promotion Contract locked intent and MUST NOT be carried only as unlocked provenance.

**Scope:** promotion

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Human approval applies to the complete execution-relevant candidate binding.

### INV-0272

**Statement**

Candidate application MUST reject any change to the expected baseline, protected authority scope, destination pre-image, or alias occupancy detected at required verification points; the documented single-governance-writer condition MUST cover final verification, sequential replacement, and recovery.

**Scope:** promotion

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Stale-state rejection is conditional on an explicit operating assumption and is not represented as compare-and-swap or global atomicity.

### INV-0273

**Statement**

Binding and promotion MUST NOT infer aliases, lifecycle state, relationships, supersession, target identity, destination, or other material intent from prose, paths, ordering, filenames, or repository contents; the complete semantic post-image and requested mutations MUST be explicit construction and caller intent.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Human and construction authority remain explicit and separable from repository observation.

### INV-0274

**Statement**

Candidate binding and repository application MUST NOT claim Runtime admission or perform external Git branch, commit, pull-request, merge, or release operations.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Repository file application, architectural acceptance, Runtime admission, and Git governance are distinct authorities.

### INV-0275

**Statement**

A prepared Promotion Contract MUST NOT be mechanically ready unless exact candidate integrity, canonical semantic qualification, complete normalized-equivalence evidence, identity continuity, source-root accounting, repository preconditions, and genuine journal outcome associations are verified.

**Scope:** promotion

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Asserted success flags and incomplete local evidence cannot substitute for qualification of the complete result.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)

**References**
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0032](ADR-L-0032-candidate-source-representation-and-round-trip-basis-authority.md)





## Notes

The accepted Design Journal and Promotion Contract v0.1 specifications are
owned by STE. This ADR uses the existing generic semantics and does not
redefine them through ADR-Kit's local schema mirrors. The architecture
conclusion is: NO_GENERIC_STE_CONTRACT_CHANGE_REQUIRED. A genuine journal
with actual outcomes must precede construction; absent journal authority
fails preparation rather than creating synthetic outcomes.

Supersession is represented by explicit typed semantic intent and complete
constructed post-images for both the new/superseding ADR and the existing
ADR. Existing UUIDs are preserved, new entities receive explicit or
construction-established UUIDs under ADR-L-0029, and lifecycle and
relationship fields are supplied by construction. The caller separately
identifies the create and supersede mutations. Promotion never infers
supersession from prose. This flow remains unavailable until canonical
construction can qualify the complete multi-root normalized result.

The initial persistence scope is complete qualified authoring_document
roots only. Standalone fragments remain detached, reference-only artifacts
are dependencies without writes, and embedded child artifacts are covered
through their document root. Every mutable root is accounted for; duplicate
or conflicting destinations, identities, or aliases fail closed. No
implicit patch, delete, rename, secondary write, or preparation-time
semantic rewrite is authorized.

The baseline is an exact expected repository revision and a declared
protected authority scope. The initial operating model assumes a single
governance writer from final verification through apply, regeneration,
validation, and recovery. The provider rechecks the baseline and target
pre-images at required points; stale state requires new preparation and
human review. Replacement may be sequential and recovery is bounded to
approved targets and verified pre-images. Neither global atomicity nor
filesystem compare-and-swap is claimed. Git operations remain external.

Human authorization covers the exact candidate bytes, qualification,
mutation set, repository baseline, and resolved destinations. Material
provider evidence is part of the existing Promotion Contract locked intent;
operational sidecars cannot redirect execution. Preparation and dry-run do
not change governed repository authority, aliases, allocator state, or Git
state. The handoff and recovery evidence do not create a parallel durable
intent authority. Accepted ADR sources remain architecture authority and
are versioned through external Git.

Before successful candidate-binding qualification and self-hosting
acceptance, implementation must conform to ADR-L-0032's minimal
non-overlapping root rule (including the known C05/C07 vectors) and prove
complete whole-result normalized semantic equivalence. These are
implementation qualification prerequisites, not reasons to weaken existing
authority or block this design ADR. Python and Node peer behavior must be
qualified before parity is advertised. The capability does not require
Runtime admission or ArchSplain.

Self-hosting acceptance requires a released ADR-Kit version containing the
qualified public construction and binding capabilities; explicit typed
intent; public validation and construction; independent candidate
verification; prepared PC; human review and lock; dry-run; authoritative
apply; regenerated and validated corpus; and external Git branch, commit,
and pull request. Evidence must establish candidate/payload/applied-byte
identity; UUID preservation; complete mutation accounting; no mutation
during construction, preparation, or dry-run; stale-state and conflict
rejection; payload, target, identity, and qualification tamper rejection;
explicit human authorization; bounded truthful recovery and execution
reporting; peer-host parity; and corpus freshness. ADR-Kit 0.12.1 does not
claim to implement or satisfy this flow. The proposed ADR itself remains
subject to human architectural review and acceptance.


---

*Generated from ADR-L-0033 by ADR Architecture Kit (projection v3)*