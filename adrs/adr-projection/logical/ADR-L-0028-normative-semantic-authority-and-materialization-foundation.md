<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 06f3bbeb8df199d7ecf884b4047aeea88419d202937c2ce41af6a79c7299c623
rendered_hash: 04a5e852e43848b1a06073c34d881af225bd8292d0156c463983237a674d1498
-->

# ADR-L-0028: Normative Semantic Authority and Exact Materialization Foundation

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0028  
**Authoring contract:** authoring v1.5  
**Created:** 2026-09-09  
**Authors:** erik.gallmann  
**Domains:** architecture, semantic-authority, materialization, schema-governance, cross-language  
**Tags:** adr-kit-0.11.0, semantic-design-lock-r1, normative-proposition, interpretation-closure, historical-materialization  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0028 |
| Status | accepted |
| Decisions | 12 |
| Invariants | 16 |


## Context

The approved ADR-Kit 0.11.0 semantic design lock (R1) requires repository-local
architectural authority before successor contracts or implementation are built.
The current authoring contract is schema v1.5 and does not yet provide a native
first-class NormativeProposition field. The promotion therefore records the
architectural meaning using decisions, invariants, boundaries, and explicit
deferrals that the current authoring contract supports.

The release must preserve the distinction between an accepted project ADR, its
exact semantic interpretation, a retained realized result, and downstream
binding or assessment. A successful parser or materializer cannot manufacture
competence, effectivity, applicability, or implementation conformance. A
shared execution boundary may realize the meaning, but its implementation is
subordinate to this authority and cannot redefine it.

This ADR promotes the bounded R1 foundation only. It does not itself amend a
successor schema, create a registry, allocate a materialization identity,
implement a fingerprint, add public SDK operations, or authorize release
packaging.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0207 | Promote R1 meaning into ADR-Kit authority while preserving responsibility-scoped ownership | — |
| DEC-0208 | Express R1 architectural meaning with supported decisions and invariants until successor authoring contracts exist | — |
| DEC-0209 | Treat NormativeProposition and Invariant as peer semantic types with no independent NP lifecycle | — |
| DEC-0210 | Use the closed force vocabulary and separate force, authority, effectivity, scope, applicability, and conformance | — |
| DEC-0211 | Make every meaning-affecting interpretation rule part of an exact semantic definition or retained input | — |
| DEC-0212 | Materialization is based on a complete sealed source basis with artifact-level contract qualification and persisted identity evidence | — |
| DEC-0213 | Keep immutable semantic definitions, exact whole-set qualification, lifecycle policy, fingerprints, and historical realization distinct | — |
| DEC-0214 | Evaluate existing attribution semantics against an explicitly pinned materialization and defer direct NP-target attribution | — |
| DEC-0215 | Require equivalent public host observations from one canonical execution boundary | — |
| DEC-0216 | Promote the specification project type as a backward-compatible general project-metadata capability for 0.11.0 | — |
| DEC-0217 | Record the STE-SPEC sequencing exception without claiming branch admission | — |
| DEC-0218 | Sequence successor contracts, implementation, Runtime integration, and release qualification after this authority promotion | — |

### DEC-0207 — Promote R1 meaning into ADR-Kit authority while preserving responsibility-scoped ownership

**Rationale**

ADR-Kit owns its authoring representation and canonical interpretation
boundary. STE-wide normative doctrine remains owned by accepted STE-SPEC
authority where assigned, Runtime owns retention and binding admission, and
competent reviewers own semantic materiality judgments. A successful
representation or interpretation operation cannot create any of those forms
of authority.

### DEC-0208 — Express R1 architectural meaning with supported decisions and invariants until successor authoring contracts exist

**Rationale**

The current repository contract does not support a normative_propositions
field. Adding an unsupported field or weakening validation would make the
promotion unverifiable. The contract-definition slice must later define the
native representation without treating this promotion as an executable
successor contract.

### DEC-0209 — Treat NormativeProposition and Invariant as peer semantic types with no independent NP lifecycle

**Rationale**

An NP is ADR-scoped intent with declaring authority, scope, and force. It is
not an independently governed record merely because a normalized common
envelope may contain lifecycle fields. Requirements remain a future distinct
semantic family and must not be absorbed into either peer type.

### DEC-0210 — Use the closed force vocabulary and separate force, authority, effectivity, scope, applicability, and conformance

**Rationale**

The permitted force values are MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY.
Force is one semantic value, not a positive operator combined with an
independently inferred polarity. Statement meaning, materiality, and
identity continuity require competent review; deterministic validation may
check structure but cannot certify natural-language equivalence.

### DEC-0211 — Make every meaning-affecting interpretation rule part of an exact semantic definition or retained input

**Rationale**

Source adapters, decoding, normalization, identity-map use, coverage rules,
and absence handling can change a materialized result even when an output
schema is unchanged. The initial semantic contract set therefore includes
architecture-interpretation 1.0 as a distinct semantic family alongside the
normalized and normative semantic families. Profiles select a set but do not
redefine it.

### DEC-0212 — Materialization is based on a complete sealed source basis with artifact-level contract qualification and persisted identity evidence

**Rationale**

A claimed revision alone does not prove which auxiliary inputs, source
contracts, or identity maps were interpreted. Successful detached
materialization must preserve the complete acquired basis, encountered
artifact-to-contract bindings, provider qualification, and any required
sealed identity map. It must not mint identity during read-time traversal.

### DEC-0213 — Keep immutable semantic definitions, exact whole-set qualification, lifecycle policy, fingerprints, and historical realization distinct

**Rationale**

A semantic definition and a current-use decision do not have the same
lifecycle. A set is qualified as a whole for each operation rather than by
inferred pairwise compatibility. Portable state fingerprints and complete
payload digests have explicit projections and do not replace source or
retained-result identity. Historical recovery verifies the retained result
and exposes mismatches instead of rewriting prior history.

### DEC-0214 — Evaluate existing attribution semantics against an explicitly pinned materialization and defer direct NP-target attribution

**Rationale**

Exact-history evaluation must not reopen mutable present-day ADR source.
The released evidence-attribution 1.5 and 1.6 target matrix remains
unchanged: a first-class NP representation does not silently become a new
attribution target, and existing Invariant enforcement semantics remain
intact.

### DEC-0215 — Require equivalent public host observations from one canonical execution boundary

**Rationale**

Python and TypeScript/Node are peer hosts for promoted capabilities. Parity
begins with equivalent raw source and exact semantic bases, including
parsing, diagnostics, coverage, and fingerprints. Public results remain
independent of compiler-internal types, private implementation objects, and
host-specific semantic defaults.

### DEC-0216 — Promote the specification project type as a backward-compatible general project-metadata capability for 0.11.0

**Rationale**

The future contract-definition and implementation slices must extend the
project-metadata capability for any project using the type. They must not
special-case STE-SPEC, reinterpret its branch state, or weaken validation.
This promotion records the requirement without changing the current enum or
claiming that the capability is implemented.

### DEC-0217 — Record the STE-SPEC sequencing exception without claiming branch admission

**Rationale**

The accumulated STE-SPEC semantic-rebaseline branch and its ADR-L-0044
artifact are qualified directional design evidence only. ADR-Kit may refine
concrete authoring and materialization mechanics, but it must not redefine
STE-wide normative force, authority, competence, effectivity, applicability,
epistemic boundaries, bounded outcomes, or the NP/Invariant peer distinction.
STE-SPEC remains untouched in this slice.

### DEC-0218 — Sequence successor contracts, implementation, Runtime integration, and release qualification after this authority promotion

**Rationale**

The contract-definition slice must define authoring 1.6, normalized 2.3,
normative-semantics 1.0, architecture-interpretation 1.0, materialization
envelopes, qualification records, canonicalization, and host evidence.
Implementation and Runtime work follows those contracts. No release or
package claim is created by this ADR alone.





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0208 | Representation, interpretation, materialization, and binding operations MUST NOT manufacture competence,… | MUST / design | manual |
| INV-0209 | A NormativeProposition MUST derive its authority from its competent, effective declaring ADR and MUST NOT acquire an… | MUST / design | manual |
| INV-0210 | Normative force MUST be exactly one of MUST, MUST NOT, SHOULD, SHOULD NOT, or MAY; implementations MUST NOT… | MUST / design | automated |
| INV-0211 | Mechanical validation MUST NOT infer an NP, certify semantic materiality, or assert meaning-preserving identity… | MUST / design | manual |
| INV-0212 | Normative force, authority, effectivity, scope, applicability, and conformance MUST remain distinct dimensions and… | MUST / design | manual |
| INV-0213 | Inclusion of an NP in a normalized or materialized model MUST NOT imply that the proposition governs a concrete context. | MUST / design | manual |
| INV-0214 | Every meaning-affecting interpretation rule and input MUST be covered by an exact semantic definition or retained… | MUST / design | automated |
| INV-0215 | Immutable semantic definitions and exact historical set identities MUST remain stable independently of lifecycle,… | MUST / design | automated |
| INV-0216 | A semantic contract set MUST contain one exact qualified member per participating family and MUST be qualified as a… | MUST / design | automated |
| INV-0217 | A successful detached materialization MUST retain the complete sealed source and auxiliary input basis actually… | MUST / design | automated |
| INV-0218 | Detached materialization MUST NOT allocate canonical identity during read-time interpretation; legacy identity… | MUST / design | automated |
| INV-0219 | Materialization MUST distinguish Materialized, Rejected, and Unavailable outcomes and MUST preserve unresolved,… | MUST / design | automated |
| INV-0220 | Portable state fingerprints, complete semantic payload digests, source provenance, and retained realized results… | MUST / design | automated |
| INV-0221 | Exact-history evaluation of existing attribution semantics MUST consume the explicitly pinned materialization and… | MUST / design | automated |
| INV-0222 | Publicly advertised shared capabilities MUST have equivalent raw-source semantic, diagnostic, coverage, fingerprint,… | MUST / test | automated |
| INV-0223 | ADR-Kit promotion MUST NOT represent the STE-SPEC semantic-rebaseline feature branch as admitted upstream authority,… | MUST / design | manual |

### INV-0208

**Statement**

Representation, interpretation, materialization, and binding operations MUST NOT manufacture competence, effectivity, applicability, or implementation-conformance authority.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Authority remains responsibility-scoped across STE-SPEC, ADR-Kit, competent review, Runtime, and conformance authorities.

### INV-0209

**Statement**

A NormativeProposition MUST derive its authority from its competent, effective declaring ADR and MUST NOT acquire an independent governance lifecycle through a shared entity envelope.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

NP and Invariant are peer semantic types, while NP governance remains ADR-scoped.

### INV-0210

**Statement**

Normative force MUST be exactly one of MUST, MUST NOT, SHOULD, SHOULD NOT, or MAY; implementations MUST NOT reconstruct force from positive force plus an independent polarity.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Closed force values prevent double-negation and modal reinterpretation drift.

### INV-0211

**Statement**

Mechanical validation MUST NOT infer an NP, certify semantic materiality, or assert meaning-preserving identity continuity from arbitrary modal or imperative prose.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Semantic materiality and equivalence are competent review responsibilities.

### INV-0212

**Statement**

Normative force, authority, effectivity, scope, applicability, and conformance MUST remain distinct dimensions and MUST NOT be substituted for one another.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

A represented proposition is not thereby governing, applicable, or conformant.

### INV-0213

**Statement**

Inclusion of an NP in a normalized or materialized model MUST NOT imply that the proposition governs a concrete context.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

Applicability requires its own qualified context and authority basis.

### INV-0214

**Statement**

Every meaning-affecting interpretation rule and input MUST be covered by an exact semantic definition or retained explicit source/request input; a profile MUST NOT redefine an identified semantic contract set.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Host defaults, mutable profiles, and undocumented adapters cannot be hidden semantic authorities.

### INV-0215

**Statement**

Immutable semantic definitions and exact historical set identities MUST remain stable independently of lifecycle, deprecation, compatibility, and current new-use policy.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

A later prohibition on new use must not erase historical addressability or alter semantic identity.

### INV-0216

**Statement**

A semantic contract set MUST contain one exact qualified member per participating family and MUST be qualified as a whole for each supported operation; duplicate, missing, or conflicting members MUST fail closed.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Pairwise compatibility, transitivity, or symmetry cannot qualify an undeclared combination.

### INV-0217

**Statement**

A successful detached materialization MUST retain the complete sealed source and auxiliary input basis actually interpreted, including artifact-level source-contract qualification and required provider identity evidence.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

A revision label alone cannot prove complete acquisition or source-contract meaning.

### INV-0218

**Statement**

Detached materialization MUST NOT allocate canonical identity during read-time interpretation; legacy identity requires an exact sealed provider-authoritative map or a typed qualification failure.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Repeated reads must not remint or repair authority-owned identity.

### INV-0219

**Statement**

Materialization MUST distinguish Materialized, Rejected, and Unavailable outcomes and MUST preserve unresolved, undeclared, inexpressible, unavailable, and unassessed states without success-shaped fallback.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Invalid or incomplete acquisition cannot masquerade as an empty or partial authority model.

### INV-0220

**Statement**

Portable state fingerprints, complete semantic payload digests, source provenance, and retained realized results MUST use explicit projections and MUST NOT replace one another or rewrite historical records.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Contract conformance and reproduction of a prior executable result are distinct claims.

### INV-0221

**Statement**

Exact-history evaluation of existing attribution semantics MUST consume the explicitly pinned materialization and MUST NOT silently reopen current ADR source; direct NP-target attribution remains unsupported under released evidence contracts.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Pinned history and released attribution target semantics remain separate authority boundaries.

### INV-0222

**Statement**

Publicly advertised shared capabilities MUST have equivalent raw-source semantic, diagnostic, coverage, fingerprint, and installed-package qualification evidence in both peer host distributions.

**Scope:** global

**Enforcement:** MUST (test)
**Verification:** automated

**Rationale**

Source-level similarity is not evidence of published Python/TypeScript parity.

### INV-0223

**Statement**

ADR-Kit promotion MUST NOT represent the STE-SPEC semantic-rebaseline feature branch as admitted upstream authority, redefine STE-wide normative doctrine, or modify STE-SPEC in this slice.

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

The sequencing exception preserves repository ownership and prevents an accepted marker on an unadmitted branch from becoming false authority.







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0027](ADR-L-0027-public-binding-construction-and-release-parity.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0004](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)

**References**
- [ADR-L-0013](ADR-L-0013-architecture-repository-boundary-and-normalized-semantic-model.md)
- [ADR-L-0019](ADR-L-0019-canonical-entity-identity.md)
- [ADR-PC-0002](../physical-component/ADR-PC-0002-schema-and-contract-validation.md)
- [ADR-PC-0004](../physical-component/ADR-PC-0004-repository-boundary-and-normalized-semantic-model.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0022](ADR-L-0022-universal-uuidv7-entity-identity.md)
- [ADR-L-0025](ADR-L-0025-topology-and-contract-succession-authority.md)
- [ADR-PC-0008](../physical-component/ADR-PC-0008-project-scope-resolution.md)
- [ADR-L-0026](ADR-L-0026-authoring-domain-contract-discovery-authority.md)
- [ADR-L-0027](ADR-L-0027-public-binding-construction-and-release-parity.md)





## Notes

Promotion evidence: .adr-kit/v11-design-journal/adr-kit-0.11.0-semantic-design-lock-approved.md
is the approved R1 design-state authority for this promotion. It is not an
executable contract, release certification, or substitute for accepted ADR
authority after this promotion. The accompanying R1 traceability matrix is
evidence only and does not create a second normative source.

The following remain explicitly deferred to later bounded slices: authoring
contract 1.6; normalized-model 2.3; normative-semantics 1.0;
architecture-interpretation 1.0 resources; architecture-materialization
envelopes; semantic contract registries and fingerprints; shared-core and
Python/Node operations; Runtime retention, recovery, binding admission, and
Snapshot behavior; direct NP-target attribution; general Requirements
semantics; and release packaging. project.type: specification is a general
future project-metadata capability, not a current schema change.

STE-SPEC exception: ADR-L-0044 at feature commit
e21b8409f09d01be419db09d979ce924a92e3777 is retained only as qualified
directional evidence. Its feature-branch status does not mean admission to
STE-SPEC develop. CE-01 promotion is not a prerequisite for this ADR-Kit
promotion, and ADR-Kit does not modify STE-SPEC here.


---

*Generated from ADR-L-0028 by ADR Architecture Kit (projection v3)*