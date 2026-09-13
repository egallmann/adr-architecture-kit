# ADR-Kit 0.11.0 R1 Construction Authority Promotion Traceability

This is bounded promotion evidence for the human-reviewed source `ADR-Kit
Semantic Authoring Construction — Candidate Design Lock R1.0`, reviewed
2026-09-13 on the basis of `69d1bdca6ab536cd18cc777d7d209bfaff990abe`.
It is not normative authority, an executable successor contract, a release
certification, or a second source of semantic meaning. After promotion,
ADR-L-0029 governs.

## Authority and representation

ADR-L-0026 remains the discovery authority. ADR-L-0029 extends it with bounded
construction authority while using the current supported ADR representation.
No unsupported `normative_propositions` field is introduced and no schema rule
is weakened. ADR-Kit constructs detached candidates; persistence, admission,
governance, Runtime Snapshot mutation, and implementation conformance remain
separate authorities.

## Decision traceability

| R1 lock | ADR-L-0029 authority |
| --- | --- |
| Semantic Fragment is primitive; ADR is synthesis | DEC-0128 |
| Detached candidates and separate external authority | DEC-0129, DEC-0197 |
| UUIDv7 identity establishment and stable child identity | DEC-0184; INV-0114, INV-0115 |
| Canonical/custom shared construction and exact contracts | DEC-0185, DEC-0186; INV-0118, INV-0120 |
| Set/graph construction and convergent inputs | DEC-0187, DEC-0188 |
| Shared validation, whole-result success, and round-trip proof | DEC-0189, DEC-0190, DEC-0191; INV-0121, INV-0122, INV-0124, INV-0126, INV-0127 |
| Successor contract line is authorized but deferred | DEC-0192; ADR-L-0029 notes |
| Owner-local topology and NP boundaries | DEC-0193, DEC-0194; INV-0165, INV-0166 |
| Peer Python and TypeScript/Node adapters | DEC-0195; INV-0167 |
| Persistence and transaction design deferred | DEC-0196; INV-0113 |

## Invariant traceability

ADR-L-0029 INV-0113 through INV-0127 preserve the construction authority,
identity, exact-basis, validation, diagnostics, outcome, and round-trip locks.
INV-0165 through INV-0168 preserve NP, topology, peer-host, and downstream
contract-ownership boundaries. The invariant aliases were allocated with the
repository promotion allocator and are projected into the canonical registries.

## Successor boundary

Later slices may define ADC 1.1, Custom Entity Contract 1.0, Authoring
Construction Contract 1.0, authoring 1.7, normalized-model 2.4,
architecture-interpretation 1.1, semantic-core 1.2, and the qualified
`architecture-authoring@1.0` set/profile. This promotion creates none of those
resources, implementations, package claims, or persistence behavior.
