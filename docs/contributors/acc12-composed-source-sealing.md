# Internal ACC 1.2 composed source sealing

`authoring_construction_v12::sealing` produces internal `Sealed` evidence for
the composition-participating inputs supported by the existing producer chain.
It does not route through a protocol operation or claim ACC `Constructed`.

## Evidence boundary

`prepare` independently replays the complete published composition-record
verifier. That verifier rechecks the private established-request insertion
receipt, exact ACC closure, complete artifact/root accounting and all applicable
dependencies. The complete record result must match, including diagnostics and
outstanding obligations. Status flags alone are never proof.

`qualify_seal` replays preparation and compares the entire supplied result:
retained artifacts, minimal roots, native basis commitment, ACC schema projection,
record-to-source association and detached context. Stale or tampered evidence
releases neither a sealed basis nor a context. Independent diagnostics retain
Rejected, Unavailable, Unresolved precedence and deterministic ordering.

## Basis commitment

All parent and child candidate artifacts remain independently retained. Only
the exactly verified minimal roots enter `candidate_source::seal_candidate_source_basis`.
Parents remain roots; independently retained embedded children are omitted once
only after insertion, exact-subtree and record proofs qualify. No generic subtree
search or request intent is substituted for those proofs.

The existing native sealer owns `adr-kit.candidate-source-basis/v1`, canonical
descriptor serialization, exact byte digests and deterministic `source_ref`
ordering. This slice adds no second descriptor serializer or fingerprint
algorithm. The existing ACC projection is reused and validated against the
exact sealed `candidate_source_basis` schema fragment. Source bytes, schema
selectors, serialization profiles, source contracts and identities are unchanged.

## Detached context

The exact verified resource
`architecture-interpretation/1.2/detached-context` supplies the domain, provider,
namespace and URI forms. Basis digest and SHA-256 of the exact UTF-8 root
`source_ref` instantiate those forms. Exact AI 1.2 and NM 2.4 qualifications
participate in context evidence, not locator derivation.

Each minimal root retains its established UUID, canonical source reference,
exact Authoring qualification and root source pointer `/`, using the existing
interpretation source/output context types. Embedded child fields and identities
remain in the retained artifact bytes and complete composition records; AI owns
their subsequent interpretation and source pointers. Detached locators remain
opaque, with no repository placement, alias reservation, persistence or admission.

## Coverage and remaining work

Tests exercise ACC12-01/02 source-basis properties, multiple parents/ordered
children, root/artifact separation, descriptor reproduction, context derivation,
permutations, forged prerequisites, byte/digest/schema/profile/authority changes,
record-linkage changes and stale context. Full frozen construction cases are not
reclassified as implemented.

The existing insertion gate does not authorize unbound standalone aggregation.
Such inputs remain blocked. Retired/custom/owner-local reference execution,
relationship construction and additional membership ownership also remain
unavailable; none can be silently omitted to obtain a seal.

Only `composed_candidate_basis_sealing` is discharged here. Complete detached
AI 1.2 interpretation into NM 2.4, expected/observed ledgers, whole-result
equivalence and complete construction qualification remain outstanding.
Published authority, historical ACC behavior, SCS, protocol 1.5 and public host
capabilities remain unchanged.
