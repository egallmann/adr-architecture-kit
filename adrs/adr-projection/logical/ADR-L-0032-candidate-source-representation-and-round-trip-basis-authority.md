<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 8b2fbc27d712fb86a0a19aa8cc6b54a9958e553acdb0631f1c37c56c5b7da7f5
rendered_hash: 4ea7dbb9366d7faf2dc5758eb5506122713cd3af1aac956e5161383b17b36a0c
-->

# ADR-L-0032: Candidate Source Representation and Round-Trip Basis Authority

## Identity / Status

**Type:** logical<br>
**Status:** accepted<br>
**Alias:** ADR-L-0032<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-09-23<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, authoring, semantic-authority, schema-governance, determinism, consumer-bindings<br>
**Tags:** candidate-source, authoring-1.7, exact-source-basis, round-trip-equivalence, rust-authority, deterministic-serialization, detached-construction<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0032 |
| Status | accepted |
| Decisions | 12 |
| Invariants | 19 |


## Context

ADR-L-0029 established detached semantic construction and made a
schema-governed Semantic Fragment the primitive construction unit.
ADR-L-0030 established the Exact Source Basis and the canonical semantic
execution surface, and ADR-L-0031 established non-recursive conformance
qualification. Authoring Domain Contract 1.1, Custom Entity Contract 1.0,
Authoring Construction Contract 1.0, authoring 1.7,
architecture-interpretation 1.1, normalized-model 2.4, and semantic-core
protocol 1.2 now provide the accepted successor boundary that a successful
construction must cross.

One design boundary remains open: how detached candidate semantic state is
represented as exact authoring source, how each source is qualified, and how
only the minimal non-overlapping source roots are fed back through the
existing canonical interpreter. Without that boundary, a Constructed result
cannot prove source integrity or semantic round-trip equivalence without
making host rendering, repository placement, or a second interpreter
authoritative.

This ADR promotes that representation and round-trip authority only. It does
not implement construction, semantic-core protocol 1.2 execution, public
Python or Node APIs, persistence, repository admission, governance
promotion, Runtime admission, alias reservation, or Git mutation.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0249 | Define candidate artifacts as detached authoring 1.7 document or fragment sources | — |
| DEC-0250 | Require every candidate source artifact to carry an exact authoring 1.7 schema selector | — |
| DEC-0251 | Make the canonical Rust semantic execution path own candidate source bytes | — |
| DEC-0252 | Define adr-kit.authoring-yaml/v1 as the language-neutral candidate serialization profile | — |
| DEC-0253 | Make candidate scalar spelling deterministic and safe from YAML implicit typing | — |
| DEC-0254 | Distinguish all returned candidate artifacts from minimal source-basis roots | — |
| DEC-0255 | Define candidate source references as detached logical identities | — |
| DEC-0256 | Define candidate content_digest as SHA-256 over exact returned source bytes | — |
| DEC-0257 | Define adr-kit.candidate-source-basis/v1 as the source-basis fingerprint domain | — |
| DEC-0258 | Route the constructed source basis through the existing authoring interpretation surface | — |
| DEC-0259 | Permit Constructed only after exact source qualification and normalized semantic equivalence | — |
| DEC-0260 | Record implementation consequences without amending ACC contracts or vectors in this promotion | — |

### DEC-0249 — Define candidate artifacts as detached authoring 1.7 document or fragment sources

**Rationale**

A successful construction may return candidate artifacts of exactly two
source kinds: authoring_document and authoring_fragment. An
authoring_document is a complete authoring 1.7 ADR source object. An
authoring_fragment is a standalone schema-governed authoring 1.7 semantic
fragment. A standalone fragment remains primitive and MUST NOT be wrapped
in a synthetic ADR merely to obtain source bytes. ADR synthesis is
composition over fragments and does not replace fragment identity.

### DEC-0250 — Require every candidate source artifact to carry an exact authoring 1.7 schema selector

**Rationale**

Every candidate artifact used as source authority carries a selector with
this exact shape:

  source_schema:
    canonical_resource_key: <exact authoring 1.7 schema resource key>
    json_pointer: <exact JSON pointer within that resource>

A decision fragment may select authoring/1.7/schema/adr-common.schema at
/definitions/decision. A logical ADR document may select
authoring/1.7/schema/adr-logical.schema at the empty JSON pointer, which
denotes the schema root. The selector is retained source-basis evidence
and is never inferred from path, filename, alias, request key, source
order, current or latest schema, host defaults, or UI state.

### DEC-0251 — Make the canonical Rust semantic execution path own candidate source bytes

**Rationale**

ADR-Kit calculates and returns the exact candidate source bytes through the
canonical Rust semantic execution path. Python and TypeScript/Node remain
peer host adapters and MUST NOT independently render candidate source
bytes. A host may preview or persist the exact returned bytes, but it may
not reinterpret, normalize, or reserialize them as shared semantic
authority.

### DEC-0252 — Define adr-kit.authoring-yaml/v1 as the language-neutral candidate serialization profile

**Rationale**

The profile fixes UTF-8 without a BOM, LF line endings, exactly one
terminal LF, two-space indentation, block-style mappings and sequences,
no YAML document marker, no directives, no comments, no anchors, no
aliases, no custom tags, and no terminal-width or host-formatting
dependency. Schema-governed object fields follow the exact property order
declared by the governing authoring 1.7 schema resource. Absent optional
fields are omitted, authorized open property maps use deterministic lexical
key order, and arrays retain their semantic order. Libraries may implement
this profile, but no library's incidental output defines it.

### DEC-0253 — Make candidate scalar spelling deterministic and safe from YAML implicit typing

**Rationale**

String scalars and mapping keys use one deterministic JSON-compatible
double-quoted YAML representation with UTF-8 characters preserved and
quote, backslash, and control characters escaped canonically. Boolean
scalars use only true or false. Null uses only null. Integers use base-ten
spelling with no plus sign or leading zero except zero. Other finite
numbers use the canonical JSON number lexical form; NaN and infinity are
not representable. These rules are part of the profile and are not
delegated to a host library.

### DEC-0254 — Distinguish all returned candidate artifacts from minimal source-basis roots

**Rationale**

candidate_artifacts contains the detached artifacts produced for the
requested fragments and compositions. candidate_source_basis.artifacts
contains the minimal non-overlapping source roots that canonical
interpretation consumes. If a synthesized authoring_document already
represents an embedded fragment, that child is excluded from the source
basis while remaining a candidate artifact. A standalone fragment not
represented in another source root remains independently present. This
prevents duplicate declaration without changing fragment identity.

### DEC-0255 — Define candidate source references as detached logical identities

**Rationale**

Each candidate source_ref is a deterministic logical reference for the
detached result. It does not allocate a repository path, choose a
filename, reserve an alias, imply Git placement, or imply persistence.
Exact candidate bytes are independent of repository location. A source_ref
identifies the candidate source for result comparison and basis sealing,
not a future storage location.

### DEC-0256 — Define candidate content_digest as SHA-256 over exact returned source bytes

**Rationale**

For every candidate artifact, content_digest is sha256 over the exact
candidate source bytes returned under adr-kit.authoring-yaml/v1. ADR-Kit
calculates this digest. A caller-provided digest is an assertion to be
checked, not authority, and cannot replace the digest calculated from the
exact bytes.

### DEC-0257 — Define adr-kit.candidate-source-basis/v1 as the source-basis fingerprint domain

**Rationale**

basis_digest is SHA-256 over UTF-8 canonical semantic JSON of a
domain-separated descriptor whose domain is
adr-kit.candidate-source-basis/v1 and whose artifacts are ordered by
source_ref. Each descriptor entry contains request_key, source_ref,
artifact_kind, exact source_schema selector, serialization_profile,
content_digest, and exact source_contract qualification. Raw source bytes
need not be repeated because content_digest commits to those bytes. A
change to retained bytes, source schema, serialization profile, source
contract, request key, or source identity changes basis_digest.

### DEC-0258 — Route the constructed source basis through the existing authoring interpretation surface

**Rationale**

The success path is explicit typed construction intent, candidate semantic
state, canonical Rust candidate serialization, sealed candidate Exact
Source Basis, exact target authoring 1.7 validation,
architecture-interpretation 1.1, normalized-model 2.4, and semantic
equivalence comparison. Architecture-interpretation remains the forward
interpreter. Construction orchestrates that path but does not define a
construction-specific semantic interpreter or clone its mappings.

### DEC-0259 — Permit Constructed only after exact source qualification and normalized semantic equivalence

**Rationale**

Constructed is permitted only when pre-construction validation and
candidate construction succeed, exact source bytes and schema
qualification exist, the candidate source basis is sealed, target
authoring 1.7 validation succeeds, architecture-interpretation 1.1 is
available and succeeds, normalized-model 2.4 is produced, and semantic
equivalence succeeds. The comparison is semantic normalized equivalence,
not byte equality; deterministic bytes provide integrity and parity while
ACC round-trip rules continue to govern authorized representation
differences.

### DEC-0260 — Record implementation consequences without amending ACC contracts or vectors in this promotion

**Rationale**

The subsequent implementation and contract slice must add the exact
source_schema selector and serialization profile to ACC candidate_artifact,
define the candidate_source_basis.basis_digest preimage, replace
Constructed vector placeholder bytes such as eA== with canonical rendered
bytes, and correct C05 and C07 to use minimal non-overlapping source roots.
C32 remains the semantic-mismatch oracle and C33 remains the
architecture-interpretation-unavailable oracle. This ADR records those
consequences only; it does not modify ACC schemas, resources, or vectors.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0249 | A successful construction MUST return candidate artifacts only as authoring_document or authoring_fragment sources… | MUST / design | automated |
| INV-0250 | A standalone authoring_fragment MUST NOT be wrapped in a synthetic ADR solely to obtain source bytes, and… | MUST / design | manual |
| INV-0251 | Every candidate source artifact used as source authority MUST carry an exact canonical_resource_key and json_pointer… | MUST / design | automated |
| INV-0252 | Source schema selection MUST NOT be inferred from repository path, filename, alias, request_key, source order,… | MUST / design | automated |
| INV-0253 | The canonical Rust semantic execution path MUST own exact candidate source bytes, and Python and TypeScript/Node… | MUST / design | manual |
| INV-0254 | adr-kit.authoring-yaml/v1 MUST use UTF-8 without BOM, LF endings, exactly one terminal LF, two-space indentation,… | MUST / design | automated |
| INV-0255 | Schema-governed mappings MUST follow governing schema property order, absent optional fields MUST be omitted,… | MUST / design | automated |
| INV-0256 | Candidate string, boolean, null, integer, and finite numeric scalars MUST use the single host-neutral lexical… | MUST / design | automated |
| INV-0257 | A host MAY preview or persist exact returned candidate bytes but MUST NOT reinterpret or reserialize them as shared… | MUST / design | manual |
| INV-0258 | A candidate source_ref MUST remain a deterministic logical candidate identity and MUST NOT allocate a repository… | MUST / design | manual |
| INV-0259 | Every candidate artifact content_digest MUST equal SHA-256 of its exact returned source bytes, and caller-provided… | MUST / design | automated |
| INV-0260 | basis_digest MUST equal SHA-256 over canonical semantic JSON of the adr-kit.candidate-source-basis/v1 descriptor… | MUST / design | automated |
| INV-0261 | Candidate source-basis artifacts MUST be ordered deterministically by source_ref before basis_digest calculation. | MUST / design | automated |
| INV-0262 | candidate_source_basis.artifacts MUST contain only minimal non-overlapping source roots; a child fragment already… | MUST / design | automated |
| INV-0263 | Excluding an embedded child from candidate_source_basis MUST NOT create, replace, derive, or otherwise alter that… | MUST / design | automated |
| INV-0264 | Constructed MUST require successful pre-construction validation, construction, exact bytes, exact schema… | MUST / design | automated |
| INV-0265 | Candidate Exact Source Basis MUST feed the canonical architecture-interpretation 1.1 execution surface, and… | MUST / design | manual |
| INV-0266 | Round-trip success MUST compare normalized semantic equivalence under ACC rules and MUST NOT elevate YAML… | MUST / design | automated |
| INV-0267 | If any required construction or round-trip gate fails, the result MUST remain Rejected, Unavailable, or Unresolved… | MUST / design | manual |

### INV-0249

**Statement**

A successful construction MUST return candidate artifacts only as authoring_document or authoring_fragment sources qualified by authoring 1.7.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

A closed source-kind set prevents an unqualified representation from becoming round-trip authority.

### INV-0250

**Statement**

A standalone authoring_fragment MUST NOT be wrapped in a synthetic ADR solely to obtain source bytes, and composition MUST NOT replace the fragment's identity.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

ADR synthesis is composition over independently meaningful semantic fragments.

### INV-0251

**Statement**

Every candidate source artifact used as source authority MUST carry an exact canonical_resource_key and json_pointer selector for an authoring 1.7 schema resource.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Exact qualification prevents a source from changing meaning through ambient schema selection.

### INV-0252

**Statement**

Source schema selection MUST NOT be inferred from repository path, filename, alias, request_key, source order, current or latest schema, host defaults, or UI state.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Schema identity is retained evidence rather than an environmental guess.

### INV-0253

**Statement**

The canonical Rust semantic execution path MUST own exact candidate source bytes, and Python and TypeScript/Node MUST NOT independently render shared candidate source authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

One renderer preserves cross-host source integrity and semantic parity.

### INV-0254

**Statement**

adr-kit.authoring-yaml/v1 MUST use UTF-8 without BOM, LF endings, exactly one terminal LF, two-space indentation, block style, no marker, directives, comments, anchors, aliases, or custom tags, and no host-formatting dependency.

**Scope:** serialization

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Exact profile rules make candidate bytes reproducible without naming an implementation library.

### INV-0255

**Statement**

Schema-governed mappings MUST follow governing schema property order, absent optional fields MUST be omitted, authorized open maps MUST use lexical key order, and serialization MUST NOT reorder arrays.

**Scope:** serialization

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Ordering is deterministic while preserving declared semantic sequence.

### INV-0256

**Statement**

Candidate string, boolean, null, integer, and finite numeric scalars MUST use the single host-neutral lexical representation defined by adr-kit.authoring-yaml/v1, and implicit YAML typing MUST NOT change their meaning.

**Scope:** serialization

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Scalar spelling is part of exact source integrity and cannot vary by library defaults.

### INV-0257

**Statement**

A host MAY preview or persist exact returned candidate bytes but MUST NOT reinterpret or reserialize them as shared semantic authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Host convenience must not create a second source representation.

### INV-0258

**Statement**

A candidate source_ref MUST remain a deterministic logical candidate identity and MUST NOT allocate a repository path, filename, alias, Git placement, or persistence location.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Repository placement is a later host and governance responsibility.

### INV-0259

**Statement**

Every candidate artifact content_digest MUST equal SHA-256 of its exact returned source bytes, and caller-provided digests MUST NOT be authoritative.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

The digest is an integrity commitment to the exact canonical source.

### INV-0260

**Statement**

basis_digest MUST equal SHA-256 over canonical semantic JSON of the adr-kit.candidate-source-basis/v1 descriptor containing every retained artifact's request_key, source_ref, artifact_kind, exact source_schema, serialization_profile, content_digest, and exact source_contract qualification.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

An explicit domain-separated preimage prevents accidental omission of authority-bearing evidence.

### INV-0261

**Statement**

Candidate source-basis artifacts MUST be ordered deterministically by source_ref before basis_digest calculation.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Equivalent detached source bases must produce the same fingerprint independent of request traversal order.

### INV-0262

**Statement**

candidate_source_basis.artifacts MUST contain only minimal non-overlapping source roots; a child fragment already represented in a synthesized authoring_document MUST NOT also be supplied independently.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Duplicate declaration would require an authority not established by this ADR.

### INV-0263

**Statement**

Excluding an embedded child from candidate_source_basis MUST NOT create, replace, derive, or otherwise alter that fragment's canonical UUID identity.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Source-root minimization is a basis operation, not an identity operation.

### INV-0264

**Statement**

Constructed MUST require successful pre-construction validation, construction, exact bytes, exact schema qualification, sealed source basis, target authoring 1.7 validation, available and successful architecture-interpretation 1.1, normalized-model 2.4 output, and semantic equivalence.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

No individual local success can substitute for complete round-trip evidence.

### INV-0265

**Statement**

Candidate Exact Source Basis MUST feed the canonical architecture-interpretation 1.1 execution surface, and construction MUST NOT introduce a second semantic interpreter or clone semantic mappings.

**Scope:** semantic-authority

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Forward semantic authority remains centralized under ADR-L-0030.

### INV-0266

**Statement**

Round-trip success MUST compare normalized semantic equivalence under ACC rules and MUST NOT elevate YAML presentation equality to architectural semantics beyond exact-source integrity and deterministic rendering.

**Scope:** construction

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Canonical bytes provide reproducible source evidence while authorized semantic representation differences remain valid.

### INV-0267

**Statement**

If any required construction or round-trip gate fails, the result MUST remain Rejected, Unavailable, or Unresolved as applicable; partial success MUST NOT be introduced, and this authority MUST NOT create persistence, admission, alias, Git, Runtime, or implementation-conformance capability.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

The design closes source authority without moving responsibility to construction.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)

**References**
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0029](ADR-L-0029-semantic-authoring-construction-and-candidate-authority.md)
- [ADR-L-0030](ADR-L-0030-canonical-source-basis-and-semantic-execution-surface.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)





## Notes

The subsequent implementation and contract slice must amend the Authoring
Construction Contract 1.0 candidate_artifact shape with source_schema and
serialization_profile, and must define candidate_source_basis.basis_digest
using the explicit adr-kit.candidate-source-basis/v1 descriptor above.
Existing Constructed conformance vectors that use placeholder bytes eA==
cannot remain executable success evidence once rendering exists. Composition
vectors such as C05 and C07, which currently repeat both synthesized ADR
documents and their child fragments in candidate_source_basis, must be
corrected to the minimal non-overlapping source-root rule. C32 remains the semantic round-trip-mismatch negative
oracle, and C33 remains the architecture-interpretation-unavailable oracle.

This ADR does not modify those contracts or vectors. It does not add
construction execution, semantic-core protocol 1.2 execution, public Python
or Node APIs, persistence, repository or Git writes, filename or path
allocation, alias reservation, governance or Runtime admission, Runtime
Snapshot mutation, or implementation-conformance claims. Exact source bytes
remain detached candidate evidence until a later authority separately admits
them.


---

*Generated from ADR-L-0032 by ADR Architecture Kit (projection v3)*