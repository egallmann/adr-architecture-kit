<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 582c06bca453dd9b34b2cb0043d554ce6d4b0f0c0dedd3b2caa3bccb2aedf309
rendered_hash: dbb6180d6a6777d2b6cd3fa7db6101a2c85c50175e23573bd94569a6b9595d66
-->

# ADR-L-0042: Separate Release Versions from Semantic Capability Milestones

## Identity / Status

**Type:** logical<br>
**Status:** proposed<br>
**Alias:** ADR-L-0042<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-11-16<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, governance, release-engineering, semantic-authority<br>
**Tags:** release-scope, capability-milestone, forward-semantic-execution, v0.13<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0042 |
| Status | proposed |
| Decisions | 4 |
| Invariants | 4 |


## Context

Accepted ADR-L-0038 and ADR-L-0039 define a complete forward semantic execution
objective across 27 catalog types and their applicable branches. Their historical
prose calls this the v0.13 objective. ADR-L-0040 separately governs candidate
authority, package inventory, promotion and the compatibility obligations created
by promotion. These are distinct concerns: a repository release version identifies
a package and its evidence, while a semantic capability milestone describes an
independently qualified system outcome.

REL-3a rehearsal on develop 602480299e5a8ea146e985a9772f0f8d26f2eebf found 33
released and 12 candidate authority rows in the current built distributions. The
current promotion subject binds the complete packaged cohort. This supports
considering a lifecycle-governed consolidation release, but does not accept its
scope, select a distribution cohort, promote authority or establish any new
runtime capability. Those actions retain their separate owner and qualification
gates.

This ADR proposes a scope clarification only. It preserves the full 27-type
objective, its 455 destination rows and every existing BLOCKED obligation. It
does not amend AI 1.4/1.5 authority, including immutable v0_13_objective labels,
or change AI, ACC, NM, SCF, protocol, SCS, runtime or publication state.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-9035 | Govern package release versions independently from semantic capability milestones | Refines Account for every required destination across entity, relationship and value branches (DEC-9014), Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance (DEC-9015), Account for all 27 types while selecting only applicable entity destinations (DEC-9021), Require closed successor publication and independent instance verification (DEC-9022), Freeze exact snapshots; promote compatibility explicitly (DEC-9023), Consolidate governed candidate semantics in independently green checkpoints (DEC-9026) |
| DEC-9036 | Preserve the complete all-27 Forward Semantic Execution Completion milestone | Refines Account for every required destination across entity, relationship and value branches (DEC-9014), Account for all 27 types while selecting only applicable entity destinations (DEC-9021) |
| DEC-9037 | Propose v0.13.0 as a lifecycle-governed consolidation release subject to owner approval | Refines Inventory before bundle finalization; attest externally afterwards (DEC-9025), Consolidate governed candidate semantics in independently green checkpoints (DEC-9026), Keep proposed governance and future promotion independently gated (DEC-9028) |
| DEC-9038 | Preserve immutable historical objective labels and avoid future release-number coupling | Refines Freeze exact snapshots; promote compatibility explicitly (DEC-9023) |

### DEC-9035 — Govern package release versions independently from semantic capability milestones

**Rationale**

A release version MUST identify the released package cohort and its exact
qualification and promotion evidence. It MUST NOT, by itself, assert completion
of a semantic capability milestone. A release promises only capabilities
demonstrated by its released authority, public interfaces, and release evidence.
A milestone records a separately governed outcome and its explicit exit criteria;
its completion may span more than one repository release.

Refine ADR-L-0038's and ADR-L-0039's use of “v0.13 objective” as the name of the
all-27 forward semantic work: that work is the Forward Semantic Execution
Completion milestone, not an unconditional claim attached to package version
0.13.0. This clarification changes neither their semantic requirements nor the
order and qualification requirements of successor authority.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Require every release to complete the next semantic milestone | This couples package maintenance and release timing to a potentially larger capability objective and can misstate the capabilities actually qualified in a release. |
| Reduce the 27-type objective to the capabilities available in one release | This would discard accepted obligations and leave the existing BLOCKED destinations without an accepted disposition. |

**Traceability**
- Refines: Account for every required destination across entity, relationship and value branches (DEC-9014)
- Refines: Select AI 1.4 and ACC 1.4 with unchanged NM 2.5 after human acceptance (DEC-9015)
- Refines: Account for all 27 types while selecting only applicable entity destinations (DEC-9021)
- Refines: Require closed successor publication and independent instance verification (DEC-9022)
- Refines: Freeze exact snapshots; promote compatibility explicitly (DEC-9023)
- Refines: Consolidate governed candidate semantics in independently green checkpoints (DEC-9026)

### DEC-9036 — Preserve the complete all-27 Forward Semantic Execution Completion milestone

**Rationale**

The Forward Semantic Execution Completion milestone remains complete only when
all 455 AI catalog destination rows are QUALIFIED or explicitly retired through
accepted authority; required successor AI, ACC and NM authorities are independently
qualified and promoted; NM materialization and ACC execution meet their required
boundary; a public forward protocol route is available and advertised; Rust,
Python and Node conform to the relevant protocol vectors; a current SCS selects
the approved successor authority; and the complete execution is independently
qualified.

No release or this ADR may relabel, omit, infer satisfied, or weaken any of the
existing 215 BLOCKED obligations. Retirement requires explicit accepted authority
for the exact destination; absence, deferral, package inclusion or release status
is not retirement. All existing scope, semantic ownership, source authority,
equality, lifecycle, outcome-precedence and fail-closed requirements remain.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Treat package release qualification as milestone qualification | Package inventory and publication do not prove complete semantic execution, public protocol conformance or current SCS selection. |

**Traceability**
- Refines: Account for every required destination across entity, relationship and value branches (DEC-9014)
- Refines: Account for all 27 types while selecting only applicable entity destinations (DEC-9021)

### DEC-9037 — Propose v0.13.0 as a lifecycle-governed consolidation release subject to owner approval

**Rationale**

If this ADR is accepted and the owner explicitly approves the v0.13.0 release
scope, v0.13.0 MAY be prepared as a lifecycle-governed consolidation release
under ADR-L-0040. The release description and evidence MUST state only the
capabilities demonstrated by its selected released authority, public interfaces
and exact release qualification. It MUST NOT claim Forward Semantic Execution
Completion unless every milestone criterion in DEC-9036 independently passes.

This proposed decision does not choose the packaged authority cohort, accept a
released-only distribution policy, retire protocol 1.4/1.5, authorize candidate
promotion, or waive exact inventory, approval, certification and publication
controls. Each remains subject to its own accepted authority and release gate.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Hold v0.13.0 until all 27 semantic types are complete | This keeps release numbering coupled to a distinct capability milestone and prevents a bounded consolidation release even when its own lifecycle gates pass. |
| Publish v0.13.0 as if all-27 execution were complete | The current objective includes BLOCKED obligations and incomplete runtime and public-conformance prerequisites; release evidence cannot imply those outcomes. |

**Traceability**
- Refines: Inventory before bundle finalization; attest externally afterwards (DEC-9025)
- Refines: Consolidate governed candidate semantics in independently green checkpoints (DEC-9026)
- Refines: Keep proposed governance and future promotion independently gated (DEC-9028)

### DEC-9038 — Preserve immutable historical objective labels and avoid future release-number coupling

**Rationale**

Existing v0_13_objective labels embedded in immutable AI 1.4/1.5 authority MUST
remain byte-for-byte unchanged. They record the historical objective vocabulary
under which those authorities were authored and qualified; they do not make a
package release number evidence of milestone completion and MUST NOT be used to
rewrite those authorities.

Future normative capability objectives MUST name their scope and exit criteria
independently of an arbitrary repository release number. A release may reference
a milestone and report its measured status, but version assignment MUST NOT
rename, narrow or declare completion of that objective.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Rewrite historical candidate labels to the new milestone name | That would mutate immutable authority and invalidate its established content identity. |

**Traceability**
- Refines: Freeze exact snapshots; promote compatibility explicitly (DEC-9023)





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0327 | A release version MUST promise only capabilities demonstrated by its released authority, public interfaces, and… | MUST / policy | automated |
| INV-0328 | Forward Semantic Execution Completion MUST retain all 455 destinations and require each to be QUALIFIED or… | MUST / policy | automated |
| INV-0329 | Historical v0_13_objective fields in AI 1.4/1.5 authority MUST remain unchanged and MUST NOT be interpreted as proof… | MUST / policy | automated |
| INV-0330 | A normative semantic capability objective MUST define its own scope and exit criteria independently of a repository… | MUST / policy | automated |

### INV-0327

**Statement**

A release version MUST promise only capabilities demonstrated by its released authority, public interfaces, and exact release evidence; the version MUST NOT imply completion of an independent semantic capability milestone.

**Scope:** release-engineering

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Separate package release claims from milestone qualification.

**Upheld by decisions**
- Govern package release versions independently from semantic capability milestones (DEC-9035)

### INV-0328

**Statement**

Forward Semantic Execution Completion MUST retain all 455 destinations and require each to be QUALIFIED or explicitly retired through accepted authority, together with successor AI/ACC/NM qualification and promotion, required NM/ACC execution, an advertised public forward route, Rust/Python/Node protocol-vector conformance, approved current SCS selection, and independent qualification of the complete execution; no existing BLOCKED destination may be silently satisfied or removed.

**Scope:** semantic-authority

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Preserve the complete accepted semantic objective across package release boundaries.

**Upheld by decisions**
- Preserve the complete all-27 Forward Semantic Execution Completion milestone (DEC-9036)

### INV-0329

**Statement**

Historical v0_13_objective fields in AI 1.4/1.5 authority MUST remain unchanged and MUST NOT be interpreted as proof that a repository release completed Forward Semantic Execution Completion.

**Scope:** semantic-authority

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Preserve historical authority bytes while clarifying release scope.

**Upheld by decisions**
- Preserve immutable historical objective labels and avoid future release-number coupling (DEC-9038)

### INV-0330

**Statement**

A normative semantic capability objective MUST define its own scope and exit criteria independently of a repository release number; release versioning MUST NOT narrow or declare completion of that objective.

**Scope:** governance

**Enforcement:** MUST (policy)
**Verification:** automated

**Rationale**

Prevent arbitrary package numbering from governing normative capability scope.

**Upheld by decisions**
- Preserve immutable historical objective labels and avoid future release-number coupling (DEC-9038)







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)
- [ADR-L-0040](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md)
- [ADR-L-0041](ADR-L-0041-qualified-shared-system-scope-and-producer-evidence.md)

**References**
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)
- [ADR-L-0040](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md)
- [ADR-L-0041](ADR-L-0041-qualified-shared-system-scope-and-producer-evidence.md)


## Architecture Relationships

| Neighbor | Relationship | Exact Path |
| --- | --- | --- |
| [ADR-L-0038 — Explicit Required-Output Authority Across the AI Catalog](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md) | refines | `DEC-9035 -[:refines]-> DEC-9014` |
| [ADR-L-0039 — Forward Identity Representation Recipes](ADR-L-0039-forward-identity-representation-recipes.md) | refines | `DEC-9035 -[:refines]-> DEC-9021` |
| [ADR-L-0040 — Enforceable Semantic Contract Candidate and Promotion Lifecycle](ADR-L-0040-semantic-contract-candidate-and-promotion-lifecycle.md) | refines | `DEC-9035 -[:refines]-> DEC-9023` |




## Notes

Proposed REL-1 scope clarification. This record is inactive unless accepted under
repository governance. It is not approval to release, promote, tag or publish
v0.13.0 and does not select candidate authority or public capability.

ADR-L-0038 DEC-9014/9015 and ADR-L-0039 DEC-9021/9022 retain their full type,
destination, successor-authority, and independent-qualification requirements.
The phrase “v0.13 objective” is refined to refer to the Forward Semantic Execution
Completion milestone rather than an unconditional assertion about a package
version. ADR-L-0040's accepted candidate, inventory, promotion and immutability
controls remain unchanged; ADR-L-0041's System evidence and execution boundaries
remain unchanged. No accepted semantic requirement is retired or weakened.

The REL-3a inventory and package hashes are rehearsal evidence only. They do not
qualify a future release source, select a packaged cohort, establish owner
approval, or attest candidate promotion.


---

*Generated from ADR-L-0042 by ADR Architecture Kit (projection v3)*