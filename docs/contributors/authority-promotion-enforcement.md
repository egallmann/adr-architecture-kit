# Exact authority-cohort release enforcement

This checkpoint implements the operational gate specified by accepted ADR-L-0040.
It does not release a package, promote a candidate authority, change an SCF, or
select a new capability. PR #186 remains a separate candidate-consolidation slice.

## Qualification and retained inventory

Release Certification still runs only on a `main` push. After building the wheel,
sdist and npm tarball once, `release_manifest.py inventory` independently reads the
actual archives. The scanner examines discoverable JSON, generated JavaScript
authority and standard WASM data segments. It rejects duplicate/unsafe archive
members, links, unknown/changed authority, inconsistent WASM, incomplete per-package
SCF resource closures and missing schema-reference dependencies. Test/example data
in an sdist is not an independently discoverable runtime authority.

Every discovered value must match exact canonical source authority on the certified
source revision. Tracked authority, packaged schema/compatibility mirrors and WASM
must match that commit; untracked or ignored authority files cannot supplement it.
Ordinary interpreter cache files are not authority. Definition fingerprints and
closures are verified by the existing Rust semantic-contract implementation.
Resource-qualified/schema-only authority is
included without an invented SCF. Source-qualified released identities and resources
remain protected by the accepted positive release evidence. Package placement and
duplicate placements are evidence, not additional semantic ownership.

The accepted registry artifact digests are checked against the actual retained
PyPI/npm release payloads, including their JS and WASM authority. Cached evidence
is rehashed before use. This also establishes schema-only released meaning rather
than treating a non-SCF authority as a candidate merely because it lacks an SCF.
Mutable catalog, policy, current-pointer and host-capability metadata remains
source/package integrity evidence; it is not promoted into immutable semantic
meaning by its physical presence.

Each Python distribution must retain the authority values from the recorded released
wheel; npm must retain those from the recorded released npm artifact. This is checked
even when an entire old definition is absent, not only when a present definition has
an incomplete closure. Equivalent package locations may change; released meaning
cannot disappear. Unreleased candidate revisions do not establish this obligation.

The resulting `authority-inventory.json` and `authority-manifest.json` use the shared
Rust canonical JSON implementation. Arrays have deterministic authority/resource/
placement/artifact ordering. The manifest commits the source, all three package
payloads and inventory; neither embeds its enclosing archive hash. They are retained
alongside the unchanged package payloads and existing Python release manifest in the
single `release-bundle` artifact. A failure requires new source/configuration and a
new fully qualified bundle. Never remove an unapproved authority from a finalized
bundle or rewrite retained artifacts.

## Authorized owner approval without a self-review deadlock

An administrator must configure the GitHub environment
`semantic-authority-promotion` before real use:

- Required human reviewers must include an authorized `PROJECT.yaml`
  `integrations.scm.required_approvers` account.
- Permit self-review for this **environment approval**, so the authorized owner can
  approve a workflow they dispatched. This is not a GitHub PR APPROVED review.
- Disable administrator bypass. Repository branch protection remains independent.

Missing or inconsistent protection fails closed even if a workflow was allowed to
start. The code never creates approval, configures a permissive environment, treats
the dispatcher as the approver, or trusts a local approval flag.

After successful exact-source main-push Release Certification, dispatch
`authority-promotion.yml` on that same `main` revision with its certification run ID.
Its first job downloads and verifies the finalized artifact, independently scans
the cohort, and prints this exact statement with computed identities:

```text
I approve semantic authority promotion for source <40-character SHA> and exact retained cohort sha256:<64-character subject digest>.
```

Review the complete retained inventory and finalized bundle. An authorized human
approves the protected-environment deployment and pastes the exact statement into
the environment review comment. The subject digest covers the exact source,
successful certification run, immutable retained artifact ID/ZIP digest, canonical
manifest/inventory digests, package hashes and full authority cohort. It excludes
only the subsequent approval reference, avoiding self-reference.

The protected job independently retrieves the GitHub review history and current
environment protection. It checks the authorized human account ID/type, exact
environment, unique actual approval, exact commitment statement, repository,
workflow and source. It emits `promotion-attestation.json` as an external artifact.
After that workflow succeeds, retain its exact canonical bytes in an evidence-only
PR at `.github/authority-promotions/<source SHA>.json`. Do not change source S,
rebuild packages, retag source, or edit the attestation. This subsequent Git commit
is external evidence, not a new package source or an input to the bundle hash.
The workflow artifact alone is pending evidence; complete durable recording and
qualification before treating it as an effective independent promotion.

The durable evidence path has one introduction and no later edits. Publishers
retrieve it through the authenticated GitHub contents/history APIs, verify its
immutable introduction snapshot and source ancestry, and independently retrieve the
actual successful promotion run and human approval again. An expired/deleted run,
artifact, approval or missing/changed evidence blocks publication. A cached record
alone is never sufficient trust. Preserve retained artifacts and workflow evidence
for the period in which promotion/retry is needed; do not imply infinite Actions
artifact retention.

Earlier genuine promotion records additionally freeze their exact SCFs and resource
closures. They are independently checked against original source authorization,
successful qualification/approval runs and actual human review history. Deleting
records cannot erase that obligation. Later same-version changed content is rejected
and requires a successor. Historical freeze evidence never authorizes a current
publisher or substitutes for the current retained ZIP. Inventory lifecycle labels
are reproducible as of source S; later external approvals do not rewrite its bytes.

## Identical PyPI and npm admission

Both publishers retain the existing successful `main`-push resolver and exact tag/
source/version requirements. Both their resolve and credential-bearing publish jobs
independently download the same immutable retained ZIP and execute the same
`release_authority_promotion.py verify` gate. The ZIP hash must match GitHub's exact
artifact metadata, and all extracted bytes must equal the verified ZIP. Redirected
blob downloads never receive the GitHub bearer token.

Each verification rechecks the source, full inventory, SCFs/closures, package bytes,
manifests, exact approved authority cohort, live authorized human evidence and
durable attestation. The publish job additionally pins the attestation digest
admitted by its resolve job. No package is rebuilt, no authority is stripped, and
OIDC credentials remain confined to the final publish job. Node's existing exact
version/no-op check and PyPI trusted publishing remain in place.

Missing, forged, stale, foreign, ambiguous, rehashed-but-unauthorized or changed
evidence blocks both publishers. Inventory counts are observations, never a proof
or a permanent contract-version baseline. This gate does not make a candidate
implemented, select it in SCS, authorize Constructed, or bypass required review.

## Qualification responsibilities

Permanent tests exercise ordinary archive and publisher verification functions with
real canonical authority and source WASM. Only GitHub transport is substituted for
adversarial human/API cases; no production fixture-acceptance switch exists. Local
qualification also scans actual built wheel/sdist/npm payloads. A real protected
environment approval and package/authority promotion are separate human release
actions and are deliberately not performed by implementation or CI fixtures.

The earlier `check_semantic_contract_lifecycle_design.py` helper remains a bounded
specification validator and deliberately never returns publisher authorization.
Its design-only `publisher_enforcement` field is not a repository-wide feature
switch. Operational admission is the shared `verify_promotion` path wired into both
publishers and independently exercised by the enforcement tests.
