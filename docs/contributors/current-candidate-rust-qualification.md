# Private current-candidate Rust authority qualification

`candidate_authority::qualify(nm, ai, acc)` is an internal Rust boundary for
NM 2.5, AI 1.5 and ACC 1.5 definition/resource bundles. It has no protocol route,
SDK export, capability registration, SCS profile or materialization profile.

## Selection and trust

The production selection factory takes no caller configuration. Rust includes
the three maintained canonical definition files directly at build time:

- `contracts/semantic-contract/v1.0/definitions/normalized-model-2.5.json`
- `contracts/architecture-interpretation/v1.5/contract.json`
- `contracts/authoring-construction/v1.5/contract.json`

These are the repository's existing inputs, not another snapshot/registry or
handwritten SCF constants. The independently audited source revision selects
authority. Caller fingerprints, flags, profiles, packaged mirrors and resource
counts cannot establish it. Production does not read the filesystem or resolve
current/latest versions. Supplied definitions must have the exact selected
family/version and verified canonical commitment. Shared SCF normalization
permits manifest/dependency permutations without accepting different content.

Candidate revisions remain governed by ADR-L-0040. Update maintained inputs,
independently qualify their semantics with the existing AI/ACC publication
qualifiers, regenerate consistent distributions, and rebuild Rust. The same
version can then have a different qualified SCF. Previously built selections do
not silently adopt a caller's new or stale bundle. No release promotion occurs.

This seam authenticates a supplied bundle against maintained authority and
independently verifies its structure and links. It does **not** replace the
publication qualifiers' complete semantic audit of maintained rules/catalogs.
A source-code change to the trust inputs still requires those repository gates
and review. No Python success receipt is accepted by the Rust interface.

## Independent checks

The shared `semantic_contract.rs` implementation calculates/verifies canonical
SCFs and validates full resource closures. Every supplied member remains visible,
including duplicates, extras, conflicts and unknown fields. Membership, resource
roles, normative conformance, content digests and actual dependency edges must
match the maintained selection. No second serializer or fingerprint algorithm
is introduced.

The qualifier independently compares ACC's AI selection with qualified AI 1.5,
AI's NM selection with qualified NM 2.5, and ACC's NM selection with that same
authority. Embedded definition resources must identify those qualified roots.
Overlapping canonical keys must have identical content across all three closures.
The union contains only their selected resources.

Inherited AI 1.3 dispositions, lifecycle/ownership/context rules, the AI 1.4
output authority and ACC 1.3 ledger keep their actual keys and digest-qualified
contents. An embedded historical definition is qualified provenance; its internal
manifest is not automatically imported as another current selection. Existing
Git-based historical reproduction remains separate and unchanged.

## Result and execution boundary

The private immutable result exposes status, sorted/deduplicated diagnostics,
derived authority identities/counts and the qualified resource map. No public DTO
is added. Any failure clears all authority/resource evidence while retaining
independently discovered violations. Resource ordering is normalized only for
deterministic verification/diagnostics; invalid values still reach the verifier.

Invalid caller selection or closure is `Rejected`. Unusable maintained trust
inputs are `Unavailable`; known caller violations still take precedence. This
static seam establishes no governed unresolved instance dependency and therefore
does not manufacture `Unresolved`. Complete interpretation is always
`Unavailable`, and instance applicability remains `Unknown`.

Schema resources are content- and dependency-qualified here. This is not an
instance JSON Schema evaluation or a claim that every schema keyword/branch has
been executed. Interpretation must separately qualify applicable source/output
schemas and instance conditions. There are no partially materialized entities,
source insertions, identity minting, recipe outputs, semantic ledgers,
`semantic_equivalent` or `Constructed` results.

The unchanged selected catalog retains 27 types, six branches, 240 producer
definitions, 215 BLOCKED destinations, 26 label rules, 54 identity definitions,
three admitted operations and five independent evidence checks. Regression counts
do not substitute for exact content/selection qualification or instance evidence.

## Verification

`cargo test --manifest-path core/Cargo.toml candidate_authority` uses actual
canonical resources. Tests cover exact positive qualification, permutations,
missing/extra/duplicate/conflicting members, malformed digests/edges, wrong
family/version/role/conformance, stale mirrors, historical substitution and
caller flags. Internally valid, rehashed unauthorized definitions are explicitly
shown to pass native cryptographic closure checks and still fail selection.

A test-only assembly routine models a rebuilt maintained cohort after a schema
title annotation change. It uses shared native commitments, preserves historical
bytes, and qualifies new same-version cross-authority commitments. Old mirrors
cannot qualify against that revised selection, and callers cannot activate it in
the original production build. The private selection implementation used by this
test is not an exposed approval or authority API.

Existing Python semantic/publication audits, Node exact discovery, historical
regressions and package parity remain required. Build WASM from Rust and verify
all host copies; unchanged optimized bytes require a fresh build as proof. A
legitimate changed artifact must update all copies through repository tooling.

The next slice may consume this private authority evidence to qualify sealed
source/identity/context prerequisites for executing the three authorized identity
representation operations. No operation is executed by this change.
