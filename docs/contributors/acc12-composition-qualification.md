# Internal ACC 1.2 composition qualification

`core/src/authoring_construction_v12.rs` is a crate-internal seam for a later
authorized compiler. It has no protocol route, host API, or public capability.
It borrows its inputs and returns typed qualification stages, intermediate
binding decisions, outstanding obligations, and deterministic diagnostics.
`Qualified` refers only to these preconditions. It is neither an ACC outcome
nor a sealed candidate basis. The status type cannot represent `Constructed`.

## Authority and schema boundary

The entry point accepts a definition, its complete resource bundle, and an ACC
request. The shared semantic-contract verifier must establish the complete
closure and the pinned ACC identity before any composition intent is read:

`scf:v1:sha256:8da499420e996c446cbc416dc7db9b4bbb2692ea5039f14461f668aaa48b9e0c`

The rules-selected table and companion schema must name the exact manifest
members and digests. The table is schema-validated, its selection tuples and
binding identifiers are unique, and every row's named AI field disposition,
ADC composition/identity policies, and Authoring schema references are checked.
ADC `input_contract` is never a prepared-field inventory. Binding rows exist
only in the qualified publication; Rust implements the table vocabulary.

Request ACC, AI, ADC, Authoring, and NM qualifications are exact. Fragment
Authoring qualification is also checked. CEC is part of the verified closure;
no custom composition row is selected or interpreted by this slice.

Schema references use the existing semantic-contract path normalizer, including
parent segments such as `../1.1/schema.json#/$defs/uuid_v7`. Resolution uses
only the sealed supplied map. Preflight visits every reachable schema branch
of the selected request fragment and the complete table schema. Missing
references and unsupported keywords fail closed, including optional properties
and alternatives. Unused complete-result definitions remain outside this seam;
their unsupported `unevaluatedProperties` is not silently accepted.

An incorrect ACC literal remains `Unavailable`. A schema-only probe of the
remaining request structure retains independently established shape violations
as `Rejected`; that probe is never used for execution or authority selection.
Inputs outside the shared canonicalizer's supported numeric domain remain
`Unavailable`, with an explicit capability diagnostic, rather than panicking
or using another canonicalization algorithm.

## Implemented checks

Endpoints match exactly one same-request `request_key`. Reference identities
can be recognized for rejection but never copied or resolved as definitions.
Aliases, canonical UUIDs, source references, paths, existing sources, and array
positions are not endpoint fallbacks. Successful decisions require prepared
create fragments and the verified row's semantic-type tuple.

The qualifier checks relation vocabulary, unsupported modes and operations,
non-empty composition keys, self-containment and cycles, duplicate membership,
duplicate sibling ordering, supplied duplicate canonical identities, and
compiler ownership of the selected property. Property presence includes null,
an empty array, and an otherwise equal child value. No field is changed.

Absent create identities remain pending. Supplied valid UUIDv7 values are
preserved; no identity minter is called. Identity-dependent duplicate checks
remain outstanding until identities exist. These preconditions do not validate
complete prepared Authoring objects or relationships: those remain later
construction obligations, along with reference interpretation outside these
composition endpoints.

Diagnostics retain the ACC codes and aggregate in the order Rejected,
Unavailable, Unresolved, then internal Qualified. They sort by status rank,
optional semantic identity, stable field/relation key, code, and the shared
canonical payload's SHA-256. An absent identity is the stable unresolved
sentinel, represented by `None`, never a request locator. Both fragment and
composition array permutations are tested, including failure cases. Failed
qualification returns no usable binding-decision set.

## Frozen conformance properties exercised

The frozen resources remain marked authority-only. No full construction case
is relabeled as implemented runtime coverage.

| ACC12 cases | Properties exercised by Rust tests | Remaining assertions |
| --- | --- | --- |
| 01–02 | Exact row/endpoint selection; authored sibling ordering | Embedding, artifacts, complete records and roots |
| 03 | Binding-decision permutation invariance | Constructed parent-byte equality |
| 04 | Supplied identity retention and input non-mutation | Complete embedded child equality |
| 05 | Missing create identity remains pending | Minting and all constructed-byte assertions |
| 06–22 | Published structural diagnostic codes and qualification status precedence | Complete construction result/evidence |
| 23–26 | Deferred | Child/identity mutation during insertion; exact-subtree and root accounting |
| 27–32 | Missing/tampered resources, incorrect digest/version/SCF, incomplete closure | No construction claim |
| 33–37 | Inner authority recheck guards for AI/ADC disagreement, duplicate rows, unqualified row claims; table schema rejection | Entry-point tampering fails earlier exact closure verification; no alternate publication is accepted |
| 38–39 | Independent diagnostic retention, stable ordering and status precedence | No ACC construction outcome is emitted |
| 40–41 | Reference-basis endpoint rejection; supplied child identity under multiple parents | Complete composition evidence |

Additional tests cover both endpoint roles, forbidden fallbacks, missing
companion/inherited schema resources, invalid schema references, unsupported
schema branches, unqualified fragments, invalid supplied IDs, and absence of a
protocol 1.5 route. Existing ACC 1.0/1.1 and host tests remain regression gates.

## Deferred execution and next slice

No compiler insertion, canonical child materialization, child-field equality,
identity-preservation proof during insertion, exact-subtree/root omission proof,
composition record, or composed candidate sealing is produced. Complete NM
2.4 interpretation, ledgers, comparison and construction qualification remain
unavailable. Protocol 1.5 and its composition capability flags are unchanged;
ACC 1.1 composition remains unavailable. Published contract bytes and current
semantic-contract selection are unchanged.

The next separately authorized slice can reuse these binding decisions to
establish identities once, insert the complete prepared child under compiler
ownership, validate Authoring fields, and produce the ACC 1.2 semantic/integrity
proof partitions and exact-subtree evidence before minimal-root sealing. This
internal qualifier supplies preconditions for that work, not those proofs.
