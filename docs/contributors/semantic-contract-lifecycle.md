# Semantic contract candidate and promotion lifecycle

This is the specification accepted by **ADR-L-0040**. Initial adoption follows
the preceding procedure recorded below; subsequent evidence rules are prospective. The checker validates the
declared map and evidence; it does not discover or resolve arbitrary prose conflicts.

## Release evidence and compatibility classification

The canonical companion is
`adrs/migrations/semantic-contract-lifecycle-classification.json`. It records exact
resource manifests and artifact evidence. The audit source is
`3c20a78bbb7baa2e84402473960ae009d29a995d`; this is an evidence snapshot, not a
permanent restriction on future changes. Public registries' hash-verified 0.12.2
wheel and npm tarball corroborate tag v0.12.2 at
`055b8634c5ffd0068bd8376ac0baae7cc76f0c6d`.

| Authority | Classification | Preservation / proposed disposition |
|---|---|---|
| AI 1.0 and 1.1 | RELEASED | Exact SCFs and 24 / 5-resource closures; preserve discovery |
| ACC 1.0 | RELEASED | Exact SCF and 2-resource closure, embedded in released WASM; preserve SDK construction and C01-C42 |
| NM 2.3 and 2.4 | RELEASED | Exact SCFs and seven-resource closures |
| Normative Semantics 1.0 | RELEASED | Exact SCF and two-resource closure |
| Authoring 1.5/1.6/1.7, earlier shipped encodings, NM 1.1/2.0/2.1/2.2 | RELEASED resources | Preserve actual released schemas; do not invent SCFs |
| ADC 1.0 discovery; ADC 1.1 and CEC 1.0 | RELEASED resources | Existing resource-qualified identities; latter contracts embedded in released WASM |
| AI 1.4/1.5 and ACC 1.4 | EXPLICITLY PROMOTED, unreleased | Preserve recorded human approvals and exact snapshots; only new authenticated acceptance may correct ongoing retention effect |
| AI 1.2/1.3 and ACC 1.1/1.2/1.3 | HISTORICAL DEVELOPMENT with accepted policy obligations | No distribution evidence found; further independent-promotion/consumer evidence must be considered before removal |
| AI 1.5 / ACC 1.5 / NM 2.5 | Target UNRELEASED CANDIDATES after correction | Same intended versions; exact revision SCFs, no automatic perpetual compatibility |
| External consumers, retained candidate results | UNKNOWN where unregistered | Investigate before withdrawing a required dependency |
| Local .tmp-release-bundle 0.9.0 | UNKNOWN/local qualification | Source and wheel hash do not match published 0.9.0; not publication proof |

The classification deliberately distinguishes evidence from the proposed future
state. A merge, tag, filename or immutable-looking JSON is not proof of release.
The latest released Python/Node WASM bytes match (SHA-256
`5d7eec35981e1cdebc15f9a448890cfe18322f7ebad055e3413a2c7f04dc1a48`).
The wheel hash is
`3fbf2ddefa77fc7abd20e09e41ad9f6d3390453c90d067f2f88426c815e3494f`;
Node tarball hash is
`8fc6b305348e7cea953fa334cd17ed311962af194209e29b846c7d17c9e00588`.
This includes embedded authorities, not just discoverable SCF files.

Released protocol 1.0-1.3, SDK/Consumer Binding 1.0, retained ADR v1.0 and the
public surfaces documented in `public-surface-and-stability.md` remain obligations.
Tracked HEAD audits of adjacent ste-spec, ste-runtime, ste-architecture-substrate
and ste-handbook found general SDK consumers but no candidate SCF or prototype-op
pins. This is bounded negative evidence, not a claim about all external consumers.

## Exact precedence and authentic activation

`adrs/migrations/semantic-contract-lifecycle-precedence.yaml` contains 29 exact
clause spans in ADR-L-0031/0034/0035/0037/0038/0039. Each binds original ADR/member
UUIDs, alias, field, unique UTF-8 anchor/digest, replacement decision identity and
closed family/version/topic applicability. It does not retire whole decisions.

| Topic | Replacement | Effect only after authenticated acceptance |
|---|---|---|
| snapshot_identity | DEC-9023 | Old exact content/conformance remains immutable and reproducible; it does not freeze every development version's active bytes or distribution |
| candidate_version_finality | DEC-9023 | Enumerated unreleased revisions can evolve at the same intended version; released/promoted identities outside the correction stay immutable |
| candidate_selection | DEC-9026 | Current candidate targets AI 1.5 / ACC 1.5 / NM 2.5; exact revised dependencies still mandatory |
| prototype_retention | DEC-9026 | Later bounded consolidation may retire unshipped prototype routing; no PR A change or released protocol withdrawal |

Scope is limited to AI 1.2-1.5, ACC 1.1-1.5 and NM 2.5 and the declared lifecycle
policy topic. Released identities are excluded. Original clauses retain force
outside that scope. The checker reports residual text of mapped members and every
unmapped accepted decision/invariant. No natural-language contradiction resolution
is claimed. Identity, ownership, five dispositions, lifecycle, representation,
composition, independent verification, equality, outcomes and fail-closed semantics
remain. DEC-0271 is not superseded. ADR-L-0028 historical recovery and SCF v1's
preimage/canonicalization are unchanged.

`python scripts/check_semantic_contract_lifecycle_design.py` validates proposed
design only. It returns zero effective replacements. Proposed acceptance metadata
is rejected. Accepted status without independent evidence is rejected.

### Initial adoption under the preceding procedure

Initial-adoption transition: this ADR's own acceptance uses the preceding
conversational ADR acceptance procedure, not the new evidence gate it introduces.
The human explicitly approved reviewed commit
b3c6c7ffcf9ccf9e2992a35d6b3ff8b2b7f9e78d and then directed continuation after
the circular requirement was identified. Record those actual messages and their
source identities in semantic-contract-lifecycle-bootstrap.json; do not fabricate
a GitHub comment or APPROVED review. This single historical adoption is qualified
against the exact approved architecture, unchanged map/classification/schemas and
only the explicit transition/lifecycle edits. It is not externally authenticated
GitHub evidence, a general metadata bypass, authority promotion, or a waiver for
later decisions, substantive amendments or release gates. The review/comment paths
below remain prospective requirements; they cannot retroactively govern their own
first adoption. Every later qualification of this initial accepted record must
verify the same bounded historical authorization and exact approved content.

Two authenticated architectural-authorization paths are supported:

- An independent GitHub **APPROVED review**, retrieved through `gh api`, from a
  non-bot authorized required approver who is not the PR author. The existing
  statement is `Approve ADR-L-0040 lifecycle governance and activation.`; GitHub's
  review `commit_id` must identify the exact 40-character reviewed revision.
- An actual authorized human's **new, unedited ordinary PR comment on #187**.
  The owner may author this comment on their own PR. It must contain exactly this
  statement (replace the placeholder with the complete lowercase commit SHA):

  ```text
  I approve ADR-L-0040 lifecycle governance and activation at reviewed commit <40-character-reviewed-commit>.
  ```

The owner must post that authorization themselves. Codex or another automated
agent must not manufacture it, impersonate the owner, or post a proxy approval.
The comment author must be a human account in PROJECT.yaml's admitted
`required_approvers` policy. Comment identity, repository, PR #187 association and
membership of the reviewed commit in that PR are independently checked. REST and
GraphQL retrieval must agree on identity, author, body and creation timestamp.
`lastEditedAt` and `editor` must be null; changed timestamps, minimized comments,
known GitHub-app/bot origins or unavailable edit-history proof fail closed.
This also rejects same-second edits that `updated_at` alone cannot establish.

Both paths independently compare the entire reviewed ADR, precedence map,
classification, specification and schema bytes. An acceptance commit may alter
only status and paired approval actor/date, with date matching the actual evidence
event. Any normative change requires fresh human authorization. No trusted local
flag, environment override or synthetic fixture can authorize activation.

The read-only checker preserves `--reviewed-revision` / `--approval-review-url`
for independent reviews. A future canonical acceptance must add the closed file
`adrs/migrations/semantic-contract-lifecycle-acceptance.json`, with this ADR's UUID,
the exact reviewed revision, and exactly one evidence branch:

- `approval_review_url` for the existing independent APPROVED review; or
- `owner_comment` with actual integer `id`, `author_login`, exact `created_at`,
  `source_url` and SHA-256 `body_digest` over the exact UTF-8 API comment body.

The reference is a locator and commitment, never self-certified approval. No such
file or approval is created during this cleanup. Every canonical accepted governance
qualification retrieves provider evidence again. Missing, forged, edited, stale or
unsupported evidence fails CI. Synthetic accepted fixtures remain tests and never
activate canonical governance. Preserve access to the exact reviewed Git object.
Proposed status remains inactive regardless of any supplied reference.

An owner comment qualifies architectural authorization only. It is **not** a
GitHub APPROVED code review, does not increase formal approval counts, does not
satisfy independently required reviews, and cannot bypass branch protection,
mandatory checks or separate merge authorization. The checker reports the evidence
kind and `github_approved_review: false` for this path. The independent review path
retains its actual APPROVED state and non-author constraint. Existing historical
approval records remain intact.

## External promotion attestation specification

The closed maintenance schemas in `scripts/schemas/` are not new public semantic
contracts or a registry. They specify this acyclic sequence:

```
source S -> exact package payloads P -> actual authority inventory I
         -> finalized qualified retained bundle A (P, I, manifest)
         -> external human approval and companion attestation B
         -> publication of unchanged P
```

The later release-controls checkpoint must independently scan wheels, sdists, npm
packages and embedded WASM, reconcile all actually included authorities and qualify
every exact closure. A declared inventory alone cannot prove completeness. Include
schema-only/resource-qualified authorities without invented SCFs, every transitive
resource and every package placement. Conflicting duplicates, unknown/unaccounted
payload and unapproved candidates fail closed. Multiple placements of one authority
are retained as evidence, not extra semantic authority.

Inventory arrays sort by authority family/version, resource key, artifact name and
placement artifact/locator; no duplicates. Envelope bytes use the existing governed
canonical JSON implementation. I hashes package payloads; the manifest commits I
and P. Neither contains its own or enclosing bundle hash. Finalized A is retained
without modification. B is created afterwards, outside S/P/A, and can hash A,
manifest, I and P. B has no self-hash. A later evidence-recording Git commit does
not replace S, retag source or rebuild payloads.

B selects the exact successful Release Certification **main-push** run, source S,
retained artifact identity and all hashes. Its approved cohort equals I exactly,
including already released/promoted members and every candidate being promoted.
Human approval must be independently verified against the exact retained cohort
and appropriate authorization; declarative approval fields alone are insufficient.
An unapproved authority cannot be removed from finalized A. Any mismatch requires
new source/configuration, qualification and a new retained bundle. Never edit
retained artifacts in place. Existing build-once promotion-only publishing remains.

The PR A helper validates shape, supplied payload hashes, declared cohort equality
and the hash DAG. It explicitly returns `promotion_authorized: false`, human trust
unverified and publisher enforcement unimplemented. It is not an operational
scanner, bundle completeness proof, release resolver or publisher gate.

## Bounded implementation sequence

1. PR A: proposed ADR, classification, exact precedence, attestation specification,
   bounded checker and adversarial tests. Human review; no automatic acceptance.
2. After authentic acceptance, independently green release-controls checkpoint:
   actual payload inventory discovery, trusted external human approval, exact
   attestation validation and publisher enforcement. Keep main-push/build-once,
   retained bundles, source/tag binding and promotion-only publishing.
3. Atomic candidate cohort checkpoint: reuse PR #186 at
   `6ddc8c2b6d66531ff3ecefb0bba7b15616ac4f0c`, preserve source/CI traceability,
   consolidate AI 1.5 / ACC 1.5 / NM 2.5 definitions, resources, exact dependency
   graphs, mirrors, loaders and conformance together. Do not modify/close #186 in A.
   Remove development-only preservation only after classification/acceptance and
   external obligation review. Never expose an unqualified intermediate capability.
4. An additional bounded private Rust qualification refactor PR is permitted if
   needed to preserve independently green review. No duplicated semantic policy.

Every revision uses exact SCF/closure and recorded Git source. An upstream candidate
change requires downstream dependency/SCF qualification; old receipts are invalid.
Prior revisions reproduce from their exact Git commit. Promotion freezes the exact
version/SCF/resource tuple; a later candidate label cannot bypass that freeze.

AI 1.5 retains 27 types, six branches, 240 qualified definitions, 215 BLOCKED
entries, 26 label rules, 54 identity representations and three operations; these
are regression expectations, not proofs. All instance prerequisites remain.
No new producer, current SCS selection, public runtime capability, materialization,
complete interpretation, semantic_equivalent, Constructed, persistence or admission
is authorized. No package version bump or release artifact/tag rewrite.

## Qualification responsibility

Permanent tests validate exact clause anchoring/scope, proposed inactivity,
independent approval rejection, released bytes/closures, same-version SCF changes,
qualified dependency propagation, old Git reproduction and post-promotion identity
protection. Attestation fixtures include embedded/no-SCF authority and adversarial
cohort mismatch/self-reference. Tests do not claim end-to-end publishing.

PR-scoped diff/original-checkout/PR #186 preservation is separately checked at the
actual base/head. No permanent test forbids future authorized successor files,
changes a current-selection policy, or pins the repository forever to this PR base.
