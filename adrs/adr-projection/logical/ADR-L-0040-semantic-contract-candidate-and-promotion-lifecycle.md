<!--
integrity_schema_version: 1
generated: deterministic_projection_v1
artifact_kind: rendered_adr_markdown
generator_id: adr-projection-markdown
generator_version: 3
hash_algorithm: sha256
source_hash: 117952683e27d9af52d98f214e9123e1bf5526aef020de12e0fa3d08afc7a2d8
rendered_hash: 0984f82b86f98d971130bcc3ec2f78c309ce3afec9802923acfa83c25f561f5e
-->

# ADR-L-0040: Enforceable Semantic Contract Candidate and Promotion Lifecycle

## Identity / Status

**Type:** logical<br>
**Status:** proposed<br>
**Alias:** ADR-L-0040<br>
**Authoring contract:** authoring v1.5<br>
**Created:** 2026-10-26<br>
**Authors:** erik.gallmann<br>
**Domains:** architecture, governance, release-engineering<br>
**Tags:** semantic-contract-lifecycle, candidate-authority, release-promotion, v0.13<br>

## Architecture at a Glance

| | |
| --- | --- |
| Logical authority | ADR-L-0040 |
| Status | proposed |
| Decisions | 6 |
| Invariants | 6 |


## Context

Development merged several unreleased AI and ACC authorities while treating each
merge and content fingerprint as a permanent compatibility boundary. That policy
creates maintenance obligations without a released consumer. Git history and SCF
content identity remain essential, but neither alone establishes release promotion.
The desired current candidates are AI 1.5, ACC 1.5 and NM 2.5. We correct when
immutability begins, without renumbering, weakening exact qualification, changing
semantic meaning, rewriting history or withdrawing actually released authority.

Hash-verified PyPI and npm artifacts, release tags and embedded WASM establish the
release baseline in the companion classification. ACC 1.0, ADC 1.1 and CEC 1.0
were embedded in released WASM; absence of standalone discovery is not absence of
release. An unrelated local retained bundle is not published-release evidence.
Earlier human publication approvals remain preserved, authentic historical records.
A new explicit human architectural acceptance is required for this one-time policy
correction; this proposed ADR cannot activate any replacement.
## Architectural Decisions

| Decision | Choice | Traceability |
| --- | --- | --- |
| DEC-9023 | Freeze exact snapshots; promote compatibility explicitly | — |
| DEC-9024 | Resolve mapped policy clauses without retiring semantic authority | — |
| DEC-9025 | Inventory before bundle finalization; attest externally afterwards | — |
| DEC-9026 | Consolidate governed candidate semantics in independently green checkpoints | — |
| DEC-9027 | Separate authority, representation, semantic and promotion proofs | — |
| DEC-9028 | Keep proposed governance and future promotion independently gated | — |

### DEC-9023 — Freeze exact snapshots; promote compatibility explicitly

**Rationale**

A contract receives its intended family/version during development. CANDIDATE
revisions may change schemas, resources, rules, conformance and implementation
within that version through governed review. Each revision MUST qualify its exact
SCF v1, complete resource closure and Git source commit. The SCF identifies exact
content; no SCF, schema or closure verification is weakened or omitted. A changed
candidate receives a changed SCF; old receipts cannot qualify the new revision.
RELEASE CANDIDATE fixes one source revision for full qualification; a correction
requires fresh qualification but not automatically a version increment.

Explicit independent authority promotion or public release freezes family,
version, exact SCF (where that family has SCF authority), full resource closure,
normative conformance and packaged bytes. Post-promotion authoritative changes
require a successor version; same-version replacement MUST fail even if a caller
relabels it candidate. Superseded/retired promoted identities retain the established
compatibility and historical recovery policy. Existing resource-qualified authorities
without SCFs remain qualified by their real identities and digests; invent no SCF.
Package version, readiness, implementation completeness, current SCS and public
capability advertisements are separately governed. A candidate can be discoverable
in development without being a released compatibility identity.

Released classifications require positive artifact evidence. The companion
classification records released, explicitly promoted, unreleased candidate,
historical development and unknown evidence separately. Past human approvals of
unreleased AI/ACC publications are preserved as exact approved content snapshots;
acceptance of THIS ADR explicitly corrects their ongoing compatibility effect only
within the mapped candidate scope. It neither denies those approvals nor authorizes
changing released artifacts. Unknown external/persisted obligations require evidence
before removal. Do not infer release from main/develop, a version number or a tag
alone. Immutable source history and content snapshots remain reproducible.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Keep every merged development version immutable forever | Merge/content identity is not positive release evidence; this perpetuates unnecessary compatibility machinery. |
| Remove versioning or weaken SCF verification | Exact content identity and qualified dependencies remain mandatory for candidates and releases. |
| Treat all unreleased approvals as nonexistent | Preserve genuine review records and exact snapshots; explicit new human correction is required. |

### DEC-9024 — Resolve mapped policy clauses without retiring semantic authority

**Rationale**

The selected closed precedence map is the exclusive replacement mechanism for
this lifecycle correction. On authenticated acceptance, each mapped exact original
clause is replaced ONLY for its declared policy topic and enumerated unreleased
family/version applicability by the identified decision requirement of this ADR.
The original MUST no longer imposes conflicting version-finality, distribution or
successor-only obligations in that domain. Outside that scope it remains in force.
A refines relationship alone is insufficient. No whole predecessor decision or
invariant is retired. Released compatibility obligations cannot be mapped away.

The checker MUST establish original ADR/member canonical UUIDs, aliases as integrity
cross-checks, field names, structurally unique exact text anchors and UTF-8 digests,
replacement UUIDs and named requirement identity, closed applicability, and absence
of overlapping replacement scopes or cycles. It reports all unmapped obligations;
it does not resolve natural-language contradictions outside the declared map.
The map covers governance lifecycle/selection only, never canonical identity,
source ownership, field dispositions, literal lifecycle, representation operations,
composition, exact dependency qualification, whole-ledger equality, outcomes or
fail-closed requirements. DEC-0271 remains unchanged. Earlier approved source and
approval records are never edited or erased.

Proposed status is INACTIVE. Accepted metadata alone cannot activate the map.
Activation requires independently retrieved, appropriately authorized human evidence
bound to the exact reviewed Git revision containing this ADR, map, classification
and specification. Verify actor against PROJECT required_approvers, human account,
approval state, repository, reviewed commit and unchanged reviewed policy. Only
status plus paired approved_by/approved_date may differ for acceptance; changes to
notes, rationale, map or evidence require a new review. Self-declared verified flags,
assistant proxy comments and synthetic accepted fixtures are not acceptance proof.
A GitHub APPROVED review must explicitly authorize ADR-L-0040 lifecycle governance
and activation; a dismissed review is invalid. A separately implemented qualified
protected human gate may supply equivalent evidence in a future checkpoint.
The current repository owner cannot approve their own PR through an ordinary PR
review. If no qualifying approval mechanism exists, acceptance remains blocked;
that does not prevent reviewing this proposed design. Never fabricate evidence.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Use a refines edge or newest ADR wins | This leaves conflicting MUST clauses or silently discards unmapped semantics; use exact scoped replacements. |

### DEC-9025 — Inventory before bundle finalization; attest externally afterwards

**Rationale**

Extend existing build-once, main-push release qualification without rebuilding at
publication. Source S produces exact package payloads P. Before finalization,
derive deterministic inventory I of ALL semantic authorities actually included in
P, including embedded WASM authorities, transitive resources, schema-only and
resource-qualified authorities without SCFs. Inventory records exact authority
identity, SCF where applicable, complete resource keys/digests, actual package
placements and evidence. Conflicting identities, unknown payloads or unaccounted
authorities fail closed. Repeated placements are recorded without inventing a
second authority. Sort identities, resources and placements deterministically.
The qualified retained bundle A contains P, I and their qualification manifest.
All released authorities retain their supported discovery and compatibility.

After A is finalized, an external companion promotion attestation B MUST approve
precisely I, including the disposition of every already released or independently
promoted member and explicit approval of each candidate being promoted. Bind B to
S, main-push qualification workflow/run and conclusion, retained bundle identity,
manifest/inventory/package hashes and authentic authorized human approval. B is
outside P, A and S. No artifact includes its own digest, no source commit includes
an attestation that hashes itself, and no later evidence-recording commit replaces
S or triggers a rebuild. I may hash P; manifest may hash I/P; B may hash finalized
A/manifest/I/P. Neither I nor manifest contains A's enclosing hash or B.

An omitted, extra, unapproved or differently qualified authority makes promotion
Unavailable. An unapproved authority MUST NOT be stripped retrospectively from a
finalized bundle, nor may its manifest or inventory be edited. Qualify a fresh
source/configuration and newly retained bundle instead. Promotion publishes only
identical retained P. Preserve existing main-push qualification, bundle retention,
tag/source checks and promotion-only publication. No ordinary tag-time rebuild.
The closed schemas and focused validators here specify this boundary only; actual
wheel/npm/WASM inventory discovery and end-to-end publisher enforcement belong to
the subsequent release-controls checkpoint. Do not claim operational gating yet.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| Embed final approval inside the hashed retained bundle | This creates artifact/Git self-reference or forces rebuilding approved payloads. |
| Strip an unapproved authority from a finalized bundle | This changes retained qualified bytes; require a fresh source and bundle instead. |

### DEC-9026 — Consolidate governed candidate semantics in independently green checkpoints

**Rationale**

After explicit acceptance, use AI 1.5, ACC 1.5 and NM 2.5 as current development
candidates, not AI/ACC 1.6 merely for corrections before promotion. Keep released
AI 1.0/1.1, ACC 1.0, NM 2.3/2.4 and all other classified released dependencies.
Absorb development-only predecessor semantics by direct qualified candidate
resources where sufficient, rather than maintaining chains only because a PR was
merged. Preserve actual independently promoted/external obligations until this
explicit correction and evidence classification permit otherwise. Git retains all
old revisions; do not rewrite tags, released artifacts or historical approvals.
An old SCF always identifies its old exact content, not whatever the version now
resolves to. Dependencies between candidate revisions MUST select exact content;
recompute downstream closure/SCF and reject stale cross-revision evidence.

Do not blindly rewrite version strings or inherited rule identities. Preserve every
accepted substantive semantic rule. AI 1.5 retains 27 types, six output branches,
240 qualified definitions, 215 BLOCKED entries, 26 literal-copy rules, 54 identity
representation definitions and three exact operations; counts do not prove meaning.
BLOCKED never becomes a producer. ACC 1.5 retains the existing single binding,
proof chain and bounded construction semantics. No missing producer may be invented.
Unshipped protocol 1.4/1.5 prototype operations can be retired in that separately
reviewed consolidation while preserving released protocol 1.0-1.3; no such change
occurs here. Current SCS and public capabilities do not change implicitly.

Reuse PR #186 source at 6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c and its validation
as migration input, not accepted release proof. This PR neither modifies nor closes
it. First independently qualify release-controls inventory/attestation enforcement.
Then consolidate the co-dependent authority cohort, loaders, mirrors and conformance
atomically in a bounded PR/checkpoint, updating PR #186 with explicit retained-work
traceability only after approval. Keep each checkpoint independently green; never
expose transient unqualified authority as a public capability. A separate bounded
Rust reusable-qualification checkpoint is permitted if genuinely needed. Preserve
meaning and trust boundaries while removing development-only version maintenance.

**Alternatives Considered**

| Alternative | Rejected because |
| --- | --- |
| One unbounded consolidation PR | Independent release-control qualification and an atomic candidate cohort are safer to review; a further bounded Rust PR is allowed. |

### DEC-9027 — Separate authority, representation, semantic and promotion proofs

**Rationale**

Qualification MUST prove released identities byte-exact and discoverable where
compatibility requires; same-version candidate correction changes SCF and requalifies
complete dependency closure; old revisions reproduce from recorded Git commits;
stale resources/receipts and validly rehashed unauthorized semantics fail; exact
promotion prevents later same-version substitution even under a candidate label.
Test competing/missing producers, source and contextual ownership independently of
content hashing. Preserve semantic and representation verification separately.

Precedence tests cover wrong/missing/ambiguous anchors, UUID substitution, digest
changes, scope expansion, duplicate replacements, unmapped obligations, proposed
inactivity and forged/unauthorized/stale approval. Synthetic accepted fixtures may
test pure resolution but MUST NOT activate canonical repository governance.
Attestation tests cover complete cohort equality, embedded/no-SCF authorities,
missing/extra/duplicate authority, package/inventory mismatch, self-reference,
non-main/non-push qualification, source/run mismatch and edits of retained bundles.
These are specification tests until operational release enforcement is qualified.

Rust/Python/Node/WASM, governance, deterministic generation, current semantic
conformance and released SDK compatibility remain required as applicable. No test
may pin all future work to this PR base, require candidates to stay unselected
forever, or interpret a successor's existence as runtime capability. No public
construction, complete interpretation, semantic_equivalent or Constructed follows
from authority publication or this governance decision.

### DEC-9028 — Keep proposed governance and future promotion independently gated

**Rationale**

PR A contains only this proposed ADR, exact precedence/classification evidence,
external attestation/inventory specification, bounded governance qualification,
focused permanent tests and owned derived projections. It publishes no successor
contract, modifies no candidate resource or SCF, and implements no runtime/publisher.
Human acceptance must explicitly approve the lifecycle correction and its map at
an exact reviewed revision. No auto-acceptance, fabricated metadata or auto-merge.

After authentic acceptance: release-controls enforcement checkpoint; qualified
candidate consolidation using PR #186; optional bounded Rust cleanup; then resume
actual interpretation/construction against exact current candidate authority.
Before release, independently qualify the fixed candidate revision and exact
packaged authority cohort, obtain external human promotion approval, and publish
retained artifacts only. Promotion and current SCS/capability selection remain
separate approvals. Until every qualification is satisfied, missing capability is
Unavailable, known invalidity Rejected and Unresolved requires a governed dependency;
preserve Rejected > Unavailable > Unresolved. No ledger/equality shortcut, synthetic
lifecycle, persistence, admission or promotion capability is introduced here.

Qualified companion content (exact UTF-8 SHA-256; no enclosing ADR hash cycle):
adrs/migrations/semantic-contract-lifecycle-precedence.yaml sha256:b3506f6b3d0ce3481f8499eeed239f3849e560a79c76024df4897e6b1e52edd5
adrs/migrations/semantic-contract-lifecycle-classification.json sha256:835f83676f3fc2023e7f057661d9e8717b1d432f1b04a77d2ea81558e9921f86
docs/contributors/semantic-contract-lifecycle.md sha256:4f455d00dfd0f276cdd72cef73adcd3b96f9e299aa63115d6556645ed1f5b62c
scripts/schemas/authority-promotion-attestation.schema.json sha256:d9624d2f07e464809c2a079dd950410608c69f5867a31affa1ccc49acd7dec3b
scripts/schemas/lifecycle-precedence.schema.json sha256:f116fe585d44c895b4133813a07cd7674f28117cbed0554d6ca9b0b04c019da2
scripts/schemas/packaged-authority-inventory.schema.json sha256:0b502d74d3b4c1b5f4481842531502bee1b09f0934c69484639c83b02a2c7cb2





## Invariants

| Invariant | Requirement | Enforcement | Verification |
| --- | --- | --- | --- |
| INV-0315 | Only explicit release or independent authority promotion freezes ongoing same-version compatibility; every candidate… | MUST / design | automated |
| INV-0316 | Only authenticated acceptance and exact mapped clause applicability may replace lifecycle obligations; all unmapped… | MUST / design | automated |
| INV-0317 | The attestation MUST approve exactly all authorities actually packaged in the finalized qualified bundle; mismatch… | MUST / design | automated |
| INV-0318 | Candidate consolidation MUST preserve released compatibility, exact dependency selection and accepted semantics… | MUST / design | automated |
| INV-0319 | Independent qualification MUST distinguish content identity, authority, instance evidence, representation… | MUST / design | automated |
| INV-0320 | Proposed governance, synthetic fixtures and self-declared approval MUST NOT activate canonical policy or publisher… | MUST / design | automated |

### INV-0315

**Statement**

Only explicit release or independent authority promotion freezes ongoing same-version compatibility; every candidate revision MUST retain exact SCF, closure and Git reproducibility.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Freeze exact snapshots; promote compatibility explicitly

**Upheld by decisions**
- Freeze exact snapshots; promote compatibility explicitly (DEC-9023)

### INV-0316

**Statement**

Only authenticated acceptance and exact mapped clause applicability may replace lifecycle obligations; all unmapped and substantive semantic obligations MUST remain in force.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Resolve mapped policy clauses without retiring semantic authority

**Upheld by decisions**
- Resolve mapped policy clauses without retiring semantic authority (DEC-9024)

### INV-0317

**Statement**

The attestation MUST approve exactly all authorities actually packaged in the finalized qualified bundle; mismatch requires a new qualification and MUST NOT mutate retained artifacts.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Inventory before bundle finalization; attest externally afterwards

**Upheld by decisions**
- Inventory before bundle finalization; attest externally afterwards (DEC-9025)

### INV-0318

**Statement**

Candidate consolidation MUST preserve released compatibility, exact dependency selection and accepted semantics without inventing producers or transient public capabilities.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Consolidate governed candidate semantics in independently green checkpoints

**Upheld by decisions**
- Consolidate governed candidate semantics in independently green checkpoints (DEC-9026)

### INV-0319

**Statement**

Independent qualification MUST distinguish content identity, authority, instance evidence, representation verification and semantic equality; none substitutes for another.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Separate authority, representation, semantic and promotion proofs

**Upheld by decisions**
- Separate authority, representation, semantic and promotion proofs (DEC-9027)

### INV-0320

**Statement**

Proposed governance, synthetic fixtures and self-declared approval MUST NOT activate canonical policy or publisher gating; authentic reviewed human evidence is required.

**Scope:** governance

**Enforcement:** MUST (design)
**Verification:** automated

**Rationale**

Keep proposed governance and future promotion independently gated

**Upheld by decisions**
- Keep proposed governance and future promotion independently gated (DEC-9028)







## Lifecycle / Related Architecture

**Related ADRs**
- [ADR-L-0028](ADR-L-0028-normative-semantic-authority-and-materialization-foundation.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)
- [ADR-L-0035](ADR-L-0035-governed-composition-intent-binding-for-authoring-construction.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)

**References**
- [ADR-L-0028](ADR-L-0028-normative-semantic-authority-and-materialization-foundation.md)
- [ADR-L-0031](ADR-L-0031-non-recursive-semantic-contract-conformance-binding.md)
- [ADR-L-0034](ADR-L-0034-detached-normalized-semantic-equivalence-for-authoring-construction.md)
- [ADR-L-0035](ADR-L-0035-governed-composition-intent-binding-for-authoring-construction.md)
- [ADR-L-0037](ADR-L-0037-lossless-authored-lifecycle-and-declaring-adr-provenance.md)
- [ADR-L-0038](ADR-L-0038-explicit-required-output-authority-across-the-ai-catalog.md)
- [ADR-L-0039](ADR-L-0039-forward-identity-representation-recipes.md)





## Notes

Proposed for explicit human architectural review only. No acceptance metadata.
The exact precedence map and released-compatibility classification are normative
companions selected below by content digest. Generated projections are derived.
PR #186 remains open and untouched; its reviewed source and validation evidence
are useful candidate input, not an immutable release or approval of this policy.
No operational publisher enforcement, consolidation or runtime work occurs here.


---

*Generated from ADR-L-0040 by ADR Architecture Kit (projection v3)*