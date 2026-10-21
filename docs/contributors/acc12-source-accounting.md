# Internal ACC 1.2 artifact qualification and root accounting

`authoring_construction_v12::sources` consumes completed insertion from PR #168.
It is crate-internal, with no protocol operation or capability flag. Its success
status is `RootsAccounted`, not an ACC construction outcome or a sealed basis.

## Proof boundary

Insertion retains a private established-request receipt and identity
dispositions. Before artifact qualification, the source coordinator requalifies
that receipt under the supplied exact ACC 1.2 closure, rechecks serialized bytes
and all preservation obligations, and compares the complete qualified proof set.
A caller-set `PreservationProven`, a qualifier-only result, missing/changed
proofs, changed identity dispositions, or inconsistent material cannot pass.
Private receipt lists normalize only nonsemantic fragment/composition order;
authored ordering values and all source fields remain unchanged.

The exact binding table remains authority for parent property, schema selectors,
semantic types, identities and authored ordering. For every membership, the gate
checks the child at that selected property and induced sequence position against
the complete established child and its retained native artifact. Pair-only
generic subtree search is never sufficient authority to omit a source root.

## Artifacts and references

The caller supplies one opaque, nonempty source reference per participating
request key. ACC's inherited artifact schema requires nonempty locators and
unique references; it does not prescribe repository paths or derive canonical
identity from a locator. No reference is parsed as a path, resolved against the
filesystem, or treated as a persistence instruction. The existing
`candidate/<request_key>` convention is usable but is not new semantic authority.

The existing `seal_candidate_artifact` helper supplies the governed
`adr-kit.authoring-yaml/v1` bytes and lowercase SHA-256 digest. This helper seals
an individual artifact, not a complete construction basis. Its rerendered bytes
must exactly equal verified insertion material. The source contract is the
receipt's exact Authoring 1.7 qualification. Parents are authoring documents;
children remain separate native authoring fragments even after embedding.

The independent validation seam checks the complete artifact set, unique source
references/request keys, digest/profile/schema/contract/kind, exact bytes, and
canonical decoding/validation. A rewritten source with an otherwise valid new
digest still fails comparison with insertion's receipt.

## Minimal roots

Only after exact-property and identity proof does the coordinator construct
containment pairs for the existing minimal-root selector. The parent remains a
root; every proved embedded child is omitted once, with its artifact retained.
Artifacts and roots sort by exact source reference. Proposed root sets may be
permuted, but missing/extra/duplicate roots, including an embedded child retained
as a root, are rejected. Each participating canonical identity is counted once
across the selected roots and their proved children.

This bounded seam does not account for other prepared child memberships. The
exact verified AI field dispositions identify additional authored memberships;
if a nonselected membership is nonempty, accounting is unavailable. Such units
cannot silently evade the canonical identity union check or gain containment
authority from a schema shape. Their fields are not reinterpreted or rewritten.

Typed root-accounting evidence binds each qualified decision to parent/child
source references, exact content digests, established identities, selected
property, induced sequence index, exact subtree and child retention/omission.
This is partial integrity evidence, not a complete published composition record.
All failures clear artifacts, roots and accounting evidence. Governed
`containment_accounting` diagnostics reject inconsistent evidence; unavailable
authority/capability remains unavailable. Diagnostics sort deterministically and
retain independent artifact violations.

## Conformance and remaining obligations

Tests exercise positive artifact-retention/minimal-root properties from
ACC12-01/02 and negative accounting properties from ACC12-25/26. They cover
tampered bytes, wrong identity/digest/kind/schema/authority, duplicate source
references, missing proof/material, wrong property, incorrect root inclusion or
omission, mixed diagnostics, multiple roots and request/artifact/root permutations.
Frozen publications remain authority-only; no complete construction case is
relabeled as executed.

The result contains no `CandidateSourceBasis`, basis digest, sealed flag,
detached NM context or complete composition record. It never invokes the
complete-basis sealer. Non-composition references and relationships remain
explicit outstanding obligations even when a fixture has no such intent.
Before complete composed-source sealing, a later slice must qualify those
dependencies, assemble and validate every required composition-record semantic,
integrity and qualification field, and qualify the complete source basis and
detached context. NM interpretation, ledgers/equivalence and Constructed remain
unimplemented. Protocol 1.5, host behavior, current SCS and immutable authorities
are unchanged.

## WASM acceptance

This internal code has no exported runtime effect. Canonical tracked binaries
are the hosted Linux Rust 1.99.1 build. The artifact-change gate accepts unchanged
host copies only after a fresh source build proves exact nonempty byte parity
with both copies; build errors, missing output or either stale copy fail closed.
Windows compiler panic locations differ from Linux and do not establish
cross-platform byte reproducibility. Windows source-build/fanout parity and the
final hosted Linux commit-bound artifact comparison are recorded separately.
