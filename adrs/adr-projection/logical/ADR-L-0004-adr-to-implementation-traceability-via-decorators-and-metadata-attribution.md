<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: db3bf83efccbfc2d45e8671735eeae9bb870e7a36c2e7cb4a45d180236547780
rendered_hash: c5bdfbc7153bd4a2e1acc640cb66db2dcc2d2e18fd6c68339fc229c66d3b19e1
-->

# ADR-L-0004: ADR-to-Implementation Traceability via Decorators and Metadata Attribution

## Identity / Status

**Type:** logical  
**Status:** accepted  
**Alias:** ADR-L-0004  
**Authoring contract:** authoring v1.5  
**Created:** 2026-03-08  
**Modified:** 2026-08-20  
**Authors:** adr-architecture-kit  
**Domains:** architecture, traceability, governance, verification  
**Tags:** traceability, decorators, verification, drift-detection, embodied-design  

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0004 |
| Status | accepted |
| Decisions | 6 |
| Capabilities | 4 |
| Invariants | 6 |
| Physical realizations | [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md) |


## Context

Architecture Decision Records document why implementation artifacts exist, but
the repo still lacks a universal, machine-verifiable way to trace code,
infrastructure, configuration, schemas, pipelines, and scripts back to the
ADRs that justify them.

Earlier design work in this ADR established decorator-based code traceability,
RECON extraction, and bidirectional verification as the right direction.
Since then, adr-architecture-kit has gained an explicit compiler pipeline,
profile-aware contract validation, and stronger governance around derived
architecture state. The traceability design now needs to be widened and
grounded in that current compiler/governance reality.

## Current State

- ADRs reference implementation via `implementation_identifiers`
- Code and infrastructure still lack a canonical reverse link to ADRs
- adr-architecture-kit owns canonical architecture authority, but not source
  extraction of implementation artifacts
- ste-runtime / RECON now extracts decorator metadata into implementation
  attribution evidence records for code paths it can parse
- Existing governance already distinguishes `greenfield`, `brownfield`, and
  `migration`, which should govern legacy onboarding instead of inventing a
  separate transition model

## Architecture Direction

This repository remains the authority for:
- the attribution rule itself
- the canonical decorator and metadata semantics
- the compiler-owned evidence contract that downstream extractors populate
- the validation posture for greenfield, brownfield, and migration use

This repository does not take on source-code parsing for this feature in the
current slice. That remains downstream work for ste-runtime / RECON.

## Problems Solved

1. **Orphaned implementation**: Artifacts exist with no architectural justification
2. **Incomplete implementation**: ADRs declare architecture that is not traced to implementation
3. **Drift**: Implementation evolves without architecture authority remaining explicit
4. **Legacy imports**: Existing codebases need staged onboarding without losing deterministic governance
5. **AI reasoning**: Agents need an explicit intent surface rather than heuristic code-to-ADR guesses
6. **EDR evidence**: Embodied decision records need provenance-rich implementation claims

## STE Principles

- **PRIME-1**: No implicit assumptions (implementation must declare its authority)
- **SYS-4**: Drift prevention (detect when code diverges from ADRs)
- **SYS-5**: Documentation-state as authoritative (ADRs govern code)
- **SYS-6**: RECON completion (architecture must be extractable)
- **Scope-aware onboarding**: Migration posture must be explicit rather than ad hoc
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-0009 | Adopt explicit architecture intent attribution for implementation artifacts | — |
| DEC-0016 | Stage downstream extraction and rule activation after ADR-Kit authority is defined | — |
| DEC-0076 | Treat runtime-emitted implementation attribution as downstream evidence | — |
| DEC-0023 | Support Bidirectional Verification | — |
| DEC-0048 | Define a compiler-owned implementation attribution evidence contract | — |
| DEC-0049 | Use existing contract profiles for legacy intent-attribution onboarding | — |

### DEC-0009 — Adopt explicit architecture intent attribution for implementation artifacts

**Rationale**

Implementation surfaces need explicit, extractable architecture authority.
For code, decorators remain the canonical mechanism:
- `@implements_adr(...)`
- `@enforces_invariant(...)`
- `@implements(...)` / `@enforces(...)` / `@embodies(...)` for UUID-canonical semantic claims (ADR-L-0020)

For infrastructure and adjacent non-code artifacts, the same intent is
expressed through metadata-level declarations rather than per-resource
decoration.

This keeps attribution explicit while respecting artifact-type differences.

**Consequences**

Positive:
- New implementation can declare architectural authority deterministically
- Code and infrastructure use a consistent intent model
- Downstream extraction can remain language-specific without changing rule semantics
- AI reasoning gains explicit implementation-to-ADR provenance

### DEC-0016 — Stage downstream extraction and rule activation after ADR-Kit authority is defined

**Rationale**

adr-architecture-kit should first define the canonical rule, evidence
contract, and profile-aware validation semantics. Source extraction,
runtime rule activation, and any shared ecosystem delivery should build on
that authority rather than forcing this repo to duplicate downstream logic.

**Consequences**

Positive:
- adr-architecture-kit remains the source of canonical architecture semantics
- ste-runtime can focus on extraction rather than architecture authority
- ste-rules-library can encode activation logic later without redefining the rule
- ste-spec only needs involvement if the evidence contract must become shared doctrine

### DEC-0076 — Treat runtime-emitted implementation attribution as downstream evidence

**Rationale**

ste-runtime now populates implementation attribution evidence from parsed
implementation artifacts. That closes the first downstream extraction gap
without moving attribution authority into ste-runtime. adr-architecture-kit
remains responsible for canonical decorator and metadata semantics, the
evidence contract shape, and profile-aware validation against canonical ADR
state.

**Consequences**

Positive:
- RECON can supply extracted attribution claims for validation
- ADR-Kit validates raw attribution evidence against canonical ADR authoring state and exposes a non-authoritative linkage projection without writing Architecture IR
- Runtime extraction can evolve by language without redefining attribution semantics

### DEC-0023 — Support Bidirectional Verification

**Rationale**

Traceability must work in both directions:

**Forward (ADR -> Implementation)**:
- ADR declares component or system implementation identifiers
- Verify that downstream attribution evidence resolves to the declared authority

**Reverse (Implementation -> ADR)**:
- Code has `@implements_adr` or equivalent metadata-level attribution
- Verify that referenced ADR exists and is still a valid authority target

This bidirectional verification detects:
- Orphaned implementation (no ADR)
- Phantom declarations (ADR but no implementation evidence)
- Invalid references (implementation references non-existent ADR)
- Status mismatches (implementation references superseded ADRs)

**Consequences**

Positive:
- Verification must check both directions
- Downstream extraction must preserve both ADR declarations and implementation attribution claims
- Drift detection becomes comprehensive
- CI/CD can enforce traceability

### DEC-0048 — Define a compiler-owned implementation attribution evidence contract

**Rationale**

adr-architecture-kit needs a canonical handoff surface for implementation
attribution evidence without taking on source parsing itself. A small,
compiler-owned schema and model let downstream extractors emit consistent
attribution records that governance can validate deterministically.

**Consequences**

Positive:
- ste-runtime / RECON has a canonical handoff contract to populate
- Governance can validate implementation attribution without parsing source code here
- EDR and coverage work can build on a stable evidence shape

### DEC-0049 — Use existing contract profiles for legacy intent-attribution onboarding

**Rationale**

Greenfield, brownfield, and migration already express the repo's adoption
postures. Intent attribution onboarding should use those same profiles
rather than creating a second transition taxonomy.

**Consequences**

Positive:
- Legacy onboarding remains aligned with existing governance
- Greenfield enforcement can be strict without blocking brownfield imports
- Migration tightening can happen without schema forks or one-off modes


## Capabilities

### CAP-0021 — Architecture Intent Attribution

Explicit declaration of architectural authority across code and other
implementation artifacts through decorators or metadata-level attribution.

**Acceptance criteria**
- @implements_adr(adr_id, ...) decorator available
- @enforces_invariant(inv_id, ...) decorator available
- @implements / @enforces / @embodies UUID claim decorators available
- infrastructure/config/schema/pipeline/script artifacts can declare ADR IDs through metadata
- attribution metadata does not alter runtime behavior
- attribution is extractable by downstream tooling

### CAP-0024 — Bidirectional Traceability Verification

Automated verification that implementation attribution and ADR declarations
agree in both directions.

**Acceptance criteria**
- Query validated implementation-to-intent links in both directions
- Preserve independent evidence occurrences behind each unique semantic linkage
- Verify attribution references valid architecture UUIDs
- Detect orphaned implementation (no ADR reference)
- Detect phantom declarations (ADR but no implementation evidence)
- Report traceability violations

### CAP-0027 — Profile-Aware Legacy Onboarding for Intent Attribution

Govern intent-attribution adoption with the existing greenfield,
brownfield, and migration profiles instead of a separate legacy mode.

**Acceptance criteria**
- greenfield treats missing required attribution as an error
- brownfield and migration can surface onboarding gaps as warnings
- missing ADR references still fail regardless of profile
- superseded ADR references are visible without blocking onboarding

### CAP-0030 — Implementation Attribution Evidence Handoff

A compiler-owned evidence contract that downstream extractors populate with
implementation-to-ADR attribution claims and provenance.

**Acceptance criteria**
- evidence records include implementation entity ID and type
- evidence records include typed relationship claims to canonical architecture UUIDs
- evidence records preserve source, extractor, commit, pointer, and optional line span
- optional invariant claims can be carried without schema forks
- ste-runtime can emit the contract without adr-architecture-kit parsing source code directly




## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0027 | Greenfield in-scope implementation artifacts MUST declare architectural authority through @implements_adr, a UUID… | MUST / design | automated |
| INV-0028 | Implementation attribution references MUST resolve to existing ADRs, and references to superseded ADRs MUST be… | MUST / design | automated |
| INV-0029 | Implementation attribution evidence MUST preserve provenance identifying the source artifact and extractor… | MUST / design | automated |
| INV-0030 | A declaration that code enforces an invariant is a claim of intent, not kit-automated proof that the enforcement… | MUST / design | manual |
| INV-0031 | adr-architecture-kit MUST define the canonical architecture-intent attribution rule and evidence contract without… | MUST / design | automated |
| INV-0032 | Downstream extractors and rule-delivery systems SHOULD consume ADR-Kit attribution contracts rather than redefining… | SHOULD / design | automated |

### INV-0027

**Statement**

Greenfield in-scope implementation artifacts MUST declare architectural
authority through @implements_adr, a UUID semantic claim decorator, or an
equivalent metadata-level attribution mechanism; equivalent semantic
declarations MUST NOT be dual-encoded on the same surface; brownfield and
migration may stage adoption under profile-specific governance

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Explicit architecture intent is mandatory for new systems, but legacy
onboarding must be staged through the existing profile model.

### INV-0028

**Statement**

Implementation attribution references MUST resolve to existing ADRs, and
references to superseded ADRs MUST be surfaced as governance warnings

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Invalid or stale authority references undermine machine traceability even
when the attribution syntax itself is present.

### INV-0029

**Statement**

Implementation attribution evidence MUST preserve provenance identifying
the source artifact and extractor responsible for the claim

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Traceability without provenance is not auditable enough for EDR evidence,
drift analysis, or trustworthy agent reasoning.

### INV-0030

**Statement**

A declaration that code enforces an invariant is a claim of intent,
not kit-automated proof that the enforcement logic exists

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** manual

**Rationale**

adr-architecture-kit does not parse implementation source to prove
enforcement. Downstream extractors and human review may pursue proof;
the kit validates that the declared target exists and is an invariant.

### INV-0031

**Statement**

adr-architecture-kit MUST define the canonical architecture-intent
attribution rule and evidence contract without taking on direct source-code
parsing responsibilities for downstream repositories

**Scope:** global

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

This repository owns architecture authority, while downstream extractors own
language-specific parsing and evidence emission.

### INV-0032

**Statement**

Downstream extractors and rule-delivery systems SHOULD consume ADR-Kit
attribution contracts rather than redefining them independently

**Scope:** global

**Enforcement:** SHOULD (design)
**Verification:** automated

**Rationale**

Reusing a single contract preserves deterministic semantics across the
ecosystem even when extraction and rule activation live elsewhere.




## Physical Realization

**Components**
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)




## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)

**References**
- [ADR-L-0005](ADR-L-0005-adr-to-prompt-translation-for-ai-implementation.md)
- [ADR-L-0001](ADR-L-0001-ste-compliant-machine-verifiable-architecture-decision-record-system.md)
- [ADR-L-0003](ADR-L-0003-quality-assurance-and-testing-strategy.md)
- [ADR-L-0002](ADR-L-0002-multi-scope-adr-architecture-for-sub-module-development.md)
- [ADR-L-0012](ADR-L-0012-federation-authority-and-qualified-identity-model.md)
- [ADR-L-0010](ADR-L-0010-kernel-interface-contract-and-validation-profiles.md)
- [ADR-PC-0007](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md)
- [ADR-L-0020](ADR-L-0020-semantic-implementation-attribution-and-cross-layer-architecture-relationships.md)
- [ADR-L-0006](ADR-L-0006-rule-library-sub-module-with-cooperative-signals.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-PC-0007 — Semantic Attribution Embodiment](../physical-component/ADR-PC-0007-semantic-attribution-embodiment.md) | implements this logical authority | `ADR-PC-0007 -[:implements_logical]-> ADR-L-0004` |



## Known Gaps

### GAP-0001: Decorator library not yet implemented

**Context:** Classification: closed. adr_kit.decorators exists and is a Stable surface; UUID claim APIs are added under ADR-L-0020 / ADR-PC-0007.
**Impact:** low
**Blocking:** false

### GAP-0002: Downstream implementation attribution evidence requires broader extractor coverage

**Context:** Classification: narrowed gap. ste-runtime / RECON now emits architecture-intent attribution records for parsed decorator metadata, but coverage across all supported implementation artifact classes remains staged.
**Impact:** medium
**Blocking:** false

### GAP-0003: Legacy onboarding rollout for adr-architecture-kit itself is not yet started

**Context:** Classification: narrowed gap. Selective high-authority dogfood is in place; remaining surfaces stay in attribution-negative-space rather than whole-repo decoration.
**Impact:** low
**Blocking:** false

### GAP-0004: ste-rules-library activation for intent-attribution enforcement remains staged

**Context:** Classification: deferred gap. Downstream rule activation may be useful later, but it should consume ADR-Kit authority rather than redefine it.
**Impact:** medium
**Blocking:** false


## Notes

Implementation phases:

Phase 1: Decorator Library (ADR-PC-0007)
- Native adr_kit.decorators module is the Stable embodiment
- Legacy @implements_adr / @enforces_invariant remain metadata-only
- UUID @implements / @enforces / @embodies compose canonical claims

Phase 2: Evidence Contract + Validation
- v1.5 semantic attribution evidence is UUID-canonical (ADR-L-0020)
- Validate evidence against canonical ADR state with profile-aware onboarding semantics
- Keep attribution authority in ADR-Kit, not in downstream extractors
- Do not parse consumer source in this repository

Phase 3: Downstream Extraction (ste-runtime)
- Extract decorators / metadata from code and infrastructure artifacts
- Emit implementation attribution evidence with provenance and UUID targets
- Preserve provenance for EDR and drift analysis

Phase 4: Legacy Onboarding
- Selective high-authority annotation only
- Do not dual-encode equivalent legacy alias and UUID edges
- Use greenfield, brownfield, and migration profiles to control enforcement

Phase 5: Optional Rule Activation (ste-rules-library)
- Encode reusable rule activation only after the authority and evidence contracts are stable
- Keep downstream delivery additive rather than redefining semantics

UUID targets are canonical. Aliases are presentation and 1.0/1.2 translation input. A decorator declaration is evidence of intent, not proof. The governed stages are source declaration, validated embodiment linkage, and separately governed graph admission. ADR-Kit owns the first two contracts but the linkage projection remains derived evidence and never performs graph admission.


---

*Generated from ADR-L-0004 by ADR Architecture Kit (projection v3)*