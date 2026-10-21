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
preserved; no identity minter is called. The same resolved child fragment under
two distinct parents is already a provable ownership violation under DEC-0274,
including while its UUID is pending. It emits `duplicate_identity` with the
unresolved identity sentinel. Request keys locate the resolved fragment objects;
they never become canonical identities. Equality of canonical identities between
distinct pending fragments remains outstanding until identities exist.

Cycle edges require a relation whose containment meaning is selected from the
qualified table, plus unambiguous endpoints satisfying its create/prepared
policy. Unknown or unmapped relation tokens contribute no containment edges.
Structural containment intent is distinct from successful type-pair binding:
frozen ACC12-20 requires rejecting the two `contains` intents' cycle even though
the reverse type pair independently has no row. Such structural violations
remain visible alongside other independent failures. An unavailable binding
does not authorize insertion or make an arbitrary relation containment.

These preconditions do not themselves validate complete prepared Authoring
objects. The separate internal insertion seam below validates those objects;
reference interpretation outside composition endpoints remains deferred.

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
| 01–02 | Exact row/endpoint selection; complete child insertion, authored sibling ordering, retained unsealed child bytes | Qualified artifacts, complete records and roots |
| 03 | Binding-decision and composed-byte permutation invariance with fixed identities | Complete construction qualification |
| 04 | Supplied identity retention, complete embedded child equality and input non-mutation | Complete records and roots |
| 05 | One UUIDv7 establishment per participating create fragment, complete child bytes | Complete construction qualification; independent mint calls are not claimed byte-identical |
| 06–22 | Published structural diagnostic codes and qualification status precedence | Complete construction result/evidence |
| 23–24 | Independent proof gate rejects child-field and identity mutation in actual serialized bytes | Complete composition records and source sealing |
| 25–26 | Deferred | Exact-subtree root omission and source-root accounting |
| 27–32 | Missing/tampered resources, incorrect digest/version/SCF, incomplete closure | No construction claim |
| 33–37 | Inner authority recheck guards for AI/ADC disagreement, duplicate rows, unqualified row claims; table schema rejection | Entry-point tampering fails earlier exact closure verification; no alternate publication is accepted |
| 38–39 | Independent diagnostic retention, stable ordering and status precedence | No ACC construction outcome is emitted |
| 40–41 | Reference-basis endpoint rejection; supplied child identity under multiple parents; same-fragment pending-ID ownership regression | Complete composition evidence |

Additional tests cover both endpoint roles, forbidden fallbacks, missing
companion/inherited schema resources, invalid schema references, unsupported
schema branches, unqualified fragments, invalid supplied IDs, and absence of a
protocol 1.5 route. Existing ACC 1.0/1.1 and host tests remain regression gates.

The post-merge ownership/cycle cleanup also tests pending-ID multi-parent
conflicts, distinct pending fragments whose identity equality remains deferred,
unknown relation loops, and retained mixed diagnostics under request-array
permutations. ACC12-19/20 remain unchanged structural cycle oracles.

The internal insertion seam produces unchanged tracked WASM bytes under Rust
1.99.1. The artifact guard now accepts unchanged binaries only after building
the exact checkout and comparing nonempty source-built bytes with both tracked
host copies. A stale target, build failure, or either mismatched copy fails
closed. Existing source-build parity and host checks still run.

## Internal insertion and preservation proof

`authoring_construction_v12::insertion::insert` consumes the existing qualifier's
binding decisions. It is not a protocol operation. The bounded seam supports
requests whose fragments all participate in qualified compositions; unbound
native aggregation remains explicitly unavailable. No identity is allocated
until initial authority, structural, schema-preflight and serializer-authority
checks pass. Missing create IDs use the existing environmental `IdentityMinter`
and `establish_identity` helper; supplied IDs bypass minting. Every participating
fragment is established once, even when a parent has several children. A sorted
request-key map schedules allocation; keys never enter the minter. Environmental
allocation is not claimed repeatable across independent mint operations.

The established request clone is requalified to reuse canonical-identity and
ownership checks. The original request is untouched. Selected Authoring 1.7
schemas come from verified binding rows and the sealed resource map. Prepared
child objects contain exactly the supplied fields plus established ID. No alias,
rationale, optional array or other default is manufactured. The complete parent
is validated after compiler-owned insertion, since its required child property
must be absent in prepared input. All reachable selected schema branches are
preflighted. The governed serializer's compiled schema catalog must equal the
verified closure; it cannot supply fallback authority.

The coordinator consumes the qualifier's authored binding order and property
selectors. It retains each native child separately and serializes parents and
children using `adr-kit.authoring-yaml/v1`. A separate proof gate decodes actual
bytes, verifies canonical rerendering and qualified schema selectors, compares embedded and
retained children deeply against immutable prepared fields plus established ID,
and checks every other parent field remains unchanged. Membership count and
ordering must match the qualified decisions. The result is `PreservationProven`,
an internal status with partial subtree proofs, never `Sealed` or an ACC outcome.

Any failure releases no materials or subtree proofs. Governed child/identity
mutation diagnostics retain their published codes and sorting. Internal typed
`PreservationFailure` values also distinguish parent-field mutation, missing
material, changed membership, invalid serialization and changed retained child
material; these are implementation proof failures, not new ACC wire codes.
Failure tests modify actual rendered bytes independently of the compiler path.
An environmental mint failure is unavailable; duplicate allocated IDs are
rejected by the reused qualifier. Allocation may consume entropy before a later
validation failure; no persistence or rollback is implied.

## Deferred execution and next slice

No child-root omission, complete composition record, final source references,
source-basis sealing, or composed candidate admission is produced. Complete NM
2.4 interpretation, ledgers, comparison and construction qualification remain
unavailable. Protocol 1.5 and its composition capability flags are unchanged;
ACC 1.1 composition remains unavailable. Published contract bytes and current
semantic-contract selection are unchanged.

The next separately authorized slice can consume retained native material and
subtree proofs to establish qualified source references/digests, exact-subtree
child-root omission, complete semantic/integrity composition evidence, and
minimal composed-source sealing. Non-composition references must also be
qualified before any complete basis claim. The current proofs satisfy only the
insertion and preservation obligations, not these remaining obligations.
